# Agente de EDOs y sistemas dinámicos — Grupo 09

Servidor MCP que resuelve problemas de ecuaciones diferenciales
ordinarias (1 a 3 variables), de mapas iterados (1 y 2 variables) y de caos y
geometría fractal **con el desarrollo matemático del balotario del grupo**. Claude interpreta el pedido del usuario y
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
ejercicios son la suite de aceptación. El agente resuelve los 25. Lo que no
pertenece a ninguno de los cinco temas (una ecuación en derivadas parciales,
una pregunta que no es de matemáticas) queda **fuera del alcance del proyecto**
y el agente lo dice con un mensaje ordenado por temas, en vez de improvisar.

## Conectarse

El servidor corre desplegado en el laboratorio (streamable-http) y se conecta
con esta URL:

```
https://rac-unmsm.vekthos.org/grupo09/grupo09_proyecto01_edos-lnl-rf/mcp
```

- **Claude (web o Desktop), ChatGPT u otro cliente:** agregar un conector MCP
  personalizado con esa URL.
- **Claude Code:**

  ```bash
  claude mcp add --transport http edos-grupo09 https://rac-unmsm.vekthos.org/grupo09/grupo09_proyecto01_edos-lnl-rf/mcp
  ```

- **MCP Inspector:** `npx @modelcontextprotocol/inspector`, transporte
  "Streamable HTTP" y la misma URL. Muestra las herramientas, su esquema de
  entrada y la respuesta cruda de cada llamada.

Luego basta pedir en lenguaje natural: *"resuelve la
ecuación de Bernoulli y' + y = y³ con y(0) = 1"* o *"clasifica el equilibrio
del oscilador ẍ + γẋ + 4x = 0 según γ ≥ 0"*. Claude traducirá el pedido a una
llamada de `resolver_graficar_y_analizar_edo` o de `analizar_equilibrios`. Para
los Temas 4 y 5 basta pegar el enunciado: *"Para el mapa de Hénon con a = 1.4 y
b = 0.3, calcule el determinante jacobiano y el inverso"* va a
`resolver_caos_fractales_y_atractores`, que ya conoce las ecuaciones de Hénon.
Cada análisis devuelve además el enlace a su informe, la página con las
gráficas interactivas y el desarrollo.

## Herramientas expuestas

| Herramienta | Qué hace | Cuándo |
| --- | --- | --- |
| `ping` | Conexión, revisión del código, los cinco temas e inventario de familias | Antes de un análisis largo |
| `resolver_graficar_y_analizar_edo` | El recorrido completo: desarrollo, trayectoria si hay condición inicial, verificación y figuras | Resolver, hallar la solución general, graficar o analizar |
| `analizar_equilibrios` | Equilibrios, estabilidad o una bifurcación, con su desarrollo, **sin integrar** | La pregunta es de equilibrios o de un parámetro y no hay condición inicial |
| `resolver_caos_fractales_y_atractores` | Temas 4 y 5 con solo el enunciado: si no trae ecuación (Cantor, herradura, Feigenbaum, el teorema del espectro) o si nombra el sistema (Lorenz, Rössler, Hénon, logístico, tienda) | Caos, fractales, atractores extraños |
| `listar_balotario` | Los problemas del balotario con su ecuación lista, cómo pedirlos y su alcance | Para usarlo como vara de nivel |

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

# 4.2 — mapa logístico con r simbólico (o solo el enunciado, que nombra el mapa)
ecuaciones=["r*x*(1 - x)"], variables_estado=["x"], tipo_de_sistema="mapa_discreto",
parametro="r", rango_parametro=[0, 4], region={"x": [0, 1]}

# 4.3 — sin ecuación: los datos del enunciado (resolver_caos_fractales_y_atractores)
enunciado="... estime r_∞ ...", datos={"r_1": 3, "r_2": 3.449489742783178, "delta": 4.6692016}

