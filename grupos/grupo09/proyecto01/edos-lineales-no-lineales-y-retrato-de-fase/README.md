# Agente de EDOs y sistemas dinámicos — Grupo 09

Servidor MCP local que resuelve y analiza ecuaciones diferenciales ordinarias
de 1 a 3 variables. Claude interpreta el pedido del usuario y llama a las
herramientas; el servidor calcula, **verifica** y devuelve resultados
estructurados; Claude redacta la explicación final a partir de ellos.

Hay una sola entrada, `mcp_server.py`, que acepta EDOs arbitrarias y devuelve
JSON más HTML interactivo. El proyecto nació como demo por terminal con tres
modelos fijos (`server.py`, `cli.py`, `modelos_referencia.py`, gráficas PNG);
todo eso se eliminó al convertirse en agente MCP, porque un menú de tres
modelos cableados no tiene sentido cuando el cliente puede mandar cualquier
sistema. Los ejemplos canónicos viven ahora en el balotario (25 problemas) y
en la documentación de la propia herramienta.

## Instalación

```bash
python -m pip install -r requirements.txt
```

## Registrar en Claude Code

Desde esta carpeta:

```bash
claude mcp add edos-grupo09 -- python mcp_server.py
```

Para que funcione desde cualquier directorio conviene usar rutas absolutas:

```bash
claude mcp add edos-grupo09 -- python /ruta/absoluta/a/mcp_server.py
```

Comprobar que quedó registrado y responde:

```bash
claude mcp list
```

Luego, dentro de Claude Code, basta pedir en lenguaje natural: *"resuelve
y' = y(1 - y/10) con y(0)=1 en [0,10] y dime la estabilidad de sus
equilibrios"*. Claude traducirá el pedido a una llamada de `analizar_edo`.

## Registrar en Claude Desktop (la app de escritorio)

Funciona sin cambiar nada del código: Claude Desktop usa servidores MCP locales
por stdio, que es exactamente lo que este servidor es. No hace falta HTTP ni
contenedor.

Edita (o crea) el archivo de configuración:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "edos-grupo09": {
      "command": "C:\\Users\\USUARIO\\AppData\\Local\\Programs\\Python\\Python311\\python.exe",
      "args": ["M:\\ruta\\al\\proyecto\\mcp_server.py"]
    }
  }
}
```

Luego reinicia Claude Desktop por completo (cerrarlo, no solo la ventana).

Tres detalles que hacen fallar el registro con más frecuencia:

1. **Rutas absolutas, siempre.** Desktop lanza el proceso con un directorio de
   trabajo propio, ajeno al proyecto. El servidor está preparado para eso —
   `catalogo.py` localiza el balotario con `Path(__file__)`, no con el cwd — y
   está probado arrancándolo desde `C:\Windows`.
2. **Ruta completa de `python.exe`, no `"python"`.** La app de escritorio no
   hereda el `PATH` de tu terminal, así que `"command": "python"` suele fallar
   aunque funcione en la consola.
3. **Barras invertidas dobles en el JSON.** `\\` en cada separador, o usa barras
   normales (`M:/ruta/...`), que Windows también acepta.

Si el servidor no aparece, los registros de Desktop muestran el error de
arranque; el servidor escribe sus mensajes a `stderr`, que es donde Desktop los
recoge.

## Probar con MCP Inspector

```bash
npx @modelcontextprotocol/inspector python mcp_server.py
```

El inspector abre una interfaz web donde se ven las herramientas, su esquema de
entrada y la respuesta cruda de cada llamada. Es la forma más rápida de
diagnosticar un problema de protocolo.

## Herramientas expuestas

| Herramienta | Qué hace | Cuándo |
| --- | --- | --- |
| `ping` | Conexión e inventario de capacidades y pendientes | Antes de un análisis largo |
| `analizar_edo` | validar → resolver → verificar → analizar → visualizar | Hay condición inicial y se quiere la trayectoria |
| `analizar_equilibrios` | Resuelve F(x)=0 exacto y clasifica, **sin integrar** | La pregunta es de equilibrios, estabilidad o bifurcación y no hay condición inicial |
| `listar_balotario` | Los problemas del balotario con su ecuación lista | Para usarlo como vara de nivel |

`analizar_equilibrios` existe porque "clasifique los equilibrios de x' = μ − x²"
no es un problema de valor inicial: no hay condición inicial que dar. Exigirla
obligaría a integrar una trayectoria que nadie pidió. Es la forma de los cinco
problemas del Tema 3, y es la pieza con la que se estudia una bifurcación
mientras el barrido automático siga pendiente: una llamada por valor del
parámetro. Su verificación es la que corresponde a esa pregunta: comprobar que
cada punto anule de verdad el campo, F(x*) = 0.

Recurso: `balotario://temas` entrega el catálogo completo en JSON.

