#!/usr/bin/env python3
"""
CyberArk Integration Dependency Mapper

Catalogs all CyberArk integrations that need to be re-pointed during migration.
Integrations are the #2 cause of migration failures - every system that talks
to CyberArk must be updated.

Based on Enhanced ETL Migration Plan v2.0 - Section 1.3

Usage:
    # Generate integration inventory template
    python integration_mapper.py --generate-template --output integrations.csv

    # Analyze codebase for integration patterns
    python integration_mapper.py --scan /path/to/codebase --output integrations.csv

    # Merge manual inventory with scan results
    python integration_mapper.py --manual manual_integrations.csv --scan /path/to/code --output merged.csv
"""

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
import re


# ============================================
# INTEGRATION TYPES
# ============================================

INTEGRATION_TYPES = {
    "SIEM": {
        "description": "Security Information and Event Management (syslog, CEF)",
        "discovery_method": "Check CyberArk syslog configuration in PVWA",
        "cutover_complexity": "LOW",
        "cutover_action": "Reconfigure Secret Server syslog to same target",
        "patterns": [
            r"syslog",
            r"splunk",
            r"qradar",
            r"arcsight",
            r"sentinel",
            r"elastic",
            r"logstash",
        ],
    },
    "TICKETING": {
        "description": "IT Service Management / Ticketing integration",
        "discovery_method": "Check ITSM integration settings in CyberArk",
        "cutover_complexity": "MEDIUM",
        "cutover_action": "Update ServiceNow/Jira integration to Secret Server API",
        "patterns": [
            r"servicenow",
            r"snow",
            r"jira",
            r"remedy",
            r"cherwell",
            r"freshservice",
            r"itsm",
        ],
    },
    "CCP_AAM": {
        "description": "Application credential retrieval via CCP/AAM",
        "discovery_method": "Audit CCP/AAM usage logs, scan code for API calls",
        "cutover_complexity": "HIGH",
        "cutover_action": "Update application code to use Secret Server SDK/API",
        "patterns": [
            r"AIMWebService",
            r"CCP",
            r"AAM",
            r"CyberArk.*API",
            r"PasswordVault",
            r"GetPassword",
        ],
    },
    "PSM": {
        "description": "Privileged Session Manager connection components",
        "discovery_method": "List PSM configurations in CyberArk",
        "cutover_complexity": "MEDIUM",
        "cutover_action": "Recreate session launchers in Secret Server",
        "patterns": [
            r"PSM",
            r"PrivilegedSession",
            r"ConnectionComponent",
            r"RDP",
            r"SSH",
            r"session.*record",
        ],
    },
    "DIRECTORY": {
        "description": "AD/LDAP directory synchronization",
        "discovery_method": "Check directory integration settings",
        "cutover_complexity": "LOW",
        "cutover_action": "Configure Secret Server AD sync with same domain",
        "patterns": [
            r"LDAP",
            r"Active.*Directory",
            r"AD.*sync",
            r"directory.*service",
        ],
    },
    "MFA": {
        "description": "Multi-factor authentication integration",
        "discovery_method": "Check authentication settings (Duo, RSA, etc.)",
        "cutover_complexity": "MEDIUM",
        "cutover_action": "Configure MFA provider in Secret Server",
        "patterns": [
            r"Duo",
            r"RSA",
            r"RADIUS",
            r"SAML",
            r"TOTP",
            r"MFA",
            r"two.*factor",
            r"2FA",
        ],
    },
    "SOAR": {
        "description": "Security Orchestration Automation and Response",
        "discovery_method": "Audit security automation playbooks",
        "cutover_complexity": "HIGH",
        "cutover_action": "Update playbooks to use Secret Server API",
        "patterns": [
            r"SOAR",
            r"Phantom",
            r"Demisto",
            r"XSOAR",
            r"playbook",
            r"orchestration",
            r"Cortex",
        ],
    },
    "CMDB": {
        "description": "Configuration Management Database integration",
        "discovery_method": "Check CMDB sync settings",
        "cutover_complexity": "MEDIUM",
        "cutover_action": "Update CMDB integration to Secret Server",
        "patterns": [
            r"CMDB",
            r"configuration.*management",
            r"asset.*management",
        ],
    },
    "CICD": {
        "description": "CI/CD pipeline credential integration",
        "discovery_method": "Scan pipeline configs (Jenkins, GitLab, etc.)",
        "cutover_complexity": "HIGH",
        "cutover_action": "Update pipeline secret retrieval to Secret Server",
        "patterns": [
            r"Jenkins",
            r"GitLab",
            r"GitHub.*Action",
            r"Azure.*DevOps",
            r"CircleCI",
            r"TeamCity",
            r"pipeline",
            r"CI.*CD",
        ],
    },
    "IAC": {
        "description": "Infrastructure as Code credential injection",
        "discovery_method": "Scan Terraform, Ansible, CloudFormation configs",
        "cutover_complexity": "HIGH",
        "cutover_action": "Update IaC provider to Secret Server",
        "patterns": [
            r"Terraform",
            r"Ansible",
            r"CloudFormation",
            r"Pulumi",
            r"Chef",
            r"Puppet",
        ],
    },
    "DATABASE": {
        "description": "Database credential provider integration",
        "discovery_method": "Check connection strings for CyberArk provider",
        "cutover_complexity": "HIGH",
        "cutover_action": "Update connection string credential retrieval",
        "patterns": [
            r"Oracle.*Provider",
            r"SQL.*Server.*Provider",
            r"connection.*string",
            r"JDBC",
            r"ODBC",
            r"ADO.*NET",
        ],
    },
    "CUSTOM": {
        "description": "Custom/other integration",
        "discovery_method": "Manual discovery required",
        "cutover_complexity": "VARIES",
        "cutover_action": "Depends on integration type",
        "patterns": [],
    },
}


