#!/usr/bin/env python3
"""
Sample CyberArk CCP Integration - Python
Used for testing ccp_code_scanner.py pattern detection.

This file contains intentional CyberArk patterns that should be detected.
"""

import requests
import os

# Pattern: CCP_APPID - Application ID configuration
APP_ID = "MyWebApp"
app_id = "SecondApp"

# Pattern: CCP_SAFE_REFERENCE - Safe name
SAFE_NAME = "Production-Secrets"
Safe = "Dev-Safe"

# Pattern: CCP_OBJECT_REFERENCE - Object/Account name
OBJECT_NAME = "db-admin-account"
objectName = "svc-account"

# Pattern: CONFIG_CYBERARK_URL - URL configuration
CYBERARK_URL = "https://cyberark.company.com"
pvwa_url = "https://pvwa.company.com/PasswordVault"
aim_url = "https://aim.company.com:18923"


def get_password_from_cyberark():
    """
    Pattern: CCP_REST_ENDPOINT - REST API call
    Pattern: PYTHON_CCP_CALL - Python requests to CyberArk
    """
    # Direct CCP call
    response = requests.get(
        f"{CYBERARK_URL}/AIMWebService/api/Accounts",
        params={
            "AppID": APP_ID,
            "Safe": SAFE_NAME,
            "Object": OBJECT_NAME
        },
        verify=True
    )
    return response.json()["Content"]


def get_password_via_passwordvault():
    """
    Pattern: CCP_REST_ENDPOINT - PasswordVault API
    """
    url = f"{pvwa_url}/PasswordVault/API/Accounts"
    response = requests.get(url, params={"AppID": "TestApp"})
    return response.json()


def connect_to_database():
    """
    Pattern: CONNECTION_STRING_CCP - CyberArk provider in connection string
    """
    # This pattern should be detected
    conn_string = "Provider=CyberArk;Server=db.company.com;AppID=MyApp"
    return conn_string


class CyberArkClient:
    """Example class that wraps CyberArk CCP calls."""

    def __init__(self):
        self.cyberark_password = None
        self.vault_address = os.environ.get("VAULT_ADDRESS")

    def retrieve_credential(self, safe, obj):
        """Retrieve credential using CCP."""
        return requests.get(
            f"https://aim.company.com/AIMWebService/api/Accounts",
            params={"AppID": "MyApp", "Safe": safe, "Object": obj}
        )


# Additional patterns that should be detected
APPLICATION_ID = "AppID='LegacyApp'"
safe_config = {"safeName": "IT-Secrets"}
account_config = {"accountName": "svc-backup"}
