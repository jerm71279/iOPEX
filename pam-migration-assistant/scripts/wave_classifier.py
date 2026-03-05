#!/usr/bin/env python3
"""
Account Wave Classifier

Classifies accounts into migration waves based on risk level, account type,
and NHI status. Supports the phased migration approach from the ETL plan.

Based on Enhanced ETL Migration Plan v2.0 - Section 3.1

Wave Definitions:
    Wave 1: Test/Dev accounts (LOW risk) - First, validates process
    Wave 2: Standard user accounts (MEDIUM risk) - After Wave 1 validated
    Wave 3: Infrastructure accounts (MEDIUM-HIGH risk) - With change window
    Wave 4: NHIs without CCP/AAM integrations (HIGH risk) - Coordinated with app teams
    Wave 5: NHIs with CCP/AAM integrations (CRITICAL risk) - Requires app cutover

Usage:
    # Classify accounts using accounts export and NHI candidates
    python wave_classifier.py --accounts accounts.csv --nhis nhi_candidates.csv --output classified.csv

    # Classify with manual overrides
    python wave_classifier.py --accounts accounts.csv --overrides overrides.csv --output classified.csv

    # Generate wave summary report
    python wave_classifier.py --classified classified.csv --summary
"""

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Set
import re


# ============================================
# WAVE DEFINITIONS
# ============================================

WAVE_DEFINITIONS = {
    1: {
        "name": "Test/Dev Accounts",
        "risk_level": "LOW",
        "description": "Test, development, and sandbox accounts",
        "gate_criteria": ">95% heartbeat success, no critical issues",
        "duration": "1 week",
    },
    2: {
        "name": "Standard User Accounts",
        "risk_level": "MEDIUM",
        "description": "Regular user accounts without special dependencies",
        "gate_criteria": ">95% heartbeat, UAT sign-off",
        "duration": "1-2 weeks",
    },
    3: {
        "name": "Infrastructure Accounts",
        "risk_level": "MEDIUM-HIGH",
        "description": "Network devices, infrastructure, admin accounts",
        "gate_criteria": ">95% heartbeat, network team sign-off",
        "duration": "1 week",
    },
    4: {
        "name": "NHIs (Non-CCP)",
        "risk_level": "HIGH",
        "description": "Service accounts and NHIs not using CCP/AAM",
        "gate_criteria": ">95% heartbeat, app teams notified",
        "duration": "1 week",
    },
    5: {
        "name": "NHIs (CCP/AAM)",
        "risk_level": "CRITICAL",
        "description": "Application credentials requiring code changes",
        "gate_criteria": "App cutover complete, >95% success",
        "duration": "1-2 weeks",
    },
}

# Patterns for automatic classification
CLASSIFICATION_PATTERNS = {
    # Wave 1: Test/Dev
    "wave_1": {
        "safe_patterns": [
            r"test",
            r"dev",
            r"sandbox",
            r"poc",
            r"lab",
            r"demo",
            r"training",
        ],
        "name_patterns": [
            r"test",
            r"dev",
            r"temp",
            r"demo",
        ],
    },
    # Wave 3: Infrastructure
    "wave_3": {
        "platform_patterns": [
            r"cisco",
            r"juniper",
            r"f5",
            r"vmware",
            r"esxi",
            r"netapp",
            r"palo.*alto",
            r"checkpoint",
            r"fortinet",
            r"arista",
            r"linux.*root",
            r"unix.*root",
            r"windows.*local.*admin",
        ],
        "safe_patterns": [
            r"network",
            r"infrastructure",
            r"firewall",
            r"switch",
            r"router",
        ],
    },
}


@dataclass
class ClassifiedAccount:
    """Represents an account with wave classification."""
    account_id: str
    account_name: str
    safe_name: str
    platform: str = ""
    username: str = ""
    address: str = ""

    # Classification
    wave: int = 2  # Default to Wave 2 (standard)
    wave_name: str = ""
    classification_reason: str = ""
    risk_level: str = ""

    # NHI status
    is_nhi: bool = False
    nhi_category: str = ""
    has_ccp_integration: bool = False

    # Migration planning
    migration_order: int = 0  # Order within wave
    dependencies: str = ""
    app_owner: str = ""
    notes: str = ""

    # Status
    status: str = "PENDING"  # PENDING, MIGRATED, SKIPPED, FAILED


