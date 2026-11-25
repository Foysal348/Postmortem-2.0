"""
Data models for PostMortem 2.0.

This module defines the typed Pydantic models that represent every data structure
in the system: dependency graphs, conflicts, advisories, evidence, and operations.

The NodeStatus enum is the linchpin for the "Unknown is never green" principle (R2.11, R3.3):
it is a closed enum, making "Unknown and healthy" unrepresentable at the type level.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Annotated, Literal, Optional, Union

from packaging.version import Version
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, BeforeValidator


def parse_version(v: Any) -> Version:
    """Parse a version from string or Version object."""
    if isinstance(v, Version):
        return v
    return Version(str(v))


# Annotated type for Version that handles both serialization and deserialization
VersionField = Annotated[Version, BeforeValidator(parse_version)]


class EvidenceSource(str, Enum):
    """
    Enum of valid sources for evidence.

    Every dependency edge, finding, and operation carries an Evidence record
    identifying where the data came from, ensuring traceability (R2.4, R5).
    """

    PYPI_JSON = "pypi-json"
    """The package metadata came from PyPI's release JSON /info.requires_dist field."""

    WHEEL_METADATA = "wheel-metadata"
    """The package metadata came from reading the wheel's .dist-info/METADATA file."""

    OSV = "osv"
    """The finding came from an OSV record."""

    PIP_REPORT = "pip-report"
    """The resolver outcome came from a pip install --report JSON."""

    UNKNOWN = "unknown"
    """The metadata could not be recovered (no wheel, unreachable, not found, etc)."""


class NodeStatus(str, Enum):
    """
    Closed enum of package node statuses.

    This is a closed enum (all members are listed; no new members can be added)
    to enforce R2.11 and R3.3: an Unknown node is structurally distinct from a
    healthy node. The type system prevents "Unknown and healthy" from existing.

    - UNKNOWN: metadata not recovered (unpinned, not found, unreachable, no wheel, etc.)
    - HEALTHY: pinned, metadata recovered, no conflicts, no known vulnerabilities
    - CONFLICT: involved in a version conflict
    - VULNERABLE: has known OSV findings
    """

    UNKNOWN = "unknown"
    """
    Metadata not recovered or node is unpinned (R1.6, R2.3, R2.7, R2.8, R2.9).
    Never assigned HEALTHY status (R2.11, R3.3, P6).
    """

    HEALTHY = "healthy"
    """Pinned, metadata recovered, no conflicts, no OSV findings."""

    CONFLICT = "conflict"
    """Involved in a detected version conflict (R4.1)."""

    VULNERABLE = "vulnerable"
    """Has one or more known OSV findings (R5)."""


class Evidence(BaseModel):
    """
    Record of the source and fetch time for a dependency edge, finding, or node.

    Satisfies R2.4: every edge and finding carries evidence identifying its source,
    URL, and fetch timestamp. The source enum ensures traceability and prevents
    invalid sources from being created.
    """

    source: EvidenceSource = Field(
        ..., description="Source of this data: pypi-json, wheel-metadata, osv, pip-report, or unknown"
    )
    url: Optional[str] = Field(
        default=None,
        description="URL from which this data was fetched (None for synthetic/unknown sources)",
    )
    fetched_at: datetime = Field(
        ..., description="Timestamp when this data was fetched (or generated)"
    )


