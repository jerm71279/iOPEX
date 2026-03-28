#!/usr/bin/env python3
"""
CyberArk CCP/AAM Code Scanner

Scans codebases for CyberArk API integration patterns to identify
applications requiring updates during PAM migration to Secret Server.

Usage:
    python ccp_code_scanner.py /path/to/codebase --output results.json
    python ccp_code_scanner.py /path/to/codebase --format csv --output results.csv
"""

import argparse
import json
import os
import re
import csv
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

# ============================================
# PATTERN DEFINITIONS
# ============================================

CYBERARK_PATTERNS = {
    # REST API Patterns
    "CCP_REST_ENDPOINT": {
        "patterns": [
            r"AIMWebService",
            r"/api/Accounts",
            r"PasswordVault/API",
            r"CyberArk.*WebService",
        ],
        "risk": "HIGH",
        "description": "CyberArk CCP REST API endpoint",
        "migration_action": "Update to Secret Server REST API: GET /api/v1/secrets/{id}/fields/password",
        "secret_server_equivalent": "https://{server}/api/v1/secrets/{id}/fields/{fieldSlug}"
    },
    
    "CCP_APPID": {
        "patterns": [
            r"AppID\s*[=:]\s*[\"'][\w\-]+[\"']",
            r"applicationId\s*[=:]\s*[\"'][\w\-]+[\"']",
            r"app[_-]?id\s*[=:]\s*[\"'][\w\-]+[\"']",
        ],
        "risk": "HIGH",
        "description": "CyberArk Application ID parameter",
        "migration_action": "Replace with Secret Server OAuth2 client credentials",
        "secret_server_equivalent": "OAuth2 token with client_id/client_secret"
    },
    
    "CCP_SAFE_REFERENCE": {
        "patterns": [
            r"Safe\s*[=:]\s*[\"'][\w\-]+[\"']",
            r"safeName\s*[=:]\s*[\"'][\w\-]+[\"']",
        ],
        "risk": "MEDIUM",
        "description": "CyberArk Safe reference",
        "migration_action": "Map to Secret Server Folder ID using migration mapping",
        "secret_server_equivalent": "folderId parameter or folder path"
    },
    
    "CCP_OBJECT_REFERENCE": {
        "patterns": [
            r"Object\s*[=:]\s*[\"'][\w\-]+[\"']",
            r"objectName\s*[=:]\s*[\"'][\w\-]+[\"']",
            r"accountName\s*[=:]\s*[\"'][\w\-]+[\"']",
        ],
        "risk": "MEDIUM",
        "description": "CyberArk Object/Account reference",
        "migration_action": "Map to Secret Server Secret ID using migration mapping",
        "secret_server_equivalent": "secretId parameter"
    },
    
    # .NET SDK Patterns
    "DOTNET_CYBERARK_SDK": {
        "patterns": [
            r"using\s+CyberArk",
            r"CyberArk\.AIM",
            r"CyberArk\.PAS",
            r"PasswordSDK",
            r"PSDKPassword",
        ],
        "risk": "HIGH",
        "description": "CyberArk .NET SDK import/usage",
        "migration_action": "Replace with Thycotic.SecretServer NuGet package",
        "secret_server_equivalent": "using Thycotic.SecretServer.SDK"
    },
    
    "DOTNET_PASSWORD_REQUEST": {
        "patterns": [
            r"PasswordRequest",
            r"new\s+PSDKPasswordRequest",
            r"GetPassword\s*\(",
            r"\.Password\s*;",
        ],
        "risk": "HIGH",
        "description": "CyberArk SDK password retrieval call",
        "migration_action": "Replace with Secret Server SDK GetSecret() call",
        "secret_server_equivalent": "client.GetSecret(secretId).Items[\"password\"]"
    },
    
    # Java SDK Patterns
    "JAVA_CYBERARK_SDK": {
        "patterns": [
            r"import\s+com\.cyberark",
            r"JavaPasswordSDK",
            r"PSDKPasswordRequest",
            r"com\.cyberark\.aim",
        ],
        "risk": "HIGH",
        "description": "CyberArk Java SDK import/usage",
        "migration_action": "Replace with Secret Server REST API client",
        "secret_server_equivalent": "HTTP client calling /api/v1/secrets endpoint"
    },
    
    # Python Patterns
    "PYTHON_CCP_CALL": {
        "patterns": [
            r"requests\.(get|post).*AIMWebService",
            r"requests\.(get|post).*PasswordVault",
            r"urllib.*AIMWebService",
            r"cyberark.*password",
        ],
        "risk": "HIGH",
        "description": "Python CyberArk API call",
        "migration_action": "Replace with Secret Server REST API call",
        "secret_server_equivalent": "requests.get(f'{ss_url}/api/v1/secrets/{id}/fields/password', headers=auth)"
    },
    
    # PowerShell Patterns
    "POWERSHELL_PSPAS": {
        "patterns": [
            r"Import-Module\s+psPAS",
            r"Get-PASAccount",
            r"Get-PASAccountPassword",
            r"New-PASSession",
        ],
        "risk": "HIGH",
        "description": "psPAS PowerShell module usage",
        "migration_action": "Replace with Thycotic.SecretServer PowerShell module",
        "secret_server_equivalent": "Get-TssSecret -TssSession $session -Id $secretId"
    },
    
    # Configuration Patterns
    "CONFIG_CYBERARK_URL": {
        "patterns": [
            r"cyberark[_\-]?url",
            r"pvwa[_\-]?url",
            r"aim[_\-]?url",
            r"vault[_\-]?address",
        ],
        "risk": "MEDIUM",
        "description": "CyberArk URL configuration",
        "migration_action": "Update to Secret Server URL in configuration",
        "secret_server_equivalent": "secret_server_url or ss_base_url"
    },
    
    # Connection String Patterns
    "CONNECTION_STRING_CCP": {
        "patterns": [
            r"Provider\s*=\s*CyberArk",
            r"CyberArkProvider",
            r"AIM\s+Provider",
        ],
        "risk": "HIGH",
        "description": "CyberArk credential provider in connection string",
        "migration_action": "Update connection string to use Secret Server SDK",
        "secret_server_equivalent": "Retrieve password via SDK, inject into connection string"
    },
}

