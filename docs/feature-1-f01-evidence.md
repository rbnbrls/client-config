# Feature 1 — F01 discovery workbench evidence

## Oplevering

F01 heeft een lokale discovery-workbench gekregen die de bestaande synthetische prototypebaseline ontsluit voor:

1. pilotprofiel en eerste service-/managerketen;
2. data dictionary met versioning/status;
3. prototype-beleidseigenaren;
4. open ADR-besluiten en verantwoordelijke rollen;
5. append-only beslisnotities met versie en audit.

De pilot-, eigenaar- en juridische keuzes blijven open; er is geen echte klant- of financiële data toegevoegd.

## Implementatie

- `app/store.py`: `discovery_decisions` met append-only triggers, catalogus en versieerbare opslag.
- `app/server.py`: `GET /api/v1/discovery` en `POST /api/v1/discovery/decisions`; de lokale index injecteert de workbench voor de browsertest.
- `app/static/discovery-workbench.js`: toegankelijke, responsive vanilla-JS workbench met synthetische baseline en menselijke beslisnotitieflow.
- `tests/test_discovery_workbench.py`: catalogus-, versioning-, audit- en statusvalidatie.
- `docs/F01-UI-DESIGN-NOTES.md`: design review en gotcha-check.

## Verification

- `python3 -m unittest tests.test_discovery_workbench -v` — 3/3 OK.
- `python3 -m unittest discover tests -v` — 417/417 OK.
- Browser: lokale build op `http://127.0.0.1:8080/`; F01 workbench geopend en inhoud gecontroleerd. De tab is voor user handoff beschikbaar.

## Open gates

- Pilotklant, asset class, partnerprofiel en concrete keten: menselijke bevestiging vereist.
- Policy owners, scope, bronclassificatie, uitzonderingsproces en reviewcadans: Compliance/Legal en business owners.
- ADR-0002 t/m ADR-0005: open beslissingen blijven open; SEC-001/SEC-002 blijven externe identity-/rolmatrixgates.