class PackageNode(BaseModel):
    """
    A node in the declared dependency graph (a package).

    Represents a single package in the manifest or discovered transitively.
    Carries its canonical name, version pinning status, metadata recovery status,
    and evidence source.

    Satisfies R1.4 (normalized names), R1.6 (unpinned marking), R2.11 (Unknown ≠ Healthy),
    and R3.3 (status assignment).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(
        ...,
        description="Unique identifier for this node: the canonical PEP 503 normalized name",
    )
    canonical_name: str = Field(
        ..., description="PEP 503 normalized package name (e.g. 'Flask' normalizes to 'flask')"
    )
    requested_spec: str = Field(
        ...,
        description="The original specifier text from the manifest or declared dependency edge",
    )
    pinned: bool = Field(
        ...,
        description="True iff the requirement is an exact pin (single == clause); R1.6",
    )
    pinned_version: Optional[VersionField] = Field(
        default=None,
        description="The pinned version if pinned=True, else None. Used for conflict checking.",
    )
    is_root: bool = Field(
        ..., description="True if this package was listed in the original manifest (a root)"
    )
    status: NodeStatus = Field(
        ...,
        description="The package's overall status: healthy, conflict, vulnerable, or unknown (R3.3, R2.11)",
    )
    unknown_reason: Optional[str] = Field(
        default=None,
        description="If status=unknown, a human-readable reason (e.g. 'not found on PyPI', 'PyPI timeout', 'no wheel')",
    )
    evidence: Optional[Evidence] = Field(
        default=None,
        description="Evidence for this node's metadata (source, URL, fetch time). None if synthetic or never fetched.",
    )

    @field_serializer("pinned_version", when_used="json")
    def serialize_version(self, value: Optional[Version]) -> Optional[str]:
        """Serialize Version to string for JSON output."""
        return str(value) if value else None


class DependencyEdge(BaseModel):
    """
    An edge in the declared dependency graph: 'source package requires target package'.

    Represents a single dependency requirement. Carries the specifier that the source
    package declares, the marker guarding the requirement, whether the marker applied
    in the target environment, and the evidence source.

    Satisfies R2.1-R2.4 (metadata edges with evidence), R3.1 (marker evaluation),
    and R4.1 (specifier for conflict detection).
    """

    source: str = Field(
        ..., description="Canonical name of the package that declares this requirement"
    )
    target: str = Field(
        ...,
        description="Canonical name of the package required by source",
    )
    specifier: str = Field(
        ...,
        description="The version specifier declared by source (e.g. '<1.24,>=1.21.1')",
    )
    marker: Optional[str] = Field(
        default=None,
        description="PEP 508 marker guarding this requirement (e.g. 'python_version>=\"3.6\"'), or None if unconditional",
    )
    marker_applies: bool = Field(
        ...,
        description="Whether the marker evaluated true in the target environment (CPython 3.12, Linux x86_64)",
    )
    evidence: Evidence = Field(
        ...,
        description="Evidence for this edge's source (pypi-json, wheel-metadata, etc.)",
    )


class Conflict(BaseModel):
    """
    A version conflict: requirer declares a specifier that the pinned version violates.

    When package A requires B with specifier S, and B is pinned to version V,
    but V does not satisfy S, a Conflict record is created. Used to highlight
    torn arteries in the UI and to identify problematic version choices.

    Satisfies R4.1: conflict with requirer, required, specifier, pinned version, and evidence.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    requirer: str = Field(
        ...,
        description="Canonical name of the package that declares the requirement (source of edge)",
    )
    required: str = Field(
        ..., description="Canonical name of the required package (target of edge)"
    )
    specifier: str = Field(
        ...,
        description="The specifier declared by requirer (e.g. '<1.24,>=1.21.1')",
    )
    pinned_version: VersionField = Field(
        ...,
        description="The pinned version of required that violates the specifier",
    )
    evidence: Evidence = Field(
        ...,
        description="Evidence for this conflict (source of the edge's requirement)",
    )

    @field_serializer("pinned_version", when_used="json")
    def serialize_version(self, value: Version) -> str:
        """Serialize Version to string for JSON output."""
        return str(value)


