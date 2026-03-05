#!/usr/bin/env python3
"""
Non-Human Identity (NHI) Discovery Script

Identifies NHIs from CyberArk audit data by analyzing access patterns.
NHIs are credentials used by applications, services, and automated processes
rather than humans - they are the highest-risk accounts in PAM migrations.

Based on Enhanced ETL Migration Plan v2.0 - Section 1.2

Usage:
    # From CyberArk audit export (CSV)
    python nhi_discovery.py --audit-file cyberark_audit.csv --output nhi_candidates.csv

    # From account activity export
    python nhi_discovery.py --accounts accounts.csv --activity activity.csv --output nhi_candidates.csv

    # Analyze and classify existing NHI candidates
    python nhi_discovery.py --nhi-file nhi_candidates.csv --classify --output classified_nhis.csv
"""

import argparse
import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Set
from collections import defaultdict
import re


# ============================================
# NHI DETECTION PATTERNS
# ============================================

# Patterns indicating programmatic/NHI access
NHI_ACCESS_PATTERNS = {
    "performed_by": [
        r"CCP",
        r"AAM",
        r"AppUser",
        r"ServiceAccount",
        r"svc[-_]",
        r"app[-_]",
        r"batch[-_]",
        r"job[-_]",
        r"scheduler",
        r"automation",
        r"api[-_]",
        r"system",
    ],
    "client_app": [
        r"^(?!PVWA$)",  # Not PVWA (human interface)
        r"CCP",
        r"AAM",
        r"SDK",
        r"REST",
        r"API",
        r"Script",
        r"Powershell",
        r"Python",
        r"Java",
        r"\.NET",
    ],
    "access_reason": [
        r"automated",
        r"scheduled",
        r"batch",
        r"job",
        r"service",
        r"application",
        r"script",
        r"api",
        r"integration",
    ],
}

# NHI Categories
NHI_CATEGORIES = {
    "CCP_AAM": "Application credentials retrieved via CCP/AAM API",
    "SERVICE_ACCOUNT": "Windows/Linux service accounts",
    "SCHEDULED_TASK": "Credentials for scheduled tasks/cron jobs",
    "DATABASE": "Database connection credentials",
    "API_KEY": "API keys and tokens",
    "DEVOPS": "CI/CD pipeline credentials",
    "MACHINE_IDENTITY": "Certificates, SSH keys, machine credentials",
}

# Risk levels based on access patterns
RISK_LEVELS = {
    "CRITICAL": "Active CCP/AAM integration with >100 accesses/day",
    "HIGH": "Frequent programmatic access (10-100/day) or undocumented",
    "MEDIUM": "Low-frequency service account (<10/day)",
    "LOW": "Dormant or test account with programmatic history",
}


@dataclass
class NHICandidate:
    """Represents a potential Non-Human Identity."""
    account_id: str
    account_name: str
    safe_name: str
    platform: str = ""
    username: str = ""
    address: str = ""

    # Access analysis
    total_access_count: int = 0
    programmatic_access_count: int = 0
    last_access: str = ""
    first_access: str = ""
    access_frequency_per_day: float = 0.0

    # Classification
    nhi_category: str = ""
    risk_level: str = ""
    confidence_score: float = 0.0

    # Access patterns
    accessed_by: List[str] = field(default_factory=list)
    client_apps: List[str] = field(default_factory=list)
    access_reasons: List[str] = field(default_factory=list)
    access_hours: Dict[int, int] = field(default_factory=dict)  # Hour -> count

    # Migration planning
    app_owner: str = ""
    app_owner_email: str = ""
    migration_wave: int = 0
    notes: str = ""


@dataclass
class NHIDiscoverySummary:
    """Summary of NHI discovery results."""
    total_accounts_analyzed: int
    nhi_candidates_found: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    categories: Dict[str, int]
    scan_timestamp: str
    source_file: str


def is_programmatic_access(
    performed_by: str = "",
    client_app: str = "",
    access_reason: str = "",
) -> bool:
    """
    Determine if an access event indicates programmatic (NHI) usage.

    Returns True if patterns suggest non-human access.
    """
    # Check performed_by patterns
    for pattern in NHI_ACCESS_PATTERNS["performed_by"]:
        if re.search(pattern, performed_by, re.IGNORECASE):
            return True

    # Check client_app patterns
    for pattern in NHI_ACCESS_PATTERNS["client_app"]:
        if re.search(pattern, client_app, re.IGNORECASE):
            return True

    # Check access_reason patterns
    for pattern in NHI_ACCESS_PATTERNS["access_reason"]:
        if re.search(pattern, access_reason, re.IGNORECASE):
            return True

    return False


