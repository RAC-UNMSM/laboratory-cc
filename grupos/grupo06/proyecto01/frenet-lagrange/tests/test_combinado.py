"""Reporte combinado: varios ejercicios en un solo HTML, publicado en su propio prefijo del almacén,
y el reporte AUTOMÁTICO de la sesión (prefijo fijo grupo06/lote-sesion-actual/)."""
import json
import re

import pytest

import core.combinado as C
from core.combinado import Combinador, ErrorCombinado, ID_LOTE, ID_SESION
from core.motor import ejecutar, publicar
from s3_simulado import SeaweedSimulado
from storage import Almacen, BackendS3

BUCKET = "grupo06-frenet-lagrange-imgs"
PUBLICA = "https://rac-unmsm.vekthos.org/img/grupo06-frenet-lagrange"

PROBLEMAS = [
    ("lagrange", {"funcion": "3x + 4y", "restricciones": ["x^2 + y^2 = 25"]}),
    ("hessiana", {"funcion": "x^2 + x*y + y^2 - 3x"}),
    ("frenet", {"curva": ["cos t", "sin t", "t"]}),
]


def _resolver(almacen, metodo, solicitud):
    id_ = almacen.nuevo_id(metodo)
    r = ejecutar(metodo, {**solicitud, "salida": {"generar_png": False}})      # HTML en memoria (bytes)
    assert r["ok"], r
    assert isinstance(r["artefactos"]["html"], bytes)
    almacen.guardar(id_, metodo, f"prueba {metodo}", r["solicitud"], r["resultado"], r["resumen"],
                    contenido_bytes=r["artefactos"])
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


# ════════════════════════════════════════════════════════════════════════════
# Reporte de sesión automático (agregar_a_sesion)
# ════════════════════════════════════════════════════════════════════════════
def test_agregar_a_sesion_sobrescribe_el_mismo_prefijo(almacen_con_tres):
    a, ids, s3 = almacen_con_tres
    C.configurar_sesion(a)
    clave_html = f"grupo06/{ID_SESION}/reporte_combinado.html"
    clave_lote = f"grupo06/{ID_SESION}/lote.json"
    assert (BUCKET, clave_lote) not in s3.objetos                      # sesión vacía al principio
    lotes_antes = {k for (_, k) in s3.objetos if "/lote-" in k}

    for i, (id_, texto) in enumerate(zip(ids, ["Ejercicio A", "Ejercicio B", "Ejercicio C"]), start=1):
        r = C.agregar_a_sesion(id_, texto)
        assert r["id_lote"] == ID_SESION and r["n_ejercicios"] == i
        assert r["archivos"]["html"] == f"{PUBLICA}/{clave_html}"
        lote = json.loads(s3.objetos[(BUCKET, clave_lote)][0])
        assert [e["id"] for e in lote["ejercicios"]] == ids[:i]          # se añade al final, en orden
        assert [e["enunciado"] for e in lote["ejercicios"]] == ["Ejercicio A", "Ejercicio B", "Ejercicio C"][:i]

    # siempre el MISMO prefijo: no aparecen lotes con id nuevo
    lotes_despues = {k for (_, k) in s3.objetos if "/lote-" in k}
    assert lotes_despues - lotes_antes == {clave_html, clave_lote}
    html = s3.objetos[(BUCKET, clave_html)][0].decode("utf-8")
    assert [e["id"] for e in _ejercicios(html)] == ids
    # repetir un id no lo duplica: pasa al final
    r = C.agregar_a_sesion(ids[0], "Ejercicio A otra vez")
    assert [e["id"] for e in json.loads(s3.objetos[(BUCKET, clave_lote)][0])["ejercicios"]] == [ids[1], ids[2], ids[0]]


def test_publicar_sube_desde_memoria_y_actualiza_la_sesion():
    with SeaweedSimulado() as s3:                                    # sin bucket: lo crea la primera subida
        a = Almacen(BackendS3(s3.url, BUCKET, PUBLICA))
        C.configurar_sesion(a)
        urls = []
        for metodo, sol in PROBLEMAS[1:]:
            id_ = a.nuevo_id(metodo)
            r = ejecutar(metodo, sol)
            assert isinstance(r["artefactos"]["png"], bytes) and r["artefactos"]["png"][:8] == b"\x89PNG\r\n\x1a\n"
            pub = publicar(a, id_, metodo, f"prueba {metodo}", r, f"enunciado {metodo}")
            assert pub["archivos"]["html"] == f"{PUBLICA}/grupo06/{id_}/reporte.html"
            assert pub["sesion"] == f"{PUBLICA}/grupo06/{ID_SESION}/reporte_combinado.html"
            # los bytes subidos son exactamente los generados en memoria
            assert s3.objetos[(BUCKET, f"grupo06/{id_}/grafico.png")][0] == r["artefactos"]["png"]
            urls.append(id_)
        lote = json.loads(s3.objetos[(BUCKET, f"grupo06/{ID_SESION}/lote.json")][0])
        assert [e["id"] for e in lote["ejercicios"]] == urls and pub["n_sesion"] == 2
        # orden de las subidas: individuales primero, sesión después
        puts = [ruta for (m, ruta, _) in s3.llamadas if m == "PUT" and ruta.count("/") > 2]
        assert puts.index(f"/{BUCKET}/grupo06/{urls[0]}/meta.json") < puts.index(
            f"/{BUCKET}/grupo06/{ID_SESION}/reporte_combinado.html")


def test_sesion_descarta_ejercicios_que_ya_no_existen(almacen_con_tres):
    a, ids, s3 = almacen_con_tres
    C.configurar_sesion(a)
    a.subir_json(ID_SESION, "lote.json", {"ejercicios": [{"id": "frenet-20000101-000000-deadbeef", "enunciado": "x"},
                                                         {"id": ids[0], "enunciado": "A"}]})
    r = C.agregar_a_sesion(ids[1], "B")
    assert [e["id"] for e in r["ejercicios"]] == [ids[0], ids[1]]
