"""Lê pacotes em hexadecimal (um por linha) e passa pelo pipeline do servidor.

Liga o firmware simulado ao servidor:
    cd firmware && make && ./build/pulso_sim --hex 30 | python3 ../servidor/ingest_stdin.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pulso_server.mapa import carregar          # noqa: E402
from pulso_server.servidor import Servidor      # noqa: E402

srv = Servidor(carregar())
for linha in sys.stdin:
    linha = linha.strip()
    if not linha:
        continue
    l = srv.receber_uplink(bytes.fromhex(linha), "stdin")
    if l is None:
        print(f"descartado: {linha}")
        continue
    nome = srv.trab[l["bracadeira_id"]]["nome"]
    print(f"{nome:10s} zona={l['zona_id']:14s} BPM={l['bpm']} SpO2={l['spo2']}% "
          f"pos=({l['x']:.1f}, {l['y']:.1f}) bat={l['bateria']}% flags=0x{l['flags']:02x}")
for e in reversed(srv.eventos):
    print("EVENTO:", e["texto"])
