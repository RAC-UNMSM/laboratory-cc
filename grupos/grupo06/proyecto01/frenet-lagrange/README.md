# Servidor MCP «Frenet, Lagrange y Puntos Críticos» (Grupo 06 · UNMSM)

Es un agente de IA para Cálculo en varias variables. El **LLM** (Claude, DeepSeek, Gemini…) entiende el
enunciado y explica la solución. Toda la matemática la hace este **servidor MCP**, con **SymPy exacto**:
fracciones y raíces, nunca decimales inventados.

```
Usuario ─▶ LLM ─(elige herramienta)─▶ cliente MCP ══STDIO══▶ server.py
                                                   │
          ┌─────────────── capa 1: core/validacion.py (Pydantic)   ¿la petición está bien formada?
          ├─────────────── capa 2: core/verificador.py             ¿tiene sentido matemático?
          ├─────────────── methods/metodo_*.py                     cálculo exacto (solo datos)
          ├─────────────── core/visualizacion.py                   datos de gráficos + PNG
          ├─────────────── core/reporte.py + templates/ (Jinja2)   página HTML interactiva
          ├─────────────── storage.py                              resultados/<id>/…
          └─────────────── core/combinado.py                       resultados_combinados/lote-…/ (varios ejercicios en 1 HTML)
```

## Estructura

```
mcp_math_server/
├── methods/                 lógica matemática pura (sin gráficos ni HTML)
│   ├── metodo_lagrange.py   multiplicadores, Hessiano orlado, puntos singulares
│   ├── metodo_hessiana.py   ∇f = 0, Sylvester, Taylor de orden superior, extremos globales
│   └── metodo_frenet.py     T, N, B, κ, τ, planos, verificación de Frenet–Serret
├── core/
│   ├── utils_math.py        parser SEGURO, resolución exacta de sistemas, formato LaTeX
│   ├── validacion.py        esquemas Pydantic (lo que ve el LLM)  ← capa 1
│   ├── verificador.py       validaciones lógicas con códigos de error ← capa 2
│   ├── diagnostico.py       lenguaje natural → método + argumentos (ruteo semántico)
│   ├── visualizacion.py     TODO lo gráfico (Plotly/matplotlib) centralizado
│   ├── reporte.py           inyecta resultados en las plantillas Jinja2
│   ├── combinado.py         reúne varios reportes en UNA página con navegación (carpeta aparte)
│   └── motor.py             orquesta un cálculo completo (se ejecuta en un proceso aparte)
├── templates/               base.html.j2 + combinado*.html.j2 + static/ (CSS y JS por método)
├── server.py                servidor MCP (FastMCP, STDIO)
├── storage.py               persistencia: resultados/<id>/{entrada,resultado}.json, reporte.html, grafico.png
├── agente.py                agente IA: LLM + cliente MCP (DeepSeek, Gemini, Claude, OpenAI, Ollama, o simulado)
├── cli.py                   uso desde la terminal, sin LLM
├── tests/                   pruebas (pytest), incluidas dos de punta a punta por STDIO
├── ejemplos/                configuraciones para Claude Desktop (Python y Docker)
├── legado/                  los tres metodos_*.py originales (referencia; mismos resultados)
├── Dockerfile · docker-compose.yml · requirements*.txt
```

## Instalación

```bash
cd mcp_math_server
pip install -r requirements.txt            # servidor y CLI
pip install -r requirements-agente.txt     # además, para agente.py con un LLM real
pip install -r requirements-dev.txt        # además, para las pruebas
```

## Uso

### 1. Terminal (sin IA)
```bash
python cli.py lagrange -f "x*y" -g "x^2 + y^2 = 8" --html lagrange.html
python cli.py hessiana -f "x^4 + y^4 - 4xy + 1" --png h.png --html h.html --offline
python cli.py frenet   -r "cos t, sin t, t" --t0 pi/4 --html helice.html
python cli.py frenet   --demo 0 --html demo.html     # todas las demos
python cli.py diagnostico "maximiza xy sobre la circunferencia x^2+y^2=8"
```

### 2. Agente IA
```bash
python agente.py --simulado                                        # sin API key: ideal para exponer
python agente.py --proveedor deepseek                              # variable DEEPSEEK_API_KEY
python agente.py --proveedor gemini --modelo <id-del-modelo>       # variable GEMINI_API_KEY
python agente.py --proveedor claude --modelo <id-del-modelo>       # variable ANTHROPIC_API_KEY
python agente.py --proveedor ollama --modelo <modelo-local>        # sin internet
python agente.py --simulado -p "curvatura de r(t)=(cos t, sin t, t) en t=0" --abrir
```
Para la clave en Windows (PowerShell) usa `$env:DEEPSEEK_API_KEY="sk-..."`; en Linux/macOS, `export DEEPSEEK_API_KEY=sk-...`.

