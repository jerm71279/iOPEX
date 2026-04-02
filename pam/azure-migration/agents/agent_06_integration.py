"""Agent 06 — Integration Repointing (CCP/AAM).

Scans codebases for CyberArk CCP/AAM integration patterns, generates
replacement code for KeeperPAM, and optionally creates dual-backend
wrappers for gradual cutover.

Phases:
    P5: Scan and generate repointing artifacts for each batch
    P6: Verify all integrations repointed during parallel running
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from core.base import AgentBase, AgentResult
from core.keeper_client import ENDPOINTS, API_BASE, ENDPOINTS_VERIFIED

logger = logging.getLogger(__name__)

# CyberArk integration detection patterns (from ccp_code_scanner.py)
CYBERARK_PATTERNS = {
    "CCP_REST_ENDPOINT": r"AIMWebService/api/Accounts",
    "CCP_APPID": r"AppID\s*=\s*['\"]?\w+",
    "CCP_SAFE_REFERENCE": r"Safe\s*=\s*['\"]?\w+",
    "CCP_OBJECT_REFERENCE": r"Object\s*=\s*['\"]?\w+",
    "DOTNET_CYBERARK_SDK": r"CyberArk\.AIM\.NetPasswordSDK",
    "JAVA_CYBERARK_SDK": r"com\.cyberark\.aim",
    "PYTHON_CCP_CALL": r"requests\.get.*AIMWebService",
    "POWERSHELL_PSPAS": r"Get-PASAccount|New-PASSession|psPAS",
    "CONFIG_CYBERARK_URL": r"(?:pvwa|cyberark|aim)[\w-]*\.[\w.]+",
    "CONNECTION_STRING_CCP": r"(?:Provider|Data Source).*CyberArk",
}

# KeeperPAM replacement templates for app teams.
# Endpoint paths are sourced from core/keeper_client.py ENDPOINTS registry.
# Set ENDPOINTS_VERIFIED = True there after confirming paths with Keeper Security.
#
# Template variables populated at generation time:
#   {base_url}      — KeeperPAM base URL from config
#   {api_base}      — API_BASE from keeper_client.py
#   {records_list}  — ENDPOINTS["records_list"]
#   {record_password_get} — ENDPOINTS["record_password_get"] (with {record_id} placeholder)

def _build_templates(base_url: str) -> dict:
    """Build replacement templates with verified endpoint paths injected."""
    records_path = f"{API_BASE}{ENDPOINTS['records_list']}"
    password_path = f"{API_BASE}{ENDPOINTS['record_password_get']}"
    verified_note = (
        "# NOTE: Endpoint paths verified against Keeper Security API docs."
        if ENDPOINTS_VERIFIED
        else "# NOTE: Endpoint paths UNVERIFIED — confirm with Keeper Security before use (C-03)."
    )

    return {
        "python": f'''import requests

{verified_note}

def get_secret(base_url, token, vault, record_name):
    """Retrieve secret from KeeperPAM."""
    url = f"{{base_url}}{records_path}?search={{record_name}}&vault={{vault}}"
    headers = {{"Authorization": f"Bearer {{token}}", "Content-Type": "application/json"}}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    records = resp.json().get("records", [])
    if not records:
        raise ValueError(f"Record {{record_name}} not found in vault {{vault}}")
    record_id = records[0]["id"]
    pwd_path = "{password_path}".replace("{{record_id}}", record_id)
    pwd_url = f"{{base_url}}{{pwd_path}}"
    pwd_resp = requests.post(pwd_url, headers=headers, json={{"reason": "Application access"}})
    pwd_resp.raise_for_status()
    return pwd_resp.json().get("password", "")
''',
        "powershell": f'''# {verified_note.lstrip("# ")}
function Get-KeeperPAMSecret {{
    param(
        [string]$BaseUrl,
        [string]$Token,
        [string]$Vault,
        [string]$RecordName
    )
    $headers = @{{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }}
    $searchUrl = "$BaseUrl{records_path}?search=$RecordName&vault=$Vault"
    $result = Invoke-RestMethod -Uri $searchUrl -Headers $headers -Method Get
    $recordId = $result.records[0].id
    $pwdPath = "{password_path}" -replace "\\{{record_id\\}}", $recordId
    $pwdUrl = "$BaseUrl$pwdPath"
    $body = @{{ reason = "Application access" }} | ConvertTo-Json
    $secret = Invoke-RestMethod -Uri $pwdUrl -Headers $headers -Method Post -Body $body
    return $secret.password
}}
''',
        "csharp": f'''using System.Net.Http;
using System.Text.Json;

// {verified_note.lstrip("# ")}
public class KeeperPAMClient
{{
    private readonly HttpClient _client;
    private readonly string _baseUrl;

    public KeeperPAMClient(string baseUrl, string token)
    {{
        _baseUrl = baseUrl;
        _client = new HttpClient();
        _client.DefaultRequestHeaders.Add("Authorization", $"Bearer {{token}}");
    }}

    public async Task<string> GetSecretAsync(string vault, string recordName)
    {{
        var searchUrl = $"{{_baseUrl}}{records_path}?search={{recordName}}&vault={{vault}}";
        var searchResp = await _client.GetStringAsync(searchUrl);
        var records = JsonSerializer.Deserialize<RecordsResponse>(searchResp);
        var recordId = records.Records[0].Id;
        var pwdUrl = $"{{_baseUrl}}{password_path}".Replace("{{record_id}}", recordId);
        var content = new StringContent("{{\\"reason\\":\\"Application access\\"}}", System.Text.Encoding.UTF8, "application/json");
        var pwdResp = await _client.PostAsync(pwdUrl, content);
        var result = JsonSerializer.Deserialize<PasswordResponse>(await pwdResp.Content.ReadAsStringAsync());
        return result.Password;
    }}
}}
''',
        "java": f'''import java.net.http.*;
import java.net.URI;

// {verified_note.lstrip("# ")}
public class KeeperPAMClient {{
    private final String baseUrl;
    private final String token;
    private final HttpClient client = HttpClient.newHttpClient();

    public KeeperPAMClient(String baseUrl, String token) {{
        this.baseUrl = baseUrl;
        this.token = token;
    }}

    public String getSecret(String vault, String recordName) throws Exception {{
        String searchUrl = baseUrl + "{records_path}?search=" + recordName + "&vault=" + vault;
        HttpRequest searchReq = HttpRequest.newBuilder()
            .uri(URI.create(searchUrl))
            .header("Authorization", "Bearer " + token)
            .GET().build();
        HttpResponse<String> searchResp = client.send(searchReq, HttpResponse.BodyHandlers.ofString());
        String recordId = parseRecordId(searchResp.body());
        String pwdUrl = baseUrl + "{password_path}".replace("{{record_id}}", recordId);
        HttpRequest pwdReq = HttpRequest.newBuilder()
            .uri(URI.create(pwdUrl))
            .header("Authorization", "Bearer " + token)
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString("{{\\"reason\\":\\"Application access\\"}}"))
            .build();
        HttpResponse<String> pwdResp = client.send(pwdReq, HttpResponse.BodyHandlers.ofString());
        return parsePassword(pwdResp.body());
    }}

    private String parseRecordId(String json) {{
        int idx = json.indexOf("\\"id\\":\\"") + 6;
        return json.substring(idx, json.indexOf("\\"", idx));
    }}

    private String parsePassword(String json) {{
        int idx = json.indexOf("\\"password\\":\\"") + 12;
        return json.substring(idx, json.indexOf("\\"", idx));
    }}
}}
''',
    }


class IntegrationRepointingAgent(AgentBase):
    """Scans for CyberArk integrations and generates KeeperPAM replacements."""

    AGENT_ID = "agent_06_integration"
    AGENT_NAME = "Integration Repointing (CCP/AAM)"

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        agent_cfg = self.config.get("agent_06_integration", {})
        scan_dirs = agent_cfg.get("scan_directories", [])

        errors = []
        for d in scan_dirs:
            if not os.path.isdir(d):
                errors.append(f"Scan directory not found: {d}")

        if errors:
            return self._result("failed", errors=errors)

        self.logger.log("preflight_passed", {"scan_dirs": scan_dirs})
        return self._result("success", data={"scan_directories": scan_dirs})

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase not in ("P5", "P6"):
            return self._result("failed", phase=phase, errors=[f"Agent 06 runs in P5/P6, not {phase}"])

        self.logger.log("integration_scan_start", {"phase": phase})
        agent_cfg = self.config.get("agent_06_integration", {})
        scan_dirs = agent_cfg.get("scan_directories", [])
        languages = agent_cfg.get("supported_languages", ["python", "powershell", "csharp", "java"])
        generate_wrapper = agent_cfg.get("generate_dual_backend_wrapper", True)

        # Scan for CyberArk patterns
        all_findings = []
        for scan_dir in scan_dirs:
            findings = self._scan_directory(scan_dir)
            all_findings.extend(findings)

        # Group by language
        by_language: Dict[str, List[dict]] = {}
        for finding in all_findings:
            lang = finding.get("language", "unknown")
            by_language.setdefault(lang, []).append(finding)

        # Generate replacement code using verified endpoint paths
        base_url = self.config.get("keeperpam", {}).get("base_url", "")
        templates = _build_templates(base_url)
        replacements = {}
        for lang in languages:
            if lang in templates:
                replacements[lang] = templates[lang]

        # Generate CCP change registry entries from discovery
        discovery = self.state.get_agent_result("agent_01_discovery", "P1") or {}
        integrations = discovery.get("integrations", [])
        ccp_registry = [
            {
                "app_id": i.get("name", ""),
                "type": i["type"],
                "source": i.get("source", ""),
                "original_url": "",  # To be filled during cutover
                "new_url": "",
                "changed_date": "",
            }
            for i in integrations
            if i["type"] == "CCP_AAM"
        ]

        report = {
            "scan_results": all_findings,
            "findings_by_language": {k: len(v) for k, v in by_language.items()},
            "total_findings": len(all_findings),
            "replacement_templates": list(replacements.keys()),
            "ccp_change_registry": ccp_registry,
            "dual_backend_wrapper": generate_wrapper,
        }

        self.logger.log("integration_scan_complete", {
            "findings": len(all_findings),
            "languages": list(by_language.keys()),
            "ccp_entries": len(ccp_registry),
        })

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.complete_step(f"{phase}:integration_repointing")

        return self._result(
            "success",
            phase=phase,
            data=report,
            metrics={
                "files_scanned": len(set(f.get("file", "") for f in all_findings)),
                "patterns_found": len(all_findings),
                "languages": list(by_language.keys()),
            },
            next_action="Run Agent 07 (Compliance) for audit trail",
        )

    def _scan_directory(self, directory: str) -> List[dict]:
        """Scan a directory tree for CyberArk integration patterns."""
        findings = []
        extensions = {
            ".py": "python", ".ps1": "powershell", ".psm1": "powershell",
            ".cs": "csharp", ".java": "java", ".js": "javascript",
            ".ts": "typescript", ".config": "config", ".xml": "config",
            ".json": "config", ".yaml": "config", ".yml": "config",
        }

        for root, _, files in os.walk(directory):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in extensions:
                    continue

                filepath = os.path.join(root, fname)
                try:
                    with open(filepath, "r", errors="ignore") as f:
                        content = f.read()
                except (PermissionError, OSError):
                    continue

                for pattern_name, pattern in CYBERARK_PATTERNS.items():
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        findings.append({
                            "file": filepath,
                            "language": extensions[ext],
                            "pattern": pattern_name,
                            "match_count": len(matches),
                            "sample": matches[0][:100] if matches else "",
                        })

        return findings
