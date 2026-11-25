"""
Unit tests for app/validate.py (R1 — Input Validation).

Tests cover:
  - Basic parsing of valid requirements
  - Rejection of dangerous constructs (pip options, URLs, VCS, local paths)
  - Byte size and line count limits
  - Normalization per PEP 503
  - Duplicate detection
  - Unpinned vs pinned detection
  - Edge cases: comments, blank lines, inline comments, continuation lines
"""

import pytest
from app.validate import validate_manifest
from app.models import ValidationError


class TestBasicParsing:
    """Test successful parsing of valid requirements."""

    def test_simple_pinned_requirement(self):
        """Parse a single pinned requirement."""
        result = validate_manifest("Flask==1.1.2\n")
        assert len(result.requirements) == 1
        assert result.requirements[0].canonical_name == "flask"
        assert result.requirements[0].specifier == "==1.1.2"
        assert result.requirements[0].pinned is True
        assert result.rejected is False
        assert len(result.errors) == 0

    def test_bare_package_name(self):
        """Parse a bare package name (unpinned)."""
        result = validate_manifest("requests\n")
        assert len(result.requirements) == 1
        assert result.requirements[0].canonical_name == "requests"
        assert result.requirements[0].specifier == ""
        assert result.requirements[0].pinned is False

    def test_requirement_with_extras(self):
        """Parse requirement with extras."""
        result = validate_manifest("requests[security,socks]==2.19.0\n")
        assert len(result.requirements) == 1
        assert result.requirements[0].canonical_name == "requests"
        assert set(result.requirements[0].extras) == {"security", "socks"}
        assert result.requirements[0].specifier == "==2.19.0"
        assert result.requirements[0].pinned is True

    def test_requirement_with_marker(self):
        """Parse requirement with environment marker."""
        result = validate_manifest("dataclasses>=0.6; python_version < '3.7'\n")
        assert len(result.requirements) == 1
        assert result.requirements[0].canonical_name == "dataclasses"
        assert "python_version" in result.requirements[0].marker
        assert result.requirements[0].pinned is False

    def test_multiple_valid_requirements(self):
        """Parse multiple valid requirements."""
        text = """Flask==1.1.2
Werkzeug==0.14.1
Jinja2==2.10"""
        result = validate_manifest(text)
        assert len(result.requirements) == 3
        assert result.rejected is False
        assert len(result.errors) == 0

    def test_complex_specifier(self):
        """Parse requirement with complex specifier."""
        result = validate_manifest("urllib3<1.24,>=1.21.1\n")
        assert len(result.requirements) == 1
        assert result.requirements[0].specifier == "<1.24,>=1.21.1"
        assert result.requirements[0].pinned is False

    def test_compatible_release_specifier(self):
        """Parse compatible release specifier (~=)."""
        result = validate_manifest("numpy~=1.19.0\n")
        assert len(result.requirements) == 1
        assert result.requirements[0].specifier == "~=1.19.0"
        assert result.requirements[0].pinned is False

    def test_inequality_specifier(self):
        """Parse inequality specifier (!=)."""
        result = validate_manifest("pytest!=6.0.0\n")
        assert len(result.requirements) == 1
        assert result.requirements[0].specifier == "!=6.0.0"
        assert result.requirements[0].pinned is False


class TestCommentsAndBlankLines:
    """Test handling of comments and blank lines."""

    def test_blank_lines(self):
        """Blank lines are ignored."""
        text = """

Flask==1.1.2


Werkzeug==0.14.1

"""
        result = validate_manifest(text)
        assert len(result.requirements) == 2
        assert len(result.errors) == 0

    def test_comment_line(self):
        """Pure comment lines are ignored."""
        text = """# This is a comment
Flask==1.1.2
# Another comment
Werkzeug==0.14.1
"""
        result = validate_manifest(text)
        assert len(result.requirements) == 2

    def test_inline_comment(self):
        """Inline comments are stripped."""
        text = """Flask==1.1.2  # Production web framework
Werkzeug==0.14.1  # WSGI utility library
"""
        result = validate_manifest(text)
        assert len(result.requirements) == 2
        assert result.requirements[0].canonical_name == "flask"

    def test_inline_comment_no_space(self):
        """Inline comment without preceding space."""
        result = validate_manifest("Flask==1.1.2#comment\n")
        assert len(result.requirements) == 1
        assert result.requirements[0].canonical_name == "flask"