@dataclass
class WaveSummary:
    """Summary of wave classification."""
    total_accounts: int
    by_wave: Dict[int, int]
    nhi_count: int
    ccp_nhi_count: int
    classification_timestamp: str


def matches_patterns(text: str, patterns: List[str]) -> bool:
    """Check if text matches any of the patterns."""
    if not text:
        return False
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def classify_account(
    account: Dict,
    nhi_data: Optional[Dict] = None,
) -> ClassifiedAccount:
    """
    Classify a single account into a migration wave.

    Args:
        account: Account data from CyberArk export
        nhi_data: Optional NHI candidate data for this account

    Returns:
        ClassifiedAccount with wave assignment
    """
    # Extract account fields (handle various column name formats)
    def get_field(field_names: List[str]) -> str:
        for name in field_names:
            if name in account and account[name]:
                return str(account[name]).strip()
            # Try lowercase
            if name.lower() in account and account[name.lower()]:
                return str(account[name.lower()]).strip()
        return ""

    account_id = get_field(["id", "AccountId", "account_id", "ID"])
    account_name = get_field(["name", "AccountName", "account_name", "Name"])
    safe_name = get_field(["safeName", "safe_name", "Safe", "safe"])
    platform = get_field(["platformId", "platform_id", "Platform", "platform"])
    username = get_field(["userName", "user_name", "Username", "username"])
    address = get_field(["address", "Address", "target", "host"])

    classified = ClassifiedAccount(
        account_id=account_id,
        account_name=account_name,
        safe_name=safe_name,
        platform=platform,
        username=username,
        address=address,
    )

    # Check NHI status first (highest priority)
    if nhi_data:
        classified.is_nhi = True
        classified.nhi_category = nhi_data.get("nhi_category", "")

        # Check for CCP/AAM integration
        accessed_by = nhi_data.get("accessed_by", "")
        client_apps = nhi_data.get("client_apps", "")
        if re.search(r"CCP|AAM|AppUser", f"{accessed_by} {client_apps}", re.IGNORECASE):
            classified.has_ccp_integration = True
            classified.wave = 5
            classified.classification_reason = "NHI with CCP/AAM integration"
        else:
            classified.wave = 4
            classified.classification_reason = "NHI without CCP integration"

    # Wave 1: Test/Dev (check safe and name patterns)
    elif (matches_patterns(safe_name, CLASSIFICATION_PATTERNS["wave_1"]["safe_patterns"]) or
          matches_patterns(account_name, CLASSIFICATION_PATTERNS["wave_1"]["name_patterns"])):
        classified.wave = 1
        classified.classification_reason = "Test/Dev account (safe or name pattern)"

    # Wave 3: Infrastructure (check platform and safe patterns)
    elif (matches_patterns(platform, CLASSIFICATION_PATTERNS["wave_3"]["platform_patterns"]) or
          matches_patterns(safe_name, CLASSIFICATION_PATTERNS["wave_3"]["safe_patterns"])):
        classified.wave = 3
        classified.classification_reason = "Infrastructure account (platform or safe pattern)"

    # Default: Wave 2 (standard accounts)
    else:
        classified.wave = 2
        classified.classification_reason = "Standard account (default classification)"

    # Set wave metadata
    wave_info = WAVE_DEFINITIONS.get(classified.wave, WAVE_DEFINITIONS[2])
    classified.wave_name = wave_info["name"]
    classified.risk_level = wave_info["risk_level"]

    return classified


def load_accounts(file_path: Path) -> List[Dict]:
    """Load accounts from CSV."""
    accounts = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            accounts.append(row)
    return accounts


