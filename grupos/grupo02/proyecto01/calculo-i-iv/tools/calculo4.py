from __future__ import annotations

from typing import Any
import sympy as sp


# ============================================================
# Helpers internos
# ============================================================

def _simbolo(nombre: str) -> sp.Symbol:
    return sp.Symbol(nombre)


def _expresion(texto: str, variables: str | None = None) -> sp.Expr:
    """Convierte una expresion escrita en sintaxis SymPy a una expresion."""
    locals_map: dict[str, Any] = {
        "pi": sp.pi,
        "E": sp.E,
        "oo": sp.oo,
    }
    if variables:
        for nombre in variables.replace(",", " ").split():
            locals_map[nombre.strip()] = sp.Symbol(nombre.strip())
    return sp.sympify(texto, locals=locals_map)


def _vector(texto: str, variables: str | None = None) -> sp.Matrix:
    """Convierte '(a,b,c)' o '[a,b,c]' en un vector columna."""
    expr = _expresion(texto, variables)
    if isinstance(expr, (tuple, list)):
        return sp.Matrix(expr)
    if isinstance(expr, sp.MatrixBase):
        return sp.Matrix(expr)
    raise ValueError(
        "El vector debe escribirse como (P,Q) o (P,Q,R), usando sintaxis SymPy."
    )


def _matrix_latex(matriz: sp.MatrixBase) -> list[list[str]]:
    return [[sp.latex(matriz[i, j]) for j in range(matriz.cols)]
            for i in range(matriz.rows)]


# ============================================================
# TEMA 1
# Parametrizacion de curvas y campos vectoriales
# ============================================================

def parametrizacion_curva(
    x: str,
    y: str,
    z: str | None = None,
    parametro: str = "t",
    inicio: float = 0.0,
    fin: float = 1.0,
    campo: str | None = None,
) -> dict[str, Any]:
    """Analiza una curva parametrizada y, opcionalmente, un campo vectorial.

    Args:
        x: Componente x(t) de la curva, en sintaxis SymPy. Ej.: "cos(t)".
        y: Componente y(t) de la curva, en sintaxis SymPy. Ej.: "sin(t)".
        z: Componente z(t), opcional. Si se omite, la curva es plana.
        parametro: Variable del parametro, normalmente "t".
        inicio: Extremo inicial del intervalo del parametro.
        fin: Extremo final del intervalo del parametro.
        campo: Campo vectorial opcional. Para una curva plana use "(P,Q)"
            y para una espacial "(P,Q,R)". Ej.: "(-y,x)".
    """
    try:
        t = _simbolo(parametro)
        componentes = [_expresion(x, parametro), _expresion(y, parametro)]
        if z is not None:
            componentes.append(_expresion(z, parametro))

        r = sp.Matrix(componentes)
        velocidad = sp.simplify(r.diff(t))
        rapidez = sp.simplify(sp.sqrt(velocidad.dot(velocidad)))
        punto_inicial = r.subs(t, inicio)
        punto_final = r.subs(t, fin)

        resultado: dict[str, Any] = {
            "estado": "exito",
            "parametro": parametro,
            "curva": [sp.sstr(v) for v in r],
            "curva_latex": sp.latex(r),
            "derivada": [sp.sstr(v) for v in velocidad],
            "derivada_latex": sp.latex(velocidad),
            "rapidez": sp.sstr(rapidez),
            "rapidez_latex": sp.latex(rapidez),
            "punto_inicial": [sp.sstr(v) for v in punto_inicial],
            "punto_final": [sp.sstr(v) for v in punto_final],
            "intervalo": [inicio, fin],
        }

        if campo is not None:
            F = _vector(campo, "x y z")
            if len(F) != len(r):
                raise ValueError(
                    "El campo vectorial debe tener la misma dimension que la curva."
                )
            resultado["campo"] = [sp.sstr(v) for v in F]
            resultado["campo_latex"] = sp.latex(F)

        return resultado
    except Exception as exc:
        return {"estado": "error", "mensaje": f"{type(exc).__name__}: {exc}"}


# ============================================================
# TEMA 2
# Integrales de linea y campos conservativos
# ============================================================