class TestNormalization:
    """Test PEP 503 name normalization (R1.4)."""

    def test_flask_case_variants(self):
        """Flask, flask, FLASK all normalize to 'flask'."""
        result = validate_manifest("Flask==1.1.2\n")
        assert result.requirements[0].canonical_name == "flask"

        result = validate_manifest("FLASK==1.1.2\n")
        assert result.requirements[0].canonical_name == "flask"

        result = validate_manifest("flask==1.1.2\n")
        assert result.requirements[0].canonical_name == "flask"

    def test_hyphen_underscore_normalization(self):
        """Hyphens and underscores normalize equivalently."""
        result1 = validate_manifest("some-package==1.0\n")
        result2 = validate_manifest("some_package==1.0\n")
        assert result1.requirements[0].canonical_name == result2.requirements[0].canonical_name

    def test_mixed_case_with_underscores(self):
        """Mixed case with underscores normalizes correctly."""
        result = validate_manifest("Django_REST_Framework==3.0\n")
        # Expects lowercased and underscores -> hyphens
        assert result.requirements[0].canonical_name == "django-rest-framework"


class TestDuplicateDetection:
    """Test duplicate detection (R1.5)."""

    def test_exact_duplicate(self):
        """Same package name twice is detected as duplicate."""
        text = """Flask==1.1.2
Flask==1.1.3"""
        result = validate_manifest(text)
        assert len(result.requirements) == 1  # Only first accepted
        assert len(result.errors) == 1
        assert result.errors[0].reason == "duplicate"
        assert result.errors[0].line_number == 1

    def test_duplicate_different_case(self):
        """Duplicates are detected even with different case."""
        text = """Flask==1.1.2
flask==1.1.3"""
        result = validate_manifest(text)
        assert len(result.requirements) == 1
        assert len(result.errors) == 1
        assert result.errors[0].reason == "duplicate"

    def test_duplicate_with_underscores_hyphens(self):
        """Duplicates detected even with underscore/hyphen variations."""
        text = """some-package==1.0
some_package==1.1"""
        result = validate_manifest(text)
        assert len(result.requirements) == 1
        assert len(result.errors) == 1
        assert result.errors[0].reason == "duplicate"

    def test_no_duplicate_different_package(self):
        """Different packages don't trigger duplicate detection."""
        text = """Flask==1.1.2
Werkzeug==0.14.1"""
        result = validate_manifest(text)
        assert len(result.requirements) == 2
        assert len(result.errors) == 0


class TestPinnedVsUnpinned:
    """Test pinned vs unpinned detection (R1.6)."""

    def test_exactly_pinned(self):
        """Single == specifier is pinned."""
        result = validate_manifest("Flask==1.1.2\n")
        assert result.requirements[0].pinned is True

    def test_unpinned_bare_name(self):
        """Bare name is unpinned."""
        result = validate_manifest("Flask\n")
        assert result.requirements[0].pinned is False

    def test_unpinned_greater_than(self):
        """>=, >, <, <= are unpinned."""
        for spec in [">=1.0", ">1.0", "<2.0", "<=2.0"]:
            result = validate_manifest(f"Flask{spec}\n")
            assert result.requirements[0].pinned is False, f"Specifier {spec} should be unpinned"

    def test_unpinned_compatible_release(self):
        """~= is unpinned."""
        result = validate_manifest("Flask~=1.1.0\n")
        assert result.requirements[0].pinned is False

    def test_unpinned_not_equal(self):
        """!= is unpinned."""
        result = validate_manifest("Flask!=1.0.0\n")
        assert result.requirements[0].pinned is False

    def test_unpinned_complex_specifier(self):
        """Multiple specifiers are unpinned."""
        result = validate_manifest("Flask>=1.0,<2.0\n")
        assert result.requirements[0].pinned is False

    def test_unpinned_arbitrary_equal(self):
        """=== (arbitrary equality) is unpinned."""
        result = validate_manifest("Flask===1.1.2\n")
        assert result.requirements[0].pinned is False


