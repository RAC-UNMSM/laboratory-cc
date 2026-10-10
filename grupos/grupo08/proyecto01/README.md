# Proyecto 01

Cada grupo debe crear, dentro de esta carpeta (`proyecto01/`), una nueva
carpeta con el nombre de su tema, **en minúscula**.

Dentro de esa carpeta, adjuntar un archivo `.md` con la propuesta del
tema, usando como nombre del archivo el nombre del tema, también en
minúscula:

```
proyecto01/
  <tema-en-minuscula>/
    <tema-en-minuscula>.md
```
# Sistemas No Lineales - MCP

Servidor MCP para resolución de sistemas de ecuaciones no lineales.

## Estructura
- `server.py`: servidor MCP y definición de tools.
- `resultado.py`: contrato de salida común.
- `validacion.py`: validaciones de entrada.
- `metodos/`: implementaciones de métodos numéricos.
- `tests/`: pruebas unitarias.

## Instalación
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt