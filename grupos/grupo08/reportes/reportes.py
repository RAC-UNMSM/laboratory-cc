"""Genera un informe PDF del avance del proyecto del Grupo 8."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


GRUPO_DIR = Path(__file__).resolve().parents[1]
PROYECTO_DIR = GRUPO_DIR / "proyecto01" / "sistemas-no-lineales"
PROPUESTA = PROYECTO_DIR / "sistemas-no-lineales-propuesta.md"


@dataclass(frozen=True)
class Metodo:
	nombre: str
	modulo: str
	prueba: str


METODOS = (
	Metodo("Punto fijo multivariable", "punto_fijo.py", "test_punto_fijo.py"),
	Metodo("Newton-Raphson", "newton_sistemas.py", "test_newton_sistemas.py"),
	Metodo("Cuasi-Newton de Broyden", "cuasi_newton.py", "test_cuasi_newton.py"),
	Metodo("Descenso más rápido", "descenso.py", "test_descenso.py"),
	Metodo("Homotopía y continuación", "homotopia.py", "test_homotopia.py"),
)


def obtener_integrantes(archivo: Path = PROPUESTA) -> list[str]:
	"""Extrae los nombres enumerados en la sección de integrantes."""
	if not archivo.is_file():
		return []

	contenido = archivo.read_text(encoding="utf-8")
	seccion = re.search(
		r"^##\s+Integrantes\s*$([\s\S]*?)(?=^##\s|\Z)", contenido, re.MULTILINE
	)
	if seccion is None:
		return []
	return re.findall(r"^\s*\d+\.\s+\*\*(.+?)\*\*", seccion.group(1), re.MULTILINE)


def recopilar_avance(proyecto_dir: Path = PROYECTO_DIR) -> dict[str, object]:
	"""Recopila el estado de los archivos del proyecto del Grupo 8."""
	metodos = []
	for metodo in METODOS:
		modulo_existe = (proyecto_dir / "metodos" / metodo.modulo).is_file()
		prueba_existe = (proyecto_dir / "tests" / metodo.prueba).is_file()
		metodos.append(
			{"nombre": metodo.nombre, "modulo": modulo_existe, "prueba": prueba_existe}
		)

	componentes = (
		("Servidor MCP", proyecto_dir / "server.py"),
		("Validación de entradas", proyecto_dir / "validacion.py"),
		("Resultado común", proyecto_dir / "resultado.py"),
	)
	return {
		"integrantes": obtener_integrantes(),
		"metodos": metodos,
		"componentes": [(nombre, ruta.is_file()) for nombre, ruta in componentes],
	}


def _crear_estilos() -> dict[str, ParagraphStyle]:
	estilos = getSampleStyleSheet()
	estilos.add(
		ParagraphStyle(
			name="TituloInforme",
			parent=estilos["Title"],
			fontName="Helvetica-Bold",
			fontSize=21,
			leading=26,
			textColor=colors.HexColor("#17324D"),
			alignment=TA_LEFT,
			spaceAfter=5 * mm,
		)
	)
	estilos.add(
		ParagraphStyle(
			name="SeccionInforme",
			parent=estilos["Heading2"],
			fontName="Helvetica-Bold",
			fontSize=13,
			leading=17,
			textColor=colors.HexColor("#087E8B"),
			spaceBefore=4 * mm,
			spaceAfter=2 * mm,
		)
	)
	estilos.add(
		ParagraphStyle(
			name="TextoInforme",
			parent=estilos["BodyText"],
			fontName="Helvetica",
			fontSize=9,
			leading=13,
			alignment=TA_LEFT,
		)
	)
	return estilos


def _estado(presente: bool) -> str:
	return "Disponible" if presente else "Pendiente"


def _estilizar_tabla(tabla: Table, encabezado: bool = True) -> None:
	comandos = [
		("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
		("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
		("LEFTPADDING", (0, 0), (-1, -1), 7),
		("RIGHTPADDING", (0, 0), (-1, -1), 7),
		("TOPPADDING", (0, 0), (-1, -1), 6),
		("BOTTOMPADDING", (0, 0), (-1, -1), 6),
		("ROWBACKGROUNDS", (0, 1 if encabezado else 0), (-1, -1),
		 [colors.white, colors.HexColor("#F1F5F9")]),
	]
	if encabezado:
		comandos.extend(
			[
				("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
				("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
				("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
			]
		)
	tabla.setStyle(TableStyle(comandos))


def _pie_pagina(canvas, documento) -> None:
	canvas.saveState()
	canvas.setFont("Helvetica", 8)
	canvas.setFillColor(colors.HexColor("#64748B"))
	canvas.drawString(18 * mm, 12 * mm, "Grupo 8 | Sistemas no lineales - MCP")
	canvas.drawRightString(192 * mm, 12 * mm, f"Página {documento.page}")
	canvas.restoreState()


def generar_pdf(destino: Path, proyecto_dir: Path = PROYECTO_DIR) -> Path:
	"""Crea un PDF con integrantes y disponibilidad de código y pruebas."""
	avance = recopilar_avance(proyecto_dir)
	estilos = _crear_estilos()
	destino = destino.expanduser().resolve()
	destino.parent.mkdir(parents=True, exist_ok=True)

	documento = SimpleDocTemplate(
		str(destino),
		pagesize=A4,
		rightMargin=18 * mm,
		leftMargin=18 * mm,
		topMargin=18 * mm,
		bottomMargin=20 * mm,
		title="Informe de avance - Grupo 8",
		author="Grupo 8",
	)
	contenido = [
		Paragraph("Informe de avance", estilos["TituloInforme"]),
		Paragraph("Grupo 8 | Servidor MCP para sistemas no lineales", estilos["TextoInforme"]),
		Paragraph(
			f"Generado: {datetime.now().astimezone().strftime('%d/%m/%Y %H:%M %Z')}",
			estilos["TextoInforme"],
		),
		Spacer(1, 5 * mm),
		Paragraph("Resumen", estilos["SeccionInforme"]),
	]

	metodos = avance["metodos"]
	componentes = avance["componentes"]
	modulos_disponibles = sum(item["modulo"] for item in metodos)
	pruebas_disponibles = sum(item["prueba"] for item in metodos)
	contenido.append(
		Paragraph(
			f"Métodos con módulo presente: {modulos_disponibles}/{len(metodos)}. "
			f"Pruebas asociadas presentes: {pruebas_disponibles}/{len(metodos)}. "
			"Este resumen verifica archivos; no ejecuta las pruebas.",
			estilos["TextoInforme"],
		)
	)

	contenido.append(Paragraph("Métodos numéricos", estilos["SeccionInforme"]))
	filas_metodos = [["Método", "Implementación", "Prueba"]]
	filas_metodos.extend(
		[item["nombre"], _estado(item["modulo"]), _estado(item["prueba"])]
		for item in metodos
	)
	tabla_metodos = Table(filas_metodos, colWidths=[83 * mm, 42 * mm, 42 * mm], repeatRows=1)
	_estilizar_tabla(tabla_metodos)
	contenido.extend([tabla_metodos, Paragraph("Componentes", estilos["SeccionInforme"])])

	filas_componentes = [["Componente", "Estado"]]
	filas_componentes.extend([nombre, _estado(presente)] for nombre, presente in componentes)
	tabla_componentes = Table(filas_componentes, colWidths=[125 * mm, 42 * mm], repeatRows=1)
	_estilizar_tabla(tabla_componentes)
	contenido.extend([tabla_componentes, Paragraph("Integrantes", estilos["SeccionInforme"])])

	integrantes = avance["integrantes"]
	if integrantes:
		filas_integrantes = [[nombre] for nombre in integrantes]
		tabla_integrantes = Table(filas_integrantes, colWidths=[167 * mm])
		_estilizar_tabla(tabla_integrantes, encabezado=False)
		contenido.append(tabla_integrantes)
	else:
		contenido.append(Paragraph("No se encontraron integrantes en la propuesta.", estilos["TextoInforme"]))

	documento.build(contenido, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
	return destino


def main() -> None:
	parser = argparse.ArgumentParser(description="Genera el PDF de avance del Grupo 8.")
	parser.add_argument(
		"--output",
		type=Path,
		default=GRUPO_DIR / "reportes" / "grupo08_reporte.pdf",
		help="Ruta de salida del PDF (por defecto: reportes/grupo08_reporte.pdf).",
	)
	argumentos = parser.parse_args()
	ruta_pdf = generar_pdf(argumentos.output)
	print(f"PDF generado: {ruta_pdf}")


if __name__ == "__main__":
	main()
