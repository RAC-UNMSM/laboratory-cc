# Grupo 09 — EDOs lineales y no lineales, retratos de fase, sistemas dinámicos caóticos, atractores extraños y bifurcaciones

**Agente MCP.** El proyecto es un **servidor MCP** al que un cliente de chat le
hace preguntas en lenguaje natural. El usuario escribe «resuelva la ecuación de
Bernoulli y' + y = y³ con y(0) = 1» o «clasifique el equilibrio del oscilador
según γ ≥ 0»; el modelo traduce eso a una llamada a las herramientas del
servidor; el servidor **entiende el tipo de problema, aplica el procedimiento
matemático que le corresponde, calcula, analiza, verifica y dibuja**, y devuelve
el desarrollo estructurado; el modelo lo presenta y le entrega al usuario el
enlace al informe.

Esa división es el criterio de diseño de todo lo demás: **el desarrollo lo
calcula el servidor, y el modelo no agrega operaciones que el servidor no
hizo.** Ninguna fórmula ni número que el usuario vea sale de la redacción del
modelo; todos salen de un cálculo (simbólico con sympy, numérico con scipy)
verificado.

## Objetivo

Resolver y analizar los problemas del balotario del grupo — EDOs de primer y
segundo orden, sistemas planos lineales y no lineales, sistemas conservativos,
ciclos límite, bifurcaciones locales y globales, y el exponente de Lyapunov de
mapas unidimensionales — con su **desarrollo matemático real**, generalizado a
cualquier ejercicio de la misma familia, y con resultados **verificables** y
reproducibles.

## Formulación

Problemas de la forma

$$
\mathbf{x}'=\mathbf{F}(t,\mathbf{x};\boldsymbol{\theta}),
\qquad \mathbf{x}(t_0)=\mathbf{x}_0\ \ (\text{opcional}),
$$

donde $\mathbf{x}$ son las variables de estado (1 a 3), $t$ la variable
independiente, $\boldsymbol{\theta}$ los parámetros (uno de ellos puede quedar
simbólico, como $\gamma$ o $\mu$) y $\mathbf{F}$ el campo vectorial; o mapas
$x_{n+1}=f(x_n)$ de una variable.

La condición inicial es opcional: «halle la solución general» o «clasifique el
equilibrio según $\gamma$» no la tienen. Una EDO de orden $n$ se reduce antes a
un sistema de $n$ ecuaciones de primer orden, y el servidor reconoce esa forma
($y'=y_p$, $y_p'=\dots$) y la trata como la EDO de orden $n$ que es.

## Estado real: qué resuelve hoy y qué no

El balotario determina el alcance. Lo que el `.tex` resuelve, el agente lo
resuelve con el mismo procedimiento; lo que el `.tex` solo enuncia, el agente lo
declara **FUERA DE ALCANCE POR AHORA**.

| Tema | Familias (problemas del balotario) | Estado |
| --- | --- | --- |
| 1. EDOs lineales y no lineales | Separable (1.1), lineal, Bernoulli (1.2), Cauchy-Euler (1.3), Riccati (1.4), péndulo conservativo (1.5) | **Implementado** |
| 2. Retratos de fase y análisis cualitativo en el plano | Lineal plano y clasificación según un parámetro (2.1, 2.2), no lineal plano (2.3), hamiltoniano con órbita homoclínica (2.4), ciclo límite por Poincaré–Bendixson (2.5) | **Implementado** |
| 3. Teoría de bifurcaciones | Silla-nodo, transcrítica, horquillas e histéresis (3.1–3.3), línea de fase, Hopf (3.4), homoclínica con Melnikov y disparo numérico (3.5) | **Implementado** |
| 4. Sistemas dinámicos caóticos | Exponente de Lyapunov y horizonte de un mapa 1D (4.1) | **Implementado** |
| 4. Sistemas dinámicos caóticos | Duplicación de periodo, Feigenbaum, disipatividad de Lorenz, espectro de Lyapunov (4.2–4.5) | **Fuera de alcance por ahora** |
| 5. Atractores extraños y geometría fractal | Dimensión fractal, herradura de Smale, Hénon, secciones de Poincaré, Kaplan-Yorke | **Fuera de alcance por ahora** |

