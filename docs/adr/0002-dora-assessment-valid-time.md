# ADR-0002: geldigheidsperiode voor DORA-assessments

- Status: prototypeconventie; formele criteria te valideren door Compliance/Legal en ICT-risk
- Datum: 2026-11-03

## Context

DORA-assessments zijn append-only versies. `created_at` legt vast wanneer een beoordeling is geregistreerd. `review_date` is de uiterste herbeoordelingsdatum en zegt niet wanneer de beoordeelde scope geldig is. Een automatische juridische of klanttoepasselijkheidsconclusie is niet beschikbaar.

## Besluit

De reviewer legt `effective_from` en optioneel `effective_to` expliciet vast. De periode is halfopen: startdatum inclusief, einddatum exclusief. Nieuwe versies bewaren hun eigen beoordeling en geldigheidsperiode. `known_at` selecteert de laatst geregistreerde versie die op dat moment bekend was; `valid_at` toetst de opgegeven periode. Een beoordeling zonder expliciete periode wordt niet als geldig gepresenteerd.

Bestaande records zonder geldigheidsdata blijven ongewijzigd en verschijnen als `unset_legacy`, met geldigheid te valideren. Geen historische datum wordt afgeleid uit `created_at` of `review_date`.

## Consequenties en open validatie

De prototype maakt tijdreisqueries mogelijk, maar stelt geen wettelijke DORA-scope, kritieke/belangrijke functie of klant-/fondsverplichting vast. Voor gebruik als blokkade of productiebeleid moeten eigenaar, bron, scope, uitzonderingsproces en acceptatiecriteria door Compliance/Legal en ICT-risk worden gevalideerd. De toepasselijkheid van DORA en niet-ICT vermogensbeheeruitbesteding blijft afzonderlijk vast te stellen.