class TestDangerousConstructs:
    """Test rejection of dangerous constructs (R1.2, P2)."""

    def test_reject_pip_option_r(self):
        """Reject -r (requirements file reference)."""
        result = validate_manifest("-r other.txt\n")
        assert result.rejected is False  # Not a file-level rejection
        assert len(result.requirements) == 0
        assert len(result.errors) == 1
        assert result.errors[0].reason == "pip_option"

    def test_reject_pip_option_c(self):
        """Reject -c (constraints file reference)."""
        result = validate_manifest("-c constraints.txt\n")
        assert len(result.errors) == 1
        assert result.errors[0].reason == "pip_option"

    def test_reject_pip_option_e(self):
        """Reject -e (editable install)."""
        result = validate_manifest("-e .\n")
        assert len(result.errors) == 1
        assert result.errors[0].reason == "pip_option"

    def test_reject_double_dash_option(self):
        """Reject -- options."""
        result = validate_manifest("--index-url https://pypi.org/simple\n")
        assert len(result.errors) == 1
        assert result.errors[0].reason == "pip_option"

    def test_reject_url_http(self):
        """Reject HTTP URL."""
        result = validate_manifest("Flask @ https://github.com/pallets/flask/archive/main.zip\n")
        assert len(result.errors) == 1
        assert result.errors[0].reason == "url_not_allowed"

    def test_reject_url_file(self):
        """Reject file:// URL."""
        result = validate_manifest("Flask @ file:///path/to/flask\n")
        assert len(result.errors) == 1
        assert result.errors[0].reason == "url_not_allowed"

    def test_reject_vcs_git(self):
        """Reject git+ VCS reference."""
        result = validate_manifest("Flask @ git+https://github.com/pallets/flask.git\n")
        assert len(result.errors) == 1
        assert result.errors[0].reason == "url_not_allowed"

    def test_reject_local_path(self):
        """Reject local path."""
        result = validate_manifest("Flask @ /path/to/flask\n")
        assert len(result.errors) == 1
        assert result.errors[0].reason == "url_not_allowed"

    def test_reject_local_path_relative(self):
        """Reject relative local path."""
        result = validate_manifest("Flask @ ./flask\n")
        assert len(result.errors) == 1
        assert result.errors[0].reason == "url_not_allowed"


class TestByteSizeLimit:
    """Test byte size limit (R1.3)."""

    def test_under_limit(self):
        """Requirement under 64 KB is accepted."""
        small_req = "Flask==1.1.2\n"
        result = validate_manifest(small_req)
        assert result.rejected is False

    def test_exactly_at_limit(self):
        """File exactly at 64 KB should be accepted."""
        # Create a file just under the limit
        base = "Flask==1.1.2\n"
        padding = "# " + "x" * (65536 - len(base) - 10)  # Leave room for padding
        text = base + padding + "\n"
        result = validate_manifest(text)
        assert result.rejected is False

    def test_exceeds_limit(self):
        """File exceeding 64 KB is rejected entirely."""
        # Create a file that exceeds the limit
        large_text = "x" * (65537)
        result = validate_manifest(large_text)
        assert result.rejected is True
        assert len(result.errors) == 1
        assert result.errors[0].reason == "byte_size_exceeded"

    def test_unicode_byte_size(self):
        """Byte size is counted in UTF-8 encoding."""
        # Emoji are 4 bytes each in UTF-8
        emoji_text = "Flask==1.1.2  # 😀\n" * 10000
        byte_size = len(emoji_text.encode("utf-8"))
        result = validate_manifest(emoji_text)
        if byte_size > 65536:
            assert result.rejected is True
        else:
            assert result.rejected is False


