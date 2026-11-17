"""Comunicación entre nodos: un servidor HTTP con un hilo por conexión y un
cliente HTTP que reutiliza una conexión por hilo (keep-alive).

Se usa solo la biblioteca estándar para que cada nodo sea un proceso Python
independiente, sin dependencias, que se puede ejecutar en un contenedor, en
una máquina virtual o en la misma máquina en otro puerto.
"""
from __future__ import annotations

import http.client
import json
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Iterator


class ErrorRed(Exception):
    """Falla de comunicación: el otro nodo no responde o respondió con error."""

    def __init__(self, mensaje: str, estado: int | None = None, cuerpo: Any = None):
        super().__init__(mensaje)
        self.estado = estado
        self.cuerpo = cuerpo


# --------------------------------------------------------------------------
# Cliente
# --------------------------------------------------------------------------
class ClienteHTTP:
    """Cliente JSON con una conexión persistente por hilo.

    Cada hilo que llama conserva su propia conexión (``threading.local``), de
    modo que varios hilos pueden llamar al mismo nodo en paralelo sin compartir
    el socket y sin abrir una conexión TCP nueva en cada solicitud.
    """

    def __init__(self, url_base: str, tiempo_espera: float = 5.0):
        partes = urllib.parse.urlsplit(url_base)
        self.url_base = url_base.rstrip("/")
        self.host = partes.hostname or "127.0.0.1"
        self.puerto = partes.port or 80
        self.tiempo_espera = tiempo_espera
        self._local = threading.local()

    def _conexion(self) -> http.client.HTTPConnection:
        con = getattr(self._local, "con", None)
        if con is None:
            con = http.client.HTTPConnection(self.host, self.puerto, timeout=self.tiempo_espera)
            self._local.con = con
        return con

    def _descartar(self) -> None:
        con = getattr(self._local, "con", None)
        if con is not None:
            con.close()
        self._local.con = None

    def llamar(self, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else b""
        cabeceras = {"Content-Type": "application/json", "Content-Length": str(len(datos))}
        # Un reintento solo si la conexión reutilizada estaba cerrada por el otro lado.
        for intento in (1, 2):
            con = self._conexion()
            try:
                con.request(metodo, ruta, body=datos, headers=cabeceras)
                resp = con.getresponse()
                texto = resp.read()
                break
            except (http.client.RemoteDisconnected, BrokenPipeError, ConnectionResetError) as e:
                self._descartar()
                if intento == 2:
                    raise ErrorRed(f"{metodo} {self.url_base}{ruta}: {e}") from e
            except (OSError, http.client.HTTPException) as e:
                self._descartar()
                raise ErrorRed(f"{metodo} {self.url_base}{ruta}: {e}") from e
        valor = json.loads(texto) if texto else None
        if resp.status >= 400:
            raise ErrorRed(f"{metodo} {self.url_base}{ruta} -> {resp.status}", resp.status, valor)
        return valor


# --------------------------------------------------------------------------
# Servidor
# --------------------------------------------------------------------------
class Solicitud:
    def __init__(self, metodo: str, ruta: str, parametros: dict, consulta: dict, cuerpo: Any):
        self.metodo = metodo
        self.ruta = ruta
        self.parametros = parametros
        self.consulta = consulta
        self.cuerpo = cuerpo


class Respuesta:
    def __init__(self, estado: int = 200, cuerpo: Any = None, tipo: str = "application/json",
                 cabeceras: dict | None = None):
        self.estado = estado
        self.cuerpo = cuerpo
        self.tipo = tipo
        self.cabeceras = cabeceras or {}


class Flujo:
    """Respuesta de eventos enviados por el servidor (SSE): un iterador de textos."""

    def __init__(self, eventos: Iterator[str]):
        self.eventos = eventos


Manejo = Callable[[Solicitud], Any]


class Enrutador:
    def __init__(self) -> None:
        self._rutas: list[tuple[str, re.Pattern, Manejo]] = []

    def ruta(self, metodo: str, patron: str):
        regex = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", patron) + "$")

        def decorador(funcion: Manejo) -> Manejo:
            self._rutas.append((metodo, regex, funcion))
            return funcion

        return decorador

    def buscar(self, metodo: str, ruta: str):
        for m, regex, funcion in self._rutas:
            coincide = regex.match(ruta)
            if coincide and m == metodo:
                return funcion, coincide.groupdict()
        return None, None


def crear_servidor(host: str, puerto: int, enrutador: Enrutador) -> ThreadingHTTPServer:
    """Servidor HTTP/1.1 que atiende cada conexión en un hilo propio."""

    class Manejador(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):  # silencio: cada nodo lleva su propia bitácora
            pass

        def _atender(self, metodo: str) -> None:
            partes = urllib.parse.urlsplit(self.path)
            funcion, parametros = enrutador.buscar(metodo, partes.path)
            largo = int(self.headers.get("Content-Length") or 0)
            crudo = self.rfile.read(largo) if largo else b""
            if funcion is None:
                self._enviar(Respuesta(404, {"error": "ruta no encontrada"}))
                return
            try:
                cuerpo = json.loads(crudo) if crudo and "json" in (self.headers.get("Content-Type") or "") else crudo
                consulta = dict(urllib.parse.parse_qsl(partes.query))
                resultado = funcion(Solicitud(metodo, partes.path, parametros, consulta, cuerpo))
            except ValueError as e:
                resultado = Respuesta(400, {"error": str(e)})
            except Exception as e:  # noqa: BLE001 - el servidor no debe caerse por una solicitud
                resultado = Respuesta(500, {"error": f"{type(e).__name__}: {e}"})
            if isinstance(resultado, Flujo):
                self._enviar_flujo(resultado)
            elif isinstance(resultado, Respuesta):
                self._enviar(resultado)
            else:
                self._enviar(Respuesta(200, resultado))

        def _enviar(self, r: Respuesta) -> None:
            if isinstance(r.cuerpo, (bytes, str)):
                datos = r.cuerpo.encode("utf-8") if isinstance(r.cuerpo, str) else r.cuerpo
            else:
                datos = json.dumps(r.cuerpo, ensure_ascii=False).encode("utf-8")
            try:
                self.send_response(r.estado)
                self.send_header("Content-Type", r.tipo + ("; charset=utf-8" if r.tipo.startswith("text") or "json" in r.tipo else ""))
                self.send_header("Content-Length", str(len(datos)))
                for k, v in r.cabeceras.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(datos)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection = True

        def _enviar_flujo(self, f: Flujo) -> None:
            self.close_connection = True
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                for texto in f.eventos:
                    self.wfile.write(texto.encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass
            finally:
                cerrar = getattr(f.eventos, "close", None)
                if cerrar:
                    cerrar()

        def do_GET(self):
            self._atender("GET")

        def do_POST(self):
            self._atender("POST")

        def do_DELETE(self):
            self._atender("DELETE")

    servidor = ThreadingHTTPServer((host, puerto), Manejador)
    servidor.daemon_threads = True
    return servidor


def iniciar_en_hilo(servidor: ThreadingHTTPServer, nombre: str) -> threading.Thread:
    hilo = threading.Thread(target=servidor.serve_forever, name=nombre, daemon=True)
    hilo.start()
    return hilo