Un problema que no pertenece a ninguna familia se resuelve numéricamente
(planteamiento, equilibrios y su linealización si es autónomo, integración con
control de error: RK45, RK23, DOP853, Radau, BDF, LSODA), y el desarrollo lo
dice. Lo fuera de alcance se reconoce por el enunciado o por la forma del
problema, y la respuesta lo declara sin ofrecer un sustituto como si fuera la
respuesta.

**El balotario tiene dos errores**, que el agente no repite (documentados en
`revision_matematica` de su JSON; el `.tex` no se modificó):

- **2.5:** el anillo de Poincaré–Bendixson contiene el equilibrio (1, 0), así
  que el teorema no aplica y el sistema no tiene órbitas periódicas.
- **3.5:** la integral de Melnikov $I_2$ vale $36/35$, no $6/7$; su cero es
  $\mu=-6/7$, el valor real de la conexión homoclínica es $\mu^*\approx-0.8645$, y
  el ciclo límite existe para $-1<\mu<\mu^*$.

### La ambigüedad continuo/discreto

$x_{n+1}=r\,x_n(1-x_n)$ y $\mathrm{d}x/\mathrm{d}t=r\,x(1-x)$ se escriben con el
mismo lado derecho: el servidor **no puede distinguirlos** mirando las
ecuaciones. Quien lo sabe es el usuario. Por eso es un campo del contrato
(`tipo_de_sistema`) y no una suposición, y `'no_estoy_seguro'` es una respuesta
válida que hace que el servidor devuelva la pregunta en vez de un número. Importa:
el mapa logístico con $r=3.8$ es caótico ($\lambda\approx0.43$), mientras que la
EDO continua del mismo lado derecho converge a un equilibrio.

## Arquitectura

Tres capas, sin dependencias hacia arriba. `matematica/` no sabe que existe
`orquestacion/`, y ninguna de las dos sabe que existe MCP.

```text
edos-lineales-no-lineales-y-retrato-de-fase/
├── mcp_server.py              Las 6 herramientas MCP (transporte stdio)
├── storage.py                 Publica el informe en el storage del laboratorio
├── matematica/                CAPA MATEMÁTICA — no sabe de MCP
│   ├── problema.py            El problema interpretado (campo exacto, parámetro, CI, región)
│   ├── clasificacion.py       Familias del balotario, selección del método, alcance
│   ├── desarrollo.py          El desarrollo estructurado: secciones, resultados, validaciones
│   ├── primer_orden.py        Separable, lineal, Bernoulli, Riccati
│   ├── segundo_orden.py       Cauchy-Euler y variación de parámetros
│   ├── conservativos.py       Integral primera, separatriz, periodo elíptico
│   ├── sistemas_planos.py     Lineal plano, no lineal plano, ciclo límite
│   ├── analisis_estabilidad.py Equilibrios exactos, linealización, regímenes
│   ├── analisis_bifurcaciones.py Bifurcación 1D, línea de fase, Hopf, homoclínica
│   ├── analisis_caos.py       Mapas 1D: Lyapunov y horizonte de predictibilidad
│   ├── muestreo.py            Curvas, órbitas y campos para figuras y evidencia numérica
│   ├── expresiones.py         Texto → sympy, sin eval
│   ├── modelo_edos.py         Integración (solve_ivp) y planteamiento numérico
│   └── validacion_solucion.py El portón numérico
├── orquestacion/              FLUJO — no sabe de MCP ni de HTML
│   ├── interpretacion.py      Solicitud → problema; método y pedidos del enunciado
│   ├── contratos.py           Qué se puede pedir y qué se devuelve (pydantic)
│   ├── capacidades.py         El recorrido completo del agente
│   ├── catalogo.py            Carga y valida el balotario
│   └── informe.py             El informe de la conversación
├── visualizacion/             PRESENTACIÓN
│   ├── html.py                Figuras de plotly (declaran su rol, no su color)
│   ├── plantilla.py           Carga la plantilla e inyecta los datos
│   └── plantillas/informe.html La plantilla (KaTeX para las fórmulas)
├── balotario/                 25 problemas en 5 temas + el .tex original
└── tests/                     280 pruebas
```

