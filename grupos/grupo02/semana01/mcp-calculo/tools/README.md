# `tools/` — los motores de cálculo del Grupo 02

Un archivo por persona, un archivo por área. Cada archivo es un módulo de
Python normal con funciones normales: se ejecuta en la terminal sin levantar el
servidor MCP.

> **Lo único que tienes que leer si tienes 2 minutos:** la sección
> [Checklist](#checklist-antes-de-hacer-pr). Son las reglas que tu archivo
> tiene que cumplir para que `server.py` registre tus tools.
>
> **Lo que NO tienes que hacer:** tocar `server.py`. Nunca. El servidor carga
> tus módulos solo al arrancar. Si tu tool no aparece en el cliente MCP, el
> problema está en tu archivo, no en el servidor.

---

## 1. Tu archivo

| Archivo | Integrante | Área | Temas |
|---|---|---|---|
| `calculo1.py` | Saico Cristhian | Cálculo I | funciones reales, límites, continuidad, derivadas |
| `calculo2.py` | Rosales Yhin | Cálculo II | antiderivadas, técnicas, aplicación de la integral |
| `calculo3.py` | Vilcapoma Jefferson | Cálculo III | R³, multivariable, optimización |
| `calculo4.py` | Meza Angel | Cálculo IV | campos vectoriales e integrales múltiples |
| `_plantilla.py` | — | — | copiar → renombrar. **No** se carga como tool |

Los 6 temas exactos de cada área están en la
[sección 6](#6-los-6-temas-de-tu-área).

> **Nota sobre la partición:** un archivo por persona, no uno por tema. Tu
> archivo `calculo1.py` lleva los 6 temas de Cálculo I, aunque sean funciones
> distintas. Es lo que dice la hoja de ruta del grupo, y es lo que está
> reflejado en las tablas de `skill/skill_resolver_examen.md`.

### Cómo se conecta tu archivo al servidor

```
tools/calculo1.py
      │
      │  server.py lo importa al arrancar (importlib) y busca las funciones
      │  públicas definidas en él
      ▼
   función limite_lateral()  ──►  tool MCP "calculo1_limite_lateral"
```

El prefijo `calculo1_` lo pone el servidor automáticamente, tomado del nombre
de tu archivo. Por eso dos personas nunca pueden colisionar con el mismo
nombre de tool.

---

## Checklist (antes de hacer PR)

- [ ] El archivo se llama exactamente `calculo<N>.py` (`calculo1.py`, etc.).
- [ ] Cada función pública tiene **docstring**.
- [ ] Cada parámetro y el retorno tienen **type hint**.
- [ ] Cada función devuelve un **`dict` con la clave `"estado"`**.
- [ ] Ninguna función lanza excepciones: todo va en `try/except`.
- [ ] Los parámetros opcionales usan `str | None = None` (no `str = None`).
- [ ] El bloque `if __name__ == "__main__":` imprime 2 o 3 resultados reales.
- [ ] `python tools/calculo<N>.py` corre sin error en tu terminal.

---

## 2. El contrato, regla por regla

### 2.1 El nombre del archivo

Exactamente `calculo<N>.py`. Es lo único que el servidor usa para encontrar tu
módulo y para nombrar tus tools.

### 2.2 Solo funciones públicas **definidas en tu archivo**

Se registra toda función que no empiece con `_` y que esté definida en tu
archivo. Si haces `from sympy import diff`, `diff` **no** se registra — porque
no la definiste tú. Eso es lo que se quiere: solo se expone lo tuyo.

Si quieres exponer solo algunas funciones, decláralo al final del archivo:

```python
HERRAMIENTAS = ["limite_lateral", "dominio"]   # el resto queda como helper
```

### 2.3 Docstring obligatorio — es documentación para la IA

El docstring **no** es un comentario para humanos: es lo que lee la IA para
saber qué hace tu tool y cómo llamarla. Si el docstring no dice qué sintaxis
espera, la IA no sabe si mandarle `"x^2"` o `"x**2"` y la tool falla.

Un docstring útil dice tres cosas: **qué hace**, **cómo se llama** (parámetros
y tipos) y **qué sintaxis espera**.

```python
def limite_lateral(expresion: str, variable: str = "x", hacia: str = "+") -> dict:
    """Calcula el limite lateral de una funcion en un punto.

    Args:
        expresion: la funcion en sintaxis sympy, ej. "sin(x)/x".
            OJO: `**` para potencia, no `^`.
        variable: nombre de la variable, default "x".
        hacia: "+" (por la derecha) o "-" (por la izquierda).
    """
```

### 2.4 Type hints en todos los parámetros y en el retorno

De ahí sale el *schema* que ve el cliente MCP. Sin type hints la tool se
registra, pero el cliente no sabe qué argumentos puede pasarle.

```python
# mal                                                    # bien
def limite(expresion):         def limite(expresion: str, punto: float = 0.0) -> dict[str, Any]:
```

### 2.5 Devuelve siempre un `dict`, nunca lances excepciones

| `"estado"`   | Cuándo                                                     | Qué incluir                      |
|---|---|---|
| `"exito"`    | Se resolvió.                                               | el resultado                     |
| `"parcial"`  | Se resolvió a medias (sympy no cerró una integral, el límite no existe...). | lo que sí se pudo calcular |
| `"error"`    | No se pudo. Siempre con `"mensaje"`.                       | `"mensaje": str(exc)`            |

**Por qué:** una excepción dentro de una tool MCP no rompe solo esa llamada,
rompe la **sesión completa del cliente**. Devolver `{"estado": "error"}` la
convierte en un resultado que la IA puede leer y explicarle al usuario.

**Ojo con un caso límite:** que un límite no exista, que una serie diverja o que
un sistema sea incompatible **no son errores** — son la respuesta. Devuélvelo
como `"parcial"` con un campo que lo diga (`"existe": False`), no como
`"error"`.

### 2.6 Parámetros opcionales: `str | None = None`

```python
# mal                                    # bien
def integral(expresion, a: str = None):  def integral(expresion: str, a: str | None = None) -> dict[str, Any]:
```

Con pydantic, `a: str = None` lanza error de validación en cuanto el cliente
omite el argumento — y el cliente las omite siempre que son opcionales.

### 2.7 El bloque `__main__` es tu demo

El profesor pide ver las funciones corriendo en la terminal, no solo el código.
`_plantilla.py` ya viene con 4 casos de prueba (un caso normal, uno con
respuesta distinta, uno donde no existe, y uno de entrada inválida). Cámbialos
por los de tu área.

---

## 3. Anatomía de una tool

```python
from __future__ import annotations
from typing import Any
import sympy as sp


def limite_lateral(expresion: str, variable: str = "x", hacia: str = "+") -> dict[str, Any]:
    """<qué hace>                              ← lo lee la IA para elegir la tool
    Args:
        expresion: <sintaxis sympy esperada>  ← lo lee la IA para pasarte los args
    """
    try:
        v = sp.Symbol(variable)
        f = sp.sympify(expresion)
        limite = sp.limit(f, v, 0, dir="+" if hacia == "+" else "-")
        existe = limite not in (sp.oo, -sp.oo, sp.zoo, sp.nan)
        return {
            "estado": "exito" if existe else "parcial",
            "funcion": sp.sstr(f),
            "limite": sp.sstr(limite),
            "existe": bool(existe),
            "latex": sp.latex(limite),        # el cliente lo renderiza bonito
        }
    except Exception as exc:                  # nunca dejes que se escape
        return {"estado": "error", "mensaje": f"{type(exc).__name__}: {exc}"}


if __name__ == "__main__":                   # tu demo de terminal
    print(limite_lateral("sin(x)/x", hacia="+"))
```

Tres cosas que se ven aquí y que conviene no olvidar:

- **`sp.latex(...)` en el resultado.** La IA escribe la respuesta en LaTeX; si
  no le devuelves el LaTeX, la arma ella y puede equivocarse.
- **`sp.sstr(...)` en vez de `str(...)`.** Para expresiones de SymPy, `str` y
  `sstr` no siempre coinciden.
- **`bool(...)` en los flags.** SymPy devuelve objetos, no `bool`; si el
  esquema dice booleano y mandas un objeto, el cliente lo serializa raro.

---

## 4. Referencia rápida: sintaxis de SymPy

Las expresiones entran como **texto en sintaxis de SymPy/Python**, no en
notación matemática. Es el error más común y el que más rompe las tools.

| Quiere decir | Escribir | No escribir |
|---|---|---|
| x al cuadrado | `x**2` | `x^2` — en Python `^` es XOR |
| seno / coseno / tangente | `sin(x)`, `cos(x)`, `tan(x)` | `sen(x)`, `seno(x)` |
| logaritmo natural | `log(x)` | `ln(x)` |
| raíz cuadrada | `sqrt(x)` | `raiz(x)`, `x**(1/2)` |
| pi / e | `pi`, `E` | `3.14159`, `2.71828` |
| división exacta | `1/2` | `0.5` (si buscas exactitud) |
| constante de integración | `+ C` (en el texto) | omitirla |

Si tu tool recibe un texto que podría venir escrito de varias formas, normaliza
al principio. SymPy tiene para eso `sympify`, `parse_expr` y `nsimplify`.

---

## 5. Cómo probarlo

### 5.1 En la terminal (lo que pide el profesor)

```bash
cd grupos/grupo02/semana01/mcp-calculo
python tools/calculo1.py
```

### 5.2 Ver que quedó registrado en el servidor

```bash
python server.py
```

Al arrancar imprime qué módulos cargó. Para el detalle completo, en el cliente
MCP llama a la tool **`estado_del_servidor`**, que devuelve:

```json
{ "modulos_cargados": ["calculo1"], "modulos_faltantes": ["calculo2", "calculo3", "calculo4"] }
```

### 5.3 Con el MCP Inspector (lo más cómodo para probar tools)

```bash
npx @modelcontextprotocol/inspector
# Transport: stdio | Command: python | Args: server.py
```

### 5.4 Los tests de estructura

```bash
python -m unittest discover -s tests -v
```

Verifican que el compose cumpla la política del CI, que los 3 skills existan y
que tus módulos cumplan el contrato. **No necesitan instalar nada** — ni SymPy,
ni el SDK de MCP, ni PyYAML: solo la librería estándar. Corren en 1 segundo.

---

## 6. Los 6 temas de tu área

El detalle completo está en el plan del grupo
(`grupos/grupo02/proyecto01/calculo-i-iv/calculo-i-iv.md`).

> Esa propuesta vive en `proyecto01/` porque ahí es donde el repo pide el `.md`
> del tema. **El código, en cambio, vive en `grupos/grupo02/semana01/mcp-calculo/`**,
> que es la ruta que el CI escanea y por la que se despliega. Son dos carpetas
> distintas a propósito; no las mezcles.

### `calculo1.py` — Cálculo I
1. Relaciones y funciones reales: dominio, rango, gráfica, inversa.
2. Límites: laterales, al infinito, asíntotas.
3. Límites especiales: trigonométricos, exponenciales, logarítmicos.
4. Continuidad y teoremas de discontinuidad.
5. Derivadas: regla de la cadena, implícita, orden superior.
6. Aplicaciones: Rolle, Valor Medio, optimización, L'Hôpital.

### `calculo2.py` — Cálculo II
1. Antiderivada e integral indefinida: inmediatas, cambio de variable, partes.
2. Técnicas avanzadas: fracciones parciales, trigonométrica, Euler, Chebyshev.
3. Sumas de Riemann y Teorema Fundamental del Cálculo.
4. Aplicaciones geométricas: áreas planas, volúmenes de revolución, longitud de arco.
5. Centro de masa e integración numérica: Pappus, trapecio, Simpson.
6. Integrales impropias y funciones Gamma / Beta.

### `calculo3.py` — Cálculo III
1. Geometría analítica en R³: vectores, rectas, planos, distancias.
2. Superficies: cilíndricas, cuádricas, esféricas.
3. Funciones vectoriales: triedro de Frenet-Serret, curvatura, torsión.
4. Cálculo diferencial multivariable: dominio, topología, límites.
5. Derivadas parciales, gradiente, regla de la cadena, plano tangente.
6. Optimización multivariable: Hessiano, multiplicadores de Lagrange.

### `calculo4.py` — Cálculo IV
1. Parametrización de curvas y campos vectoriales.
2. Integrales de línea y campos conservativos: función potencial.
3. Integrales dobles, cambio de variable y Jacobiano.
4. Teorema de Green y superficies.
5. Integrales triples e integrales de superficie.
6. Teoremas integrales vectoriales: Divergencia, Rotacional, Stokes, Gauss.

---

## 7. Troubleshooting

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| Mi tool no aparece en el cliente | La función no es pública, o no está definida en tu archivo (la importaste de otro módulo) | Renómbrala o quítala de las importadas; si es un helper, déjala fuera con `HERRAMIENTAS = [...]` |
| La tool aparece pero el cliente no encuentra los argumentos | Faltan type hints en los parámetros | Anótalos todos |
| `estado: error` con un mensaje de pydantic | Usaste `a: str = None` en vez de `a: str | None = None` | Cambia la anotación |
| `estado: error` con `"no se pudo convertir a SymPy"` | La expresión llegó en notación matemática (`x^2`, `sen(x)`, `π`) | Normaliza la entrada, o pide explícitamente la sintaxis en el docstring |
| El módulo no sale en `modulos_cargados` | Error de sintaxis o de import en tu archivo | `python tools/calculo<N>.py` te muestra el error real |
| La respuesta llega sin formato bonito | Falta el campo `latex` en el dict que devuelves | Agrégalo: `sp.latex(resultado)` |