def classify_nhi_category(candidate: NHICandidate) -> str:
    """Classify NHI into a category based on access patterns."""

    # Check for CCP/AAM access
    for accessor in candidate.accessed_by + candidate.client_apps:
        if re.search(r"CCP|AAM", accessor, re.IGNORECASE):
            return "CCP_AAM"

    # Check for service account patterns
    if re.search(r"svc[-_]|service", candidate.account_name, re.IGNORECASE):
        return "SERVICE_ACCOUNT"

    # Check for scheduled task patterns
    for reason in candidate.access_reasons:
        if re.search(r"scheduled|cron|task|job|batch", reason, re.IGNORECASE):
            return "SCHEDULED_TASK"

    # Check for database patterns
    if re.search(r"sql|oracle|postgres|mysql|db[-_]|database",
                 candidate.account_name, re.IGNORECASE):
        return "DATABASE"

    # Check for DevOps patterns
    for accessor in candidate.accessed_by + candidate.client_apps:
        if re.search(r"jenkins|gitlab|github|azure|terraform|ansible",
                     accessor, re.IGNORECASE):
            return "DEVOPS"

    # Check for API patterns
    if re.search(r"api[-_]|key[-_]|token", candidate.account_name, re.IGNORECASE):
        return "API_KEY"

    # Default to service account if clearly programmatic
    if candidate.programmatic_access_count > 0:
        return "SERVICE_ACCOUNT"

    return ""


def calculate_risk_level(candidate: NHICandidate) -> str:
    """Calculate risk level based on access patterns."""

    freq = candidate.access_frequency_per_day

    # CRITICAL: Active CCP/AAM with high frequency
    if candidate.nhi_category == "CCP_AAM" and freq > 100:
        return "CRITICAL"

    # HIGH: Frequent access or CCP/AAM
    if freq > 100 or candidate.nhi_category == "CCP_AAM":
        return "HIGH"

    # MEDIUM: Regular programmatic access
    if freq >= 10 or candidate.programmatic_access_count > 50:
        return "MEDIUM"

    # LOW: Infrequent access
    return "LOW"


def calculate_confidence_score(candidate: NHICandidate) -> float:
    """
    Calculate confidence score (0-1) that this is truly an NHI.

    Factors:
    - Programmatic access ratio
    - Access pattern consistency
    - Off-hours access
    - Known NHI naming patterns
    """
    score = 0.0

    # Programmatic access ratio (max 0.4)
    if candidate.total_access_count > 0:
        ratio = candidate.programmatic_access_count / candidate.total_access_count
        score += ratio * 0.4

    # High frequency access (max 0.2)
    if candidate.access_frequency_per_day > 10:
        score += min(0.2, candidate.access_frequency_per_day / 500)

    # Off-hours access pattern (max 0.2)
    if candidate.access_hours:
        off_hours_count = sum(
            candidate.access_hours.get(h, 0)
            for h in [0,1,2,3,4,5,22,23]
        )
        total = sum(candidate.access_hours.values())
        if total > 0:
            off_hours_ratio = off_hours_count / total
            score += off_hours_ratio * 0.2

    # Known NHI naming pattern (max 0.2)
    nhi_name_patterns = [
        r"^svc[-_]",
        r"^app[-_]",
        r"^batch[-_]",
        r"[-_]svc$",
        r"[-_]api$",
        r"service",
        r"automation",
    ]
    for pattern in nhi_name_patterns:
        if re.search(pattern, candidate.account_name, re.IGNORECASE):
            score += 0.2
            break

    return min(1.0, score)


