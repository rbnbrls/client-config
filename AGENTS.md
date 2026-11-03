# Werkafspraken

- Gebruik uitsluitend synthetische klant- en financiële gegevens in code, fixtures, voorbeelden en commits.
- Wijzig configuratie append-only; geen harde verwijdering. Behoud valid time én transaction time.
- Houd fee-, SLA- en simulatieberekeningen in gedeelde domeinfuncties zodat productiepad en twin dezelfde logica uitvoeren.
- Versieer API-contracten, parameter-schema's, policyregels en partner-exportprofielen.
- Leg actor, reden, bewijs, goedkeuring, simulatie en export/publicatie vast in audit.
- Complianceclaims zonder gevalideerde bron moeten als `te valideren door Compliance/Legal` worden gemarkeerd.
- Houd modules klein en begrijpelijk; vermijd extra runtime-dependencies zonder noodzaak.
- Gebruik `docs/PROJECT-PLAN.md` als backlog en volg de fasevolgorde; begin met discovery/ADR bij open juridische of klantbeleidskeuzes.
- Bouw klantvereisten (OESO/UNGP, ESG, SFDR/PAI, Wtp en DNB-uitbesteding) als versieerbare, klant-/mandaatspecifieke afspraken; hardcode geen universele klantvoorbeeldnorm.
- DORA en niet-ICT vermogensbeheeruitbesteding zijn afzonderlijke classificaties. Laat toepasselijkheid per dienst, fonds en ICT-leverancier vaststellen.
- Vereis voor elke policy die een wijziging blokkeert een gevalideerde eigenaar, bron, scope, uitzonderingsproces en acceptatiecriteria.

## Frontend- en UI-werk

- Gebruik voor **elke frontendgerelateerde taak** — nieuwe schermen of componenten, wijzigingen aan HTML/CSS/JS of frontendframeworks, responsive gedrag, toegankelijkheid, visuele audits en UI-bugfixes — de designrichtlijnen uit [`jdeworks/make-it-look-good`](https://github.com/jdeworks/make-it-look-good).
- Raadpleeg vóór frontendwijzigingen de actuele [`CONSULT.md`](https://raw.githubusercontent.com/jdeworks/make-it-look-good/dev/CONSULT.md), [`workflows/quick-reference.md`](https://raw.githubusercontent.com/jdeworks/make-it-look-good/dev/workflows/quick-reference.md), [`heuristics/llm-design-gotchas.md`](https://raw.githubusercontent.com/jdeworks/make-it-look-good/dev/heuristics/llm-design-gotchas.md) en [`docs/presets/index.json`](https://raw.githubusercontent.com/jdeworks/make-it-look-good/dev/docs/presets/index.json). Lees daarnaast alleen de kennisbestanden die passen bij de UI en het probleem; volg daarvoor de selectietabellen in `CONSULT.md`.
- Audit bestaande frontendcode volgens stap 1A van `CONSULT.md` voordat je die aanpast. Gebruik de intake- en beslispunten uit die playbook wanneer informatie ontbreekt; vraag niet opnieuw naar voorkeuren die al in de opdracht of projectcontext staan. Leg voor een nieuw scherm, redesign of visuele audit beknopte Design Review Notes vast.
- Controleer de preset-index als bron van waarheid voordat je een preset kiest. Lees de exacte preset-HTML uit `docs/presets/<element>/<variant>.html`; gebruik preview-URL's alleen om de vormgeving visueel te bekijken. Pas de richtlijnen aan de bestaande projectstack en bestaande componentpatronen aan.
- Voer de gotcha-zelfcontrole uit vóór het schrijven van UI-code en nogmaals vóór oplevering. Voer visuele/browsercontroles uit wanneer de taak daarom vraagt en rapporteer bevindingen die je niet daadwerkelijk hebt kunnen controleren als onbevestigd.
- Raadpleeg de toolkit online of clone de `dev`-branch buiten deze projectrepository voor intensief frontendwerk. Voeg de toolkit niet als runtime dependency toe en kopieer geen volledige toolkit naar deze repository tenzij de gebruiker dat vraagt.
