"""Agent 06 — Integration Repointing (CyberArk → Secret Server).

Scans codebases for CyberArk CCP/AAM/SDK patterns and generates
Secret Server REST API replacement code. The target is Secret Server's
OAuth2 + /api/v1/secrets endpoint (fundamentally different from CyberArk's
CCP model).

CyberArk CCP: GET /AIMWebService/api/Accounts?AppID=X&Safe=Y&Object=Z
Secret Server: GET /api/v1/secrets/{id}/fields/password (Bearer token)

This is a FULL re-architecture — not a URL swap.

Phases:
    P5: Scan and generate replacement code
    P6: Validate repointing during parallel running
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from core.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)

# Patterns to detect CyberArk CCP/AAM/SDK usage
CYBERARK_PATTERNS = {
    "CCP_REST_ENDPOINT": [
        r"AIMWebService/api/Accounts",
        r"/AIMWebService",
        r"GetPassword.*AppID",
    ],
    "CCP_APPID": [
        r"AppID\s*=\s*['\"]",
        r"appid\s*[=:]\s*['\"]",
    ],
    "CCP_SAFE_REFERENCE": [
        r"Safe\s*=\s*['\"]",
        r"safe\s*[=:]\s*['\"]",
    ],
    "CCP_OBJECT_REFERENCE": [
        r"Object\s*=\s*['\"]",
        r"Folder\s*=\s*['\"]",
    ],
    "DOTNET_SDK": [
        r"CyberArk\.AIM",
        r"PasswordSDK",
        r"Pacli",
    ],
    "JAVA_SDK": [
        r"com\.cyberark\.aim",
        r"PASJava",
    ],
    "POWERSHELL_MODULE": [
        r"psPAS",
        r"Get-PASAccount",
        r"New-PASSession",
        r"Get-PASPassword",
    ],
    "PYTHON_CCP": [
        r"requests\.get.*AIMWebService",
        r"cyberark.*password",
    ],
    "CONFIG_REFERENCE": [
        r"pvwa\.\w+\.com",
        r"cyberark\.\w+\.com",
        r"aim\.\w+\.com",
        r"CentralCredentialProvider",
    ],
}

# File extensions to scan
SCAN_EXTENSIONS = {
    ".py", ".ps1", ".psm1", ".cs", ".java", ".js", ".ts",
    ".xml", ".json", ".yaml", ".yml", ".config", ".ini",
    ".sh", ".bash", ".bat", ".cmd",
}

# Secret Server replacement code templates
SS_REPLACEMENT_TEMPLATES = {
    "python": '''# Secret Server — Python (replaces CyberArk CCP)
import requests, os

SS_URL = os.environ["SECRET_SERVER_URL"]

def get_token():
    resp = requests.post(f"{{SS_URL}}/oauth2/token", data={{
        "grant_type": "client_credentials",
        "client_id": os.environ["SS_CLIENT_ID"],
        "client_secret": os.environ["SS_CLIENT_SECRET"],
    }})
    return resp.json()["access_token"]

def get_password(secret_id):
    headers = {{"Authorization": f"Bearer {{get_token()}}"}}
    resp = requests.get(f"{{SS_URL}}/api/v1/secrets/{{secret_id}}/fields/password",
                        headers=headers)
    return resp.json()["value"]
''',
    "powershell": '''# Secret Server — PowerShell (replaces psPAS / CyberArk CCP)
# Requires: Install-Module -Name Thycotic.SecretServer
Import-Module Thycotic.SecretServer

$session = New-TssSession -SecretServer $env:SECRET_SERVER_URL `
    -AccessToken (Get-TssAccessToken -SecretServer $env:SECRET_SERVER_URL `
        -ClientId $env:SS_CLIENT_ID -ClientSecret $env:SS_CLIENT_SECRET)

$secret = Get-TssSecret -TssSession $session -Id $SecretId
$password = Get-TssSecretField -TssSession $session -Id $SecretId -Slug password
''',
    "csharp": '''// Secret Server — C# (replaces CyberArk.AIM.NetPasswordSDK)
// NuGet: Thycotic.SecretServer.SDK
using var client = new HttpClient();
var tokenResp = await client.PostAsync($"{ssUrl}/oauth2/token",
    new FormUrlEncodedContent(new Dictionary<string, string> {
        {"grant_type", "client_credentials"},
        {"client_id", clientId},
        {"client_secret", clientSecret}
    }));
var token = JsonSerializer.Deserialize<TokenResponse>(
    await tokenResp.Content.ReadAsStringAsync());
client.DefaultRequestHeaders.Authorization =
    new AuthenticationHeaderValue("Bearer", token.AccessToken);
var password = await client.GetStringAsync(
    $"{ssUrl}/api/v1/secrets/{secretId}/fields/password");
''',
    "java": '''// Secret Server — Java (replaces com.cyberark.aim)
HttpClient client = HttpClient.newHttpClient();
HttpRequest tokenReq = HttpRequest.newBuilder()
    .uri(URI.create(ssUrl + "/oauth2/token"))
    .POST(HttpRequest.BodyPublishers.ofString(
        "grant_type=client_credentials&client_id=" + clientId +
        "&client_secret=" + clientSecret))
    .header("Content-Type", "application/x-www-form-urlencoded")
    .build();
HttpResponse<String> tokenResp = client.send(tokenReq,
    HttpResponse.BodyHandlers.ofString());
String token = new JSONObject(tokenResp.body()).getString("access_token");

HttpRequest secretReq = HttpRequest.newBuilder()
    .uri(URI.create(ssUrl + "/api/v1/secrets/" + secretId + "/fields/password"))
    .header("Authorization", "Bearer " + token)
    .build();
''',
}


class IntegrationRepointingAgent(AgentBase):
    """Scans for CyberArk integrations and generates Secret Server replacements."""

    AGENT_ID = "agent_06_integration"
    AGENT_NAME = "Integration Repointing"

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        agent_cfg = self.config.get("agent_06_integration", {})
        scan_dirs = agent_cfg.get("scan_directories", [])

        if not scan_dirs:
            return self._result("success", data={
                "scan_directories": 0,
                "note": "No scan directories configured — will use discovery data only",
            })

        missing = [d for d in scan_dirs if not os.path.isdir(d)]
        if missing:
            return self._result("failed", errors=[f"Directories not found: {missing}"])

        self.logger.log("preflight_passed", {"directories": len(scan_dirs)})
        return self._result("success", data={"scan_directories": len(scan_dirs)})

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase not in ("P5", "P6"):
            return self._result("failed", phase=phase,
                                errors=[f"Agent 06 runs in P5/P6, not {phase}"])

        self.logger.log("integration_scan_start", {"phase": phase})
        agent_cfg = self.config.get("agent_06_integration", {})
        scan_dirs = agent_cfg.get("scan_directories", [])

        # Scan directories for CyberArk patterns
        all_findings = []
        for scan_dir in scan_dirs:
            findings = self._scan_directory(scan_dir)
            all_findings.extend(findings)

        # Also use discovery data for application inventory
        discovery = self.state.get_agent_result("agent_01_discovery", "P1") or {}
        integrations = discovery.get("integrations", [])
        applications = discovery.get("applications", {})

        # Generate replacement code
        languages = agent_cfg.get("supported_languages", ["python", "powershell", "csharp", "java"])
        replacements = {lang: SS_REPLACEMENT_TEMPLATES.get(lang, "") for lang in languages}

        # Build CCP change registry
        change_registry = []
        for finding in all_findings:
            change_registry.append({
                "file": finding["file"],
                "pattern_type": finding["type"],
                "line": finding.get("line", 0),
                "original": finding.get("match", ""),
                "action": "Replace with Secret Server REST API call",
                "template": finding.get("language", "python"),
            })

        for app in applications.get("app_ids", []):
            change_registry.append({
                "app_id": app,
                "source": "CyberArk Applications API",
                "action": "Map AppID to Secret Server secret ID, update auth to OAuth2",
            })

        report = {
            "scan_findings": all_findings,
            "integration_count": len(integrations),
            "application_count": len(applications.get("app_ids", [])),
            "change_registry": change_registry,
            "replacement_templates": replacements,
            "total_changes_required": len(change_registry),
        }

        self.logger.log("integration_scan_complete", {
            "findings": len(all_findings),
            "changes_required": len(change_registry),
        })

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.complete_step(f"{phase}:integration")

        return self._result(
            "success", phase=phase, data=report,
            metrics={
                "files_scanned": len(set(f["file"] for f in all_findings)) if all_findings else 0,
                "findings": len(all_findings),
                "changes_required": len(change_registry),
            },
            next_action="Run Agent 07 (Compliance) for compliance check",
        )

    def _scan_directory(self, scan_dir: str) -> List[dict]:
        """Walk directory tree and scan files for CyberArk patterns."""
        findings = []
        scan_path = Path(scan_dir)

        for filepath in scan_path.rglob("*"):
            if not filepath.is_file():
                continue
            if filepath.suffix.lower() not in SCAN_EXTENSIONS:
                continue

            try:
                content = filepath.read_text(errors="ignore")
            except Exception:
                continue

            for pattern_type, patterns in CYBERARK_PATTERNS.items():
                for pattern in patterns:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        # Find line number
                        line_num = content[:match.start()].count("\n") + 1
                        findings.append({
                            "file": str(filepath),
                            "type": pattern_type,
                            "pattern": pattern,
                            "match": match.group()[:100],
                            "line": line_num,
                            "language": self._detect_language(filepath.suffix),
                        })

        return findings

    def _detect_language(self, suffix: str) -> str:
        lang_map = {
            ".py": "python",
            ".ps1": "powershell", ".psm1": "powershell",
            ".cs": "csharp",
            ".java": "java",
            ".js": "javascript", ".ts": "typescript",
        }
        return lang_map.get(suffix.lower(), "config")
