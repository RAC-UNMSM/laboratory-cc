from server import _ejecutar_metodo


def test_ejecutar_metodo_entrada_invalida():
    res = _ejecutar_metodo(
        "test",
        "mod",
        "func",
        expresiones=[],
        variables=["x"],
        x0=[1.0],
        tolerancia=1e-8,
        max_iter=100
    )
    assert res["status"] == "invalid_input"
    assert len(res["warnings"]) > 0


def test_ejecutar_metodo_modulo_no_implementado():
    res = _ejecutar_metodo(
        "test",
        "modulo_inexistente",
        "funcion_inexistente",
        expresiones=["x**2 - 1"],
        variables=["x"],
        x0=[1.0],
        tolerancia=1e-8,
        max_iter=100
    )
    assert res["status"] == "invalid_input"
    assert "Módulo no implementado" in res["warnings"][0]


def test_resolver_ejercicio_genera_html_y_actualiza_configuracion(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    import server

    monkeypatch.setattr(server, "OUTPUT_DIR", tmp_path / "salida-mathjax")
    monkeypatch.setattr(server, "CONFIG_PATH", tmp_path / "config" / "proyecto_config.json")
    respuesta = server._resolver_ejercicio(
        enunciado="Resolver la circunferencia unitaria y la recta y=x.",
        expresiones=["x**2 + y**2 - 1", "x - y"],
        variables=["x", "y"],
        x0=[1.0, 0.5],
        metodo="newton_sistemas",
        tolerancia=1e-8,
        max_iter=50,
    )

    reporte = Path(respuesta["reporte_html"])
    contenido = reporte.read_text(encoding="utf-8")
    configuracion = json.loads(server.CONFIG_PATH.read_text(encoding="utf-8"))

    assert respuesta["status"] == "converged"
    assert reporte.parent == server.OUTPUT_DIR
    assert "mathjax@3/es5/tex-svg.js" in contenido
    assert "Iteraciones" in contenido
    assert respuesta["id"] in contenido
    assert configuracion["ejercicios"][0]["reporte_html"] == reporte.relative_to(server.OUTPUT_DIR.parent).as_posix()
    assert configuracion["ejercicios"][0]["estado"] == "converged"