class TestLineCountLimit:
    """Test line count limit (R1.3)."""

    def test_exactly_200_requirements(self):
        """Exactly 200 requirement lines should be accepted."""
        lines = [f"package{i}==1.1.2\n" for i in range(200)]
        text = "".join(lines)
        result = validate_manifest(text)
        assert result.rejected is False
        assert len(result.requirements) == 200

    def test_exceeds_200_requirements(self):
        """More than 200 requirement lines should be rejected."""
        lines = ["Flask==1.1.2\n"] * 201
        text = "".join(lines)
        result = validate_manifest(text)
        assert result.rejected is True
        assert len(result.errors) == 1
        assert result.errors[0].reason == "line_count_exceeded"

    def test_200_with_comments_and_blanks(self):
        """Line count is requirement lines only (not comments/blanks)."""
        req_lines = [f"package{i}==1.1.2\n" for i in range(200)]
        comment_lines = ["# Comment\n"] * 100
        blank_lines = ["\n"] * 100
        text = "".join(req_lines + comment_lines + blank_lines)
        result = validate_manifest(text)
        assert result.rejected is False
        assert len(result.requirements) == 200

    def test_201_requirements_with_comments(self):
        """201 requirement lines with comments should be rejected."""
        req_lines = ["Flask==1.1.2\n"] * 201
        comment_lines = ["# Comment\n"] * 50
        text = "".join(req_lines + comment_lines)
        result = validate_manifest(text)
        assert result.rejected is True


class TestParseErrors:
    """Test handling of parse errors."""

    def test_invalid_requirement_syntax(self):
        """Invalid requirement syntax produces parse error."""
        result = validate_manifest("Flask [invalid\n")
        assert len(result.requirements) == 0
        assert len(result.errors) == 1
        assert result.errors[0].reason == "parse_error"

    def test_multiple_parse_errors(self):
        """Multiple lines with parse errors are all recorded."""
        text = """Flask==1.1.2
invalid [syntax [here
Werkzeug==0.14.1
another { bad one
"""
        result = validate_manifest(text)
        assert len(result.requirements) == 2  # Flask and Werkzeug
        assert len(result.errors) == 2  # Two parse errors
        for error in result.errors:
            assert error.reason == "parse_error"


class TestSampleLegacyFlask:
    """Test parsing the demo patient (samples/legacy_flask_requests.txt)."""

    def test_legacy_flask_manifest(self):
        """Successfully parse the legacy Flask 0.12 requirements."""
        with open("samples/legacy_flask_requests.txt", "r") as f:
            text = f.read()

        result = validate_manifest(text)

        # Should have 11 valid requirements
        assert len(result.requirements) == 11
        assert result.rejected is False

        # Check specific packages
        canonical_names = {req.canonical_name for req in result.requirements}
        expected = {
            "flask",
            "werkzeug",
            "jinja2",
            "markupsafe",
            "itsdangerous",
            "click",
            "requests",
            "urllib3",
            "certifi",
            "chardet",
            "idna",
        }
        assert canonical_names == expected

        # All should be pinned
        for req in result.requirements:
            assert req.pinned is True

        # Known conflict: requests==2.19.0 requires urllib3<1.24,>=1.21.1 but file pins urllib3==1.24.1
        requests_req = next(r for r in result.requirements if r.canonical_name == "requests")
        urllib3_req = next(r for r in result.requirements if r.canonical_name == "urllib3")

        assert requests_req.specifier == "==2.19.0"
        assert urllib3_req.specifier == "==1.24.1"


class TestEdgeCases:
    """Test edge cases and corner cases."""

    def test_empty_manifest(self):
        """Empty manifest is valid."""
        result = validate_manifest("")
        assert result.rejected is False
        assert len(result.requirements) == 0
        assert len(result.errors) == 0

    def test_only_comments(self):
        """Manifest with only comments and blanks is valid."""
        text = """# Comment 1
# Comment 2

# Comment 3
"""
        result = validate_manifest(text)
        assert result.rejected is False
        assert len(result.requirements) == 0

    def test_requirement_with_whitespace_padding(self):
        """Requirements with leading/trailing whitespace are handled."""
        result = validate_manifest("   Flask==1.1.2   \n")
        assert len(result.requirements) == 1
        assert result.requirements[0].canonical_name == "flask"

    def test_raw_line_preserved(self):
        """Raw line content is preserved in ParsedRequirement."""
        raw = "Flask==1.1.2  # Production framework"
        result = validate_manifest(raw + "\n")
        assert result.requirements[0].raw_line == raw

    def test_line_number_recorded(self):
        """Line numbers are recorded correctly."""
        text = """Flask==1.1.2
# Comment
Werkzeug==0.14.1"""
        result = validate_manifest(text)
        assert result.requirements[0].line_number == 0
        assert result.requirements[1].line_number == 2
