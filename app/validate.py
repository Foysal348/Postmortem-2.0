"""
Input Validation Module (R1) — Requirement 1: Input Validation

Validates a requirements manifest against a strict PEP 508 subset, rejects dangerous
constructs, enforces size and line count limits, normalizes names per PEP 503,
detects duplicates, and flags unpinned requirements.

The function validate_manifest() is pure: it takes a string and returns a typed result.
No I/O, no exceptions beyond programming errors.

Traceability:
  - R1.1: Accept only `name[extras] specifier [; marker]` with comments and blank lines
  - R1.2: Reject lines with `-r`, `-c`, `-e`, `--` options, URLs, VCS, local paths
  - R1.3: Reject files exceeding 64 KB or 200 requirement lines
  - R1.4: Normalize names per PEP 503 (Flask -> flask)
  - R1.5: Detect duplicate canonical names
  - R1.6: Mark non-exact pins (`!=`, `~=`, `>=`, bare name) as unpinned
  - P1: Name normalization is idempotent: norm(norm(x)) == norm(x)
  - P2: Validator never accepts a line with URL, path, or pip option
"""

from packaging.requirements import Requirement, InvalidRequirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from app.models import ValidationResult, ParsedRequirement, ValidationError


def validate_manifest(text: str) -> ValidationResult:
    """
    Validate a requirements manifest against the strict PEP 508 subset.

    Processing order:
      1. Byte size check (R1.3): reject if > 64 KB
      2. Line count check (R1.3): reject if > 200 non-comment, non-blank lines
      3. Per-line processing (R1.1, R1.2):
         - Strip inline comments (at first unquoted #)
         - Reject lines starting with `-` (pip options)
         - Parse with packaging.requirements.Requirement
         - Reject if parsed .url is non-None (URL/VCS/path)
      4. Normalize (R1.4): canonicalize_name per PEP 503
      5. Duplicate detection (R1.5): track by canonical name
      6. Unpinned detection (R1.6): check for single == specifier

    Args:
        text: The requirements file contents as a string

    Returns:
        ValidationResult with requirements, errors, and rejected flag
    """

    result = ValidationResult()

    # Step 1: Byte size check (R1.3)
    byte_size = len(text.encode("utf-8"))
    if byte_size > 64 * 1024:
        result.rejected = True
        result.errors.append(
            ValidationError(
                line_number=None,
                message=f"File size {byte_size} bytes exceeds limit of 65536 bytes",
                reason="byte_size_exceeded",
            )
        )
        return result

    # Split into lines and count non-comment, non-blank requirement lines
    lines = text.splitlines()
    requirement_line_count = 0
    for line in lines:
        stripped = line.strip()
        # Skip blank lines and pure comments
        if not stripped or stripped.startswith("#"):
            continue
        requirement_line_count += 1

    # Step 2: Line count check (R1.3)
    if requirement_line_count > 200:
        result.rejected = True
        result.errors.append(
            ValidationError(
                line_number=None,
                message=f"Number of requirements ({requirement_line_count}) exceeds limit of 200",
                reason="line_count_exceeded",
            )
        )
        return result

    # Track canonical names for duplicate detection
    seen_canonical_names: dict[str, int] = {}

    # Step 3-6: Per-line processing, normalization, duplicate detection, unpinned detection
    for line_idx, line in enumerate(lines):
        raw_line = line
        stripped = line.strip()

        # Skip blank lines and pure comments (R1.1 allows both)
        if not stripped or stripped.startswith("#"):
            continue

        # Strip inline comments (find first # not inside a quoted string)
        # In PEP 508, strings appear in markers (after semicolon). Package names,
        # specifiers do not contain #. So the first # reliably begins a comment.
        comment_idx = stripped.find("#")
        if comment_idx != -1:
            stripped = stripped[:comment_idx].strip()

        # If comment was the entire line, skip it
        if not stripped:
            continue

        # Dangerous construct rejection: reject lines starting with - (R1.2)
        if stripped.startswith("-"):
            result.errors.append(
                ValidationError(
                    line_number=line_idx,
                    message=f"Line {line_idx}: pip option not allowed: {stripped[:20]}...",
                    reason="pip_option",
                )
            )
            continue

        # Parse the requirement line (R1.1, R1.2)
        try:
            req = Requirement(stripped)
        except InvalidRequirement as e:
            result.errors.append(
                ValidationError(
                    line_number=line_idx,
                    message=f"Line {line_idx}: invalid requirement: {str(e)}",
                    reason="parse_error",
                )
            )
            continue

        # Dangerous construct rejection: reject URL/VCS/local path (R1.2)
        if req.url is not None:
            result.errors.append(
                ValidationError(
                    line_number=line_idx,
                    message=f"Line {line_idx}: URL, VCS, or local path not allowed",
                    reason="url_not_allowed",
                )
            )
            continue

        # Normalize the name (R1.4)
        canonical_name = canonicalize_name(req.name)

        # Duplicate detection (R1.5)
        if canonical_name in seen_canonical_names:
            other_line_idx = seen_canonical_names[canonical_name]
            result.errors.append(
                ValidationError(
                    line_number=line_idx,
                    message=f"Line {line_idx}: duplicate of line {other_line_idx}: {canonical_name}",
                    reason="duplicate",
                )
            )
            continue
        seen_canonical_names[canonical_name] = line_idx

        # Unpinned detection (R1.6)
        # A requirement is exactly pinned iff SpecifierSet contains exactly one specifier with operator "=="
        pinned = (
            len(req.specifier) == 1
            and list(req.specifier)[0].operator == "=="
        )

        # Build ParsedRequirement
        parsed_req = ParsedRequirement(
            canonical_name=canonical_name,
            extras=list(req.extras),  # extras is a frozenset in packaging
            specifier=str(req.specifier),
            marker=str(req.marker) if req.marker else None,
            pinned=pinned,
            raw_line=raw_line,
            line_number=line_idx,
        )

        result.requirements.append(parsed_req)

    return result
