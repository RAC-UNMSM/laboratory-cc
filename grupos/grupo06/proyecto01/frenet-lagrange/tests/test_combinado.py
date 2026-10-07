"""Reporte combinado: varios ejercicios en un solo HTML, publicado en su propio prefijo del almacén."""
import json
import re
import tempfile

import pytest

from core.combinado import Combinador, ErrorCombinado, ID_LOTE
from core.motor import ejecutar
from s3_simulado import SeaweedSimulado
from storage import Almacen, BackendS3

BUCKET = "frenet-lagrange-imgs"
PUBLICA = "https://rac-unmsm.vekthos.org/img/frenet-lagrange"

PROBLEMAS = [
    ("lagrange", {"funcion": "3x + 4y", "restricciones": ["x^2 + y^2 = 25"]}),
    ("hessiana", {"funcion": "x^2 + x*y + y^2 - 3x"}),
    ("frenet", {"curva": ["cos t", "sin t", "t"]}),
]


def _resolver(almacen, metodo, solicitud):
    id_ = almacen.nuevo_id(metodo)
    with tempfile.TemporaryDirectory() as tmp:            # igual que server.py: carpeta temporal → S3
        r = ejecutar(metodo, {**solicitud, "salida": {"generar_png": False}}, tmp)
        assert r["ok"], r
        almacen.guardar(id_, metodo, f"prueba {metodo}", r["solicitud"], r["resultado"], r["resumen"],
                        r["archivos"])
    return id_


@pytest.fixture(scope="module")
def almacen_con_tres():
    with SeaweedSimulado(crear_buckets=(BUCKET,)) as s3:
        a = Almacen(BackendS3(s3.url, BUCKET, PUBLICA))
        ids = [_resolver(a, m, s) for m, s in PROBLEMAS]
        yield a, ids, s3


def _ejercicios(html):
    m = re.search(r"const EJ = (\[.*?\]), TITULO = ", html, re.S)
    assert m, "no se encontró el arreglo de ejercicios en el HTML"
    return json.loads(m.group(1))


def test_combinado_tres_metodos(almacen_con_tres):
    a, ids, s3 = almacen_con_tres
    antes = {k: v for k, v in s3.objetos.items()}
    r = Combinador(a).combinar(ids, "Práctica <3> & 'prueba'", ["$f = 3x+4y$", "Hessiana de f", "Hélice"])
    assert r["ok"] and r["n_ejercicios"] == 3 and ID_LOTE.match(r["id_lote"])
    # publicado en SU prefijo grupo06/<lote>/, con URL pública
    clave_html = f"grupo06/{r['id_lote']}/reporte_combinado.html"
    assert (BUCKET, clave_html) in s3.objetos and (BUCKET, f"grupo06/{r['id_lote']}/lote.json") in s3.objetos
    assert r["archivos"]["html"] == f"{PUBLICA}/{clave_html}" and r["markdown"].endswith(f"({PUBLICA}/{clave_html})")
    # los reportes individuales siguen intactos (mismos bytes)
    for clave, valor in antes.items():
        assert s3.objetos[clave] == valor
        if clave[1].endswith("reporte.html"):
            assert b"postMessage" not in valor[0]

    html = s3.objetos[(BUCKET, clave_html)][0].decode("utf-8")
    assert html.lower().startswith("<!doctype html>")
    assert not re.search(r"\{\{\s*\w+|\{%", html)                      # Jinja2 sin restos
    assert "Práctica &lt;3&gt; &amp; &#39;prueba&#39;" in html            # título escapado
    script = html.split("const EJ = ", 1)[1]
    assert script.count("</script>") == 1                              # solo el cierre real
    ej = _ejercicios(html)
    assert [e["id"] for e in ej] == ids and [e["n"] for e in ej] == [1, 2, 3]
    assert [e["metodo"] for e in ej] == ["lagrange", "hessiana", "frenet"]
    # cada reporte copiado conserva sus 5 pestañas y lleva el pie de navegación
    for e in ej:
        for pestaña in ("resumen", "proc", "g3d", "g2d", "json"):
            assert f'data-tab="{pestaña}"' in e["html"]
        assert "postMessage" in e["html"] and "Ejercicio" in e["html"]
    assert "Siguiente ejercicio (2)" in ej[0]["html"] and "volver al índice" in ej[2]["html"]

    lote = json.loads(s3.objetos[(BUCKET, f"grupo06/{r['id_lote']}/lote.json")][0])
    assert [x["id"] for x in lote["ejercicios"]] == ids
    assert lote["ejercicios"][0]["html_individual"] == f"{PUBLICA}/grupo06/{ids[0]}/reporte.html"


def test_combinado_errores(almacen_con_tres):
    a, ids, _ = almacen_con_tres
    with pytest.raises(ErrorCombinado) as e:
        Combinador(a).combinar([ids[0], "hessiana-20000101-000000-abcdef12"])
    assert e.value.codigo == "NO_ENCONTRADO" and "hessiana-20000101-000000-abcdef12" in e.value.mensaje


def test_validacion_combinar():
    from pydantic import ValidationError
    from core.validacion import SolicitudCombinar
    with pytest.raises(ValidationError):
        SolicitudCombinar(ids=["frenet-20261003-184624-5794a3", "frenet-20261003-184624-5794a3"])
    with pytest.raises(ValidationError):
        SolicitudCombinar(ids=["../../etc"])
    with pytest.raises(ValidationError):
        SolicitudCombinar(ids=["frenet-20261003-184624-5794a3"], enunciados=["a", "b"])
    assert SolicitudCombinar(ids=["frenet-20261006-184624-5794a3b2"]).ids          # ids nuevos (8 hex)
