#!/usr/bin/env python3
"""
Unit tests for ccp_code_scanner.py

Tests pattern detection across multiple languages and file types.
"""

import pytest
import json
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ccp_code_scanner import (
    scan_file,
    scan_directory,
    generate_summary,
    CYBERARK_PATTERNS,
    SCAN_EXTENSIONS,
)


class TestPatternDefinitions:
    """Test that pattern definitions are properly structured."""

    def test_all_patterns_have_required_fields(self):
        """Each pattern should have patterns, risk, description, migration_action."""
        required_fields = ["patterns", "risk", "description", "migration_action"]

        for name, info in CYBERARK_PATTERNS.items():
            for field in required_fields:
                assert field in info, f"Pattern {name} missing field: {field}"

    def test_risk_levels_are_valid(self):
        """Risk levels should be HIGH, MEDIUM, or LOW."""
        valid_risks = {"HIGH", "MEDIUM", "LOW"}

        for name, info in CYBERARK_PATTERNS.items():
            assert info["risk"] in valid_risks, f"Pattern {name} has invalid risk: {info['risk']}"

    def test_patterns_are_valid_regex(self):
        """All patterns should be valid regular expressions."""
        import re

        for name, info in CYBERARK_PATTERNS.items():
            for pattern in info["patterns"]:
                try:
                    re.compile(pattern)
                except re.error as e:
                    pytest.fail(f"Pattern {name} has invalid regex '{pattern}': {e}")


class TestScanFile:
    """Test single file scanning."""

    @pytest.fixture
    def fixtures_path(self):
        return Path(__file__).parent / "fixtures"

    def test_scan_python_file(self, fixtures_path):
        """Should detect CyberArk patterns in Python files."""
        python_file = fixtures_path / "sample_cyberark_python.py"
        matches = scan_file(python_file)

        assert len(matches) > 0, "Should find matches in Python file"

        # Check for specific patterns
        pattern_names = {m.pattern_name for m in matches}
        assert "CCP_APPID" in pattern_names, "Should detect AppID pattern"
        assert "CCP_SAFE_REFERENCE" in pattern_names, "Should detect Safe pattern"
        assert "CCP_REST_ENDPOINT" in pattern_names, "Should detect REST endpoint"
        assert "CONFIG_CYBERARK_URL" in pattern_names, "Should detect URL config"

    def test_scan_powershell_file(self, fixtures_path):
        """Should detect CyberArk patterns in PowerShell files."""
        ps_file = fixtures_path / "sample_cyberark_powershell.ps1"
        matches = scan_file(ps_file)

        assert len(matches) > 0, "Should find matches in PowerShell file"

        pattern_names = {m.pattern_name for m in matches}
        assert "POWERSHELL_PSPAS" in pattern_names, "Should detect psPAS patterns"

    def test_scan_csharp_file(self, fixtures_path):
        """Should detect CyberArk patterns in C# files."""
        cs_file = fixtures_path / "sample_cyberark_csharp.cs"
        matches = scan_file(cs_file)

        assert len(matches) > 0, "Should find matches in C# file"

        pattern_names = {m.pattern_name for m in matches}
        assert "DOTNET_CYBERARK_SDK" in pattern_names, "Should detect .NET SDK"
        assert "DOTNET_PASSWORD_REQUEST" in pattern_names, "Should detect password request"

    def test_scan_yaml_file(self, fixtures_path):
        """Should detect CyberArk patterns in YAML config files."""
        yaml_file = fixtures_path / "sample_config.yml"
        matches = scan_file(yaml_file)

        assert len(matches) > 0, "Should find matches in YAML file"

        pattern_names = {m.pattern_name for m in matches}
        assert "CONFIG_CYBERARK_URL" in pattern_names, "Should detect URL in config"

    def test_scan_nonexistent_file(self, fixtures_path):
        """Should handle nonexistent files gracefully."""
        fake_file = fixtures_path / "does_not_exist.py"
        matches = scan_file(fake_file)
        assert matches == [], "Should return empty list for nonexistent file"


