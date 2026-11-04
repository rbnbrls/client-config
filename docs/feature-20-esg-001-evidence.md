# Feature 20 — ESG-001 Beleidsprofiel: evidence

**Branch:** `wt/t_536fcb6c` · **Basis:** main `9241c7c` (na P2-merge Features 13–19, 134 tests groen) · **Datum:** 2026-11-04

## Requirement (PROJECT-PLAN.md, ES-105)

> ESG-001 Beleidsprofiel: per klant/fonds en mandaat het geldende MVB/ESG-beleid, doelen, prioriteit
> (bijv. rendement/risico/duurzaamheid), asset-class scope, versie en bronbewijs.

**Acceptatie (fase P3):** toepasselijke criteria zichtbaar en bewijsbaar bij manager onboarding en
jaarlijkse review; uitzonderingen hebben rationale, goedkeurder en einddatum; een wijziging van
klantbeleid laat zien welke managers/mandaten en rapportageprofielen geraakt worden.

**Validatienotitie (P3):** OESO/UNGP/IMVB-invulling per klant en contract, beoordelingsmethodologie,
ESG-ratingbron en beslisdrempels: **te valideren door klantbeleidseigenaar en Compliance/Legal**.
Het verlopen IMVB-convenant wordt niet als zelfstandige actuele wettelijke verplichting gemodelleerd;
fondsbeleid kan verwijzen naar afspraken daaruit.

## Implementatie

Aangeraakt: alleen `app/store.py` (nieuwe tabellen + domeinfuncties), `tests/test_esg_policy_profiles.py`
(nieuw) en dit document. De opzet volgt Features 16–19: store-layer-module, append-only versietabel,
geen HTTP-routes, gebruikersbestanden onaangetast.

1. Tabel `esg_policy_profiles` — append-only versieer (`PRIMARY KEY(id,version)`, `BEFORE UPDATE/DELETE`
   → `RAISE(ABORT)`-triggers). Velden:
   - geldend beleid: `policy_framework`, `goals`, `priority` (enum `return|risk|sustainability|balanced`),
     `asset_class_scope`;
   - P3-validatienotitie geïnventariseerd als vrije velden **zonder gevulde universele waarden**:
     `oeso_ungp_diligence`, `imvb_diligence`, `assessment_methodology`, `esg_rating_source`,
     `decision_thresholds` — te valideren door klantbeleidseigenaar en Compliance/Legal;
   - versie + bronbewijs: eigen `version` per profiel-id, plus `policy_document_version`,
     `evidence_ref`, `source_ref`;
   - geldigheid en review: `effective_from` (verplicht), `effective_to`, `review_cycle`, `next_review_at`.
2. Tabel `esg_policy_exceptions` — append-only; verplicht `description|rationale|approver|end_date`
   (acceptatie: rationale, goedkeurder, einddatum); `end_date` moet ISO zijn en na eventuele
   `effective_from` liggen; erft `fund_ref`/`subject_type`/`subject_id` van het profiel tenzij expliciet
   gegeven.
3. Domeinfuncties (in `app/store.py`):
   - `save_esg_policy_profile(data)` — verplichte-veld-, enum- (subject_type exact `fund|mandate|party`,
     zelfde vocabulaire als de selectiebeoordelingen) en ISO-datumvalidatie; per-id-versieer met
     `created`/`versioned`-audit;
   - `esg_policy_profiles(valid_at=None, known_at=None, customer_id=None, fund_ref=None)` — laatste
     versie per id (transaction-time filter via `created_at<=known_at`), zoals `governance_policies`;
     met `valid_at` alleen profielen geldend op die datum;
   - `esg_policy_profile_in_force(customer_id, fund_ref, subject_type, subject_id, valid_at, known_at)` —
     toepasselijke criteria bij manager onboarding en jaarlijkse review: mandaatspecifiek profiel wint
     van het fondsdekkende standaardprofiel; retourneert een `evidence`-blok met bronbewijs
     (`source_ref`, `evidence_ref`, `policy_document_version`, reviewmarkeringen); geeft `ValueError`
     als er niets geldt (vóór ingangsdatum, ná einde geldigheid of bij `known_at` vóór registratie);
   - `save_esg_policy_exception(data)` / `esg_policy_exceptions(valid_at=None, known_at=None, customer_id=None)` —
     uitzonderingsregister; na de einddatum wordt `validity_status="expired"` afgeleid (append-only,
     geen hard delete); zonder `valid_at` expliciet `unknown_without_valid_at`;
   - `esg_policy_change_impact(data)` — wijziging van klantbeleid: toont per in-kracht-profiel welke
     profielen afwijken van de voorgestelde waarden (`affected_profiles` met `changed_fields`),
     de betreffende mandaten/managers (`affected_managers_mandates`), de rapportagevereisten
     (`affected_reporting_requirements`, categorie `reporting` uit de klantvereisten) en de
     exportprofielen in gebruik bij de klant (`affected_partner_export_profiles`); auditactie
     `impact_reviewed` vastgelegd.

