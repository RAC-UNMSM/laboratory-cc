# Agente de EDOs y sistemas dinámicos — Grupo 09

Servidor MCP local que resuelve problemas de ecuaciones diferenciales
ordinarias (1 a 3 variables) y de mapas unidimensionales **con el desarrollo
matemático del balotario del grupo**. Claude interpreta el pedido del usuario y
llama a las herramientas; el servidor clasifica el problema, elige el método
que le corresponde, lo **ejecuta** con cálculo simbólico (sympy) y numérico
(scipy), lo **verifica** y lo dibuja; Claude presenta ese desarrollo sin
agregarle operaciones que el servidor no hizo.

El recorrido de cada pregunta es:

```
PROBLEMA → INTERPRETACIÓN → CLASIFICACIÓN → SELECCIÓN DEL MÉTODO → DESARROLLO
→ CÁLCULO SIMBÓLICO / NUMÉRICO → ANÁLISIS → VALIDACIÓN → VISUALIZACIÓN → PRESENTACIÓN
```

El balotario (`balotario/balotario.tex`, 25 problemas en 5 temas) es la
especificación: define qué familias se resuelven, con qué procedimiento, y sus
ejercicios son la suite de aceptación. Lo que el balotario todavía no resuelve
queda **FUERA DE ALCANCE POR AHORA** y el agente lo dice en vez de improvisar.

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

Luego, dentro de Claude Code, basta pedir en lenguaje natural: *"resuelve la
ecuación de Bernoulli y' + y = y³ con y(0) = 1"* o *"clasifica el equilibrio
del oscilador ẍ + γẋ + 4x = 0 según γ ≥ 0"*. Claude traducirá el pedido a una
llamada de `resolver_graficar_y_analizar_edo` o de `analizar_equilibrios`.

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
| `ping` | Conexión, revisión del código e inventario de familias y de lo fuera de alcance | Antes de un análisis largo |
| `nuevo_informe` / `informe` | Abre un informe vacío / devuelve su enlace | Al empezar un chat / cuando el usuario lo pida |
| `resolver_graficar_y_analizar_edo` | El recorrido completo: desarrollo, trayectoria si hay condición inicial, verificación y figuras | Resolver, hallar la solución general, graficar o analizar |
| `analizar_equilibrios` | Equilibrios, estabilidad o una bifurcación, con su desarrollo, **sin integrar** | La pregunta es de equilibrios o de un parámetro y no hay condición inicial |
| `listar_balotario` | Los problemas del balotario con su ecuación lista y su alcance | Para usarlo como vara de nivel |

El nombre largo de `resolver_graficar_y_analizar_edo` es a propósito. En Claude
Desktop las herramientas del conector llegan diferidas: el modelo elige mirando
solo el nombre y lee la descripción después. Con el nombre anterior,
`analizar_edo`, un enunciado que dice "Resuelve… Grafica…" se resolvía con
Python en vez de con el agente.

**La condición inicial es opcional.** "Halle la solución general de
x²y'' − 2xy' + 2y = x³ ln x" no la tiene, y exigirla obligaba a inventar un
PVI. Sin condición inicial el servidor hace el desarrollo y no integra nada;
con ella, además integra la trayectoria y la contrasta con la solución
analítica.

`analizar_equilibrios` existe porque "clasifique los equilibrios de x' = μ − x²"
no es un problema de valor inicial. Con el parámetro declarado en `parametro`,
**una sola llamada** estudia la bifurcación entera: ramas de equilibrio, su
estabilidad por tramos, los valores críticos y el tipo de bifurcación. Con el
parámetro fijado en `parametros`, clasifica los equilibrios de ese régimen
(línea de fase en 1D, linealización en 2D).

### Cómo se escribe un problema

Las ecuaciones van en forma explícita de primer orden **x' = F(t, x)**: una
expresión por variable de estado. Una EDO de orden n se reduce antes a un
sistema de n ecuaciones; el servidor reconoce esa forma (y' = yp, yp' = …) y la
trata como la EDO de orden n que es.