# File extensions to scan
SCAN_EXTENSIONS = {
    ".py": "Python",
    ".ps1": "PowerShell",
    ".psm1": "PowerShell Module",
    ".cs": "C#",
    ".java": "Java",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".sh": "Bash",
    ".bash": "Bash",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".json": "JSON",
    ".xml": "XML",
    ".config": "Config",
    ".conf": "Config",
    ".ini": "INI",
    ".env": "Environment",
    ".properties": "Properties",
}

# Directories to skip
SKIP_DIRS = {
    "node_modules",
    ".git",
    ".svn",
    "__pycache__",
    "venv",
    ".venv",
    "bin",
    "obj",
    "packages",
    ".idea",
    ".vs",
}


@dataclass
class ScanMatch:
    """Represents a single pattern match in the codebase."""
    file_path: str
    line_number: int
    line_content: str
    pattern_name: str
    pattern_type: str
    risk_level: str
    description: str
    migration_action: str
    secret_server_equivalent: str
    language: str


@dataclass
class ScanSummary:
    """Summary of scan results."""
    total_files_scanned: int
    total_matches: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    files_with_matches: int
    languages_detected: List[str]
    scan_timestamp: str
    scan_path: str


def scan_file(file_path: Path) -> List[ScanMatch]:
    """Scan a single file for CyberArk patterns."""
    matches = []
    extension = file_path.suffix.lower()
    language = SCAN_EXTENSIONS.get(extension, "Unknown")
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return matches
    
    for line_num, line in enumerate(lines, 1):
        for pattern_name, pattern_info in CYBERARK_PATTERNS.items():
            for pattern in pattern_info["patterns"]:
                if re.search(pattern, line, re.IGNORECASE):
                    matches.append(ScanMatch(
                        file_path=str(file_path),
                        line_number=line_num,
                        line_content=line.strip()[:200],  # Truncate long lines
                        pattern_name=pattern_name,
                        pattern_type=pattern,
                        risk_level=pattern_info["risk"],
                        description=pattern_info["description"],
                        migration_action=pattern_info["migration_action"],
                        secret_server_equivalent=pattern_info["secret_server_equivalent"],
                        language=language
                    ))
                    break  # Only match once per pattern group per line
    
    return matches


