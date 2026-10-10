"""PRUEBA DE CORRECTITUD MATEMATICA -- respuestas conocidas, a mano.

Esta NO es la prueba de los tests: es la que responde "las tools del grupo
calculan bien?", que es lo que va a ver el profesor.

Cada caso tiene la respuesta correcta puesta a mano (no la computa sympy en el
test), y se busca ese valor DENTRO de lo que devuelve la tool -- porque las
tools envuelven el resultado en su propio formato ('datos', 'exacto',
'latex'...) y no todas lo exponen igual.

    python _prueba_matematica.py
"""

import asyncio
import json
import math

import server

FALLOS = 0
CASOS = 0


def _a_texto(d):
    """Todo el dict serializado a texto: para buscar un valor no importa donde
    lo haya puesto la tool."""
    return json.dumps(d, ensure_ascii=False, default=str)


def _numeros(d):
    """Todos los valores numéricos que aparecen en el dict.

    Incluye los que SymPy devuelve como fracciones exactas en texto ("1/3",
    "1/4"), que son la forma normal en que estas tools reportan un resultado:
    un checker que solo mira floats marca como error la mitad de las
    respuestas correctas."""
    import re
    from fractions import Fraction
    vals = []

    def agregar(x):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            vals.append(float(x))
            return
        if isinstance(x, str):
            s = x.strip()
            try:
                vals.append(float(s))
                return
            except ValueError:
                pass
            m = re.fullmatch(r"(-?\d+)\s*/\s*(-?\d+)", s)
            if m:
                try:
                    vals.append(float(Fraction(int(m.group(1)), int(m.group(2)))))
                except (ZeroDivisionError, ValueError):
                    pass

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
        else:
            agregar(x)

    walk(d)
    return vals


