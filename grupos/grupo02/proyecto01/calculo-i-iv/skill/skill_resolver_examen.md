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
   calcula.
3. **Recibir el resultado estructurado de la tool** (pasos intermedios clave,
   resultado final, dominio/condiciones de validez si aplica).
4. **Redactar la respuesta en el formato de salida** de la sección 4.

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
como tools MCP con el prefijo de su módulo. Para exercise de Cálculo I, la tool
es `calculo1_algo`.

| Tipo de ejercicio                        | Tool (prefijo)     | Módulo          |
|------------------------------------------|--------------------|-----------------|
| Límites, continuidad, asíntotas           | `calculo1_*`       | `calculo1.py`   |
| Derivadas, optimización, máx/mín          | `calculo1_*`       | `calculo1.py`   |
| Antiderivadas, técnicas de integración     | `calculo2_*`       | `calculo2.py`   |
| Áreas, volúmenes de revolución, long. arco| `calculo2_*`       | `calculo2.py`   |
| Derivadas parciales, gradiente, Lagrange  | `calculo3_*`       | `calculo3.py`   |
| Geometría en R³, superficies               | `calculo3_*`       | `calculo3.py`   |
| Integrales dobles/triples, cambio de coord.| `calculo4_*`      | `calculo4.py`   |
| Campos vectoriales, Green, Stokes, Gauss   | `calculo4_*`       | `calculo4.py`   |

Además, el servidor trae 4 tools base que funcionan siempre, incluso antes de
que existan los módulos: `calcular_derivada`, `calcular_integral`,
`calcular_gradiente` y `verificar_respuesta`. Si el ejercicio cae en algo que
ningún módulo cubre todavía, se usa la que más se le acerque.

## 6. Manejo de errores

- Si la tool devuelve un error (ejercicio mal planteado, dominio inválido,
  integral divergente), reportarlo de forma directa y formal:
  > "La integral no converge en el intervalo dado. Verifique los límites de
  > integración."
- Nunca "arreglar" el enunciado del usuario sin avisar. Si hay ambigüedad
  (ej. falta un límite de integración), pedir la aclaración puntual antes de
  llamar a la tool.

## 7. Ejemplo breve

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