# PostMortem 2.0 - Non-Negotiable Principles

These four principles are non-negotiable. Every feature and claim must satisfy them.

1. **Evidence over assumptions.** Every claim shows its source (PyPI JSON, wheel METADATA, OSV record id, pip report).
2. **Simulation over promises.** A resolver success means *constraints are satisfiable*, never "your app will run".
3. **Unknown is never green.** Missing metadata is shown as unknown fog, never as healthy.
4. **Decoration serves decision.** Every visual effect encodes data (severity, conflict, uncertainty).

## Strict definitions
| Term | Meaning |
|---|---|
| Declared graph | Built from the manifest + package metadata. May be partial or contradictory. |
| Resolved graph | One package selection pip accepted for a recorded target environment. Not proof the app runs. |
| Remove Pin | Delete a line and re-resolve; the package may come back transitively. |
| Force Remove | Hypothetical removal from a graph; shows which packages declare it as a requirement. |
| Constraint pass | Resolver success only. |
| Unknown | No reliable metadata / evidence. |
| Known OSV finding | An OSV record that matches this package+version. Not proof of exploitability. |
| Time since last release | A date interval. Not proof of abandonment. |

Never conflate these. A "constraint pass" is not "the app runs". A "known OSV finding" is not "exploitable". "Time since last release" is not "dead". Label uncertainty explicitly rather than implying certainty.
