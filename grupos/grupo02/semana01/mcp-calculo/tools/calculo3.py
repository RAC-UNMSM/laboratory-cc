import sympy as sp

# Definición de variables simbólicas globales
x, y, z, t = sp.symbols('x y z t', real=True)
u, v, lambda_ = sp.symbols('u v lambda', real=True)


# =============================================================================
# Geometría Analítica en R3
# =============================================================================
def geometria_analitica_r3():
    """Vectores, rectas, planos y distancias en R3."""
    print("=== TEMA A: GEOMETRÍA ANALÍTICA EN R3 ===")

    # Vectores y puntos
    p0 = sp.Point3D(1, 2, 3)
    p1 = sp.Point3D(4, 0, 5)
    v1 = sp.Matrix([2, -1, 3])
    v2 = sp.Matrix([1, 4, -2])

    # Producto escalar y vectorial
    dot_prod = v1.dot(v2)
    cross_prod = v1.cross(v2)

    # Ecuación del plano dada un punto y un vector normal
    plano = sp.Plane(p0, normal_vector=cross_prod)

    # Ecuación de la recta en R3
    recta = sp.Line3D(p1, direction_ratio=v1)

    # Distancia de un punto a un plano
    p_test = sp.Point3D(0, 0, 0)
    distancia_p_plano = plano.distance(p_test)

    print(f"Producto Escalar: {dot_prod}")
    print(f"Producto Vectorial: {cross_prod}")
    print(f"Ecuación implícita del Plano: {plano.equation()}")
    print(f"Distancia del punto {p_test} al plano: {distancia_p_plano}\n")


# =============================================================================
# Superficies
# =============================================================================
def superficies():
    """Identificación y cambio de coordenadas en superficies (cuádricas, cilíndricas, esféricas)."""
    print("=== TEMA B: SUPERFICIES Y TRANSFORMACIÓN DE COORDENADAS ===")

    # Transformación a Coordenadas Esféricas (r, theta, phi)
    r_sym, theta_sym, phi_sym = sp.symbols('r theta phi', real=True, positive=True)

    x_esf = r_sym * sp.sin(phi_sym) * sp.cos(theta_sym)
    y_esf = r_sym * sp.sin(phi_sym) * sp.sin(theta_sym)
    z_esf = r_sym * sp.cos(phi_sym)

    # Definición implícita de una esfera: x^2 + y^2 + z^2 - R^2 = 0
    R = sp.Symbol('R', positive=True)
    eq_esfera_cartesiana = x**2 + y**2 + z**2 - R**2

    # Sustitución a coordenadas esféricas
    eq_esfera_transformada = sp.simplify(
        eq_esfera_cartesiana.subs({x: x_esf, y: y_esf, z: z_esf})
    )

    print(f"Ecuación Esfera Cartesiana: {eq_esfera_cartesiana} = 0")
    print(f"Transformada a Esféricas: {eq_esfera_transformada} = 0\n")


# =============================================================================
#Funciones Vectoriales
# =============================================================================
def funciones_vectoriales():
    """Triedro de Frenet-Serret (T, N, B), curvatura y torsión."""
    print("=== TEMA C: FUNCIONES VECTORIALES Y FRENET-SERRET ===")

    # Curva parametrizada r(t) (ej. hélice circular)
    r_t = sp.Matrix([sp.cos(t), sp.sin(t), t])

    # Velocidad v(t) y Aceleración a(t)
    v_t = sp.diff(r_t, t)
    a_t = sp.diff(v_t, t)

    rapidez = v_t.norm()

    # Vector Tangente Unitario T(t)
    T = sp.simplify(v_t / rapidez)

    # Vector Binormal B(t) ~ (v x a) / ||v x a||
    v_cross_a = v_t.cross(a_t)
    B = sp.simplify(v_cross_a / v_cross_a.norm())

    # Vector Normal Principal N(t) = B x T
    N = sp.simplify(B.cross(T))

    # Curvatura kappa(t) = ||v x a|| / ||v||^3
    kappa = sp.simplify(v_cross_a.norm() / (rapidez**3))

    # Torsión tau(t) = (v x a) . a' / ||v x a||^2
    da_t = sp.diff(a_t, t)
    tau = sp.simplify(v_cross_a.dot(da_t) / (v_cross_a.norm()**2))

    print(f"Curva r(t): {r_t.T}")
    print(f"Tangente Unitario T(t): {T.T}")
    print(f"Curvatura kappa(t): {kappa}")
    print(f"Torsión tau(t): {tau}\n")