@dataclass
class Integration:
    """Represents a CyberArk integration dependency."""
    integration_type: str
    name: str
    target: str = ""
    protocol: str = ""

    # Ownership
    owner_name: str = ""
    owner_email: str = ""
    owner_team: str = ""

    # Cutover planning
    cutover_complexity: str = ""
    cutover_action: str = ""
    cutover_order: int = 0
    maintenance_window_required: bool = False
    estimated_downtime: str = ""

    # Status
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, BLOCKED
    notes: str = ""
    discovered_from: str = ""  # Source of discovery (scan, manual, etc.)

    # Risk
    risk_level: str = "MEDIUM"
    business_impact: str = ""


@dataclass
class IntegrationSummary:
    """Summary of integration inventory."""
    total_integrations: int
    by_type: Dict[str, int]
    by_complexity: Dict[str, int]
    high_risk_count: int
    scan_timestamp: str


def scan_file_for_integrations(file_path: Path) -> List[Integration]:
    """Scan a single file for integration patterns."""
    integrations = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return integrations

    for int_type, info in INTEGRATION_TYPES.items():
        for pattern in info["patterns"]:
            if re.search(pattern, content, re.IGNORECASE):
                # Found a match - create integration record
                integration = Integration(
                    integration_type=int_type,
                    name=f"{int_type} in {file_path.name}",
                    target=str(file_path),
                    cutover_complexity=info["cutover_complexity"],
                    cutover_action=info["cutover_action"],
                    discovered_from=f"Code scan: {file_path}",
                    notes=f"Pattern matched: {pattern}",
                )

                # Set risk based on complexity
                complexity_risk = {"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH", "VARIES": "MEDIUM"}
                integration.risk_level = complexity_risk.get(info["cutover_complexity"], "MEDIUM")

                integrations.append(integration)
                break  # Only one match per type per file

    return integrations