```python
# 1.1 — separable con intervalo maximal
ecuaciones=["3*x*y**2"], variables_estado=["y"], variable_independiente="x",
y0=[1], intervalo=[0, 0.7],
enunciado="Resuelva dy/dx = 3xy^2, y(0) = 1 y determine el intervalo máximo de existencia"

# 1.3 — Cauchy-Euler, solución general (sin condición inicial)
ecuaciones=["yp", "(2*x*yp - 2*y + x**3*log(x))/x**2"], variables_estado=["y", "yp"],
variable_independiente="x"

# 1.5 — péndulo con ω₀ simbólico
ecuaciones=["thetapunto", "-w0**2*sin(theta)"], variables_estado=["theta", "thetapunto"],
parametro="w0", rango_parametro=[0, None], parametros={"w0": 1.0},
y0=[1.0472, 0.0], intervalo=[0, 20]

# 2.2 — clasificación según un parámetro (analizar_equilibrios)
ecuaciones=["y", "-4*x - gamma*y"], variables_estado=["x", "y"],
parametro="gamma", rango_parametro=[0, None]

# 4.1 — mapa tienda (mapa definido a trozos)
ecuaciones=["x"], variables_estado=["x"], tipo_de_sistema="mapa_discreto",
trozos=[{"expresion": "2*x", "desde": 0, "hasta": 0.5},
        {"expresion": "2*(1 - x)", "desde": 0.5, "hasta": 1}],
separacion_inicial=1e-10
```

Campos que deciden el desarrollo, todos opcionales:

| Campo | Para qué |
| --- | --- |
| `enunciado` | De él se leen el método que nombra ("Bernoulli", "Hopf"…) y lo que pide ("intervalo máximo", "trayectorias", "separatriz", "periodo"…), que decide qué secciones tiene el desarrollo |
| `metodo_analitico` | El método pedido. Si la ecuación no tiene esa forma, se dice y se aplica el que corresponde |
| `pedidos` | Lo que pide el enunciado, explícito (`intervalo_maximo`, `separatriz`, `ciclo_limite`…) |
| `parametro`, `rango_parametro` | Parámetro que queda simbólico (γ, μ, ω₀) y su dominio |
| `region` | Cotas de las variables (el cuadrante biológico del 2.3) |
| `solucion_particular` | La y₁ conocida de una Riccati (si falta, se busca una polinómica) |
| `trozos`, `separacion_inicial` | Mapa a trozos y δ₀ del horizonte de predictibilidad |

Se usa `**` para la potencia (nunca `^`). Funciones disponibles: `sin`, `cos`,
`tan`, `exp`, `log`/`ln`, `sqrt`, `sinh`, `cosh`, `tanh`, las inversas, `Abs`,
`sign`, `Min`, `Max`, `floor`, `ceiling`, y las constantes `pi` y `E`. Todo
nombre que no sea variable de estado ni función debe declararse en
`parametros` o en `parametro`.

## Qué resuelve: las familias del balotario

Cada familia se reconoce por su forma (`identificar_*`) y ejecuta el
procedimiento del balotario (`desarrollar_*`), generalizado: el mismo método
funciona con otros coeficientes, parámetros y condiciones iniciales. No hay
soluciones particulares del balotario escritas en el código.

| Tema | Familia | Problemas | Procedimiento que se calcula |
| --- | --- | --- | --- |
| 1 | Separable | 1.1 | g(x)h(y), primitivas, despeje, constante, intervalo maximal por dominio de continuidad y límites |
| 1 | Lineal de 1.er orden | 1.2 (pasos 5–6) | Forma estándar, μ = e^{∫P}, (μy)' = μQ |
| 1 | Bernoulli | 1.2 | v = y^{1−n}, división entre yⁿ, ecuación lineal en v, regreso con ramas ± |
| 1 | Riccati | 1.4 | Verificación de y₁, y = y₁ + 1/u, ecuación lineal en u |
| 1 | Cauchy-Euler | 1.3 | Ecuación indicial, sistema fundamental, wronskiano, variación de parámetros |
| 1–2 | Conservativo / hamiltoniano | 1.5, 2.4 | Integral primera, equilibrios por energía, separatriz, lazo homoclínico, periodo con K(k) |
| 2 | Sistema lineal plano | 2.1, 2.2 | Autovalores, autovectores, τ/Δ/D, solución general, trayectorias, variedades; regímenes según un parámetro y plano traza-determinante |
| 2 | No lineal plano | 2.3 | Equilibrios por casos de factores, jacobiano, clasificación, nulclinas, variedades de las sillas y cuencas |
| 2 | Ciclo límite | 2.5 | Forma polar, región anular, hipótesis de Poincaré–Bendixson comprobadas una por una |
| 3 | Bifurcación en 1D | 3.1–3.3 | Ramas x*(μ), estabilidad por tramos, condiciones de Sotomayor, biestabilidad e histéresis |
| 3 | Línea de fase | 3.1–3.3 | Los equilibrios de un régimen con el parámetro fijado: f(x*) = 0, f'(x*) y signo de f |
| 3 | Hopf | 3.4 | λ(μ) = α ± iω, condición espectral, transversalidad, forma polar, primer coeficiente de Lyapunov |
| 3 | Homoclínica | 3.5 | Hamiltoniano no perturbado, lazo, integral de Melnikov, disparo numérico, divergencia del periodo |
| 4 | Mapa unidimensional | 4.1 | Derivada a trozos, puntos fijos y multiplicadores, exponente de Lyapunov, horizonte n* |