class TestScanDirectory:
    """Test directory scanning."""

    @pytest.fixture
    def fixtures_path(self):
        return Path(__file__).parent / "fixtures"

    def test_scan_fixtures_directory(self, fixtures_path):
        """Should find matches across all fixture files."""
        matches, files_scanned = scan_directory(fixtures_path)

        assert files_scanned >= 4, "Should scan at least 4 fixture files"
        assert len(matches) > 10, "Should find many matches across fixtures"

    def test_scan_returns_file_count(self, fixtures_path):
        """Should return accurate file count."""
        matches, files_scanned = scan_directory(fixtures_path)

        # Count files with known extensions
        expected_files = sum(
            1 for f in fixtures_path.iterdir()
            if f.suffix.lower() in SCAN_EXTENSIONS
        )

        assert files_scanned == expected_files, "File count should match"


class TestGenerateSummary:
    """Test summary generation."""

    def test_summary_counts_risk_levels(self):
        """Summary should correctly count risk levels."""
        from ccp_code_scanner import ScanMatch

        # Create mock matches
        matches = [
            ScanMatch(
                file_path="test.py",
                line_number=1,
                line_content="test",
                pattern_name="TEST",
                pattern_type="test",
                risk_level="HIGH",
                description="",
                migration_action="",
                secret_server_equivalent="",
                language="Python"
            ),
            ScanMatch(
                file_path="test.py",
                line_number=2,
                line_content="test",
                pattern_name="TEST2",
                pattern_type="test",
                risk_level="HIGH",
                description="",
                migration_action="",
                secret_server_equivalent="",
                language="Python"
            ),
            ScanMatch(
                file_path="test.py",
                line_number=3,
                line_content="test",
                pattern_name="TEST3",
                pattern_type="test",
                risk_level="MEDIUM",
                description="",
                migration_action="",
                secret_server_equivalent="",
                language="Python"
            ),
        ]

        summary = generate_summary(matches, 5, "/test")

        assert summary.high_risk_count == 2
        assert summary.medium_risk_count == 1
        assert summary.low_risk_count == 0
        assert summary.total_matches == 3
        assert summary.files_with_matches == 1


class TestMatchDataclass:
    """Test ScanMatch dataclass."""

    def test_match_has_all_fields(self):
        """ScanMatch should have all required fields."""
        from ccp_code_scanner import ScanMatch

        match = ScanMatch(
            file_path="/test/file.py",
            line_number=42,
            line_content="AppID = 'test'",
            pattern_name="CCP_APPID",
            pattern_type=r"AppID\s*[=:]\s*",
            risk_level="HIGH",
            description="CyberArk Application ID",
            migration_action="Replace with OAuth2",
            secret_server_equivalent="client_id",
            language="Python"
        )

        assert match.file_path == "/test/file.py"
        assert match.line_number == 42
        assert match.risk_level == "HIGH"


class TestIntegration:
    """Integration tests using real scanner workflow."""

    @pytest.fixture
    def fixtures_path(self):
        return Path(__file__).parent / "fixtures"

    def test_full_scan_workflow(self, fixtures_path, tmp_path):
        """Test complete scan → summary → output workflow."""
        matches, files_scanned = scan_directory(fixtures_path)
        summary = generate_summary(matches, files_scanned, str(fixtures_path))

        # Verify summary
        assert summary.total_files_scanned == files_scanned
        assert summary.total_matches == len(matches)
        assert summary.high_risk_count > 0, "Should find high-risk patterns"

        # Verify we found patterns across multiple languages
        languages = set(m.language for m in matches)
        assert "Python" in languages
        assert "PowerShell" in languages
        assert "C#" in languages

    def test_scan_identifies_all_expected_patterns(self, fixtures_path):
        """Verify all expected pattern types are detected."""
        matches, _ = scan_directory(fixtures_path)

        pattern_names = {m.pattern_name for m in matches}

        # Core patterns that should be found
        expected = {
            "CCP_APPID",
            "CCP_SAFE_REFERENCE",
            "CCP_OBJECT_REFERENCE",
            "CCP_REST_ENDPOINT",
            "CONFIG_CYBERARK_URL",
            "DOTNET_CYBERARK_SDK",
            "DOTNET_PASSWORD_REQUEST",
            "POWERSHELL_PSPAS",
        }

        missing = expected - pattern_names
        assert len(missing) == 0, f"Missing patterns: {missing}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
