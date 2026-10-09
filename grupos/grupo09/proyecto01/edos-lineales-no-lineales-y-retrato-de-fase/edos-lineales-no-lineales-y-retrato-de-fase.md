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
ciclos límite, bifurcaciones locales y globales, caos en mapas y en flujos
(Lyapunov, duplicación de periodo, Feigenbaum, disipatividad), atractores
extraños y geometría fractal — con su **desarrollo matemático real**,
generalizado a cualquier ejercicio de la misma familia, y con resultados
**verificables** y reproducibles.

## Formulación

Problemas de la forma

$$
\mathbf{x}'=\mathbf{F}(t,\mathbf{x};\boldsymbol{\theta}),
\qquad \mathbf{x}(t_0)=\mathbf{x}_0\ \ (\text{opcional}),
$$

donde $\mathbf{x}$ son las variables de estado (1 a 3), $t$ la variable
independiente, $\boldsymbol{\theta}$ los parámetros (uno de ellos puede quedar
simbólico, como $\gamma$ o $\mu$) y $\mathbf{F}$ el campo vectorial; o mapas
$\mathbf{x}_{n+1}=\mathbf{f}(\mathbf{x}_n)$ de una o dos variables; o preguntas
sin ecuación de los Temas 4 y 5 (la dimensión del conjunto de Cantor, la
herradura de Smale, la estimación de Feigenbaum, el teorema del espectro de
Lyapunov), que se responden a partir del enunciado y sus datos.

La condición inicial es opcional: «halle la solución general» o «clasifique el
equilibrio según $\gamma$» no la tienen. Una EDO de orden $n$ se reduce antes a
un sistema de $n$ ecuaciones de primer orden, y el servidor reconoce esa forma
($y'=y_p$, $y_p'=\dots$) y la trata como la EDO de orden $n$ que es.

## Estado real: qué resuelve hoy y qué no

El balotario determina el alcance: lo que el `.tex` resuelve, el agente lo
resuelve con el mismo procedimiento. Hoy el `.tex` desarrolla los 25 problemas,
y el agente los 25.

| Tema | Familias (problemas del balotario) | Estado |
| --- | --- | --- |
| 1. EDOs lineales y no lineales | Separable (1.1), lineal, Bernoulli (1.2), Cauchy-Euler (1.3), Riccati (1.4), péndulo conservativo (1.5) | **Implementado** |
| 2. Retratos de fase y análisis cualitativo en el plano | Lineal plano y clasificación según un parámetro (2.1, 2.2), no lineal plano (2.3), hamiltoniano con órbita homoclínica (2.4), ciclo límite por Poincaré–Bendixson (2.5) | **Implementado** |
| 3. Teoría de bifurcaciones | Silla-nodo, transcrítica, horquillas e histéresis (3.1–3.3), línea de fase, Hopf (3.4), homoclínica con Melnikov y disparo numérico (3.5) | **Implementado** |
| 4. Sistemas dinámicos caóticos | Exponente de Lyapunov y horizonte de un mapa 1D (4.1), duplicación de periodo (4.2), Feigenbaum (4.3), disipatividad y elipsoide de Lorenz (4.4), teorema del espectro de Lyapunov (4.5) | **Implementado** |
| 5. Atractores extraños y geometría fractal | Dimensión de caja (5.1), herradura de Smale (5.2), mapa de Hénon (5.3), sección de Poincaré de Rössler (5.4), Kaplan-Yorke (5.5) | **Implementado** |

Un problema que no pertenece a ninguna familia se resuelve numéricamente
(planteamiento, equilibrios y su linealización si es autónomo, integración con
control de error: RK45, RK23, DOP853, Radau, BDF, LSODA), y el desarrollo lo
dice.