def scan_directory(root_path: Path, extensions: set = None) -> List[Integration]:
    """Scan directory for integration patterns."""
    if extensions is None:
        extensions = {
            ".py", ".ps1", ".psm1", ".cs", ".java", ".js", ".ts",
            ".yml", ".yaml", ".json", ".xml", ".config", ".conf",
            ".tf", ".hcl",  # Terraform
            ".jenkinsfile", ".gitlab-ci.yml",  # CI/CD
        }

    skip_dirs = {
        "node_modules", ".git", ".svn", "__pycache__",
        "venv", ".venv", "bin", "obj", "packages",
    }

    all_integrations = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]

        for filename in filenames:
            file_path = Path(dirpath) / filename
            if file_path.suffix.lower() in extensions:
                integrations = scan_file_for_integrations(file_path)
                all_integrations.extend(integrations)

    # Deduplicate by type (keep first occurrence)
    seen_types = {}
    unique = []
    for i in all_integrations:
        key = (i.integration_type, i.target)
        if key not in seen_types:
            seen_types[key] = i
            unique.append(i)

    return unique


def generate_template() -> List[Integration]:
    """Generate template with all integration types for manual completion."""
    template = []

    for int_type, info in INTEGRATION_TYPES.items():
        integration = Integration(
            integration_type=int_type,
            name=f"[Enter {int_type} integration name]",
            target="[Enter target system/URL]",
            protocol="[Enter protocol]",
            owner_name="[Enter owner name]",
            owner_email="[Enter owner email]",
            owner_team="[Enter team name]",
            cutover_complexity=info["cutover_complexity"],
            cutover_action=info["cutover_action"],
            notes=f"Discovery: {info['discovery_method']}",
        )
        template.append(integration)

    return template


def load_csv(file_path: Path) -> List[Integration]:
    """Load integrations from CSV."""
    integrations = []

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            integration = Integration(
                integration_type=row.get("integration_type", "CUSTOM"),
                name=row.get("name", ""),
                target=row.get("target", ""),
                protocol=row.get("protocol", ""),
                owner_name=row.get("owner_name", ""),
                owner_email=row.get("owner_email", ""),
                owner_team=row.get("owner_team", ""),
                cutover_complexity=row.get("cutover_complexity", "MEDIUM"),
                cutover_action=row.get("cutover_action", ""),
                cutover_order=int(row.get("cutover_order", 0) or 0),
                maintenance_window_required=row.get("maintenance_window_required", "").lower() == "true",
                estimated_downtime=row.get("estimated_downtime", ""),
                status=row.get("status", "PENDING"),
                notes=row.get("notes", ""),
                discovered_from=row.get("discovered_from", "Manual entry"),
                risk_level=row.get("risk_level", "MEDIUM"),
                business_impact=row.get("business_impact", ""),
            )
            integrations.append(integration)

    return integrations


def merge_integrations(manual: List[Integration], scanned: List[Integration]) -> List[Integration]:
    """Merge manual inventory with scan results."""
    # Index manual by type and name
    manual_index = {}
    for i in manual:
        key = (i.integration_type, i.name.lower())
        manual_index[key] = i

    # Add scanned that don't exist in manual
    merged = list(manual)

    for scanned_int in scanned:
        # Check if already in manual
        exists = False
        for m in manual:
            if (m.integration_type == scanned_int.integration_type and
                (scanned_int.target in m.target or scanned_int.target in m.notes)):
                exists = True
                break

        if not exists:
            scanned_int.notes = f"[AUTO-DISCOVERED] {scanned_int.notes}"
            merged.append(scanned_int)

    return merged


def generate_summary(integrations: List[Integration]) -> IntegrationSummary:
    """Generate summary statistics."""
    by_type = {}
    by_complexity = {}
    high_risk = 0

    for i in integrations:
        by_type[i.integration_type] = by_type.get(i.integration_type, 0) + 1
        by_complexity[i.cutover_complexity] = by_complexity.get(i.cutover_complexity, 0) + 1
        if i.risk_level == "HIGH" or i.cutover_complexity == "HIGH":
            high_risk += 1

    return IntegrationSummary(
        total_integrations=len(integrations),
        by_type=by_type,
        by_complexity=by_complexity,
        high_risk_count=high_risk,
        scan_timestamp=datetime.now().isoformat(),
    )


