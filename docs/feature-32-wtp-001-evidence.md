# Feature 32 — WTP-001 evidence

**Requirement (verbatim):** Transitieprofiel: — fondsregeling/transitiefase, planning, scope, relevante besluit-/go-live-/invaardata en eigenaar.

**Implementatie:** register `wtp_transition_profiles` in `app/store.py` (append-only, versieer per `(id,version)`), met:
- verplicht: `customer_id`, `fund_ref`, `fund_regulation` (fondsregeling), `transition_phase` (enum), `planning`, `scope`, `owner`, `source_ref`, `rationale`;
- relevant besluit-/go-live-/invaardata als optionele velden `decision_date`, `golive_date`, `migration_date` (vast te leggen zodra besloten; whitespace/leeg wordt NULL);
- enum `WTP_TRANSITION_PHASES=("preparation","decision","migration","golive","aftercare","closed")`;
- append-only-triggers (`no_update`/`no_delete`), versieer met audit-registratie (`created`/`versioned`);
- filter-query `wtp_transition_profiles(customer_id, fund_ref, transition_phase, owner)`.
- `app/server.py` en UI zijn niet aangeraakt (register is store-only, conform Features 27–31); `server.py` en andere gebruikersbestanden ongemoeid gelaten.

**TDD-cyclus (synthetische gegevens):**
- RED: `python3.13 -m pytest tests/test_wtp_transition_profiles.py -q` → 12 failed (alle: `save_wtp_transition_profile`/`wtp_transition_profiles` ontbreken — feature ontbreekt, geen typefout).
- GREEN: `python3.13 -m pytest tests/test_wtp_transition_profiles.py -q` → 12 passed in 0.88s.
- Covers: basisvelden, verplichte velden, lege-string-afwijzing, onbekende klant, fase-enum, optionele/whitespace-datums, append-only (UPDATE/DELETE afgebroken), versieer met behoud eerdere fase, aparte profielen per fonds, audit-registratie, query-filters.

**Volledige suite:**

Command: `python3.13 -m pytest -q`
Result: 253 passed in 16.37s (exit 0)
git diff --check: clean
Worktree: wt/t_2e15273a (basis: main 4ad1a96)
Commit: see git log

**Open menselijke gates (vastgelegd, niet geïnventariseerd):** policy-owner-aanstelling voor WTP-TRANSITION-DATA / CLIENT-PAI-DATA / ICT-DORA-SCOPE staat nog op `pending` in `policy_controls` (seedstatus "te valideren"); fondsspecifieke datalijst, rekeningverantwoordelijkheid en wettelijke interpretatie (PW/BuPW) te valideren door klant, pensioenexpert en Compliance/Legal. Geen data-eisen of berekeningen ingebakken — applicatie blijft geen pensioenadministratie- of invaren-rekenplatform.
