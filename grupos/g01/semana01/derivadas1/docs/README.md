# derivadas1 — cómo está armado este piloto

Este proyecto **no es la tarea de un grupo**: es el piloto del profesor
(`g01`, no `grupoNN`) que muestra cómo se ve un servidor MCP propio antes de
que cada grupo real construya el suyo con su tema asignado. Léanlo como un
ejemplo a imitar, no como algo que van a entregar tal cual.

La tool que expone hace una sola cosa: recibe una función `f(x)` de una
variable, la deriva de forma simbólica exacta (con sympy, no aproximada) y
devuelve la derivada más un gráfico de `f(x)` y `f'(x)` superpuestas.

## Por qué está dividido en varios archivos

Un servidor MCP de verdad lo va a construir un grupo de 6-7 personas. Si todo
vive en un solo `server.py`, todos terminan editando el mismo archivo al
mismo tiempo y se pisan los cambios. Por eso este piloto separa el trabajo en
**un módulo por rol**, y `server.py` queda como el único archivo que conecta
todo (el "orquestador"):

```
server.py         orquestador: define la tool MCP, llama a los demás módulos
validacion.py     rol "Validación de entradas"
matematica.py     rol "Lógica matemática"
visualizacion.py  rol "Visualización"
storage.py        rol "Storage/infra"
```

Cada módulo se puede leer, entender y modificar sin tener que entender los
otros tres. `matematica.py`, por ejemplo, no importa nada de `mcp` ni hace
ninguna llamada de red — es sympy y numpy puro, así que la persona a cargo de
ese rol lo puede probar con un test normal sin levantar el servidor.

## El flujo completo, en orden

1. El usuario llama a la tool `derivar(expresion, x_min, x_max)`.
2. `validacion.py` revisa que `x_min < x_max` y convierte el texto de la
   expresión en un objeto sympy, chequeando que solo use la variable `x`. Si
   algo está mal, corta acá con un mensaje de error legible.
3. `matematica.py` deriva `f` simbólicamente (`sp.diff`) y evalúa `f` y `f'`
   en un arreglo de puntos del rango pedido (`sp.lambdify` + numpy).
4. `visualizacion.py` grafica ambas curvas en un PNG (en memoria, nunca en
   disco — el contenedor no persiste nada entre llamadas).
5. `storage.py` sube ese PNG a SeaweedFS y devuelve una URL pública.
6. `server.py` arma la respuesta final: texto con la derivada (normal y
   LaTeX) + el link de la imagen en markdown + la imagen también como
   `ImageContent` de MCP, por si el cliente no soporta imágenes en URL.

## Dos detalles no obvios que vale la pena explicar en clase

- **El docstring de la tool (`derivar` en `server.py`) es metadata de
  confianza**: es lo que la IA lee para saber en qué sintaxis mandar la
  expresión. Por eso es tan explícito ("usa `x**2`, no `x^2`").
- **El resultado de la tool NO es metadata de confianza**: es dato. Por eso
  el link de la imagen se agrega como un dato más de la respuesta, sin
  ninguna instrucción tipo "debes mostrar esto" — meter un imperativo ahí
  tendría la forma de un prompt injection. La instrucción de cómo tratar ese
  link vive en el docstring, no en el resultado.

## Empaquetado y despliegue

- `Dockerfile`: imagen base `python:3.11-slim`, instala `requirements.txt` y
  corre `server.py`.
- `docker-compose.yml`: sigue las reglas obligatorias de todo el repo (ver
  `grupos/TEMPLATE/README.md`): `mem_limit`, `container_name:
  ${LAB_CONTAINER_NAME}` tal cual (sin reemplazar a mano), red externa
  `lab_net`.
- `server.py` corre con `transport="streamable-http"` (no `stdio` ni `sse`)
  para que Caddy lo pueda exponer con una URL pública.

Las tareas concretas para practicar sobre este código están en
[`tareas.md`](./tareas.md).