# =============================================================================
# Cálculo Diferencial Multivariable (Dominio y Límites)
# =============================================================================
def calculo_multivariable_basico():
    """Evaluación de límites por trayectorias."""
    print("=== TEMA D: LÍMITES MULTIVARIABLE Y TRAYECTORIAS ===")

    # Función f(x, y) = (x * y) / (x^2 + y^2)
    f_xy = (x * y) / (x**2 + y**2)

    # Límite a lo largo de la trayectoria recta y = m*x
    m = sp.Symbol('m', real=True)
    f_trayectoria_recta = f_xy.subs(y, m * x)
    limite_rectas = sp.limit(f_trayectoria_recta, x, 0)

    print(f"Función: f(x, y) = {f_xy}")
    print(f"Límite acercándose por y = m*x cuando x -> 0: {limite_rectas}")
    print("-> Como depende de 'm', el límite multivariable NO existe.\n")


# =============================================================================
# Derivadas Parciales, Gradiente y Plano Tangente
# =============================================================================
def derivadas_y_geometria_diferencial():
    """Derivadas parciales, gradiente y ecuación del plano tangente."""
    print("=== TEMA E: DERIVADAS, GRADIENTE Y PLANO TANGENTE ===")

    # Campo escalar f(x, y) = x^2 * y + sp.sin(y)
    f = x**2 * y + sp.sin(y)

    # Derivadas parciales
    fx = sp.diff(f, x)
    fy = sp.diff(f, y)

    # Vector Gradiente
    grad_f = sp.Matrix([fx, fy])

    # Plano Tangente a z = f(x,y) en el punto (x0, y0)
    x0, y0 = 1, 0
    z0 = f.subs({x: x0, y: y0})
    fx_eval = fx.subs({x: x0, y: y0})
    fy_eval = fy.subs({x: x0, y: y0})

    # Ecuación z - z0 = fx(x0,y0)*(x - x0) + fy(x0,y0)*(y - y0)
    plano_tangente = sp.Eq(z - z0, fx_eval * (x - x0) + fy_eval * (y - y0))

    print(f"Gradiente grad(f): {grad_f.T}")
    print(f"Plano tangente en ({x0}, {y0}, {z0}): {plano_tangente}\n")


# =============================================================================
#Optimización Multivariable
# =============================================================================
def optimizacion_multivariable():
    """Matriz Hessiana y Multiplicadores de Lagrange."""
    print("=== TEMA F: OPTIMIZACIÓN MULTIVARIABLE ===")

    # 1. Puntos Críticos y Clasificación por Hessiano
    f = x**3 + y**3 - 3 * x * y

    grad_f = [sp.diff(f, var) for var in (x, y)]
    puntos_criticos = sp.solve(grad_f, (x, y), dict=True)

    H = sp.hessian(f, (x, y))

    print(f"Función a optimizar: f(x,y) = {f}")
    print("Puntos críticos hallados:")
    for pt in puntos_criticos:
        H_eval = H.subs(pt)
        det_H = H_eval.det()
        f_xx = H_eval[0, 0]

        tipo = "Desconocido"
        if det_H < 0:
            tipo = "Punto Silla"
        elif det_H > 0:
            tipo = "Mínimo Local" if f_xx > 0 else "Máximo Local"

        print(f"  Punto {pt} -> Det(H) = {det_H} | Clasificación: {tipo}")

    # 2. Multiplicadores de Lagrange
    print("\n-- Multiplicadores de Lagrange --")
    # Maximizar f(x, y) = x * y sujeto a g(x, y) = x^2 + y^2 - 1 = 0
    f_lagrange = x * y
    g_lagrange = x**2 + y**2 - 1

    L = f_lagrange - lambda_ * g_lagrange
    sistema_eqs = [sp.diff(L, var) for var in (x, y, lambda_)]

    soluciones_lagrange = sp.solve(sistema_eqs, (x, y, lambda_), dict=True)
    print(f"Sujeto a restricción: {g_lagrange} = 0")
    print("Soluciones (x, y, lambda):")
    for sol in soluciones_lagrange:
        val_f = f_lagrange.subs(sol)
        print(f"  Punto: (x={sol[x]}, y={sol[y]}) | f(x,y) = {val_f}")


# =============================================================================
# Función Principal
# =============================================================================
def main():
    geometria_analitica_r3()
    superficies()
    funciones_vectoriales()
    calculo_multivariable_basico()
    derivadas_y_geometria_diferencial()
    optimizacion_multivariable()


if __name__ == "__main__":
    main()