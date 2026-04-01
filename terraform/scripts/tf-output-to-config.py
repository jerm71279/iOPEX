#!/usr/bin/env python3
"""
tf-output-to-config.py — Generate orchestrator config.json from Terraform outputs.

Reads Terraform outputs from the shared and option-specific compositions
and generates the AI orchestrator's config.json with connection details.

Credentials remain in Azure Key Vault (not written to config).

Usage:
    python3 scripts/tf-output-to-config.py --option a --env dev --output config.json
    python3 scripts/tf-output-to-config.py --option b --env prod --output config.json
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def get_terraform_output(composition_dir: str) -> dict:
    """Run terraform output -json and return parsed dict."""
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=composition_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        raw = json.loads(result.stdout)
        # Extract values from terraform output format {key: {value: ..., type: ...}}
        return {k: v.get("value", v) for k, v in raw.items()}
    except subprocess.CalledProcessError as e:
        print(f"ERROR: terraform output failed in {composition_dir}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("ERROR: terraform CLI not found in PATH", file=sys.stderr)
        sys.exit(1)


def build_config(option: str, shared: dict, option_outputs: dict) -> dict:
    """Build orchestrator config.json from Terraform outputs."""
    config = {
        "cyberark_on_prem": {
            "base_url": "https://pvwa.company.com",
            "username": "COMMENT: Retrieved from Key Vault at runtime",
            "password": "COMMENT: Retrieved from Key Vault at runtime",
            "auth_type": "LDAP",
            "verify_ssl": True,
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "rate_limit": 0.1,
            "batch_size": 1000,
        },
        "servicenow": {
            "instance_url": "",
            "username": "COMMENT: Retrieved from Key Vault at runtime",
            "password": "COMMENT: Retrieved from Key Vault at runtime",
        },
        "output_dir": "./output",
        "log_level": "INFO",
        "environment": shared.get("environment", "dev"),
        "infrastructure": {
            "key_vault_uri": shared.get("key_vault_uri", ""),
            "orchestrator_ip": shared.get("orchestrator_public_ip", ""),
            "vnet_id": shared.get("vnet_id", ""),
            "log_analytics_workspace_id": shared.get(
                "log_analytics_workspace_id", ""
            ),
        },
    }

    if option == "a":
        config["secret_server"] = {
            "base_url": "COMMENT: Set via SS_BASE_URL env var or Key Vault",
            "auth_method": "oauth2",
            "client_id": "COMMENT: Retrieved from Key Vault at runtime",
            "client_secret": "COMMENT: Retrieved from Key Vault at runtime",
            "verify_ssl": True,
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "rate_limit": 0.1,
            "batch_size": 500,
            "default_folder_id": -1,
            "inherit_permissions": True,
        }
        config["strongdm"] = {
            "gateway_id": option_outputs.get("strongdm_gateway_id", ""),
            "resource_count": option_outputs.get("strongdm_resource_count", 0),
            "resource_ids": option_outputs.get("strongdm_resource_ids", {}),
            "role_ids": option_outputs.get("strongdm_role_ids", {}),
        }

    elif option == "b":
        config["privilege_cloud"] = {
            "base_url": "COMMENT: Set via PCLOUD_BASE_URL env var or Key Vault",
            "auth_method": "oauth2",
            "identity_url": "COMMENT: Set via PCLOUD_IDENTITY_URL env var",
            "client_id": "COMMENT: Retrieved from Key Vault at runtime",
            "client_secret": "COMMENT: Retrieved from Key Vault at runtime",
            "verify_ssl": True,
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "rate_limit": 0.1,
            "batch_size": 500,
        }
        config["cyberark_safes"] = {
            "safe_count": option_outputs.get("safe_count", 0),
            "safe_ids": option_outputs.get("safe_ids", {}),
            "safe_names": option_outputs.get("safe_names", []),
        }

    return config


def main():
    parser = argparse.ArgumentParser(
        description="Generate orchestrator config.json from Terraform outputs"
    )
    parser.add_argument(
        "--option",
        choices=["a", "b"],
        required=True,
        help="Migration option: a (Delinea/StrongDM) or b (Privilege Cloud)",
    )
    parser.add_argument(
        "--env",
        choices=["dev", "staging", "prod"],
        required=True,
        help="Target environment",
    )
    parser.add_argument(
        "--output",
        default="config.json",
        help="Output file path (default: config.json)",
    )
    parser.add_argument(
        "--terraform-dir",
        default="",
        help="Root terraform directory (default: auto-detect from script location)",
    )
    args = parser.parse_args()

    # Resolve terraform directory
    if args.terraform_dir:
        tf_dir = Path(args.terraform_dir)
    else:
        tf_dir = Path(__file__).resolve().parent.parent

    shared_dir = tf_dir / "compositions" / "shared"
    option_dir = tf_dir / "compositions" / f"option-{args.option}"

    if not shared_dir.exists():
        print(f"ERROR: Shared composition not found: {shared_dir}", file=sys.stderr)
        sys.exit(1)
    if not option_dir.exists():
        print(
            f"ERROR: Option {args.option} composition not found: {option_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Reading Terraform outputs for option-{args.option} ({args.env})...")
    print(f"  Shared: {shared_dir}")
    print(f"  Option: {option_dir}")

    shared_outputs = get_terraform_output(str(shared_dir))
    option_outputs = get_terraform_output(str(option_dir))

    config = build_config(args.option, shared_outputs, option_outputs)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"\nGenerated: {output_path}")
    print(f"Environment: {args.env}")
    print(f"Option: {'Delinea SS + StrongDM' if args.option == 'a' else 'CyberArk Privilege Cloud'}")
    print("\nNOTE: Credentials are NOT in this file.")
    print("      They are retrieved from Azure Key Vault at runtime.")


if __name__ == "__main__":
    main()
