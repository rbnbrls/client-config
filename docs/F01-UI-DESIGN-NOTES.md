# Design Review Notes — F01 discovery workbench

## Scope

Een compacte, lokale workbench voor de P0-discoveryvraag: pilotprofiel, eerste service-/managerketen, data dictionary, beleidseigenaren en open ADR-besluiten zichtbaar maken en beslisnotities append-only vastleggen.

## Existing UI audit (CONSULT step 1A)

- Plain HTML/CSS/vanilla JS met bestaande navy/teal Atlas-shell; geen framework of runtime dependency.
- Bestaande patronen gebruiken modals, panels, `btn`, `field` en `policy-card`; de nieuwe flow hergebruikt die taal en voegt alleen een eigen namespace (`f01-*`) toe.
- De bestaande shell is responsive, maar de sidebar is op smalle schermen verborgen. Daarom staat F01 naast de hoofdactie in de page heading en niet alleen in de sidebar.
- Bestaande labels en focus states zijn behouden; de nieuwe form controls hebben expliciete labels, zichtbare focus, Escape/achtergrondsluiting en minimaal 44px primaire knoppen.

## Design decisions

- Dashboard/workbench-vorm op basis van de `shell-dashboard`-richting uit de preset-index: scanbare cards, een expliciete menselijke-gate callout en compacte tabellen met horizontale overflow op smalle schermen.
- Teal is de bestaande actie-/statuskleur; amber markeert open menselijke beslissingen. Status wordt altijd met tekst getoond, niet alleen met kleur.
- Eén primaire actie: `Beslisnotitie opslaan`. De inhoud blijft synthetisch en open totdat een menselijke eigenaar een bevestiging vastlegt.
- ADR's en beleidseigenaren zijn read-first; de gebruiker hoeft geen modal te openen om de open scope te begrijpen.

## Gotcha self-check

- Geen placeholder-/loremtekst; alle demo-inhoud is synthetisch en gelabeld.
- Geen universele complianceclaim; juridische/beleidsmatige open punten zijn expliciet gemarkeerd als `te valideren door Compliance/Legal`.
- Geen data wordt verwijderd of overschreven; beslisnotities maken een nieuwe versie en auditregel.
- Formulierlabels, focus states, Escape-sluiting en mobiele tabel-ervaring zijn toegevoegd.
- Browsercontrole uitgevoerd op de lokale build; volledige responsieve matrix en contrastmeting zijn nog niet formeel geautomatiseerd.