def load_nhis(file_path: Path) -> Dict[str, Dict]:
    """Load NHI candidates indexed by account ID."""
    nhis = {}
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            account_id = row.get("account_id", "")
            if account_id:
                nhis[account_id] = row
    return nhis


def load_overrides(file_path: Path) -> Dict[str, int]:
    """Load manual wave overrides (account_id -> wave)."""
    overrides = {}
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            account_id = row.get("account_id", "")
            wave = row.get("wave", "")
            if account_id and wave:
                try:
                    overrides[account_id] = int(wave)
                except ValueError:
                    pass
    return overrides


def classify_accounts(
    accounts: List[Dict],
    nhis: Dict[str, Dict] = None,
    overrides: Dict[str, int] = None,
) -> List[ClassifiedAccount]:
    """
    Classify all accounts into waves.

    Args:
        accounts: List of account dictionaries from CyberArk export
        nhis: Optional NHI candidates indexed by account ID
        overrides: Optional manual wave overrides by account ID

    Returns:
        List of ClassifiedAccount objects
    """
    nhis = nhis or {}
    overrides = overrides or {}

    classified = []

    for account in accounts:
        # Get account ID
        account_id = account.get("id") or account.get("AccountId") or account.get("account_id", "")

        # Check if this account is an NHI
        nhi_data = nhis.get(account_id)

        # Classify the account
        result = classify_account(account, nhi_data)

        # Apply manual override if exists
        if account_id in overrides:
            result.wave = overrides[account_id]
            wave_info = WAVE_DEFINITIONS.get(result.wave, WAVE_DEFINITIONS[2])
            result.wave_name = wave_info["name"]
            result.risk_level = wave_info["risk_level"]
            result.classification_reason = f"Manual override (original: {result.classification_reason})"

        classified.append(result)

    # Sort by wave, then by account name
    classified.sort(key=lambda x: (x.wave, x.account_name.lower()))

    # Assign migration order within each wave
    current_wave = 0
    order = 0
    for account in classified:
        if account.wave != current_wave:
            current_wave = account.wave
            order = 0
        order += 1
        account.migration_order = order

    return classified


def generate_summary(classified: List[ClassifiedAccount]) -> WaveSummary:
    """Generate classification summary."""
    by_wave = {}
    nhi_count = 0
    ccp_nhi_count = 0

    for account in classified:
        by_wave[account.wave] = by_wave.get(account.wave, 0) + 1
        if account.is_nhi:
            nhi_count += 1
        if account.has_ccp_integration:
            ccp_nhi_count += 1

    return WaveSummary(
        total_accounts=len(classified),
        by_wave=by_wave,
        nhi_count=nhi_count,
        ccp_nhi_count=ccp_nhi_count,
        classification_timestamp=datetime.now().isoformat(),
    )


def output_csv(classified: List[ClassifiedAccount], output_path: str):
    """Output classified accounts to CSV."""
    if not classified:
        print("No accounts to write.")
        return

    rows = [asdict(a) for a in classified]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Classified accounts written to: {output_path}")


def output_json(classified: List[ClassifiedAccount], summary: WaveSummary, output_path: str):
    """Output classification and summary to JSON."""
    result = {
        "summary": asdict(summary),
        "wave_definitions": WAVE_DEFINITIONS,
        "accounts": [asdict(a) for a in classified],
    }

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"JSON results written to: {output_path}")


