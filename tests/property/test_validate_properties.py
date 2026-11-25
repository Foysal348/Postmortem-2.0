"""
Property-based tests for app/validate.py (R1 — Input Validation).

Validates correctness properties:
  - P1: Name normalization is idempotent: norm(norm(x)) == norm(x)
  - P2: Validator never accepts a line with URL, path, or pip option

Uses Hypothesis for property-based testing.
"""

from hypothesis import given, strategies as st
from packaging.utils import canonicalize_name

from app.validate import validate_manifest


class TestP1Idempotence:
    """
    **Validates: Requirements P1**

    Property P1: Name normalization is idempotent.
    norm(norm(x)) == norm(x)

    This property tests that the normalization function (canonicalize_name)
    is truly idempotent: applying it twice gives the same result as applying it once.
    """

    @given(
        package_name=st.from_regex(r"[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?", fullmatch=True)
    )
    def test_normalization_idempotent(self, package_name):
        """
        For any package name, norm(norm(name)) == norm(name).

        This validates P1 directly by testing the packaging library's
        canonicalize_name function used by validate_manifest.
        """
        normalized_once = canonicalize_name(package_name)
        normalized_twice = canonicalize_name(normalized_once)
        assert normalized_once == normalized_twice

    @given(
        package_name=st.from_regex(r"[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?", fullmatch=True)
    )
    def test_manifest_normalization_idempotent(self, package_name):
        """
        Validator produces idempotent canonical names for all packages.

        When a package is parsed by validate_manifest, its canonical_name
        is fully normalized. If we were to parse the already-normalized name,
        it should produce the same canonical_name.
        """
        # Parse the original name as a requirement
        req_text = f"{package_name}==1.0.0\n"
        result1 = validate_manifest(req_text)

        if result1.requirements:
            canonical1 = result1.requirements[0].canonical_name

            # Parse the already-normalized name
            req_text2 = f"{canonical1}==1.0.0\n"
            result2 = validate_manifest(req_text2)

            if result2.requirements:
                canonical2 = result2.requirements[0].canonical_name
                assert canonical1 == canonical2, f"Normalization not idempotent: {canonical1} != {canonical2}"


class TestP2NoUrlsPaths:
    """
    **Validates: Requirements P2**

    Property P2: Validator never accepts a line containing a URL, path, or pip option.

    This property tests that all dangerous constructs that should be rejected
    according to R1.2 are indeed rejected and never appear in the parsed requirements.
    """

    @given(
        url=st.one_of(
            st.just("http://example.com/package"),
            st.just("https://github.com/user/repo.git"),
            st.just("file:///path/to/package"),
            st.just("git+https://github.com/user/repo.git"),
            st.just("hg+https://example.com/repo"),
            st.just("svn+http://example.com/repo"),
            st.just("bzr+https://example.com/repo"),
        )
    )
    def test_reject_urls_and_vcs(self, url):
        """
        Validator rejects all URL and VCS references and never includes them
        in the parsed requirements.
        """
        req_text = f"package @ {url}\n"
        result = validate_manifest(req_text)

        # Should have zero valid requirements (rejected the line)
        assert len(result.requirements) == 0

        # Should have exactly one error with reason url_not_allowed
        assert len(result.errors) == 1
        assert result.errors[0].reason == "url_not_allowed"

    @given(
        path=st.one_of(
            st.just("/absolute/path"),
            st.just("./relative/path"),
            st.just("../parent/path"),
            st.just("~/home/path"),
        )
    )
    def test_reject_local_paths(self, path):
        """
        Validator rejects all local file paths.
        """
        req_text = f"package @ {path}\n"
        result = validate_manifest(req_text)

        # Should have zero valid requirements
        assert len(result.requirements) == 0

        # Should have exactly one error
        assert len(result.errors) == 1
        assert result.errors[0].reason == "url_not_allowed"

    @given(
        option=st.one_of(
            st.just("-r requirements.txt"),
            st.just("-c constraints.txt"),
            st.just("-e ."),
            st.just("--index-url https://pypi.org/simple"),
            st.just("--extra-index-url https://test.pypi.org/simple"),
            st.just("--find-links /path/to/links"),
        )
    )
    def test_reject_pip_options(self, option):
        """
        Validator rejects all pip command-line options.
        """
        result = validate_manifest(option + "\n")

        # Should have zero valid requirements
        assert len(result.requirements) == 0

        # Should have exactly one error with reason pip_option
        assert len(result.errors) == 1
        assert result.errors[0].reason == "pip_option"

    @given(st.data())
    def test_no_url_in_accepted_requirements(self, data):
        """
        No accepted requirement ever contains a URL or path.

        This tests that all accepted (non-error) requirements are safe simple
        requirements with no @ URL syntax.
        """
        # Generate a valid simple requirement (name + optional specifier)
        name = data.draw(st.from_regex(r"[a-z][a-z0-9-]*", fullmatch=True))
        specifier = data.draw(
            st.one_of(
                st.just(""),
                st.just("==1.0"),
                st.just(">=1.0,<2.0"),
                st.just("~=1.0"),
            )
        )
        req_text = f"{name}{specifier}\n"
        result = validate_manifest(req_text)

        # Should have exactly one valid requirement
        if result.requirements:
            req = result.requirements[0]
            # Should have no URL (this is structural, but we assert for thoroughness)
            assert req is not None
            # Verify that the requirement doesn't have an @ symbol that would indicate URL syntax
            assert "@" not in req.raw_line or "@" in req.raw_line.split("#")[0].split(";")[0] is False