def integral_linea(
    campo: str,
    curva_x: str,
    curva_y: str,
    curva_z: str | None = None,
    parametro: str = "t",
    inicio: float = 0.0,
    fin: float = 1.0,
) -> dict[str, Any]:
    """Calcula una integral de linea F·dr y analiza si el campo es conservativo.

    Args:
        campo: Campo vectorial como "(P,Q)" o "(P,Q,R)" en sintaxis SymPy.
            Ej.: "(-y,x)".
        curva_x: x(t), componente x de la curva.
        curva_y: y(t), componente y de la curva.
        curva_z: z(t), opcional para curvas espaciales.
        parametro: Parametro de la curva, normalmente "t".
        inicio: Limite inferior del parametro.
        fin: Limite superior del parametro.

    Returns:
        Un dict con la integral de linea, el integrando, el potencial cuando
        puede obtenerse y el rotacional del campo.
    """
    try:
        t = _simbolo(parametro)
        r_componentes = [
            _expresion(curva_x, parametro),
            _expresion(curva_y, parametro),
        ]
        if curva_z is not None:
            r_componentes.append(_expresion(curva_z, parametro))
        r = sp.Matrix(r_componentes)

        F = _vector(campo, "x y z")
        if len(F) != len(r):
            raise ValueError("El campo y la curva deben tener la misma dimension.")

        dr = r.diff(t)
        integrando = sp.simplify(F.subs({
            sp.Symbol("x"): r[0],
            sp.Symbol("y"): r[1],
            sp.Symbol("z"): r[2] if len(r) == 3 else 0,
        }).dot(dr))

        integral = sp.integrate(integrando, (t, inicio, fin))

        xvar, yvar, zvar = sp.symbols("x y z")
        potencial = None
        conservativo = False
        rotacional = None

        if len(F) == 2:
            P, Q = F
            rot = sp.simplify(sp.diff(Q, xvar) - sp.diff(P, yvar))
            rotacional = sp.sstr(rot)
            conservativo = sp.simplify(rot) == 0

            if conservativo:
                phi = sp.integrate(P, xvar)
                resto = sp.simplify(Q - sp.diff(phi, yvar))
                psi = sp.integrate(resto, yvar)
                potencial = sp.simplify(phi + psi)
        else:
            P, Q, R = F
            curl = sp.Matrix([
                sp.diff(R, yvar) - sp.diff(Q, zvar),
                sp.diff(P, zvar) - sp.diff(R, xvar),
                sp.diff(Q, xvar) - sp.diff(P, yvar),
            ])
            rotacional = [sp.sstr(v) for v in curl]
            conservativo = all(sp.simplify(v) == 0 for v in curl)

            if conservativo:
                phi = sp.integrate(P, xvar)
                resto_y = sp.simplify(Q - sp.diff(phi, yvar))
                phi += sp.integrate(resto_y, yvar)
                resto_z = sp.simplify(R - sp.diff(phi, zvar))
                phi += sp.integrate(resto_z, zvar)
                potencial = sp.simplify(phi)

        return {
            "estado": "exito",
            "campo": [sp.sstr(v) for v in F],
            "curva": [sp.sstr(v) for v in r],
            "integrando": sp.sstr(integrando),
            "integrando_latex": sp.latex(integrando),
            "integral_linea": sp.sstr(integral),
            "integral_linea_latex": sp.latex(integral),
            "conservativo": bool(conservativo),
            "rotacional": rotacional,
            "funcion_potencial": None if potencial is None else sp.sstr(potencial),
            "funcion_potencial_latex": None if potencial is None else sp.latex(potencial),
        }
    except Exception as exc:
        return {"estado": "error", "mensaje": f"{type(exc).__name__}: {exc}"}


# ============================================================
# TEMA 3
# Integrales dobles, cambio de variable y Jacobiano
# ============================================================

