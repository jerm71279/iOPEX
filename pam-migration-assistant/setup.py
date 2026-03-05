#!/usr/bin/env python3
"""
PAM Migration Assistant - Setup Configuration

CyberArk PAS to Delinea Secret Server migration toolkit.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="pam-migration-assistant",
    version="0.1.0",
    author="iOPEX Migration Team",
    description="CyberArk to Delinea Secret Server PAM migration toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iopex/pam-migration-assistant",
    packages=find_packages(exclude=["tests", "tests.*"]),
    py_modules=[
        "scripts.ccp_code_scanner",
        "scripts.code_converter",
        "scripts.generate_wrapper",
    ],
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "responses>=0.22.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pam-scan=scripts.ccp_code_scanner:main",
            "pam-convert=scripts.code_converter:main",
            "pam-wrapper=scripts.generate_wrapper:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="cyberark, delinea, secret-server, pam, migration, security",
)
