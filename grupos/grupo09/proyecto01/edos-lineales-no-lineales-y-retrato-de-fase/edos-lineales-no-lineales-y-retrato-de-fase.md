# Grupo 09 — EDOs lineales y no lineales, retratos de fase, sistemas dinámicos caóticos, atractores extraños y bifurcaciones

**Agente MCP.** El proyecto dejó de ser un programa que se corre en una terminal
y resuelve un problema fijo: es un **servidor MCP** al que un cliente de chat le
hace preguntas en lenguaje natural. El usuario escribe «analiza el oscilador de
Van der Pol con μ = 1 desde (0.5, 0) y clasifica el equilibrio»; el modelo
traduce eso a una llamada a las herramientas del servidor; el servidor calcula,
**verifica** y devuelve datos estructurados; el modelo redacta la explicación a
partir de ellos y le entrega al usuario el enlace al informe.

Esa división es el criterio de diseño de todo lo demás: **el servidor no
interpreta ni redacta, y el modelo no calcula.** Ningún número que el usuario
vea sale de la redacción del modelo; todos salen de un cálculo verificado.

## Objetivo

Resolver y analizar EDOs lineales y no lineales de 1 a 3 variables, estudiando
estabilidad, retratos de fase, sensibilidad a condiciones iniciales, atractores
extraños y bifurcaciones, con resultados **verificables** y reproducibles.

## Formulación

Problemas de valor inicial de la forma

$$
\mathbf{x}'=\mathbf{F}(t,\mathbf{x};\boldsymbol{\theta}),
\qquad \mathbf{x}(t_0)=\mathbf{x}_0,
\qquad t\in[t_0,t_f],
$$

donde $\mathbf{x}$ son las variables de estado, $t$ la variable independiente,
$\boldsymbol{\theta}$ los parámetros y $\mathbf{F}$ el campo vectorial.

El análisis de equilibrios y bifurcaciones exige sistemas autónomos,
$\mathbf{x}'=\mathbf{F}(\mathbf{x};\boldsymbol{\theta})$; el servidor detecta
cuándo no lo son y lo dice en vez de calcular algo sin sentido. Una EDO de orden
$n$ se reduce antes a un sistema de $n$ ecuaciones de primer orden: por ejemplo
$\theta''=-\sin\theta$ se escribe como `ecuaciones=["v", "-sin(theta)"]` con
`variables_estado=["theta", "v"]`.

## Estado real: qué calcula hoy y qué no

Esta tabla es el corazón del documento. El agente **declara** lo que no sabe
hacer en vez de devolver un sustituto con apariencia de respuesta.

| Capacidad | Estado | Qué ocurre si se pide |
| --- | --- | --- |
| Integración numérica con control de error | **Implementado** | RK45, RK23, DOP853, Radau, BDF, LSODA |
| Equilibrios exactos (sympy), Jacobiano, autovalores, clasificación | **Implementado** | Resuelve $\mathbf{F}=\mathbf{0}$ de forma simbólica, no aproximada |
| Verificación independiente de la solución | **Implementado** | Cinco pruebas; si fallan, no hay conclusiones |
| Visualización HTML interactiva e informe de sesión | **Implementado** | Series, línea de fase 1D, retrato de fase 2D, trayectoria 3D |
| Catálogo del balotario (25 problemas, 5 temas) | **Implementado** | Consultable como herramienta |
| Exponente de Lyapunov, Poincaré, cuantificación del caos | **Pendiente** | Devuelve «pendiente de implementación» con el detalle de lo que falta |
| Diagramas de bifurcación y barridos automáticos | **Pendiente** | Se puede llamar varias veces variando el parámetro: cada llamada da los equilibrios exactos de ese valor |
| Resolución analítica (simbólica) | **Pendiente** | Integra numéricamente; sí **verifica** una solución cerrada que el usuario aporte |
| Mapas iterados $x_{n+1}=f(x_n)$ | **Fuera de alcance** | Lo declara: el motor integra EDOs continuas |

Los tres pendientes son *stubs deliberados*: módulos que levantan un error
explícito en vez de devolver números inventados. Un exponente de Lyapunov falso
sería peor que su ausencia, porque el agente lo presentaría como evidencia
calculada.

