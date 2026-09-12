# Tema: Integración simple y doble

# Contenido
La tool recibe una función `f` de una o dos variables, sobre un intervalo o dominio rectangular y la integra de forma simbólica exacta (con `sympy`, no aproximada). Devuelve la integral (un número real) y la gráfica asociada.

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

1. El usuario llama a la tool `integra_simple(expresion, x_min, x_max)` o `integra_doble(expresion, x_min, x_max, y_min, y_max)` o . Nótese que se solicitan parámetros en función de si se trata una integral simple o doble: `expresion` es la función de una o dos variables a integrar y el dominio queda definido por `x_min`, `x_max`, `y_min` y `y_max`.

2. `validacion.py` revisa que `x_min < x_max`, `y_min < y_max` y que los ingresos sean numéricos. También convierte el texto de la expresión en un objeto `sympy`. Coteja asimismo que solo usen las variables `x` y `y`. Si algo estuviera mal ingresado, se corta la tool con un mensaje de error explicativo.

3. `matematica.py` integra `expresion` simbólicamente usando (`sp.integrate`) según la sintaxis `sp.integrate(expresion, (x, x_min, x_max))` o `sp.integrate(expresion, (x, x_min, x_max), (y, y_min, y_max))` habiendo definido `x, y = sp.symbols('x y')`. Se entiende que esta cargada la librería `sympy` como `sp`.

4. `visualizacion.py` grafica la función de una o dos variables definida por `expresion` en un archivo PNG (en memoria, nunca en disco — el contenedor no persiste nada entre llamadas).

5. `storage.py` sube ese PNG a `SeaweedFS` y devuelve una URL pública.

6. `server.py` arma la respuesta final: un texto con el valor de la integral (normal y LaTeX) más el link de la imagen en markdown más la imagen también como `ImageContent` de MCP, por si el cliente no soporta imágenes en URL.

## Empaquetado y despliegue

* `Dockerfile`: imagen base `python:3.11-slim`, instala `requirements.txt` y corre `server.py`.
* `docker-compose.yml`: sigue las reglas obligatorias de todo el repo (ver `grupos/TEMPLATE/README.md`): `mem_limit`, `container_name: ${LAB_CONTAINER_NAME}` tal cual (sin reemplazar a mano), red externa `lab_net`.
* `server.py` corre con `transport="streamable-http"` (no `stdio` ni `sse`) para que Caddy lo pueda exponer con una URL pública.
