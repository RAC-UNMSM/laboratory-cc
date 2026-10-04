"""Capa 1: estructura (Pydantic)."""
import pytest
from pydantic import ValidationError

from core.validacion import SolicitudConsulta, SolicitudFrenet, SolicitudHessiana, SolicitudLagrange


def test_lagrange_valida():
    s = SolicitudLagrange(funcion="f(x,y) = x*y", restricciones=["x^2 + y^2 = 8"])
    assert s.funcion == "x*y" and s.salida.generar_html


@pytest.mark.parametrize("datos", [
    {"funcion": "x*y"},                                              # falta restricciones
    {"funcion": "x*y", "restricciones": []},                         # lista vacía
    {"funcion": "x*y", "restricciones": ["x^2 + y^2 <= 8"]},         # desigualdad
    {"funcion": "x*y", "restricciones": ["x = y = 1"]},              # dos '='
    {"funcion": "x^^2", "restricciones": ["x = 1"]},                 # sintaxis
    {"funcion": "x*y", "restricciones": ["x=1"], "extra": 1},        # campo desconocido
    {"funcion": "x*y", "restricciones": ["x=1"], "variables": ["x", "x"]},
    {"funcion": "x*y", "restricciones": ["x=1"], "variables": ["pi"]},
])
def test_lagrange_rechaza(datos):
    with pytest.raises(ValidationError):
        SolicitudLagrange(**datos)


def test_hessiana_y_frenet():
    assert SolicitudHessiana(funcion="x^3 + y^3 - 3xy").metodo == "auto"
    assert SolicitudFrenet(curva="cos t, sin t, t").curva == ["cos(t)", "sin(t)", "t"]
    with pytest.raises(ValidationError):
        SolicitudFrenet(curva=["t"])                                  # 1 componente
    with pytest.raises(ValidationError):
        SolicitudFrenet(curva=["t", "t^2"], rango=(2, 1))             # rango invertido


def test_consulta_bloquea_rutas():
    with pytest.raises(ValidationError):
        SolicitudConsulta(id_resultado="../../etc/passwd")
