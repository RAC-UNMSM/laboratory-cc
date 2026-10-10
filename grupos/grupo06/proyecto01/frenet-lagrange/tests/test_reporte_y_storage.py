"""Plantillas Jinja2, gráficos EN MEMORIA y almacenamiento en SeaweedFS (S3 simulado)."""
import json
import re
import socket

import pytest

from core import reporte, visualizacion
from methods import metodo_frenet as MF, metodo_hessiana as MH, metodo_lagrange as ML
from storage import ID_PATRON, ID_SESION, Almacen, BackendS3, ErrorAlmacen, nuevo_id
from s3_simulado import SeaweedSimulado

BUCKET = "grupo06-frenet-lagrange-imgs"
PUBLICA = "https://rac-unmsm.vekthos.org/img/grupo06-frenet-lagrange"


# ════════════════════════════════════════════════════════════════════════════
# Reportes
# ════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("metodo, objeto", [
    ("lagrange", lambda: ML.resolver("x*y", ["x^2 + y^2 = 8"])),
    ("hessiana", lambda: MH.resolver("x^4 + y^4 - 4xy + 1")),
    ("frenet", lambda: MF.resolver("cos t, sin t, t", "0")),
])
def test_html_y_png_en_memoria(tmp_path, monkeypatch, metodo, objeto):
    monkeypatch.chdir(tmp_path)                                   # si algo escribiera en disco, aparecería aquí
    obj = objeto()
    datos = visualizacion.datos_grafico(metodo, obj)
    html_b = reporte.html_bytes(metodo, obj, datos=datos)
    assert isinstance(html_b, bytes)
    html = html_b.decode("utf-8")
    assert html.lower().startswith("<!doctype html>") and "katex" in html.lower()
    assert not re.search(r"\{\{\s*\w+\s*\}\}|\{%", html)          # Jinja2 sin variables sin rellenar
    assert reporte.CONFIG[metodo]["titulo"] in html
    png = reporte.grafico_png_bytes(metodo, obj, datos)
    assert isinstance(png, bytes) and png[:8] == b"\x89PNG\r\n\x1a\n"
    assert reporte.resumen_breve(metodo, reporte.a_dict(metodo, obj))
    assert list(tmp_path.iterdir()) == []                          # nada se escribió en disco


# ════════════════════════════════════════════════════════════════════════════
# Almacén S3 (SeaweedFS simulado)
# ════════════════════════════════════════════════════════════════════════════
def _almacen(s3: SeaweedSimulado, **kw) -> Almacen:
    return Almacen(BackendS3(s3.url, BUCKET, PUBLICA, **kw))


def test_nuevo_id_sin_colisiones():
    # 32 bits aleatorios por id: con k ids en el MISMO segundo, P(choque) ≈ k²/2³³.
    # 2000 ids (casi todos en el mismo segundo) → ≈ 0,05 %; con 20 000 sería ≈ 5 % y la prueba
    # fallaría a veces por pura estadística, no por un error del código.
    ids = [nuevo_id("frenet") for _ in range(2000)]
    assert len(set(ids)) == len(ids)
    assert all(ID_PATRON.match(i) for i in ids[:50])
    assert re.fullmatch(r"frenet-\d{8}-\d{6}-[0-9a-f]{8}", ids[0])


def test_ensure_bucket_hace_put_y_tolera_que_ya_exista():
    with SeaweedSimulado() as s3:
        b = BackendS3(s3.url, BUCKET, PUBLICA)
        assert b.ensure_bucket() and b.ensure_bucket()            # 2.ª vez: 409 → también OK
        assert s3.puts() == [f"/{BUCKET}/", f"/{BUCKET}/"] and BUCKET in s3.buckets


def test_ensure_bucket_no_falla_si_seaweedfs_no_responde():
    with socket.socket() as s:                                    # puerto libre: nadie escucha
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    b = BackendS3(f"http://127.0.0.1:{puerto}", BUCKET, PUBLICA, timeout=2)
    assert b.ensure_bucket() is False                             # no lanza excepción
    with pytest.raises(ErrorAlmacen):
        Almacen(b).subir("frenet-20261006-000000-abcdef12", "x.json", b"{}")