Lo que no pertenece a ninguno de los cinco temas —una ecuación en derivadas
parciales, estocástica o con retardo, un sistema de más de tres variables— se
responde con `etapa: fuera_de_alcance` y un mensaje ordenado: «Problema fuera
del alcance de los temas trabajados: …; el proyecto abarca: Tema 1 — …, Tema 2
— …». Una pregunta que no es de matemáticas («¿dónde queda el baño?») recibe
`etapa: no_es_un_problema_del_proyecto` con el mismo listado, y un dato
imposible (r₂ ≤ r₁, una razón fuera de (0, 1)) recibe `etapa: datos` con el
valor que hay que corregir. Ninguna de las tres ofrece un sustituto como si
fuera la respuesta.

**El balotario tiene cuatro errores**, que el agente no repite (documentados en
`revision_matematica` de su JSON; el `.tex` no se modificó):

- **2.5:** el anillo de Poincaré–Bendixson contiene el equilibrio (1, 0), así
  que el teorema no aplica y el sistema no tiene órbitas periódicas.
- **3.5:** la integral de Melnikov $I_2$ vale $36/35$, no $6/7$; su cero es
  $\mu=-6/7$, el valor real de la conexión homoclínica es $\mu^*\approx-0.8645$, y
  el ciclo límite existe para $-1<\mu<\mu^*$.
- **5.3:** el segundo punto fijo de Hénon es $x_-\approx-1.1314$, no $-1.1135$.
- **5.4:** la reducción de Rössler a un mapa unimodal funciona en la mitad
  $y=0,\ \dot y<0$ de la sección; en la mitad $\dot y>0$ que elige el `.tex` los
  cruces caen sobre el pliegue ($z$ entre 0.08 y 18) y $x_{n+1}$ no es función
  de $x_n$.

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
├── server.py                  Las 5 herramientas MCP (streamable-http, puerto 8000)
├── storage.py                 Publica el informe en el storage del laboratorio
├── matematica/                CAPA MATEMÁTICA — no sabe de MCP
│   ├── problema.py            El problema interpretado (campo exacto, parámetro, CI, región)
│   ├── clasificacion.py       Familias del balotario, selección del método, los cinco temas
│   ├── sistemas_conocidos.py  Lorenz, Rössler, Hénon, logístico, tienda; datos del enunciado
│   ├── desarrollo.py          El desarrollo estructurado: secciones, resultados, validaciones
│   ├── primer_orden.py        Separable, lineal, Bernoulli, Riccati
│   ├── segundo_orden.py       Cauchy-Euler y variación de parámetros
│   ├── conservativos.py       Integral primera, separatriz, periodo elíptico
│   ├── sistemas_planos.py     Lineal plano, no lineal plano, ciclo límite
│   ├── analisis_estabilidad.py Equilibrios exactos, linealización, regímenes
│   ├── analisis_bifurcaciones.py Bifurcación 1D, línea de fase, Hopf, homoclínica
│   ├── analisis_caos.py       Mapas 1D: Lyapunov y horizonte, duplicación de periodo, Feigenbaum
│   ├── caos_en_flujos.py      Disipatividad y elipsoide atrapante, teorema del espectro
│   ├── atractores_fractales.py Dimensión fractal, herradura, Hénon, Poincaré, Kaplan-Yorke
│   ├── espectro_lyapunov.py   Espectro de Lyapunov de flujos y mapas (método QR)
│   ├── muestreo.py            Curvas, órbitas y campos para figuras y evidencia numérica
│   ├── expresiones.py         Texto → sympy, sin eval
│   ├── modelo_edos.py         Integración (solve_ivp) y planteamiento numérico
│   └── validacion_solucion.py El portón numérico
├── orquestacion/              FLUJO — no sabe de MCP ni de HTML
│   ├── interpretacion.py      Solicitud → problema; método y pedidos del enunciado
│   ├── contratos.py           Qué se puede pedir y qué se devuelve (pydantic)
│   ├── capacidades.py         El recorrido completo del agente
│   ├── catalogo.py            Carga y valida el balotario
│   └── informe.py             La página HTML de cada análisis
├── visualizacion/             PRESENTACIÓN
│   ├── html.py                Figuras de plotly (declaran su rol, no su color)
│   ├── plantilla.py           Carga la plantilla e inyecta los datos
│   └── plantillas/informe.html La plantilla (KaTeX para las fórmulas)
├── balotario/                 25 problemas en 5 temas + el .tex original
└── test/                      Pruebas locales (no se suben al repositorio)
```

### El recorrido de una pregunta

```text
Usuario (lenguaje natural)
        │
        ▼
