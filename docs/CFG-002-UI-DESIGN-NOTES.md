# CFG-002 UI Design Review Notes

## DORA assessment tijdreis

- Behoudt de bestaande Atlas-modal, kaartindeling en form-grid; voegt klant, valid_at en UTC known_at toe boven de lijst.
- Valid-time start/einddatum staan expliciet in het formulier; `review_date` is apart gelabeld als reviewdeadline.
- Legacy-items zonder geldigheidsdata krijgen een zichtbare status “Geldigheid te valideren” en worden niet als geldig gepresenteerd.
- Juridische reikwijdte blijft een menselijke beoordeling en is zichtbaar als open validatie; geen automatische DORA-claim.
- Browseracceptatie: synthetische assessment is opgeslagen; eerder `known_at` verbergt die, latere kennisdatum toont haar. Serverlog: requests 200/201, geen 4xx/5xx.

## Controls & beleid tijdreis

- Behoudt de bestaande controlkaart en form-grid; twee native datum/tijdvelden filteren de registerlijst.
- Snapshottekst benoemt `valid_at` en UTC `known_at`; kaarten tonen afzonderlijk ingangsdatum en reviewdeadline.
- De query toont alleen de controlversie en review-/besluitstatus die op het gekozen registratiemoment bekend waren.
- Geen complianceclaim of automatische geldigheid na reviewdeadline; bestaande menselijke validatieworkflow blijft leidend.
