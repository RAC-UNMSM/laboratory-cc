from mcp.server.mcpserver import MCPServer
from typing import List, Dict, Any
import importlib
import os
import sympy as sp
import numpy as np

from resultado import ResultadoMetodo, EstadoMetodo
from expresiones import parsear_expresion
from identificadores import crear_identificador
from reportes import generar_reporte_html
from storage import subir_reporte
from validacion import validar_entrada, resultado_error

# En el contenedor el servidor escucha por HTTP (puerto 8000); para usarlo
# desde un cliente local por stdio, exportar MCP_TRANSPORT=stdio.
TRANSPORTE = os.environ.get("MCP_TRANSPORT", "streamable-http")
mcp = MCPServer("grupo08-sistemas-no-lineales")

_METODOS_DISPONIBLES = {
    "newton_sistemas": ("metodos.newton_sistemas", "newton_sistemas"),
    "newton_raphson": ("metodos.newton_sistemas", "newton_sistemas"),
    "punto_fijo": ("metodos.punto_fijo", "punto_fijo_varias_variables"),
    "punto_fijo_varias_variables": ("metodos.punto_fijo", "punto_fijo_varias_variables"),
    "cuasi_newton": ("metodos.cuasi_newton", "cuasi_newton_broyden"),
    "cuasi_newton_broyden": ("metodos.cuasi_newton", "cuasi_newton_broyden"),
    "descenso_gradiente": ("metodos.descenso", "descenso_mas_rapido"),
    "descenso_mas_rapido": ("metodos.descenso", "descenso_mas_rapido"),
    "homotopia_continuacion": ("metodos.homotopia", "homotopia_continuacion"),
}


def _compilar_funciones(expresiones: List[str], variables: List[str]):
    simbolos = tuple(sp.Symbol(v) for v in variables)

    funciones = []
    for expr in expresiones:
        f_sym = parsear_expresion(expr, variables)
        f_num = sp.lambdify(simbolos, f_sym, modules=['numpy'])

        def wrapper(x, f_num=f_num):
            return float(f_num(*x))

        funciones.append(wrapper)
    return funciones


def _ejecutar_metodo(
    nombre_metodo: str,
    modulo: str,
    funcion: str,
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float,
    max_iter: int,
) -> Dict[str, Any]:
    errores = validar_entrada(expresiones, variables, x0, tolerancia, max_iter)
    if errores:
        return resultado_error(nombre_metodo, errores).model_dump()

    try:
        funciones = _compilar_funciones(expresiones, variables)
        mod = importlib.import_module(modulo)
        impl = getattr(mod, funcion)
        resultado = impl(funciones, x0, tolerancia, max_iter)
        return resultado.model_dump()
    except ImportError:
        return ResultadoMetodo(
            method=nombre_metodo,
            status=EstadoMetodo.INVALID_INPUT,
            warnings=[f"Módulo no implementado: {modulo}"],
            message="Método no disponible aún."
        ).model_dump()
    except Exception as e:
        return ResultadoMetodo(
            method=nombre_metodo,
            status=EstadoMetodo.INVALID_INPUT,
            warnings=[str(e)],
            message="Error al ejecutar el método."
        ).model_dump()