### Cómo se escribe un sistema

`analizar_edo` espera la forma explícita de primer orden **x' = F(t, x)**: una
expresión por variable de estado. Una EDO de orden n se reduce antes a un
sistema de n ecuaciones.

```python
# Logístico: y' = r·y·(1 - y/K)
ecuaciones=["r*y*(1 - y/K)"], variables_estado=["y"], y0=[1.0],
intervalo=[0, 10], parametros={"r": 1.0, "K": 10.0}

# Péndulo no lineal: θ'' + ω₀²·sin θ = 0  →  θ' = v, v' = -ω₀²·sin θ
ecuaciones=["v", "-w0**2*sin(theta)"], variables_estado=["theta", "v"],
y0=[1.0472, 0.0], intervalo=[0, 20], parametros={"w0": 1.0}

# Separable escrito como dy/dx, con su solución exacta para contrastar
ecuaciones=["3*x*y**2"], variables_estado=["y"], y0=[1.0],
intervalo=[0, 0.7], variable_independiente="x",
solucion_exacta="2/(2 - 3*x**2)"
```

Se usa `**` para la potencia (nunca `^`). Funciones disponibles: `sin`, `cos`,
`tan`, `exp`, `log`/`ln`, `sqrt`, `sinh`, `cosh`, `tanh`, las inversas, `Abs`,
`sign`, `floor`, `ceiling`, y las constantes `pi` y `E`. Todo nombre que no sea
variable de estado ni función debe declararse en `parametros`.

## Qué sabe hacer y qué contesta cuando no sabe

El agente no finge. Cada operación que la propuesta pide está en una de tres
situaciones, y el servidor las distingue explícitamente:

| Operación | Estado | Qué pasa si se la piden |
| --- | --- | --- |
| Integración numérica | **implementada** | La resuelve |
| Estabilidad: equilibrios, Jacobiano, autovalores | **implementada** | La resuelve |
| Retratos de fase 1D / 2D / 3D | **implementada** | Los dibuja |
| Verificación (5 comprobaciones) | **implementada** | Siempre se ejecuta |
| Lyapunov, Poincaré, cuantificar el caos | pendiente | `analisis=['caos']` → `estado: pendiente_de_implementacion` con el detalle de qué falta |
| Barridos y diagramas de bifurcación | pendiente | `analisis=['bifurcaciones']` → idem |
| Resolución analítica (simbólica) | pendiente | `analisis=['solucion_analitica']` → idem |
| Mapas iterados `x_{n+1} = f(x_n)` | **fuera de alcance** | Declarado en `limites`; el motor integra EDOs continuas |

Pedir algo pendiente **no es un error**: la solicitud se acepta, los demás
análisis se ejecutan con normalidad y el bloque correspondiente informa que
está pendiente. Un análisis que no se reconoce de ninguna forma sí se rechaza,
y el mensaje enumera lo implementado y lo pendiente por separado.

Los nombres se resuelven por alias, para que pedirlo de forma natural llegue a
la capacidad correcta en un solo paso: `lyapunov`, `poincare` y `sensibilidad`
van a `caos`; `hopf`, `barrido` y `silla_nodo` a `bifurcaciones`; `simbolica` y
`analitica` a `solucion_analitica`; `equilibrios` y `autovalores` a
`estabilidad`. Tolera mayúsculas, guiones y espacios.

