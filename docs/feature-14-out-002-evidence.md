# Feature 14 — OUT-002 Ketenregister — Evidence

**Task:** t_8b6c16e6 · **Branch:** `wt/t_8b6c16e6` · **Base:** Feature 13 goedgekeurde tip `59a5d3a` (nog niet gemerged naar main; keten-bouwvolgorde conform teamconventie — Feature 13-bladeren is de laatst goedgekeurde stand, main staat nog op de P1-merge `3a952fc`).

## Implementatie (plank 91 van docs/PROJECT-PLAN.md, OUT-002)

Nieuwe append-only registers in `app/store.py`:

- `chain_parties` — ketenschakels per klant: `party_type` (direct/indirect/subcontractor), naam, dienst, **datastroom**, **jurisdictie** en **juridische entiteit**, **contractreferentie**, `parent_party_id` (direct→indirect→onderuitbesteders als ketenboom), kritikaliteit, `subcontract_share` (fractie 0–1), source_ref, rationale, effective_from/to. PK(id,version), no-update/no-delete-triggers, valid- en transaction time behouden (zelfde patroon als activity_register).
- `chain_tasks` — meldingstaken met verplichte **eigenaar en deadline**; afronding via `complete_chain_task` (**bewijs van afronding verplicht**) als nieuwe append-only versie (status `'completed'` + `completion_evidence`); geen update of delete.
- `chain_trace(customer_id, party_id)` — volledige keten om een schakel heen: up- en downstream schakels met diepte (directe én indirecte niveau's), cyclussen onmogelijk gemaakt bij opslag.
- `chain_impact(customer_id, party_id, thresholds=None)` — bij wijziging van een schakel: geraakte klanten/mandaten via dienst-koppeling op het activiteitenregister (Feature 13), thresholdovertredingen en open meldingstaken.
- Thresholds zijn **policyparameters met bronverwijzing**, nooit universeel hardcoded: default `CHAIN_THRESHOLD_DEFAULTS` bevat de DNB 30%-onderuitbestedingsverwachting als bronvermelding met `subcontract_share_pct=None` (alleen actief met een expliciete, gebronverwijde parameter); elke override vereist een `source_ref`.
- Review-/meldstatus blijft `"pending"` met de validatienotitie "te valideren door Compliance/Legal voor relevante klant/partij" (open gate, nooit geclaimd compleet).

Nieuwe endpoints in `app/server.py`: `GET/POST /api/chain-parties`, `GET /api/v1/chain-parties` (bitemporaal), `GET /api/customers/<cid>/chain-trace/<pid>`, `GET /api/customers/<cid>/chain-impact/<pid>`, `GET /api/chain-tasks?customer_id=`, `POST /api/chain-tasks`, `POST /api/chain-tasks/<id>/complete`.

## Test-first

RED: `tests/test_chain_register.py` aangeemaakt vóór implementatie; eerste run `14 failed, 0 passed` (AttributeError: functies nog niet aanwezig). Daarna GREEN.

```
$ python3.13 -m pytest tests/test_chain_register.py -q
14 failed → na implementatie: 14 passed
```

## Volledige suite (eindstand)

```
$ python3.13 -m pytest -q
.............                                                            [100%]
85 passed in 3.65s
```

Exit 0. 71 vooraf bestaande tests ongewijzigd groen + 14 nieuwe (register met verplichte velden, enum party_type, versiebeheer zonder overschrijving, delete-blokkade, onbekende parent, parent-cyclus, direct+indirect trace 2 niveaus, impact→geraakte mandaten, threshold als parameter met bron (30% vangt 0.35-share; 40% niet; source_ref in output), meldingstaak eigenaar/deadline verplicht, afronding bewijs verplicht, bitemporale valid-time filter, onbekende partij in impact).

## Live API-verificatie (eerlijke smoke op scratch-DB met synthetische gegevens)

```
$ CLIENT_CONFIG_PORT=8917 python3.13 -m app.server   # CLIENT_CONFIG_DB scratch
POST /api/chain-parties (direct)  → PARTY1 synth-beheer direct 1
POST /api/chain-parties (indirect)→ PARTY2 sub-data indirect parent= synth-beheer
GET /api/customers/northstar/chain-trace/synth-beheer → upstream=['synth-beheer'] downstream=[('sub-data',1)]
GET /api/customers/northstar/chain-impact/sub-data   → downstream=['sub-data'], review=pending, threshold-source = "DNB-verwachting 30% onderuitbesteding…"
POST /api/chain-tasks (zonder owner)                 → {"error": "owner is verplicht"}
POST /api/chain-tasks (goedgevuld)                   → TASK ctk-northstar-sub-data-melding open owner=demo.compliance deadline=2026-12-01
POST /api/chain-tasks/.../complete (bewijs)          → COMPLETE completed evidence=SYNTH-EVIDENCE-001 v=2
GET /api/v1/chain-parties?valid_at=2026-07-01        → ['sub-data','synth-beheer']
GET /api/v1/chain-parties?valid_at=2025-01-01        → []  (bitemporale filter)
```

Server gestopt; smoke-DB verwijderd (niets achtergelaten in de worktree).

## AI-zelfaudit

- Geen secrets/API-keys in diff (`git diff --check` schoon; grep op secret-patronen leeg).
- Geparametriseerde SQL (bound arguments) door alle nieuwe query's; geen stringconcatenatie van invoer.
- Invoervalidatie: verplichte velden, party_type-enum, kritikaliteit-enum, share 0–1, ISO-datums, deadline-formaat, parent-cyclus-afwijzing, beweisplicht bij afronding, already-completed-afwijzing.
- Append-only geconsolideerd: beide nieuwe tabellen met no-update/no-delete-triggers en PK(id,version); audit-regel per insert; valid/transaction time behouden.
- Thresholds (DNB 30%) zijn bronverwijzingen/policyparameters (default None + verplichte source_ref bij override), niet universeel hardcoded.
- Auth/rate-limit: out of scope conform de open SEC-gates (SEC-001/SEC-002), zoals bij Features 11–13.
- Geen door de gebruiker gewijzigde bestanden aangeraakt (diff: `app/store.py`, `app/server.py`, `tests/test_chain_register.py`, dit evidence-bestand).

## Open human gates (record, niet geïnventeerd)

- Interpretatie Pensioenwet art. 34, Wft art. 3:18, Besluit uitvoering Pw/Wvb, Besluit prudentiële regels Wft: **te valideren door Compliance/Legal** per relevante klant/partij.
- Kritikaliteit- en meldplicht-interpretatie: te valideren door Compliance/Legal; review_status bewust `pending`.
- DNB-verwachting rond 30% onderuitbesteding: als bronvermelding/policyparameter opgenomen; klantspecifieke bevestiging open.
- Policy owner appointment (CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE), enforcement levels + uitzonderingsproces, primary source classification policy, SEC-002 gevalideerde rolmatrix, FactSet tenant-bevestiging, identiteitsprovider/tenant (ADR-0005) — onveranderd open.
