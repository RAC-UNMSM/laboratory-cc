"""
tests/s3_simulado.py — Un SeaweedFS de mentira (API S3 mínima) para las pruebas.

Corre en un hilo, en 127.0.0.1 y un puerto libre, y GUARDA EL REGISTRO de cada petición para
que las pruebas puedan verificar exactamente qué hizo storage.py:

    with SeaweedSimulado() as s3:
        ...                              # s3.url → "http://127.0.0.1:PUERTO"
        s3.llamadas                      # [("PUT", "/frenet-lagrange-imgs/", {...cabeceras}), ...]
        s3.objetos                       # {("bucket", "grupo06/<id>/reporte.html"): (bytes, content-type)}

Implementa lo que usa storage.py: PUT bucket, PUT/GET objeto, ListObjectsV2 (prefix + delimiter).
Si el bucket no existe responde 404 NoSuchBucket, igual que S3.
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit
from xml.sax.saxutils import escape

NS = "http://s3.amazonaws.com/doc/2006-03-01/"


class SeaweedSimulado:
    def __init__(self, crear_buckets: tuple[str, ...] = ()) -> None:
        self.buckets: set[str] = set(crear_buckets)
        self.objetos: dict[tuple[str, str], tuple[bytes, str]] = {}
        self.llamadas: list[tuple[str, str, dict[str, str]]] = []
        self._candado = threading.Lock()
        simulado = self

        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silencio
                pass

            def _responder(self, codigo: int, cuerpo: bytes = b"", tipo: str = "application/xml") -> None:
                self.send_response(codigo)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(cuerpo)

            def _error(self, codigo: int, s3code: str) -> None:
                self._responder(codigo, f"<Error><Code>{s3code}</Code></Error>".encode())

            def _partes(self) -> tuple[str, str, dict[str, list[str]]]:
                u = urlsplit(self.path)
                ruta = unquote(u.path).lstrip("/")
                bucket, _, clave = ruta.partition("/")
                return bucket, clave, parse_qs(u.query)

            def do_PUT(self):  # noqa: N802
                bucket, clave, _ = self._partes()
                datos = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                with simulado._candado:
                    simulado.llamadas.append(("PUT", self.path, dict(self.headers)))
                    if not clave:                                   # crear bucket
                        if bucket in simulado.buckets:
                            return self._error(409, "BucketAlreadyOwnedByYou")
                        simulado.buckets.add(bucket)
                        return self._responder(200)
                    if bucket not in simulado.buckets:
                        return self._error(404, "NoSuchBucket")
                    simulado.objetos[(bucket, clave)] = (datos, self.headers.get("Content-Type", ""))
                self._responder(200)

            def do_GET(self):  # noqa: N802
                bucket, clave, q = self._partes()
                with simulado._candado:
                    simulado.llamadas.append(("GET", self.path, dict(self.headers)))
                    if bucket not in simulado.buckets:
                        return self._error(404, "NoSuchBucket")
                    if not clave and q.get("list-type") == ["2"]:
                        return self._listar(bucket, q)
                    obj = simulado.objetos.get((bucket, clave))
                if obj is None:
                    return self._error(404, "NoSuchKey")
                self._responder(200, obj[0], obj[1] or "application/octet-stream")

            def _listar(self, bucket: str, q: dict[str, list[str]]) -> None:
                prefijo = (q.get("prefix") or [""])[0]
                delim = (q.get("delimiter") or [""])[0]
                claves, comunes = [], set()
                for (b, k) in simulado.objetos:
                    if b != bucket or not k.startswith(prefijo):
                        continue
                    resto = k[len(prefijo):]
                    if delim and delim in resto:
                        comunes.add(prefijo + resto.split(delim, 1)[0] + delim)
                    else:
                        claves.append(k)
                xml = [f'<?xml version="1.0" encoding="UTF-8"?><ListBucketResult xmlns="{NS}">',
                       f"<Name>{bucket}</Name><Prefix>{escape(prefijo)}</Prefix><IsTruncated>false</IsTruncated>"]
                xml += [f"<Contents><Key>{escape(k)}</Key></Contents>" for k in sorted(claves)]
                xml += [f"<CommonPrefixes><Prefix>{escape(p)}</Prefix></CommonPrefixes>" for p in sorted(comunes)]
                xml.append("</ListBucketResult>")
                self._responder(200, "".join(xml).encode())

        self._servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        self.url = f"http://127.0.0.1:{self._servidor.server_address[1]}"
        self._hilo = threading.Thread(target=self._servidor.serve_forever, daemon=True)

    # ── utilidades para las aserciones ───────────────────────────────────────
    def claves(self, bucket: str | None = None) -> list[str]:
        return sorted(k for (b, k) in self.objetos if bucket is None or b == bucket)

    def puts(self) -> list[str]:
        return [ruta for (m, ruta, _) in self.llamadas if m == "PUT"]

    def __enter__(self) -> "SeaweedSimulado":
        self._hilo.start()
        return self

    def __exit__(self, *exc) -> None:
        self._servidor.shutdown()
        self._servidor.server_close()
