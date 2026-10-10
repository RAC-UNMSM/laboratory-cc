"""Módulo de Cálculo III — Geometría en R³, curvas, multivariable y optimización.

Responsable: Jefferson Vilcapoma Pariona (Grupo 02)
Contrato: tools/README.md
"""

from __future__ import annotations
import sympy as sp


def geometria_analitica_r3(u_str: str, v_str: str) -> dict:
    """Realiza operaciones de geometría analítica en R3 (producto punto y producto cruz).

    Args:
        u_str: primer vector en sintaxis de lista o tupla, ej. "[1, 2, 3]".
        v_str: segundo vector en sintaxis de lista o tupla, ej. "[2, -1, 3]".
    """
    try:
        u_expr = sp.parse_expr(u_str.strip())
        v_expr = sp.parse_expr(v_str.strip())
        u = sp.Matrix(u_expr)
        v = sp.Matrix(v_expr)

        if u.shape not in ((3, 1), (1, 3)) or v.shape not in ((3, 1), (1, 3)):
            return {
                "estado": "error",
                "mensaje": "Los vectores deben ser tridimensionales (3 componentes).",
            }

        # Asegurar formato columna
        u = u.reshape(3, 1)
        v = v.reshape(3, 1)

        dot_product = u.dot(v)
        cross_product = u.cross(v)

        resultado_latex = (
            f"\\mathbf{{u}} \\cdot \\mathbf{{v}} = {sp.latex(dot_product)} \\\\\n"
            f"\\mathbf{{u}} \\times \\mathbf{{v}} = {sp.latex(cross_product)}"
        )
        return {
            "estado": "exito",
            "producto_punto": sp.sstr(dot_product),
            "producto_cruz": sp.sstr(list(cross_product)),
            "latex": resultado_latex,
        }
    except Exception as e:
        return {"estado": "error", "mensaje": f"Error en geometria_analitica_r3: {e}"}


def superficies(ecuacion_str: str, variables: str = "x, y, z") -> dict:
    """Analiza una ecuación de superficie S(x, y, z) = 0 y calcula su vector normal (gradiente).

    Args:
        ecuacion_str: expresión implícita de la superficie igualada a cero, ej. "x**2 + y**2 - z**2".
        variables: variables involucradas separadas por coma, default "x, y, z".
    """
    try:
        vars_list = [sp.Symbol(v.strip(), real=True) for v in variables.split(",")]
        local_dict = {str(v): v for v in vars_list}
        ecuacion = sp.parse_expr(ecuacion_str, local_dict=local_dict)

        gradiente = [sp.diff(ecuacion, var) for var in vars_list]
        gradiente_mat = sp.Matrix(gradiente)

        resultado_latex = (
            f"S({', '.join(variables.split(','))}) = {sp.latex(ecuacion)} = 0 \\\\\n"
            f"\\nabla S = {sp.latex(gradiente_mat)}"
        )
        return {
            "estado": "exito",
            "superficie": sp.sstr(ecuacion),
            "gradiente_normal": [sp.sstr(g) for g in gradiente],
            "latex": resultado_latex,
        }
    except Exception as e:
        return {"estado": "error", "mensaje": f"Error en superficies: {e}"}