def analyze_audit_file(audit_file: Path) -> List[NHICandidate]:
    """
    Analyze CyberArk audit export to identify NHI candidates.

    Expected CSV columns (flexible - will map common variations):
    - Account ID / AccountID / accountId
    - Account Name / AccountName / accountName / Name
    - Safe / SafeName / safe_name
    - Action / ActionType
    - Performed By / PerformedBy / User
    - Client Application / ClientApp / Application
    - Reason / AccessReason
    - Timestamp / Time / Date
    """
    # Column name mappings (lowercase)
    column_mappings = {
        "account_id": ["account id", "accountid", "account_id", "id"],
        "account_name": ["account name", "accountname", "account_name", "name"],
        "safe_name": ["safe", "safename", "safe_name"],
        "action": ["action", "actiontype", "action_type"],
        "performed_by": ["performed by", "performedby", "performed_by", "user"],
        "client_app": ["client application", "clientapp", "client_app", "application"],
        "reason": ["reason", "accessreason", "access_reason"],
        "timestamp": ["timestamp", "time", "date", "datetime"],
        "platform": ["platform", "platformid", "platform_id"],
        "username": ["username", "user_name"],
        "address": ["address", "target", "host"],
    }

    accounts: Dict[str, NHICandidate] = {}

    with open(audit_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        # Map actual columns to our expected names
        actual_columns = {col.lower().strip(): col for col in reader.fieldnames}
        col_map = {}

        for our_name, variations in column_mappings.items():
            for var in variations:
                if var in actual_columns:
                    col_map[our_name] = actual_columns[var]
                    break

        for row in reader:
            # Extract values using mapped columns
            def get_val(key: str) -> str:
                if key in col_map and col_map[key] in row:
                    return str(row[col_map[key]]).strip()
                return ""

            account_id = get_val("account_id")
            if not account_id:
                continue

            # Get or create candidate
            if account_id not in accounts:
                accounts[account_id] = NHICandidate(
                    account_id=account_id,
                    account_name=get_val("account_name"),
                    safe_name=get_val("safe_name"),
                    platform=get_val("platform"),
                    username=get_val("username"),
                    address=get_val("address"),
                )

            candidate = accounts[account_id]

            # Analyze this access event
            performed_by = get_val("performed_by")
            client_app = get_val("client_app")
            reason = get_val("reason")
            timestamp = get_val("timestamp")
            action = get_val("action")

            # Only count password retrieval actions
            if action and "retrieve" not in action.lower() and "password" not in action.lower():
                continue

            candidate.total_access_count += 1

            # Check if programmatic access
            if is_programmatic_access(performed_by, client_app, reason):
                candidate.programmatic_access_count += 1

                if performed_by and performed_by not in candidate.accessed_by:
                    candidate.accessed_by.append(performed_by)

                if client_app and client_app not in candidate.client_apps:
                    candidate.client_apps.append(client_app)

                if reason and reason not in candidate.access_reasons:
                    candidate.access_reasons.append(reason)

            # Track timestamps
            if timestamp:
                if not candidate.first_access or timestamp < candidate.first_access:
                    candidate.first_access = timestamp
                if not candidate.last_access or timestamp > candidate.last_access:
                    candidate.last_access = timestamp

                # Track access hours
                try:
                    # Try common timestamp formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M:%S"]:
                        try:
                            dt = datetime.strptime(timestamp[:19], fmt)
                            hour = dt.hour
                            candidate.access_hours[hour] = candidate.access_hours.get(hour, 0) + 1
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

    # Post-process candidates
    results = []
    for candidate in accounts.values():
        # Skip if no programmatic access
        if candidate.programmatic_access_count == 0:
            continue

        # Calculate access frequency
        if candidate.first_access and candidate.last_access:
            try:
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M:%S"]:
                    try:
                        first = datetime.strptime(candidate.first_access[:19], fmt)
                        last = datetime.strptime(candidate.last_access[:19], fmt)
                        days = max(1, (last - first).days)
                        candidate.access_frequency_per_day = candidate.total_access_count / days
                        break
                    except ValueError:
                        continue
            except Exception:
                candidate.access_frequency_per_day = candidate.total_access_count

        # Classify
        candidate.nhi_category = classify_nhi_category(candidate)
        candidate.risk_level = calculate_risk_level(candidate)
        candidate.confidence_score = calculate_confidence_score(candidate)

        # Assign default migration wave based on risk
        wave_map = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2}
        candidate.migration_wave = wave_map.get(candidate.risk_level, 3)

        results.append(candidate)

    # Sort by risk level and confidence
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    results.sort(key=lambda x: (risk_order.get(x.risk_level, 99), -x.confidence_score))

    return results


def generate_summary(candidates: List[NHICandidate], source: str) -> NHIDiscoverySummary:
    """Generate summary statistics from NHI candidates."""

    categories = defaultdict(int)
    for c in candidates:
        if c.nhi_category:
            categories[c.nhi_category] += 1

    return NHIDiscoverySummary(
        total_accounts_analyzed=len(candidates),
        nhi_candidates_found=len([c for c in candidates if c.confidence_score > 0.3]),
        critical_count=len([c for c in candidates if c.risk_level == "CRITICAL"]),
        high_count=len([c for c in candidates if c.risk_level == "HIGH"]),
        medium_count=len([c for c in candidates if c.risk_level == "MEDIUM"]),
        low_count=len([c for c in candidates if c.risk_level == "LOW"]),
        categories=dict(categories),
        scan_timestamp=datetime.now().isoformat(),
        source_file=source,
    )


