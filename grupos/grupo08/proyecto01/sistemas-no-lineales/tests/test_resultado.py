from resultado import ResultadoMetodo, EstadoMetodo


def test_resultado_metodo_creacion():
    res = ResultadoMetodo(
        method="test",
        status=EstadoMetodo.CONVERGED,
        solution=[1.0, 2.0],
        iterations=5,
        final_error=1e-9,
        final_residual=1e-9,
        trajectory=[[0.0, 0.0], [1.0, 2.0]],
        warnings=[],
        message="ok"
    )
    assert res.method == "test"
    assert res.status == EstadoMetodo.CONVERGED
    assert res.solution == [1.0, 2.0]
    assert res.iterations == 5


def test_resultado_metodo_serializacion():
    res = ResultadoMetodo(method="test", status=EstadoMetodo.INVALID_INPUT)
    data = res.model_dump()
    assert data["method"] == "test"
    assert data["status"] == "invalid_input"