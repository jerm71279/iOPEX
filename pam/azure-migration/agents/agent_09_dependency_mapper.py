"""Agent 09 — Dependency Mapper (G-04 Gap Closure).

Scans infrastructure to discover everything consuming each credential BEFORE
migration. This is ARC-08: no credential migrates without a dependency map.

Scanners:
    - IIS application pools (WinRM)
    - Windows services (WinRM)
    - Scheduled tasks (WinRM)
    - Jenkins credential stores (REST API)
    - Shell/PowerShell scripts (file system)
    - Configuration files (file system)

Phases:
    P1: Full dependency scan (after Agent 01 discovery)
"""

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from core.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)

# File extensions to scan for hardcoded credentials
SCRIPT_EXTENSIONS = {".sh", ".ps1", ".py", ".bat", ".cmd", ".bash", ".zsh", ".rb", ".pl"}
CONFIG_EXTENSIONS = {
    ".config", ".xml", ".json", ".yaml", ".yml", ".properties", ".ini",
    ".env", ".conf", ".cfg", ".toml",
}
CONFIG_FILENAMES = {
    "web.config", "appsettings.json", "appsettings.development.json",
    "appsettings.production.json", "applicationhost.config",
    "machine.config", "connectionstrings.config",
}

# Patterns indicating credential usage in scripts/configs
CREDENTIAL_PATTERNS = [
    r"AIMWebService", r"GetPassword", r"AppID\s*=", r"CentralCredentialProvider",
    r"CredentialProvider", r"Safe\s*=", r"Object\s*=", r"Folder\s*=",
    r"PVWA", r"CyberArk", r"AIM\s+agent", r"CCPPasswordSDK",
    r"password\s*=\s*[\"']", r"connectionString.*password",
    r"New-PASSession", r"Get-PASAccount", r"Invoke-PASRestMethod",
]


@dataclass
class DependencyRecord:
    """A discovered consumer of a credential."""
    account_id: str
    account_name: str
    dependency_type: str       # iis_app_pool | windows_service | scheduled_task | jenkins | script | config
    consumer_name: str         # Name of the consuming entity
    consumer_host: str         # Host where consumer runs
    consumer_path: str = ""    # File/config path if applicable
    confidence: float = 0.0    # 0.0-1.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    remediation: str = ""      # How to update this consumer post-migration

    def to_dict(self) -> dict:
        return asdict(self)


