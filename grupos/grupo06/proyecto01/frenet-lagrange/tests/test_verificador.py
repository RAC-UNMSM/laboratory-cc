"""Capa 2: sentido matemático."""
import pytest

from core.validacion import SolicitudFrenet, SolicitudHessiana, SolicitudLagrange
from core.verificador import ErrorVerificacion, verificar


@pytest.mark.parametrize("metodo, solicitud, codigo", [
    ("lagrange", SolicitudLagrange(funcion="x+y", restricciones=["x^2 + y^2 = -1"]), "RESTRICCION_IMPOSIBLE"),
    ("lagrange", SolicitudLagrange(funcion="x+y", restricciones=["1 = 2"]), "RESTRICCION_IMPOSIBLE"),
    ("lagrange", SolicitudLagrange(funcion="x+y", restricciones=["x = 1", "y = 2", "x + y = 3"]), "SOBREDETERMINADO"),
    ("lagrange", SolicitudLagrange(funcion="x/(y-y)", restricciones=["x = 1"]), "DIVISION_POR_CERO"),
    ("lagrange", SolicitudLagrange(funcion="x*y*z", restricciones=["x = 1"], variables=["x", "y"]),
     "SIMBOLOS_NO_DECLARADOS"),
    ("hessiana", SolicitudHessiana(funcion="5"), "FUNCION_CONSTANTE"),
    ("hessiana", SolicitudHessiana(funcion="1/(x-x)"), "DIVISION_POR_CERO"),
    ("frenet", SolicitudFrenet(curva=["t", "2t", "3t"]), "CURVATURA_CERO"),
    ("frenet", SolicitudFrenet(curva=["1", "2", "3"]), "NO_DEPENDE_DEL_PARAMETRO"),
    ("frenet", SolicitudFrenet(curva=["t^2", "t^3"], t0="0"), "PUNTO_SINGULAR"),
    ("frenet", SolicitudFrenet(curva=["t", "t^3", "0"], t0="0"), "CURVATURA_CERO_EN_T0"),
    ("frenet", SolicitudFrenet(curva=["log(t)", "t^2", "t"], t0="-1"), "T0_FUERA_DEL_DOMINIO"),
])
def test_errores_con_codigo(metodo, solicitud, codigo):
    with pytest.raises(ErrorVerificacion) as e:
        verificar(metodo, solicitud)
    assert e.value.codigo == codigo
    assert e.value.mensaje and e.value.como_dict()["tipo"] == "verificacion"


def test_casos_validos_pasan():
    assert verificar("lagrange", SolicitudLagrange(funcion="x*y", restricciones=["x^2+y^2=8"])).datos["n_variables"] == 2
    assert verificar("hessiana", SolicitudHessiana(funcion="(x - y)^2 + 1")).datos["n_variables"] == 2
    assert verificar("frenet", SolicitudFrenet(curva=["cos t", "sin t", "t"])).datos["r_t0"] == [1.0, 0.0, 0.0]