def print_summary(summary: WaveSummary, classified: List[ClassifiedAccount]):
    """Print classification summary to console."""
    print("\n" + "=" * 70)
    print("ACCOUNT WAVE CLASSIFICATION SUMMARY")
    print("=" * 70)
    print(f"Classification Time:  {summary.classification_timestamp}")
    print(f"Total Accounts:       {summary.total_accounts}")
    print(f"NHI Accounts:         {summary.nhi_count}")
    print(f"CCP/AAM NHIs:         {summary.ccp_nhi_count}")
    print("-" * 70)
    print("WAVE DISTRIBUTION:")
    print("-" * 70)

    for wave_num in sorted(summary.by_wave.keys()):
        count = summary.by_wave[wave_num]
        wave_info = WAVE_DEFINITIONS.get(wave_num, {})
        pct = (count / summary.total_accounts * 100) if summary.total_accounts > 0 else 0

        print(f"\nWave {wave_num}: {wave_info.get('name', 'Unknown')}")
        print(f"  Count:       {count} ({pct:.1f}%)")
        print(f"  Risk Level:  {wave_info.get('risk_level', 'Unknown')}")
        print(f"  Duration:    {wave_info.get('duration', 'Unknown')}")
        print(f"  Gate:        {wave_info.get('gate_criteria', 'N/A')}")

    print("\n" + "=" * 70)
    print("MIGRATION ORDER:")
    print("-" * 70)
    print("Wave 1 -> Wave 2 -> Wave 3 -> Wave 4 -> Wave 5")
    print("(Test)   (Users)   (Infra)   (NHI)     (CCP/AAM)")
    print("=" * 70)

    # Sample accounts per wave
    print("\nSAMPLE ACCOUNTS PER WAVE:")
    for wave_num in sorted(summary.by_wave.keys()):
        wave_accounts = [a for a in classified if a.wave == wave_num][:3]
        if wave_accounts:
            print(f"\n  Wave {wave_num}:")
            for a in wave_accounts:
                print(f"    - {a.account_name} ({a.safe_name}) - {a.classification_reason}")


def main():
    parser = argparse.ArgumentParser(
        description="Classify accounts into migration waves"
    )
    parser.add_argument(
        "--accounts", "-a",
        help="Path to accounts CSV export from CyberArk"
    )
    parser.add_argument(
        "--nhis", "-n",
        help="Path to NHI candidates CSV from nhi_discovery.py"
    )
    parser.add_argument(
        "--overrides", "-r",
        help="Path to manual wave overrides CSV (account_id, wave)"
    )
    parser.add_argument(
        "--classified", "-c",
        help="Path to already-classified accounts (for summary only)"
    )
    parser.add_argument(
        "--output", "-o",
        default="classified_accounts.csv",
        help="Output file path (default: classified_accounts.csv)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary only (requires --classified)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress console output"
    )

    args = parser.parse_args()

    # Summary mode
    if args.summary and args.classified:
        classified_path = Path(args.classified)
        if not classified_path.exists():
            print(f"Error: Classified file not found: {classified_path}")
            return 1

        # Load and display summary
        accounts = load_accounts(classified_path)
        classified = [ClassifiedAccount(**{k: v for k, v in a.items() if k in ClassifiedAccount.__dataclass_fields__})
                      for a in accounts]
        summary = generate_summary(classified)
        print_summary(summary, classified)
        return 0

    # Classification mode
    if not args.accounts:
        parser.error("--accounts is required for classification")

    accounts_path = Path(args.accounts)
    if not accounts_path.exists():
        print(f"Error: Accounts file not found: {accounts_path}")
        return 1

    # Load data
    if not args.quiet:
        print(f"Loading accounts from {accounts_path}...")
    accounts = load_accounts(accounts_path)

    nhis = {}
    if args.nhis:
        nhis_path = Path(args.nhis)
        if nhis_path.exists():
            if not args.quiet:
                print(f"Loading NHI candidates from {nhis_path}...")
            nhis = load_nhis(nhis_path)

    overrides = {}
    if args.overrides:
        overrides_path = Path(args.overrides)
        if overrides_path.exists():
            if not args.quiet:
                print(f"Loading overrides from {overrides_path}...")
            overrides = load_overrides(overrides_path)

    # Classify accounts
    if not args.quiet:
        print(f"Classifying {len(accounts)} accounts into waves...")

    classified = classify_accounts(accounts, nhis, overrides)
    summary = generate_summary(classified)

    if not args.quiet:
        print_summary(summary, classified)

    # Output results
    if args.format == "json":
        json_path = args.output if args.output.endswith(".json") else args.output.replace(".csv", ".json")
        output_json(classified, summary, json_path)
    else:
        output_csv(classified, args.output)

    return 0


if __name__ == "__main__":
    exit(main())
