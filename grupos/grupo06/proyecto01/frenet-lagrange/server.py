#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server.py — Servidor MCP Completo para Geometría Diferencial y Optimización
===========================================================================
Servidor Model Context Protocol (MCP) que expone el conjunto completo de
herramientas de cálculo matemático simbólico/numérico a Claude:

  1. analizar_curva_frenet: Triedro de Frenet (T, N, B), curvatura, torsión y planos.
  2. analizar_puntos_criticos_hessiana: Matriz Hessiana y clasificación de puntos críticos.
  3. optimizar_lagrange: Optimización con restricciones usando multiplicadores de Lagrange.
"""

import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from metodos_frenet import resolver_frenet

try:
    from metodos_hessiana import resolver_hessiana
except ImportError:
    resolver_hessiana = None

try:
    from metodos_lagrange import resolver_lagrange
except ImportError:
    resolver_lagrange = None

from validacion import (
    validar_expresion_matematica,
    validar_punto_evaluacion,
    validar_constantes,
    FormatoEntradaInvalidoError
)
from storage import StorageManager

storage = StorageManager()

def procesar_mcp_request(linea: str) -> dict | None:
    """Procesa una solicitud de JSON-RPC del protocolo MCP."""
    if not linea.strip():
        return None

    try:
        req = json.loads(linea)
    except json.JSONDecodeError:
        return None

    msg_id = req.get("id")
    method = req.get("method")

    # 1. Inicialización MCP
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "math-mcp-server",
                    "version": "1.0.0"
                }
            }
        }

    if method == "notifications/initialized":
        return None

    # 2. Lista completa de herramientas expuestas a Claude
    if method == "tools/list":
        tools = [
            {
                "name": "analizar_curva_frenet",
                "description": "Calcula de forma exacta el triedro de Frenet (T, N, B), curvatura kappa, torsión tau, rapidez v y los planos fundamentales (osculador, normal, rectificante) de una curva r(t) en R^3.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "r": {
                            "type": "string",
                            "description": "Expresión vectorial r(t), ej: 'cos(t), sin(t), t' o 't, t^2, t^3'"
                        },
                        "t0": {
                            "type": "string",
                            "description": "Punto de evaluación t0, ej: '0' o 'pi/4'",
                            "default": "0"
                        },
                        "parametro": {
                            "type": "string",
                            "description": "Símbolo paramétrico (por defecto 't')",
                            "default": "t"
                        },
                        "constantes": {
                            "type": "object",
                            "description": "Valores para constantes simbólicas ej: {'a': 2, 'b': 1}"
                        }
                    },
                    "required": ["r"]
                }
            },
            {
                "name": "analizar_puntos_criticos_hessiana",
                "description": "Encuentra puntos críticos de una función multivariable f(x, y, ...), calcula la matriz Hessiana y clasifica cada punto (máximo, mínimo, punto silla).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "f": {
                            "type": "string",
                            "description": "Función escalar f, ej: 'x^3 + y^3 - 3*x*y' o 'x^2 + y^2'"
                        },
                        "variables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de variables de la función, ej: ['x', 'y']"
                        }
                    },
                    "required": ["f"]
                }
            },
            {
                "name": "optimizar_lagrange",
                "description": "Resuelve problemas de optimización con restricciones de la forma f(x, y, ...) sujeta a g_i(x, y, ...) = 0 mediante Multiplicadores de Lagrange.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "f": {
                            "type": "string",
                            "description": "Función objetivo f(x, y, ...), ej: 'x*y'"
                        },
                        "restricciones": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de restricciones g(x, y, ...) = 0, ej: ['x^2 + y^2 - 1']"
                        },
                        "variables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de variables, ej: ['x', 'y']"
                        }
                    },
                    "required": ["f", "restricciones"]
                }
            }
        ]
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": tools}
        }

    # 3. Ejecución de herramientas requeridas por Claude
    if method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        try:
            if tool_name == "analizar_curva_frenet":
                r_str = args.get("r")
                t0 = args.get("t0", "0")
                parametro = args.get("parametro", "t")
                constantes = validar_constantes(args.get("constantes"))

                validar_expresion_matematica(r_str)
                validar_punto_evaluacion(t0)

                res = resolver_frenet(r=r_str, t0=t0, parametro=parametro, constantes=constantes)
                storage.guardar_resultado("analizar_curva_frenet", args, res)

            elif tool_name == "analizar_puntos_criticos_hessiana":
                if resolver_hessiana is None:
                    raise RuntimeError("El módulo metodos_hessiana.py no está disponible.")
                f_str = args.get("f")
                variables = args.get("variables", None)

                validar_expresion_matematica(f_str)
                res = resolver_hessiana(f=f_str, variables=variables)
                storage.guardar_resultado("analizar_puntos_criticos_hessiana", args, res)

            elif tool_name == "optimizar_lagrange":
                if resolver_lagrange is None:
                    raise RuntimeError("El módulo metodos_lagrange.py no está disponible.")
                f_str = args.get("f")
                restricciones = args.get("restricciones", [])
                variables = args.get("variables", None)

                validar_expresion_matematica(f_str)
                for g in restricciones:
                    validar_expresion_matematica(g)

                res = resolver_lagrange(f=f_str, restricciones=restricciones, variables=variables)
                storage.guardar_resultado("optimizar_lagrange", args, res)

            else:
                raise ValueError(f"Herramienta desconocida: {tool_name}")

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(res, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            }

        except (FormatoEntradaInvalidoError, Exception) as err:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error ejecutando la herramienta {tool_name}: {str(err)}"
                        }
                    ]
                }
            }

    if msg_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": "Método no encontrado"
            }
        }

    return None

def main():
    """Bucle principal de comunicación por STDIN / STDOUT."""
    for linea in sys.stdin:
        respuesta = procesar_mcp_request(linea)
        if respuesta:
            sys.stdout.write(json.dumps(respuesta, ensure_ascii=False) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
