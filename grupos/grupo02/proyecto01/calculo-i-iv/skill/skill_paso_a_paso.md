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
   pasos intermedios verificados. En la práctica, eso significa: elegir la
   función `calculo<N>_<tema>` que resuelve el punto exacto del ejercicio, y
   si ninguna encaja del todo, usar la tool base más cercana
   (`calcular_derivada`, `calcular_integral`, `calcular_gradiente`) Y ADEMÁS
   invocar a mano las tools `calculo<N>_*` necesarias para las etapas
   intermedias, en vez de pedir un "paso a paso" a una sola tool.
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
*Error común:* [si aplica, qué suelen confundir los estudiantes aquí]

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
sino en cómo se comunica: aquí se invoca a **más de una tool por ejercicio**, una
por etapa, en vez de pedirle a una sola el resultado completo. Eso es lo que
permite explicar paso a paso sin inventar las etapas intermedias.

## 6. Manejo de errores

- Si el usuario comete un error conceptual en su planteamiento previo, se
  corrige con tacto, explicando el porqué del error antes de mostrar lo
  correcto (nunca solo decir "está mal").
- Si la tool reporta que el ejercicio no tiene solución (ej. límite no existe,
  integral diverge), explicar el motivo matemático de forma comprensible,
  no solo reportar el error técnico.

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
*Error común:* Elegir u = e^x haría que el proceso se complique en vez
de simplificarse.

**Paso 2: Aplicar la fórmula de integración por partes**
...
```