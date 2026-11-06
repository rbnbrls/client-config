# Product Backlog

Canonical backlog location: repository root `PRODUCT_BACKLOG.md`.

This file migrates the former `docs/PROJECT-PLAN.md` backlog. GitHub Issues and GitHub Projects are external work sources; Hermes Kanban is execution mirror. Sync policy:

- Open GitHub issues map to open Kanban tasks.
- Closed GitHub issues remain documented here under **Completed from GitHub**.
- GitHub Project items map to backlog entries and Kanban tasks.
- Sync runs weekly and after issue/project changes.
- Source links and last-sync timestamp stay attached to every imported entry.

## Sync metadata

- GitHub repository: https://github.com/rbnbrls/client-config
- Former source: `docs/PROJECT-PLAN.md`
- GitHub Issues at migration: none
- GitHub Project items at migration: none; user projects 1, 2, and 3 were empty
- Initial migration: 2026-11-05
- Latest state review: 2026-11-06 07:16 CET
- Latest GitHub inventory: [issues](https://github.com/rbnbrls/client-config/issues) — 0 open, 0 closed; [Project 1](https://github.com/users/rbnbrls/projects/1), [Project 2](https://github.com/users/rbnbrls/projects/2), [Project 3](https://github.com/users/rbnbrls/projects/3) — 0 items each
- Latest Hermes Kanban verification: local board `client-config`, 167 non-archived tasks (136 done, 29 todo, 1 scheduled, 1 blocked); this includes stale/duplicate release-gate tasks that require board hygiene.
- Sync result: local backlog state refreshed from `main` at `dff07bd`; GitHub inventory was last verified on 2026-11-05 and was not changed by this review.

Source snapshots: `gh issue list --repo rbnbrls/client-config --state all`; `gh project item-list 1|2|3 --owner rbnbrls`; `hermes kanban --board client-config list` at 2026-11-05 10:46 CET.

## Migrated product plan

# Projectplan — Client Service Configuration Platform

**Status:** Features 1–51 zijn in `main` aanwezig en volgens de beschikbare merge-/reviewevidence als prototype-slices afgerond. De productrelease is niet production-ready: SEC-001, formele rol-/bevoegdheidskeuzes, Compliance/Legal-validatie, productie-infrastructuur, herstel/retentie en klant-/leveranciersbesluiten blijven gates. Feature 52 (BENCH-003) is de volgende geplande prototype-slice; de P8-releasegate staat nog open.
**Doel:** de klantbediening als gecontroleerde, versieerbare configuratie beheren en wijzigingen veilig simuleren, goedkeuren en publiceren.  
**Productbasis:** huidige repository is een lokale prototype-slice. De bestaande SQLite-demo is geen production-ready control environment.

## Implementatiestatus

| Backlog-item | Status | Toelichting |
|---|---|---|
| Feature 1 — domein- en legal discovery | **Gereed in prototype** | Discovery-evidence is vastgelegd in `docs/discovery/feature-1-discovery-evidence.md` en Feature 1 is gemerged. De uitkomst is richtinggevend voor de prototypebacklog; pilotklant, formele beleidsbesluiten en productionele eigenaren blijven open. |
| POL-001 Besluitenregister | **Gereed in prototype** | Append-only, versieerbaar register met eigenaar, scope, bron, toepasselijkheid, handhavingsniveau, ingangs-/reviewdatum en validatiestatus. Harde blokkade wordt geweigerd zonder gevalideerde status en bewijs. Voorbeelden zijn synthetisch; actor/goedkeuring is nog demo en niet production-ready. |
| POL-002 Broncontrole | **Gereed in prototype** | Append-only bronreviews per controlversie met brontype, titel/locator, uitkomst, reviewer/rol, motivering en tijdstip. Alleen geverifieerde primaire bronnen of klantcontract/-beleid kunnen een afzonderlijk policybesluit tot validatie ondersteunen. Nieuwere bronreviews maken een ouder validatiebesluit opnieuw pending. Demo-actoren; formele identiteit en bevoegdheden ontbreken. |
| POL-003 Klantvarianten | **Gereed in prototype** | Per klant versieerbare contractuele vereisten voor ESG, SFDR/PAI, Wtp, rapportage, disclosure, kosten en keten/uitbesteding; bronreferentie, frequentie, geldigheids-/reviewdatum, configuratiepad en motivering; audittrail. Reconciliatie toont ingestelde match, afwijking, ontbrekende mapping of handmatige review. Match is geen nalevingsconclusie; demo-identiteit en eenvoudige exactewaardevergelijking. |
| POL-004 DORA-classificatie | **Gereed in prototype** | Append-only, versieerbare menselijke scopebeoordelingen voor vermogensbeheeractiviteiten, ICT-diensten van derde leveranciers en eigen platform-/cloud-ICT. Vastlegging omvat klantrelatie, partij/dienst, scope, toepasselijkheidsstatus, kritikaliteitsbeoordeling, contract-/bronreferenties, reviewer, motivering en reviewdatum. Geen automatische juridische conclusie; DORA/Wft-classificatie en criteria blijven te valideren door Compliance/Legal en ICT-risk. |
| CFG-001 Entiteiten en relaties | **Gereed in prototype** | Per klant/fonds versieerbare entiteiten en groeps-/dienstrelaties voor fonds, juridische entiteit, groep, fiduciair, manager, submanager en custodian, inclusief jurisdictie, classificatie, geldigheid, bron, motivering en audit. Geen productieautorisatie of volledige bitemporele opslag. |
| CFG-002 Bitemporele revisies | **Gereed in prototype; productie-open** | Hoofdconfiguratie, CFG-001, klantvereisten, DORA-assessments en controls/beleid hebben tijdreisleesqueries en append-only snapshots. Feature 7 is gemerged en evidence is aanwezig. Pre-migratiehistorie, productie-retentie/immutability en Compliance/Legal- en ICT-risk-validatie blijven open. |
| CFG-003 Getypeerde parameterdefinities | **Gereed in prototype; productie-open** | Feature 8 is gemerged met versieerbare schema's, server-side validatie en auditfingerprint. De ondersteunde JSON Schema-subset, formele eigenaarstoewijzing en klant-/mandaatspecifieke normvalidatie begrenzen de claim. |
| SEC-001 Identiteit en SSO | **Geblokkeerd — externe beslissing vereist** | Voorbereiding en ADR-0005 liggen vast. De read-only SEC-001-statusdialoog is volgens bestaande projectevidence in Safari gecontroleerd. Implementatie wacht op bevestiging van provider, tenant, identity-owner, deployment en claimmapping. De demo-actor en actorvelden zijn geen authenticatie; de prototype-API blijft onbeschermd en mag alleen met synthetische data worden gebruikt. |
| SEC-002 Autorisatie en functiescheiding | **Gereed in prototype; productioneel geblokkeerd** | Feature 10 en review-evidence zijn gemerged, maar de rolmatrix, echte identiteit, formele bevoegdheden en periodieke toegangsreview zijn niet bevestigd. |
| AUD-001 / DOC-001 Audit en bewijsreferenties | **Gereed in prototype; productie-open** | Features 11–12 zijn gemerged met append-only audit en versiegebonden documentmetadata. Immutability, retentie, toegangsbeperking en productieopslag zijn nog gates. |
| P2–P7 — keten, ESG, reporting, Wtp, fees, twin en exports | **Prototype-slices gereed** | Features 13–47 zijn gemerged met fase-evidence en onafhankelijke review. Dit bewijst de prototype-acceptatiecriteria, niet productie-integratie, juridische toepasselijkheid of operationele readiness. |
| P8 — performance en benchmarks | **Features 48–51 gereed; vervolg gepland** | PERF-001, PERF-002, BENCH-001 en BENCH-002 zijn gemerged. BENCH-003 (Feature 52) staat gepland; PORT-001 t/m GOV-002 (Features 53–62) zijn nog niet uitgevoerd. |

**Volgende backlogstap:** Feature 1 — domein- en legal discovery — is gestart als Kanban-taak `t_3151cf55`; vóór implementatie moet de discovery zijn opgeleverd en onafhankelijk beoordeeld. SEC-001 blijft geblokkeerd totdat de identity-owner de provider (Entra ID of enterprise OIDC), tenant, deployment, app registration, secretsbeheer en claimmapping bevestigt. Daarna kan SEC-001 volgens ADR-0005 worden ingepland en uitgevoerd. SEC-002 autorisatie/RBAC blijft een aparte stap waarvoor de rolmatrix expliciete goedkeuring nodig heeft. De CFG-002-inventarisatie voor het huidige prototype omvat hoofdconfiguratie, entiteiten/relaties, klantvereisten, DORA-assessments en controls/beleid. Bronreviews, besluiten, audit en exports zijn gebeurtenis-/transactieregisters en worden niet met een verzonnen geldigheidsperiode verrijkt. Historie vóór migratie en productie-hardening blijven een P1-gereedheidskloof, niet een prototypefeature. Tijdconventies staan in ADR-0002 en ADR-0003; schemaversies staan in ADR-0004. Formele beleidscriteria blijven te valideren door Compliance/Legal.

**Actuele volgende backlogstap (2026-11-06):** voer Feature 52 — BENCH-003 Beschikbaarheid en timing — uit en laat deze onafhankelijk reviewen. Leg eerst de klant-/mandaatbesluiten vast over markt- en indexkalenders, cutoffs en toegestane proxy's; proxydata mag niet als definitieve waarneming worden gepresenteerd. Daarna volgen PORT-001 t/m GOV-002 lineair. SEC-001 blijft een afzonderlijke menselijke gate totdat de identity-owner provider, tenant, deployment, app registration, secretsbeheer en claimmapping bevestigt; SEC-002 blijft afhankelijk van een goedgekeurde rolmatrix.

De oorspronkelijke migratienotitie hierboven is historische context; deze actuele status is leidend.

## Productdoel en afbakening

De applicatie wordt de bron voor contractuele en operationele klantbedieningsafspraken: welke klant/entiteit welke dienst ontvangt, onder welke mandaat-, prijs-, SLA-, rapportage-, duurzaamheids-, uitbestedings- en governancevoorwaarden. Operationele systemen blijven voorlopig leidend voor posities, performance, factuuruitvoering en rapportageproductie.

De tool ondersteunt bewijsvoering, configuratievalidatie, workflow en signalering. De tool vervangt geen juridische interpretatie, fondsbestuur, professioneel oordeel, complianceprogramma of DNB/AFM-melding. Een policy wordt pas een harde blokkade nadat de eigenaar en Compliance/Legal de precieze regel, bron, reikwijdte en uitzonderingsroute hebben goedgekeurd.

**Buiten scope tenzij apart besloten:** transacties uitvoeren, pensioenadministratie/deelnemersdata beheren, zelf SFDR-rapportages namens klanten opstellen, zelfstandig manager ESG-ratings bepalen, juridische contracten redigeren/ondertekenen, of namens het fonds toezichthoudersmeldingen indienen.

## Prioriteiten en releasevolgorde

1. **P0 — Product- en compliancebesluiten vóór harde controles:** bevestig klantsegment, rolmodel, bron van data, schema-eigenaren, DNB-meldingsproces, bewaartermijn en partnerpilot. Leg beslissingen vast in ADR’s. Alle open juridische/beleidsvragen blijven zachte signalen of handmatige taken.
2. **P1 — Productionwaardige configuratiebasis:** vervang demo-identiteit en SQLite voor productiegebruik; introduceer PostgreSQL, echte SSO/RBAC, transactionele bitemporele opslag, append-only audit, schemavalidatie en documentreferenties. Geen echte klantdata in repo/fixtures.
3. **P2 — Contractuele uitbesteding en managerketen:** modelleer uitbestede activiteiten, asset managers, fiduciary manager, custodian, onderuitbesteders en contractuele rechten/verplichtingen. Voeg wijzigingsimpact en meld-/reviewworkflow toe.
4. **P3 — Verantwoord beleggen en manager due diligence:** voeg fondsbeleid, selectie-/behoudcriteria, OESO/UNGP-afspraken, ESG-data, incidents, engagement, remedies, jaarlijkse beoordelingen en bewijs toe.
5. **P4 — Rapportage, SFDR/PAI en comply-or-explain:** configureer datapunten en rapportageverplichtingen per klant/mandaat/manager inclusief rapportagekalender, kwaliteit, afwijkingen en opvolging.
6. **P5 — Wtp-keten/transitieafspraken:** beheer transitieprogramma-afspraken, data- en procesafhankelijkheden, rollen, mijlpalen, risico’s, data voor/tijdens/na transitie en gereedheidsbewijzen.
7. **P6 — Vergoedingen en transparantie:** breid fee-model en simulatie uit met staffels, minimums, performance fees, valuta, overige kosten en externe-manageroverzichten/look-through waar contractueel gevraagd.
8. **P7 — Digital twin, exports en integraties:** hergebruik productie-domeinlogica voor multi-domeinsimulatie; lever versiegebonden partnerbestanden en API’s met ontvangststatus, reconciliatie en monitoring.
9. **P8 — Performance-inrichting en rapportageketen:** leg methodiek en benchmarks per mandaat vast; bouw een gevalideerde portfolio-input-, berekenings-, datawarehouse- en BI-keten met FactSet-route pas na verificatie van de beschikbare omgeving.

## Features en acceptatiecriteria

### P0 — Discovery en policy governance

- **POL-001 Besluitenregister — gereed in prototype:** leg per control vast: eigenaar, doelgroep, bron/artikel of klantcontract, toepasselijkheid, harde/zachte/handmatige afhandeling, ingangsdatum, versie en reviewdatum.
- **POL-002 Broncontrole — gereed in prototype:** registreer bronreview append-only per controlversie (brontype, titel, locator, reviewer/rol, uitkomst, motivering en tijdstip). `secondary_guidance`, gebruikersclaims en gegenereerde tekst mogen niet als geverifieerde primaire bron gelden. Een aparte policybeslissing kan alleen na geverifieerde primaire bron, klantcontract of vastgesteld klantbeleid; reviewer en beslisser moeten verschillende actoren zijn. Nieuwe bronreview na validatie zet de afgeleide validatiestatus terug op `pending`. Dit is een menselijke reviewworkflow, geen juridische broninterpretatie; demo-actoren zijn niet production-ready.
- **POL-003 Klantvarianten — gereed in prototype:** leg per klant/fonds contractuele ESG/SFDR/PAI-, Wtp-, rapportage-, disclosure-, kosten- en keten-/uitbestedingsvereisten vast met bronreferentie, scopebeschrijving, frequentie, geldigheids- en reviewdatum, actor en motivering. Een optioneel expliciet configuratiepad en verwachte waarde tonen `configured_match`, `configuration_gap`, `unmapped` of `manual_review`; dit automatiseert geen contractinterpretatie en bewijst geen compliance. Geen universele verplichting afleiden uit één fondsvoorbeeld.
- **POL-004 DORA-classificatie — gereed in prototype:** leg afzonderlijk vast (a) vermogensbeheeractiviteit/dienstverlening, (b) ICT-dienst door derde leverancier en (c) eigen applicatie-/cloud-/ICT-dienst. Per beoordeling worden klantrelatie (optioneel voor eigen platform), partij, dienst, scope, menselijke toepasselijkheidsstatus, menselijke kritikaliteitsbeoordeling, contract-/bronreferentie, reviewer/rol, motivering en reviewdatum vastgelegd. Beoordelingen zijn append-only versieerbaar; herbeoordeling start opnieuw met status `pending_review`. Er is geen DORA-classificatiealgoritme of wettelijke conclusie. Compliance/Legal en ICT-risk stellen criteria, impact en contractvereisten vast.

**Acceptatie:** voor elke automatische blokkade bestaat een goedgekeurde policyversie met scope, eigenaar en tests; nog niet goedgekeurde interpretaties zijn niet-blokkerende signalen.

**POL-002 prototype-acceptatie gecontroleerd:** secundaire bron als geverifieerd geweigerd; policybesluit zonder geverifieerde bron geweigerd; synthetische klantbronreview en afzonderlijk besluit succesvol vastgelegd; bronreviewhistorie blijft beschikbaar. Productiegebruik vereist echte SSO/rollen, formele bevoegdheden, opslagbeveiliging en Compliance/Legal-goedkeuring van bronclassificaties en retentie.

**POL-003 prototype-acceptatie gecontroleerd:** drie synthetische contractvereisten opgeslagen en via de browser getoond; exacte configuratiewaarde toont “Waarde ingesteld · review vereist”, afwijkende deadline toont “Configuratie wijkt af” met verwachte en actuele waarde, en een vereiste zonder gekoppeld configuratiepad toont “Handmatige reconciliatie”. Een correctie maakt een nieuwe append-only versie; writes verschijnen in audit. De formulierflow behoudt na opslaan de gekozen klant en categorie. Contractbestand/OCR, semantische mapping, formele contractreview en echte klantdata zijn niet inbegrepen.

**POL-004 prototype-acceptatie gecontroleerd:** via de browser zijn synthetische beoordelingen voor alle drie perimeters vastgelegd; een derde-ICT-beoordeling is herzien van v1 naar v2 met auditregistratie; de eigen-platformbeoordeling kan zonder klant/fonds worden opgeslagen; alle writes geven HTTP 201 en de registerlezingen HTTP 200. Beoordelingsuitkomsten zijn testinvoer, geen Compliance/Legal-conclusies. Productie vereist gevalideerde juridische criteria, formele rollen, leveranciers-/ICT-registerintegratie en retentiebeleid.

### P1 — Bronconfiguratie, autorisatie en audit

- **CFG-001 Entiteiten en relaties — gereed in prototype:** koppel versieerbare juridische entiteiten, groepen, fondsen, fiduciairs, managers, submanagers, custodians en dienstverleners aan klantconfiguraties. Bewaar jurisdictie, classificatie, optionele identifier, geldigheidsdata, bronreferentie en motivering; modelleer gerichte relaties (groep-/moederrelatie, fiduciary-for, beheert, subdelegeert, custody-for, service-provider-for en client-of) met dienstscope en geldigheid. Klanttype/jurisdictie/classificatie van de hoofdklant blijven op klantrecord. Records worden niet verwijderd; nieuwe versies en auditregels bewaren correcties. De prototypegraaf is per klant gescopeerd; enterprise-entity resolution en volledige bitemporele reconstructie vallen onder CFG-002.
- **CFG-002 Bitemporele revisies — gedeeltelijk gereed in prototype:** voor de hoofdklantconfiguratie in `config_versions` combineert de tijdreisquery `valid_at` met `known_at`. Append-only kennis-snapshots bewaren de geldigheidssegmenten die op dat transactietijdstip bekend waren. CFG-001-entiteiten/relaties en klantvereisten staan in dezelfde append-only klantregistersnapshot. De snapshot bewaart alle bekende vereisteversies; de query kiest per vereiste de versie met de laatste `effective_date` die op `valid_at` ingaat. `review_date` wordt niet als `valid_to` geïnterpreteerd. De versieerbare route staat in `schemas/client-requirements-api-v1.json`. DORA-assessments bewaren elke beoordeling als append-only versie met `created_at` als transaction-time en reviewer-invoer `effective_from`/optioneel exclusief `effective_to` als valid-time. Controls/beleid kiezen per `control_code` de laatst bekende versie (`created_at <= known_at`) met de nieuwste inclusieve `effective_date` die op `valid_at` is ingegaan; bronreviews en besluiten zijn begrensd op hun transaction-time. `schemas/dora-assessments-api-v1.json` vereist `valid_at` en UTC `known_at`; de tijdreis selecteert de laatste bekende assessmentversie en toetst de expliciete geldigheidsperiode. `review_date` is alleen reviewdeadline. Legacyrecords zonder geldigheidsdata blijven onveranderd en worden als `unset_legacy` getoond; historie wordt niet afgeleid. Deze prototypeconventies staan in ADR-0002 en ADR-0003 en stellen geen juridische toepasselijkheid vast; criteria te valideren door Compliance/Legal en ICT-risk. Eventregisters (bronreviews, besluiten, audit en exports) bewaren transactietijd; historie vóór migratie en productie-retentie-/immutability-beveiliging blijven open.
- **CFG-003 Getypeerde parameterdefinities — gereed in prototype:** `schemas/configuration-v1.json` definieert versie, ingangsdatum, type, eenheid, range, vereiste bewijsreferentie, afhankelijkheden en eigenaar voor kernparameters. Een append-only SQLite-catalogus bewaart schema-inhoud en registratietijd; configuratie- en changeversies pinnen de schemaversie. Create, activation en export valideren server-side; `GET /api/v1/config-schemas[/<version>]` toont definities en `POST /api/v1/configurations/validate` geeft foutpaden terug en audit actor, reden, resultaat en payloadhash. De browsercatalogus kan een synthetische configuratie inspecteren en valideren zonder opslag. Dit is een beperkte JSON Schema-subset zonder runtime-dependency; concrete eigenaarstoewijzing en klant-/mandaatspecifieke normen zijn te valideren. Niet-gemodelleerde extensies worden niet als gecontroleerd gepresenteerd.
- **SEC-001 Echte identiteit — voorbereiding vastgelegd in ADR-0005; implementatie open:** bevestig met de identity-owner Microsoft Entra ID of de enterprise OIDC-provider, tenant, app registration, stabiele `iss` + `sub` actor-mapping, deployment en secretsbeheer. De server leidt actor-identiteit af uit een gevalideerde provider-sessie; caller-provided actor strings zijn nooit autoritatief. Implementeer pas na providerkeuze en voldoe aan de ADR-acceptatiecriteria. Demo-authenticatie blijft uitgeschakeld en is geen beveiligingsgrens.
- **SEC-002 Autorisatie en functiescheiding:** RBAC, waar nuttig ABAC, initiator ≠ goedkeurder, beperkte adminrollen en periodieke toegangsreview.
- **AUD-001 Append-only audit:** actor, actie, tijd, oude/nieuwe waarde, reden, bronbewijs, policy-/schema-versie, simulatie, goedkeuring, activatie en export/publicatiestatus.
- **DOC-001 Bewijs:** versiegebonden documentreferenties met documenttype, datum, eigenaar, vertrouwelijkheid en retentieklasse; geen contractbestand of klantgegeven in git.

**Acceptatie:** autorisatie wordt server-side afgedwongen; historische configuratie is reconstrueerbaar; records zijn niet hard te verwijderen; audit is niet wijzigbaar via reguliere product-API.

**CFG-002 prototype-acceptatie voor de hoofdklantconfiguratie gecontroleerd:** browserquery toont de baselinesnapshot; een geactiveerde synthetische wijziging met toekomstige ingangsdatum reconstrueert v1 op basis van kennis vóór activatie en v2 op basis van kennis erna, voor dezelfde `valid_at`-datum. Snapshot bevat valid-time segmenten, actor, reden en activatiereferentie. Historie vóór de migratiesnapshot is niet reconstrueerbaar en wordt niet als beschikbaar gepresenteerd. Alleen synthetische demo-data gebruikt.

**CFG-002 prototype-acceptatie voor entiteiten en relaties gecontroleerd:** de graafweergave reconstrueert actieve entiteiten en relaties met afzonderlijke `valid_at`- en `known_at`-waarden. Een synthetische vermogensbeheerder en relatie zijn via de browser opgeslagen; audit en graafsnapshot zijn samen zichtbaar. Voor dezelfde geldigheidsdatum toont `known_at` vóór de entiteitsregistratie de migratiesnapshot zonder manager en `known_at` erna snapshot v2 met de manager. `known_at` op secondeprecisie neemt subsecond-audittijden binnen die seconde mee. Graafsnapshots zijn append-only. Latere CFG-002-slices voegen klantvereisten, DORA-assessments en controls/beleid toe; bestaande historie vóór migratie is niet reconstrueerbaar.

**CFG-002 prototype-acceptatie voor klantvereisten gecontroleerd:** synthetische vereiste geregistreerd met ingangsdatum in de toekomst; vóór `known_at` is deze afwezig, na registratie maar vóór `effective_date` blijft zij inactief, en vanaf de ingangsdatum verschijnt dezelfde versie. De auditregel en append-only klantregistersnapshot worden samen geschreven. Bestaande vereisteversies krijgen bij migratie een baseline; eerdere transaction-time is niet reconstrueerbaar. `review_date` blijft een reviewdeadline en sluit de geldigheid niet automatisch af. DORA-assessments en controls/beleid zijn daarna als afzonderlijke CFG-002-registers toegevoegd.

**CFG-002 prototype-acceptatie voor DORA-assessments gecontroleerd:** browserformulier heeft een synthetische beoordeling append-only opgeslagen met expliciete `effective_from`; API v1 filtert op `valid_at` en `known_at`. Browserquery met een kennisdatum vóór registratie gaf geen beoordeling; na opslag werd de beoordeling getoond. Geïsoleerde databaseasserties controleerden startdatum inclusief, einddatum exclusief, klantfilter, versieherziening en delete-trigger. HTTP-log bevatte alleen 200/201 voor de feature. Legacyrecords zonder valid-time blijven als onbekend gemarkeerd. Juridische criteria blijven te valideren door Compliance/Legal en ICT-risk.


**CFG-002 prototype-acceptatie voor controls/beleid gecontroleerd:** tijdreisfilters reconstrueren per controlcode de effectieve versie zoals bekend op `known_at`; bronreviews en besluiten van later worden niet in een oudere snapshot getoond. Een synthetische control met ingangsdatum 2026-11-10 bleef afwezig vóór registratie en vóór de ingangsdatum, en verscheen erna. SQLite-triggers blokkeren update/verwijdering van controls, bronreviews en besluiten. Browser-HTTP-log bevatte alleen 200/201.

**API-contracten:** `GET /api/v1/customers/{customer_id}/client-requirements` en `GET /api/v1/dora-assessments` vereisen `valid_at` en UTC `known_at`. Registerhistorie voor klantvereisten staat in `GET /api/v1/customers/{customer_id}/register-history`. Contracten: `schemas/client-requirements-api-v1.json`, `schemas/dora-assessments-api-v1.json`, `schemas/policies-api-v1.json` (`GET /api/v1/policies`) en `schemas/config-schemas-api-v1.json` (`GET /api/v1/config-schemas`, `POST /api/v1/configurations/validate`); de bestaande `/api/client-requirements`-route houdt zijn huidige antwoordvorm voor actuele registerlezingen.

**CFG-003 prototype-acceptatie gecontroleerd:** de browser toonde schema v1 met kernparameterdefinities, types, eenheden, ranges, afhankelijkheden en eigenaarschap. Een synthetische configuratie valideerde zonder fouten; een gedeeltelijke JSON met `fees.bps` als string toonde typefout en ontbrekende verplichte velden met veldpaden. Beide validatieresultaten zijn geaudit op actor, reden, versie, uitkomst en SHA-256, zonder payload in audit of wijziging aan klantconfiguratie. Geïsoleerde controles bevestigden seedvalidatie, versie-pin bij change/activation/export, append-only schemaregistratie en historische schema-referentie. De browserserverlog bevatte alleen HTTP 200 voor API-reads en validatieresponsen.
**CFG-001 prototype-acceptatie gecontroleerd:** via de browser zijn synthetische fonds-, groep-, fiduciair-, vermogensbeheerder-, submanager- en custodianrecords vastgelegd en twee relaties getoond (fiduciair voor fonds; fonds is lid van groep). Entiteitscorrecties zijn als nieuwe versies geregistreerd; relaties vereisen bestaande entiteiten binnen dezelfde klant en wijzen niet naar zichzelf. Auditregels zijn zichtbaar. De volledige P1-acceptatie voor productie blijft open.

### P2 — Uitbesteding en due diligence van de keten

- **OUT-001 Activiteitregister:** per relatie de concrete werkzaamheden, grenzen, betrokken diensten, fonds-/mandaatrelatie, kritikaliteit/materialiteit, eigenaar en contractperiode vastleggen.
- **OUT-002 Ketenregister:** directe en indirecte aanbieders, diensten, datastromen, geografische/juridische entiteiten, contractrelaties en onderuitbesteders kunnen volgen. Wijziging van een schakel identificeert geraakte klanten/mandaten.
- **OUT-003 Contractuele minimumvelden:** aansprakelijkheid, overdracht van rechten/verplichtingen, dooruitbesteding (partij/dienst/voorwaarden), informatie-uitwisseling, monitoring, audit/controlerechten, informatieverstrekking en toegang voor toezichthouders, evaluatie, looptijd, exit/continuïteit en gedetailleerde kosten.
- **OUT-004 Selectie- en periodieke beoordeling:** selectiecriteria, vergunning/certificering waar relevant, financiële soliditeit, continuïteit, risicobeheer en integriteit als configureerbare klant-/fondscriteria met bewijs en reviewcyclus.
- **OUT-005 Melding en wijzigingssignalering:** status, datum, eigenaar en referentie van eventuele fonds-/toezichthoudermelding vastleggen. Trigger menselijke controle bij onboarding, kritieke scopewijziging, relevante onderuitbesteding en offboarding. Geen automatische verzending naar DNB in deze release.
- **OUT-006 DORA/ICT-loskoppeling:** afzonderlijke ICT-providerrelatie, ICT-dienst, kritieke/belangrijke functieclassificatie, contract-/registervelden en incident-/exitbewijs als de klant-/eigen toepasselijkheid is vastgesteld.
- **OUT-007 Governance en countervailing power:** fondsbeleid, monitoringfrequentie, rapportage, escalatie, onafhankelijke evaluatie, capaciteit en evaluatiedatum kunnen worden vastgelegd.

**Acceptatie:** een fonds-/mandaatwijziging toont de complete relevante keten, missende contractvelden, huidige review-/meldstatus en afhankelijkheden. Meldingstaken vereisen eigenaar, deadline en bewijs van afronding. Thresholds (waaronder DNB’s genoemde 30%-verwachting) zijn bronverwijzingen/policyparameters, niet universeel hardcoded.

**Validatie:** interpretatie van Pensioenwet art. 34, Wft art. 3:18, Besluit uitvoering Pw/Wvb, Besluit prudentiële regels Wft, kritikaliteit en meldplicht: te valideren door Compliance/Legal voor relevante klant/partij.

### P3 — Verantwoord beleggen en ESG-manager lifecycle

- **ESG-001 Beleidsprofiel:** per klant/fonds en mandaat het geldende MVB/ESG-beleid, doelen, prioriteit (bijv. rendement/risico/duurzaamheid), asset-class scope, versie en bronbewijs.
- **ESG-002 Manager selectie en behoud:** criteria zoals minimum ESG-rating, uitsluitings-/insluitingsbeleid, ESG-integratie, klimaat/natuur/mensenrechten, 3D/impacttargets, drempelwaarden, uitzonderingen en reviewmomenten.
- **ESG-003 Contractuele flow-down:** verplichtingen kunnen worden gekoppeld aan directe manager én diens ondermanagers; clausules voor OESO/UNGP, due diligence, medewerking, rapportage, incidentmelding, data-/positie-inzicht, herstel en escalatie.
- **ESG-004 Due diligence dossier:** workflow vastleggen voor beleidssystemen, identificatie/prioritering van negatieve impacts, voorkomen/beperken, monitoring/resultaten, communicatie en herstel; documenteer menselijk oordeel, bevindingen, actiehouder en deadline.
- **ESG-005 Engagement en incidenten:** incident/controverse, bron, ernst, betrokkenheid/relatie, engagementdoel, voortgang, acties, remedie, afsluiting en eventuele managerbehoud-/exitbeslissing.
- **ESG-006 Periodieke beoordeling:** jaarlijkse (of klantafgesproken) beoordeling van managers, ESG-risico’s, resultaten en verbeteracties; afwijking/uitstel met motivering en escalatie.

**Acceptatie:** bij manager onboarding en jaarlijkse review zijn toepasselijke criteria zichtbaar en bewijsbaar; uitzonderingen hebben rationale, goedkeurder en einddatum; een wijziging van klantbeleid laat zien welke managers/mandaten en rapportageprofielen geraakt worden.

**Validatie:** OESO/UNGP/IMVB-invulling per klant en contract, beoordelingsmethodologie, ESG-ratingbron en beslisdrempels: te valideren door klantbeleidseigenaar en Compliance/Legal. Het verlopen IMVB-convenant wordt niet als zelfstandige actuele wettelijke verplichting gemodelleerd; fondsbeleid kan wel blijven verwijzen naar afspraken daaruit.

### P4 — SFDR/PAI en verantwoordingsrapportages

- **RPT-001 Rapportagecatalogus:** type, metric/data-item, definitie, eenheid, perimeter, portefeuille-/manager-scope, berekeningsbron, frequentie, deadline, taal, template en ontvangers.
- **RPT-002 Data-aanleverafspraak:** welk fonds, fiduciair, manager, submanager of derde datapartner levert welk veld, over welke periode, via welk kanaal en met welke validatie/bewijs.
- **RPT-003 SFDR/PAI-profielen:** configureerbare PAI-indicatoren/datavragen, referentieperiode, rapportagefrequentie, methodologie, datadekking, ontbrekende-datareden, assurance/bewijs en verantwoordelijkheden. Geen vast PAI-profiel zonder gevalideerd toepassingsbesluit.
- **RPT-004 Comply-or-explain:** per code/richtlijn compliance status, uitleg bij afwijking, geldigheidsperiode, impact, goedkeurder en follow-upactie.
- **RPT-005 Rapportage-uitvoering:** kalender, aanleverstatus, volledigheid, datakwaliteitsfouten, vertraging, incident/herstel, escalatie en goedgekeurde eindrapportreferentie.
- **RPT-006 Transparantie-/disclosure-output:** export van contractuele managergegevens en datadekking waar openbaarmaking of klantverantwoording is afgesproken; confidentiality flags en toestemming voor openbaarmaking ondersteunen.

**Acceptatie:** rapportagedeadlines genereren taken; een ontbrekende of afwijkende input is zichtbaar met eigenaar en gevolg; PAI-/SFDR-export is reproduceerbaar met schema- en methodologieversie; het systeem doet geen ongefundeerde juridische SFDR-classificatie.

**Validatie:** toepasselijkheid SFDR, rollen als financiëlemarktdeelnemer, indicatoren/methodologie en openbaarmaking: te valideren door Compliance/Legal. SFDR (EU) 2019/2088 en toepasselijke gedelegeerde regels zijn bron-/versiereferenties, geen ingebakken aanname dat iedere klant hetzelfde rapporteert.

### P5 — Wtp-transitie en ketensamenwerking

- **WTP-001 Transitieprofiel:** fondsregeling/transitiefase, planning, scope, relevante besluit-/go-live-/invaardata en eigenaar.
- **WTP-002 RACI en afhankelijkheden:** fonds, PUO, fiduciair, manager, custodian en technologiepartijen met taken, input/output, handoff, afhankelijkheid en escalatie.
- **WTP-003 Data voor/tijdens/na:** vereiste data-items voor transitie en beheer, eigenaar/bron, frequentie, validatieregel, reconciliatie, datakwaliteitsnorm, bewijs en continuïteit/terugvalafspraak.
- **WTP-004 Mijlpalen en gereedheidscriteria:** deliverables, planning, validatiecriteria, periodieke voortgangsrapportage, risico/effect op kritieke tijdslijn, herstelplan en gezamenlijke go/no-go-bewijsstukken.
- **WTP-005 Risico’s en wijzigingsbeheer:** transitiegerelateerde operationele, data-, IT-, financiële en ketenrisico’s, beheersmaatregelen en wijzigingsimpact over mandaat en reporting heen.

**Acceptatie:** een Wtp-gerelateerde servicewijziging toont partijrollen, benodigde data, ontbrekende interfaces, kritieke mijlpalen en status van bewijs. De applicatie wordt geen pensioenadministratie- of invaren-rekenplatform.

**Validatie:** fondsspecifieke datalijst, rekenverantwoordelijkheid, validatiecriteria en wettelijke interpretatie (onder meer toepasselijke PW/BuPW-bepalingen): te valideren door klant, pensioenexpert en Compliance/Legal.

### P6 — Fees, performance fees en kosten-/managertransparantie

- **FEE-001 Fee-componenten:** AUM-tarieven, staffels, minimums, vaste fees, performance fees, hurdle/high-water mark, kortings-/side-letterafspraken, valuta, accrual-/factuurfrequentie en indexatie.
- **FEE-002 Rekenregels:** expliciete grondslag, meetperiode, waarderings-/AUM-input, valuta-omrekening, afronding, caps/floors en contractuele randgevallen; versieerbare en gedeelde rekenfuncties.
- **FEE-003 Kostenoverzicht:** directe fees, performance fees en overeengekomen overige kosten; bron, ontvanger, periode en allocatie naar klant/mandaat/product.
- **FEE-004 Externe managerlijst/look-through:** manager, fonds/vehikel, mandaat, asset class, AUM/coverage-datum en disclosure-permissie; datadekking is zichtbaar en mag niet als universele 95%-norm worden gecodeerd.
- **FEE-005 Simulatie:** vergelijk baseline/scenario op manager-, product-, klant- en totaalniveau; toon ontbrekende input en onzekerheid. Verifieer dat productie- en twin-berekening dezelfde domeinfunctie gebruiken.

**Acceptatie:** fixtures met synthetische data controleren staffels, minimums, performance fee, FX, rounding en geldigheid; een export bevat datum/perimeter/coverage zodat cijfers herleidbaar zijn.

### P7 — Twin, API/export en integraties

- **TWIN-001 Change-as-code:** declaratieve diff met basisversie, ingangsdatum, rationale, bewijs, schema- en policyversie.
- **TWIN-002 Isolatie en reproduceerbaarheid:** scenario bevat onveranderlijke snapshot, inputs, rekenlogica-, policy- en schema-versie; geen writes naar productie tijdens simulatie.
- **TWIN-003 Impact:** fees/kosten, contract/keten, ESG, Wtp-tijdlijn/data, reportkalender/capaciteit, compliance-signalen en afhankelijkheden; baseline-/scenariovergelijking en time-travel.
- **EXP-001 Partnerprofielen:** versiebeheer voor JSON/CSV/partnerformaten, veldmapping, validatie, classificatie/privacyfilter en schema-contracttests.
- **EXP-002 Publicatiestatus:** alleen geautoriseerde, goedgekeurde en effectieve configuratie publiceren; export-ID, checksum, snapshot/schema/mappingversie, actor, tijd, target en ontvangst-/verwerkingsstatus bewaren.
- **INT-001 Koppelingen:** kandidaatbronnen zijn portefeuille-/performanceplatform, FactSet, facturatie, ADLS Gen2 en Power BI; per koppeling data owner, richting, frequentie, contract, privacyclassificatie en reconciliatie bevestigen vóór bouwen.

**Acceptatie:** dezelfde snapshot en inputs produceren identieke uitkomsten; exportbestand en API-payload zijn inhoudelijk equivalent; mislukte/duplicaatlevering is herhaalbaar en auditeerbaar.

### P8 — Rendementsmethodiek, benchmarks, portefeuilledata en performancepipeline

**PERF-001 Rendementsmethodiek per mandaat:** configureer en versioneer rendementsmethode (bijv. TWR voor liquide en Modified Dietz of IRR/MWR voor illiquide, afhankelijk van klantbeleid), cashflow-timing BOD/EOD, geometrische periodenkoppeling, bruto/netto-definitie en fee-accrual, waarderingsbasis (trade/settlement date, clean/dirty), koersbron/tijdstip, basis- en rapportagevaluta, FX-bron/fixing, lokaal/valuta/totaalrendement, derivaten/overlay-conventie, rapportageperioden (MTD/QTD/YTD/1Y/3Y/ITD), annualisatie en inception date. Geen standaardmethode als klant-/mandaatbeleid nog niet is vastgesteld.

**PERF-002 Pensioenspecifieke portefeuille-indeling:** modelleer return-portefeuille en matching-/LDI-portefeuille afzonderlijk; leg swaps/renteoverlay, hedge-return versus onderliggende beleggingen, verplichtingenbenchmark/rentetermijnstructuur en afgesproken dekkingsgraad-/hedge-ratio-indicatoren vast.

**BENCH-001 Benchmarkdefinitie:** index-ID en aanbieder, total/net/price-return-type, valuta en hedge-status. Samengestelde benchmarks bevatten componenten, gewichten, rebalancefrequentie (daily/monthly/quarterly/buy-and-hold) en geldigheidsdata.

**BENCH-002 Bitemporele benchmarkwijziging:** leg ingangsdatum en keuze “historie herzien” versus “doorlinken” expliciet vast. Elke wijziging bewaart wat gold en wat wanneer bekend was; oude performance-uitkomsten blijven herleidbaar naar benchmark- en methodiekversie.

**BENCH-003 Beschikbaarheid en timing:** leg markt-/indexkalender, close-/NAV-cutoff en indexfrequentie vast. Voor indices met vertraagde of kwartaaldata (zoals private markets) wordt een goedgekeurde proxy-regel, bron, statusflag en toepassingsperiode vastgelegd; toon proxydata niet als definitieve waarneming.

**PORT-001 Identifiers en hiërarchie:** fonds → klant → mandaat → portfolio/subportfolio → asset class → manager → composite. Beheer versieerbare mappings tussen interne klant-/mandaat-ID’s en externe broncodes, inclusief FactSet-portfolio-code alleen na verificatie van de lokale omgeving.

**PORT-002 Invoercontract:** definieer bron, schema, frequentie, timestamp en definitiestatus voor posities, transacties, cashflows, corporate actions, accruals en fees. Elke input heeft herkomst en as-of/periode.

**PORT-003 Datakwaliteit en correcties:** reconciliatie met custodian; checks voor rendement-uitbijters, ontbrekende prijzen, stale FX en grote cashflows; voorlopige versus definitieve status. Correcties maken een nieuwe input- en berekeningsversie aan en overschrijven de eerdere dag niet.

**CALC-001 Berekenings-/attributieprofiel:** indien berekening in FactSet of een andere vastgestelde engine plaatsvindt, configureer requestvariant, account, benchmark, datumrange, frequentie, valuta, groepering, gewenste return-/benchmark-/weight-/contribution-/attributionvelden en gebruikte methode. Attributieprofiel omvat gekozen Brinson-variant, sector-/regiohiërarchie en waar nodig fixed-income duration/curve/spread-decompositie. Kies en versioneer geometrische attributiekoppeling, bijvoorbeeld Carino of Menchero; neem geen methode aan zonder klant-/modelbesluit.

**CALC-002 Herleidbare run:** archiveer request, ruwe response, parameter-/benchmark-/schema-versies, brondatareferenties, rekentijd en status in een onveranderlijke runreferentie. Ruwe data kan naar ADLS Gen2 bronze indien platform, privacy, contract en retentie zijn bevestigd; gevalideerde/normaliseerde gegevens gaan naar silver en BI-/rapportageklare gegevens naar gold. De applicatie bewaart links/checksums en niet onnodig een tweede kopie.

**CALC-003 Orkestratie:** plan runs nadat prijzen en FX beschikbaar zijn; gebruik idempotente run-ID’s, herhaalbare retries, fout-/rate-limitstatus en beheerste authenticatie. ADF of Fabric pipelines zijn kandidaten, nog geen vaststaande keuze. Correcties op input starten een expliciet nieuwe run.

**BI-001 Power BI-model:** definieer facttabellen voor dagelijkse performance, attributie en allocatie plus dimensies voor handelsdatum/-kalender, portfolio/mandaat, klant, benchmark, asset class, valuta en versie/as-of. Centrale datalaag bevat gecontroleerde berekeningen (cumulatief en periodiek rendement, excess return, tracking error, information ratio, attributie en allocatie versus beleid/bandbreedtes); geen dubbele, afwijkende berekeningslogica in DAX.

**BI-002 Dashboard en toegang:** toon cumulatief rendement versus benchmark, afgesproken periodetabel, excess return, attributie, tracking error/information ratio, allocatie versus beleid, laatste update, voorlopige/definitieve status en meetperiode. Klanttoegang via Entra ID/RLS en guest/embedded toegang alleen na expliciet security-/privacybesluit en klantisolatietest.

**GOV-001 Indicatief versus officieel:** dagelijkse cijfers blijven als voorlopig gemarkeerd. Contractuele maand-/kwartaalrapportages volgen de afgesproken kalender; officiële perioderesultaten krijgen vastgelegde review/goedkeuring en worden daarna gelockt. Restatements/correcties worden als nieuwe versie gepubliceerd met herleidbare reden en vergelijking.

**GOV-002 Methodedocument:** per klant/mandaat exporteer een goedgekeurde methodenota met rendements- en feegrondslag, waardering, cashflowtiming, FX, benchmark, attributie, perioden, brondata, kalender, provisional/final-status en wijzigingshistorie.

**Acceptatie:**
- Dezelfde brondata, methodiek-, benchmark- en engineversie levert reproduceerbare resultaten op; wijziging van methodiek of benchmark maakt een nieuwe herleidbare versie.
- BOD/EOD, bruto/netto, fee-accrual, FX-fixing, gehedged/ungehedged en trade/settlement-date configuraties zijn onderling gescheiden en zichtbaar in rapportmetadata.
- Missing/stale inputs en proxydata blokkeren of markeren official close volgens een door de klant goedgekeurde kwaliteitsregel.
- Custodian-reconciliatie, uitbijtercontroles, correcties en voorlopige/definitieve status zijn zichtbaar en auditeerbaar.
- Power BI RLS-tests bewijzen dat een klant uitsluitend de toegewezen klant-/mandaatdata kan zien.
- ADLS raw request/response, silver normalisatie en gold outputs zijn aan dezelfde performance run en parameterversie gekoppeld, als ADLS als opslag is bevestigd.
- Portfolio-/benchmarkrendement en attributie worden niet op twee plekken met afwijkende formules berekend; golden-master en contracttests controleren overeengekomen output.

**FactSet-validatie:** de termen “PA Engine”, “Analytics API” en “SPAR” zijn aangeleverd vanuit gebruikerskennis en zijn nog niet bevestigd voor de eigen FactSet-tenant, licenties, API’s of architectuur. Fase 0 moet met de FactSet-beheerder bepalen welke dienst beschikbaar is, welke request-/responsevelden en berekeningsmethoden ondersteund zijn, welke marktdata- en portfolio-ID’s gelden, en of FactSet, interne services of een andere route de berekeningsbron blijft. Bouw geen endpointcontract op basis van deze namen voordat die controle is afgerond.

**Scopekeuze:** deze fase maakt de klant-/mandaatmethodiek en rapportagecontracten configureerbaar en verbindt met de vastgestelde performanceberekeningsbron. Zelf een volledige performance-engine bouwen blijft buiten scope tenzij dit expliciet als architectuurbesluit wordt genomen.

## Cross-cutting kwaliteit en security

- PostgreSQL als beoogde productiebron; migratie-/rollbackplan en temporal-queryscenario’s.
- Encryptie in transit/rust, secrets management, least privilege, SSO, RBAC/ABAC en audit.
- Privacy-by-design: alleen benodigde contactgegevens, access logging, retentie per gegevenscategorie en verwijdering/anonimisering alleen waar juridisch toegestaan met behoud van vereiste audit/integriteit.
- Backup/restore en hersteldoelen worden vóór productie vastgesteld en herstel daadwerkelijk gevalideerd.
- OpenAPI contracten, API contracttests, integratietests, property-based tests voor financiële rekenregels, golden-master tests voor simulaties en security tests voor autorisatie/functiescheiding.
- Observability: logs, metrics en traces; geen klantgevoelige waarden in logs; alerts voor exportfouten, verlopen rapportages en workflowdeadlines.
- Synthetische testgegevens uitsluitend. Geen secrets, echte contracten, klantidentifiers of productie-exporten in git.

## Rollen en goedkeuringsmodel

Minimaal: initiator, klant-/mandaat-eigenaar, operations reviewer, bevoegde approver, implementer, Compliance, Risk, Legal en read-only auditor. Bevoegdheden worden per klant-/wijzigingscategorie beheerd door organisatiebeleid. Initiator kan niet zelf finaal goedkeuren. Compliance/Risk/Legal zijn conditioneel vereist op basis van gevalideerde policyregels. Spoedroute vereist reden, scope, expliciete risicogoedkeuring en verplichte beoordeling achteraf. Deadlines, delegatie, commentaar, bewijs en uitzonderingen zijn geaudit.

## Afzonderlijke feature-taken en afhankelijkheden

Onderstaande werkvolgorde splitst de roadmap op in afzonderlijk opleverbare taken. Iedere taak heeft één herkenbaar resultaat en een controleerbaar opleverpunt. De afhankelijkheid is bewust lineair: feature 2 start na feature 1, feature 3 na feature 2, enzovoort. Daarmee blijven discoverybesluiten en de eerder vastgelegde fasevolgorde leidend. Een taak met open juridische, klantbeleids- of leverancierskeuzes levert eerst een besluit-/configuratiepunt op; er wordt geen onbevestigde norm hard afgedwongen.

| Feature | Fase | Afzonderlijke taak / resultaat | Afhankelijk van |
|---|---|---|---|
| 1 | P0 | Domein- en legal discovery: bevestig pilotprofiel, eerste keten, data dictionary, beleidseigenaren en open ADR-besluiten. | Geen |
| 2 | P0 | POL-001 Besluitenregister: versieerbare policyregistratie met eigenaar, scope, bron en handhavingsniveau. | Feature 1 |
| 3 | P0 | POL-002 Broncontrole: append-only bronreview en afzonderlijk gevalideerd policybesluit. | Feature 2 |
| 4 | P0 | POL-003 Klantvarianten: registreer contractuele klant-/fondsvereisten en handmatige reconciliatiestatus. | Feature 3 |
| 5 | P0 | POL-004 DORA-classificatie: leg menselijke beoordelingen voor de drie onderscheiden perimeters vast. | Feature 4 |
| 6 | P1 | CFG-001 Entiteiten en relaties: versieer klant-, fonds-, partij- en dienstrelaties. | Feature 5 |
| 7 | P1 | CFG-002 Bitemporele revisies: reconstrueer configuratie op valid time en transaction time. | Feature 6 |
| 8 | P1 | CFG-003 Getypeerde parameterdefinities: versieer schema’s en valideer configuratie tegen de gekozen schemaversie. | Feature 7 |
| 9 | P1 | SEC-001 Echte identiteit: kies provider/tenant en implementeer gevalideerde OIDC-identiteit volgens ADR-0005. | Feature 8 |
| 10 | P1 | SEC-002 Autorisatie en functiescheiding: voer goedgekeurde rolmatrix en initiator-goedkeurder-scheiding in. | Feature 9 |
| 11 | P1 | AUD-001 Append-only audit: leg actor, reden, bewijs, versies, besluit, simulatie en publicatiestatus vast. | Feature 10 |
| 12 | P1 | DOC-001 Bewijsreferenties: beheer versiegebonden documentmetadata, vertrouwelijkheid en retentieklasse. | Feature 11 |
| 13 | P2 | OUT-001 Activiteitregister: leg werkzaamheden, scope, dienst, eigenaar en contractperiode vast. | Feature 12 |
| 14 | P2 | OUT-002 Ketenregister: volg directe/indirecte partijen en identificeer geraakte mandaten bij wijzigingen. | Feature 13 |
| 15 | P2 | OUT-003 Contractuele minimumvelden: registreer contractrechten, monitoring, audit, toegang, exit en kosten. | Feature 14 |
| 16 | P2 | OUT-004 Selectie- en periodieke beoordeling: configureer criteria, bewijs en reviewcyclus per klant/fonds. | Feature 15 |
| 17 | P2 | OUT-005 Melding en wijzigingssignalering: registreer meldstatus en maak menselijke reviewtaken aan. | Feature 16 |
| 18 | P2 | OUT-006 DORA/ICT-loskoppeling: beheer de afzonderlijke ICT-relatie, dienst, beoordeling en bewijsvelden. | Feature 17 |
| 19 | P2 | OUT-007 Governance en countervailing power: leg beleid, monitoring, escalatie, capaciteit en review vast. | Feature 18 |
| 20 | P3 | ESG-001 Beleidsprofiel: versieer klant-/fonds-/mandaatbeleid, doelen, scope en bronbewijs. | Feature 19 |
| 21 | P3 | ESG-002 Managerselectie en behoud: configureer klantgebonden criteria, uitzonderingen en reviewmomenten. | Feature 20 |
| 22 | P3 | ESG-003 Contractuele flow-down: koppel overeengekomen verplichtingen aan managerketen en bewijs. | Feature 21 |
| 23 | P3 | ESG-004 Due-diligencedossier: registreer bevindingen, menselijk oordeel, actiehouder en deadline. | Feature 22 |
| 24 | P3 | ESG-005 Engagement en incidenten: beheer incidentbron, opvolging, remedie en besluitvorming. | Feature 23 |
| 25 | P3 | ESG-006 Periodieke beoordeling: plan en registreer managerreviews en opvolgacties. | Feature 24 |
| 26 | P4 | RPT-001 Rapportagecatalogus: definieer rapportage-items, perimeter, frequentie, deadline en ontvangers. | Feature 25 |
| 27 | P4 | RPT-002 Data-aanleverafspraak: koppel velden aan leverancier, kanaal, periode, validatie en bewijs. | Feature 26 |
| 28 | P4 | RPT-003 SFDR/PAI-profielen: configureer uitsluitend gevalideerde toepasselijke indicatoren en verantwoordelijkheden. | Feature 27 |
| 29 | P4 | RPT-004 Comply-or-explain: versieer status, uitleg, impact, goedkeuring en follow-up. | Feature 28 |
| 30 | P4 | RPT-005 Rapportage-uitvoering: volg kalender, volledigheid, fouten, vertraging, herstel en goedkeuring. | Feature 29 |
| 31 | P4 | RPT-006 Transparantie-output: publiceer toegestane managergegevens met vertrouwelijkheidscontrole. | Feature 30 |
| 32 | P5 | WTP-001 Transitieprofiel: leg fondsregeling, fase, planning, scope en eigenaar vast. | Feature 31 |
| 33 | P5 | WTP-002 RACI en afhankelijkheden: registreer partijen, taken, overdrachten en escalaties. | Feature 32 |
| 34 | P5 | WTP-003 Transitiegegevens: beheer data-items, bron/eigenaar, validatie, reconciliatie en continuïteit. | Feature 33 |
| 35 | P5 | WTP-004 Mijlpalen en gereedheidscriteria: volg deliverables, planning, risico’s en go/no-go-bewijs. | Feature 34 |
| 36 | P5 | WTP-005 Risico’s en wijzigingsbeheer: registreer transitiebeheersing en impact op mandaat/reporting. | Feature 35 |
| 37 | P6 | FEE-001 Fee-componenten: configureer overeengekomen fee-typen, staffels, valuta en frequenties. | Feature 36 |
| 38 | P6 | FEE-002 Rekenregels: implementeer versieerbare gedeelde domeinberekeningen voor fee-randgevallen. | Feature 37 |
| 39 | P6 | FEE-003 Kostenoverzicht: herleid kosten naar bron, ontvanger, periode en perimeter. | Feature 38 |
| 40 | P6 | FEE-004 Managerlijst/look-through: registreer managerdekking en disclosure-permissie. | Feature 39 |
| 41 | P6 | FEE-005 Simulatie: vergelijk baseline en scenario met gedeelde rekenlogica en zichtbare onzekerheid. | Feature 40 |
| 42 | P7 | TWIN-001 Change-as-code: leg diff, basisversie, reden, bewijs en schema-/policyversies vast. | Feature 41 |
| 43 | P7 | TWIN-002 Isolatie en reproduceerbaarheid: maak geïsoleerde scenario-snapshots zonder productiewrites. | Feature 42 |
| 44 | P7 | TWIN-003 Impactanalyse: vergelijk gevolgen voor fees, keten, ESG, Wtp, rapportage en signalen. | Feature 43 |
| 45 | P7 | EXP-001 Partnerprofielen: versieer mapping, validatie, privacyfilter en contracttests per partner. | Feature 44 |
| 46 | P7 | EXP-002 Publicatiestatus: publiceer goedgekeurde effectieve configuratie en registreer ontvangststatus. | Feature 45 |
| 47 | P7 | INT-001 Integraties: bevestig per bron eigenaar, richting, frequentie, contract en reconciliatie en bouw de eerste koppeling. | Feature 46 |
| 48 | P8 | PERF-001 Methodiekprofiel: configureer de per mandaat goedgekeurde rendementsconventies. | Feature 47 |
| 49 | P8 | PERF-002 Pensioenspecifieke indeling: modelleer return- en matching/LDI-portefeuille en afgesproken indicatoren. | Feature 48 |
| 50 | P8 | BENCH-001 Benchmarkdefinitie: versieer index- en samengestelde benchmarkkenmerken. | Feature 49 |
| 51 | P8 | BENCH-002 Bitemporele benchmarkwijziging: bewaar geldigheids- en bekendheidsmoment plus historiebeleid. | Feature 50 |
| 52 | P8 | BENCH-003 Beschikbaarheid en timing: leg kalender/cutoff vast en beheer goedgekeurde proxy’s zichtbaar. | Feature 51 |
| 53 | P8 | PORT-001 Identifiers en hiërarchie: beheer interne en bevestigde externe portfolio-identifiers. | Feature 52 |
| 54 | P8 | PORT-002 Invoercontract: definieer herleidbare schemas en timing voor portefeuille-inputs. | Feature 53 |
| 55 | P8 | PORT-003 Datakwaliteit en correcties: valideer, reconcileer en bewaar correcties als nieuwe versies. | Feature 54 |
| 56 | P8 | CALC-001 Berekenings-/attributieprofiel: configureer pas na keuze van engine en klant-/modelconventies. | Feature 55 |
| 57 | P8 | CALC-002 Herleidbare run: archiveer request, response, bronreferenties, versies en status. | Feature 56 |
| 58 | P8 | CALC-003 Orkestratie: voer idempotente runs uit na bevestiging van platform en bronbeschikbaarheid. | Feature 57 |
| 59 | P8 | BI-001 Power BI-model: lever gecontroleerd facts-/dimensiemodel met centrale berekeningen. | Feature 58 |
| 60 | P8 | BI-002 Dashboard en toegang: toon overeengekomen resultaten en bewijs klantisolatie. | Feature 59 |
| 61 | P8 | GOV-001 Indicatief versus officieel: beheer review, goedkeuring, lock en versiegebonden restatement. | Feature 60 |
| 62 | P8 | GOV-002 Methodedocument: exporteer de goedgekeurde methodiek en wijzigingshistorie per mandaat. | Feature 61 |

Elke feature behoudt de inhoudelijke acceptatiecriteria uit de betreffende fase hierboven. De lineaire afhankelijkheid is de uitvoeringsvolgorde; open provider-, juridische, klantbeleids- en platformkeuzes blijven expliciete gates binnen de betreffende taak.

## Roadmap en gates

| Fase | Resultaat | Exit gate |
|---|---|---|
| 0. Domein-/legal discovery | Besluiten, klantprofielen, data dictionary, beleidseigenaren en ADR’s | Geen onbekende juridische interpretatie wordt hard afgedwongen; pilotklant en eerste managerketen geselecteerd. |
| 1. Platformbasis | PostgreSQL, SSO, temporeel configuratiemodel, API, audit, bewijs en autorisatie | Reconstructie, vier-ogen-principe, API-contract en restore-pad aantoonbaar. |
| 2. Outsourcing control | Ketenregister, contractvelden, kritikaliteit, monitoring, meldworkflow en exit | Een synthetisch fonds/mandaat doorloopt onboarding, wijziging, evaluatie en beëindiging met complete keten/audit. |
| 3. ESG manager lifecycle | ESG-beleid, OESO/UNGP, selectie, due diligence, incidenten, engagement en periodieke review | Contractueel criterium leidt tot zichtbare manager/mandaatimpact en opvolgbare actie. |
| 4. Reporting + SFDR/PAI | Schema’s, data-aanlevering, PAI-profiel, comply-or-explain en rapportagekalender | Compleet, ontbrekend en afgeweken rapportage-item zijn traceerbaar naar bron/eigenaar. |
| 5. Wtp keten | RACI, mijlpalen, data voor/tijdens/na, validatie en gereedheidsbewijs | Transitiescenario rapporteert afhankelijkheden, datarisico’s, owners en go/no-go-open punten. |
| 6. Fees/transparantie | Alle afgesproken fee-typen, kosten, managerlijst en geavanceerde simulatie | Rekenresultaten zijn reproduceerbaar en getest voor relevante contractrandgevallen. |
| 7. Partnerpilot/opschaling | Partnerbestand + API, statusreconciliatie en bevestigde integraties | Eén partnercontract/schema is end-to-end geaccepteerd met auditbewijs en incident/herstelpad. |
| 8. Rendements- en BI-keten | Methodiekprofielen, benchmarkversies, inputvalidatie, runarchief, afgesproken performancebron en Power BI-model | Een synthetische maand-/kwartaalrun is reproduceerbaar, gereconcilieerd, as-of traceerbaar, klantgescheiden en als definitief goedgekeurd/vergrendeld. |

**Sizing:** omvang pas ramen na fase 0, technische keuze en inventarisatie van bestaande systemen/data. Elke fase wordt als vertical slice per klant-/mandaatproces geleverd; geen productie-uitrol zonder security-, herstel- en Compliance/Legal-gates.

## Open beslissingen en aannames

- **Aanname:** Azure/Entra ID blijft voorkeursrichting tot platform owner dit bevestigt.
- **Aanname:** SFDR/PAI en Wtp data-eisen zijn klantspecifiek te configureren; geen vaste universele verplichting.
- **Aanname:** OESO/UNGP/IMVB-afspraken zijn contract-/beleidseisen waar de klant ze toepast; hun exacte juridische status en formulering wordt niet door de tool bepaald.
- **Aanname:** DNB-meldworkflow registreert bewijs en herinneringen, maar verstuurt geen melding automatisch.
- **Aanname:** klantconfiguratie blijft SSOT voor afspraken; operationele brondata blijft bij bestaande systemen tot een interfacebesluit is genomen.
- **Open:** eerste pilotfonds, asset class, fiduciair/asset-managerketen en partnerexport-schema.
- **Open:** definitieve rolmatrix, drempels, spoedbevoegdheid, retentie, RTO/RPO, gegevenslocatie, API-authenticatie en externe auditeurs/toezichthoudertoegang.
- **Open:** actuele klantcontracten, PAI metrics, ESG-scoremethodologie, rapportagetaxonomie, Wtp milestones en kosten/look-through-perimeter.
- **Open:** FactSet-component/API/licenties en de performanceberekeningsbron; valideer PA Engine, Analytics API en SPAR tegen de eigen tenant.
- **Open:** performanceconventies per mandaat, officiële kalender en close, benchmarkhistoriebeleid, proxy-indexregels, custodian-reconciliatie en voorlopige/definitieve lock-goedkeuring.
- **Open:** ADLS Gen2 zones/retentie en ADF versus Fabric orchestration; Power BI semantic model, RLS-claims en externe guest/embedded toegang.

## Bronnenregister en interpretatiestatus

De onderstaande bronnen zijn startpunten voor requirement discovery. Ze maken voorbeelden niet automatisch universeel bindend. Laat toepasselijkheid, actuele versies en contractuele implementatie valideren.

- DNB, [Guidance uitbesteding pensioenfondsen](https://www.dnb.nl/media/un1fz452/guidance-uitbesteding-pensioenfondsen.pdf): contractonderdelen, monitoring, dooruitbesteding, audit-/toezichtsinformatie, evaluatie, exit en kosten.
- DNB, [Uitbesteding door pensioenfondsen](https://www.dnb.nl/voor-de-sector/open-boek-toezicht/sectoren/pensioenfondsen/prudentieel-toezicht/uitbesteding-pensioenfondsen/uitbesteding-door-pensioenfondsen/): toepassingsgrens factsheet/DORA; bijgewerkt 17 januari 2025 volgens de pagina.
- DNB, [Q&A melding uitbesteding](https://www.dnb.nl/voor-de-sector/open-boek-toezicht/sectoren/pensioenfondsen/prudentieel-toezicht/uitbesteding-pensioenfondsen/qa-melding-van-werkzaamheden-bij-de-nederlandsche-bank-door-pensioenfondsen-en-premiepensioeninstellingen/): melding, kritieke wijzigingen, fiduciair beheer en 30%-verwachting; laat juridische toepassing toetsen.
- DNB, [Good Practice implementatieplan](https://www.dnb.nl/voor-de-sector/open-boek-toezicht/sectoren/pensioenfondsen/verzamelpagina-transitie-wet-toekomst-pensioenen/implementatieplan/good-practice-inhoudsopgave-implementatieplan-pensioenfonds/) en [Good Practices pensioenbeheer](https://www.dnb.nl/voor-de-sector/open-boek-toezicht/sectoren/pensioenfondsen/verzamelpagina-transitie-wet-toekomst-pensioenen/implementatieplan/good-practices-nadere-invulling-pensioenbeheer-in-het-implementatieplan/): indicatieve Wtp-transitie-, data-, keten- en risicopraktijken.
- EU, [SFDR Verordening (EU) 2019/2088](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R2088): regelgeving en rolafhankelijke disclosure; toepasselijkheid te valideren.
- ABP, [Implementatie OESO-richtlijnen voor due diligence 2026](https://www.abp.nl/content/dam/abp/documenten/juridisch/imvb-oeso-due-diligence-2026.pdf): voorbeeld van PAI-data, managerclausules, incidenten en periodieke ESG-rapportage.
- BpfBOUW, [OESO-richtlijnen voor due diligence, update 2026](https://www.bpfbouw.nl/content/dam/bpfbouw/documenten/beleggen/imvb-bpfbouw-implementatie-oeso.pdf): voorbeeld van OESO/UNGP, contractuele uitvoering, monitoring en rapportage.
- Pensioenfederatie, [Good Practice IMVB-convenant Pensioenfondsen](https://www.pensioenfederatie.nl/stream/good-practice-imvb-convenant-pensioenfondsen.pdf): contractuele voorbeeldpraktijk; convenant eindigde 2022, fondsafspraken kunnen blijven bestaan.
- PFZW, [Beleggingsovertuigingen](https://www.pfzw.nl/content/dam/pfzw/web/over-ons/zo-beleggen-we/Beleggingsovertuigingen-PFZW-0524.pdf): klantvoorbeeld van rendement/risico/duurzaamheid.
- ABP, [Overzicht externe vermogensbeheerders 2024](https://www.abp.nl/content/dam/abp/documenten/beleggen/overzicht-externe-vermogensbeheerders.pdf): openbaarmaking/coverage als klantpraktijk, geen universele wettelijke 95%-norm.
- Performanceparameterlijst en FactSet-namen: aangeleverd door de gebruiker; FactSet-productnamen, endpoints en licenties zijn niet onafhankelijk geverifieerd en moeten worden bevestigd bij de eigen FactSet-beheerder. Rendementsconventies zijn klant-/mandaatbesluiten, geen standaardaanname.

De door de aanvrager genoemde Ahold Delhaize-, Aegon AM- en ABP performance-fee-publicaties zijn klant-/marktvoorbeelden. Verifieer per implementatie de actuele brontekst, contractversie en geldigheid voordat hier controls of drempels van worden gemaakt.


## Completed from GitHub

_No GitHub issues closed at initial migration._