Un problema que no pertenece a ninguna familia se trata numéricamente, y el
desarrollo lo dice: planteamiento, equilibrios y su linealización si el
sistema es autónomo, e integración con control de error.

### FUERA DE ALCANCE POR AHORA

Los problemas 4.2 a 4.5 y todo el Tema 5 están en el balotario solo con su
enunciado. El agente los reconoce (por el enunciado o por la forma) y responde
que están fuera de alcance, sin sustituirlos por otra cosa:

| Problema | Tema |
| --- | --- |
| 4.2 | Duplicación de periodo del mapa logístico (y en general mapas con parámetro) |
| 4.3 | Cascada de Feigenbaum |
| 4.4 | Disipatividad y elipsoide atrapante de Lorenz |
| 4.5 | Espectro de Lyapunov de un flujo |
| 5.1 – 5.5 | Dimensión de caja, herradura de Smale, mapa de Hénon, secciones de Poincaré, Kaplan-Yorke |

Si el sistema es integrable (Lorenz, Rössler) se ofrece solo su tratamiento
numérico, dicho como tal.

### Mapas discretos: el agente pregunta en vez de adivinar

`x_{n+1} = r·x_n(1−x_n)` y `ẋ = r·x(1−x)` se escriben con el mismo lado
derecho, así que el servidor **no puede** distinguirlos mirando las ecuaciones.
Y la diferencia no es cosmética: con r = 3.8 el mapa es caótico (λ ≈ 0.43),
mientras que la EDO continua converge monótonamente a un equilibrio.

Quien sí lo sabe es el usuario. Por eso la distinción es un campo del contrato,
`tipo_de_sistema`, y no una suposición:

| Valor | Qué hace el servidor |
| --- | --- |
| `edo_continua` (por defecto) | Lo trata como ecuación diferencial |
| `mapa_discreto` | Un mapa de una variable sin parámetro simbólico: procedimiento del 4.1. Uno de dos variables o con parámetro: fuera de alcance |
| `no_estoy_seguro` | Devuelve `etapa: aclaracion_necesaria` con la pregunta para el usuario y las dos opciones con sus consecuencias, **sin calcular nada** |

Además hay una heurística de notación: si la variable independiente es un
índice (`n`, `k`, `i`, `j`, `m`) o una variable de estado lleva sufijo de índice
(`x_n`, `theta_k`), el agente pide la aclaración aunque se haya declarado
continua — nadie escribe `dx/dn`. La heurística es deliberadamente estrecha
para no estorbar: `x1, x2` y `x, y` son nombres normales de componentes de un
sistema continuo y no disparan nada.

## La verificación es un portón, no un adorno

Toda respuesta trae un bloque `verificacion`. Si una comprobación concluyente no
se supera, el resultado llega con `ok: false`, la `etapa` que falló y **sin
conclusiones** ni desarrollo que interpretar. Las etapas posibles son
`validacion_solicitud`, `compilacion`, `interpretacion`, `resolucion` y
`verificacion`.

Hay dos clases de comprobaciones y las dos entran al mismo veredicto:

