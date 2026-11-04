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
     als er niets geldt (vóór ingangsdatum, ná einde geldigheid of bij `known_at` vóór registratie).
     **Rework (review t_f5af23e4):** zonder fondsdekkend standaardprofiel wordt óók geweigerd
     (`ValueError`) — zowel voor een fonds-vraag zonder subject-args als voor een vraag om een niet
     geregistreerd subject; een ander mandaatprofiel wordt nooit als `resolved_from="fund_default"`
     (mét bronbewijs) gepresenteerd. De specific→fund_default-ladder zelf is ongewijzigd;
   - `save_esg_policy_exception(data)` / `esg_policy_exceptions(valid_at=None, known_at=None, customer_id=None)` —
     uitzonderingsregister; na de einddatum wordt `validity_status="expired"` afgeleid (append-only,
     geen hard delete); zonder `valid_at` expliciet `unknown_without_valid_at`. Identiteitssemantiek:
     zonder expliciete `actor` wordt de audit van een uitzondering toegeschreven aan
     `data["approver"]` (`actor=data.get("actor", data["approver"])`) — de goedkeurder is per default
     de geregistreerde actor; een afwijkende actor (bijv. een systeemgebruiker of ondersteunende medewerker)
     moet expliciet als `actor` meegegeven worden. Update-blokkering van uitzonderingen is bewaakt met
     een `IntegrityError`-assertie (no-update trigger `esg_policy_exceptions_no_update`);
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

`tests/test_esg_policy_profiles.py` — 21 tests, waaronder de negatieve paden uit het plan:

- versieer zonder overwrite: tweede save → versie 2, eerdere versie blijft staan;
- append-only: `UPDATE` en `DELETE` blokkeren via triggers (`sqlite3.IntegrityError`) — voor
  `esg_policy_profiles` én `esg_policy_exceptions` (de UPDATE-blokkeerassertie op uitzonderingen is
  toegevoegd in de rework; de no-update trigger bestond al en wordt daarmee bewaakt);
- verplichte-veld-, enum- (ongeldige `subject_type`/`priority`), klant-niet-gevonden- en
  datumnegatieve paden (niet-ISO ingangsdatum; `effective_to` vóór `effective_from`);
- zichtbaar en bewijsbaar in force bij onboarding/review (mandaat-precedent, geldigheidsvenster,
  transaction-time `known_at` in het verleden vindt niets);
- **rework (review t_f5af23e4):** zonder fondsdekkend standaardprofiel wordt geweigerd — een fonds-vraag
  zonder subject-args én een vraag om een niet-geregistreerd mandaat krijgen `ValueError` in plaats van
  ander mandaatbeleid als `fund_default` met bronbewijs terug te geven
  (`test_in_force_fund_query_rejected_without_fund_default`,
  `test_in_force_unknown_mandate_rejected_without_fund_default`);
- uitzonderingen: elk verplicht veld individueel gecontroleerd (description, rationale, approver,
  end_date), einddatum moet ISO zijn, profiel bestaat, update én delete blokkeren, verlopen op `valid_at`;
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

## Rework (review t_f5af23e4 — CHANGES REQUESTED @ `0b77954`)

Blokkerende bevinding: de `else`-fallback in `esg_policy_profile_in_force` (oud `app/store.py:732`)
etiketteerde `candidates[0]` als `resolved_from="fund_default"` óók wanneer er géén fondsdekkend
standaardprofiel bestaat (config met alleen mandaatprofielen), zodat ander mandaatbeleid mét zijn
bronbewijs als fondsdekkend werd gepresenteerd — voor een niet-geregistreerd mandaat én voor een
fonds-vraag zonder subject-args. Gecorrigeerd naar een expliciete weigering (`ValueError`) in de stijl
van het bestaande no-candidates-pad, met klant/fonds/valid_at (en bij een subject-vraag het gezochte
subject) in de boodschap; de specific→fund_default-ladder zelf is verder ongewijzigd en alle
bestaande tests blijven onveranderd groen.

1) RED (twee nieuwe negatieve tests eerst geschreven, fix nog niet toegepast):

```
$ /opt/homebrew/bin/python3.13 -m pytest tests/test_esg_policy_profiles.py -q
........F...F........                                                    [100%]
FAILED tests/test_esg_policy_profiles.py::ESG001::test_in_force_fund_query_rejected_without_fund_default
FAILED tests/test_esg_policy_profiles.py::ESG001::test_in_force_unknown_mandate_rejected_without_fund_default
2 failed, 19 passed in 1.07s
```

`ValueError not raised` op beide nieuwe tests — de bug gereproduceerd (oud gedrag gaf
`resolved_from="fund_default"` terug met het evidence-blok van het enige bestaande mandaatprofiel).

2) GREEN (zelfde bestand na fix):

```
$ /opt/homebrew/bin/python3.13 -m pytest tests/test_esg_policy_profiles.py -q
.....................                                                    [100%]
21 passed in 1.01s
```

3) Volledige suite na fix (python3.13, niet python3/3.9):

```
$ /opt/homebrew/bin/python3.13 -m pytest -q
........................................................................ [ 46%]
........................................................................ [ 92%]
...........                                                              [100%]
155 passed in 7.36s
```

153 eerder groen (134 basis + 19 Feature 20) + 2 nieuwe negatieve tests; exit 0; geen regressies.
`git diff --check`: schoon (exit 0). Gewijzigde bestanden in de rework: alleen `app/store.py`
(else-tak + docstring) en `tests/test_esg_policy_profiles.py` (+13 regels: 2 tests + 1 assertie);
`2 files changed, 20 insertions(+), 3 deletions(-)` (de 3 verwijderde regels zijn de vervangen
bugregels/docstringregels uit Feature 20 zelf).

De UPDATE-blokkeerassertie op `esg_policy_exceptions` is een bewakingsassertie (characterization)
tegen de reeds bestaande no-update trigger; hij passeerde al tijdens de RED-run, wat bevestigt dat
de RED-falen uitsluitend door de fallback-bug veroorzaakt werden.

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
- **Volgende gate:** onafhankelijke her-review van deze branch op de rework-SHA (review gate
  t_f5af23e4); Feature 21 (volgens plan) pas up nadat die her-review aantoonbaar groen is.