def frenet_serret_curvatura_torsion(r_str: str, t_var: str = "t") -> dict:
    """Calcula curvatura kappa, torsión tau y componentes cinemáticas para una curva r(t).

    Args:
        r_str: vector de posición r(t) como lista, ej. "[cos(t), sin(t), t]".
        t_var: parámetro de la curva, default "t".
    """
    try:
        t = sp.Symbol(t_var, real=True)
        r = sp.Matrix(sp.parse_expr(r_str, local_dict={t_var: t})).reshape(3, 1)

        v = sp.diff(r, t)
        a = sp.diff(v, t)

        rapidez = sp.simplify(v.norm())
        if rapidez == 0:
            return {"estado": "error", "mensaje": "La rapidez de la curva es cero (curva no regular)."}

        v_cross_a = v.cross(a)
        norm_v_cross_a = sp.simplify(v_cross_a.norm())

        kappa = sp.simplify(norm_v_cross_a / (rapidez**3))
        jerk = sp.diff(a, t)

        if norm_v_cross_a == 0:
            tau = sp.Integer(0)
        else:
            tau = sp.simplify(v_cross_a.dot(jerk) / (norm_v_cross_a**2))

        resultado_latex = (
            f"\\mathbf{{r}}'(t) = {sp.latex(v)} \\\\\n"
            f"\\|\\mathbf{{r}}'(t)\\| = {sp.latex(rapidez)} \\\\\n"
            f"\\kappa(t) = {sp.latex(kappa)} \\\\\n"
            f"\\tau(t) = {sp.latex(tau)}"
        )
        return {
            "estado": "exito",
            "velocidad": sp.sstr(list(v)),
            "rapidez": sp.sstr(rapidez),
            "curvatura": sp.sstr(kappa),
            "torsion": sp.sstr(tau),
            "latex": resultado_latex,
        }
    except Exception as e:
        return {"estado": "error", "mensaje": f"Error en frenet_serret: {e}"}


def derivadas_parciales_gradiente(expr_str: str, variables: str = "x, y") -> dict:
    """Calcula derivadas parciales de primer orden y vector gradiente de un campo escalar.

    Args:
        expr_str: campo escalar f(x, y, ...), ej. "x**2 * y + sin(x*y)".
        variables: variables respecto a las cuales derivar, default "x, y".
    """
    try:
        vars_list = [sp.Symbol(v.strip(), real=True) for v in variables.split(",")]
        local_dict = {str(v): v for v in vars_list}
        f = sp.parse_expr(expr_str, local_dict=local_dict)

        parciales = [sp.diff(f, var) for var in vars_list]
        gradiente = sp.Matrix(parciales)

        resultado_latex = (
            f"f({', '.join(variables.split(','))}) = {sp.latex(f)} \\\\\n"
            f"\\nabla f = {sp.latex(gradiente)}"
        )
        return {
            "estado": "exito",
            "funcion": sp.sstr(f),
            "derivadas_parciales": {str(var): sp.sstr(p) for var, p in zip(vars_list, parciales)},
            "gradiente": [sp.sstr(p) for p in parciales],
            "latex": resultado_latex,
        }
    except Exception as e:
        return {"estado": "error", "mensaje": f"Error en derivadas_parciales: {e}"}


def plano_tangente(expr_str: str, x0: str = "0", y0: str = "0") -> dict:
    """Calcula la ecuación del plano tangente a la superficie z = f(x, y) en el punto (x0, y0).

    Args:
        expr_str: función z = f(x, y), ej. "x**2 + y**2".
        x0: coordenada en x del punto de tangencia (número o expresión exacta, ej. "1", "pi/2").
        y0: coordenada en y del punto de tangencia (número o expresión exacta, ej. "2", "sqrt(2)").
    """
    try:
        x, y = sp.symbols("x y", real=True)
        local_dict = {"x": x, "y": y}
        f = sp.parse_expr(expr_str, local_dict=local_dict)

        p_x0 = sp.sympify(x0)
        p_y0 = sp.sympify(y0)

        z0 = sp.simplify(f.subs({x: p_x0, y: p_y0}))
        fx = sp.diff(f, x)
        fy = sp.diff(f, y)

        fx_0 = sp.simplify(fx.subs({x: p_x0, y: p_y0}))
        fy_0 = sp.simplify(fy.subs({x: p_x0, y: p_y0}))

        # Ecuación: z = z0 + fx(x0,y0)*(x - x0) + fy(x0,y0)*(y - y0)
        plano = sp.simplify(z0 + fx_0 * (x - p_x0) + fy_0 * (y - p_y0))

        resultado_latex = (
            f"z_0 = f({sp.latex(p_x0)}, {sp.latex(p_y0)}) = {sp.latex(z0)} \\\\\n"
            f"f_x({sp.latex(p_x0)}, {sp.latex(p_y0)}) = {sp.latex(fx_0)}, \\quad "
            f"f_y({sp.latex(p_x0)}, {sp.latex(p_y0)}) = {sp.latex(fy_0)} \\\\\n"
            f"\\pi_T: z = {sp.latex(plano)}"
        )
        return {
            "estado": "exito",
            "punto": [sp.sstr(p_x0), sp.sstr(p_y0), sp.sstr(z0)],
            "ecuacion_plano": sp.sstr(plano),
            "latex": resultado_latex,
        }
    except Exception as e:
        return {"estado": "error", "mensaje": f"Error en plano_tangente: {e}"}