def output_csv(candidates: List[NHICandidate], output_path: str):
    """Output NHI candidates to CSV."""
    if not candidates:
        print("No NHI candidates to write.")
        return

    # Flatten dataclass for CSV
    rows = []
    for c in candidates:
        row = {
            "account_id": c.account_id,
            "account_name": c.account_name,
            "safe_name": c.safe_name,
            "platform": c.platform,
            "username": c.username,
            "address": c.address,
            "total_access_count": c.total_access_count,
            "programmatic_access_count": c.programmatic_access_count,
            "access_frequency_per_day": round(c.access_frequency_per_day, 2),
            "last_access": c.last_access,
            "nhi_category": c.nhi_category,
            "risk_level": c.risk_level,
            "confidence_score": round(c.confidence_score, 3),
            "accessed_by": "; ".join(c.accessed_by[:5]),  # Limit for readability
            "client_apps": "; ".join(c.client_apps[:5]),
            "migration_wave": c.migration_wave,
            "app_owner": c.app_owner,
            "app_owner_email": c.app_owner_email,
            "notes": c.notes,
        }
        rows.append(row)

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"NHI candidates written to: {output_path}")


def output_json(candidates: List[NHICandidate], summary: NHIDiscoverySummary, output_path: str):
    """Output NHI candidates and summary to JSON."""
    result = {
        "summary": asdict(summary),
        "candidates": [asdict(c) for c in candidates],
    }

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"JSON results written to: {output_path}")


def print_summary(summary: NHIDiscoverySummary, candidates: List[NHICandidate]):
    """Print summary to console."""
    print("\n" + "=" * 60)
    print("NON-HUMAN IDENTITY (NHI) DISCOVERY RESULTS")
    print("=" * 60)
    print(f"Source File:          {summary.source_file}")
    print(f"Scan Timestamp:       {summary.scan_timestamp}")
    print(f"Accounts Analyzed:    {summary.total_accounts_analyzed}")
    print(f"NHI Candidates Found: {summary.nhi_candidates_found}")
    print("-" * 60)
    print("Risk Distribution:")
    print(f"  CRITICAL: {summary.critical_count}")
    print(f"  HIGH:     {summary.high_count}")
    print(f"  MEDIUM:   {summary.medium_count}")
    print(f"  LOW:      {summary.low_count}")
    print("-" * 60)
    print("Categories:")
    for cat, count in summary.categories.items():
        desc = NHI_CATEGORIES.get(cat, cat)
        print(f"  {cat}: {count} - {desc}")
    print("=" * 60)

    if candidates:
        print("\nTOP 10 CRITICAL/HIGH RISK NHIs:")
        print("-" * 60)
        high_risk = [c for c in candidates if c.risk_level in ["CRITICAL", "HIGH"]][:10]
        for c in high_risk:
            print(f"\n  Account: {c.account_name}")
            print(f"  Safe: {c.safe_name}")
            print(f"  Category: {c.nhi_category}")
            print(f"  Risk: {c.risk_level} (confidence: {c.confidence_score:.2f})")
            print(f"  Access: {c.programmatic_access_count} programmatic / {c.total_access_count} total")
            if c.accessed_by:
                print(f"  Accessed by: {', '.join(c.accessed_by[:3])}")


def main():
    parser = argparse.ArgumentParser(
        description="Discover Non-Human Identities (NHIs) from CyberArk audit data"
    )
    parser.add_argument(
        "--audit-file", "-a",
        help="Path to CyberArk audit export CSV"
    )
    parser.add_argument(
        "--output", "-o",
        default="nhi_candidates.csv",
        help="Output file path (default: nhi_candidates.csv)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.3,
        help="Minimum confidence score to include (default: 0.3)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress console output"
    )

    args = parser.parse_args()

    if not args.audit_file:
        parser.error("--audit-file is required")

    audit_path = Path(args.audit_file)
    if not audit_path.exists():
        print(f"Error: Audit file not found: {audit_path}")
        return 1

    if not args.quiet:
        print(f"Analyzing {audit_path} for NHI patterns...")

    # Analyze audit file
    candidates = analyze_audit_file(audit_path)

    # Filter by confidence
    candidates = [c for c in candidates if c.confidence_score >= args.min_confidence]

    # Generate summary
    summary = generate_summary(candidates, str(audit_path))

    if not args.quiet:
        print_summary(summary, candidates)

    # Output results
    if args.format == "json":
        json_path = args.output if args.output.endswith(".json") else args.output.replace(".csv", ".json")
        output_json(candidates, summary, json_path)
    else:
        output_csv(candidates, args.output)

    # Return exit code based on critical findings
    return 1 if summary.critical_count > 0 else 0


if __name__ == "__main__":
    exit(main())
