# MCP de transformaciones lineales y cifrado Hill - Grupo 05

Servidor educativo para construir matrices respecto de bases, analizar invertibilidad, explicar Gauss-Jordan, reconstruir la inversa y verificar ambas composiciones. Incluye cifrado y descifrado de mensajes mediante matrices.

**Contenido:** Álgebra lineal. **Curso de entrega:** Redes, Arquitectura y Comunicaciones - Práctica, UNMSM.

## Inicio rápido en Windows

Abre PowerShell en esta carpeta. Necesitas Python 3.12 o superior.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

La CLI incluye una demostración opcional con `python cli.py demo`. Genera reportes locales con el ejemplo del PDF, las operaciones de Gauss-Jordan, la comprobación, una gráfica y el recorrido `HOLA -> LGHW -> HOLA`. Esos archivos generados deben mantenerse fuera de la entrega; para usarlos en el clon, agregar su carpeta al único `.gitignore` global antes de generarlos.

Inicia el servidor:

```powershell
.\.venv\Scripts\python.exe server.py
```

Endpoint: **http://127.0.0.1:8000/mcp**, transporte **Streamable HTTP**. Se usa con un cliente MCP; no es una página web.

Con MCP Inspector (opcional, requiere Node.js 22.19 o superior): ejecuta `npx @modelcontextprotocol/inspector`, selecciona Streamable HTTP y esa URL. `ejemplos.json` contiene llamadas completas; copia los argumentos de cada herramienta. Referencia: [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector).

Para clientes que lancen un proceso local también se admite:

```powershell
.\.venv\Scripts\python.exe server.py --transport stdio
```

## Herramientas

| Herramienta | Resultado |
|---|---|
| `calcular_inversa_tl` | Solución completa de Rn→Rn en Markdown y LaTeX con una sola llamada |
| `analizar_transformacion` | Espacios, dimensiones, bases, imágenes, matriz, rango e invertibilidad |
| `construir_matriz_asociada` | Construcción de A = C⁻¹ M B, columna por columna |
| `verificar_invertibilidad` | Determinante, rango y conclusión |
| `hallar_inversa` | Inversa, reconstrucción, Gauss-Jordan y verificación |
| `mostrar_gauss_jordan` | Operaciones y estados de la matriz aumentada |
| `verificar_inversa` | Verificación de una candidata con ambos productos |
| `visualizar_transformacion` | PNG para R²/R³, con base y vector elegido |
| `analizar_clave_hill` | Condición modular e inversa de la clave |
| `cifrar_hill` | Cifrado, relleno y operaciones por bloque |
| `descifrar_hill` | Recuperación con la inversa modular |

Las herramientas numéricas devuelven JSON estructurado y texto JSON. Las fracciones se devuelven como cadenas (`"1/3"`). `calcular_inversa_tl` devuelve una solución completa en Markdown y LaTeX, adaptando la presentación del proyecto paralelo del grupo. Todas comparten el mismo motor matemático y la misma validación. Una entrada inválida produce un error MCP. Los gráficos son imágenes nativas. En el laboratorio, si llegan `LAB_IMG_BUCKET` y `LAB_PUBLIC_IMG_URL`, también se publican en SeaweedFS y se devuelve un enlace Markdown. Sin esas variables o si el almacenamiento falla, se conserva la imagen nativa.

Recurso adicional: `algebra://guia`. Prompt: `tutor_algebra`.

### Resolver en una sola llamada

La herramienta integrada conserva el nombre y la entrada del proyecto paralelo:

```json
{"n":2,"regla":["3x1+2x2","x1+x2"]}
```

`calcular_inversa_tl` presenta la base canónica, sus imágenes, la matriz estándar, determinante, rango, cada estado de Gauss-Jordan, la regla inversa y las dos composiciones. En el ejemplo, T⁻¹(y1,y2)=(y1−2y2,−y1+3y2). Si la matriz es singular, explica por qué no existe la inversa. Para polinomios, matrices o bases personalizadas, usar `hallar_inversa`.

