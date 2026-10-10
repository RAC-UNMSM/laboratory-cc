# Skill: Resolutor de Examen Formal

**Módulo:** Apartado 1 — Resolutor de Ejercicios Prácticos
**Opción:** A — Respuesta Formal de Examen
**Cursos cubiertos:** Cálculo I, II, III, IV

## 1. Propósito

Esta skill se activa cuando el usuario pide la resolución de un ejercicio de cálculo
"como si fuera examen": quiere el procedimiento correcto, riguroso y directo, sin
rodeos pedagógicos. El resultado debe parecerse a lo que un profesor esperaría ver
en la hoja de respuestas de una evaluación presencial.

## 2. Cuándo se activa

- El usuario selecciona explícitamente el modo "Examen" / "Formal" en el Apartado 1.
- El usuario usa frases como: "resuélvelo como en un examen", "solo dame el
  procedimiento formal", "necesito la respuesta rápida y rigurosa".
- Por defecto, si el usuario no especifica modalidad y pide "resolver" un ejercicio
  puntual (no una explicación), se asume este modo A.

## 3. Flujo de trabajo obligatorio

1. **Identificar el tipo de problema** (límite, derivada, integral simple/doble/
   triple, campo vectorial, optimización, etc.) y el curso al que pertenece.
2. **Delegar el cálculo exacto a la tool de Python correspondiente** (SymPy/NumPy)
   según la tabla de la sección 5. Nunca inventar ni aproximar un resultado
   numérico o simbólico "de memoria": el LLM solo formatea y explica, la tool
   calcula. Las expresiones se pasan a las tools en sintaxis SymPy (`x**2`,
   no `x^2`; `sin`, `cos`, `log`, `sqrt`, no `sen` ni `ln`).
3. **Leer el resultado de la tool.** Toda tool devuelve un diccionario con el
   campo `estado`: éxito es `"exito"` (o `"ok"`, que es lo que devuelve
   `calculo1.py`); resultado incompleto es `"parcial"` (o `"no_determinado"`);
   fallo es `"error"`. En éxito, el diccionario trae el resultado y, **solo si
   la tool los entrega**, pasos y condiciones de validez (dominio,
   convergencia). Si la tool devuelve LaTeX (campo `latex`), usarlo tal cual
   en vez de reescribirlo. Si la tool tiene parámetro `modo` (las de
   `calculo1.py`), llamarla con `modo="examen"`, que devuelve solo el paso
   final. Para resultados incompletos o errores, ver la sección 7.
4. **Redactar la respuesta en el formato de salida** de la sección 4. Los pasos
   del desarrollo salen de lo que devolvió la tool. Si la tool solo entregó el
   resultado final, el desarrollo se reconstruye con pasos que se puedan
   respaldar con llamadas adicionales a las tools (por ejemplo, derivar `u`
   o integrar `dv`), nunca con pasos supuestos.

## 4. Formato de salida (obligatorio)

```markdown
### Solución

**Planteamiento:**
[Enunciado reformulado + método a aplicar, 1-2 líneas máximo]

**Desarrollo:**
1. [Paso algebraico clave en LaTeX, sin explicaciones largas]
2. [Paso algebraico clave en LaTeX]
3. ...

**Teorema(s)/Propiedad(es) aplicada(s):** [nombre exacto, ej. "Teorema de Green",
"Regla de la cadena", "Criterio de la segunda derivada"]

**Respuesta final:**
> $$ [resultado en LaTeX] $$
```

### Reglas de formato

- Toda expresión matemática va en LaTeX (`$...$` para inline, `$$...$$` para
  bloque).
- Los pasos algebraicos se **resumen**: máximo 4-7 líneas de desarrollo, sin
  explicar el "por qué" de cada propiedad (eso es trabajo de `skill_paso_a_paso.md`).
- El resultado final siempre va destacado (bloque cita o negrita) y al final del
  mensaje.
- Si el ejercicio tiene condiciones de validez (dominio, convergencia, continuidad
  requerida), se mencionan en una línea aparte, nunca se omiten.
