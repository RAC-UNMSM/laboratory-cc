from validacion import validar_entrada


def test_validar_entrada_correcta():
    errores = validar_entrada(
        expresiones=["x**2 + y**2 - 1", "x - y"],
        variables=["x", "y"],
        x0=[1.0, 0.5],
        tolerancia=1e-8,
        max_iter=100
    )
    assert errores == []


def test_validar_entrada_dimension_incorrecta():
    errores = validar_entrada(
        expresiones=["x**2 + y**2 - 1"],
        variables=["x", "y"],
        x0=[1.0, 0.5],
        tolerancia=1e-8,
        max_iter=100
    )
    assert len(errores) > 0


def test_validar_entrada_tolerancia_negativa():
    errores = validar_entrada(
        expresiones=["x**2 + y**2 - 1", "x - y"],
        variables=["x", "y"],
        x0=[1.0, 0.5],
        tolerancia=-1e-8,
        max_iter=100
    )
    assert any("tolerancia" in e.lower() for e in errores)