# Design Review Notes — SEC-001 identity readiness

> Guided by [make-it-look-good](https://github.com/jdeworks/make-it-look-good)

## Overview

- **What:** A read-only readiness dialog for the next identity/SSO backlog item.
- **Stack:** Existing plain HTML, CSS, and JavaScript; no runtime dependency added.
- **Date:** 2026-11-03
- **Purpose:** Show clearly that the prototype has no authentication and state what must be decided before implementation.

## Existing UI audit and design decisions

- Kept the current Atlas shell, teal accent, system font, and modal pattern so the status belongs with the existing prototype.
- Used a warning panel with text labels to communicate demo-only identity; color is not the only signal.
- Exposed the same read-only status from the top-bar demo identity so it remains reachable when the existing sidebar is hidden on narrow screens.
- Kept the dialog read-only. Provider, tenant, role mapping, and session controls are not available because those decisions are open.
- Made the close controls at least 44px, added a visible focus outline, Escape dismissal, focus return, and a small keyboard focus loop.
- Stacked the decision facts on narrow screens. The dialog copy identifies the demo actor as non-authenticated and warns to use synthetic data only.

## Known design limitations

- Existing application shell uses 14px body text, compact labels and controls, and hides the sidebar on small screens. Those issues predate this slice and were not redesigned here.
- This page presents preparation status only. It does not add authentication, session state, authorization, or API protection.
- Browser review in Safari confirmed that both entry points open the status dialog and Escape closes it. After starting the stopped local API, reload produced no browser-console errors; the initial failed requests were caused by the unavailable server.
- Increased dialog body copy to 16px. Automated contrast measurement and a separate mobile-device emulation were not run.
