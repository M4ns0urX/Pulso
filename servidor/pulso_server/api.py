"""API HTTP + dashboard.

Só usa a biblioteca padrão do Python. Rotas:
  GET  /                              dashboard
  GET  /api/mapa                      mapa da mina (níveis, galerias, âncoras, gateways)
  GET  /api/estado                    estado atual (trabalhadores, alertas, KPIs)
  GET  /api/stream                    o mesmo estado a cada 1 s (Server-Sent Events)
  GET  /api/historico?dispositivo=ID&minutos=5
  GET  /api/relatorio                 resumo para relatório NR-22
  POST /api/alertas/ID/recebido       operador assume o alerta
  POST /api/alertas/ID/encerrar       operador encerra ({"falso_alarme": true})
  POST /api/sim/ACAO/ID               ações do digital twin (sos, gas, queda, sem_sinal, normalizar)
"""
from __future__ import annotations

import json
import mimetypes
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

from .servidor import Servidor


def criar_servidor_http(srv: Servidor, pasta_dashboard: Path, porta: int = 8080,
                        acao_sim: Callable[[str, int], bool] | None = None) -> ThreadingHTTPServer:
    pasta_dashboard = Path(pasta_dashboard).resolve()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):  # silencioso
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False, default=float).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path == "/api/mapa":
                return self._json(srv.mina.para_json())
            if u.path == "/api/estado":
                return self._json(srv.estado())
            if u.path == "/api/historico":
                return self._json(srv.historico(int(q["dispositivo"][0]), float(q.get("minutos", [5])[0])))
            if u.path == "/api/relatorio":
                return self._json(srv.relatorio())
            if u.path == "/api/stream":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                try:
                    while True:
                        data = json.dumps(srv.estado(), ensure_ascii=False, default=float)
                        self.wfile.write(f"data: {data}\n\n".encode())
                        self.wfile.flush()
                        time.sleep(1)
                except (BrokenPipeError, ConnectionResetError):
                    return
            # arquivos estáticos do dashboard
            rel = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
            arq = (pasta_dashboard / rel).resolve()
            if pasta_dashboard not in arq.parents or not arq.is_file():
                return self._json({"erro": "não encontrado"}, 404)
            body = arq.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", (mimetypes.guess_type(arq.name)[0] or "application/octet-stream")
                             + ("; charset=utf-8" if arq.suffix in (".html", ".js", ".css") else ""))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            u = urlparse(self.path)
            n = int(self.headers.get("Content-Length") or 0)
            corpo = json.loads(self.rfile.read(n) or b"{}") if n else {}
            partes = u.path.strip("/").split("/")
            if len(partes) == 4 and partes[:2] == ["api", "alertas"]:
                aid = int(partes[2])
                if partes[3] == "recebido":
                    return self._json({"ok": srv.reconhecer(aid, corpo.get("operador", "Operador"))})
                if partes[3] == "encerrar":
                    return self._json({"ok": srv.encerrar(aid, corpo.get("operador", "Operador"),
                                                          bool(corpo.get("falso_alarme")))})
            if len(partes) == 4 and partes[:2] == ["api", "sim"] and acao_sim:
                return self._json({"ok": acao_sim(partes[2], int(partes[3]))})
            return self._json({"erro": "rota inválida"}, 404)

    httpd = ThreadingHTTPServer(("0.0.0.0", porta), Handler)
    httpd.daemon_threads = True
    return httpd
