# ADR-0004: getypeerde configuratieschema's

- Status: prototypebesluit; concrete schema-eigenaren en klantspecifieke normen te bevestigen
- Datum: 2026-11-03

## Besluit

Configuratieschema's zijn JSON-bestanden met unieke oplopende `x-version`, inclusieve `x-effective-from` en expliciete schema-/parameter-eigenaar. De eerste bootstrap registreert de inhoud, transaction-time, actor en reden in `config_schema_versions`; database-triggers blokkeren update en delete. Een bestaande versie met gewijzigde inhoud wordt geweigerd; uitbreidingen krijgen een nieuw versienummer.

Een klantconfiguratieversie en change-set pinnen de toegepaste `schema_version`. Change creation en activation valideren tegen die versie; export valideert opnieuw tegen de vastgelegde versie. De prototypevalidator ondersteunt een expliciet beperkte JSON Schema-subset uit `app/config_schema.py`, waaronder typen, enums, ranges, verplichte velden, afhankelijkheden, patronen en arrays. Geen extra runtime-dependency.

Validatieresultaten bewaren in audit de actor, reden, schemaversie, uitkomst, aantal fouten en SHA-256 van de JSON. De configuratie-inhoud zelf komt niet in deze auditregel.

## Grenzen

Een type-/structuurmatch bewijst geen contractuele juistheid of compliance. Domeineigenaren zijn in de demo rollen die nog formeel moeten worden toegewezen. Klant- en mandaatspecifieke waarden blijven data-/afspraakkeuzes; algemene wettelijke normen worden niet in het schema vastgelegd. Velden die niet in de subset vallen vereisen een nieuw schema-/validatorbesluit voordat ze als gecontroleerd worden gepresenteerd.