# 5.4 — Rössler: basta el enunciado; la sección también se puede dar explícita
enunciado="El sistema de Rössler ... sección de Poincaré y = 0, ẏ > 0",
seccion_poincare={"variable": "y", "valor": 0, "sentido": "creciente"}
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
| `datos` | Números que no son parámetros del sistema: `r_1`, `r_2`, `delta` (Feigenbaum), `exponentes` (Kaplan-Yorke), `copias` y `razon` (fractal), `contraccion` y `expansion` (herradura). Si faltan, se leen del enunciado |
| `seccion_poincare` | `{variable, valor, sentido}` de la sección de Poincaré. Si falta, se lee del enunciado ("y = 0, ẏ > 0") |

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
| 4 | Duplicación de periodo | 4.2 | Puntos fijos y su existencia según r, multiplicadores, f²(x) − x factorizado por f(x) − x, discriminante, multiplicador del 2-ciclo por Vieta, r₁ y r₂ |
| 4 | Feigenbaum | 4.3 | Ley de convergencia geométrica, suma de la serie de razón 1/δ, r_∞ y r₃ estimados frente a los rₙ numéricos (Newton sobre f^p(x) = x, (f^p)' = −1) |
| 4 | Disipatividad | 4.4 | ∇·f, Liouville V(t) = V(0)e^{(∇·f)t}, búsqueda de V = Σaᵢ(xᵢ − cᵢ)² con V̇ = −k(Q − K), acotación Q ≥ κV − D, Gronwall y elipsoide atrapante |
| 4 | Espectro de Lyapunov | 4.5 | Demostración (+, 0, −): f(x(t)) resuelve la variacional, Liouville, ubicación del cero; contraste con el espectro por el método QR |
| 5 | Dimensión fractal | 5.1 | Conteo exacto N(sⁿ) = Nⁿ, cotas y límite, autosemejanza N·s^D = 1, medida, conteo de cajas sobre el conjunto construido |
| 5 | Herradura de Smale | 5.2 | Modelo lineal, Λ ≅ Cantor × Cantor y su dimensión, conjugación con el desplazamiento, los 2ⁿ puntos de periodo n resueltos uno por uno |
| 5 | Mapa del plano | 5.3 | Jacobiana, determinante, contracción de áreas, despeje del inverso y su comprobación por composición, descomposición en tres pasos, puntos fijos, exponentes |
| 5 | Sección de Poincaré | 5.4 | Divergencia y equilibrios, sección y su sentido, cruces por detección de eventos, contracción e^{λ₃T}, mapa de retorno unimodal y su exponente |
| 5 | Kaplan-Yorke | 5.5 | Σλᵢ frente a ⟨∇·f⟩, sumas parciales, k, D_L, contraste con el espectro calculado |

Un problema que no pertenece a ninguna familia se trata numéricamente, y el
desarrollo lo dice: planteamiento, equilibrios y su linealización si el
sistema es autónomo, e integración con control de error.

Para los Temas 4 y 5 el servidor conoce por su nombre los sistemas del
balotario (`matematica/sistemas_conocidos.py`): Lorenz, Rössler, Hénon, el
mapa logístico y el mapa tienda. Si el enunciado los nombra, se usan sus
ecuaciones con los valores que el enunciado escribe ("a = b = 0.2 y c = 5.7"),
y se leen los datos que no son parámetros (r₁, r₂, δ, los exponentes λᵢ, la
sección "y = 0, ẏ > 0"). La respuesta dice qué se leyó en
`interpretacion.sistema_reconocido` y `interpretacion.datos`.

### Lo que queda fuera del proyecto

Cuatro respuestas distintas, según qué llegue:

| Llega | Respuesta |
| --- | --- |
| Algo de matemáticas que no está en ningún tema: EDP, ecuaciones estocásticas, con retardo o integrales, series de Fourier, sistemas de más de 3 variables, mapas de 3 variables | `etapa: fuera_de_alcance` con `mensaje_para_el_usuario`: el motivo y, tema por tema, lo que el proyecto abarca |
| Algo que no es de matemáticas ("¿dónde queda el baño?") | `etapa: no_es_un_problema_del_proyecto`, con el mismo listado de temas. Las instrucciones del servidor le piden a Claude que ni siquiera llame a una herramienta |
| Un dato imposible (r₂ ≤ r₁, una razón de semejanza fuera de (0, 1), μ ≤ 2 en la herradura) | `etapa: datos`: qué valor está mal y qué rango se esperaba, para pedirle al usuario el correcto |
| Un método que existe pero que el balotario no trabaja (transformada de Laplace, Frobenius) | Se resuelve con el método del balotario que corresponde a la forma de la ecuación, y el desarrollo lo dice en su primera sección |

Un ejemplo del mensaje:

```
Problema fuera del alcance de los temas trabajados: el enunciado trata de ecuaciones en
derivadas parciales, que no forman parte de los cinco temas. Queda fuera de las limitaciones
del proyecto, así que no se resuelve.
El proyecto abarca:
  • Tema 1 — EDOs lineales y no lineales: separables (con intervalo maximal), lineales, ...
  • Tema 2 — Retratos de fase y análisis cualitativo en el plano: ...
  • Tema 3 — Teoría de bifurcaciones: silla-nodo, transcrítica, horquilla, Hopf y homoclínica.
  • Tema 4 — Sistemas dinámicos caóticos: ...
  • Tema 5 — Atractores extraños y geometría fractal: ...
Si su pregunta encaja en uno de estos temas, reformúlela con la ecuación o los datos del problema.
```

Las dos capas se cuidan por separado. Claude es quien recibe el lenguaje natural
y quien decide no llamar a una herramienta ante una charla; el servidor no
puede confiar en eso, porque cualquier cliente MCP puede mandarle cualquier
cosa, así que valida todo lo que llega y nunca levanta una excepción hacia el
cliente: cada fallo viaja como una respuesta con su `etapa`.

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
| `mapa_discreto` | Lo itera como mapa: el 4.1 si es de una variable, el 4.2 (o el 4.3 si se pregunta por Feigenbaum) si tiene un parámetro simbólico, el 5.3 si es del plano |
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
`validacion_solicitud`, `compilacion`, `interpretacion`, `datos`, `resolucion`
y `verificacion`, más `fuera_de_alcance` y `no_es_un_problema_del_proyecto`,
que no son fallos sino respuestas.

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
| `orbita_periodo_2_iterada`, `umbrales_numericos`, `razones_tienden_a_delta` | La órbita de periodo 2 y los r₁, r₂ exactos frente al mapa iterado; los rₙ resueltos por Newton. |
| `liouville_numerico`, `cota_de_gronwall`, `terminan_en_el_elipsoide` | det Φₜ = e^{(∇·f)t} integrando la variacional; trayectorias reales contra la cota del elipsoide. |
| `suma_igual_divergencia`, `exponente_nulo` | El espectro QR: Σλᵢ frente a ⟨∇·f⟩ sobre la misma órbita y el cero de la dirección del flujo. |
| `conteo_exacto`, `dimension_por_conteo`, `puntos_de_periodo_n` | Cajas contadas sobre el fractal construido; los 2ⁿ puntos periódicos de la herradura resueltos uno a uno. |
| `inverso_por_*`, `seccion_delgada`, `unimodal`, `lyapunov_por_el_mapa` | T∘T⁻¹ = id; la sección cae sobre una curva y el mapa de retorno reproduce λ₁ del flujo. |

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
server.py                      Servidor MCP (streamable-http, 0.0.0.0:8000): las cinco herramientas
storage.py                     Sube cada informe al SeaweedFS del laboratorio (patrón del piloto)
Dockerfile, docker-compose.yml, requirements.txt   Despliegue, con el contrato del laboratorio
orquestacion/
  capacidades.py               El recorrido completo, etapa por etapa (no calcula: ordena)
  interpretacion.py            Solicitud → Problema; lee del enunciado el método y lo pedido
  contratos.py                 Qué puede pedir un cliente y la forma de la respuesta
  catalogo.py                  Carga y valida balotario/tema_*.json
  informe.py                   Compone y publica la página de cada análisis
matematica/
  problema.py                  El problema interpretado (campo exacto, parámetro, CI, región…)
  clasificacion.py             Familias, selección del método, los cinco temas y lo que queda fuera
  sistemas_conocidos.py        Lorenz, Rössler, Hénon, logístico, tienda; datos leídos del enunciado
  desarrollo.py                Representación estructurada del desarrollo (secciones, resultados…)
  primer_orden.py              Separable, lineal, Bernoulli, Riccati (Tema 1)
  segundo_orden.py             Cauchy-Euler (1.3)
  conservativos.py             Integral primera, separatriz, periodo elíptico (1.5, 2.4)
  sistemas_planos.py           Lineal plano, no lineal plano, ciclo límite (Tema 2)
  analisis_estabilidad.py      Equilibrios exactos, linealización, clasificación, regímenes
  analisis_bifurcaciones.py    Bifurcación 1D, línea de fase, Hopf, homoclínica (Tema 3)
  analisis_caos.py             Mapas unidimensionales: Lyapunov y horizonte, duplicación de periodo, Feigenbaum (4.1–4.3)
  caos_en_flujos.py            Disipatividad y elipsoide atrapante, teorema del espectro (4.4, 4.5)
  atractores_fractales.py      Dimensión fractal, herradura, mapas del plano, Poincaré, Kaplan-Yorke (Tema 5)
  espectro_lyapunov.py         Espectro de Lyapunov de flujos y mapas por el método QR
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
test/                          Pruebas locales (no se suben al repositorio)
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
| `analisis_caos.py` | C (stub) y F | Se implementó el 4.1 y, cuando el `.tex` tuvo su solución, el 4.2 y el 4.3; el 4.4, el 4.5 y el Tema 5 viven en módulos propios (`caos_en_flujos.py`, `atractores_fractales.py`, `espectro_lyapunov.py`) |
| `datos_validacion.py` | D. Redundante | Una función que solo usaba el integrador y repetía la validación de `contratos`: se fusionó en `modelo_edos.py` |
| `buscar_equilibrios`, `es_autonomo` (en `orquestacion/capacidades.py`) | E. Mal ubicados | Era matemática dentro de la orquestación: se movieron a `analisis_estabilidad.py` |

### El informe de cada análisis

Un resultado de herramienta MCP es **datos para el modelo**, no algo que la
interfaz dibuje: ningún cliente de chat renderiza el HTML que devuelve una
tool. Lo que sí funciona es un enlace.

Por eso `orquestacion/informe.py` compone una página por análisis y
`storage.py` la sube al SeaweedFS del laboratorio con un nombre aleatorio
(`uuid`), el mismo patrón con que el piloto sube cada imagen. La página muestra
**primero las gráficas** (las del desarrollo antes que las numéricas), después
el enunciado y el desarrollo completo con las fórmulas compuestas por KaTeX, las
conclusiones y la tabla de verificación. La respuesta trae su URL en
`visualizacion.informe` y el enlace markdown en `visualizacion.enlace`.

El servidor desplegado lo comparten todos los usuarios y atiende llamadas en
paralelo, así que no hay un informe "de la conversación": cada análisis tiene su
propia dirección. Un análisis que no supera la resolución o la verificación
también tiene su página, con su etapa y su error, y el enlace viaja en
`detalles`. Una pregunta fuera de los temas del proyecto no publica página.

Nada se escribe a disco. Sin storage (en local) la herramienta responde igual,
sin enlace.

### Despliegue

Sigue el contrato del laboratorio y el piloto `grupos/g01/semana01/derivadas1/`:

| Archivo | Qué lleva |
| --- | --- |
| `server.py` | `MCPServer("grupo09-edos-lnl-rf")` y `mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)` |
| `storage.py` | `LAB_IMG_BUCKET` y `LAB_PUBLIC_IMG_URL`, que pone el despliegue; `PUT` a `seaweedfs:8333` con `uuid`, `timeout` y `None` si falla |
| `Dockerfile` | `python:3.11-slim`, copia `server.py`, `storage.py` y las carpetas `matematica/`, `orquestacion/`, `visualizacion/`, `balotario/`; `CMD ["python", "server.py"]` |
| `docker-compose.yml` | `container_name: ${LAB_CONTAINER_NAME}`, `mem_limit: 512m`, `restart: unless-stopped`, red `lab_net`, sin puertos ni volúmenes |
| `requirements.txt` | `mcp==2.1.1` y lo que el código importa |

Medido con `mcp==2.1.1` sobre HTTP, el proceso no pasa de unos 205 MB ni con
tres análisis pesados en paralelo (espectro de Lorenz y sección de Rössler).

El cliente pide la lista de herramientas **una sola vez, al conectar**: después
de un despliegue hay que reconectar el conector. `ping` devuelve `revision`,
una huella del código que está corriendo, para comprobar qué versión responde.

### Seguridad de la frontera

`matematica/expresiones.py` recibe texto de un cliente MCP arbitrario. **No usa
`eval`.** Valida en tres capas: léxica (lista blanca de caracteres, `__`
prohibido), de nombres (todo identificador debe ser un símbolo declarado o una
función permitida) y simbólica (tras parsear con sympy se comprueba que no
quedaron símbolos libres ni funciones ajenas).

## Pruebas

Las pruebas son locales: viven en `test/` y no se suben al repositorio. Desde
esta carpeta:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s test -t . -v
```

| Archivo | Cubre |
| --- | --- |
| `test_tema1.py` | Separable, lineal, Bernoulli, Riccati, Cauchy-Euler y péndulo: el ejercicio del balotario y equivalentes con otros datos, con sus resultados intermedios. |
| `test_tema2.py` | Sistemas lineales (silla, foco, centro, regímenes según γ), no lineales, hamiltonianos y ciclos límite. |
| `test_tema3.py` | Silla-nodo, transcrítica, horquillas con histéresis, Hopf super y subcrítica, homoclínica y línea de fase. |
| `test_tema4.py` | 4.1 a 4.5 con los datos del balotario y con otros (mapa cúbico, Lorenz con otros parámetros, Rössler sin elipsoide, un ciclo límite que no es caótico); datos imposibles; lo que queda fuera del proyecto. |
| `test_tema5.py` | 5.1 a 5.5: Cantor, Sierpinski, Koch y conjuntos dados por N y s; otra herradura; Hénon con otros parámetros, un mapa que conserva área y uno no invertible; las dos mitades de la sección de Rössler; Kaplan-Yorke con casos límite. |
| `test_clasificacion.py` | Lectura del enunciado, selección y rechazo del método, cada tema a su familia, lo que queda fuera y el mensaje de alcance. |
| `test_balotario.py` | Integridad del catálogo y que el agente reproduce cada problema del balotario solo con su enunciado (y corrige 2.5, 3.5, 5.3 y 5.4). |
| `test_capacidades.py` | El recorrido completo, el portón, la degradación honesta y la serialización JSON. |
| `test_mcp_server.py` | Nombre del servidor, registro y esquema de las herramientas, llamada por el protocolo y resultados sin órdenes para el modelo. |
| `test_informe.py` | El informe: una página por análisis, desarrollo con fórmulas, gráficas primero, `storage.py` y el caso sin storage. |
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
| 4. Sistemas caóticos | 5 | 5 | Mapas discretos, estimaciones y demostraciones |
| 5. Atractores extraños | 5 | 5 | Fractales, mapas 2D, Poincaré, Kaplan-Yorke |

Los problemas 4.2 a 5.5 se completaron en el `.tex` después del resto; cada
uno lleva en su JSON la solución que el agente reproduce y, en `solicitud`, cómo
se pide (para casi todos basta el enunciado). `listar_balotario` informa el
alcance de cada problema.

**Cuatro problemas del balotario tienen errores**, documentados en el campo
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
- **5.3.** El segundo punto fijo de Hénon es x₋ = (−0.7 − √6.09)/2.8 ≈ −1.1314,
  no −1.1135 (dos cifras transpuestas). La conclusión no cambia: los dos son
  sillas.
- **5.4.** Sobre y = 0 es ẏ = x, así que la mitad ẏ > 0 que elige el `.tex` es
  x > 0, justo donde ocurre la excursión: allí los cruces tienen z entre 0.08 y
  18 y x_{n+1} no es función de x_n. La reducción a un mapa unimodal (máximo en
  u = −x ≈ 5.78, ⟨ln|g'|⟩/T ≈ λ₁ ≈ 0.07) funciona en la otra mitad, ẏ < 0. El
  agente prueba la mitad pedida, lo detecta, lo dice y usa la otra.

Además se corrigió en el JSON un valor transcrito mal (3.3B, μ = 0.5: el
equilibrio es ±√((1+√3)/2) = ±1.16877089, no ±1.16877082).

## Estado y límites

Implementado: las 23 familias de la tabla, que cubren los 25 problemas del
balotario, con su desarrollo, validaciones simbólicas y numéricas y figuras; el
tratamiento numérico verificado para lo que no tiene familia; el mensaje
ordenado por temas para lo que queda fuera del proyecto; el informe con el
desarrollo compuesto; el servidor MCP por streamable-http y su despliegue.

Límites conocidos de lo implementado:

- La región atrapante (4.4) se demuestra con funciones cuadráticas diagonales
  V = Σaᵢ(xᵢ − cᵢ)²: sirve para Lorenz y sistemas parecidos; para Rössler no
  existe una así, y el desarrollo lo dice.
- El exponente λ₁ ≈ 0.07 de Rössler converge despacio: según la órbita sale
  entre 0.066 y 0.079 con 1500 unidades de tiempo. Las validaciones usan
  tolerancias de ese tamaño.
- El 4.2 da r₂ en forma cerrada cuando f²(x) − x deja un factor cuadrático
  (mapas cuadráticos como el logístico); para otros mapas da r₁ exacto y lo dice.

- La línea de fase con infinitos equilibrios (sen x) estudia los de una ventana
  y no informa las cuencas que tocan su borde.
- En un sistema no lineal, un centro de la linealización se informa como no
  concluyente: decidirlo exige un argumento no lineal, que solo existe hoy para
  los sistemas conservativos.
- Los trayectos de un foco lineal no tienen ecuación cartesiana cerrada en el
  desarrollo (son espirales logarítmicas); se describen con la solución general.

### Sobre el despliegue

- **Sin autenticación propia.** La URL es pública, como la de los demás grupos
  del laboratorio; HTTPS y la ruta los pone el proxy del laboratorio.
- **Sin tope de tiempo por llamada.** Los casos más lentos medidos rondan los
  8 s (el disparo numérico del 3.5, la sección de Rössler). Las herramientas
  son síncronas y el SDK las ejecuta en hilos, así que un cálculo largo no
  bloquea a los demás clientes.

### Sobre borrar `balotario.tex`

El `.tex` sigue en el proyecto a propósito. Los JSON conservan los enunciados,
los resultados finales y las fórmulas clave, pero **no las demostraciones paso
a paso**: el `.tex` tiene unas 2 800 líneas de desarrollo algebraico que el
catálogo no reproduce, y es la referencia del procedimiento que implementa cada
familia. Además, `test_catalogo.py` comprueba contra él que ningún ejercicio
sea inventado; si falta, ese test se salta con un mensaje explícito en vez de
fallar.
