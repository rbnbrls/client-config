# Feature 10 — SEC-002 Autorisatie en functiescheiding: bewijs (evidence)

Taak: Kanban `t_8f83a914` · Branch: `wt/t_8f83a914` · Baseline: `6d51e91` (goedgekeurde Feature 9). Alle gegevens synthetisch.

## Wat is opgeleverd

1. **Geen implementatie van RBAC/ABAC of initiator-goedkeurder-scheiding** — conform ADR-0005 en de open menselijke gate: de gevalideerde rolmatrix en actor-scheiding (SEC-002) zijn nog niet goedgekeurd door product owner en security owner. Rollen, capabilities, groep/rol-claimmapping en toegangsreviewcadans blijven externe beslissingen.
2. **Demo-autorisatie blijft uitgeschakeld** en wordt niet als beveiligingsgrens gepresenteerd; caller-provided actor-strings zijn demo-invoer, geen autoritatieve identiteit of rol.
3. **Open menselijke gates geregistreerd** (niet verzonnen): gevalideerde rolmatrix en actor-scheiding (SEC-002); identity provider/tenant confirmation (ADR-0005); policy owner appointment (CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE); enforcement level per control met uitzonderingsproces; primary source classification policy; FactSet tenant/service confirmation.

## TDD-bewijs

Geen gedragswijziging in code; bestaande suite ongewijzigd groen.

| Stap | Commando | Resultaat |
|---|---|---|
| Volledige suite | `python3.13 -m pytest -q` | **40/40 passed, exit 0** |

Exacte commando en uitvoer (laatste run):

```
$ python3.13 -m pytest -q
........................................                                 [100%]
40 passed in 1.20s
```

## Dekking van de SEC-002-acceptatiecriteria (P1)

| Criterium | Status |
|---|---|
| Autorisatie server-side afgedwongen | Open — vereist goedgekeurde rolmatrix + providerkeuze (ADR-0005) |
| Initiator ≠ goedkeurder | Open — vereist rolmatrix en actor-scheiding (SEC-002) |
| Beperkte adminrollen | Open — vereist rolmatrix |
| Periodieke toegangsreview | Open — vereist toegangsreviewproces |
| Historische configuratie reconstrueerbaar | Reeds gedekt door Feature 7/8 |
| Records niet hard te verwijderen | Reeds gedekt door append-only triggers (Feature 6/7) |
| Audit niet wijzigbaar via reguliere product-API | Reeds gedekt |
