# ADR — Bitemporeel benchmarkmodel en wijzigingsregels (BENCH-002)

Status: proposed (ontwerpadvies voor builder)
Datum: 2026-11-05
Eigenaar: Architect
Bron: Feature 50 (BENCH-001) contracten in worktree `t_6792522b`; nog niet geland op `main` → **blokkade**.

## 1. Doel
Vastleggen hoe benchmarkwijzigingen bitemporeel worden opgeslagen: valid time (ingangsdatum) en transaction time (bekendheidsmoment), met versiebeheer en wijzigingsbeleid.

## 2. Tijdsemantiek
- `valid_from` / `effective_date` = **valid time** (ingangsdatum): wanneer de benchmarkdefinitie geldt in de werkelijkheid.
- `valid_to` = einde geldigheidsinterval (exclusief of inclusief af te spreken; default: geldig t/m `valid_to`, volgende start bij volgende `valid_from`).
- `known_at` = **transaction time** (bekendheidsmoment): wanneer de organisatie de wijziging kent/registreert. Default `created_at`/stamp.
- `created_at` = technische registratiestempel (append-only).

## 3. Versies
- `id` = stabiele logische sleutel (`benchmark:<name>:<customer_id>`).
- `version` = monotone oplopend per `id`+`customer_id`.
- Nieuwe wijziging = nieuwe rij; nooit UPDATE/DELETE (triggers).

## 4. Wijzigingsbeleid (history_policy)
- `revise`: historische versies worden herzien (logisch; fysiek append-only, nieuwe versie met zelfde valid interval en latere known_at).
- `link`: doorlinken — nieuwe versie met nieuw valid interval, oude blijft geldig voor eigen interval.
- Default: `link` (veiligst; geen stille herschrijving van historie).
- Enum: {`revise`, `link`}.

## 5. Schema (SQLite, append-only)
Tabel `benchmark_versions` (bestaand uit BENCH-001) + bitemporele kolommen:
- `effective_date TEXT` (valid time start; default = `valid_from`)
- `history_policy TEXT` NOT NULL-ish met default `link`
- `known_at TEXT` (transaction time; default stamp)
- `valid_from TEXT`, `valid_to TEXT` (geldigheidsinterval)
- Triggers: `no_update`, `no_delete` (append-only).

Migratie: add-only ALTER TABLE (geen verwijdering), zoals reeds in worktree t_6792522b.

## 6. Invarianten
1. `customer_id` moet bestaan (unknown customer → ValueError).
2. `return_type` ∈ {total, net, price}.
3. `rebalance_frequency` ∈ {daily, monthly, quarterly, buy-and-hold} of NULL.
4. `history_policy` ∈ {revise, link}.
5. `effective_date` default = `valid_from` indien niet opgegeven.
6. `known_at` default = registratiestempel.
7. Append-only: UPDATE/DELETE blokkeren op DB-niveau.
8. Versie monotoon oplopend per logische sleutel.
9. Geldigheidsinterval: indien beide gezet, `valid_from <= valid_to`.

## 7. Negatieve gevallen
- Onbekende klant → fout.
- Ontbrekende required (`customer_id`, `return_type`, `actor`, `source_ref`) → fout.
- Ongeldige enum-waarden → fout.
- UPDATE/DELETE op tabel → DB-fout.
- Ongeldig interval (`valid_from > valid_to`) → fout (builder te implementeren).

## 8. API-contract (domeinfuncties)
- `save_benchmark(data)` → nieuwe versie; retourneert dict.
- `benchmarks(customer_id=None, return_type=None, index_id=None)` → lijst.
- `benchmark_export(customer_id=None)` → lijst met velden incl. `effective_date`, `history_policy`, `known_at`, `valid_from`, `valid_to`.
- Audit-entry bij elke save (actor, reden, bewijs, versie).

## 9. Blokkades
- Feature 50 (BENCH-001) is nog niet op `main` (alleen in worktree `t_6792522b`). Design gaat uit van dat contract; landing van Feature 50 op main is vereist vóór implementatie van BENCH-002.