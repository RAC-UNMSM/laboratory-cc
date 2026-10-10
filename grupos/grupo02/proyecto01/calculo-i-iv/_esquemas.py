import asyncio
import json

import server


async def main():
    ts = await server.mcp.list_tools()
    for t in sorted(ts, key=lambda x: x.name):
        props = {}
        schema = getattr(t, "inputSchema", None) or {}
        required = set(schema.get("required", []))
        for k, v in (schema.get("properties") or {}).items():
            marca = "*" if k in required else ""
            props[k] = "{}{}: {}".format(k, marca, v.get("type", "?"))
        print("\n=== {} ===".format(t.name))
        print("   required: {}".format(sorted(required) or "(ninguno)"))
        for k in sorted(props):
            print("   - " + props[k])
        print("   desc: " + (t.description or "")[:110].replace("\n", " "))


if __name__ == "__main__":
    asyncio.run(main())
