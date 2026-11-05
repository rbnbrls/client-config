# Phase P7 merge evidence

Date: 2026-11-05

## Merges (numeric order)

| Feature | Branch | Reviewed SHA | Merge SHA (main) | GitHub SHA |
|---|---|---|---|---|
| 44 | wt/t_182c295c | 1e89f4d | c442c14 | c442c14 |
| 45 | wt/t_63145776 | a94672a | 8da8733 | 8da8733 |
| 46 | wt/t_a2c0d351 | ead4f5e | f4ff216 | f4ff216 |
| 47 | wt/t_063c93d5 | 35003b4 | bf79e64 | bf79e64 |

(F42 TWIN-001 and F43 twin-002 were already on main.)

## Full suite on merged main

Command: `python3.13 -m pytest -q`
Result: 406 passed in 38.20s (exit 0)

## Acceptance URL

http://localhost:8080 (verified via land-feature.sh)

## Notes

- Local main fast-forwarded to origin/main (c97d247) before landing, preserving remote backlog changes.
- Each landing published and read back origin/main successfully.
- Worktrees cleaned up.
}