### 3. Como servidor MCP de Claude Desktop (u otro cliente MCP)
Copia `ejemplos/claude_desktop_config.json` dentro del `claude_desktop_config.json` de Claude Desktop,
cambia `C:\RUTA\A\...` por tu ruta real y reinicia la aplicación. Aparecerán las 6 herramientas.
Con Docker, usa `ejemplos/claude_desktop_config_docker.json`.

### 4. Docker
```bash
docker build -t mcp-math-server .
docker run -i --rm -v "$PWD/resultados:/data/resultados" mcp-math-server     # -i es obligatorio (STDIO)
docker compose run --rm mcp-math                                              # equivalente con compose
```

### 5. Pruebas
```bash
python -m pytest -q
```

## Herramientas MCP

| Herramienta | Cuándo la elige el LLM |
|---|---|
| `diagnosticar_problema` | enunciado ambiguo en lenguaje natural → recomienda método y extrae argumentos |
| `optimizar_con_restricciones` | máx/mín de f **sujeto a** igualdades g = c (Lagrange) |
| `analizar_puntos_criticos` | máx/mín relativos, sillas, Hessiana, **sin** restricciones |
| `analizar_curva_frenet` | curva r(t): T, N, B, curvatura, torsión, planos |
| `listar_resultados` / `obtener_resultado` | historial guardado |
| `combinar_reportes` | el usuario envió **varios ejercicios a la vez** → un solo HTML con navegación entre ellos |

También hay recursos (`resultados://{id}`, `ayuda://metodos`) y un prompt (`resolver_problema`).

## Varios ejercicios a la vez: reporte combinado

Si el usuario envía dos o más ejercicios en un mismo mensaje, el LLM resuelve **cada uno** con su
herramienta (cada ejercicio conserva su carpeta y su `reporte.html` individual en `resultados/`) y al
final llama a `combinar_reportes` con los `id_resultado` en orden. Se crea, en una carpeta **aparte**:

```
resultados_combinados/
└── lote-20261003-190512-a1b2c3/
    ├── reporte_combinado.html   ← los N ejercicios, cada uno con sus 5 pestañas
    └── lote.json                ← qué ejercicios contiene y en qué orden
```

La página tiene barra con «← Anterior / Siguiente ejercicio →», puntos numerados, un índice con el
enunciado y el resumen de cada ejercicio, botones al final de cada reporte y atajos (`←` `→`, `I`).
Cada reporte individual se copia completo dentro del combinado, así que este sigue funcionando aunque
se borren las carpetas individuales. No recalcula nada ni modifica los reportes individuales.

## Validación en dos capas

1. **Estructural (Pydantic, `core/validacion.py`).** El SDK genera el JSON Schema a partir de estos modelos
   y rechaza la llamada **antes de ejecutar nada** en estos casos: falta un campo, sobra un campo, la
   expresión no se puede interpretar o la restricción es una desigualdad.
2. **Lógica (`core/verificador.py`).** Cada error devuelve un `codigo`, un `mensaje` y una `sugerencia`
   que el LLM explica al usuario. Códigos: `DIVISION_POR_CERO`, `RESTRICCION_IMPOSIBLE`
   (p. ej. x²+y² = −1), `SOBREDETERMINADO` (más restricciones que variables), `FUNCION_CONSTANTE`,
   `HESSIANA_NO_CUADRADA`, `CURVATURA_CERO` (la curva es una recta), `PUNTO_SINGULAR`,
   `CURVATURA_CERO_EN_T0`, `T0_FUERA_DEL_DOMINIO`, `SIMBOLOS_NO_DECLARADOS`, entre otros.

## Seguridad y robustez
- **Parser seguro.** Lista blanca de funciones, sin `__builtins__` y con caracteres filtrados. Una entrada
  como `__import__('os')` se rechaza.
- **Tiempo límite.** Cada cálculo corre en un proceso aparte con límite de tiempo (`MCP_MATH_TIMEOUT`,
  120 s por defecto). Si se excede, el proceso se termina y el servidor sigue respondiendo.
- **STDIO limpio.** Nada se imprime en stdout; los logs van a stderr.
- **Ids validados.** Los ids de resultados se validan para impedir el acceso a rutas fuera de `resultados/`.

## Variables de entorno
`MCP_MATH_RESULTADOS` (carpeta de salida), `MCP_MATH_COMBINADOS` (reportes combinados; por defecto
`resultados_combinados/` junto a `resultados/`), `MCP_MATH_TIMEOUT`,
`MCP_MATH_PROCESOS=0` (calcular en el mismo proceso, para depurar), `MCP_MATH_LOG`.
