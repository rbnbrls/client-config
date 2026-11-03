"""Small, dependency-free JSON Schema subset for versioned client configuration."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
SUPPORTED = {"$schema", "$id", "title", "description", "type", "required", "properties", "items", "enum", "minimum", "maximum", "minLength", "minItems", "pattern", "dependentRequired", "x-version", "x-effective-from", "x-owner", "x-unit", "x-evidence-required", "x-dependencies"}


def schema_versions():
    found = []
    for path in SCHEMA_DIR.glob("configuration-v*.json"):
        if not re.fullmatch(r"configuration-v\d+\.json", path.name): continue
        schema = json.loads(path.read_text())
        validate_schema(schema)
        number = int(schema["x-version"])
        if path.name != f"configuration-v{number}.json": raise ValueError(f"Schema-ID en bestandsversie komen niet overeen: {path.name}")
        found.append((number, schema))
    found.sort(key=lambda pair: pair[0])
    if len({number for number, _ in found}) != len(found): raise ValueError("Dubbele configuratieschemaversie")
    return found


def latest_schema(valid_at=None):
    from datetime import date
    valid_at = valid_at or date.today().isoformat()
    versions = [pair for pair in schema_versions() if pair[1]["x-effective-from"] <= valid_at]
    if not versions:
        raise ValueError("Geen configuratieschema beschikbaar op deze geldigheidsdatum")
    return versions[-1][1]


def get_schema(version=None):
    versions = schema_versions()
    if not versions:
        raise ValueError("Geen configuratieschema beschikbaar")
    if version is None:
        return versions[-1][1]
    for number, schema in versions:
        if str(number) == str(version):
            return schema
    raise ValueError(f"Configuratieschema v{version} niet gevonden")


def parameter_definitions(schema=None):
    schema = schema or latest_schema()
    result = []

    def walk(node, prefix=""):
        required = set(node.get("required", []))
        for name, definition in node.get("properties", {}).items():
            path = f"{prefix}.{name}" if prefix else name
            if "type" in definition:
                result.append({"path": path, "type": definition["type"], "required": name in required, "unit": definition.get("x-unit"), "minimum": definition.get("minimum"), "maximum": definition.get("maximum"), "owner": definition.get("x-owner", schema.get("x-owner")), "evidence_required": definition.get("x-evidence-required", False), "dependencies": definition.get("x-dependencies", [])})
            walk(definition, path)
            if isinstance(definition.get("items"), dict): walk(definition["items"], path + "[]")
    walk(schema)
    return result


def validate(configuration, schema=None):
    schema = schema or latest_schema()
    errors = []

    def add(path, code, message):
        errors.append({"path": path or "$", "code": code, "message": message})

    def check(value, definition, path):
        expected = definition.get("type")
        type_ok = True
        if expected == "object": type_ok = isinstance(value, dict)
        elif expected == "array": type_ok = isinstance(value, list)
        elif expected == "string": type_ok = isinstance(value, str)
        elif expected == "integer": type_ok = isinstance(value, int) and not isinstance(value, bool)
        elif expected == "number": type_ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected == "boolean": type_ok = isinstance(value, bool)
        if expected and not type_ok:
            add(path, "type", f"verwacht {expected}")
            return
        if "enum" in definition and value not in definition["enum"]:
            add(path, "enum", "waarde is niet toegestaan")
        if expected in {"number", "integer"}:
            if isinstance(value, float) and not math.isfinite(value):
                add(path, "number", "waarde moet eindig zijn")
                return
            for bound in ("minimum", "maximum"):
                if bound in definition and ((bound == "minimum" and value < definition[bound]) or (bound == "maximum" and value > definition[bound])):
                    add(path, bound, f"waarde moet {bound} {definition[bound]} zijn")
        if expected == "string":
            if len(value) < definition.get("minLength", 0): add(path, "minLength", "waarde is te kort")
            if "pattern" in definition and not re.fullmatch(definition["pattern"], value): add(path, "pattern", "waarde heeft een ongeldig formaat")
        if expected == "object":
            for key in definition.get("required", []):
                if key not in value: add(f"{path}.{key}".strip("."), "required", "verplicht veld ontbreekt")
            for key, deps in definition.get("dependentRequired", {}).items():
                if key in value:
                    for dependency in deps:
                        if dependency not in value: add(f"{path}.{dependency}".strip("."), "dependency", f"vereist door {path}.{key}".strip("."))
            for key, child in definition.get("properties", {}).items():
                if key in value: check(value[key], child, f"{path}.{key}".strip("."))
        if expected == "array":
            if len(value) < definition.get("minItems", 0): add(path, "minItems", f"minimaal {definition['minItems']} item(s) vereist")
            child = definition.get("items")
            if child:
                for index, item in enumerate(value): check(item, child, f"{path}[{index}]")

    check(configuration, schema, "")
    if isinstance(configuration, dict):
        evidence_parameters=[parameter["path"] for parameter in parameter_definitions(schema) if parameter["evidence_required"]]
        evidence_definition=schema.get("properties",{}).get("evidence",{})
        if evidence_parameters and not configuration.get("evidence") and "evidence" not in schema.get("required",[]) and not evidence_definition.get("minItems"):
            add("evidence", "evidence_required", "bewijs vereist voor: "+", ".join(evidence_parameters))
        for parameter in parameter_definitions(schema):
            value = configuration
            present = True
            for part in parameter["path"].split("."):
                if not isinstance(value, dict) or part not in value:
                    present = False; break
                value = value[part]
            if present:
                for dependency in parameter["dependencies"]:
                    required = configuration
                    for part in dependency.split("."):
                        required = required.get(part) if isinstance(required, dict) else None
                    if required is None: add(dependency, "dependency", f"vereist door {parameter['path']}")
    return errors


def validate_schema(schema):
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError("Schema moet een objectdefinitie zijn")
    if schema.get("x-version", 0) < 1 or not schema.get("x-owner") or not schema.get("x-effective-from"):
        raise ValueError("Schema vereist x-version, x-effective-from en een schema-eigenaar")
    from datetime import date
    try: date.fromisoformat(schema["x-effective-from"])
    except ValueError: raise ValueError("x-effective-from moet ISO-formaat YYYY-MM-DD zijn")
    def inspect(node):
        unknown = set(node) - SUPPORTED
        if unknown: raise ValueError(f"Niet-ondersteunde schema-keywords: {', '.join(sorted(unknown))}")
        if node.get("type") not in {None, "object", "array", "string", "integer", "number", "boolean"}: raise ValueError("Niet-ondersteund schematype")
        if "minimum" in node and "maximum" in node and node["minimum"] > node["maximum"]: raise ValueError("Schema minimum ligt boven maximum")
        if "pattern" in node: re.compile(node["pattern"])
        for child in node.get("properties", {}).values(): inspect(child)
        if isinstance(node.get("items"), dict): inspect(node["items"])
    inspect(schema)