def optimizacion_lagrange_hessiano(
    expr_str: str,
    variables: str = "x, y",
    restriccion: str | None = None,
) -> dict:
    """Calcula la matriz Hessiana y optimización con o sin restricciones (Multiplicadores de Lagrange).

    Args:
        expr_str: función objetivo f(x, y, ...), ej. "x**2 + y**2".
        variables: variables involucradas, default "x, y".
        restriccion: ecuación g(x, y) = 0 opcional para Lagrange, ej. "x + y - 1".
    """
    try:
        vars_list = [sp.Symbol(v.strip(), real=True) for v in variables.split(",")]
        local_dict = {str(v): v for v in vars_list}
        f = sp.parse_expr(expr_str, local_dict=local_dict)

        n = len(vars_list)
        hessiano = sp.zeros(n, n)
        for i in range(n):
            for j in range(n):
                hessiano[i, j] = sp.diff(sp.diff(f, vars_list[i]), vars_list[j])

        det_h = sp.simplify(hessiano.det()) if n == 2 else None

        puntos_lagrange = None
        if restriccion:
            lam = sp.Symbol("lambda", real=True)
            local_dict["lambda"] = lam
            g = sp.parse_expr(restriccion, local_dict=local_dict)

            # Sistema de Lagrange: grad(f) - lambda * grad(g) = 0 y g = 0
            sistema = [sp.diff(f, var) - lam * sp.diff(g, var) for var in vars_list]
            sistema.append(g)
            soluciones = sp.solve(sistema, (*vars_list, lam), dict=True)
            puntos_lagrange = [
                {str(k): sp.sstr(v) for k, v in sol.items() if str(k) != "lambda"}
                for sol in soluciones
            ]

        lineas_latex = [f"H = {sp.latex(hessiano)}"]
        if det_h is not None:
            lineas_latex.append(f"\\det(H) = {sp.latex(det_h)}")
        if puntos_lagrange is not None:
            lineas_latex.append(f"\\text{{Puntos críticos (Lagrange)}}: {sp.latex(puntos_lagrange)}")

        return {
            "estado": "exito",
            "hessiano": sp.sstr(hessiano.tolist()),
            "determinante_hessiano": sp.sstr(det_h) if det_h is not None else None,
            "lagrange_puntos": puntos_lagrange,
            "latex": " \\\\\n".join(lineas_latex),
        }
    except Exception as e:
        return {"estado": "error", "mensaje": f"Error en optimizacion_lagrange_hessiano: {e}"}


if __name__ == "__main__":
    print("--- 1. Geometría R3 ---")
    print(geometria_analitica_r3("[1, 2, 3]", "[2, -1, 3]"))
    print("\n--- 3. Frenet-Serret ---")
    print(frenet_serret_curvatura_torsion("[cos(t), sin(t), t]"))
    print("\n--- 5. Plano Tangente ---")
    print(plano_tangente("x**2 + y**2", "1", "2"))
    print("\n--- 6. Lagrange ---")
    print(optimizacion_lagrange_hessiano("x*y", "x, y", restriccion="x + y - 10"))
