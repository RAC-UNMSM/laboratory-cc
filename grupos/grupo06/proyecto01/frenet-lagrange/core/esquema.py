"""
core/esquema.py — Convierte el JSON Schema de las herramientas MCP a un esquema "portable"
(sin $ref/$defs ni claves que algunos clientes rechazan). Lo usan las pruebas para verificar
que los esquemas expuestos no tengan referencias.
"""
from __future__ import annotations

import json
from typing import Any

__all__ = ["esquema_portable"]

_CLAVES_OK = {"type", "description", "properties", "required", "items", "enum", "minItems", "maxItems",
              "minimum", "maximum"}


def esquema_portable(esquema: dict[str, Any]) -> dict[str, Any]:
    """Resuelve $ref/$defs, quita lo que algunos proveedores rechazan (additionalProperties,
    examples, title, prefixItems...) y aplana 'anyOf [X, null]' → X. Los valores por defecto se
    pasan a la descripción para no perder información."""
    defs = esquema.get("$defs", {})

    def conv(n: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in n:
            base = conv(defs[n["$ref"].split("/")[-1]])
            return {**base, **({"description": n["description"]} if "description" in n else {})}
        if "anyOf" in n:
            opciones = [o for o in n["anyOf"] if o.get("type") != "null"]
            base = conv(opciones[0]) if opciones else {"type": "string"}
            extra = {k: v for k, v in n.items() if k != "anyOf"}
            return conv({**base, **extra}) if extra else base
        out: dict[str, Any] = {}
        for k, v in n.items():
            if k == "properties":
                out[k] = {p: conv(s) for p, s in v.items()}
            elif k == "items" and isinstance(v, dict):
                out[k] = conv(v)
            elif k == "prefixItems":                       # tuplas (p. ej. rango [min, max])
                out["items"] = conv(v[0])
                out["minItems"] = out["maxItems"] = len(v)
            elif k == "additionalProperties" and isinstance(v, dict):   # dict[str, float] → objeto libre
                out.setdefault("description", "")
                out["description"] += f" (objeto: nombre → {v.get('type', 'valor')})"
            elif k in _CLAVES_OK:
                out[k] = v
        if "default" in n and n["default"] is not None:
            out["description"] = (out.get("description", "") + f" Por defecto: {json.dumps(n['default'])}.").strip()
        if out.get("type") == "object" and "properties" not in out:
            out["properties"] = {}
        return out

    return conv({k: v for k, v in esquema.items() if k != "$defs"})
