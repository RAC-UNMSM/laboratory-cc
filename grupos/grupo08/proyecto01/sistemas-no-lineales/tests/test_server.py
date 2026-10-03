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