### Mapas discretos: el agente pregunta en vez de adivinar

`x_{n+1} = r·x_n(1−x_n)` y `ẋ = r·x(1−x)` se escriben con el mismo lado
derecho, así que el servidor **no puede** distinguirlos mirando las ecuaciones.
Y la diferencia no es cosmética: con r=3.8 el mapa es caótico, mientras que la
EDO continua converge monótonamente a un equilibrio. Integrar un mapa como si
fuera una EDO devuelve números válidos **para la ecuación equivocada**.

Quien sí lo sabe es el usuario. Por eso la distinción es un campo del contrato,
`tipo_de_sistema`, y no una suposición:

| Valor | Qué hace el servidor |
| --- | --- |
| `edo_continua` (por defecto) | Resuelve con normalidad |
| `mapa_discreto` | Rechaza con `etapa: fuera_de_alcance` y explica la diferencia de dinámica |
| `no_estoy_seguro` | Devuelve `etapa: aclaracion_necesaria` con la pregunta para el usuario y las dos opciones con sus consecuencias, **sin calcular nada** |

Además hay una heurística de notación: si la variable independiente es un
índice (`n`, `k`, `i`, `j`, `m`) o una variable de estado lleva sufijo de índice
(`x_n`, `theta_k`), el agente pide la aclaración aunque se haya declarado
continua — nadie escribe `dx/dn`. La heurística es deliberadamente estrecha
para no estorbar: `x1, x2` y `x, y` son nombres normales de componentes de un
sistema continuo y no disparan nada.

Los problemas 4.1 a 4.3 y 5.3 del balotario son mapas.

## La verificación es un portón, no un adorno

Toda respuesta trae un bloque `verificacion`. Si no se supera, el resultado
llega con `ok: false`, la `etapa` que falló y **sin conclusiones**: no hay
análisis que interpretar. Las etapas posibles son `validacion_solicitud`,
`compilacion`, `resolucion` y `verificacion`.

Las comprobaciones no confían en el integrador que produjo la solución:

| Comprobación | Contra qué contrasta |
| --- | --- |
| `condicion_inicial` | La condición inicial pedida. |
| `residuo` | El propio campo, sustituyendo la trayectoria en la EDO. |
| `convergencia` | Una reintegración con tolerancias 100 veces más finas. |
| `metodo_alternativo` | Una reintegración con otro integrador (DOP853 o Radau). |
| `solucion_exacta` | La solución analítica, cuando el cliente la aporta. |

**Sistemas caóticos.** Dos integraciones correctas de un sistema sensible
*tienen* que separarse a tiempo largo. Exigir coincidencia punto a punto en
todo el intervalo marcaría como inválido el atractor de Lorenz, que es uno de
los casos de demostración del proyecto. Por eso el veredicto se decide en el
tramo inicial, y cuando dos integraciones coinciden al principio y divergen
después se reporta `sensibilidad_detectada` junto al instante de separación:
es un hallazgo legítimo, no un fallo. A tiempo largo la comparación válida es
la estadística (medias y desviaciones), que también se reporta.

