import numpy as np
from scipy.integrate import solve_ivp

def resolver_lotka_volterra(alpha, beta, delta, gamma, pre_ini, dep_ini, t_max):
    """
    Resuelve el sistema Lotka-Volterra.
    Retorna arreglos de tiempo, presas y depredadores.
    """
    # 1. Definimos el sistema de ecuaciones diferenciales (EDO)
    def ecuaciones(t, variables):
        x, y = variables
        # x: presas, y: depredadores
        dxdt = alpha * x - beta * x * y
        dydt = delta * x * y - gamma * y
        return [dxdt, dydt]

    # 2. Definimos el intervalo de tiempo
    t_span = (0, t_max)
    
    # Creamos un arreglo de puntos de tiempo para evaluar la solución.
    # Usamos 500 puntos como base para garantizar que la curva sea suave al graficarla.
    t_eval = np.linspace(0, t_max, 500)

    # 3. Resolvemos el sistema con condiciones iniciales
    solucion = solve_ivp(
        ecuaciones, 
        t_span, 
        [pre_ini, dep_ini], 
        t_eval=t_eval, 
        method='RK45'
    )

    # solucion.t contiene el arreglo de tiempo
    # solucion.y[0] contiene el arreglo de la población de presas
    # solucion.y[1] contiene el arreglo de la población de depredadores
    
    return solucion.t, solucion.y[0], solucion.y[1]


def resolver_calor_2d(difusividad, malla, tiempo, longitud):
    """
    Resuelve la Ecuación del Calor 2D por diferencias finitas explícitas.
    """
    L = longitud
    dx = L / (malla - 1)
    
    dt_maximo = (dx**2) / (4 * difusividad)
    dt = dt_maximo * 0.9 
    
    pasos_tiempo = int(tiempo / dt)
    
    # 1. Inicializamos la matriz a temperatura ambiente (20°C)
    u = np.full((malla, malla), 20.0)
    
    # 2. Generamos un sistema de coordenadas espaciales reales (de 0 a L)
    x = np.linspace(0, L, malla)
    y = np.linspace(0, L, malla)
    X, Y = np.meshgrid(x, y)
    
    # 3. Aplicamos la condición inicial circular: (x-5)^2 + (y-5)^2 <= 4
    # (Usamos L/2 para que el centro sea dinámico si L cambia, en este caso 5)
    mascara_circulo = (X - L/2)**2 + (Y - L/2)**2 <= 4.0
    u[mascara_circulo] = 100.0
    
    # Variables para rastrear la evolución temporal
    centro_idx = malla // 2
    historial_tiempo = [0.0]
    historial_temp_centro = [u[centro_idx, centro_idx]]
    tiempo_actual = 0.0
    
    # 4. Evolución temporal (Ecuación del calor)
    for _ in range(pasos_tiempo):
        u_nueva = u.copy()
        u_nueva[1:-1, 1:-1] = u[1:-1, 1:-1] + (difusividad * dt / dx**2) * (
            u[2:, 1:-1] + u[:-2, 1:-1] + u[1:-1, 2:] + u[1:-1, :-2] - 4 * u[1:-1, 1:-1]
        )
        u = u_nueva
        
        tiempo_actual += dt
        historial_tiempo.append(tiempo_actual)
        historial_temp_centro.append(u[centro_idx, centro_idx])
        
    return u, np.array(historial_tiempo), np.array(historial_temp_centro)