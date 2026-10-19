"""Demonstração completa da Pulso: digital twin + servidor + dashboard.

    python3 run_demo.py                 # abre em http://localhost:8080
    python3 run_demo.py --velocidade 3  # simulação 3x mais rápida
    python3 run_demo.py --sem-roteiro   # sem eventos automáticos

Só precisa de Python 3.10+ (nenhuma biblioteca externa).
"""
import argparse
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "servidor"))
sys.path.insert(0, str(RAIZ / "digital-twin"))

from pulso_server.api import criar_servidor_http  # noqa: E402
from pulso_server.db import Banco                 # noqa: E402
from pulso_server.mapa import carregar            # noqa: E402
from pulso_server.servidor import Servidor        # noqa: E402
from pulso_twin.simulacao import ROTEIRO_PADRAO, Simulacao  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Demonstração Pulso")
    ap.add_argument("--porta", type=int, default=8080)
    ap.add_argument("--velocidade", type=float, default=1.0)
    ap.add_argument("--sem-roteiro", action="store_true")
    ap.add_argument("--banco", default=":memory:", help="arquivo SQLite (padrão: em memória)")
    a = ap.parse_args()

    mina = carregar()
    sim = Simulacao(mina, velocidade=a.velocidade, roteiro=[] if a.sem_roteiro else ROTEIRO_PADRAO)
    srv = Servidor(mina, Banco(a.banco), relogio=sim.agora, downlink=sim.rede.agendar_downlink)
    sim.rede.entregar = srv.receber_uplink        # rede LoRa → servidor

    def rotina():
        while True:
            srv.tick()
            time.sleep(1 / max(a.velocidade, 1))
    threading.Thread(target=rotina, daemon=True).start()
    sim.iniciar()

    httpd = criar_servidor_http(srv, RAIZ / "dashboard", a.porta, acao_sim=sim.acao)
    print(f"\n  Pulso rodando: http://localhost:{a.porta}\n")
    print("  Roteiro: oxigenação baixa do Marcos (40 s), SOS do Carlos (75 s), queda do Diego (130 s),")
    print("           braçadeira do Sérgio sem sinal (170 s). Ctrl+C para sair.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