class Advisory(BaseModel):
    """
    A single advisory from OSV: a vulnerability record with aliases and severity.

    Represents one OSV record (identified by osv_id) and its metadata: aliases
    (CVE, GHSA, PYSEC identifiers for the same underlying vulnerability),
    modification time, and severity.

    Satisfies R5.1 (OSV id + aliases), R5.3/R5.5 (severity label), R5.6 (severity source).
    """

    osv_id: str = Field(
        ..., description="The primary OSV ID for this advisory (e.g. 'PYSEC-2024-123')"
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alias IDs for the same vulnerability (CVE, GHSA, PYSEC identifiers)",
    )
    modified_at: datetime = Field(
        ..., description="Timestamp of the last modification to this record"
    )
    severity_label: str = Field(
        ...,
        description="Severity label derived from database_specific.severity or CVSS score (LOW, MODERATE, HIGH, CRITICAL, or 'severity unknown')",
    )
    severity_source: str = Field(
        ...,
        description="Which field provided the severity: 'database_specific.severity', 'cvss', or 'none'",
    )
    url: str = Field(..., description="URL to the full advisory record on the OSV site")


class Finding(BaseModel):
    """
    A deduplicated OSV finding: groups all records that alias to the same vulnerability.

    After OSV deduplication, records sharing any alias ID are collapsed into one finding.
    The finding preserves all raw IDs in the equivalence class and stores the advisory
    records (which should be treated as equivalent).

    Satisfies R5.2: raw vs dedup count, and P8 (alias deduplication).
    """

    ids: list[str] = Field(
        ...,
        description="All raw OSV IDs in this equivalence class (the finding's id plus all its aliases)",
    )
    advisories: list[Advisory] = Field(
        ...,
        description="Advisory records for this finding (usually one; multiple if multiple APIs returned data)",
    )
    severity_label: str = Field(
        ...,
        description="Severity label (from the dedup'd advisories)",
    )
    severity_source: str = Field(
        ...,
        description="Which field provided the severity (from the dedup'd advisories)",
    )


class Operation(BaseModel):
    """
    A dependency modification operation to be simulated: remove_pin, force_remove, or set_pin.

    Represents a single change the user wishes to test before modifying their repo.
    Used by the simulation worker (R7, P1 — deferred).

    Satisfies R7.1: operation kinds.
    """

    kind: Literal["remove_pin", "force_remove", "set_pin"] = Field(
        ...,
        description="The type of operation: 'remove_pin' (delete the line), 'force_remove' (remove from graph), or 'set_pin' (change the specifier)",
    )
    package: str = Field(
        ..., description="Canonical name of the package to operate on"
    )
    new_spec: Optional[str] = Field(
        default=None,
        description="For set_pin, the new specifier to use (e.g. '==1.21.1'); None for other kinds",
    )


class ResolutionResult(BaseModel):
    """
    Outcome of a simulated resolver run: success or failure with error message.

    Returned by the pip dry-run worker (R7, P1 — deferred). Carries the resolver's
    determination of whether the constraints are satisfiable, the resolved versions,
    the target environment, and an honest label about what was tested.

    Satisfies R7.2-R7.4: isolation, resolved versions, error message, label.
    """

    ok: bool = Field(
        ...,
        description="True iff the resolver succeeded (constraints are satisfiable)",
    )
    resolved: Optional[dict[str, str]] = Field(
        default=None,
        description="If ok=True: map of canonical package names to resolved versions. If ok=False: None.",
    )
    error: Optional[str] = Field(
        default=None,
        description="If ok=False: the resolver's conflict message describing why resolution failed",
    )
    environment: dict[str, str] = Field(
        default_factory=dict,
        description="PEP 508 marker environment that was used for resolution (Python version, platform, etc.)",
    )
    raw_report_path: Optional[str] = Field(
        default=None,
        description="Path to the raw pip install --report JSON (for detailed investigation)",
    )
    label: str = Field(
        ...,
        description="Human-readable label: 'Constraints satisfied - runtime not tested' on success; error message on failure",
    )


