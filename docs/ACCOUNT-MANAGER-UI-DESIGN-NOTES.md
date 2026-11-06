# Design Review Notes — multi-persona customer journey

## Audit finding

De technische labels `F01 · P0 DISCOVERY`, `DORA-classificatie`, `Entiteiten & relaties`, `Schema & parameters` en `Identiteit & toegang` maakten de primaire navigatie code-/platformgericht. De tool ondersteunt echter meerdere samenwerkende personas over de volledige klantbediening, niet alleen de accountmanager.

## Information architecture

De zichtbare navigatie volgt nu deze journey en toont de toekomstige persona-eigenaar per functie:

1. **Prospect & sales:** Prospectdossier, Voorstel & prijs.
2. **Onboarden als klant:** Klantdossier, Afspraken & vereisten, Keten & partijen, Uitbesteding & risico, Beleid & afspraken.
3. **Dagelijkse klantbediening:** Klantoverzicht, Wijzigingen beheren, Review & audit, Exports delen.
4. **Platform & governance:** Identiteit & toegang, Schema & parameters, Pilot & open besluiten.

Alle functies blijven in deze ontwikkelfase zichtbaar. Persona-labels zijn informatief en vormen nog geen autorisatie. F01 blijft intern traceerbaar in backlog, code en audit; de gezamenlijke workflow is zichtbaar als **Pilot & open besluiten**.

## Design decisions

- Gebruik taakgerichte zelfstandige naamwoorden/werkwoorden in plaats van featurecodes.
- Groepeer op de klantreis en toon toekomstige persona-eigenaars als secundaire labels; target size blijft minimaal 44px.
- Toon nog niet gebouwde prospect-/salesfuncties als zichtbare roadmap-acties met expliciete `in ontwikkeling` feedback.
- Behoud bestaande click handlers en prototype-workflows; deze wijziging verandert de informatiearchitectuur en labels, niet de domeinlogica.
- Gebruik `aria-label` voor de navigatie en `aria-current="page"` voor het actieve klantoverzicht.
- Behoud synthetische demo-aanduiding; noem demo-identiteit niet productioneel.

## Verification

- Browser smoke test vereist op `http://127.0.0.1:8080/`.
- Controleer dat F01 nergens als primaire menuoptie verschijnt.
- Controleer dat `Pilot & open besluiten` de bestaande discovery-modal opent.
- Controleer desktop en small-screen navigatie; alle bestaande technische en operationele functies zijn zichtbaar onder **Platform & governance** of de relevante klantreisfase.
- Prospectdossier en Voorstel & prijs zijn zichtbaar als roadmap-functies en claimen geen bestaande backendfunctionaliteit.