### El recorrido de una pregunta

```text
Usuario (lenguaje natural)
        │
        ▼
Modelo del cliente MCP ── elige la herramienta; pasa el enunciado y los datos
        │
        ▼
mcp_server.py ─────────── frontera MCP; protege stdout (es el canal JSON-RPC)
        │
        ▼
contratos.py ──────────── valida la solicitud; ¿mapa o EDO? si hay duda, pregunta
        │
        ▼
interpretacion.py ─────── PROBLEMA → INTERPRETACIÓN (método y pedidos del enunciado)
        │
        ▼
clasificacion.py ──────── CLASIFICACIÓN → SELECCIÓN DEL MÉTODO (o fuera de alcance)
        │
        ▼
familia del balotario ─── DESARROLLO + CÁLCULO SIMBÓLICO + ANÁLISIS + validaciones
        │
        ▼
modelo_edos.py ────────── CÁLCULO NUMÉRICO si hay condición inicial o no hay familia
        │
        ▼
validacion_solucion.py ── PORTÓN: si algo falla, se detiene sin conclusiones
        │
        ▼
html.py + informe.py ──── VISUALIZACIÓN → informe de la sesión → enlace
        │
        ▼
Modelo ── PRESENTACIÓN: sigue `desarrollo.secciones` y entrega el enlace
```

`capacidades.py` es el único módulo que conoce a todos los demás. **El orden no
es decorativo:** la verificación va antes de la presentación, de modo que un
resultado inválido no llegue nunca acompañado de conclusiones.

### El desarrollo como dato, no como texto

Cada familia produce un `Desarrollo`:

- `resultados`: los objetos matemáticos con nombre semántico —
  `factor_integrante`, `ecuacion_indicial`, `wronskiano`, `autovalores`,
  `ramas`, `coeficiente_lyapunov`, `mu_melnikov`— solo los que su método
  produce;
- `secciones`: el orden en que ese cálculo se lee, con títulos propios del
  problema y fórmulas en LaTeX generadas desde los objetos sympy (no escritas a
  mano); las destacadas son las que el balotario encuadra;
- `conclusiones`, `validaciones` y las especificaciones de las gráficas.

El modelo de lenguaje recibe ese desarrollo y lo presenta; no tiene que, ni
debe, rehacer el cálculo.

## Las herramientas MCP

| Herramienta | Para qué |
| --- | --- |
| `resolver_graficar_y_analizar_edo` | Resolver, hallar la solución general, graficar o analizar; con condición inicial además integra y contrasta |
| `analizar_equilibrios` | Equilibrios, estabilidad o una bifurcación, **sin** condición inicial; con `parametro` declarado, una sola llamada estudia la bifurcación entera |
| `listar_balotario` | Los 25 problemas del grupo, con su ecuación, su alcance y las revisiones |
| `informe` | La dirección del informe de la conversación |
| `nuevo_informe` | Abre uno vacío al empezar un chat |
| `ping` | Revisión del código e inventario de familias y de lo fuera de alcance |

## Verificación: el portón del agente

Toda respuesta trae un bloque `verificacion` con dos clases de pruebas.

**Del desarrollo (simbólicas):** la solución sustituida en la ecuación da
$y'-f\equiv0$ (o $X'-AX\equiv0$); la solución particular cumple la condición
inicial; derivar la solución implícita devuelve la ecuación; la integral
primera tiene derivada nula a lo largo del flujo; las ramas de equilibrio
anulan el campo; las condiciones espectral y de transversalidad de Hopf se
cumplen.

**Numéricas, independientes del cálculo simbólico:**