def integral_doble(
    expresion: str,
    variable_x: str = "x",
    variable_y: str = "y",
    x_inferior: str = "0",
    x_superior: str = "1",
    y_inferior: str = "0",
    y_superior: str = "1",
    cambio_x: str | None = None,
    cambio_y: str | None = None,
    variables_nuevas: str = "u v",
) -> dict[str, Any]:
    """Calcula una integral doble rectangular y, opcionalmente, un Jacobiano.

    Args:
        expresion: Integrando f(x,y), en sintaxis SymPy.
        variable_x: Nombre de la primera variable, normalmente "x".
        variable_y: Nombre de la segunda variable, normalmente "y".
        x_inferior: Limite inferior de x.
        x_superior: Limite superior de x.
        y_inferior: Limite inferior de y.
        y_superior: Limite superior de y.
        cambio_x: Expresion x(u,v), opcional.
        cambio_y: Expresion y(u,v), opcional.
        variables_nuevas: Variables del cambio, normalmente "u v".

    Returns:
        Resultado de la integral doble y, si se proporciona el cambio,
        el determinante Jacobiano y el integrando transformado.
    """
    try:
        x = sp.Symbol(variable_x)
        y = sp.Symbol(variable_y)
        f = _expresion(expresion, f"{variable_x} {variable_y}")

        xa = _expresion(x_inferior, f"{variable_x} {variable_y}")
        xb = _expresion(x_superior, f"{variable_x} {variable_y}")
        ya = _expresion(y_inferior, f"{variable_x} {variable_y}")
        yb = _expresion(y_superior, f"{variable_x} {variable_y}")

        integral = sp.integrate(f, (y, ya, yb), (x, xa, xb))

        resultado: dict[str, Any] = {
            "estado": "exito",
            "integrando": sp.sstr(f),
            "integrando_latex": sp.latex(f),
            "integral_doble": sp.sstr(integral),
            "integral_doble_latex": sp.latex(integral),
            "limites": {
                variable_x: [sp.sstr(xa), sp.sstr(xb)],
                variable_y: [sp.sstr(ya), sp.sstr(yb)],
            },
        }

        if cambio_x is not None or cambio_y is not None:
            if cambio_x is None or cambio_y is None:
                raise ValueError("Debe proporcionar cambio_x y cambio_y juntos.")

            nombres = variables_nuevas.replace(",", " ").split()
            if len(nombres) != 2:
                raise ValueError("variables_nuevas debe contener exactamente dos variables.")
            u, v = sp.symbols(" ".join(nombres))

            X = _expresion(cambio_x, " ".join(nombres))
            Y = _expresion(cambio_y, " ".join(nombres))

            J = sp.Matrix([
                [sp.diff(X, u), sp.diff(X, v)],
                [sp.diff(Y, u), sp.diff(Y, v)],
            ]).det()

            transformada = sp.simplify(f.subs({x: X, y: Y}) * sp.Abs(J))

            resultado["cambio_variable"] = {
                "x": sp.sstr(X),
                "y": sp.sstr(Y),
                "jacobiano": sp.sstr(J),
                "jacobiano_latex": sp.latex(J),
                "valor_absoluto_jacobiano": sp.sstr(sp.Abs(J)),
                "integrando_transformado": sp.sstr(transformada),
                "integrando_transformado_latex": sp.latex(transformada),
            }

        return resultado
    except Exception as exc:
        return {"estado": "error", "mensaje": f"{type(exc).__name__}: {exc}"}


# ============================================================
# TEMA 4
# Teorema de Green y superficies
# ============================================================

def green(
    P: str,
    Q: str,
    x_inferior: str = "0",
    x_superior: str = "1",
    y_inferior: str = "0",
    y_superior: str = "1",
) -> dict[str, Any]:
    """Aplica el Teorema de Green sobre un rectangulo orientado positivamente.

    Args:
        P: Primera componente P(x,y) del campo.
        Q: Segunda componente Q(x,y) del campo.
        x_inferior: Limite inferior de x de la region.
        x_superior: Limite superior de x de la region.
        y_inferior: Limite inferior de y de la region.
        y_superior: Limite superior de y de la region.

    Returns:
        Integral doble de dQ/dx-dP/dy y la integral de linea equivalente
        calculada recorriendo los cuatro lados del rectangulo.
    """
    try:
        x, y = sp.symbols("x y")
        p = _expresion(P, "x y")
        q = _expresion(Q, "x y")
        xa = _expresion(x_inferior, "x y")
        xb = _expresion(x_superior, "x y")
        ya = _expresion(y_inferior, "x y")
        yb = _expresion(y_superior, "x y")

        integrando_green = sp.simplify(sp.diff(q, x) - sp.diff(p, y))
        integral_doble_green = sp.integrate(
            integrando_green, (y, ya, yb), (x, xa, xb)
        )

        # Frontera positiva: abajo -> derecha -> arriba -> izquierda.
        t = sp.Symbol("t")
        abajo = sp.integrate(
            p.subs({x: t, y: ya}), (t, xa, xb)
        )
        derecha = sp.integrate(
            q.subs({x: xb, y: t}), (t, ya, yb)
        )
        arriba = sp.integrate(
            p.subs({x: t, y: yb}), (t, xb, xa)
        )
        izquierda = sp.integrate(
            q.subs({x: xa, y: t}), (t, yb, ya)
        )
        integral_linea = sp.simplify(abajo + derecha + arriba + izquierda)

        return {
            "estado": "exito",
            "campo": [sp.sstr(p), sp.sstr(q)],
            "rotacion_escalar": sp.sstr(integrando_green),
            "rotacion_escalar_latex": sp.latex(integrando_green),
            "integral_doble": sp.sstr(integral_doble_green),
            "integral_doble_latex": sp.latex(integral_doble_green),
            "integral_linea_frontera": sp.sstr(integral_linea),
            "integral_linea_frontera_latex": sp.latex(integral_linea),
            "verificacion_green": bool(
                sp.simplify(integral_doble_green - integral_linea) == 0
            ),
        }
    except Exception as exc:
        return {"estado": "error", "mensaje": f"{type(exc).__name__}: {exc}"}