def output_csv(integrations: List[Integration], output_path: str):
    """Output integrations to CSV."""
    if not integrations:
        print("No integrations to write.")
        return

    rows = [asdict(i) for i in integrations]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Integration inventory written to: {output_path}")


def output_json(integrations: List[Integration], summary: IntegrationSummary, output_path: str):
    """Output integrations and summary to JSON."""
    result = {
        "summary": asdict(summary),
        "integrations": [asdict(i) for i in integrations],
    }

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"JSON results written to: {output_path}")


def print_summary(summary: IntegrationSummary, integrations: List[Integration]):
    """Print summary to console."""
    print("\n" + "=" * 60)
    print("CYBERARK INTEGRATION DEPENDENCY INVENTORY")
    print("=" * 60)
    print(f"Scan Timestamp:       {summary.scan_timestamp}")
    print(f"Total Integrations:   {summary.total_integrations}")
    print(f"High Risk/Complexity: {summary.high_risk_count}")
    print("-" * 60)
    print("By Type:")
    for int_type, count in sorted(summary.by_type.items()):
        desc = INTEGRATION_TYPES.get(int_type, {}).get("description", "")
        print(f"  {int_type}: {count} - {desc[:40]}")
    print("-" * 60)
    print("By Cutover Complexity:")
    for complexity, count in sorted(summary.by_complexity.items()):
        print(f"  {complexity}: {count}")
    print("=" * 60)

    # High complexity integrations
    high_complexity = [i for i in integrations if i.cutover_complexity == "HIGH"]
    if high_complexity:
        print("\nHIGH COMPLEXITY INTEGRATIONS (Require most attention):")
        print("-" * 60)
        for i in high_complexity[:10]:
            print(f"\n  Type: {i.integration_type}")
            print(f"  Name: {i.name}")
            print(f"  Target: {i.target}")
            print(f"  Action: {i.cutover_action}")
            if i.owner_name:
                print(f"  Owner: {i.owner_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Map CyberArk integration dependencies for migration planning"
    )
    parser.add_argument(
        "--generate-template",
        action="store_true",
        help="Generate empty template for manual completion"
    )
    parser.add_argument(
        "--scan", "-s",
        help="Directory to scan for integration patterns"
    )
    parser.add_argument(
        "--manual", "-m",
        help="Manual integration inventory CSV to merge with scan results"
    )
    parser.add_argument(
        "--output", "-o",
        default="integration_dependencies.csv",
        help="Output file path (default: integration_dependencies.csv)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress console output"
    )

    args = parser.parse_args()

    integrations = []

    # Generate template
    if args.generate_template:
        integrations = generate_template()
        if not args.quiet:
            print("Generated integration template with all types.")

    # Scan directory
    elif args.scan:
        scan_path = Path(args.scan)
        if not scan_path.exists():
            print(f"Error: Scan path not found: {scan_path}")
            return 1

        if not args.quiet:
            print(f"Scanning {scan_path} for integration patterns...")

        integrations = scan_directory(scan_path)

        # Merge with manual if provided
        if args.manual:
            manual_path = Path(args.manual)
            if manual_path.exists():
                manual = load_csv(manual_path)
                integrations = merge_integrations(manual, integrations)
                if not args.quiet:
                    print(f"Merged with manual inventory: {manual_path}")

    # Load manual only
    elif args.manual:
        manual_path = Path(args.manual)
        if not manual_path.exists():
            print(f"Error: Manual inventory not found: {manual_path}")
            return 1
        integrations = load_csv(manual_path)

    else:
        parser.error("Must specify --generate-template, --scan, or --manual")

    # Generate summary
    summary = generate_summary(integrations)

    if not args.quiet:
        print_summary(summary, integrations)

    # Output results
    if args.format == "json":
        json_path = args.output if args.output.endswith(".json") else args.output.replace(".csv", ".json")
        output_json(integrations, summary, json_path)
    else:
        output_csv(integrations, args.output)

    return 0


if __name__ == "__main__":
    exit(main())
