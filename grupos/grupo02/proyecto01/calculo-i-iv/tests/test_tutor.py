import pytest
from engine import solve
from tutor import LESSONS, lesson, verify


@pytest.mark.parametrize("tema", list(LESSONS))
def test_lessons(tema):
    assert "respuesta" not in lesson(tema)
    assert verify(tema, LESSONS[tema]["respuesta"])["correcta"] is True
    assert solve({"problema": LESSONS[tema]["ejemplo"]})["estado"] != "error"


def test_wrong_answer():
    assert verify("derivadas", "3*x")["correcta"] is False


def test_primitive_constant():
    assert verify("integrales", "sin(x)+7")["correcta"] is True


def test_hole_not_erased():
    assert verify("derivadas", "3*x**3/x")["correcta"] is None
