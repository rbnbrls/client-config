# ADR-0003: tijdreisconventie voor versieerbare controls

- Status: prototypeconventie; formele beleidsinhoud blijft ter validatie door de control-eigenaar en Compliance/Legal
- Datum: 2026-11-03

## Context

Controls hebben al append-only versies, `effective_date` en `created_at`. De bestaande lijst toonde alleen de nieuwste versie en bronreview-/besluitstatus zonder tijdsfilter. `review_date` is een reviewdeadline en definieert geen geldigheidseinde.

## Besluit

`effective_date` is de inclusieve valid-time start; er wordt geen valid-time einddatum afgeleid. Voor een `valid_at`/`known_at` paar zijn alleen versies bekend op `known_at` kandidaten. Per controlcode wordt de kandidaat met de meest recente `effective_date` gekozen die op `valid_at` is ingegaan; bij gelijke ingangsdatum wint het hogere versienummer. Bronreviews en policybesluiten worden eveneens begrensd op hun registratietijd (`checked_at` en `decided_at`).

Deze query reconstrueert registerinhoud zoals vastgelegd en is geen juridische interpretatie, beleidsgoedkeuring of automatische blokkade. Harde controles blijven onderworpen aan de bestaande gevalideerde eigenaar-, bron-, scope-, uitzonderings- en acceptatiecriteria.
