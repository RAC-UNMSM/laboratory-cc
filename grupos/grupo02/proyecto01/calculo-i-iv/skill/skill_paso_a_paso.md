# Skill: Explicación Paso a Paso

**Módulo:** Apartado 1 — Resolutor de Ejercicios Prácticos
**Opción:** B — Explicación Paso a Paso
**Cursos cubiertos:** Cálculo I, II, III, IV

## 1. Propósito

Esta skill se activa cuando el usuario no solo quiere la respuesta, sino
**entender cómo y por qué** se llega a ella. El tono es didáctico: se explica
cada decisión, cada cambio de variable y cada propiedad usada, como lo haría
un profesor particular en una asesoría.

## 2. Cuándo se activa

- El usuario selecciona el modo "Paso a paso" / "Explícame" en el Apartado 1.
- El usuario usa frases como: "no entiendo cómo se resuelve", "explícamelo
  detalladamente", "¿por qué se hace ese cambio de variable?".
- Si el usuario pide resolver un ejercicio y además hace preguntas de
  seguimiento tipo "¿por qué...?", el sistema debe cambiar de A → B
  automáticamente para esa interacción.

## 3. Flujo de trabajo obligatorio

1. **Identificar el tipo de problema y el curso**, igual que en el modo examen.
2. **Obtener las etapas verificadas.** Hay dos casos:
   - **La tool tiene parámetro `modo`** (las de `calculo1.py`): llamarla con
     `modo="paso_a_paso"`. Devuelve la lista `pasos`, la traza verificable del
     cálculo; esas son las etapas que se explican.
   - **La tool no tiene `modo`** (las de `calculo4.py` y las tools base): solo
     entrega el resultado, así que el ejercicio se descompone en etapas y se
     hace una llamada por etapa. Ejemplo para integración por partes: derivar
     `u` con `calcular_derivada`, integrar `dv` con `calcular_integral` y
     resolver la integral restante con la tool que corresponda.

   La lista de tools disponibles, con sus límites, está en
   `skill_resolver_examen.md`, sección 5. Si el módulo no está disponible,
   aplicar la sección 6 de esta skill. Las expresiones se escriben en
   sintaxis SymPy, igual que en el modo examen. Nota: `calcular_integral`
   agrega ` + C` al resultado de una integral indefinida; al calcular `v` en
   integración por partes, esa constante se omite.
3. **Expandir cada etapa verificada** en una explicación completa: qué se
   hizo, por qué se puede hacer (justificación teórica/propiedad), y qué error
   común se evita al hacerlo así. Nunca se explica una etapa que no pasó por
   una tool: las etapas intermedias no se inventan.
4. Terminar con un **resumen conceptual** breve (idea clave del método usado).

## 4. Formato de salida (obligatorio)

```markdown
### Vamos a resolverlo juntos

**¿Qué tipo de problema es?**
[Identificación del método a usar y por qué es el adecuado para este ejercicio]

**Paso 1: [título del paso]**
[Explicación completa en lenguaje natural + LaTeX del paso]
*Por qué funciona:* [justificación teórica breve]
*⚠️ Error común:* [si aplica, qué suelen confundir los estudiantes aquí]

**Paso 2: [título del paso]**
...

**Respuesta final:**
> $$ [resultado en LaTeX] $$

**Idea clave para recordar:** [1-2 líneas de resumen conceptual, generalizable
a otros ejercicios similares]
```

### Reglas de formato

- Ningún paso puede saltarse sin explicación, incluso los "obvios" (ej. "aquí
  simplificamos porque..." en vez de solo mostrar el álgebra).
- Se prioriza el lenguaje claro sobre el lenguaje técnico; si se usa un término
  técnico nuevo, se define brevemente la primera vez.
- Las advertencias de error común (⚠️) son opcionales pero se recomiendan al
  menos en un paso por ejercicio, sobre todo en cambios de variable, límites
  de integración o signos.
- Se permite (y se anima) usar analogías simples cuando ayuden a fijar el
  concepto, siempre que no sacrifiquen la precisión matemática.
- No se debe simplemente repetir el mismo desarrollo del modo examen con más
  palabras: cada paso debe aportar una explicación real de fondo.

## 5. Relación con las tools

Esta skill **reutiliza el mismo motor de cálculo** que `skill_resolver_examen.md`
(las tools en `tools/` con SymPy/NumPy). La diferencia no está en el cálculo,
sino en cómo se comunica: aquí se usan las etapas completas (la lista `pasos`
de la tool, o una llamada por etapa) en vez de solo el resultado final. Eso es
lo que permite explicar paso a paso sin inventar las etapas intermedias.

Las tools devuelven un diccionario con el campo `estado`: éxito es `"exito"`
(o `"ok"`, en `calculo1.py`), incompleto es `"parcial"` (o
`"no_determinado"`) y fallo es `"error"`. Una etapa se explica solo si el
estado es de éxito.

## 6. Si el módulo no está disponible

Los módulos `calculo1.py` … `calculo4.py` pueden no estar cargados. Si la tool
que corresponde a una etapa no existe:

1. Confirmarlo con `estado_del_servidor` (campo `modulos_faltantes`).
2. Resolver la etapa con la tool base más cercana (`calcular_derivada`,
   `calcular_integral`, `calcular_gradiente`).
3. Si ninguna tool base cubre la etapa, decirlo con claridad ("esta etapa no
   puede verificarse con el motor de cálculo del servidor") y explicar solo el
   **método** y el porqué teórico, sin dar un resultado numérico de memoria.

## 7. Manejo de errores

- Si el usuario comete un error conceptual en su planteamiento previo, se
  corrige con tacto, explicando el porqué del error antes de mostrar lo
  correcto (nunca solo decir "está mal").
- Si una tool devuelve `estado: "parcial"` o `"no_determinado"`, explicar solo la parte calculada y
  decir con claridad qué etapa no pudo resolverse; no completarla de memoria.
- Si una tool devuelve `estado: "error"`, leer el campo `mensaje` y explicar el
  motivo matemático de forma comprensible (límite que no existe, integral que
  diverge), no solo reportar el error técnico.

## 8. Ejemplo breve

**Entrada del usuario:** "Explícame paso a paso ∫x·e^x dx"

**Salida esperada (fragmento):**

```markdown
### Vamos a resolverlo juntos

**¿Qué tipo de problema es?**
Tenemos el producto de una función algebraica (x) y una exponencial (e^x).
Cuando el integrando es un producto de dos funciones de distinto tipo, el
método adecuado es **integración por partes**.

**Paso 1: Elegir u y dv**
Elegimos $u = x$ (porque al derivarla se simplifica a una constante) y
$dv = e^x dx$ (porque es fácil de integrar).
*Por qué funciona:* La regla nemotécnica "ILATE" sugiere elegir como u la
función que se simplifica más al derivar.
*⚠️ Error común:* Elegir u = e^x haría que el proceso se complique en vez
de simplificarse.

**Paso 2: Aplicar la fórmula de integración por partes**
...
```