def test_guardar_sube_bytes_bajo_grupo06_id_con_urls_publicas():
    html = "<!doctype html><p>hola</p>".encode("utf-8")
    png = b"\x89PNG\r\n\x1a\nfalso"
    with SeaweedSimulado() as s3:                                 # sin bucket: lo crea la 1.ª subida
        a = _almacen(s3)
        id_ = a.nuevo_id("hessiana")
        reg = a.guardar(id_, "hessiana", "f = x^2", {"funcion": "x^2"}, {"ñ": "á"}, ["P1 mínimo"],
                        contenido_bytes={"html": html, "png": png})
        esperadas = {f"grupo06/{id_}/{n}" for n in
                     ("reporte.html", "grafico.png", "resultado.json", "entrada.json", "meta.json")}
        assert set(s3.claves(BUCKET)) == esperadas
        assert f"/{BUCKET}/" in s3.puts()                         # ensure_bucket antes de subir
        assert not any("indice" in k for k in s3.claves())        # ya no hay índice compartido
        tipos = {k.rsplit("/", 1)[1]: t for (b, k), (_, t) in s3.objetos.items()}
        assert tipos["reporte.html"].startswith("text/html") and tipos["grafico.png"] == "image/png"
        assert tipos["resultado.json"].startswith("application/json")
        assert reg.archivos["html"] == f"{PUBLICA}/grupo06/{id_}/reporte.html"
        assert reg.archivos["png"] == f"{PUBLICA}/grupo06/{id_}/grafico.png"
        assert json.loads(s3.objetos[(BUCKET, f"grupo06/{id_}/resultado.json")][0]) == {"ñ": "á"}
        assert s3.objetos[(BUCKET, f"grupo06/{id_}/reporte.html")][0] == html          # mismos bytes
        assert s3.objetos[(BUCKET, f"grupo06/{id_}/grafico.png")][0] == png


def test_subir_exige_bytes_y_acepta_el_prefijo_de_sesion():
    with SeaweedSimulado(crear_buckets=(BUCKET,)) as s3:
        a = _almacen(s3)
        with pytest.raises(TypeError):
            a.subir("frenet-20261006-000000-abcdef12", "x.json", "texto, no bytes")   # type: ignore[arg-type]
        url = a.subir(ID_SESION, "lote.json", b"{}")
        assert url == f"{PUBLICA}/grupo06/{ID_SESION}/lote.json"
        assert ID_SESION not in [x["id"] for x in a.listar()]                       # no es un ejercicio


def test_listar_y_obtener_sin_indice():
    with SeaweedSimulado(crear_buckets=(BUCKET,)) as s3:
        a = _almacen(s3)
        ids = []
        for i, m in enumerate(("lagrange", "hessiana", "frenet")):
            id_ = f"{m}-2026100{i + 1}-120000-0000000{i}"
            a.guardar(id_, m, f"ejercicio {m}", {}, {"n": i}, [f"r{i}"], {})
            ids.append(id_)
        # un cálculo a medio guardar (sin meta.json) no debe aparecer
        a.subir("frenet-20261009-120000-ffffffff", "resultado.json", b"{}")
        assert [x["id"] for x in a.listar()] == ids[::-1]         # más reciente primero
        assert [x["id"] for x in a.listar(metodo="hessiana")] == [ids[1]]
        assert len(a.listar(limite=2)) == 2
        r = a.obtener(ids[2])
        assert r["resultado"] == {"n": 2} and r["resumen"] == ["r2"] and r["metodo"] == "frenet"
        with pytest.raises(KeyError):
            a.obtener("frenet-20200101-000000-00000000")
        listados = [ruta for (m, ruta, _) in s3.llamadas if "list-type=2" in ruta]
        assert listados and all("prefix=grupo06%2F" in ruta and "delimiter=%2F" in ruta for ruta in listados)


def test_firma_sigv4_cuando_hay_credenciales():
    with SeaweedSimulado(crear_buckets=(BUCKET,)) as s3:
        a = _almacen(s3, access_key="AK", secret_key="SK")
        a.subir("frenet-20261006-000000-abcdef12", "x.json", b"{}")
        cab = {k.lower(): v for k, v in s3.llamadas[-1][2].items()}
        assert cab["authorization"].startswith("AWS4-HMAC-SHA256 Credential=AK/")
        assert "x-amz-date" in cab and len(cab["x-amz-content-sha256"]) == 64


def test_ids_y_nombres_maliciosos():
    a = Almacen(BackendS3("http://127.0.0.1:9", BUCKET, PUBLICA))
    for malo in ("../x", "hessiana-1-2-zz", "lagrange-20260101-000000-abcdef/../.."):
        with pytest.raises(KeyError):
            a.clave(malo, "reporte.html")
    with pytest.raises(KeyError):
        a.clave("frenet-20261006-000000-abcdef12", "../../otro_grupo")
