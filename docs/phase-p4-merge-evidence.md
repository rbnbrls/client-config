# Phase P4 merge evidence — Features 26–30 into main

Date: 2026-11-04 (CET). Executed by @release (gate task t_c0ce14c7).

## Scope and re-scope

Merged reviewed feature commits for Features 26–30 (RPT-001..RPT-005) into `main`
in numeric order, all `--no-ff` via `land-feature.sh`, zero conflicts.

Per Lead re-scope (2026-11-04 18:05): Feature 31 (RPT-006, tip 9cd1d6b on
wt/t_16b132a1) is under independent review and is explicitly out of this gate;
its reviewed branch lands with the Phase P5 gate.

## Authority to merge

Reviewer approvals recorded against the exact branch tip SHA for every feature
(review runs on the kanban board, verified before landing; each tip re-verified
byte-for-byte identical to the approved HEAD at landing time):

| Feature | RPT | Task | Reviewed (approved) HEAD | Merge commit |
|---|---|---|---|---|
| 26 | RPT-001 Rapportagecatalogus | t_73ca1c09 | 2d0fb94 | 6f14538 |
| 27 | RPT-002 Data-aanleverafspraak | t_bc63643b | 0c97504 | 1e8bf6e |
| 28 | RPT-003 SFDR/PAI-profielen | t_bedfa1f8 | 258b723 | a5253fd |
| 29 | RPT-004 Comply-or-explain | t_3c7a4397 | b393ca7 | c5c40f8 |
| 30 | RPT-005 Rapportage-uitvoering | t_67540018 | f6a78d4 | c8d6ab0 |

Base before this gate: main `e9b0a25` — P3 tip `c75ff30` plus the stray
`docs/phase-p3-merge-evidence.md` committed so the gate could accept a clean
`main` (merge-commit SHAs of Features 20–25 backfilled into that doc; commit
`e9b0a25`).

## Verification performed

- `land-feature.sh` gate GREEN in every feature worktree before its merge and
  GREEN on `main` after every merge (logs under `.hermes/team/evidence/`,
  2026-11-04T17:37–17:40Z).
- Post-merge suite progression on `main`: 212 → 219 → 226 → 233 → 241 passed —
  each landing's gate PASS, no rollback needed.
- Tree of merged `main` equals reviewed F30 tip `f6a78d4` byte-for-byte except
  `docs/phase-p3-merge-evidence.md`, which main legitimately added (see above).

## Full suite on merged main

Command: `python3.13 -m pytest -q`
Result: `241 passed in 16.62s` (exit 0).

## Acceptance URL

`http://localhost:8080` — published from the runtime by `local-url.sh`
(state file records `branch: main`, `head: c8d6ab0`), endpoint verified:
`/api/health` HTTP 200, `/` HTTP 200. Serve re-pointed from the Feature 31
worktree to merged `main`. User acceptance should target this URL.

## Notes

- Conflicts: none (the five branches are a linear stack on P3 tip `c75ff30`).
- Worktrees left in place per re-scope ("do not delete anything"); no `--cleanup`,
  so merged branches `wt/t_73ca1c09`..`wt/t_67540018` remain and are fully merged.
- No push to origin, no production deploy, no tagging, no Coolify (out of scope).
Next phase (P5) starts from `main` `c8d6ab0`.