Modelo del cliente MCP ── elige la herramienta; pasa el enunciado y los datos
        │
        ▼
server.py ─────────────── frontera MCP: define las herramientas y delega
        │
        ▼
contratos.py ──────────── valida la solicitud; ¿mapa o EDO? si hay duda, pregunta
        │
        ▼
interpretacion.py ─────── PROBLEMA → INTERPRETACIÓN (método y pedidos del enunciado)
        │
        ▼
clasificacion.py ──────── CLASIFICACIÓN → SELECCIÓN DEL MÉTODO (o fuera del proyecto)
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
html.py + informe.py ──── VISUALIZACIÓN → página del análisis en el storage → enlace
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
| `resolver_caos_fractales_y_atractores` | Temas 4 y 5 con solo el enunciado: con o sin ecuación, o nombrando el sistema (Lorenz, Rössler, Hénon, logístico, tienda) |
| `listar_balotario` | Los 25 problemas del grupo, con su ecuación, cómo pedirlos, su alcance y las revisiones |
| `ping` | Revisión del código, los cinco temas e inventario de familias |

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
| 2-ciclo iterado, $r_n$ por Newton | Los umbrales exactos de 4.2 y la estimación de 4.3 frente al mapa iterado |
| Liouville, Gronwall | $\det\Phi_t=e^{(\nabla\cdot f)t}$ integrando la variacional; trayectorias reales contra la cota del elipsoide (4.4) |
| $\sum\lambda_i$ vs. $\langle\nabla\cdot f\rangle$ | El espectro QR sobre la misma órbita (4.5, 5.5) |
| Conteo de cajas, puntos periódicos | El fractal construido (5.1); los $2^n$ puntos de periodo $n$ de la herradura resueltos uno a uno (5.2) |
| $T\circ T^{-1}$, sección delgada | El inverso de Hénon por composición (5.3); la sección cae sobre una curva y el mapa de retorno reproduce $\lambda_1$ (5.4) |

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

Por eso cada análisis compone su página y `storage.py` la sube al SeaweedFS del
laboratorio con un nombre aleatorio (`uuid`), igual que el piloto sube cada
imagen. La respuesta trae la URL en `visualizacion.informe` y el enlace markdown
en `visualizacion.enlace`. El servidor desplegado lo comparten todos los
usuarios, así que no hay un informe "de la conversación": cada análisis tiene
su propia dirección. Nada se escribe a disco; sin storage (en local) la
herramienta responde igual, sin enlace.

Cada análisis muestra, en este orden: **las gráficas** (las del desarrollo
—solución analítica con la numérica encima, retrato de fase con nulclinas,
variedades y separatrices, diagrama de bifurcación, plano traza-determinante,
telaraña— antes que las numéricas), el enunciado, el desarrollo con las
fórmulas compuestas por KaTeX, las conclusiones y la tabla de verificación. Una
pregunta fuera de los temas del proyecto no publica página: la respuesta trae el
mensaje ordenado por temas.

Un análisis que **no** supera la resolución o la verificación también tiene su
página, con su etapa y su error, y el enlace viaja en `detalles`.

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
| **Quispe Gonzales Mark** | Orquestación, backend y datos | `server.py`, `capacidades.py`, `contratos.py`, `catalogo.py`, `storage.py` |
| **David Alejandro Tejada Ossio** | Visualización | `html.py`, `plantilla.py`, `plantillas/informe.html`, `informe.py` |
| **Illescas Vicente Alexander George** | Verificación | `validacion_solucion.py`, `test/` |