# ============================================================
# TEMA 5
# Integrales triples e integrales de superficie
# ============================================================

def integrales_triples_superficie(
    densidad: str = "1",
    x_inferior: str = "0",
    x_superior: str = "1",
    y_inferior: str = "0",
    y_superior: str = "1",
    z_inferior: str = "0",
    z_superior: str = "1",
    superficie_z: str | None = None,
    superficie_x_inferior: str = "0",
    superficie_x_superior: str = "1",
    superficie_y_inferior: str = "0",
    superficie_y_superior: str = "1",
) -> dict[str, Any]:
    """Calcula una integral triple y una integral escalar sobre z=g(x,y).

    Args:
        densidad: Funcion f(x,y,z) para la integral triple.
        x_inferior, x_superior: Limites en x.
        y_inferior, y_superior: Limites en y.
        z_inferior, z_superior: Limites en z.
        superficie_z: Superficie z=g(x,y). Si se omite, no se calcula
            la integral de superficie.
        superficie_x_inferior, superficie_x_superior: Limites de x de la superficie.
        superficie_y_inferior, superficie_y_superior: Limites de y de la superficie.

    Returns:
        Integral triple sobre un bloque rectangular y, opcionalmente,
        integral de superficie de la funcion escalar sobre z=g(x,y).
    """
    try:
        x, y, z = sp.symbols("x y z")
        f = _expresion(densidad, "x y z")

        xa = _expresion(x_inferior, "x y z")
        xb = _expresion(x_superior, "x y z")
        ya = _expresion(y_inferior, "x y z")
        yb = _expresion(y_superior, "x y z")
        za = _expresion(z_inferior, "x y z")
        zb = _expresion(z_superior, "x y z")

        integral_triple = sp.integrate(
            f, (z, za, zb), (y, ya, yb), (x, xa, xb)
        )

        resultado: dict[str, Any] = {
            "estado": "exito",
            "densidad": sp.sstr(f),
            "integral_triple": sp.sstr(integral_triple),
            "integral_triple_latex": sp.latex(integral_triple),
        }

        if superficie_z is not None:
            g = _expresion(superficie_z, "x y")
            xs = _expresion(superficie_x_inferior, "x y")
            xe = _expresion(superficie_x_superior, "x y")
            ys = _expresion(superficie_y_inferior, "x y")
            ye = _expresion(superficie_y_superior, "x y")

            gx = sp.diff(g, x)
            gy = sp.diff(g, y)
            elemento_area = sp.sqrt(1 + gx**2 + gy**2)

            integrando_superficie = sp.simplify(
                f.subs(z, g) * elemento_area
            )
            integral_superficie = sp.integrate(
                integrando_superficie, (y, ys, ye), (x, xs, xe)
            )

            resultado["superficie"] = {
                "z": sp.sstr(g),
                "gradiente_superficie": [sp.sstr(gx), sp.sstr(gy)],
                "dS": sp.sstr(elemento_area),
                "dS_latex": sp.latex(elemento_area),
                "integrando": sp.sstr(integrando_superficie),
                "integral_superficie": sp.sstr(integral_superficie),
                "integral_superficie_latex": sp.latex(integral_superficie),
            }

        return resultado
    except Exception as exc:
        return {"estado": "error", "mensaje": f"{type(exc).__name__}: {exc}"}


# ============================================================
# TEMA 6
# Divergencia, Rotacional, Stokes y Gauss
# ============================================================