El residuo estima su propio error: la derivada por diferencias finitas tiene un
error de truncamiento O(h²)·x''' que no dice nada sobre la calidad del
integrador, así que la prueba lo descuenta antes de denunciar nada.

## Organización

```
mcp_server.py               Servidor MCP (stdio): ping, analizar_edo, listar_balotario
orquestacion/
  capacidades.py            Núcleo: el flujo completo y el registro de análisis
  contratos.py              SolicitudEDO, forma de la respuesta, conversión a JSON
  catalogo.py               Carga y valida balotario/tema_*.json
matematica/
  expresiones.py            Compila texto a funciones con sympy (frontera de seguridad)
  datos_validacion.py       Valida modelo, y0, intervalo y parámetros
  modelo_edos.py            Integración con solve_ivp
  analisis_estabilidad.py   Jacobiano numérico, autovalores y clasificación
  validacion_solucion.py    El portón de verificación
  analisis_caos.py          STUB: no implementado
  analisis_bifurcaciones.py STUB: no implementado
visualizacion/
  html.py                   Figuras interactivas con plotly
balotario/
  balotario.tex             Problemario original del grupo (25 problemas, 5 temas)
  tema_01.json .. tema_05.json   Los 25 problemas convertidos
tests/                      116 pruebas
```

Un `analizar_edo` recorre: `contratos` valida la solicitud → `expresiones`
compila el campo → `modelo_edos` integra → `validacion_solucion` verifica →
`analisis_estabilidad` analiza → `html` dibuja. `capacidades` es quien ordena
ese recorrido y el único módulo que los conoce a todos.

El HTML viaja inline por el transporte, nunca a disco: una ruta local no le
sirve a un cliente que puede estar en otra máquina. Su peso queda acotado
dibujando como máximo 2000 puntos por traza, con independencia de cuántos
tenga la malla; si aun así no cupiera, se baja la resolución antes de
rendirse.

### Seguridad de la frontera

`matematica/expresiones.py` recibe texto de un cliente MCP arbitrario. **No usa
`eval`.** Valida en tres capas: léxica (lista blanca de caracteres, `__`
prohibido), de nombres (todo identificador debe ser un símbolo declarado o una
función permitida) y simbólica (tras parsear con sympy se comprueba que no
quedaron símbolos libres ni funciones ajenas).

## Pruebas

```bash
python -m unittest discover -s tests -v
```

| Archivo | Cubre |
| --- | --- |
| `test_expresiones.py` | Compilación válida y rechazo de entrada hostil. |
| `test_balotario.py` | Cada problema del Tema 1 contra su solución esperada. |
| `test_capacidades.py` | El flujo completo, el portón y la serialización JSON. |
| `test_mcp_server.py` | Registro de herramientas y limpieza de stdout. |
| `test_catalogo.py` | Consistencia del catálogo contra el `.tex`. |

El balotario funciona como vara de medir: `test_balotario.py` pasa cada
ejercicio por el solver y lo compara con la solución que el `.tex` demuestra.
Los problemas marcados con `ci_derivada: true` tienen una condición inicial
que no está en el enunciado original: el `.tex` da la solución general, y para
concretar un PVI hubo que fijar las constantes. Cada caso explica en `notas`
de dónde sale.

### Qué cubre el balotario convertido

Los 25 problemas de los 5 temas están en `balotario/tema_0N.json`. No todos son
problemas de valor inicial, así que cada uno declara `verificable_con_solver`:

| Tema | Problemas | Verificables hoy | Tipo de objeto |
| --- | --- | --- | --- |
| 1. EDOs lineales y no lineales | 5 | 5 | PVI de 1ª y 2ª orden |
| 2. Retratos de fase | 5 | 5 | Sistemas autónomos 2D |
| 3. Bifurcaciones | 5 | 5 | Familias paramétricas |
| 4. Sistemas caóticos | 5 | 0 | Mapas discretos y demostraciones |
| 5. Atractores extraños | 5 | 0 | Fractales, mapas 2D, Poincaré |

**10 de 25 se verifican con el motor actual.** Los 15 restantes no por dos
razones distintas, que conviene no confundir:

- **9 problemas no tienen solución en el `.tex`** (4.2 a 4.5 y 5.1 a 5.5): solo
  enunciado. Se registran con `solucion_esperada.tipo: "pendiente"` y
  `solucion_en_tex: false`. No se inventaron respuestas; lo que aparece en
  `datos_del_enunciado` son las cifras que el propio enunciado aporta.
- **Los temas 4 y 5 son mayormente mapas discretos** (tienda, logístico, Hénon)
  y demostraciones analíticas. El motor integra EDOs continuas con `solve_ivp` y
  no itera mapas: cada problema dice por qué en `motivo_no_verificable`.

Según el tipo de respuesta, el test verifica de forma distinta:

| `solucion_esperada.tipo` | Cómo se comprueba |
| --- | --- |
| `analitica_explicita` | Comparación punto a punto con la solución cerrada. |
| `invariantes` | Conservación de energía/hamiltoniano a lo largo del flujo. |
| `clasificacion_equilibrios` | Equilibrios exactos con sympy + autovalores. |
| `bifurcacion` | Un caso por régimen del parámetro, con sus equilibrios. |
| `ciclo_limite` | Convergencia asintótica del radio, desde dentro y desde fuera. |
| `analitico_discreto` | Consistencia interna de los valores registrados. |
| `pendiente` | Solo que esté declarado como tal, con su motivo. |

El Tema 3 es, de hecho, la especificación de
`matematica/analisis_bifurcaciones.py`: cuando se implemente, esos casos ya son
su suite de aceptación.

## Estado y pendientes

Implementado: compilación de EDOs arbitrarias, integración, el portón de
verificación completo, equilibrios exactos con sympy, Jacobiano, autovalores y
clasificación, visualización HTML 1D/2D/3D, y el servidor MCP sobre stdio.

Pendiente:

- `matematica/analisis_caos.py`: sensibilidad, máximo exponente de Lyapunov con
  renormalización y secciones de Poincaré. Hoy es un stub que informa que no
  está implementado en lugar de devolver números. Punto de partida disponible:
  la verificación ya detecta y fecha la sensibilidad a condiciones iniciales.
- `matematica/analisis_bifurcaciones.py`: barridos paramétricos, ramas de
  equilibrio y detección de silla-nodo, horquilla y Hopf. Mismo criterio de
  stub. Punto de partida: `capacidades.buscar_equilibrios` ya resuelve F=0 de
  forma exacta para unos parámetros dados.
- Iteración de mapas discretos, que desbloquearía el Tema 4 completo y el 5.3.
  Es un motor distinto del integrador de EDOs, no una adaptación.
- Los 9 problemas del balotario sin solución en el `.tex` (4.2 a 4.5, 5.1 a
  5.5) siguen pendientes de resolver por el equipo.
- Empaquetado: el `Dockerfile` que figura en la propuesta se eliminó porque
  estaba vacío (0 bytes) y el alcance actual es solo transporte stdio. Cuando
  haga falta HTTP o contenedor, se escribe desde cero.

### Si alguna vez hay que exponerlo por red

Hoy el alcance es stdio, que cubre Claude Code y Claude Desktop porque ambos
lanzan el servidor como proceso local. El SDK acepta otros transportes —
`servidor.run(transport="streamable-http")`— así que el cambio de transporte es
una línea, pero **no basta con eso**. Faltaría:

- **Autenticación.** El servidor no tiene ninguna: `MCPServer` soporta
  `auth_server_provider`, `token_verifier` y `auth`, y hoy no se usan.
- **Un tope de tiempo por llamada.** No existe. Las cotas actuales (dimensión
  ≤ 3, puntos ≤ 200 000) mantienen el peor caso medido en ~9 s para un sistema
  rígido, que en local es irrelevante pero expuesto es un vector de agotamiento.
- **Herramientas asíncronas.** Son síncronas: una integración larga bloquea el
  bucle de eventos, de modo que un cliente puede dejar sin servicio a los demás.
- **HTTPS y un host alcanzable**, si el destino es un conector remoto.

### Sobre borrar `balotario.tex`

El `.tex` sigue en el proyecto a propósito. Los JSON conservan los enunciados,
los resultados finales y las fórmulas clave, pero **no las demostraciones paso
a paso**: el `.tex` tiene unas 2 800 líneas de desarrollo algebraico que el
catálogo no reproduce. Además, `test_catalogo.py` comprueba contra él que
ningún ejercicio sea inventado; si falta, ese test se salta con un mensaje
explícito en vez de fallar, y la procedencia (`tema.origen`) queda registrada en
cada JSON pero ya no se puede verificar contra nada.
