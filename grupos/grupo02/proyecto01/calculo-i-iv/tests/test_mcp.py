from mcp import Client
from server import mcp


async def test_protocol_in_process():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert {
            "resolver",
            "catalogo",
            "leccion",
            "verificar_respuesta",
            "graficar",
        } <= {t.name for t in tools.tools}
        result = await client.call_tool(
            "resolver",
            {
                "problema": {
                    "operacion": "integral",
                    "expresion": "x**2",
                    "inferior": "0",
                    "superior": "3",
                }
            },
        )
        assert not result.is_error
        assert result.structured_content["exacto"] == "9"
        prompts = await client.list_prompts()
        assert len(prompts.prompts) == 3
        resource = await client.read_resource("calculo://guia")
        assert resource.contents
        prompt = await client.get_prompt("resolver_examen")
        assert prompt.messages
        invalid = await client.call_tool(
            "resolver",
            {"problema": {"operacion": "derivada", "expresion": "x", "orden": 99}},
        )
        assert invalid.is_error
        graph = await client.call_tool(
            "graficar", {"expresion": "x**2", "inferior": "0", "superior": "1"}
        )
        assert not graph.is_error and any(c.type == "image" for c in graph.content)
