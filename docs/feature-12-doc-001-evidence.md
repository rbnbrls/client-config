# Feature 12 — DOC-001 Bewijsreferenties — Evidence

## Requirement (verbatim, docs/PROJECT-PLAN.md:69)
> **DOC-001 Bewijs:** versiegebonden documentreferenties met documenttype, datum, eigenaar, vertrouwelijkheid en retentieklasse; geen contractbestand of klantgegeven in git.

## Implementatie
- `app/store.py` — nieuwe append-only tabel `document_references` met `CREATE TABLE IF NOT EXISTS` en `RAISE(ABORT)`-triggers voor UPDATE en DELETE (add-only migratie; bestaande tabellen niet gewijzigd).
- Identiteit van een referentie is de `(subject_type, subject_id, document_type)`-binding; elke registratie/herziening append een nieuwe versie (`PRIMARY KEY(id,version)`), vastgebonden op `subject_version` (positief geheel getal, getypeerd gecontroleerd).
- Verplichte velden: documenttype, documentdatum (ISO), eigenaar, vertrouwelijkheid, retentieklasse, storage_ref, rationale. Enum-validatie voor documenttype, vertrouwelijkheid (`open/intern/vertrouwelijk/geheim`) en retentieklasse (`default_7y/default_10y/permanent/custom`).
- **Geen contractbestand of klantgegeven in git:** inline `content`/`file_path`/`blob` wordt geweigerd; `storage_ref` moet een externe opslagreferentie zijn (`dms://`, `s3://`, `https://`, `azblob://`, `gs://`) — lokale bestandspaden worden geweigerd. Alleen metadata en referenties worden bewaard.
- Audit: elke create/versioning schrijft een auditregel (`entity_type=document_reference`) met acteur, reden en alle velden — zelf niet wijzigbaar via de bestaande append-only audit-triggers.
- Geen nieuwe runtime-dependency; SQLite-prototype blijft conform de faseroute.

## Test-first (RED → GREEN)
1. `tests/test_document_references.py` geschreven (10 tests): create, append-only versiebeheer per subject-binding, UPDATE/DELETE-blokkade, enum- en verplicht-veld-validatie, inline-inhoud-/lokale-pad-weigering, auditregistratie, subject_version-binding, getypeerde `subject_version`.
2. RED: `python3.13 -m pytest tests/test_document_references.py -q` → **9 failed** (API nog niet geïmplementeerd).
3. GREEN: implementatie in `app/store.py`.

## Volledige suite
```
$ python3.13 -m pytest -q
......................................................                   [100%]
54 passed in 1.79s
```
Exit 0; 45 bestaande + 9 nieuwe document_reference-tests (10 in bestand, waaronder negatieve paden) — niets bestaands gebroken.

## Migratieprobe (legacy SQLite)
Legacy DB met bestaande `customers`-rij: kolommen en rij behouden; `document_references` add-only aangemaakt; UPDATE en DELETE op document_reference geweigerd ("document references are append-only"); audit-triggers nog intact ("audit records are append-only"). (Eerste probe-output "UPDATE allowed" was een probe-artefact: `WHERE 1=0` matchte geen rij, dus geen trigger; herprobeerd met matchende rij.)

## Synthetische data
Alle test- en seedgegevens synthetisch (bijv. `DEMO-CLIENT`, `dms://synthetic/...`); geen klantgegevens of contractinhoud in git.

## Open human gates (niet geïmplementeerd, zoals in de taak vermeld)
- Beleideigenaar-benoeming CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE (Compliance/Legal + Client Service + ICT-risk).
- Afdwingniveau per controle met uitzonderingsproces.
- Classificatiebeleid primaire bron.
- Gevalideerde rolmatrix en functiescheiding (SEC-002).
- FactSet tenant/service-bevestiging vóór performance-endpointcontracten.
- Identity provider/tenant-bevestiging (ADR-0005).

## Wijzigingen
- `app/store.py` (+55: tabel, triggers, registerfuncties)
- `tests/test_document_references.py` (nieuw, 10 tests)
- `docs/feature-12-doc-001-evidence.md` (dit bestand)
- Geen user-touched bestanden (`AGENTS.md`, `app/server.py`, `app/static/index.html`, `docs/*-UI-DESIGN-NOTES.md`, `docs/adr/*`) aangeraakt.
