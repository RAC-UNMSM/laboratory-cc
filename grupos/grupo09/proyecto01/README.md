### Estado actual del proyecto

#### `datos_validacion.py` 
**Responsable: Orquestador / Datos**

- Valida el modelo recibido.
- Valida las condiciones iniciales y su dimensión.
- Comprueba que el intervalo de tiempo sea válido.
- Valida los parámetros antes de enviarlos al solver.

#### `modelos_referencia.py` 

Actualmente contiene tres modelos de prueba:

- Lineal: $x'=-ax$.
- Logístico: $x'=rx(1-x/K)$.
- Sistema de Lorenz.

También contiene los puntos de equilibrio conocidos para los modelos lineal y logístico y la función `obtener_modelo()` para cargar cada configuración.

#### `modelo_edos.py` 

- Resolución numérica mediante `solve_ivp`.
- Método RK45.
- Manejo de `rtol` y `atol`.
- Trabaja con las validaciones de entrada.
- Actualmente genera 300 puntos para representar la solución.

#### `analisis_estabilidad.py` 

- Cálculo numérico del Jacobiano.
- Cálculo de autovalores.
- Clasificación de los puntos de equilibrio como estables, inestables o no concluyentes.

Actualmente funciona con los modelos lineal y logístico.

#### `visualizacion.py` 

- Gráficas de las soluciones en función del tiempo.
- Soporte para sistemas de hasta 3 variables.
- Retrato de fase para modelos 1D.
- Representación de puntos de equilibrio y dirección del sistema.
- Comparación de trayectorias con distintas condiciones iniciales.
- Las gráficas se guardan automáticamente en formato PNG.

#### `server.py` 
**Responsable: Orquestador / Backend**

Actualmente permite ejecutar:

```bash
python server.py --modelo lineal
python server.py --modelo logistico
python server.py --modelo lorenz