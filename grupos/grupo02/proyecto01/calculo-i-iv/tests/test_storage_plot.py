import base64

import pytest
import storage
from validacion import EntradaError
from visualizacion import render


@pytest.mark.parametrize("expr", ["3", "x**2", "sin(x)"])
def test_png(expr):
    r = render(expr, "-2", "2")
    assert base64.b64decode(r["png_base64"]).startswith(b"\x89PNG\r\n\x1a\n")


def test_pole_rejected():
    with pytest.raises(EntradaError):
        render("1/x", "-1", "1")


def test_no_storage(monkeypatch):
    monkeypatch.setattr(storage, "IMG_BUCKET", "")
    assert storage.subir_imagen(b"x") is None


def test_storage_unavailable(monkeypatch):
    monkeypatch.setattr(storage, "IMG_BUCKET", "grupo02-calculo-i-iv-imgs")
    monkeypatch.setattr(storage, "PUBLIC_IMG_BASE_URL", "https://example.org/img")

    def fail(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(storage, "urlopen", fail)
    assert storage.subir_imagen(b"x") is None


def test_storage_put(monkeypatch):
    monkeypatch.setattr(storage, "IMG_BUCKET", "grupo02-calculo-i-iv-imgs")
    monkeypatch.setattr(storage, "PUBLIC_IMG_BASE_URL", "https://example.org/img")
    seen = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def upload(req, timeout):
        seen.append(req)
        assert timeout == 3
        return Response()

    monkeypatch.setattr(storage, "urlopen", upload)
    a = storage.subir_imagen(b"png")
    b = storage.subir_imagen(b"png")
    assert a != b and a.startswith("https://example.org/img/")
    assert seen[0].method == "PUT" and seen[0].data == b"png"
