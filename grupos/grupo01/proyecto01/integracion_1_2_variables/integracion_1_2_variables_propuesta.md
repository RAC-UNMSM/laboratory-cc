# Tema: Integración simple y doble

# Contenido
La tool recibe una función `f` de una o dos variables. En el caso univariado, el dominio es un intervalo y en el caso de dos variables puede ser un dominio general, es decir, no necesarimente rectangular. Con esa información, se determina la integral con el uso de la librería `sympy`. Devuelve la integral (un número real) y la gráfica asociada, es decir, en el caso univarable el área bajo la curva y en caso de dos variables el volumen bajo la superficie.

## Por qué está dividido en varios archivos

Un servidor MCP de verdad lo va a construir un grupo de 6-7 personas. Si todo vive en un solo `server.py` , todos terminan editando el mismo archivo al mismo tiempo y se pisan los cambios. Por eso en el diseño de esta tool se ha separado el trabajo en un módulo por rol, y `server.py` queda como el único archivo que conecta todo (el "orquestador"):

# Roles
```text
- Sebastian ->   validacion.py             rol "Validación de entradas"
- Saúl ->        matematica.py             rol "Lógica matemática"
- Jan ->         matematica.py             rol "Lógica matemática"
- Cielo ->       visualizacion.py          rol "Visualización"
- Sachy ->       visualizacion.py          rol "Visualización"
- Melanie ->     server.py                 rol "orquestador" (define la tool MCP, llama a los demás módulos)
- Melanie ->     storage.py                rol "Storage/infra"
```

Cada módulo se puede leer, entender y modificar sin tener que entender los otros tres. matematica.py, por ejemplo, no importa nada de mcp ni hace ninguna llamada de red — es sympy y numpy puro, así que la persona responsable de ese rol lo puede probar con un test normal sin levantar el servidor.

## El flujo completo

1. El usuario llama a la tool bajo tres opciones: `integra_simple(expresion, x_min, x_max)` para integrales simples, `integra_doble_rectangular(expresion, x_min, x_max, y_min, y_max)` para integrales dobles sobre un dominio rectagular y `integra_doble_general(expresion, (y, g_1(x), g_2(x)), (x, x_min, y_max))` o `integra_doble_general(expresion, (x, h_1(y), h_2(y)), (y, y_min, y_max))` para integrales dobles sobre dominios no rectangualares (el escenario más complicado). En los tres casos, `expresion` es la función de una o dos variables a integrar y el dominio queda definido por `x_min`, `x_max` como los extremos del intervalo para el caso simple, `x_min`, `x_max`,`y_min` y `y_max` como los vértices del rectángulo para el caso de dominio rectangular. Para el caso de dominio general, se debe usar un dominio tipo x o dominio tipo y luego enviar las funciones y reales resultantes.

2. `validacion.py` revisa que `x_min < x_max`, `y_min < y_max` y que los ingresos sean numéricos. También convierte el texto de la expresión en un objeto `sympy`. Coteja asimismo que solo usen las variables `x` y `y`. Si algo estuviera mal ingresado, se corta la tool con un mensaje de error explicativo.

3. `matematica.py` integra `expresion` simbólicamente usando (`sp.integrate`) según la sintaxis `sp.integrate(expresion, (x, x_min, x_max))` o `sp.integrate(expresion, (x, x_min, x_max), (y, y_min, y_max))` o `sp.integrate(expresion, y, g_1(x), g_2(x)), (x, x_min, y_max))` o `sp.integrate(expresion, (x, h_1(y), h_2(y)), (y, y_min, y_max))`  habiendo definido `x, y = sp.symbols('x y')`. Se entiende que esta cargada la librería `sympy` como `sp`.

4. `visualizacion.py` grafica la función de una o dos variables definida por `expresion` en un archivo PNG (en memoria, nunca en disco — el contenedor no persiste nada entre llamadas). La interpretación geométrica en una variables es el área o volumne bajo la gráfica de `expresion` según se trate de una función de una o dos variables.

5. `storage.py` sube ese PNG a `SeaweedFS` y devuelve una URL pública.

6. `server.py` arma la respuesta final: un texto con el valor de la integral (normal y LaTeX) más el link de la imagen en markdown más la imagen también como `ImageContent` de MCP, por si el cliente no soporta imágenes en URL.

## Empaquetado y despliegue

* `Dockerfile`: imagen base `python:3.11-slim`, instala `requirements.txt` y corre `server.py`.
* `docker-compose.yml`: sigue las reglas obligatorias de todo el repo (ver `grupos/TEMPLATE/README.md`): `mem_limit`, `container_name: ${LAB_CONTAINER_NAME}` tal cual (sin reemplazar a mano), red externa `lab_net`.
* `server.py` corre con `transport="streamable-http"` (no `stdio` ni `sse`) para que Caddy lo pueda exponer con una URL pública.