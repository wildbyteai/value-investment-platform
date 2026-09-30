"""Conservative checker for the Schema keywords used by these design fixtures.

Not a complete draft-2020-12 implementation. Unknown assertion keywords fail,
and external refs are forbidden. Product implementation must use a standard
validator plus business semantic validation.
"""
import re
import uuid
from datetime import datetime


class MaterialError(ValueError):
    pass


def validate(value, schema, root=None):
    root = root or schema
    allowed = {"$schema", "$defs", "$ref", "title", "description", "type", "enum",
               "const", "properties", "required", "additionalProperties", "items",
               "minLength", "maxLength", "minItems", "maxItems", "minProperties",
               "minimum", "maximum", "pattern", "format", "uniqueItems", "oneOf", "anyOf",
               "allOf", "not", "if", "then", "else"}
    if set(schema) - allowed:
        raise MaterialError(f"Unsupported keywords: {set(schema) - allowed}")
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise MaterialError("External refs are not supported")
        target = root
        for part in ref[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        validate(value, target, root)
    if "const" in schema and (value != schema["const"] or
                               isinstance(value, bool) != isinstance(schema["const"], bool)):
        raise MaterialError("const mismatch")
    if "enum" in schema and value not in schema["enum"]:
        raise MaterialError("enum mismatch")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        predicates = {"object": lambda: isinstance(value, dict),
                      "array": lambda: isinstance(value, list),
                      "string": lambda: isinstance(value, str),
                      "boolean": lambda: isinstance(value, bool),
                      "null": lambda: value is None,
                      "integer": lambda: isinstance(value, int) and not isinstance(value, bool),
                      "number": lambda: isinstance(value, (int, float)) and not isinstance(value, bool)}
        if not any(predicates[t]() for t in types):
            raise MaterialError("type mismatch")
    for keyword in ["oneOf", "anyOf", "allOf"]:
        if keyword in schema:
            matches = 0
            for option in schema[keyword]:
                try:
                    validate(value, option, root)
                    matches += 1
                except MaterialError:
                    pass
            wanted = matches == 1 if keyword == "oneOf" else (matches >= 1 if keyword == "anyOf" else matches == len(schema[keyword]))
            if not wanted:
                raise MaterialError(f"{keyword} mismatch")
    if "not" in schema:
        try:
            validate(value, schema["not"], root)
        except MaterialError:
            pass
        else:
            raise MaterialError("not mismatch")
    if "if" in schema:
        try:
            validate(value, schema["if"], root)
            branch = "then"
        except MaterialError:
            branch = "else"
        if branch in schema:
            validate(value, schema[branch], root)
    if isinstance(value, dict):
        if not set(schema.get("required", [])) <= value.keys():
            raise MaterialError("missing required property")
        if len(value) < schema.get("minProperties", 0):
            raise MaterialError("minProperties")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                validate(item, props[key], root)
            elif schema.get("additionalProperties") is False:
                raise MaterialError("extra property")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(item, schema["additionalProperties"], root)
    if isinstance(value, list):
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", float("inf")):
            raise MaterialError("array length")
        if schema.get("uniqueItems"):
            if any(item in value[:i] for i, item in enumerate(value)):
                raise MaterialError("duplicate array item")
        for item in value:
            if "items" in schema:
                validate(item, schema["items"], root)
    if isinstance(value, str):
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", float("inf")):
            raise MaterialError("string length")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise MaterialError("pattern mismatch")
        if schema.get("format") == "uuid":
            try:
                if str(uuid.UUID(value)) != value.lower():
                    raise ValueError("not canonical")
            except ValueError as exc:
                raise MaterialError("uuid format") from exc
        elif schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if "T" not in value or parsed.tzinfo is None:
                    raise ValueError("offset required")
            except ValueError as exc:
                raise MaterialError("date-time format") from exc
        elif "format" in schema:
            raise MaterialError("unsupported format")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not schema.get("minimum", -float("inf")) <= value <= schema.get("maximum", float("inf")):
            raise MaterialError("numeric bounds")