async def main():
    global CASOS, FALLOS

    async def check(nombre, args, texto_esperado=None, numero_esperado=None, tol=1e-9):
        global CASOS, FALLOS
        CASOS += 1
        try:
            res = await server.mcp.call_tool(nombre, args)
            d = res.structured_content
            if d is None:
                for b in (res.content or []):
                    try:
                        d = json.loads(b.text)
                        break
                    except Exception:
                        pass
        except Exception as exc:
            FALLOS += 1
            print("  XX {} -> {}: {}".format(nombre, type(exc).__name__, exc))
            return
        if not isinstance(d, dict):
            FALLOS += 1
            print("  XX {} -> no devolvio un dict".format(nombre))
            return

        problemas = []
        if texto_esperado is not None and texto_esperado not in _a_texto(d):
            problemas.append("no aparece {!r}".format(texto_esperado))
        if numero_esperado is not None:
            if not any(abs(v - numero_esperado) < tol for v in _numeros(d)):
                problemas.append("ningun numero ~= {} (hay {})".format(
                    numero_esperado, [round(v, 6) for v in _numeros(d)][:8]))
        if problemas:
            FALLOS += 1
            print("  XX {} {}".format(nombre, "; ".join(problemas)))
            print("     -> " + _a_texto(d)[:200])
        else:
            print("  ok {}".format(nombre))

    print("=" * 74)
    print("CORRECTITUD MATEMATICA -- {} casos con respuesta conocida".format(25))
    print("=" * 74)

    print("\n[1] Tools base del servidor (server.py)")
    await check("calcular_derivada", {"expresion": "x**3*sin(x)"},
                texto_esperado="3*x**2*sin(x)")
    await check("calcular_derivada", {"expresion": "x**2+3*x", "orden": 2},
                texto_esperado="2")
    await check("calcular_integral", {"expresion": "x*exp(x)"},
                texto_esperado="(x - 1)*exp(x)")
    await check("calcular_integral",
                {"expresion": "x**2", "limite_inferior": "0", "limite_superior": "1"},
                numero_esperado=1.0 / 3.0)
    await check("calcular_gradiente", {"expresion": "x**2*y", "variables": ["x", "y"]},
                texto_esperado="2*x*y")
    await check("calcular_integral", {"expresion": "sin(x)"}, texto_esperado="-cos(x)")
    print("\n[2] Verificacion de respuestas del alumno")
    await check("verificar_respuesta",
                {"respuesta_alumno": "x**3/3", "expresion": "x**2"},
                texto_esperado='"correcta": true')
    await check("verificar_respuesta",
                {"respuesta_alumno": "x**3/3 + 1", "expresion": "x**2"},
                texto_esperado='"correcta": true')
    await check("verificar_respuesta",
                {"respuesta_alumno": "x*exp(x) - exp(x) + C", "expresion": "x*exp(x)"},
                texto_esperado='"correcta": true')
    await check("verificar_respuesta",
                {"respuesta_alumno": "2", "referencia": "2"},
                texto_esperado='"correcta": true')

    print("\n[3] Calculo I -- Cristhian")
    await check("calculo1_calcular_limite", {"expresion": "sin(x)/x", "punto": "0"},
                numero_esperado=1.0)
    await check("calculo1_calcular_limite", {"expresion": "(x**2-1)/(x-1)", "punto": "1"},
                numero_esperado=2.0)
    await check("calculo1_calcular_limite", {"expresion": "1/x", "punto": "0"},
                texto_esperado="existe")
    await check("calculo1_analizar_continuidad", {"expresion": "x/x", "punto": "0"},
                texto_esperado="removible")
    await check("calculo1_analizar_asintotas", {"expresion": "(x**2+1)/(x-1)"},
                texto_esperado="vertical")
    await check("calculo1_analizar_asintotas", {"expresion": "(x**2+1)/(x-1)"},
                texto_esperado="oblicua")
    await check("calculo1_derivada_implicita", {"ecuacion": "x**2+y**2-25"},
                texto_esperado="-x/y")
    await check("calculo1_recta_tangente", {"expresion": "x**2", "punto": "2"},
                texto_esperado="4*x - 4")
    await check("calculo1_optimizar_polinomio",
                {"expresion": "x**3-3*x", "inicio": "-2", "fin": "2"},
                numero_esperado=-2.0)
    await check("calculo1_verificar_derivada", {"expresion": "x**2", "respuesta": "2*x"},
                texto_esperado="correcta")

    print("\n[4] Calculo II -- Yhin")
    await check("calculo2_calcular_integral_indefinida", {"expresion": "x**2"},
                texto_esperado="x**3/3")
    await check("calculo2_calcular_integral_indefinida", {"expresion": "sin(x)"},
                texto_esperado="-cos(x)")
    await check("calculo2_riemann_y_teorema_fundamental",
                {"expresion": "x**2", "a_str": "0", "b_str": "1", "n_particiones": 4},
                numero_esperado=1.0 / 3.0, tol=1e-6)
    await check("calculo2_aplicaciones_geometricas",
                {"tipo": "area", "f_str": "x**2", "a_str": "0", "b_str": "1"},
                numero_esperado=1.0 / 3.0)
    await check("calculo2_integrales_impropias_gamma_beta",
                {"expresion": "1/x**2", "a_str": "1", "b_str": "oo"},
                numero_esperado=1.0)
    await check("calculo2_centro_masa_e_integracion_num",
                {"operacion_tipo": "trapecio", "expresion": "x**2",
                 "a_str": "0", "b_str": "1", "n_tramos": 100},
                numero_esperado=1.0 / 3.0, tol=1e-3)
    await check("calculo2_tecnicas_avanzadas_integracion",
                {"expresion": "1/(x**2-1)", "tecnica": "fracciones_parciales"},
                texto_esperado="log")

    print("\n[5] Calculo IV -- Angel")
    await check("calculo4_integral_doble",
                {"expresion": "x*y", "x_inferior": "0", "x_superior": "1",
                 "y_inferior": "0", "y_superior": "1"},
                numero_esperado=0.25)
    await check("calculo4_integral_doble",
                {"expresion": "x+y", "x_inferior": "0", "x_superior": "2",
                 "y_inferior": "0", "y_superior": "3"},
                numero_esperado=15.0)
    await check("calculo4_green", {"P": "-y", "Q": "x",
                                   "x_inferior": "0", "x_superior": "1",
                                   "y_inferior": "0", "y_superior": "1"},
                numero_esperado=2.0)
    await check("calculo4_parametrizacion_curva",
                {"x": "cos(t)", "y": "sin(t)", "parametro": "t",
                 "inicio": "0", "fin": "2*pi"},
                texto_esperado="2")
    await check("calculo4_integral_linea",
                {"campo": "(-y, x, 0)", "curva_x": "cos(t)", "curva_y": "sin(t)",
                 "curva_z": "0", "parametro": "t", "inicio": "0", "fin": "2*pi"},
                numero_esperado=2 * math.pi)
    await check("calculo4_integrales_triples_superficie",
                {"densidad": "1", "x_inferior": "0", "x_superior": "1",
                 "y_inferior": "0", "y_superior": "1",
                 "z_inferior": "0", "z_superior": "1",
                 "superficie_z": "1"},
                numero_esperado=1.0)
    await check("calculo4_teoremas_integrales_vectoriales",
                {"campo": "(x, y, z)",
                 "volumen_x_inferior": "0", "volumen_x_superior": "1",
                 "volumen_y_inferior": "0", "volumen_y_superior": "1",
                 "volumen_z_inferior": "0", "volumen_z_superior": "1"},
                numero_esperado=1.0)

    print("\n" + "=" * 74)
    print("RESULTADO: {}/{} correctos, {} fallos".format(CASOS - FALLOS, CASOS, FALLOS))
    print("=" * 74)
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
