# Design Review Notes — crawl-report visual direction

## Scope

De bestaande operationele dashboard-structuur blijft behouden; alleen de visuele laag is afgestemd op de stijl uit het aangeleverde crawl report.

## Applied direction

- Licht canvas met wit als primaire achtergrond en zacht lichtblauw voor secties.
- Institutionele blauwtonen voor navigatie, kaarten, statusaccenten en footer-achtige structuur.
- Magenta als beperkt interactieaccent voor primaire CTA's en feedbacksignalen.
- Editoriale serif-koppen gecombineerd met Roboto/Arial voor functionele tekst.
- Ruimere marges, afgeronde kaarten en begrensde tekstbreedte om de lange-regel- en uitlijningswaarschuwingen uit het report te beperken.
- Grotere interactieve targets en een responsive small-screen layout.

## Constraints

- Geen externe runtime-dependencies of remote assets toegevoegd.
- Bestaande F01-workflows, routes en append-only opslag zijn niet functioneel gewijzigd.
- Donkere modus is opt-in via `body.theme-dark`; de standaardweergave volgt de lichte referentiestijl uit het crawl report.

## Verification

- Lokale browserpreview gecontroleerd op `http://127.0.0.1:8080/`.
- `git diff --check` uitgevoerd.
- `python3 -m py_compile app/server.py` uitgevoerd.
- Gerichte F01-tests: 3/3 groen.
