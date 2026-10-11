"""
validacion.py - Filtro de seguridad física y numérica para simulaciones.

Evita que los modelos matemáticos procesen valores absurdos que 
podrían corromper las matrices de NumPy o generar resultados ilógicos.
"""

class ValidationError(ValueError):
    """
    Error de validación personalizado. 
    Hereda de ValueError para que la herramienta MCP pueda capturarlo 
    fácilmente y devolver el mensaje al modelo en lugar de crashear.
    """
    pass

def validar_parametros_lotka(alpha: float, beta: float, delta: float, gamma: float, 
                             p0: float, d0: float, t_max: float) -> None:
    """
    Valida las reglas biológicas y temporales del modelo Depredador-Presa.
    """
    # 1. Tasas de interacción (todas deben ser estrictamente positivas)
    tasas = {'alpha': alpha, 'beta': beta, 'delta': delta, 'gamma': gamma}
    for nombre, valor in tasas.items():
        if valor <= 0:
            raise ValidationError(f"Error físico: La tasa '{nombre}' ({valor}) debe ser mayor a 0.")
            
    # 2. Poblaciones (no pueden existir poblaciones negativas)
    if p0 < 0 or d0 < 0:
        raise ValidationError(f"Error biológico: Las poblaciones iniciales no pueden ser negativas. (Presas: {p0}, Depredadores: {d0})")
        
    # 3. Tiempo de simulación
    if t_max <= 0:
        raise ValidationError(f"Error temporal: El tiempo máximo ({t_max} meses) debe ser mayor a 0.")
        
    # 4. Límite de cómputo para evitar bucles gigantes
    if t_max > 5000:
        raise ValidationError(f"Límite excedido: Un tiempo de {t_max} requeriría demasiado cómputo. Usa un valor menor a 5000.")


def validar_parametros_calor(difusividad: float, tamaño_malla: int, tiempo_total: float, 
                             longitud_placa: float, radio_fuente: float) -> None:
    """
    Valida las restricciones termodinámicas y geométricas de la Ecuación del Calor 2D.
    """
    # 1. Propiedades térmicas
    if difusividad <= 0:
        raise ValidationError(f"Error termodinámico: La difusividad térmica ({difusividad}) debe ser estrictamente positiva.")
        
    # 2. Restricciones de la malla geométrica
    if not isinstance(tamaño_malla, int) or tamaño_malla < 5 or tamaño_malla > 200:
        raise ValidationError(f"Error de malla: El tamaño ({tamaño_malla}) debe ser un entero entre 5 y 200 para garantizar estabilidad numérica.")
        
    # 3. Geometría física de la placa
    if longitud_placa <= 0:
        raise ValidationError("Error geométrico: La longitud de la placa debe ser mayor a 0.")
    if radio_fuente <= 0:
        raise ValidationError("Error geométrico: El radio de la fuente de calor debe ser mayor a 0.")
        
    # 4. Condición de frontera interna (la fuente no puede salirse de la placa)
    if radio_fuente >= (longitud_placa / 2):
        raise ValidationError(f"Error de diseño: El radio de la fuente ({radio_fuente}) es demasiado grande. Debe caber dentro de la placa (longitud/2 = {longitud_placa/2}).")
        
    # 5. Tiempo
    if tiempo_total <= 0:
        raise ValidationError("Error temporal: El tiempo de simulación térmica debe ser mayor a 0.")


def validar_parametros_decaimiento(n0: float, lam: float, t_max: float) -> None:
    """
    Valida las restricciones físicas y temporales del modelo de Decaimiento Radiactivo.
    """
    # 1. Cantidad inicial de sustancia
    if n0 < 0:
        raise ValidationError(f"Error físico: La cantidad inicial (N0 = {n0}) no puede ser negativa. Debe ser mayor o igual a 0.")
        
    # 2. Constante de desintegración
    if lam <= 0:
        raise ValidationError(f"Error cinético: La constante de decaimiento lambda ({lam}) debe ser estrictamente mayor a 0 para representar un decaimiento real.")
        
    # 3. Tiempo de simulación
    if t_max <= 0:
        raise ValidationError(f"Error temporal: El tiempo máximo de simulación ({t_max}) debe ser mayor a 0.")
    
    # 4. Límite de cómputo y representación gráfica (opcional pero recomendado)
    if t_max > 100000:
         raise ValidationError(f"Límite excedido: Un tiempo de {t_max} es demasiado grande para la visualización. Por favor, usa un valor menor a 100000.")