**Designkeuze — namespaced standaard-id:** default id `esgp-<klant>-<fonds>-<subject_type>[-<subject_id>]`,
zodat dezelfde natuurlijke sleutel (zelfde fonds naam) bij een tweede klant nooit botst op de globale
PK `(id,version)`. De eerste run van `test_query_customer_filter` legde precies die UNIQUE-violatie
bloot; daarna naamgeving aangepast en opnieuw groen.

**IMVB-convenant (validatienotitie P3):** geen seed- of migratierecord modellert het convenant als
zelfstandige actuele wettelijke verplichting; test `test_seed_has_no_standalone_imvb_covenant_obligation`
bewaakt dat het beleidsregister geen convenant-record bevat. De IMVB-invulling leeft per klant/fonds in
het profiel met bronverwijzing naar klantaafspraak/fondsbeleid
(`test_imvb_invulling_per_klant_met_bron`).

## Dekking (tests)

`tests/test_esg_policy_profiles.py` — 19 tests, waaronder de negatieve paden uit het plan:

- versieer zonder overwrite: tweede save → versie 2, eerdere versie blijft staan;
- append-only: `UPDATE` en `DELETE` blokkeren via triggers (`sqlite3.IntegrityError`);
- verplichte-veld-, enum- (ongeldige `subject_type`/`priority`), klant-niet-gevonden- en
  datumnegatieve paden (niet-ISO ingangsdatum; `effective_to` vóór `effective_from`);
- zichtbaar en bewijsbaar in force bij onboarding/review (mandaat-precedent, geldigheidsvenster,
  transaction-time `known_at` in het verleden vindt niets);
- uitzonderingen: elk verplicht veld individueel gecontroleerd (description, rationale, approver,
  end_date), einddatum moet ISO zijn, profiel bestaat, delete blokkeert, verlopen op `valid_at`;
- impactanalyse: alleen afwijkende mandaten/profielen geraakt (FUND-001-mandaat → getroffen,
  gelijkgerichte FUND-002-fondsprofiel → niet getroffen), rapportagevereisten zichtbaar, onbekende
  klant geweigerd.

## Evidence runs (exacte commando's en output)

1) RED (test eerst geschreven, implementatie ontbrak):

```
$ python3.13 -m pytest tests/test_esg_policy_profiles.py -q
19 failed in 0.84s   (AttributeError: esg_*-functies bestonden nog niet)
```

2) GREEN per bestand na implementatie:

```
$ python3.13 -m pytest tests/test_esg_policy_profiles.py -q
...................                                                      [100%]
19 passed in 0.88s
```

3) Volledige suite (alles, niet alleen het nieuwe bestand):

```
$ python3.13 -m pytest -q
........................................................................ [ 47%]
........................................................................ [ 94%]
.........                                                                [100%]
153 passed in 7.03s
```

134 reeds geredigeerde tests uit Features 1–19 + 19 nieuwe ESG-001-tests; exit 0; geen regressies.

## Zelf-audit (voorspelbare AI-faalfactoren)

- Geen secrets/API-keys in de patch; uitsluitend `SYNTHETIC-*` verwijzingen.
- Geen harde deletes; alleen append met no-update/no-delete triggers; valid time (`effective_from/to`)
  en transaction time (`created_at`, `known_at`-filters) behouden.
- Invoervalidatie vóór insert; SQL uitsluitend met bound parameters (geen string-concatenatie van
  gebruikersinvoer); geen LLM-prompt-concatenatie in dit feature.
- Rate limiting en authenticatie: niet onderdeel van dit feature (store-layer, bestaand
  HTTP-oppervlak raakt het niet); identity-gate blijft open staan zoals vermeld.
- `git diff --check`: schoon. Gewijzigde bestanden beperkt tot `app/store.py`,
  `tests/test_esg_policy_profiles.py`, `docs/feature-20-esg-001-evidence.md`.

## Status gates

- **User-touched bestanden onaangetast:** `AGENTS.md`, `app/server.py`, `app/static/index.html`,
  `docs/*-UI-DESIGN-NOTES.md`, `docs/adr/*` — niet gewijzigd in deze branch (geverifieerd via
  `git status`/`git diff --check`).
- **Open human gates (vastgelegd, niet geïnvent):** beleidseigenaar-aanwijzing
  CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE (Compliance/Legal + Client Service +
  ICT-risk); enforcement-niveau per controle met uitzonderingsproces; primaire bronclassificatie;
  gevalideerde rolematrix en actorscheiding (SEC-002); FactSet-tenant/servicebevestiging;
  identity provider/tenant-bevestiging (ADR-0005).
- **Volgende gate:** onafhankelijke review; Feature 21 (volgens plan) pas up nadat deze review
  aantoonbaar groen is.
