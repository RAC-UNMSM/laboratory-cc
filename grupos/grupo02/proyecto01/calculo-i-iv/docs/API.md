# Contrato de la API

MCP Streamable HTTP en `/mcp`. Cinco tools, tres prompts y un recurso. Argumentos
JSON, nunca código Python. `resolver(problema, modo)` admite `examen` (por defecto)
o `paso_a_paso`. El segundo conserva etapas del motor; no es una traza detallada
del algoritmo interno de SymPy. Esquema exacto: [problem.schema.json](problem.schema.json).
Los campos adicionales y tipos incorrectos se rechazan.

## Gramática

Expresiones como cadenas: `2*x`, `sin(x)`, `x**2` o `x^2`, `1/3`, `pi/2`.
Variables reales `x,y,z,t,u,v`, restringidas por cada herramienta. Constantes
`pi`, `E`. Funciones de un argumento: `sin`, `cos`, `tan`, `asin`, `acos`,
`atan`, `sinh`, `cosh`, `tanh`, `exp`, `log`, `sqrt`, `Abs`.
`oo` y `-oo` solo donde se permiten límites infinitos. Multiplicación explícita;
no se admiten `2x`, LaTeX, multiplicación implícita, atributos, indexación,
funciones Python, comparaciones, listas dentro de expresiones ni código.
Decimales escritos se convierten a racionales exactos.

Límites por expresión: 512 caracteres, 128 nodos AST, 24 niveles, constantes
numéricas de valor absoluto hasta 10^12, exponentes numéricos hasta 100 en valor
absoluto. Aun dentro de esos límites una expresión puede exceder los recursos.

## Operaciones de resolver

Todos los ejemplos omiten `modo`. En campos univariados `variable` vale `x`
por defecto. Para vectores espaciales se usa el orden x,y,z; curvas usan t;
superficies usan u,v.

| Operación | Campos específicos | Alcance |
|---|---|---|
| `limite` | expresion, punto, variable?, direccion? | `ambos`, `+` o `-`; compara laterales |
| `continuidad` | expresion, punto, variable? | Punto finito; conserva exclusiones sintácticas de denominadores |
| `derivada` | expresion, variable?, orden? | Orden entero 1–6 |
| `extremos` | expresion, inferior, superior, variable? | Polinomio en intervalo cerrado finito; evalúa críticos y extremos |
| `integral` | expresion, variable?, inferior?, superior? | Primitiva o integral definida; ambos límites o ninguno |
| `area` | expresion, inferior, superior, variable? | Integral de valor absoluto entre gráfica y eje |
| `longitud_arco` | mismos campos que area | Gráfica y=f(x); integral de sqrt(1+f'²) |
| `volumen_revolucion` | mismos campos que area | Discos alrededor del eje de la variable, π∫f² |
| `gradiente` | expresion, variables | Derivadas parciales en el orden dado |
| `hessiano` | expresion, variables | Matriz de segundas derivadas |
| `direccional` | expresion, variables, punto, direccion | Normaliza vector no nulo; presupone diferenciabilidad |
| `lagrange` | expresion, variables, restriccion | Polinomios, una igualdad g=0; candidatos regulares, sin certificación global |
| `integral_multiple` | expresion, limites | Dos o tres integraciones, de dentro hacia fuera |
| `divergencia` | campo | Vector de 2 o 3 componentes |
| `rotacional` | campo | Tres componentes |
| `integral_linea` | campo, curva, inferior, superior | Integral de trabajo F(r(t))·r'(t), 2D o 3D |
| `flujo_superficie` | campo, superficie, limites | F(r)·(r_u × r_v), sin normalizar la normal |
| `green` | campo, limites | Lado de área ∫∫(Q_x−P_y), frontera positiva supuesta |
| `stokes` | campo, superficie, limites | Lado superficial del rotacional, orientación r_u × r_v |
| `gauss` | campo, limites | Lado volumétrico de la divergencia, normal exterior supuesta |

Una frontera tiene forma `{"variable":"y","inferior":"0","superior":"x"}`.
Solo puede depender de variables integradas después. No repita variables.
En superficies el par de variables debe ser u,v; Green usa x,y; Gauss x,y,z.
Integrales definidas e iteradas admiten orientación por límites invertidos.
Las aplicaciones geométricas y curvas requieren extremos crecientes; para
invertir orientación de curva cambie la parametrización.

## Respuestas

- `calculado`: resultado simbólico calculado; no certifica hipótesis externas.
- `no_finito`: resultado infinito, no un número real finito.
- `indefinido`: resultado con valores indefinidos.
- `no_existe`: límites laterales incompatibles.
- `no_resuelto`: persiste un operador simbólico o el algoritmo no lo resuelve.
- `candidatos`: salida de Lagrange que aún requiere clasificación.
- `error`: revisar `codigo` (`entrada`, `tiempo`, `recursos`, `ocupado`, `interno`).

En resultados ordinarios: `exacto`, `latex`, `decimal` (cadena de aproximación
o null), `observaciones`; `pasos` solo en modo paso_a_paso. Matrices se devuelven
como representación simbólica y LaTeX. Primitivas incluyen
`constante_integracion: "C"`; no se debe omitir +C en una solución general.
La verificación de una primitiva no certifica todas sus ramas o intervalos.

Los errores de esquema se expresan como errores MCP del SDK; errores del motor
se devuelven en el campo `estado`. Un cliente debe revisar ambos, no solo HTTP 200.
Una integral indefinida no expresa automáticamente dominio ni rama real completa.
Singularidades interiores finitas en integrales numéricas se separan, sin
interpretar por defecto el valor principal de Cauchy. No se garantiza detección
de toda divergencia en dominios paramétricos ni validez de Fubini.

## Tutor y gráficos

`leccion(tema,nivel)` acepta `desde_cero` o `avanzado`. Temas: limites,
derivadas, integrales, gradiente, integrales_multiples, lagrange, green, stokes,
gauss. `verificar_respuesta(tema,respuesta)` evalúa el ejercicio fijo de esa
lección, no ejercicios arbitrarios ni demostraciones. No mantiene intentos,
notas ni historial; el cliente conserva el progreso.

`graficar(expresion,inferior,superior,variable_nombre="x")` admite funciones
reales continuas sobre un intervalo finito. Devuelve `TextContent` y
`ImageContent` PNG; URL opcional. No envía imágenes a terceros. El muestreo de
600 puntos puede no captar oscilaciones rápidas; no demuestra propiedades.
No implementa gráficos 3D ni gráficos automáticos para cada operación.

Las hipótesis de regularidad, topología y orientación de Green, Stokes y Gauss
requieren revisión explícita. Calcular uno de sus lados no prueba el teorema
para cualquier entrada. El alcance no incluye «cualquier ejercicio de cálculo».