### La ambigüedad continuo/discreto

$x_{n+1}=r\,x_n(1-x_n)$ y $\mathrm{d}x/\mathrm{d}t=r\,x(1-x)$ se escriben con el
mismo lado derecho: el servidor **no puede distinguirlos** mirando las
ecuaciones. Quien lo sabe es el usuario. Por eso es un campo del contrato
(`tipo_de_sistema`) y no una suposición, y `'no_estoy_seguro'` es una respuesta
válida que hace que el servidor devuelva la pregunta en vez de un número. Importa:
el mapa logístico con $r=3.8$ es caótico, mientras que la EDO continua del mismo
lado derecho converge a un equilibrio. Los problemas 4.1 a 4.3 y 5.3 del
balotario son mapas.

## Arquitectura

Tres capas, sin dependencias hacia arriba. `matematica/` no sabe que existe
`orquestacion/`, y ninguna de las dos sabe que existe MCP: cada pieza se puede
usar y probar por separado.

```text
edos-lineales-no-lineales-y-retrato-de-fase/
├── mcp_server.py              Las 5 herramientas MCP (transporte stdio)
├── storage.py                 Publica el informe en el storage del laboratorio
├── requirements.txt
├── matematica/                CAPA MATEMÁTICA — no sabe de MCP
│   ├── expresiones.py         Texto → función numérica, sin eval
│   ├── datos_validacion.py    Validación de entrada al solver
│   ├── modelo_edos.py         Integración (solve_ivp) · stub de resolución analítica
│   ├── validacion_solucion.py Las cinco verificaciones
│   ├── analisis_estabilidad.py Jacobiano, autovalores, clasificación
│   ├── analisis_caos.py       Stub declarado
│   └── analisis_bifurcaciones.py Stub declarado
├── orquestacion/              FLUJO — no sabe de MCP ni de HTML
│   ├── contratos.py           Qué se puede pedir y qué se devuelve (pydantic)
│   ├── capacidades.py         El recorrido completo del agente
│   ├── catalogo.py            Carga y valida el balotario
│   └── informe.py             Acumula la conversación y publica el informe
├── visualizacion/             PRESENTACIÓN
│   ├── html.py                Figuras de plotly (declaran su rol, no su color)
│   ├── plantilla.py           Carga la plantilla e inyecta los datos
│   └── plantillas/informe.html La plantilla, HTML de verdad
├── balotario/                 25 problemas en 5 temas + el .tex original
└── tests/                     142 pruebas
```

### El recorrido de una pregunta

```text
Usuario (lenguaje natural)
        │
        ▼
Modelo del cliente MCP ── elige la herramienta y arma los argumentos
        │
        ▼
mcp_server.py ─────────── frontera MCP; protege stdout (es el canal JSON-RPC)
        │
        ▼
contratos.py ──────────── valida la solicitud ANTES de tocar el solver
        │                 ¿mapa o EDO? si hay duda, devuelve la pregunta
        ▼
expresiones.py ────────── compila el campo sin eval (3 capas de validación)
        │
        ▼
modelo_edos.py ────────── integra
        │
        ▼
validacion_solucion.py ── PORTÓN: si falla, se detiene sin conclusiones
        │
        ▼
analisis_estabilidad.py ─ equilibrios, Jacobiano, autovalores
        │
        ▼
html.py + informe.py ──── figuras → informe de la sesión → enlace
        │
        ▼
Modelo ── redacta a partir de los datos y entrega el enlace al usuario
```

`capacidades.py` es el único módulo que conoce a todos los demás. **El orden no
es decorativo:** la verificación va antes del análisis, de modo que un resultado
inválido no llegue nunca acompañado de conclusiones.

## Las herramientas MCP

| Herramienta | Para qué |
| --- | --- |
| `resolver_graficar_y_analizar_edo` | Problema de valor inicial: integra, verifica, analiza y dibuja |
| `analizar_equilibrios` | Equilibrios y estabilidad **sin** condición inicial |
| `listar_balotario` | Los 25 problemas del grupo, con su ecuación y su solución esperada |
| `informe` | La dirección del informe de la conversación |
| `nuevo_informe` | Abre uno vacío al empezar un chat |
| `ping` | Inventario exacto de capacidades y pendientes |