def scan_directory(root_path: Path) -> tuple[List[ScanMatch], int]:
    """Recursively scan directory for CyberArk patterns."""
    all_matches = []
    files_scanned = 0
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        
        for filename in filenames:
            file_path = Path(dirpath) / filename
            
            # Only scan files with known extensions
            if file_path.suffix.lower() in SCAN_EXTENSIONS:
                files_scanned += 1
                matches = scan_file(file_path)
                all_matches.extend(matches)
    
    return all_matches, files_scanned


def generate_summary(matches: List[ScanMatch], files_scanned: int, scan_path: str) -> ScanSummary:
    """Generate summary statistics from scan results."""
    files_with_matches = len(set(m.file_path for m in matches))
    languages = list(set(m.language for m in matches))
    
    return ScanSummary(
        total_files_scanned=files_scanned,
        total_matches=len(matches),
        high_risk_count=sum(1 for m in matches if m.risk_level == "HIGH"),
        medium_risk_count=sum(1 for m in matches if m.risk_level == "MEDIUM"),
        low_risk_count=sum(1 for m in matches if m.risk_level == "LOW"),
        files_with_matches=files_with_matches,
        languages_detected=languages,
        scan_timestamp=datetime.now().isoformat(),
        scan_path=scan_path
    )


def output_json(matches: List[ScanMatch], summary: ScanSummary, output_path: str):
    """Output results as JSON."""
    result = {
        "summary": asdict(summary),
        "matches": [asdict(m) for m in matches]
    }
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"JSON results written to: {output_path}")


def output_csv(matches: List[ScanMatch], output_path: str):
    """Output results as CSV."""
    if not matches:
        print("No matches to write.")
        return
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=asdict(matches[0]).keys())
        writer.writeheader()
        for match in matches:
            writer.writerow(asdict(match))
    
    print(f"CSV results written to: {output_path}")


def print_summary(summary: ScanSummary, matches: List[ScanMatch]):
    """Print summary to console."""
    print("\n" + "=" * 60)
    print("CYBERARK CCP/AAM CODE SCAN RESULTS")
    print("=" * 60)
    print(f"Scan Path:           {summary.scan_path}")
    print(f"Scan Timestamp:      {summary.scan_timestamp}")
    print(f"Files Scanned:       {summary.total_files_scanned}")
    print(f"Files with Matches:  {summary.files_with_matches}")
    print(f"Total Matches:       {summary.total_matches}")
    print("-" * 60)
    print(f"HIGH Risk:           {summary.high_risk_count}")
    print(f"MEDIUM Risk:         {summary.medium_risk_count}")
    print(f"LOW Risk:            {summary.low_risk_count}")
    print("-" * 60)
    print(f"Languages Detected:  {', '.join(summary.languages_detected)}")
    print("=" * 60)
    
    if matches:
        print("\nTOP 10 HIGH-RISK FINDINGS:")
        print("-" * 60)
        high_risk = [m for m in matches if m.risk_level == "HIGH"][:10]
        for m in high_risk:
            print(f"\n  File: {m.file_path}:{m.line_number}")
            print(f"  Type: {m.description}")
            print(f"  Action: {m.migration_action}")


def main():
    parser = argparse.ArgumentParser(
        description="Scan codebase for CyberArk CCP/AAM dependencies"
    )
    parser.add_argument(
        "path",
        help="Path to directory to scan"
    )
    parser.add_argument(
        "--output", "-o",
        default="ccp_scan_results.json",
        help="Output file path (default: ccp_scan_results.json)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress console output"
    )
    
    args = parser.parse_args()
    
    scan_path = Path(args.path)
    if not scan_path.exists():
        print(f"Error: Path does not exist: {scan_path}")
        return 1
    
    if not args.quiet:
        print(f"Scanning {scan_path} for CyberArk CCP/AAM patterns...")
    
    matches, files_scanned = scan_directory(scan_path)
    summary = generate_summary(matches, files_scanned, str(scan_path))
    
    if not args.quiet:
        print_summary(summary, matches)
    
    if args.format == "json":
        output_json(matches, summary, args.output)
    else:
        output_csv(matches, args.output)
    
    return 0 if summary.high_risk_count == 0 else 1


if __name__ == "__main__":
    exit(main())