Módulos nuevos de esta etapa, todavía sin responsable asignado:
`problema.py`, `clasificacion.py`, `desarrollo.py`, `primer_orden.py`,
`segundo_orden.py`, `conservativos.py`, `sistemas_planos.py`, `muestreo.py`,
`sistemas_conocidos.py`, `caos_en_flujos.py`, `atractores_fractales.py`,
`espectro_lyapunov.py` y `orquestacion/interpretacion.py`.

## Casos de demostración y pruebas

El balotario es la suite de aceptación: `test/test_balotario.py` pasa cada
problema por el agente tal como lo pediría un cliente y lo compara con la
solución del `.tex` (y, en 2.5, 3.5, 5.3 y 5.4, con la corrección documentada).
Los de los Temas 4 y 5 se le pasan con solo su enunciado. Las pruebas de cada
tema (`test_tema1.py` … `test_tema5.py`) repiten cada familia con ejercicios
equivalentes de otros datos y comprueban los resultados intermedios del
procedimiento.

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
| 4.2 Mapa logístico | $x_2^*=1-1/r$, $f'(x_2^*)=2-r$, $\Delta=r^2(r-3)(r+1)$, $(f^2)'=-r^2+2r+4$, $r_1=3$, $r_2=1+\sqrt6$ |
| 4.3 Feigenbaum | $r_\infty\approx3.57199$ frente a $3.56995$ numérico (0.057 %), $r_3\approx3.54576$ |
| 4.4 Lorenz | $\nabla\cdot f=-(\sigma+1+b)$, $V=rx^2+\sigma y^2+\sigma(z-2r)^2$, $\dot V=-2\sigma(Q-br^2)$, $V^*=2br^2/\kappa$ |
| 4.5 Espectro | Lorenz $\approx(0.91,0,-14.58)$ y Rössler $\approx(0.07,0,-5.39)$, $\sum\lambda_i=\langle\nabla\cdot f\rangle$ |
| 5.1 Cantor | $N(3^{-n})=2^n$ exacto, $D_0=\ln2/\ln3$, conteo de cajas $\approx0.64$ |
| 5.2 Herradura | $2^n$ puntos de periodo $n$ ($n\le8$), $D_0=2\ln2/\ln3$, $h_{top}=\ln2$ |
| 5.3 Hénon | $\det DT=-b$, $T^{-1}=(y/b,\ x-1+ay^2/b^2)$, sillas en $x\approx0.6314$ y $-1.1314$ |
| 5.4 Rössler | Sección $y=0,\ \dot y<0$, mapa de retorno unimodal (máximo en $u\approx5.78$), $e^{\lambda_3T}\sim10^{-14}$ |
| 5.5 Kaplan-Yorke | $\sum\lambda_i=-41/3$, $k=2$, $D_L\approx2.0621$ |

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s test -t .       # pruebas locales
claude mcp add --transport http edos-grupo09 \
  https://rac-unmsm.vekthos.org/grupo09/grupo09_proyecto01_edos-lineales-no-lineales-y-retrato-de-fase/mcp
```

## Qué entrega el agente

1. La clasificación del problema y el método aplicado, con el motivo.
2. El desarrollo matemático completo (`desarrollo.secciones`) y sus resultados
   con nombre.
3. La solución numérica, si hubo condición inicial, contrastada con la
   analítica.
4. El bloque de verificación completo, con lo medido y el umbral de cada prueba.
5. El enlace al informe, donde todo lo anterior aparece dibujado y legible.
6. Lo que se pidió y está **fuera del alcance del proyecto**, dicho como tal y
   con los temas que sí abarca.

El punto 6 no es una carencia del entregable: es parte de él. Un agente que
calla lo que no sabe hacer es menos útil que uno que lo declara, porque obliga a
desconfiar de todo lo demás.