- No se agregan comentarios motivacionales, ni "¡buen trabajo!", ni relleno.

## 5. Mapeo de ejercicios a tools (`tools/`)

`tools/` tiene **un archivo por persona**, y cada archivo expone sus funciones
como tools MCP con el prefijo de su módulo. Para un ejercicio de Cálculo I, la
tool es `calculo1_<tema>`.

| Tipo de ejercicio                         | Tool (prefijo)  | Módulo          |
|-------------------------------------------|-----------------|-----------------|
| Límites, continuidad, asíntotas            | `calculo1_*`    | `calculo1.py`   |
| Derivadas, optimización, máx/mín           | `calculo1_*`    | `calculo1.py`   |
| Antiderivadas, técnicas de integración      | `calculo2_*`    | `calculo2.py`   |
| Áreas, volúmenes de revolución, long. arco | `calculo2_*`    | `calculo2.py`   |
| Derivadas parciales, gradiente, Lagrange   | `calculo3_*`    | `calculo3.py`   |
| Geometría en R³, superficies                | `calculo3_*`    | `calculo3.py`   |
| Integrales dobles/triples, cambio de coord. | `calculo4_*`    | `calculo4.py`   |
| Campos vectoriales, Green, Stokes, Gauss    | `calculo4_*`    | `calculo4.py`   |

### Tools base

El servidor trae 5 tools base que funcionan siempre, incluso antes de que
existan los módulos:

- Cuatro de cálculo: `calcular_derivada`, `calcular_integral`,
  `calcular_gradiente` y `verificar_respuesta`.
- Una de diagnóstico: `estado_del_servidor`. No sirve para resolver
  ejercicios; solo informa qué módulos están cargados.

### Tools de los módulos (estado actual)

Cada tool se llama `<modulo>_<funcion>`. Los parámetros listados son los
principales; el resto está en el esquema de cada tool.

**`calculo1.py` (Cálculo I).** Todas tienen el parámetro `modo`
(`"examen"` o `"paso_a_paso"`) y devuelven el resultado dentro de `datos`
(con `exacto` y `latex`) más la lista `pasos`. Los ángulos van en radianes.

- `calculo1_calcular_limite(expresion, punto, variable, direccion)`:
  `direccion` es `"bilateral"`, `"+"` o `"-"`.
- `calculo1_analizar_continuidad(expresion, punto, variable)`
- `calculo1_analizar_asintotas(expresion, variable)`: solo funciones racionales.
- `calculo1_calcular_derivada(expresion, variable, orden)`: `orden` de 1 a 6.
- `calculo1_derivada_implicita(ecuacion, variable, dependiente)`
- `calculo1_recta_tangente(expresion, punto, variable)`
- `calculo1_optimizar_polinomio(expresion, inicio, fin)`: polinomios de grado
  ≤ 6 con coeficientes y extremos racionales.
- `calculo1_verificar_derivada(expresion, respuesta, variable)`: ver la skill
  del tutor.

No cubre funciones por tramos, L'Hôpital ni los teoremas de Rolle y del valor
medio.

**`calculo4.py` (Cálculo IV).** No tienen parámetro `modo`: devuelven el
resultado final, no una lista de pasos.

- `calculo4_parametrizacion_curva(x, y, z, parametro, inicio, fin, campo)`
- `calculo4_integral_linea(campo, curva_x, curva_y, curva_z, parametro, inicio, fin)`
- `calculo4_integral_doble(expresion, ..., límites, cambio_x, cambio_y)`:
  región rectangular, con Jacobiano opcional.
- `calculo4_green(P, Q, límites)`: solo rectángulos.
- `calculo4_integrales_triples_superficie(densidad, límites, superficie_z, ...)`
- `calculo4_teoremas_integrales_vectoriales(campo, límites)`: divergencia,
  rotacional y Gauss, solo en cuboides.

No hay tool para Stokes ni para regiones que no sean rectángulos o cuboides.

**`calculo2.py` (Cálculo II).** Integración indefinida, definida y aplicaciones.