**Simbólicas, del desarrollo.** Cada familia comprueba lo que calculó: que la
solución general y la particular satisfagan la ecuación (y' − f ≡ 0, X' − AX ≡ 0)
y la condición inicial; que derivar la solución implícita devuelva la ecuación;
que la y₁ de una Riccati sea solución; que dH/dt ≡ 0; que las ramas de
equilibrio anulen el campo; que la condición espectral y la de transversalidad
de Hopf se cumplan.

**Numéricas, independientes del cálculo simbólico.** No confían en lo que
contrastan:

| Comprobación | Contra qué contrasta |
| --- | --- |
| `condicion_inicial` | La condición inicial pedida. |
| `residuo` | El propio campo, sustituyendo la trayectoria en la EDO. |
| `convergencia` | Una reintegración con tolerancias 100 veces más finas. |
| `metodo_alternativo` | Una reintegración con otro integrador (DOP853 o Radau). |
| `solucion_exacta` | La solución analítica del desarrollo (o la que aporte el cliente). |
| `integral_primera` | La energía/hamiltoniano del desarrollo a lo largo de la trayectoria. |
| `*_contra_autovalores_numericos` | La clasificación exacta frente a los autovalores de numpy. |
| `ramas_contra_muestreo_numerico` | Las ramas de una bifurcación frente al signo de f en una malla. |
| `linea_de_fase_coherente` | La estabilidad por f'(x*) frente al signo de f a cada lado. |
| `melnikov_vs_disparo`, `radio_del_ciclo_numerico`, `lyapunov_numerico`… | Las predicciones analíticas de Tema 3 y 4.1 frente a integraciones o iteraciones. |

**Sistemas caóticos.** Dos integraciones correctas de un sistema sensible
*tienen* que separarse a tiempo largo. Por eso el veredicto de convergencia se
decide en el tramo inicial, y cuando dos integraciones coinciden al principio y
divergen después se reporta `sensibilidad_detectada`: es un hallazgo legítimo,
no un fallo. A tiempo largo la comparación válida es la estadística.

