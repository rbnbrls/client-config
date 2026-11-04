# Phase P1 merge evidence — Features 6–12 into main

Date: 2026-11-04 (CET). Executed by @release (gate task t_30b99bcc), workspace /Users/ruben/Code/client-config.

## Scope

Merge the independently reviewed feature branches for Features 8–12 into `main` in numeric
order (Features 6 and 7 were already merged by the previous reconcile gate t_9bcd340f at
5dd9114). Each merge was made only after confirming the branch tip exactly matches the
reviewer-approved HEAD SHA.

## Merges (numeric order, all `--no-ff`, all clean — zero conflicts)

| Feature | ID | Branch | Approved HEAD | Merge commit |
|---|---|---|---|---|
| 8 | CFG-003 | wt/t_56f6aee3 | e3a199da39e924dab12b4d14a25cfc7404112f64 | 19aa0eb219ad3dac02a3c72b50f4979ea1e64ef9 |
| 9 | SEC-001 | wt/t_8c16891d | 6d51e910daffa92752d8ce845294f780c35e4aa2 | 07d4bb32492106eb34d9449c6e73590dfaf31785 |
| 10 | SEC-002 | wt/t_8f83a914 | 3b316cf887703189b279208b08d61a4fe73abab6 | 8bf55881068d9deba00bc88ac5e07405d7e5b181 |
| 11 | AUD-001 | wt/t_bd3105c6 | 32f9808c6a88787bfad5946a1e08caa6a0c3b97a | 6adf5be5eb96838aaf1183353a1f7a2cd7c773ae |
| 12 | DOC-001 | wt/t_2511a615 | 0f1d414fcfc7751e40978a7d01c8ea392d6e30c3 | 6b1d24ec1bc43b46a1348fa09a296c53266319ae |

Pre-merge checks performed per branch:

- `git rev-parse <branch>` compared byte-for-byte against the reviewer-approved HEAD from
  the board (review gates t_0ccc8d67, t_dd6ef21f, t_17c0c8c0, t_a51f958f, t_e07a3b56).
  All matched; no branch moved after approval, so no re-review was required.
- Reviewer verdicts recorded: all five `APPROVE` with independently re-run suites
  (F8 47/47, F9 40/40, F10 40/40, F11 45/45, F12 54/54).

### Note on Feature 10 and the revert commit on main

Before this gate, commit 3062893 (docs(sec-002) Feature 10 evidence) had been committed
directly on main by mistake and reverted by e6bcc37 (author ruben, 14:00:33 CET, 18 seconds
later). The F10 branch commit 3b316cf is the reviewed original; merging wt/t_8f83a914 at
8bf5588 restored that exact reviewed file `docs/feature-10-sec-002-evidence.md` through the
sanctioned gate path (content identical to 3062893 except one pytest timing value). The revert itself is
preserved in history — no rewrite, append-only.

Verification: `git diff 3062893 8bf5588 -- docs/feature-10-sec-002-evidence.md` shows a
single hunk: the suite duration line `40 passed in 1.20s` → `40 passed in 1.46s` (the
reviewer's own re-run timing). Reviewed content otherwise identical to the earlier direct
commit; no behavioural difference.

## Full suite on merged main

Command (Python 3.13.14; system python3 is 3.9 and cannot parse `int | float` annotations):

```
$ python3.13 -m pytest -q
.............................................................            [100%]
61 passed in 2.05s
exit code: 0
```

61 passed = 40 pre-existing + 7 config-schema (F8) + 5 audit append-only (F11) + 9
document_references (F12). Features 9 and 10 added evidence documents only (their
implementations are correctly gated by open human decisions — see below).

Main HEAD after merge + evidence commit: this file's commit (parent 6b1d24ec1bc43b46a1348fa09a296c53266319ae).

## Invariants checked

- No conflicts occurred; no conflict resolution was needed. User-touched files
  (AGENTS.md, app/server.py UI parts, app/static/index.html, docs/*-UI-DESIGN-NOTES.md,
  docs/adr/*) were untouched by any merge diff.
- Append-only and synthetic-data invariants preserved (per reviewer evidence, re-verified
  by the green suite including negative-path tests).
- No push performed; main is ahead of origin/main, same as after the previous gate.

## Open human gates (recorded, not implemented — unchanged by this merge)

1. Policy owner appointment for CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE
2. Enforcement level per control with exception process
3. Primary source classification policy
4. SEC-002 validated role matrix and actor separation
5. FactSet tenant/service confirmation
6. ADR-0005 identity provider/tenant confirmation

## Out of scope (not done here)

Production deployment, release tagging, Coolify, and Feature 13 implementation (next chain task t_57ced659, already queued).