class SurgeryReport(BaseModel):
    """
    Exported surgical report: findings, graph structure, and all evidence.

    Produced by the report exporter (R8, P1 — deferred). Contains every finding,
    every dependency edge, all unknown nodes, and all evidence records so the report
    is complete, deduplicated, and allows offline review.

    Satisfies R8.1: every finding + evidence + unknowns.
    """

    patient_id: str = Field(..., description="UUID of the patient (session) this report describes")
    findings: list[Finding] = Field(
        ...,
        description="All OSV findings for all packages in the declared graph",
    )
    edges: list[DependencyEdge] = Field(
        ...,
        description="All dependency edges in the declared graph",
    )
    unknowns: list[PackageNode] = Field(
        ...,
        description="All nodes whose metadata is unknown (unpinned, not found, unreachable, etc.)",
    )
    evidence: list[Evidence] = Field(
        ...,
        description="All evidence records (deduplicated) used in findings and edges",
    )
    timestamp: datetime = Field(
        ..., description="When this report was exported"
    )


class ValidationError(BaseModel):
    """
    A validation error raised during manifest parsing.

    Recorded per-line during validation (R1). Carries the line number where the error
    occurred (or None for file-level errors like size/line count), a human-readable
    message, and a reason code for programmatic handling.

    Satisfies R1.1-R1.6: rejection reasons include byte_size_exceeded, line_count_exceeded,
    pip_option, url_not_allowed, parse_error, and duplicate.
    """

    line_number: Optional[int] = Field(
        default=None,
        description="Line number where the error occurred (0-indexed), or None for file-level errors",
    )
    message: str = Field(
        ...,
        description="Human-readable error message (e.g. 'Line 3: invalid requirement: unexpected character')",
    )
    reason: str = Field(
        ...,
        description="Machine-readable reason code: byte_size_exceeded, line_count_exceeded, pip_option, url_not_allowed, parse_error, or duplicate",
    )


class ParsedRequirement(BaseModel):
    """
    A successfully parsed requirement from the manifest.

    Represents a single requirement line after validation and normalization,
    carrying the canonical name, extras, specifier, marker, and pinning status.
    Used as input to the metadata recovery and graph-building stages.

    Satisfies R1.1-R1.6: normalized name (R1.4), pinning check (R1.6), duplicate
    detection input (R1.5), and preservation of raw line and line number for error reporting.
    """

    canonical_name: str = Field(
        ...,
        description="PEP 503 normalized package name (e.g. 'Flask' normalizes to 'flask')",
    )
    extras: list[str] = Field(
        default_factory=list,
        description="List of requested extras (e.g. ['dev', 'security'])",
    )
    specifier: str = Field(
        ...,
        description="Version specifier string (e.g. '==1.2.3', '>=1.0,<2', or empty string for bare name)",
    )
    marker: Optional[str] = Field(
        default=None,
        description="PEP 508 environment marker (e.g. 'python_version>=\"3.6\"'), or None if unconditional",
    )
    pinned: bool = Field(
        ...,
        description="True iff the specifier is an exact pin (single '==' clause), per R1.6",
    )
    raw_line: str = Field(
        ..., description="The original requirement line from the manifest (for display/error reporting)"
    )
    line_number: int = Field(
        ..., description="0-indexed line number in the manifest"
    )


class ValidationResult(BaseModel):
    """
    Result of validating a requirements manifest.

    Produced by validate_manifest() (R1). Contains the list of successfully parsed
    requirements, any validation errors encountered, and a flag indicating whether
    the file was rejected entirely (size/line count limits).

    Satisfies R1.1-R1.6: acceptance criteria for input validation.
    """

    requirements: list[ParsedRequirement] = Field(
        default_factory=list,
        description="Successfully parsed and validated requirements",
    )
    errors: list[ValidationError] = Field(
        default_factory=list,
        description="Validation errors encountered during parsing (parse errors, duplicates, dangerous constructs)",
    )
    rejected: bool = Field(
        default=False,
        description="True if the file was rejected entirely (exceeds byte size or line count limits)",
    )