`analizar_equilibrios` existe porque «clasifique los equilibrios de
$x'=\mu-x^2$» **no es** un problema de valor inicial: no hay condición inicial
que dar, y exigirla obligaría a integrar una trayectoria que nadie pidió. Es la
forma de los cinco problemas del Tema 3.

## Verificación: el portón del agente

Toda respuesta trae un bloque `verificacion`. Ninguna prueba confía en el
integrador que produjo la solución; cada una la contrasta contra algo externo:

| Prueba | Contra qué contrasta |
| --- | --- |
| `condicion_inicial` | La condición inicial pedida |
| `residuo` | El propio campo vectorial, por diferencias finitas |
| `convergencia` | Una reintegración con tolerancias 100 veces más finas |
| `metodo_alternativo` | Una reintegración con otro integrador |
| `solucion_exacta` | Una solución cerrada, cuando el usuario la aporta |

Dos detalles que distinguen una verificación honesta de una que solo aparenta:

- **El residuo estima su propio error.** La derivada central tiene un error de
  truncamiento $-(h^2/6)\,x'''$ que no dice nada sobre la calidad del
  integrador. La prueba calcula ese error esperado y solo denuncia el residuo
  cuando lo supera por un margen, de modo que el umbral deje de ser un número
  arbitrario.
- **El caos no se confunde con un error.** Dos integraciones correctas de un
  sistema sensible *tienen* que separarse a tiempo largo. Exigir coincidencia
  punto a punto marcaría como inválido el atractor de Lorenz, que es uno de los
  casos de demostración. Por eso el veredicto se decide en una ventana inicial,
  y la separación posterior se reporta como **evidencia de sensibilidad**, no
  como fallo; a tiempo largo la comparación válida es la estadística.

Si la verificación no se supera, el servidor devuelve la etapa que falló y **no
emite conclusiones**. La forma del resultado lo hace imposible: no existe una
respuesta que lleve a la vez un error y un análisis.

## Seguridad de la frontera

`matematica/expresiones.py` recibe texto de un cliente MCP arbitrario. **No usa
`eval`.** Valida en tres capas: léxica (lista blanca de caracteres, `__`
prohibido), de nombres (todo identificador debe ser un símbolo declarado o una
función permitida) y simbólica (tras parsear con sympy se comprueba que no
quedaron símbolos libres ni funciones ajenas).

El informe se publica en una URL pública del laboratorio, así que todo lo que el
cliente controla —título, nombres de variable y de parámetro— se inserta como
texto y nunca como marcado.

## El informe: cómo ve el usuario su trabajo

Un resultado de herramienta MCP es **datos para el modelo**, no algo que la
interfaz dibuje: ningún cliente de chat renderiza el HTML que devuelve una
tool. Mandar el documento dentro de la respuesta no sirve para que el usuario lo
vea y además gasta contexto —medido sobre un Van der Pol, el 75 % de la
respuesta—. Lo que sí funciona es un enlace.

Sin el storage del laboratorio el informe queda en un archivo, y una ruta
`C:\...\informe.html` no se puede abrir con un clic: el navegador no navega a
`file://` desde una página https, y un documento abierto así tampoco puede leer
su JSON vecino. Por eso el agente sirve esa carpeta en `127.0.0.1`, en un puerto
que elige el sistema: el enlace se abre con un clic y la página se actualiza
igual que en el despliegue del laboratorio.

`orquestacion/informe.py` mantiene **un documento por conversación**. Cada
análisis agrega una sección (planteamiento, figuras, equilibrios, tabla de
verificación y pendientes) y el documento se reescribe sobre la **misma**
dirección. El usuario abre el enlace una vez, deja la pestaña abierta, y los
problemas van apareciendo conforme el agente los resuelve.

| Entorno | Dónde queda el informe | Cómo se actualiza |
| --- | --- | --- |
| Contenedor en la red del laboratorio | URL pública, clave estable | Pide el JSON y **agrega** la sección nueva, sin recargar |
| Local por stdio | `informes/`, junto al proyecto, servido en `127.0.0.1` | Igual: pide el JSON y agrega la sección nueva |

El informe enseña **la última pregunta**, no un historial: cada análisis
reemplaza al anterior en la misma dirección, así que una pestaña abierta vale
para toda la conversación y no hay nada que pueda mezclarse entre chats.
Con `EDOS_INFORME_MODO=acumula` las secciones se apilan, la más reciente
arriba; sirve para comparar respuestas entre sí, que es como se estudia una
bifurcación mientras el barrido siga pendiente.

**Una sesión no es un proceso.** El cliente levanta el servidor una vez y lo
mantiene vivo para todas las conversaciones, así que el informe no empieza de
cero por sí solo: el agente llama a `nuevo_informe` al abrir un chat, y hay un
relevo por inactividad como red de seguridad. El informe anterior no se borra,
queda en su archivo fechado.

Un análisis que **no** supera una etapa también entra al informe, con su etapa y
su error. Esconderlo dejaría el documento contando una historia más limpia que
la real.

La plantilla es un `.html` de verdad, separada del Python: los datos entran como
JSON y el render ocurre en el navegador. Las figuras no llevan colores
cocinados; cada traza declara **qué es** y la página le asigna el color desde su
CSS, que es lo que permite que la misma figura se vea bien en claro y en oscuro.
La paleta está validada (banda de luminosidad, croma, separación para daltonismo
y contraste); como el verde y el rojo de estable/inestable quedan en banda de
advertencia, el marcador cambia además de forma: disco, aspa o rombo.

## Integrantes y responsabilidades

| Integrante | Rol | Archivos |
| --- | --- | --- |
| **Yanac Minaya Junior Alberto** | Modelado, resolución y simulación dinámica | `modelo_edos.py`, `analisis_caos.py` |
| **Tisnado Yarleque Christian David** | Estabilidad y bifurcaciones | `analisis_estabilidad.py`, `analisis_bifurcaciones.py` |
| **Quispe Gonzales Mark** | Orquestación, backend y datos | `mcp_server.py`, `capacidades.py`, `contratos.py`, `catalogo.py`, `storage.py` |
| **David Alejandro Tejada Ossio** | Visualización | `html.py`, `plantilla.py`, `plantillas/informe.html`, `informe.py` |
| **Illescas Vicente Alexander George** | Verificación | `validacion_solucion.py`, `tests/` |

## Casos de demostración y pruebas

El balotario funciona como vara de medir: `tests/test_balotario.py` pasa cada
ejercicio por el solver y lo compara con la solución que el `.tex` demuestra.

| Caso | Qué se verifica | Estado |
| --- | --- | --- |
| $x'=-2x$, $x(0)=1$ | Contraste con $x(t)=e^{-2t}$ | Verificado |
| Logístico $x'=rx(1-x/K)$ | Equilibrios $\{0,K\}$ exactos y convergencia a $K$ | Verificado |
| Silla-nodo $x'=\mu-x^2$ | Sin equilibrios si $\mu<0$; ramas $\pm\sqrt{\mu}$ si $\mu>0$ | Verificado |
| Horquilla $x'=\mu x-x^3$ | El origen cambia de estabilidad en $\mu=0$ | Verificado |
| Hopf | Ciclo límite de radio $\sqrt{\mu}$ para $\mu>0$ | Verificado |
| Lorenz | Trayectoria 3D y sensibilidad a condiciones iniciales | Sensibilidad detectada y fechada; **no cuantificada** |

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests          # 142 pruebas
claude mcp add edos-grupo09 -- python mcp_server.py
```

## Qué entrega el agente

1. El problema interpretado y la configuración exacta con que se calculó.
2. La solución numérica, con su malla y sus estados inicial y final.
3. El análisis de estabilidad: equilibrios exactos, Jacobiano, autovalores y
   clasificación.
4. El bloque de verificación completo, con lo medido y el umbral de cada prueba.
5. El enlace al informe, donde todo lo anterior aparece dibujado y legible.
6. Lo que se pidió y **no** está implementado, dicho como tal.

El punto 6 no es una carencia del entregable: es parte de él. Un agente que
calla lo que no sabe hacer es menos útil que uno que lo declara, porque obliga a
desconfiar de todo lo demás.