En Claude, activar el conector y pedir: «Usa calcular_inversa_tl con n=2 y regla=[\"3x1+2x2\",\"x1+x2\"]. Explica los pasos y verifica ambas composiciones». La llamada a la herramienta permite comprobar que se ejecutó el MCP.

## Entradas y coordenadas

- Espacios: `R2` o `R^2`; `P2` significa grado menor o igual a 2, dimensión 3; `M2x3` tiene dimensión 6.
- Proporciona exactamente una entrada: `regla` o `matriz`. La matriz M siempre representa T en las **bases canónicas**, incluso cuando se indican otras bases.
- En las herramientas generales, `regla` es texto JSON de expresiones con x1,x2,...: `["2*x1+x2", "x1-x2"]`. En `calcular_inversa_tl` es una lista de expresiones. Se admite `*` y notación como `2x1`, `2(x1+x2)` o `(1/2)x1`. La división solo acepta constantes racionales no nulas; normalizar la escritura no permite reglas no lineales.
- Las variables de una regla representan coordenadas canónicas. En P2: coeficientes de `1,t,t²`. En M2x3: entradas por filas `(a11,a12,a13,a21,a22,a23)`.
- `matriz` es texto JSON: `[[2,1],[1,-1]]`. Para fracciones: `[["1/2",0],[0,1]]`.
- Las bases opcionales son matrices cuyos **vectores base son columnas**, en coordenadas canónicas. Se valida su independencia.
- A = C⁻¹ M B; la matriz canónica de la inversa es B A⁻¹ C⁻¹.
- Al reconstruir T⁻¹, `y1,y2,...` son coordenadas canónicas del dato de entrada. El resultado es vector, polinomio en t o matriz del dominio original.

Ejemplo para `hallar_inversa`:

```json
{"dominio":"R2","codominio":"R2","regla":"[\"2*x1+x2\",\"x1-x2\"]"}
```

Se obtiene det(A)=-3 y A⁻¹=`[[1/3,1/3],[1/3,-2/3]]`.

Para T:P2→R3, T(p)=(p(0),p(1),p(2)), usa `dominio=P2`, `codominio=R3` y `matriz=[[1,0,0],[1,1,1],[1,2,4]]`.

## Encriptación con matrices

Hill transforma bloques columna: `c = Kp mod m`, con m igual a la longitud del alfabeto. Alfabeto por defecto: `ABCDEFGHIJKLMNOPQRSTUVWXYZ`, A=0,...,Z=25.

```json
{"texto":"HOLA","clave":"[[3,3],[2,5]]"}
```

`cifrar_hill` devuelve `LGHW`; `descifrar_hill` con la misma clave recupera `HOLA`.

Se necesita **mcd(det(K),m)=1**. Una matriz de determinante no nulo sobre los reales puede carecer de inversa modular. Se calcula `K⁻¹ = det(K)⁻¹ adj(K) mod m` y se verifica el producto.

Si se agrega relleno para completar un bloque, se guarda `cantidad_relleno`. Pasa ese valor al descifrar para retirar únicamente las letras agregadas y conservar cualquier X original.

No se eliminan espacios, no se cambian minúsculas ni se quitan tildes silenciosamente. Para Ñ o espacios, define un alfabeto que los incluya y úsalo también al descifrar. Los símbolos deben ser únicos.

Hill es un cifrado histórico didáctico, vulnerable a texto conocido; no protege información real.

## Alcance

- Espacios reales con **coeficientes racionales** exactos: enteros, fracciones y decimales finitos. No se admiten coeficientes simbólicos, complejos ni funciones (`sin`, `sqrt`, `pi`).
- Dimensión total de cada espacio: 1 a 8. Se analizan matrices rectangulares para explicar la ausencia de una inversa global.
- Hill: claves enteras 2x2, 3x3 o 4x4; alfabetos de 2 a 100 símbolos; mensajes originales de hasta 512 caracteres. Al descifrar se admite el crecimiento por relleno, hasta 515 caracteres cifrados.
- Gráficos para R2→R2 y R3→R3, con entradas de magnitud máxima 1000. Otros espacios se muestran mediante coordenadas, matrices y expresiones.
- La validación usa un árbol sintáctico de aritmética permitida, sin ejecutar código del usuario. La regla debe ser lineal, con T(0)=0.

## Módulos

| Archivo | Responsabilidad |
|---|---|
| `validacion.py` | Espacios, reglas, números, vectores y matrices |
| `bases.py` | Bases, coordenadas y objetos |
| `matematica.py` | Matriz asociada, rango, determinante e inversión |
| `presentacion.py` | Solución completa en Markdown y LaTeX de la herramienta integrada |
| `criptografia.py` | Hill e inversa modular |
| `visualizacion.py` | PNG 2D/3D en memoria |
| `server.py` | Herramientas, recurso, prompt y transporte MCP |
| `storage.py` | Publicación opcional de gráficos en SeaweedFS del laboratorio |
| `cli.py`, `reporte_html.py` | Demostración local y reporte |

La separación modular y Docker toman como referencia el grupo 01. Gauss-Jordan adapta el notebook `InversaTL.ipynb.txt`. Consulta la [propuesta](inversa_tl_mcp.md).

## Pruebas

La versión integrada aprobó 66 pruebas en Windows y 66 en Docker Linux en la copia de desarrollo. Incluyen ejemplos del PDF/notebook, bases no canónicas, interpolación, R6↔M2x3, casos singulares/rectangulares, intercambio de filas, claves modulares, relleno, Ñ, sesiones MCP y almacenamiento de gráficos.

Las pruebas y el cliente de demostración se conservan en la copia de desarrollo y en un ZIP local separado; esta entrega no incluye su carpeta. Según la indicación del profesor, las pruebas locales deben reunirse en `test/` dentro del proyecto y excluirse mediante el único `.gitignore` global. La opción de pytest `-p no:cacheprovider` evita generar otro `.gitignore` dentro de su cache.

Para comprobar esta entrega, usar MCP Inspector con el endpoint del servidor y los casos de `ejemplos.json`.

## Docker y laboratorio

Compose incluye `mem_limit: 512m`, red externa `lab_net` y `container_name: ${LAB_CONTAINER_NAME}` literalmente. El despliegue proporciona el nombre del contenedor y las variables del almacenamiento. Identificador de carpeta: `grupo05_proyecto01_inversa_tl_mcp`.

Validar sin desplegar:

```powershell
$env:LAB_CONTAINER_NAME = 'lab-grupo05_proyecto01_inversa_tl_mcp'
docker compose config --quiet
```

En local, las variables de almacenamiento pueden quedar vacías; Compose avisará que usa cadenas vacías. No se necesita levantar SeaweedFS para resolver ejercicios ni recibir las imágenes nativas.

Prueba local, con Docker Desktop y motor Linux activos:

```powershell
docker build -t grupo05-algebra .
docker run --rm -p 127.0.0.1:8000:8000 grupo05-algebra
```

El profesor despliega en el laboratorio. El contrato de la copia actual `laboratory-cc-main` genera las rutas MCP y de imágenes a partir de la carpeta. La ruta prevista, aún sin verificar ni publicar para el grupo 05, es `https://rac-unmsm.vekthos.org/grupo05/grupo05_proyecto01_inversa_tl_mcp/mcp`. El nombre `lab-grupo05_proyecto01_inversa_tl_mcp` tiene 37 caracteres y cumple el máximo de 63 exigido por el validador actualizado.

Para revisar desde la raíz de un clon Git del repositorio, usar los comandos del profesor:

```powershell
git fetch origin
git merge origin/main
python .claude/skills/mcp-validator/scripts/validar_entrega.py grupo05
```

Una descarga ZIP no contiene historial Git. En ese caso se revisa el contenido y se puede simular la entrega contra la instantánea descargada, pero no se certifica el estado de una rama remota.

La entrega incluye únicamente archivos dentro de `grupos/grupo05/`. Las pruebas locales se conservan fuera de esta copia y se utiliza el `.gitignore` global del repositorio, siguiendo la indicación del profesor.

La ubicación sigue `proyecto01/README.md`; el validador y el workflow actuales encuentran Compose en esta profundidad. Si el profesor solicita `semanaNN`, usar la semana que indique y mover el proyecto sin duplicar Compose.

Documentación del SDK: [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/), [ejecución](https://py.sdk.modelcontextprotocol.io/run/) e [imágenes](https://py.sdk.modelcontextprotocol.io/servers/media/).
