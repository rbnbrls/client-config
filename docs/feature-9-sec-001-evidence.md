# Feature 9 — SEC-001 Echte identiteit: bewijs (evidence)

Taak: Kanban `t_8c16891d` · Branch: `wt/t_8c16891d` · Baseline: `e3a199d` (goedgekeurde Feature 8). Alle gegevens synthetisch.

## Wat is opgeleverd

1. **Geen implementatie van een login/OIDC-flow** — conform ADR-0005 (Status: Accepted for preparation; identity provider selection remains open). Providerselectie, tenant, app registration, secretsbeheer en rol-mapping zijn externe beslissingen die nog niet bevestigd zijn door de identity/platform-owner.
2. **Demo-authenticatie blijft uitgeschakeld** en wordt niet als beveiligingsgrens gepresenteerd; caller-provided actor-strings zijn demo-invoer, geen autoritatieve identiteit.
3. **Open menselijke gates geregistreerd** (niet verzonnen): identity provider/tenant confirmation (ADR-0005); policy owner appointment (CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE); enforcement level per control met uitzonderingsproces; primary source classification policy; gevalideerde rolmatrix en actor-scheiding (SEC-002); FactSet tenant/service confirmation.

## TDD-bewijs

Geen gedragswijziging in code; bestaande suite ongewijzigd groen.

| Stap | Commando | Resultaat |
|---|---|---|
| Volledige suite | `python3.13 -m pytest -q` | **40/40 passed, exit 0** |

Exacte commando en uitvoer (laatste run):

```
$ python3.13 -m pytest -q
........................................                                 [100%]
40 passed in 1.29s
```

## Dekking van de SEC-001-acceptatiecriteria (P1)

| Criterium | Status |
|---|---|
| Autorisatie server-side afgedwongen | Open — vereist SEC-002 rolmatrix + providerkeuze (ADR-0005) |
| Historische configuratie reconstrueerbaar | Reeds gedekt door Feature 7/8 |
| Records niet hard te verwijderen | Reeds gedekt door append-only triggers (Feature 6/7) |
| Audit niet wijzigbaar via reguliere product-API | Reeds gedekt |
| Caller-provided actor strings nooit autoritatief | Geregistreerd als invariant; implementatie volgt na providerkeuze |
| SSO/actor attribution browser+API acceptatiechecks | Open — niet-Productie tenant vereist |