class DependencyMapperAgent(AgentBase):
    """Discovers credential consumers across infrastructure before migration."""

    AGENT_ID = "agent_09_dependency_mapper"
    AGENT_NAME = "Dependency Mapper"

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})
        errors = []

        # Must have discovery data
        discovery = self.state.get_agent_result("agent_01_discovery", "P1")
        if not discovery:
            errors.append("No discovery data. Run Agent 01 first.")

        # Check agent config exists
        agent_cfg = self.config.get("agent_09_dependency_mapper", {})
        enabled = agent_cfg.get("enabled_scanners", [])
        if not enabled:
            errors.append("No scanners enabled in agent_09_dependency_mapper config.")

        # Check WinRM connectivity if Windows scanners enabled
        winrm_scanners = {"iis", "windows_service", "scheduled_task"}
        if winrm_scanners & set(enabled):
            hosts = agent_cfg.get("scan_hosts", [])
            if not hosts:
                errors.append(
                    "Windows scanners enabled but no scan_hosts configured. "
                    "Set agent_09_dependency_mapper.scan_hosts in agent_config.json."
                )

        if errors:
            return self._result("failed", errors=errors)

        self.logger.log("preflight_passed", {"enabled_scanners": enabled})
        return self._result("success", data={"enabled_scanners": enabled})

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase != "P1":
            return self._result("failed", phase=phase,
                                errors=[f"Agent 09 runs in P1, not {phase}"])

        self.logger.log("dependency_scan_start", {"phase": phase})
        agent_cfg = self.config.get("agent_09_dependency_mapper", {})
        enabled = set(agent_cfg.get("enabled_scanners", []))
        confidence_threshold = agent_cfg.get("confidence_threshold", 0.5)

        # Load discovery data
        raw = self.state.get_raw_data("agent_01_discovery", "P1") or {}
        accounts = raw.get("raw_accounts", [])
        if not accounts:
            return self._result("failed", phase=phase,
                                errors=["No raw account data from discovery."])

        # Build lookup structures
        account_names = {}  # lowercase name → account
        account_usernames = {}  # lowercase username → account
        for acct in accounts:
            acct_id = acct.get("id", "")
            name = (acct.get("name") or "").lower()
            username = (acct.get("userName") or "").lower()
            if name:
                account_names[name] = acct
            if username:
                account_usernames[username] = acct
            # Also index by address\username pattern
            addr = (acct.get("address") or "").lower()
            if addr and username:
                account_usernames[f"{addr}\\{username}"] = acct

        all_deps: Dict[str, List[dict]] = {}
        scan_results = {}

        # Run each enabled scanner
        hosts = agent_cfg.get("scan_hosts", [])
        winrm_port = agent_cfg.get("winrm_port", 5986)
        winrm_transport = agent_cfg.get("winrm_transport", "kerberos")

        if "iis" in enabled and hosts:
            deps = self._scan_iis_app_pools(
                hosts, account_usernames, winrm_port, winrm_transport)
            scan_results["iis"] = len(deps)
            self._merge_deps(all_deps, deps)

        if "windows_service" in enabled and hosts:
            deps = self._scan_windows_services(
                hosts, account_usernames, winrm_port, winrm_transport)
            scan_results["windows_service"] = len(deps)
            self._merge_deps(all_deps, deps)

        if "scheduled_task" in enabled and hosts:
            deps = self._scan_scheduled_tasks(
                hosts, account_usernames, winrm_port, winrm_transport)
            scan_results["scheduled_task"] = len(deps)
            self._merge_deps(all_deps, deps)

        if "jenkins" in enabled:
            jenkins_urls = agent_cfg.get("jenkins_urls", [])
            if jenkins_urls:
                deps = self._scan_jenkins_jobs(
                    jenkins_urls, account_names, account_usernames)
                scan_results["jenkins"] = len(deps)
                self._merge_deps(all_deps, deps)

        if "script" in enabled:
            scan_dirs = agent_cfg.get("scan_directories", [])
            if scan_dirs:
                deps = self._scan_scripts(scan_dirs, account_names, account_usernames)
                scan_results["script"] = len(deps)
                self._merge_deps(all_deps, deps)

        if "config" in enabled:
            config_paths = agent_cfg.get("config_scan_paths", [])
            if config_paths:
                deps = self._scan_config_files(
                    config_paths, account_names, account_usernames)
                scan_results["config"] = len(deps)
                self._merge_deps(all_deps, deps)

        # Filter by confidence threshold
        filtered_deps = {}
        for acct_id, dep_list in all_deps.items():
            high_conf = [d for d in dep_list if d.get("confidence", 0) >= confidence_threshold]
            if high_conf:
                filtered_deps[acct_id] = high_conf

        # Build summary
        total_deps = sum(len(v) for v in filtered_deps.values())
        by_type: Dict[str, int] = {}
        for dep_list in filtered_deps.values():
            for dep in dep_list:
                dt = dep.get("dependency_type", "unknown")
                by_type[dt] = by_type.get(dt, 0) + 1

        summary = {
            "total_accounts_scanned": len(accounts),
            "accounts_with_dependencies": len(filtered_deps),
            "accounts_without_dependencies": len(accounts) - len(filtered_deps),
            "total_dependencies": total_deps,
            "dependencies_by_type": by_type,
            "scan_results": scan_results,
            "confidence_threshold": confidence_threshold,
            "scanners_run": list(enabled),
        }

        # Store raw dependency map (indexed by account ID)
        self.state.store_raw_data(self.AGENT_ID, phase, {
            "dependency_map": filtered_deps,
            "all_deps_unfiltered": all_deps,
        })
        self.state.store_agent_result(self.AGENT_ID, phase, summary)
        self.state.complete_step("P1:dependency_mapping")

        self.logger.log("dependency_scan_complete", summary)

        return self._result(
            "success", phase=phase, data=summary,
            metrics={
                "accounts_with_deps": len(filtered_deps),
                "total_deps_found": total_deps,
                "scanners_run": len(scan_results),
            },
            next_action="Review dependency map before migration. Accounts with dependencies "
                        "will require approval before ETL migration (ARC-08).",
        )

    # ── Scanner: IIS App Pools ──────────────────────────────────

    def _scan_iis_app_pools(
        self, hosts: List[str], account_lookup: Dict[str, dict],
        winrm_port: int, winrm_transport: str,
    ) -> List[dict]:
        """Scan IIS application pools for service account usage via WinRM."""
        self.logger.log("scan_iis_start", {"hosts": len(hosts)})
        deps = []

        ps_command = (
            "Import-Module WebAdministration -ErrorAction SilentlyContinue; "
            "Get-ChildItem IIS:\\AppPools | ForEach-Object { "
            "[PSCustomObject]@{"
            "Name=$_.Name;"
            "UserName=$_.processModel.userName;"
            "IdentityType=$_.processModel.identityType;"
            "State=$_.state"
            "} } | ConvertTo-Json -Compress"
        )

        for host in hosts:
            try:
                result = self._run_winrm(host, ps_command, winrm_port, winrm_transport)
                if not result:
                    continue

                pools = json.loads(result) if isinstance(result, str) else result
                if isinstance(pools, dict):
                    pools = [pools]

                for pool in pools:
                    identity_type = str(pool.get("IdentityType", "")).lower()
                    username = str(pool.get("UserName", "")).lower()
                    pool_name = pool.get("Name", "")

                    # Only check pools with specific user identity
                    if identity_type not in ("specificuser", "3"):
                        continue

                    matched_acct = self._match_account(username, account_lookup)
                    if matched_acct:
                        deps.append(DependencyRecord(
                            account_id=matched_acct.get("id", ""),
                            account_name=matched_acct.get("name", ""),
                            dependency_type="iis_app_pool",
                            consumer_name=pool_name,
                            consumer_host=host,
                            confidence=0.95,
                            evidence={"pool": pool_name, "identity_type": identity_type,
                                      "state": pool.get("State", "")},
                            remediation=f"Update IIS App Pool '{pool_name}' on {host} "
                                        f"to use new credential after migration.",
                        ).to_dict())

            except Exception as e:
                logger.warning(f"IIS scan failed for {host}: {e}")
                self.logger.log("scan_iis_error", {"host": host, "error": str(e)})

        self.logger.log("scan_iis_complete", {"deps_found": len(deps)})
        return deps

    # ── Scanner: Windows Services ───────────────────────────────

    def _scan_windows_services(
        self, hosts: List[str], account_lookup: Dict[str, dict],
        winrm_port: int, winrm_transport: str,
    ) -> List[dict]:
        """Scan Windows services for service account logon credentials via WinRM."""
        self.logger.log("scan_services_start", {"hosts": len(hosts)})
        deps = []

        ps_command = (
            "Get-WmiObject Win32_Service | Where-Object { "
            "$_.StartName -and $_.StartName -ne 'LocalSystem' -and "
            "$_.StartName -ne 'NT AUTHORITY\\\\LocalService' -and "
            "$_.StartName -ne 'NT AUTHORITY\\\\NetworkService' -and "
            "$_.StartName -ne 'NT SERVICE' } | "
            "Select-Object Name, DisplayName, StartName, PathName, State | "
            "ConvertTo-Json -Compress"
        )

        for host in hosts:
            try:
                result = self._run_winrm(host, ps_command, winrm_port, winrm_transport)
                if not result:
                    continue

                services = json.loads(result) if isinstance(result, str) else result
                if isinstance(services, dict):
                    services = [services]

                for svc in services:
                    start_name = str(svc.get("StartName", "")).lower()
                    svc_name = svc.get("Name", "")
                    display_name = svc.get("DisplayName", "")

                    matched_acct = self._match_account(start_name, account_lookup)
                    if matched_acct:
                        deps.append(DependencyRecord(
                            account_id=matched_acct.get("id", ""),
                            account_name=matched_acct.get("name", ""),
                            dependency_type="windows_service",
                            consumer_name=f"{display_name} ({svc_name})",
                            consumer_host=host,
                            confidence=0.95,
                            evidence={"service": svc_name, "start_name": start_name,
                                      "state": svc.get("State", ""),
                                      "path": svc.get("PathName", "")},
                            remediation=f"Update service '{svc_name}' logon account on {host} "
                                        f"after credential migration. Restart service.",
                        ).to_dict())

            except Exception as e:
                logger.warning(f"Service scan failed for {host}: {e}")
                self.logger.log("scan_services_error", {"host": host, "error": str(e)})

        self.logger.log("scan_services_complete", {"deps_found": len(deps)})
        return deps

    # ── Scanner: Scheduled Tasks ────────────────────────────────

    def _scan_scheduled_tasks(
        self, hosts: List[str], account_lookup: Dict[str, dict],
        winrm_port: int, winrm_transport: str,
    ) -> List[dict]:
        """Scan Windows scheduled tasks for credential usage via WinRM."""
        self.logger.log("scan_tasks_start", {"hosts": len(hosts)})
        deps = []

        ps_command = (
            "Get-ScheduledTask | Where-Object { $_.Principal.UserId -and "
            "$_.Principal.UserId -ne 'SYSTEM' -and "
            "$_.Principal.UserId -ne 'LOCAL SERVICE' -and "
            "$_.Principal.UserId -ne 'NETWORK SERVICE' } | "
            "ForEach-Object { [PSCustomObject]@{"
            "TaskName=$_.TaskName;"
            "TaskPath=$_.TaskPath;"
            "UserId=$_.Principal.UserId;"
            "State=$_.State"
            "} } | ConvertTo-Json -Compress"
        )

        for host in hosts:
            try:
                result = self._run_winrm(host, ps_command, winrm_port, winrm_transport)
                if not result:
                    continue

                tasks = json.loads(result) if isinstance(result, str) else result
                if isinstance(tasks, dict):
                    tasks = [tasks]

                for task in tasks:
                    user_id = str(task.get("UserId", "")).lower()
                    task_name = task.get("TaskName", "")
                    task_path = task.get("TaskPath", "")

                    matched_acct = self._match_account(user_id, account_lookup)
                    if matched_acct:
                        deps.append(DependencyRecord(
                            account_id=matched_acct.get("id", ""),
                            account_name=matched_acct.get("name", ""),
                            dependency_type="scheduled_task",
                            consumer_name=f"{task_path}{task_name}",
                            consumer_host=host,
                            confidence=0.90,
                            evidence={"task": task_name, "path": task_path,
                                      "user_id": user_id,
                                      "state": str(task.get("State", ""))},
                            remediation=f"Update scheduled task '{task_name}' credentials "
                                        f"on {host} after migration.",
                        ).to_dict())

            except Exception as e:
                logger.warning(f"Task scan failed for {host}: {e}")
                self.logger.log("scan_tasks_error", {"host": host, "error": str(e)})

        self.logger.log("scan_tasks_complete", {"deps_found": len(deps)})
        return deps

    # ── Scanner: Jenkins ────────────────────────────────────────

    def _scan_jenkins_jobs(
        self, jenkins_urls: List[str],
        name_lookup: Dict[str, dict], username_lookup: Dict[str, dict],
    ) -> List[dict]:
        """Scan Jenkins credential stores and pipeline configs for CyberArk references."""
        self.logger.log("scan_jenkins_start", {"urls": len(jenkins_urls)})
        deps = []

        for base_url in jenkins_urls:
            try:
                import requests
                base_url = base_url.rstrip("/")

                # Jenkins credentials API
                jenkins_token = os.environ.get("JENKINS_API_TOKEN", "")
                jenkins_user = os.environ.get("JENKINS_API_USER", "")
                auth = (jenkins_user, jenkins_token) if jenkins_user and jenkins_token else None

                # Get credential stores
                cred_url = f"{base_url}/credentials/store/system/domain/_/api/json"
                resp = requests.get(
                    cred_url,
                    params={"tree": "credentials[id,description,typeName]"},
                    auth=auth, timeout=30, verify=True,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    creds = data.get("credentials", [])

                    for cred in creds:
                        cred_id = cred.get("id", "").lower()
                        cred_desc = cred.get("description", "").lower()

                        # Check if credential ID or description matches account names
                        for lookup in (name_lookup, username_lookup):
                            for acct_key, acct in lookup.items():
                                if acct_key in cred_id or acct_key in cred_desc:
                                    deps.append(DependencyRecord(
                                        account_id=acct.get("id", ""),
                                        account_name=acct.get("name", ""),
                                        dependency_type="jenkins",
                                        consumer_name=f"Jenkins credential: {cred.get('id', '')}",
                                        consumer_host=base_url,
                                        confidence=0.75,
                                        evidence={"credential_id": cred.get("id", ""),
                                                  "type": cred.get("typeName", ""),
                                                  "description": cred.get("description", "")},
                                        remediation=f"Update Jenkins credential '{cred.get('id', '')}' "
                                                    f"at {base_url} after migration.",
                                    ).to_dict())
                                    break

                # Scan pipeline configs for CyberArk patterns
                jobs_url = f"{base_url}/api/json"
                resp = requests.get(
                    jobs_url,
                    params={"tree": "jobs[name,url]"},
                    auth=auth, timeout=30, verify=True,
                )

                if resp.status_code == 200:
                    jobs = resp.json().get("jobs", [])
                    for job in jobs[:100]:  # Limit to prevent excessive scanning
                        job_name = job.get("name", "")
                        config_url = f"{base_url}/job/{job_name}/config.xml"
                        try:
                            cfg_resp = requests.get(
                                config_url, auth=auth, timeout=10, verify=True)
                            if cfg_resp.status_code == 200:
                                config_text = cfg_resp.text
                                for pattern in CREDENTIAL_PATTERNS[:6]:  # CyberArk-specific
                                    if re.search(pattern, config_text, re.IGNORECASE):
                                        deps.append(DependencyRecord(
                                            account_id="",
                                            account_name="",
                                            dependency_type="jenkins",
                                            consumer_name=f"Jenkins job: {job_name}",
                                            consumer_host=base_url,
                                            consumer_path=config_url,
                                            confidence=0.70,
                                            evidence={"job": job_name, "pattern": pattern},
                                            remediation=f"Update CyberArk references in "
                                                        f"Jenkins job '{job_name}' pipeline config.",
                                        ).to_dict())
                                        break
                        except Exception:
                            pass

            except ImportError:
                logger.warning("requests library not available for Jenkins scanning")
                break
            except Exception as e:
                logger.warning(f"Jenkins scan failed for {base_url}: {e}")
                self.logger.log("scan_jenkins_error", {"url": base_url, "error": str(e)})

        self.logger.log("scan_jenkins_complete", {"deps_found": len(deps)})
        return deps

    # ── Scanner: Scripts ────────────────────────────────────────

    def _scan_scripts(
        self, scan_dirs: List[str],
        name_lookup: Dict[str, dict], username_lookup: Dict[str, dict],
    ) -> List[dict]:
        """Scan shell/PowerShell scripts for hardcoded credential references."""
        self.logger.log("scan_scripts_start", {"dirs": len(scan_dirs)})
        deps = []

        for scan_dir in scan_dirs:
            scan_path = Path(scan_dir)
            if not scan_path.exists():
                logger.warning(f"Script scan directory not found: {scan_dir}")
                continue

            for file_path in self._walk_files(scan_path, SCRIPT_EXTENSIONS):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    content_lower = content.lower()

                    # Check for account name references
                    for acct_key, acct in {**name_lookup, **username_lookup}.items():
                        if len(acct_key) < 4:  # Skip very short names to avoid false positives
                            continue
                        if acct_key in content_lower:
                            # Verify it's not a comment or variable name collision
                            lines = content.split("\n")
                            for line_num, line in enumerate(lines, 1):
                                if acct_key in line.lower():
                                    deps.append(DependencyRecord(
                                        account_id=acct.get("id", ""),
                                        account_name=acct.get("name", ""),
                                        dependency_type="script",
                                        consumer_name=file_path.name,
                                        consumer_host="local",
                                        consumer_path=str(file_path),
                                        confidence=0.65,
                                        evidence={"file": str(file_path),
                                                  "line": line_num,
                                                  "snippet": line.strip()[:200]},
                                        remediation=f"Update credential reference in "
                                                    f"{file_path.name}:{line_num}",
                                    ).to_dict())
                                    break  # One match per file per account

                    # Check for CyberArk API patterns
                    for pattern in CREDENTIAL_PATTERNS:
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            line_num = content[:match.start()].count("\n") + 1
                            deps.append(DependencyRecord(
                                account_id="",
                                account_name="",
                                dependency_type="script",
                                consumer_name=file_path.name,
                                consumer_host="local",
                                consumer_path=str(file_path),
                                confidence=0.60,
                                evidence={"file": str(file_path),
                                          "line": line_num,
                                          "pattern": pattern,
                                          "snippet": match.group()[:100]},
                                remediation=f"Rewrite CyberArk integration in "
                                            f"{file_path.name} for target PAM system.",
                            ).to_dict())
                            break  # One CyberArk pattern match per file

                except Exception as e:
                    logger.debug(f"Error scanning {file_path}: {e}")

        self.logger.log("scan_scripts_complete", {"deps_found": len(deps)})
        return deps

    # ── Scanner: Config Files ───────────────────────────────────

    def _scan_config_files(
        self, config_paths: List[str],
        name_lookup: Dict[str, dict], username_lookup: Dict[str, dict],
    ) -> List[dict]:
        """Scan configuration files for credential references."""
        self.logger.log("scan_configs_start", {"paths": len(config_paths)})
        deps = []

        for scan_dir in config_paths:
            scan_path = Path(scan_dir)
            if not scan_path.exists():
                logger.warning(f"Config scan path not found: {scan_dir}")
                continue

            for file_path in self._walk_files(scan_path, CONFIG_EXTENSIONS, CONFIG_FILENAMES):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    content_lower = content.lower()

                    # Check for account name references in config values
                    for acct_key, acct in {**name_lookup, **username_lookup}.items():
                        if len(acct_key) < 4:
                            continue
                        if acct_key in content_lower:
                            # Find the matching line
                            lines = content.split("\n")
                            for line_num, line in enumerate(lines, 1):
                                if acct_key in line.lower():
                                    deps.append(DependencyRecord(
                                        account_id=acct.get("id", ""),
                                        account_name=acct.get("name", ""),
                                        dependency_type="config",
                                        consumer_name=file_path.name,
                                        consumer_host="local",
                                        consumer_path=str(file_path),
                                        confidence=0.70,
                                        evidence={"file": str(file_path),
                                                  "line": line_num,
                                                  "snippet": line.strip()[:200]},
                                        remediation=f"Update credential reference in "
                                                    f"config {file_path.name}:{line_num}",
                                    ).to_dict())
                                    break

                    # Check for CyberArk-specific config patterns
                    for pattern in CREDENTIAL_PATTERNS:
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            line_num = content[:match.start()].count("\n") + 1
                            deps.append(DependencyRecord(
                                account_id="",
                                account_name="",
                                dependency_type="config",
                                consumer_name=file_path.name,
                                consumer_host="local",
                                consumer_path=str(file_path),
                                confidence=0.70,
                                evidence={"file": str(file_path),
                                          "line": line_num,
                                          "pattern": pattern},
                                remediation=f"Update CyberArk config in "
                                            f"{file_path.name} for target PAM system.",
                            ).to_dict())
                            break

                except Exception as e:
                    logger.debug(f"Error scanning config {file_path}: {e}")

        self.logger.log("scan_configs_complete", {"deps_found": len(deps)})
        return deps

    # ── Helpers ──────────────────────────────────────────────────

    def _run_winrm(
        self, host: str, command: str, port: int, transport: str,
    ) -> Optional[str]:
        """Execute PowerShell command on remote host via WinRM.

        Uses pywinrm if available, falls back to PowerShell remoting subprocess.
        """
        # Try pywinrm first
        try:
            import winrm
            protocol = "https" if port == 5986 else "http"
            url = f"{protocol}://{host}:{port}/wsman"

            session = winrm.Session(
                url,
                auth=(
                    os.environ.get("WINRM_USERNAME", ""),
                    os.environ.get("WINRM_PASSWORD", ""),
                ),
                transport=transport,
                server_cert_validation="ignore",
            )
            result = session.run_ps(command)

            if result.status_code == 0:
                return result.std_out.decode("utf-8", errors="ignore")
            else:
                stderr = result.std_err.decode("utf-8", errors="ignore")
                logger.warning(f"WinRM command failed on {host}: {stderr[:200]}")
                return None

        except ImportError:
            pass

        # Fallback: subprocess with PowerShell remoting
        try:
            ps_cmd = (
                f"Invoke-Command -ComputerName {host} "
                f"-ScriptBlock {{ {command} }} | ConvertTo-Json -Compress"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"PowerShell remoting failed for {host}: {e}")

        return None

    def _match_account(
        self, identity: str, account_lookup: Dict[str, dict],
    ) -> Optional[dict]:
        """Match an identity string against known accounts.

        Handles domain\\username, username@domain, and bare username formats.
        """
        identity = identity.strip().lower()
        if not identity:
            return None

        # Direct match
        if identity in account_lookup:
            return account_lookup[identity]

        # Strip domain prefix (DOMAIN\\username → username)
        if "\\" in identity:
            bare = identity.split("\\", 1)[1]
            if bare in account_lookup:
                return account_lookup[bare]

        # Strip UPN suffix (user@domain.com → user)
        if "@" in identity:
            bare = identity.split("@", 1)[0]
            if bare in account_lookup:
                return account_lookup[bare]

        return None

    def _walk_files(
        self, root: Path, extensions: Set[str], filenames: Optional[Set[str]] = None,
        max_files: int = 10000,
    ) -> List[Path]:
        """Walk directory tree yielding files matching extensions or exact names."""
        files = []
        skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv",
                     "bin", "obj", ".vs", ".idea", "packages"}

        try:
            for item in root.rglob("*"):
                if len(files) >= max_files:
                    break
                if item.is_file():
                    if any(skip in item.parts for skip in skip_dirs):
                        continue
                    if item.suffix.lower() in extensions:
                        files.append(item)
                    elif filenames and item.name.lower() in filenames:
                        files.append(item)
        except PermissionError:
            pass

        return files

    def _merge_deps(
        self, all_deps: Dict[str, List[dict]], new_deps: List[dict],
    ) -> None:
        """Merge new dependency records into the main map, keyed by account_id."""
        for dep in new_deps:
            acct_id = dep.get("account_id", "")
            if acct_id:
                all_deps.setdefault(acct_id, []).append(dep)
            else:
                # Unmatched dependencies (CyberArk pattern matches without account link)
                all_deps.setdefault("_unmatched", []).append(dep)
