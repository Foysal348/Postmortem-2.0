# PostMortem 2.0 - Schedule, Gates, Demo

All dates 2026, Bangladesh time. Submission deadline: **5 Dec 04:00 BD** (4 Dec 2:00 PM PT). Aim to submit on 4 Dec evening.

| Date | Work |
|---|---|
| 24 Nov | Kiro: steering + spec from `docs/plan`. Project setup, sample patient file. |
| 25 Nov | Validator (R1) + metadata recovery (R2) + tests. |
| 26 Nov | Declared graph + conflicts (R3, R4) + PBT. **Gate 1** |
| 27 Nov | OSV integration (R5) + evidence drawer data. |
| 28 Nov | Force Remove (R6) + autopsy table UI v1. |
| 29 Nov | Isolated resolver + diff (R7). **Gate 2** |
| 30 Nov | Full gothic UI: organs, arteries, fog, heartbeat, animations. |
| 1 Dec | Minimum-Change comparison, report export. Check credit email / ID check. |
| 2 Dec | Deploy. **Feature freeze (Gate 3).** |
| 3 Dec | Bug fixes, README, Kiro write-up, record video, blog post draft. |
| 4 Dec | Publish blog + social post, final checks, submit. |

## Gates
- **Gate 1 (26 Nov):** graph + conflict detection correct on the demo patient? If not, stop new features and fix the core.
- **Gate 2 (29 Nov):** resolver safe and reliable? If not, drop live resolution; show clearly labelled recorded cases.
- **Gate 3 (2 Dec):** no new features after this.

## 3-minute video
| Time | Scene |
|---|---|
| 0:00-0:20 | The problem: a legacy project, a dry wall of pip-audit text nobody reads. |
| 0:20-0:45 | Upload -> the patient appears on the autopsy table. |
| 0:45-1:10 | Click the torn artery: requests 2.19 vs urllib3 1.24.1, with evidence. |
| 1:10-1:50 | Two candidate surgeries, exact diff, real resolver results; "The patient survives". |
| 1:50-2:15 | Fogged organs (Unknown) and OSV before/after - honesty as a feature. |
| 2:15-2:40 | How Kiro built it: spec -> property test caught a bug -> fix. |
| 2:40-2:55 | Value + tagline. |

## Submission checklist
- [ ] Public GitHub repo, MIT license visible in About
- [ ] `/.kiro` at repo root, NOT in .gitignore
- [ ] Working app URL (+ sample file for judges)
- [ ] YouTube video < 3 min, public, no copyrighted music
- [ ] Text description + Kiro usage write-up (use `docs/KIRO_LOG.md`)
- [ ] Student details (LinkedIn, student email, year/degree, school)
- [ ] Blog post URL (mentions Kiroween 2026) - Blog prize
- [ ] Social post starting with `#KiroweenHackathon26` - Social Blitz
