# Phase P2 merge evidence — Features 13–19 into main

Date: 2026-11-04 (CET). Executed by @release (gate task t_349e20ea), workspace
/Users/ruben/Code/client-config (main checkout; main started at 3a952fc).

## Scope

Merge the independently reviewed feature branches for Features 13–19 into `main` in
numeric order. Each merge was made only after confirming the branch tip
byte-for-byte matches the reviewer-approved HEAD SHA from the board. Approver / reviewer verdicts were read from the board review gates
(t_f16005cc, t_d606936f, t_566a65ed, t_199a6540, t_83b4ed7c, t_e1c70943, t_9400e7dd);
all seven `APPROVE`.

## Merges (numeric order, all `--no-ff`, all zero conflicts)

| Feature | ID | Branch | Approved HEAD (verified byte-for-byte) | Merge commit |
|---|---|---|---|---|
| 13 | OUT-001 Activiteitregister | wt/t_57ced659 | 59a5d3a93acd03e15369e5b2671fd5693d735580 | 03f7cb3 |
| 14 | OUT-002 Ketenregister | wt/t_8b6c16e6 | db95bc7b612b12eeabe6fbe9740a1be91293fedd | 60aafcc |
| 15 | OUT-003 Contractuele minimumvelden | wt/t_462f95d7 | e4b372cf60a8af440ea3186cac0e57431cc6199e | b74c766 |
| 16 | OUT-004 Selectie- en periodieke beoordeling | wt/t_16313c4b | 1f77e9e626e8a7bbf924c7c2e3cc8048e00b77e9 | 8b88b31 |
| 17 | OUT-005 Melding en wijzigingssignalering | wt/t_53fb98b1 | 1f40b406b752b8913d5a055f58c8bfb8c5d8190f | 79e906b |
| 18 | OUT-006 DORA/ICT-loskoppeling | wt/t_433d3751 | b082e7820b5733381b2662ccfc4593a3ef6b372e | b68f4cb |
| 19 | OUT-007 Governance en countervailing power | wt/t_8f871df8 | a3aa1a23b69958df7e90902e263b0dd68106d4ef | 8179eeb |

Chain sanity verified: every later tip contains the previous approved tip
(F13 ⊂ F14 ⊂ F15 ⊂ F16 ⊂ F17 ⊂ F18 ⊂ F19), so the merges are a linear application
of reviewed content. No branch moved after approval.

## Incident: unreviewed `app/server.py` overwrite in Feature 18 tip (resolved at the gate)

The F18 merge (b68f4cb) arrived clean, but its diff showed **48 deletions in
`app/server.py`** — a user-touched file. Diagnosis:

- `git diff 3a952fc b082e78 -- app/server.py` is **empty**: the F18 tip's
  `app/server.py` is byte-identical to main-before-P2's, i.e. the F18 chain
  overwrote the file with a stale pre-chain snapshot.
- Within the chain, e23abee (F18 implementation, "ICT provider relation register")
  touched only `app/store.py` (+30); the deletion came entirely from b082e78
  ("parity with dora assessments"), removing exactly the +15 (F13) and +33 (F14)
  reviewed HTTP routes (`/api/activities`, `/api/v1/activities`, chain-trace,
  chain-impact, `/api/chain-parties` incl. v1, `/api/chain-tasks` + complete,
  activity-chain) — all unreviewed deletions of reviewed content.
- F18's evidence scope ("ICT provider relation register brought to parity with
  dora_assessments") is store-level; the reviewer's recorded checks cover append-only
  triggers, bi-temporal filtering, validation, audit — no `app/server.py` route
  removals were part of any approved diff.

Resolution (ordering rule: resolve in favour of the reviewed branch, preserving
user-touched files): restored `app/server.py` to the reviewed union state — the
post-F17-merge main version (79e906b), which contains the F13+F14 approved routes;
F18 and F19 add nothing to this file. Committed on main as **6f37969**
(`merge(t_349e20ea): restore app/server.py routes clobbered by unreviewed overwrite
in Feature 18 tip`) with the full diagnosis in the commit message. No history rewrite;
the regressed merge commit b68f4cb remains in history transparently.

Verification after fix: `git diff 79e906b 6f37969 -- app/server.py` empty
(server.py == reviewed union state); net diff 3a952fc..6f37969 for user-touched
files is exactly this intended +48 (`M app/server.py`) and nothing else —
`AGENTS.md`, `app/static/index.html`, `docs/*-UI-DESIGN-NOTES.md`, `docs/adr/*`
untouched by the whole phase. `app/store.py` net = 614 insertions, 0 deletions.

**Follow-up for the Feature 18 chain:** b082e78 contains an unreviewed wholesale
overwrite of a user-touched file that reviewers did not flag. Recommend the board
note it; no further action needed here because the gate restored reviewed content.

## Full suite on merged main (+ evidence doc, no test impact)

Command (Python 3.13; system python3 is 3.9 and cannot parse `int | float` annotations):

```
$ python3.13 -m pytest -q
........................................................................ [ 53%]
..............................................................           [100%]
134 passed in 5.84s
exit code: 0
```

134 = 61 (end of P1) + 10 activities (F13) + 14 chain register (F14) + 8 contract
minimums (F15) + 8 selection/assessment (F16) + 9 notification signals (F17) + 8 ICT
provider relations (F18) + 16 governance policies (F19). Matches the F19 reviewer's
independent 134-passed run on the review tip.

Main HEAD after merge chain + restore + evidence commit: this file's commit
(parent 6f37969).

## Open human gates (recorded, not implemented — unchanged by this merge)

1. Policy owner appointment for CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE
2. Enforcement level per control with exception process
3. Primary source classification policy
4. SEC-002 validated role matrix and actor separation
5. FactSet tenant/service confirmation
6. ADR-0005 identity provider/tenant confirmation
7. OUT-007 Pensioenwet art. 34 / Wft art. 3:18 interpretation — Compliance/Legal validation
   (new with Feature 19)

## Out of scope (not done here)

Next phase implementation (Feature 20 chain), production deployment, tagging,
Coolify, `git push`.
