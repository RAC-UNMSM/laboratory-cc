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


def test_resolver_ejercicio_sube_reporte_y_devuelve_url(monkeypatch):
    import server

    subidos = {}

    def falso_subir(html, identificador):
        subidos["html"] = html
        subidos["id"] = identificador
        return f"https://ejemplo.test/reporte_{identificador}.html"

    monkeypatch.setattr(server, "subir_reporte", falso_subir)
    enunciado = "Resolver la circunferencia unitaria y la recta y=x."
    respuesta = server._resolver_ejercicio(
        enunciado=enunciado,
        expresiones=["x**2 + y**2 - 1", "x - y"],
        variables=["x", "y"],
        x0=[1.0, 0.5],
        metodo="newton_sistemas",
        tolerancia=1e-8,
        max_iter=50,
    )

    assert respuesta["status"] == "converged"
    assert respuesta["reporte_url"] == f"https://ejemplo.test/reporte_{respuesta['id']}.html"
    assert subidos["id"] == respuesta["id"]
    assert "mathjax@3/es5/tex-svg.js" in subidos["html"]
    assert enunciado in subidos["html"]


def test_resolver_ejercicio_sin_storage_devuelve_url_nula():
    import server

    respuesta = server._resolver_ejercicio(
        enunciado="Resolver la circunferencia unitaria y la recta y=x.",
        expresiones=["x**2 + y**2 - 1", "x - y"],
        variables=["x", "y"],
        x0=[1.0, 0.5],
        metodo="newton_sistemas",
    )
    assert respuesta["status"] == "converged"
    assert respuesta["reporte_url"] is None
