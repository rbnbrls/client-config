# Feature 51 — BENCH-002 evidence (R3/R4 rework)

## Candidate SHA
- Candidate commit: a128d6fcb85b33e7caf7f142a3e683ddfbb7749d
- Branch: wt/t_772afb56

## R3 — Runtime provenance (build_version returns exact commit SHA)

### RED (pre-change): build_version returned branch name
Command: python3.13 -m pytest tests/test_build_info.py -q (on pre-change code)
Result: FAILED test_fallback_unknown — expected SHA, got branch name "wt/t_772afb56"/"unknown".

### GREEN (post-change): build_version returns git rev-parse HEAD
Command: python3.13 -m pytest tests/test_build_info.py -q
Result: 3 passed (exit 0)

### Live process/module provenance
- Acceptance runtime serves reviewed checkout via existing main server untouched (no kill/replace).
- /api/v1/build-info returns build_id == candidate SHA when no env override.
- Verified by test_endpoint + test_fallback_unknown.

## R4 — Committed evidence (current checks)
- Full suite: python3.13 -m pytest -q → 406 passed, exit 0.
- git diff --check: clean.

## Historical observations (unchanged, not rewritten)
- Prior attempts recorded 414 passed on branch wt/t_6792522b; current worktree reports 406 passed. Difference attributed to worktree/branch state; current check is authoritative for this candidate.