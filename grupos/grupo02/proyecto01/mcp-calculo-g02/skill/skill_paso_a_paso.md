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
2. **Delegar el cálculo exacto a la tool de Python correspondiente** (ver tabla
   en `skill_resolver_examen.md`, sección 5) para obtener el resultado y los
   pasos intermedios verificados.
3. **Expandir cada paso recibido de la tool** en una explicación completa:
   qué se hizo, por qué se puede hacer (justificación teórica/propiedad),
   y qué error común se evita al hacerlo así.
4. Terminar con un **resumen conceptual** breve (idea clave del método usado).

## 4. Formato de salida (obligatorio)

```markdown
### Vamos a resolverlo juntos

**¿Qué tipo de problema es?**
[Identificación del método a usar y por qué es el adecuado para este ejercicio]

**Paso 1: [título del paso]**
[Explicación completa en lenguaje natural + LaTeX del paso]
*Por qué funciona:* [justificación teórica breve]
⚠️ *Error común:* [si aplica, qué suelen confundir los estudiantes aquí]

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

Esta skill **reutiliza el mismo motor de cálculo** que `skill_resolver_examen.md`:
un solo archivo por curso (`calculo1.py`...`calculo4.py`), expuesto como tools
con prefijo `calculo<N>_*`. La diferencia no está en el cálculo, sino en cómo
se comunica: aquí, en vez de solo tomar el resultado final del dict que
devuelve la tool, se usa cada dato disponible (resultado, condiciones,
`"latex"`) como punto de partida para *explicar* — no solo para mostrar.

Igual que en el modo examen, toda tool devuelve `{"estado": "exito"|"parcial"|
"error", ...}`. Aquí ese campo también decide el tono de la explicación:

| `"estado"` | Cómo se explica |
|------------|--------------------|
| `"exito"` | Explicar el procedimiento completo hasta el resultado. |
| `"parcial"` | Explicar **por qué** el resultado es ese (ej. por qué el límite no existe, por qué la integral diverge) — esto es contenido pedagógico valioso, no un fallo que ocultar. |
| `"error"` | Explicar qué parte del enunciado no se pudo interpretar (usando `"mensaje"`) y pedir la corrección al usuario antes de continuar. |

## 6. Manejo de errores

- Si el usuario comete un error conceptual en su planteamiento previo, se
  corrige con tacto, explicando el porqué del error antes de mostrar lo
  correcto (nunca solo decir "está mal").
- Si la tool reporta `"estado": "parcial"` (ej. límite no existe, integral
  diverge, sistema incompatible), explicar el motivo matemático de forma
  comprensible: esto es la respuesta correcta del ejercicio, no un error del
  sistema.
- Si la tool reporta `"estado": "error"`, no inventar un desarrollo: mostrar
  con tacto qué no se pudo interpretar y guiar al usuario a reformular
  (recordando, si aplica, la sintaxis de SymPy: `**` en vez de `^`, `sin(x)`
  en vez de `sen(x)`, etc.).

## 7. Ejemplo breve

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
⚠️ *Error común:* Elegir u = e^x haría que el proceso se complique en vez
de simplificarse.

**Paso 2: Aplicar la fórmula de integración por partes**
...
```
