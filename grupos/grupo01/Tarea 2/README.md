# [nombre_de_tu_proyecto] — cómo está armado este proyecto

Este proyecto es la entrega del grupo **[tu_grupo]** que muestra cómo se ve un servidor MCP propio.

La tool que expone hace una sola cosa: recibe [parámetros_de_entrada] y devuelve [resultado_esperado].

## Por qué está dividido en varios archivos

Un servidor MCP de verdad lo construye un grupo de trabajo. Si todo vive en un solo `server.py`, todos terminan editando el mismo archivo al mismo tiempo y se pisan los cambios. Por eso se separa el trabajo en un módulo por rol, y `server.py` queda como el único archivo que conecta todo (el "orquestador"):

```text
server.py        orquestador: define la tool MCP, llama a los demás módulos
validacion.py    rol "Validación de entradas"
matematica.py    rol "Lógica principal / procesamiento"
visualizacion.py rol "Visualización / reportes"
storage.py       rol "Storage/infra"