- `calculo2_calcular_integral_indefinida(expresion, variable, modo)`: primitiva simbólica inmediata o por partes.
- `calculo2_tecnicas_avanzadas_integracion(expresion, variable, tecnica, modo)`: fracciones parciales, sustitución trigonométrica.
- `calculo2_riemann_y_teorema_fundamental(expresion, a_str, b_str, n_particiones, regla_riemann, variable, modo)`: Teorema Fundamental y sumas de Riemann.
- `calculo2_aplicaciones_geometricas(tipo, f_str, g_str, a_str, b_str, eje_giro, variable, modo)`: áreas entre curvas, volúmenes y longitud de arco.
- `calculo2_centro_masa_e_integracion_num(operacion_tipo, expresion, a_str, b_str, g_str, n_tramos, variable, modo)`: centroides y aproximaciones numéricas.
- `calculo2_integrales_impropias_gamma_beta(expresion, a_str, b_str, variable, modo)`: convergencia de impropias, Gamma y Beta.

**`calculo3.py` (Cálculo III).** Geometría en R³ y cálculo diferencial multivariable.

- `calculo3_geometria_analitica_r3(u_str, v_str)`: producto escalar y cruz en R³.
- `calculo3_superficies(ecuacion_str, variables)`: superficies de nivel y vector normal / gradiente.
- `calculo3_frenet_serret_curvatura_torsion(r_str, t_var)`: triedro T, N, B, curvatura y torsión.
- `calculo3_derivadas_parciales_gradiente(expr_str, variables)`: derivadas parciales y gradiente multivariable.
- `calculo3_plano_tangente(expr_str, x0, y0)`: plano tangente y recta normal a superficies.
- `calculo3_optimizacion_lagrange_hessiano(expr_str, variables, restriccion)`: matriz Hessiana y multiplicadores de Lagrange.

## 6. Si el módulo no está disponible

Los módulos `calculo1.py` … `calculo4.py` se cargan al arrancar el servidor y
pueden faltar. Si la tool `calculo<N>_*` que corresponde no aparece entre las
tools disponibles:

1. Llamar a `estado_del_servidor` para confirmar en `modulos_faltantes` que
   el módulo no está cargado.
2. Usar la tool base más cercana al ejercicio (`calcular_derivada`,
   `calcular_integral` o `calcular_gradiente`).
3. Si ninguna tool cubre el ejercicio (o este sale de los límites de la
   tool, por ejemplo una región no rectangular en `calculo4.py`), decirlo en una línea
   ("Este tipo de ejercicio aún no tiene motor de cálculo en el servidor, por
   lo que el resultado no puede verificarse") y entregar solo el
   **Planteamiento** y el método a seguir. **Nunca** completar el cálculo de
   memoria.

## 7. Manejo de errores

- Si la tool devuelve `estado: "parcial"` o `"no_determinado"` (por ejemplo, `calcular_integral`
  cuando SymPy no resuelve la integral completa), reportar solo lo que se
  calculó y decir con claridad que el resto no pudo resolverse. No completar
  el resultado de memoria.
- Si la tool devuelve `estado: "error"`, leer el campo `mensaje` y reportarlo
  de forma directa y formal (ejercicio mal planteado, dominio inválido,
  integral divergente):
  > "La integral no converge en el intervalo dado. Verifique los límites de
  > integración."
- Nunca "arreglar" el enunciado del usuario sin avisar. Si hay ambigüedad
  (ej. falta un límite de integración), pedir la aclaración puntual antes de
  llamar a la tool.

## 8. Ejemplo breve

**Entrada del usuario:** "Modo examen: resuelve ∫x·e^x dx"

**Salida esperada:**

```markdown
### Solución

**Planteamiento:** Integración por partes con u = x, dv = e^x dx.

**Desarrollo:**
1. $u = x \Rightarrow du = dx$
2. $dv = e^x dx \Rightarrow v = e^x$
3. $\int x e^x dx = x e^x - \int e^x dx$

**Teorema(s)/Propiedad(es) aplicada(s):** Integración por partes.

**Respuesta final:**
> $$ \int x e^x \, dx = x e^x - e^x + C $$
```