| Prueba | Contra qué contrasta |
| --- | --- |
| `condicion_inicial` | La condición inicial pedida |
| `residuo` | El propio campo vectorial, por diferencias finitas |
| `convergencia` | Una reintegración con tolerancias 100 veces más finas |
| `metodo_alternativo` | Una reintegración con otro integrador |
| `solucion_exacta` | La solución analítica del desarrollo (o la que aporte el usuario) |
| `integral_primera` | La energía del desarrollo a lo largo de la trayectoria numérica |
| clasificación vs. numpy | El tipo y la estabilidad exactos frente a los autovalores numéricos |
| ramas vs. muestreo | Las ramas de una bifurcación frente al signo de $f$ en una malla |
| Melnikov vs. disparo, radio del ciclo, Lyapunov | Las predicciones del Tema 3 y del 4.1 frente a integraciones o iteraciones |

Dos detalles que distinguen una verificación honesta de una que solo aparenta:

- **El residuo estima su propio error.** La derivada central tiene un error de
  truncamiento $-(h^2/6)\,x'''$ que no dice nada sobre la calidad del
  integrador; la prueba lo descuenta antes de denunciar nada.
- **El caos no se confunde con un error.** Dos integraciones correctas de un
  sistema sensible *tienen* que separarse a tiempo largo. El veredicto se decide
  en una ventana inicial, y la separación posterior se reporta como **evidencia
  de sensibilidad**, no como fallo.

Si una prueba concluyente no se supera, el servidor devuelve la etapa que falló
y **no emite conclusiones**: no existe una respuesta que lleve a la vez un error
y un desarrollo.

## Seguridad de la frontera

`matematica/expresiones.py` recibe texto de un cliente MCP arbitrario. **No usa
`eval`.** Valida en tres capas: léxica (lista blanca de caracteres, `__`
prohibido), de nombres (todo identificador debe ser un símbolo declarado o una
función permitida) y simbólica (tras parsear con sympy se comprueba que no
quedaron símbolos libres ni funciones ajenas).

El informe se publica en una URL pública del laboratorio, así que todo lo que el
cliente controla —título, enunciado, nombres de variable y de parámetro— se
inserta como texto y nunca como marcado.

## El informe: cómo ve el usuario su trabajo

Un resultado de herramienta MCP es **datos para el modelo**, no algo que la
interfaz dibuje: ningún cliente de chat renderiza el HTML que devuelve una
tool. Lo que sí funciona es un enlace.

Sin el storage del laboratorio el informe queda en un archivo, y una ruta
`C:\...\informe.html` no se puede abrir con un clic. Por eso el agente sirve esa
carpeta en `127.0.0.1`, en un puerto que elige el sistema: el enlace se abre con
un clic y la página se actualiza igual que en el despliegue del laboratorio.

Cada análisis muestra, en este orden: **las gráficas** (las del desarrollo
—solución analítica con la numérica encima, retrato de fase con nulclinas,
variedades y separatrices, diagrama de bifurcación, plano traza-determinante,
telaraña— antes que las numéricas), el enunciado, el desarrollo con las
fórmulas compuestas por KaTeX, las conclusiones y la tabla de verificación. Lo
fuera de alcance se avisa arriba.

El informe enseña **la última pregunta**, no un historial: cada análisis
reemplaza al anterior en la misma dirección. Con `EDOS_INFORME_MODO=acumula`
las secciones se apilan, la más reciente arriba, para comparar respuestas entre
sí.

**Una sesión no es un proceso.** El cliente levanta el servidor una vez y lo
mantiene vivo para todas las conversaciones: el agente llama a `nuevo_informe`
al abrir un chat, y hay un relevo por inactividad como red de seguridad. En
local solo se conserva el último informe.

Un análisis que **no** supera una etapa también entra al informe, con su etapa y
su error.

La plantilla es un `.html` de verdad, separada del Python: los datos entran como
JSON y el render ocurre en el navegador. Las figuras no llevan colores
cocinados; cada traza declara **qué es** (una rama estable, una separatriz, una
nulclina) y la página le asigna el color desde su CSS, de modo que la misma
figura se ve bien en claro y en oscuro. Como el verde y el rojo de
estable/inestable quedan en banda de advertencia para daltonismo, el marcador
cambia además de forma.

## Integrantes y responsabilidades

| Integrante | Rol | Archivos |
| --- | --- | --- |
| **Yanac Minaya Junior Alberto** | Modelado, resolución y simulación dinámica | `modelo_edos.py`, `analisis_caos.py` |
| **Tisnado Yarleque Christian David** | Estabilidad y bifurcaciones | `analisis_estabilidad.py`, `analisis_bifurcaciones.py` |
| **Quispe Gonzales Mark** | Orquestación, backend y datos | `mcp_server.py`, `capacidades.py`, `contratos.py`, `catalogo.py`, `storage.py` |
| **David Alejandro Tejada Ossio** | Visualización | `html.py`, `plantilla.py`, `plantillas/informe.html`, `informe.py` |
| **Illescas Vicente Alexander George** | Verificación | `validacion_solucion.py`, `tests/` |

Módulos nuevos de esta etapa, todavía sin responsable asignado:
`problema.py`, `clasificacion.py`, `desarrollo.py`, `primer_orden.py`,
`segundo_orden.py`, `conservativos.py`, `sistemas_planos.py`, `muestreo.py` y
`orquestacion/interpretacion.py`.

## Casos de demostración y pruebas

El balotario es la suite de aceptación: `tests/test_balotario.py` pasa cada
problema por el agente tal como lo pediría un cliente y lo compara con la
solución del `.tex` (y, en 2.5 y 3.5, con la corrección documentada). Las
pruebas de cada tema (`test_tema1.py` … `test_tema4.py`) repiten cada familia
con ejercicios equivalentes de otros datos y comprueban los resultados
intermedios del procedimiento.

| Caso | Qué se verifica |
| --- | --- |
| 1.1 $y'=3xy^2$, $y(0)=1$ | Primitivas, $C=-1$, $y=2/(2-3x^2)$, intervalo $(-\sqrt6/3,\sqrt6/3)$ |
| 1.2 Bernoulli | $v=y^{-2}$, $v'-2v=-2$, $\mu=e^{-2x}$, $y\equiv1$ sobre el equilibrio |
| 1.3 Cauchy-Euler | $m^2-3m+2=0$, $W=x^2$, $y_p=\tfrac12x^3\ln x-\tfrac34x^3$ |
| 1.5 Péndulo | $E$, separatriz $\pm2\omega_0\cos(\theta/2)$, $T=\tfrac{4}{\omega_0}K(k)$ |
| 2.2 Oscilador según $\gamma\ge0$ | Centro, foco, nodo degenerado en $\gamma=4$, nodo |
| 2.3 Competencia | Cuatro equilibrios, silla $-1\pm\sqrt2$, cuencas separadas por $W^s$ |
| 3.3B Histéresis | Silla-nodos en $\mu=-1/4$, horquilla subcrítica en 0, ancho $1/4$ |
| 3.4 Hopf | $\alpha=\mu$, $\omega=1$, $R=\sqrt\mu$, $T=2\pi$, $l_1=-1$ |
| 3.5 Homoclínica | $I_1=6/5$, $I_2=36/35$, $\mu_M=-6/7$, $\mu^*\approx-0.8645$ |
| 4.1 Mapa tienda | $\lambda=\ln2$ exacto, $n^*=34$ para $\delta_0=10^{-10}$ |
| Lorenz | Tratamiento numérico, sensibilidad detectada; Lyapunov de flujos fuera de alcance |

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests          # 280 pruebas
claude mcp add edos-grupo09 -- python mcp_server.py
```

## Qué entrega el agente

1. La clasificación del problema y el método aplicado, con el motivo.
2. El desarrollo matemático completo (`desarrollo.secciones`) y sus resultados
   con nombre.
3. La solución numérica, si hubo condición inicial, contrastada con la
   analítica.
4. El bloque de verificación completo, con lo medido y el umbral de cada prueba.
5. El enlace al informe, donde todo lo anterior aparece dibujado y legible.
6. Lo que se pidió y está **fuera de alcance por ahora**, dicho como tal.

El punto 6 no es una carencia del entregable: es parte de él. Un agente que
calla lo que no sabe hacer es menos útil que uno que lo declara, porque obliga a
desconfiar de todo lo demás.