@mcp.tool()
def cuasi_newton_broyden(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando el método de Broyden."""
    return _ejecutar_metodo(
        "cuasi_newton_broyden",
        "metodos.cuasi_newton",
        "cuasi_newton_broyden",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def descenso_mas_rapido(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando descenso más rápido."""
    return _ejecutar_metodo(
        "descenso_mas_rapido",
        "metodos.descenso",
        "descenso_mas_rapido",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def newton_sistemas(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando Newton-Raphson."""
    return _ejecutar_metodo(
        "newton_sistemas",
        "metodos.newton_sistemas",
        "newton_sistemas",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def punto_fijo_varias_variables(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando punto fijo."""
    return _ejecutar_metodo(
        "punto_fijo_varias_variables",
        "metodos.punto_fijo",
        "punto_fijo_varias_variables",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def homotopia_continuacion(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando homotopía."""
    return _ejecutar_metodo(
        "homotopia_continuacion",
        "metodos.homotopia",
        "homotopia_continuacion",
        expresiones, variables, x0, tolerancia, max_iter
    )


def _formatear_vector_tex(vector: List[float]) -> str:
    return r"\begin{bmatrix}" + r"\\".join(f"{valor:.8g}" for valor in vector) + r"\end{bmatrix}"


def _construir_contexto_ejercicio(
    enunciado: str,
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    metodo: str,
    tolerancia: float,
    max_iter: int,
    resultado: Dict[str, Any],
) -> Dict[str, Any]:
    simbolos = [sp.Symbol(variable) for variable in variables]
    expresiones_sym = [parsear_expresion(expresion, variables) for expresion in expresiones]
    vector_funciones = r"\begin{bmatrix}" + r"\\".join(
        sp.latex(expresion) for expresion in expresiones_sym
    ) + r"\end{bmatrix}"

    es_punto_fijo = metodo in ("punto_fijo", "punto_fijo_varias_variables")
    if es_punto_fijo:
        ecuacion = r"\mathbf{x}=\mathbf{G}(\mathbf{x})=" + vector_funciones
        nombre_jacobiano = r"J_G(\mathbf{x})"
    else:
        ceros = r"\begin{bmatrix}" + r"\\".join("0" for _ in expresiones) + r"\end{bmatrix}"
        ecuacion = r"F(\mathbf{x})=" + vector_funciones + "=" + ceros
        nombre_jacobiano = r"J_F(\mathbf{x})"

    jacobiano = sp.Matrix(expresiones_sym).jacobian(simbolos)
    matriz_tex = sp.latex(jacobiano)

    funciones = _compilar_funciones(expresiones, variables)
    trayectoria = resultado.get("trajectory") or []
    iteraciones = []
    for indice, punto in enumerate(trayectoria):
        punto_array = np.asarray(punto, dtype=float)
        valores = np.asarray([funcion(punto_array) for funcion in funciones], dtype=float)
        if es_punto_fijo:
            valores = valores - punto_array
        if indice == 0:
            error = None
        else:
            diferencia = punto_array - np.asarray(trayectoria[indice - 1], dtype=float)
            error = float(np.linalg.norm(diferencia, ord=np.inf if es_punto_fijo else 2))
        iteraciones.append(
            {
                "k": indice,
                "x": punto_array.tolist(),
                "error": error,
                "residuo": float(np.linalg.norm(valores)),
            }
        )

    error_final = iteraciones[-1]["error"] if iteraciones else None
    residuo_final = iteraciones[-1]["residuo"] if iteraciones else None
    pasos = [f"Se formula el problema: \\({ecuacion}\\)."]
    if metodo in ("newton_sistemas", "newton_raphson"):
        pasos.extend(
            [
                f"El Jacobiano es \\({nombre_jacobiano}={matriz_tex}\\); el solver lo aproxima mediante diferencias centrales.",
                r"Se resuelve \(J_F(\mathbf{x}_k)\,\Delta\mathbf{x}_k=-F(\mathbf{x}_k)\) y se actualiza \(\mathbf{x}_{k+1}=\mathbf{x}_k+\Delta\mathbf{x}_k\).",
            ]
        )
        criterio = r"\|F(\mathbf{x}_k)\|_2<\varepsilon"
    elif metodo in ("punto_fijo", "punto_fijo_varias_variables"):
        pasos.append(r"Se itera \(\mathbf{x}_{k+1}=\mathbf{G}(\mathbf{x}_k)\).")
        criterio = r"\|\mathbf{x}_{k+1}-\mathbf{x}_k\|_\infty<\varepsilon"
    elif metodo in ("cuasi_newton", "cuasi_newton_broyden"):
        pasos.extend(
            [
                r"Se inicia la aproximación del Jacobiano con \(B_0=I\).",
                r"Se resuelve \(B_k\,\Delta\mathbf{x}_k=-F(\mathbf{x}_k)\) y se actualiza \(B_k\) con la fórmula de rango uno de Broyden.",
            ]
        )
        criterio = r"\|F(\mathbf{x}_k)\|_2<\varepsilon"
    elif metodo in ("descenso_gradiente", "descenso_mas_rapido"):
        pasos.extend(
            [
                r"Se minimiza \(\phi(\mathbf{x})=\frac{1}{2}\|F(\mathbf{x})\|_2^2\).",
                f"El gradiente es \\((\\nabla\\phi=2J_F(\\mathbf{{x}})^T F(\\mathbf{{x}})),\\quad J_F={matriz_tex}\\); se usa búsqueda de línea.",
            ]
        )
        criterio = r"\|F(\mathbf{x}_k)\|_2<\varepsilon"
    else:
        pasos.extend(
            [
                r"Se define la homotopía \(H(\mathbf{x},t)=F(\mathbf{x})-(1-t)F(\mathbf{x}_0)\).",
                r"Se incrementa \(t\) de 0 a 1 y se corrige cada punto mediante Newton.",
            ]
        )
        criterio = r"\|F(\mathbf{x}(1))\|_2<\varepsilon"

    solucion = resultado.get("solution") or []
    valores_solucion = np.asarray([funcion(solucion) for funcion in funciones], dtype=float)
    if es_punto_fijo:
        valores_solucion = valores_solucion - np.asarray(solucion, dtype=float)
    verificacion_vector = valores_solucion.tolist()
    conclusion = (
        f"Estado: {resultado.get('status')}. Solucion aproximada: "
        f"({', '.join(f'{float(valor):.10g}' for valor in solucion)}). "
        f"El metodo registro {resultado.get('iterations', 0)} iteraciones."
    )

    return {
        "enunciado": enunciado,
        "ecuaciones_tex": [ecuacion, f"{nombre_jacobiano}={matriz_tex}"],
        "punto_inicial": x0,
        "tolerancia": tolerancia,
        "max_iteraciones": max_iter,
        "criterio_tex": criterio.replace(r"\varepsilon", f"{tolerancia:g}"),
        "pasos": pasos,
        "iteraciones": iteraciones,
        "error_final": error_final,
        "residuo_final": residuo_final,
        "verificacion_tex": (
            r"\text{Residual en la solucion}=" + _formatear_vector_tex(verificacion_vector)
        ),
        "conclusion": conclusion,
        "grafico": "Trayectoria de las variables, incrustada como SVG en el HTML.",
    }


def _resolver_ejercicio(
    enunciado: str,
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    metodo: str,
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Ejecuta un método, genera su HTML y lo sube al storage del laboratorio."""
    if not enunciado.strip():
        return {"status": "invalid_input", "message": "El enunciado no puede estar vacío."}
    if metodo not in _METODOS_DISPONIBLES:
        return {
            "status": "invalid_input",
            "message": f"Método no disponible: {metodo}.",
            "metodos_disponibles": sorted(_METODOS_DISPONIBLES),
        }

    modulo, funcion = _METODOS_DISPONIBLES[metodo]
    resultado = _ejecutar_metodo(
        metodo,
        modulo,
        funcion,
        expresiones,
        variables,
        x0,
        tolerancia,
        max_iter,
    )
    estado = resultado.get("status")
    estado = getattr(estado, "value", estado)
    resultado["status"] = estado
    if estado == EstadoMetodo.INVALID_INPUT.value:
        return {"resultado": resultado, "status": "invalid_input", "reporte_url": None}

    contexto = _construir_contexto_ejercicio(
        enunciado,
        expresiones,
        variables,
        x0,
        metodo,
        tolerancia,
        max_iter,
        resultado,
    )
    resultado["final_error"] = contexto["error_final"]
    if contexto["residuo_final"] is not None:
        resultado["final_residual"] = contexto["residuo_final"]

    identificador = crear_identificador()
    html = generar_reporte_html(
        resultado,
        f"Resolucion: {metodo}",
        identificador,
        contexto,
    )
    reporte_url = subir_reporte(html, identificador)
    return {
        "status": resultado.get("status"),
        "resultado": resultado,
        "reporte_url": reporte_url,
        "id": identificador,
        "mensaje": (
            "Ejercicio resuelto. Muestra al usuario el enlace de reporte_url."
            if reporte_url
            else "Ejercicio resuelto. El reporte no se pudo publicar."
        ),
    }


@mcp.tool()
def resolver_ejercicio(
    enunciado: str,
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    metodo: str,
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un ejercicio y publica un reporte HTML con un enlace público.

    Usa esta herramienta cuando el usuario envíe un ejercicio del tema. Primero
    interpreta el enunciado y entrega expresiones, variables, x0 y método en forma
    estructurada. Si el método o el punto inicial faltan en el enunciado, pregunta
    al usuario antes de invocar la herramienta. El reporte incluye formulación TeX,
    pasos del método, tabla de trayectoria, verificación y gráfica SVG. La respuesta
    trae reporte_url, un enlace público al reporte: muéstraselo siempre al
    usuario (si es null, el reporte no se pudo publicar).
    Métodos aceptados: newton_sistemas, punto_fijo_varias_variables,
    cuasi_newton_broyden, descenso_mas_rapido, homotopia_continuacion.
    """
    return _resolver_ejercicio(
        enunciado,
        expresiones,
        variables,
        x0,
        metodo,
        tolerancia,
        max_iter,
    )


if __name__ == "__main__":
    if TRANSPORTE == "streamable-http":
        mcp.run(
            transport=TRANSPORTE,
            host=os.environ.get("MCP_HOST", "0.0.0.0"),
            port=int(os.environ.get("MCP_PORT", "8000")),
        )
    else:
        mcp.run(transport=TRANSPORTE)