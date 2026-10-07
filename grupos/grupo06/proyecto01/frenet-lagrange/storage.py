"""
storage.py — Almacenamiento de resultados en SeaweedFS (API S3), sin índice compartido.

Cada cálculo se guarda bajo una "carpeta virtual" (prefijo S3) propia del grupo:

    s3://<IMG_BUCKET>/
    └── grupo06/
        ├── hessiana-20261006-153012-a1b2c3d4/
        │   ├── reporte.html        ← página interactiva (LaTeX + gráficos 3D)
        │   ├── grafico.png         ← lámina estática
        │   ├── resultado.json      ← JSON exacto del método
        │   ├── entrada.json        ← la solicitud validada
        │   └── meta.json           ← id, método, fecha, descripción y resumen (se escribe AL FINAL)
        └── lote-20261006-153500-9f8e7d6c/
            ├── reporte_combinado.html
            └── lote.json

Las URLs que se devuelven son PÚBLICAS (las sirve Caddy):
    ${PUBLIC_IMG_BASE_URL}/grupo06/<id>/reporte.html

¿Por qué ya no hay ``indice.json``?  Un índice único compartido obliga a leer-modificar-escribir
el mismo objeto desde todos los procesos/réplicas: dos escrituras simultáneas se pisan. Ahora
cada cálculo escribe SOLO en su propio prefijo (claves que nadie más usa) y el listado se
obtiene preguntándole a S3 qué prefijos existen (ListObjectsV2 con delimitador '/').

Variables de entorno:
    MCP_MATH_STORAGE      s3 | local | auto  (auto: s3 si el transporte es HTTP, local si es STDIO)
    SEAWEEDFS_S3_URL      http://seaweedfs:8333          (DNS interno de Docker)
    IMG_BUCKET            frenet-lagrange-imgs
    PUBLIC_IMG_BASE_URL   https://rac-unmsm.vekthos.org/img/frenet-lagrange
    MCP_GRUPO             grupo06                        (prefijo de todas las claves)
    S3_ACCESS_KEY / S3_SECRET_KEY / S3_REGION            (opcionales: firma AWS SigV4)
    MCP_MATH_RESULTADOS   carpeta del modo local         (def. ./resultados)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import tempfile
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import ProxyHandler, Request, build_opener

__all__ = ["Almacen", "BackendS3", "BackendLocal", "RegistroResultado", "ErrorAlmacen", "ID_PATRON",
           "ID_LOTE", "nuevo_id", "nuevo_id_lote", "GRUPO"]

log = logging.getLogger("mcp_math.storage")

GRUPO = os.environ.get("MCP_GRUPO", "grupo06")
IMG_BUCKET = "grupo06-frenet-lagrange-imgs"
PUBLIC_IMG_BASE_URL = "https://rac-unmsm.vekthos.org/img/grupo06-frenet-lagrange"
# 8 hex (uuid4) en los ids nuevos; se aceptan 6 hex para leer resultados antiguos.
ID_PATRON = re.compile(r"^(lagrange|hessiana|frenet)-\d{8}-\d{6}-[0-9a-f]{6}(?:[0-9a-f]{2})?$")
ID_LOTE = re.compile(r"^lote-\d{8}-\d{6}-[0-9a-f]{6}(?:[0-9a-f]{2})?$")
ARCHIVOS = {"html": "reporte.html", "png": "grafico.png", "resultado": "resultado.json",
            "entrada": "entrada.json", "meta": "meta.json"}
TIPOS = {".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8",
         ".png": "image/png", ".txt": "text/plain; charset=utf-8"}


class ErrorAlmacen(RuntimeError):
    """El almacenamiento no respondió como se esperaba (SeaweedFS caído, permisos...)."""


def _marca_tiempo() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def nuevo_id(metodo: str) -> str:
    """Id único aun con muchos usuarios a la vez: fecha UTC + 32 bits aleatorios de uuid4.
    (Con 3 bytes, dos cálculos en el mismo segundo tenían 1 en 16,7 millones de chocar; con
    4 bytes y la escritura en prefijos separados, el riesgo práctico desaparece.)"""
    return f"{metodo}-{_marca_tiempo()}-{uuid.uuid4().hex[:8]}"


def nuevo_id_lote() -> str:
    return f"lote-{_marca_tiempo()}-{uuid.uuid4().hex[:8]}"


def _orden(id_: str) -> str:
    """Clave de orden cronológico: la parte 'AAAAMMDD-HHMMSS-xxxx' del id."""
    return id_.split("-", 1)[1] if "-" in id_ else id_


def _tipo(nombre: str) -> str:
    return TIPOS.get(Path(nombre).suffix.lower(), "application/octet-stream")


# ════════════════════════════════════════════════════════════════════════════
# Backends: dónde viven los bytes
# ════════════════════════════════════════════════════════════════════════════
class Backend(Protocol):
    descripcion: str

    def preparar(self) -> bool: ...
    def subir(self, clave: str, datos: bytes, tipo: str) -> None: ...
    def leer(self, clave: str) -> bytes: ...
    def prefijos(self, prefijo: str) -> list[str]: ...
    def url_publica(self, clave: str) -> str: ...


class BackendS3:
    """Cliente S3 mínimo con la librería estándar (urllib). Compatible con SeaweedFS, MinIO y AWS.

    Sin credenciales hace peticiones anónimas (lo habitual en SeaweedFS de laboratorio); si se
    definen S3_ACCESS_KEY y S3_SECRET_KEY, firma cada petición con AWS Signature V4."""

    def __init__(self, url: str, bucket: str, url_publica_base: str, *, timeout: float = 20.0,
                 access_key: str | None = None, secret_key: str | None = None, region: str = "us-east-1") -> None:
        self.url = url.rstrip("/")
        self.bucket = bucket
        self.base_publica = url_publica_base.rstrip("/")
        self.timeout = timeout
        self.access_key, self.secret_key, self.region = access_key, secret_key, region
        self.descripcion = f"SeaweedFS S3 {self.url}/{self.bucket}"
        # Nunca usar el proxy HTTP del sistema para hablar con el S3 interno de la red Docker.
        self._abridor = build_opener(ProxyHandler({}))
        self._bucket_listo = False

    @classmethod
    def desde_entorno(cls) -> "BackendS3":
        return cls(
            os.environ.get("SEAWEEDFS_S3_URL", "http://seaweedfs:8333"),
            IMG_BUCKET,
            PUBLIC_IMG_BASE_URL,
            timeout=float(os.environ.get("S3_TIMEOUT", "20")),
            access_key=os.environ.get("S3_ACCESS_KEY") or None,
            secret_key=os.environ.get("S3_SECRET_KEY") or None,
            region=os.environ.get("S3_REGION", "us-east-1"))

    # ── HTTP ─────────────────────────────────────────────────────────────────
    def _ruta(self, clave: str = "") -> str:
        return f"/{quote(self.bucket)}/{quote(clave, safe='/-_.~')}"

    def _peticion(self, metodo: str, clave: str = "", datos: bytes | None = None,
                  consulta: dict[str, str] | None = None, tipo: str | None = None) -> bytes:
        ruta = self._ruta(clave)
        qs = "&".join(f"{quote(k, safe='-_.~')}={quote(v, safe='-_.~')}" for k, v in sorted((consulta or {}).items()))
        cuerpo = datos or b""
        cabeceras = {"x-amz-content-sha256": hashlib.sha256(cuerpo).hexdigest()}
        if tipo:
            cabeceras["Content-Type"] = tipo
        if self.access_key and self.secret_key:
            cabeceras.update(self._firma_v4(metodo, ruta, qs, cabeceras["x-amz-content-sha256"]))
        req = Request(self.url + ruta + (f"?{qs}" if qs else ""), data=datos if metodo == "PUT" else None,
                      method=metodo, headers=cabeceras)
        with self._abridor.open(req, timeout=self.timeout) as resp:
            return resp.read()

    def _firma_v4(self, metodo: str, ruta: str, qs: str, hash_cuerpo: str) -> dict[str, str]:
        """AWS Signature Version 4 (servicio 's3'), firmando host, x-amz-date y x-amz-content-sha256."""
        ahora = datetime.now(timezone.utc)
        fecha_amz, dia = ahora.strftime("%Y%m%dT%H%M%SZ"), ahora.strftime("%Y%m%d")
        host = urlsplit(self.url).netloc
        firmadas = "host;x-amz-content-sha256;x-amz-date"
        canonica = "\n".join([metodo, ruta, qs, f"host:{host}\nx-amz-content-sha256:{hash_cuerpo}\n"
                              f"x-amz-date:{fecha_amz}\n", firmadas, hash_cuerpo])
        alcance = f"{dia}/{self.region}/s3/aws4_request"
        a_firmar = "\n".join(["AWS4-HMAC-SHA256", fecha_amz, alcance, hashlib.sha256(canonica.encode()).hexdigest()])

        def h(k: bytes, m: str) -> bytes:
            return hmac.new(k, m.encode(), hashlib.sha256).digest()

        k = h(h(h(h(("AWS4" + str(self.secret_key)).encode(), dia), self.region), "s3"), "aws4_request")
        firma = hmac.new(k, a_firmar.encode(), hashlib.sha256).hexdigest()
        return {"x-amz-date": fecha_amz, "Authorization": f"AWS4-HMAC-SHA256 Credential={self.access_key}/{alcance}, "
                                                          f"SignedHeaders={firmadas}, Signature={firma}"}

    # ── Interfaz ─────────────────────────────────────────────────────────────
    def preparar(self) -> bool:
        """ensure_bucket(): PUT /<bucket>/. Nunca lanza: si SeaweedFS aún está arrancando (pasa al
        desplegar todos los contenedores a la vez) se reintenta en la primera subida."""
        try:
            self._peticion("PUT")
            self._bucket_listo = True
            log.info("Bucket '%s' creado en %s", self.bucket, self.url)
        except HTTPError as e:
            if e.code == 409:                         # BucketAlreadyExists / BucketAlreadyOwnedByYou
                self._bucket_listo = True
            else:
                log.warning("SeaweedFS respondió %s al crear el bucket '%s'", e.code, self.bucket)
        except (URLError, TimeoutError, OSError) as e:
            log.warning("SeaweedFS no disponible todavía en %s (%s); se reintentará al subir.", self.url, e)
        return self._bucket_listo

    ensure_bucket = preparar                          # nombre usado en el enunciado del laboratorio

    def subir(self, clave: str, datos: bytes, tipo: str) -> None:
        if not self._bucket_listo:
            self.preparar()
        try:
            self._peticion("PUT", clave, datos, tipo=tipo)
        except HTTPError as e:
            # SeaweedFS responde 404 (NoSuchBucket) o 403 si el bucket no existe: crearlo y reintentar una vez.
            if e.code in (403, 404) and self.preparar():
                try:
                    self._peticion("PUT", clave, datos, tipo=tipo)
                    return
                except HTTPError as e2:
                    raise ErrorAlmacen(f"SeaweedFS respondió {e2.code} al subir {clave}") from e2
            raise ErrorAlmacen(f"SeaweedFS respondió {e.code} al subir {clave}") from e
        except (URLError, TimeoutError, OSError) as e:
            raise ErrorAlmacen(f"No se pudo conectar con SeaweedFS ({self.url}): {e}") from e

    def leer(self, clave: str) -> bytes:
        try:
            return self._peticion("GET", clave)
        except HTTPError as e:
            if e.code == 404:
                raise KeyError(clave) from e
            raise ErrorAlmacen(f"SeaweedFS respondió {e.code} al leer {clave}") from e
        except (URLError, TimeoutError, OSError) as e:
            raise ErrorAlmacen(f"No se pudo conectar con SeaweedFS ({self.url}): {e}") from e

    def prefijos(self, prefijo: str) -> list[str]:
        """Sub-"carpetas" inmediatas de ``prefijo`` (ListObjectsV2 con delimitador '/'), paginando."""
        out: list[str] = []
        token: str | None = None
        while True:
            consulta = {"list-type": "2", "prefix": prefijo, "delimiter": "/", "max-keys": "1000"}
            if token:
                consulta["continuation-token"] = token
            try:
                xml = self._peticion("GET", "", consulta=consulta)
            except HTTPError as e:
                if e.code == 404:
                    return []
                raise ErrorAlmacen(f"SeaweedFS respondió {e.code} al listar {prefijo}") from e
            except (URLError, TimeoutError, OSError) as e:
                raise ErrorAlmacen(f"No se pudo conectar con SeaweedFS ({self.url}): {e}") from e
            raiz = ET.fromstring(xml)
            ns = raiz.tag[: raiz.tag.index("}") + 1] if raiz.tag.startswith("{") else ""
            for cp in raiz.iter(f"{ns}CommonPrefixes"):
                p = cp.findtext(f"{ns}Prefix") or ""
                out.append(p[len(prefijo):].strip("/"))
            if (raiz.findtext(f"{ns}IsTruncated") or "").lower() == "true":
                token = raiz.findtext(f"{ns}NextContinuationToken")
                if token:
                    continue
            return [p for p in out if p]

    def url_publica(self, clave: str) -> str:
        return f"{self.base_publica}/{quote(clave, safe='/-_.~')}"


class BackendLocal:
    """Misma estructura de claves, pero en una carpeta del disco. Para usar el servidor por STDIO
    en la PC (Claude Desktop, agente.py) sin SeaweedFS."""

    def __init__(self, base: str | Path, url_publica_base: str | None = None) -> None:
        self.base = Path(base).resolve()
        self.base_publica = (url_publica_base or "").rstrip("/") or None
        self.descripcion = f"carpeta local {self.base}"

    @classmethod
    def desde_entorno(cls) -> "BackendLocal":
        defecto = Path(__file__).resolve().parent / "resultados"
        return cls(os.environ.get("MCP_MATH_RESULTADOS") or defecto, os.environ.get("PUBLIC_LOCAL_BASE_URL"))

    def _ruta(self, clave: str) -> Path:
        ruta = (self.base / clave).resolve()
        if self.base not in ruta.parents:
            raise KeyError(clave)
        return ruta

    def preparar(self) -> bool:
        self.base.mkdir(parents=True, exist_ok=True)
        return True

    def subir(self, clave: str, datos: bytes, tipo: str) -> None:
        ruta = self._ruta(clave)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "wb") as fh:
            fh.write(datos)

    def leer(self, clave: str) -> bytes:
        ruta = self._ruta(clave)
        if not ruta.is_file():
            raise KeyError(clave)
        with open(ruta, "rb") as fh:
            return fh.read()

    def prefijos(self, prefijo: str) -> list[str]:
        carpeta = self.base / prefijo
        return [p.name for p in carpeta.iterdir() if p.is_dir()] if carpeta.is_dir() else []

    def url_publica(self, clave: str) -> str:
        if self.base_publica:
            return f"{self.base_publica}/{quote(clave, safe='/-_.~')}"
        return self._ruta(clave).as_uri()


# ════════════════════════════════════════════════════════════════════════════
# Almacén: lógica de resultados sobre cualquier backend
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class RegistroResultado:
    """Lo que se guarda en meta.json (y lo que devuelve listar)."""
    id: str
    metodo: str
    fecha: str
    descripcion: str
    resumen: list[str] = field(default_factory=list)
    archivos: dict[str, str] = field(default_factory=dict)      # nombre lógico → URL pública


def elegir_backend(transporte: str | None = None) -> Backend:
    modo = os.environ.get("MCP_MATH_STORAGE", "auto").lower()
    if modo == "auto":
        modo = "local" if (transporte or os.environ.get("MCP_TRANSPORT", "streamable-http")) == "stdio" else "s3"
    if modo == "local":
        return BackendLocal.desde_entorno()
    if modo == "s3":
        return BackendS3.desde_entorno()
    raise ValueError(f"MCP_MATH_STORAGE='{modo}' no es válido (usa s3, local o auto).")


class Almacen:
    """Guarda y recupera resultados. Cada id escribe solo bajo ``<grupo>/<id>/``: no hay objetos
    compartidos entre cálculos, así que varios procesos o réplicas pueden escribir a la vez."""

    def __init__(self, backend: Backend | None = None, grupo: str = GRUPO) -> None:
        self.backend: Backend = backend or elegir_backend()
        self.grupo = grupo.strip("/")
        self.descripcion = self.backend.descripcion

    def preparar(self) -> bool:
        """ensure_bucket() del backend (en local, crea la carpeta)."""
        return self.backend.preparar()

    @staticmethod
    def nuevo_id(metodo: str) -> str:
        return nuevo_id(metodo)

    # ── claves y URLs ────────────────────────────────────────────────────────
    def clave(self, id_: str, nombre: str) -> str:
        if not (ID_PATRON.match(id_) or ID_LOTE.match(id_)):
            raise KeyError(f"Id con formato inválido: '{id_}'.")
        if "/" in nombre or nombre.startswith("."):
            raise KeyError(f"Nombre de archivo inválido: '{nombre}'.")
        return f"{self.grupo}/{id_}/{nombre}"

    def url(self, id_: str, nombre: str) -> str:
        return self.backend.url_publica(self.clave(id_, nombre))

    # ── escritura ────────────────────────────────────────────────────────────
    def subir(self, id_: str, nombre: str, datos: bytes | str, tipo: str | None = None) -> str:
        if isinstance(datos, str):
            datos = datos.encode("utf-8")
        self.backend.subir(self.clave(id_, nombre), datos, tipo or _tipo(nombre))
        return self.url(id_, nombre)

    def subir_json(self, id_: str, nombre: str, datos: Any) -> str:
        return self.subir(id_, nombre, json.dumps(datos, ensure_ascii=False, indent=2, default=str))

    def guardar(self, id_: str, metodo: str, descripcion: str, entrada: dict, resultado: dict,
                resumen: list[str], archivos_locales: dict[str, str | Path] | None = None) -> RegistroResultado:
        """Sube los artefactos del cálculo. ``archivos_locales``: {"html": ruta, "png": ruta} generados por
        el proceso de cálculo en una carpeta temporal. meta.json se escribe al final: si existe, el
        resultado está completo."""
        urls: dict[str, str] = {}
        for clave_logica, ruta in (archivos_locales or {}).items():
            if clave_logica in ARCHIVOS and ruta and Path(ruta).is_file():
                urls[clave_logica] = self.subir(id_, ARCHIVOS[clave_logica], Path(ruta).read_bytes())
        urls["resultado"] = self.subir_json(id_, ARCHIVOS["resultado"], resultado)
        urls["entrada"] = self.subir_json(id_, ARCHIVOS["entrada"], entrada)
        reg = RegistroResultado(id=id_, metodo=metodo,
                                fecha=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                descripcion=descripcion[:200], resumen=resumen[:12], archivos=urls)
        self.subir_json(id_, ARCHIVOS["meta"], asdict(reg))
        return reg

    # ── lectura ──────────────────────────────────────────────────────────────
    def leer(self, id_: str, nombre: str) -> bytes:
        return self.backend.leer(self.clave(id_, nombre))

    def leer_json(self, id_: str, nombre: str) -> Any:
        return json.loads(self.leer(id_, nombre).decode("utf-8"))

    def ids(self, patron: re.Pattern[str] = ID_PATRON) -> list[str]:
        """Ids existentes (más recientes primero), sin índice: se listan los prefijos del grupo."""
        return sorted((p for p in self.backend.prefijos(self.grupo + "/") if patron.match(p)),
                      key=_orden, reverse=True)

    def listar(self, metodo: str | None = None, limite: int = 20) -> list[dict]:
        out: list[dict] = []
        for id_ in self.ids():
            if metodo and not id_.startswith(metodo + "-"):
                continue
            try:
                m = self.leer_json(id_, ARCHIVOS["meta"])
            except KeyError:                          # cálculo a medio guardar: se omite
                continue
            out.append({"id": id_, "metodo": m.get("metodo"), "fecha": m.get("fecha"),
                        "descripcion": m.get("descripcion", ""), "html": m.get("archivos", {}).get("html")})
            if len(out) >= limite:
                break
        return out

    def obtener(self, id_: str) -> dict:
        if not ID_PATRON.match(id_):
            raise KeyError(f"Id con formato inválido: '{id_}'.")
        try:
            meta = self.leer_json(id_, ARCHIVOS["meta"])
        except KeyError as e:
            raise KeyError(f"No existe el resultado '{id_}'.") from e
        out: dict[str, Any] = {"id": id_, "metodo": meta.get("metodo"), "fecha": meta.get("fecha"),
                               "descripcion": meta.get("descripcion", ""), "resumen": meta.get("resumen", []),
                               "archivos": meta.get("archivos", {})}
        for nombre in ("entrada", "resultado"):
            try:
                out[nombre] = self.leer_json(id_, ARCHIVOS[nombre])
            except KeyError:
                out[nombre] = None
        return out