El residuo estima su propio error: la derivada por diferencias finitas tiene un
error de truncamiento O(h²)·x''' que no dice nada sobre la calidad del
integrador, así que la prueba lo descuenta antes de denunciar nada.

## Organización

```
mcp_server.py                  Servidor MCP (stdio): las seis herramientas
orquestacion/
  capacidades.py               El recorrido completo, etapa por etapa (no calcula: ordena)
  interpretacion.py            Solicitud → Problema; lee del enunciado el método y lo pedido
  contratos.py                 Qué puede pedir un cliente y la forma de la respuesta
  catalogo.py                  Carga y valida balotario/tema_*.json
  informe.py, servidor_local.py   El informe de la sesión y su servidor http local
matematica/
  problema.py                  El problema interpretado (campo exacto, parámetro, CI, región…)
  clasificacion.py             Familias, selección del método, alcance (lo fuera de alcance)
  desarrollo.py                Representación estructurada del desarrollo (secciones, resultados…)
  primer_orden.py              Separable, lineal, Bernoulli, Riccati (Tema 1)
  segundo_orden.py             Cauchy-Euler (1.3)
  conservativos.py             Integral primera, separatriz, periodo elíptico (1.5, 2.4)
  sistemas_planos.py           Lineal plano, no lineal plano, ciclo límite (Tema 2)
  analisis_estabilidad.py      Equilibrios exactos, linealización, clasificación, regímenes
  analisis_bifurcaciones.py    Bifurcación 1D, línea de fase, Hopf, homoclínica (Tema 3)
  analisis_caos.py             Mapas unidimensionales: Lyapunov y horizonte (4.1)
  muestreo.py                  Curvas, órbitas y campos muestreados para figuras y evidencia
  expresiones.py               Texto → sympy (frontera de seguridad)
  modelo_edos.py               Integración con solve_ivp y planteamiento del tratamiento numérico
  validacion_solucion.py       El portón numérico
visualizacion/
  html.py                      Figuras plotly (numéricas y del desarrollo), por roles
  plantilla.py, plantillas/informe.html   El informe que abre el usuario
balotario/
  balotario.tex                Problemario original del grupo (25 problemas, 5 temas)
  tema_01.json .. tema_05.json Los 25 problemas convertidos
tests/                         280 pruebas
```

`capacidades` es quien ordena el recorrido y el único módulo que conoce a
todos; cada etapa vive en su capa. Ninguna familia sabe de MCP ni de plotly:
producen un `Desarrollo` (fórmulas en LaTeX salidas de objetos sympy,
resultados con nombre, validaciones y especificaciones de gráficas con roles),
y `visualizacion` lo convierte en figuras.

### Clasificación de los módulos originales y qué se hizo con cada uno

El prototipo tenía en `matematica/` ocho módulos. Se revisó el código de cada
uno (no su nombre) y se clasificó así:

| Módulo original | Clase | Qué se hizo |
| --- | --- | --- |
| `expresiones.py` | A. Funcional y reutilizable | Se conserva como frontera de seguridad; se agregó el parseo simbólico con números exactos (0.5 → 1/2) que necesita el desarrollo |
| `validacion_solucion.py` | A. Funcional y reutilizable | Se conserva como portón numérico; se agregaron `integral_primera` y un criterio mixto absoluto/relativo para `solucion_exacta` |
| `modelo_edos.py` | B. Funcional pero incompleto | Se conserva la integración; el stub `resolver_analitico` se reemplazó por las familias, y el tratamiento numérico ahora hace su planteamiento |
| `analisis_estabilidad.py` | C. Provisional | Jacobiano por diferencias finitas y solo "estable / inestable / no concluyente". Se reescribió: todo exacto, clasificación fina por τ, Δ, D, equilibrios por casos de factores y regímenes según un parámetro |
| `analisis_bifurcaciones.py` | C. Provisional (stub) | Se implementó el Tema 3 completo |
| `analisis_caos.py` | C (stub) y F | Se implementó solo el 4.1; el resto del Tema 4 y el Tema 5 quedan fuera de alcance, declarados en `clasificacion.py` |
| `datos_validacion.py` | D. Redundante | Una función que solo usaba el integrador y repetía la validación de `contratos`: se fusionó en `modelo_edos.py` |
| `buscar_equilibrios`, `es_autonomo` (en `orquestacion/capacidades.py`) | E. Mal ubicados | Era matemática dentro de la orquestación: se movieron a `analisis_estabilidad.py` |

### El informe de la sesión

Un resultado de herramienta MCP es **datos para el modelo**, no algo que la
interfaz dibuje: ningún cliente de chat renderiza el HTML que devuelve una
tool. Lo que sí funciona es un enlace.

`orquestacion/informe.py` mantiene un documento por conversación. Cada análisis
muestra **primero las gráficas** (las del desarrollo antes que las numéricas),
después el enunciado y el desarrollo completo con las fórmulas compuestas por
KaTeX, las conclusiones y la tabla de verificación. Lo fuera de alcance se avisa
arriba. El documento se reescribe sobre la **misma** dirección: el usuario abre
el enlace una vez y la página se actualiza sola.

**Una sesión no es un proceso.** El cliente MCP levanta este servidor una vez y
lo mantiene vivo para todas las conversaciones, y el protocolo no le dice al
servidor en qué chat está. Dos mecanismos, en este orden:

1. La herramienta **`nuevo_informe`**, que el agente llama al empezar una
   conversación. Es el camino bueno: explícito y exacto.
2. **Relevo por inactividad** (`EDOS_INACTIVIDAD_MIN`, 120 por defecto) como red
   de seguridad para cuando el agente no lo haga.

En local solo se conserva el último informe: al escribir uno nuevo se borran
los anteriores de `informes/`, para que la carpeta no crezca sin límite.

El destino depende de dónde corra el servidor:

| Entorno | Dónde queda | Qué recibe el usuario |
| --- | --- | --- |
| Contenedor en la red del lab | SeaweedFS, clave estable `informe-<sesion>.html` | URL pública |
| Local por stdio | `informes/` junto al proyecto | `http://127.0.0.1:<puerto>/informe-...` |

Un análisis que **no** supera una etapa también entra al informe, con su etapa
y su error. Esconderlo dejaría el documento contando una historia más limpia
que la real.

### Cómo se conecta

El transporte es **stdio**: el cliente MCP lanza el proceso y le habla por
stdin/stdout. No es un servicio que quede escuchando, así que no hay puerto ni
`docker compose up` que valga.

| Forma | Archivo de ejemplo |
| --- | --- |
| Proceso local | `conexion/claude_desktop_config.json` |
| Dentro del contenedor | `conexion/claude_desktop_config_docker.json` |

```bash
claude mcp add edos-grupo09 -- python mcp_server.py    # Claude Code
docker build -t edos-grupo09 .                          # imagen
docker compose run --rm edos                            # sesión stdio a mano
```

El cliente pide la lista de herramientas **una sola vez, al conectar**: después
de cambiar el servidor hay que reiniciar el cliente, o se sigue viendo lo de
antes. `ping` devuelve `revision`, una huella del código que está corriendo,
para comprobarlo.

Variables de entorno, todas opcionales. Sin ellas el agente funciona igual y el
informe queda en `informes/`:

| Variable | Para qué |
| --- | --- |
| `EDOS_INFORMES` | Dónde escribir el informe sin storage. En el contenedor apunta al volumen |
| `EDOS_SIN_SERVIDOR_LOCAL` | Apaga el servidor http del informe; entonces se entrega la ruta del archivo |
| `EDOS_INACTIVIDAD_MIN` | Minutos de silencio tras los cuales se abre un informe nuevo (120) |
| `EDOS_INFORME_MODO` | `ultimo` (por defecto) o `acumula` |
| `EDOS_STORAGE_URL` / `EDOS_STORAGE_BUCKET` | El SeaweedFS del laboratorio |
| `EDOS_URL_PUBLICA` | La ruta pública que asigna el Caddyfile del curso |

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
| `test_tema1.py` | Separable, lineal, Bernoulli, Riccati, Cauchy-Euler y péndulo: el ejercicio del balotario y equivalentes con otros datos, con sus resultados intermedios. |
| `test_tema2.py` | Sistemas lineales (silla, foco, centro, regímenes según γ), no lineales, hamiltonianos y ciclos límite. |
| `test_tema3.py` | Silla-nodo, transcrítica, horquillas con histéresis, Hopf super y subcrítica, homoclínica y línea de fase. |
| `test_tema4.py` | El 4.1 y mapas equivalentes; lo fuera de alcance (4.2–4.5, Tema 5). |
| `test_clasificacion.py` | Lectura del enunciado, selección y rechazo del método, alcance. |
| `test_balotario.py` | Integridad del catálogo y que el agente reproduce cada problema del balotario (y corrige 2.5 y 3.5). |
| `test_capacidades.py` | El recorrido completo, el portón, la degradación honesta y la serialización JSON. |
| `test_mcp_server.py` | Registro y esquema de las herramientas, llamada por el protocolo y limpieza de stdout. |
| `test_informe.py` | El informe: desarrollo con fórmulas, gráficas primero, dirección estable, sesión. |
| `test_visualizacion.py` | Escapado del HTML y roles de todas las figuras, numéricas y del desarrollo. |
| `test_expresiones.py`, `test_catalogo.py` | Entrada hostil; procedencia del catálogo contra el `.tex`. |

Las pruebas de familia no comparan solo la respuesta final: comprueban la
clasificación, el método elegido, las transformaciones (v = y^{1−n}, y = y₁ + 1/u),
los resultados intermedios (factor integrante, ecuación indicial, wronskiano,
autovalores, condiciones de Sotomayor, integral de Melnikov), la solución, las
condiciones iniciales, el análisis cualitativo, la consistencia analítico-numérica,
las gráficas y las validaciones.

### Qué cubre el balotario convertido

Los 25 problemas de los 5 temas están en `balotario/tema_0N.json`:

| Tema | Problemas | Los resuelve el agente | Tipo de objeto |
| --- | --- | --- | --- |
| 1. EDOs lineales y no lineales | 5 | 5 | EDO de 1.er y 2.º orden |
| 2. Retratos de fase | 5 | 5 | Sistemas autónomos 2D |
| 3. Bifurcaciones | 5 | 5 | Familias paramétricas |
| 4. Sistemas caóticos | 5 | 1 (4.1) | Mapas discretos y demostraciones |
| 5. Atractores extraños | 5 | 0 | Fractales, mapas 2D, Poincaré |

Los 9 restantes (4.2 a 4.5 y 5.1 a 5.5) **no tienen solución en el `.tex`**:
solo enunciado. Se registran con `solucion_esperada.tipo: "pendiente"`; no se
inventaron respuestas. `listar_balotario` informa el alcance de cada problema.

**Dos problemas del balotario tienen errores**, documentados en el campo
`revision_matematica` de su JSON (el `.tex` no se modificó):

- **2.5.** El anillo K = {1/2 ≤ r ≤ 2} contiene el equilibrio (1, 0) — en
  polares θ̇ = 1 − cos θ se anula en θ = 0 y ṙ = 0 en r = 1 —, así que
  Poincaré–Bendixson no aplica y el sistema **no tiene órbitas periódicas**:
  toda trayectoria con r > 0 tiende a (1, 0). Las pruebas numéricas anteriores
  no lo veían porque el radio converge a 1 en los dos casos.
- **3.5.** La segunda integral de Melnikov es I₂ = 36/35, no 6/7: M(μ) se anula
  en μ = −6/7, no en −5/7. Además, como la perturbación no es pequeña, el valor
  real de la conexión (disparo numérico) es μ* ≈ −0.8645, y el ciclo límite
  existe para −1 < μ < μ* (nace en el Hopf supercrítico de μ = −1), no "al
  cruzar μc".

Además se corrigió en el JSON un valor transcrito mal (3.3B, μ = 0.5: el
equilibrio es ±√((1+√3)/2) = ±1.16877089, no ±1.16877082).

## Estado y pendientes

Implementado: las 14 familias de la tabla, con su desarrollo, validaciones
simbólicas y numéricas y figuras; el tratamiento numérico verificado para lo
que no tiene familia; la detección de lo fuera de alcance; el informe con el
desarrollo compuesto; el servidor MCP sobre stdio y su contenedor.

Pendiente, a la espera de que el balotario lo desarrolle:

- Los problemas 4.2 a 4.5 (duplicación de periodo, Feigenbaum, disipatividad,
  espectro de Lyapunov de flujos) y todo el Tema 5. Cuando el `.tex` tenga su
  solución, cada uno será una familia nueva en `clasificacion.FAMILIAS` y sus
  ejercicios, su prueba de aceptación.

Límites conocidos de lo implementado:

- La línea de fase con infinitos equilibrios (sen x) estudia los de una ventana
  y no informa las cuencas que tocan su borde.
- En un sistema no lineal, un centro de la linealización se informa como no
  concluyente: decidirlo exige un argumento no lineal, que solo existe hoy para
  los sistemas conservativos.
- Los trayectos de un foco lineal no tienen ecuación cartesiana cerrada en el
  desarrollo (son espirales logarítmicas); se describen con la solución general.

### Si alguna vez hay que exponerlo por red

Hoy el alcance es stdio, que cubre Claude Code y Claude Desktop porque ambos
lanzan el servidor como proceso local. El SDK acepta otros transportes —
`servidor.run(transport="streamable-http")`— así que el cambio de transporte es
una línea, pero **no basta con eso**. Faltaría:

- **Autenticación.** El servidor no tiene ninguna: `MCPServer` soporta
  `auth_server_provider`, `token_verifier` y `auth`, y hoy no se usan.
- **Un tope de tiempo por llamada.** No existe. El caso más lento medido es el
  3.5 (unos 8 s, por el disparo numérico); en local es irrelevante, pero
  expuesto es un vector de agotamiento.
- **Herramientas asíncronas.** Son síncronas: un cálculo largo bloquea el bucle
  de eventos, de modo que un cliente puede dejar sin servicio a los demás.
- **HTTPS y un host alcanzable**, si el destino es un conector remoto.

### Sobre borrar `balotario.tex`

El `.tex` sigue en el proyecto a propósito. Los JSON conservan los enunciados,
los resultados finales y las fórmulas clave, pero **no las demostraciones paso
a paso**: el `.tex` tiene unas 2 800 líneas de desarrollo algebraico que el
catálogo no reproduce, y es la referencia del procedimiento que implementa cada
familia. Además, `test_catalogo.py` comprueba contra él que ningún ejercicio
sea inventado; si falta, ese test se salta con un mensaje explícito en vez de
fallar.