def teoremas_integrales_vectoriales(
    campo: str,
    volumen_x_inferior: str = "0",
    volumen_x_superior: str = "1",
    volumen_y_inferior: str = "0",
    volumen_y_superior: str = "1",
    volumen_z_inferior: str = "0",
    volumen_z_superior: str = "1",
) -> dict[str, Any]:
    """Calcula divergencia y rotacional y verifica Gauss en un cuboide.

    Args:
        campo: Campo vectorial "(P,Q,R)" en sintaxis SymPy.
        volumen_x_inferior, volumen_x_superior: Limites en x.
        volumen_y_inferior, volumen_y_superior: Limites en y.
        volumen_z_inferior, volumen_z_superior: Limites en z.

    Returns:
        Divergencia, rotacional, integral triple de la divergencia y flujo
        por la frontera del cuboide. También incluye una verificacion
        algebraica del Teorema de la Divergencia (Gauss).
    """
    try:
        x, y, z = sp.symbols("x y z")
        F = _vector(campo, "x y z")
        if len(F) != 3:
            raise ValueError("Este tool requiere un campo vectorial de R^3.")

        P, Q, R = F

        divergencia = sp.simplify(
            sp.diff(P, x) + sp.diff(Q, y) + sp.diff(R, z)
        )
        rotacional = sp.Matrix([
            sp.diff(R, y) - sp.diff(Q, z),
            sp.diff(P, z) - sp.diff(R, x),
            sp.diff(Q, x) - sp.diff(P, y),
        ])

        xa = _expresion(volumen_x_inferior, "x y z")
        xb = _expresion(volumen_x_superior, "x y z")
        ya = _expresion(volumen_y_inferior, "x y z")
        yb = _expresion(volumen_y_superior, "x y z")
        za = _expresion(volumen_z_inferior, "x y z")
        zb = _expresion(volumen_z_superior, "x y z")

        integral_div = sp.integrate(
            divergencia, (z, za, zb), (y, ya, yb), (x, xa, xb)
        )

        # Flujo exterior de cada una de las seis caras.
        flujo_x_pos = sp.integrate(
            P.subs(x, xb), (z, za, zb), (y, ya, yb)
        )
        flujo_x_neg = sp.integrate(
            -P.subs(x, xa), (z, za, zb), (y, ya, yb)
        )
        flujo_y_pos = sp.integrate(
            Q.subs(y, yb), (z, za, zb), (x, xa, xb)
        )
        flujo_y_neg = sp.integrate(
            -Q.subs(y, ya), (z, za, zb), (x, xa, xb)
        )
        flujo_z_pos = sp.integrate(
            R.subs(z, zb), (y, ya, yb), (x, xa, xb)
        )
        flujo_z_neg = sp.integrate(
            -R.subs(z, za), (y, ya, yb), (x, xa, xb)
        )

        flujo_total = sp.simplify(
            flujo_x_pos + flujo_x_neg +
            flujo_y_pos + flujo_y_neg +
            flujo_z_pos + flujo_z_neg
        )

        # Para Stokes se entrega la identidad diferencial que relaciona
        # el rotacional con una superficie orientada. No se inventa una
        # frontera adicional que el usuario no haya especificado.
        return {
            "estado": "exito",
            "campo": [sp.sstr(v) for v in F],
            "divergencia": sp.sstr(divergencia),
            "divergencia_latex": sp.latex(divergencia),
            "rotacional": [sp.sstr(v) for v in rotacional],
            "rotacional_latex": sp.latex(rotacional),
            "integral_triple_divergencia": sp.sstr(integral_div),
            "flujo_frontera": sp.sstr(flujo_total),
            "verificacion_gauss": bool(
                sp.simplify(integral_div - flujo_total) == 0
            ),
            "flujos_caras": {
                "x_superior": sp.sstr(flujo_x_pos),
                "x_inferior": sp.sstr(flujo_x_neg),
                "y_superior": sp.sstr(flujo_y_pos),
                "y_inferior": sp.sstr(flujo_y_neg),
                "z_superior": sp.sstr(flujo_z_pos),
                "z_inferior": sp.sstr(flujo_z_neg),
            },
            "stokes_forma": (
                "La integral de superficie del rotacional sobre una superficie "
                "orientada es igual a la integral de linea del campo sobre su "
                "curva frontera orientada."
            ),
            "divergencia_forma": (
                "La integral triple de div(F) en el volumen es igual al flujo "
                "de F a traves de la superficie cerrada."
            ),
        }
    except Exception as exc:
        return {"estado": "error", "mensaje": f"{type(exc).__name__}: {exc}"}


# Solo estas funciones se exponen como tools MCP.
HERRAMIENTAS = [
    "parametrizacion_curva",
    "integral_linea",
    "integral_doble",
    "green",
    "integrales_triples_superficie",
    "teoremas_integrales_vectoriales",
]


if __name__ == "__main__":
    print("=== Demo calculo4.py ===")

    print("\n1) Parametrizacion:")
    print(
        parametrizacion_curva(
            "cos(t)", "sin(t)", inicio=0, fin=sp.pi / 2
        )
    )

    print("\n2) Integral de linea / campo conservativo:")
    print(
        integral_linea(
            "(2*x, 2*y)",
            "t",
            "t**2",
            inicio=0,
            fin=1,
        )
    )

    print("\n3) Teorema de Green:")
    print(green("0", "x", "0", "1", "0", "1"))
