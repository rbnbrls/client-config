# Client Service Configuration Platform

Een dependency-vrije MVP-slice voor het beheren van institutionele klantconfiguratie, wijzigingssets, deterministische impactsimulatie en partnerexports.

## Starten

```sh
python3 -m app.server
```

Open vervolgens http://127.0.0.1:8080. De app gebruikt SQLite in `data/client_config.db` (automatisch aangemaakt). Stel `CLIENT_CONFIG_HOST` en `CLIENT_CONFIG_PORT` in om bind-adres/poort te wijzigen.

## Projectplanning

De feature-backlog, roadmap, acceptatiecriteria, besluiten en bronnen voor coding agents staan in [docs/PROJECT-PLAN.md](docs/PROJECT-PLAN.md).

## MVP-opzet

- Python 3 standaardbibliotheek HTTP API en SQLite-repository.
- Bitemporele versies: `valid_from`/`valid_to` en `recorded_from`/`recorded_to`; configuratierevisies worden toegevoegd, niet verwijderd.
- Change sets met status, actor, reden, simulatie, goedkeuring en activering.
- Fee-impactberekening gebruikt dezelfde gedeelde pure domeinfunctie voor simulatie en verificatie.
- Export als versiegebonden JSON-bestand en als API-payload op basis van partnerprofiel.
- Alleen synthetische voorbeeldgegevens.

Dit is een lokale MVP-basis, geen productieklare omgeving: SSO, PostgreSQL, deployment, operationele monitoring, formele juridische beleidsregels en partner-specifieke transporten moeten nog worden aangesloten en gevalideerd.
