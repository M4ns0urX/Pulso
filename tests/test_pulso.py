"""Testes do servidor e do digital twin:  python3 -m unittest discover tests -v"""
import math
import random
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "servidor"))
sys.path.insert(0, str(RAIZ / "digital-twin"))

from pulso_server import regras                                  # noqa: E402
from pulso_server.mapa import carregar                           # noqa: E402
from pulso_server.packet import (DL_SOS_ACK, FLAG_SOS, TYPE_PERIODIC, TYPE_SOS,  # noqa: E402
                                 Packet, PacketError)
from pulso_server.servidor import Servidor                       # noqa: E402
from pulso_twin import uwb                                       # noqa: E402
from pulso_twin.simulacao import Simulacao                       # noqa: E402

# mesmo vetor usado em firmware/tests/test_main.c
VETOR = "1142010078e768805fd204c8ff48f447010728e2"


class Relogio:
    def __init__(self, t=1_760_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def pacote(dev=321, seq=0, bpm=75, spo2=97, flags=0, tipo=TYPE_PERIODIC, ts=1_760_000_000, x=100, y=60, z=-298.8, bat=80):
    return Packet(tipo, dev, ts, bpm, spo2, x, y, z, bat, flags, seq).encode()


class TestPacote(unittest.TestCase):
    def test_vetor_igual_ao_firmware(self):
        p = Packet(TYPE_SOS, 0x0142, 1760000000, 128, 95, 123.4, -5.6, -300.0, 71, FLAG_SOS, 7)
        self.assertEqual(p.encode().hex(), VETOR)

    def test_ida_e_volta(self):
        p = Packet.decode(bytes.fromhex(VETOR))
        self.assertEqual((p.device_id, p.bpm, p.spo2, p.y, p.z), (0x0142, 128, 95, -5.6, -300.0))
        self.assertTrue(p.sos)

    def test_crc_rejeita_corrompido(self):
        b = bytearray.fromhex(VETOR)
        b[7] ^= 1
        with self.assertRaises(PacketError):
            Packet.decode(bytes(b))


class TestUWB(unittest.TestCase):
    def test_precisao_em_galeria(self):
        mina = carregar()
        nivel = mina.niveis["N300"]
        rng = random.Random(1)
        erros = []
        for g in nivel.galerias:
            for t in (0.2, 0.5, 0.8):
                x, y = g.ponto(t)
                sol = uwb.resolver(uwb.medir(nivel.ancoras, x, y, nivel.z, rng), nivel.z, (x + 1, y + 1))
                self.assertIsNotNone(sol)
                erros.append(math.dist((sol[0], sol[1]), (x, y)))
        self.assertLess(sum(erros) / len(erros), 0.10, "erro médio < 10 cm")


class TestServidor(unittest.TestCase):
    def setUp(self):
        self.rel = Relogio()
        self.dl = []
        self.srv = Servidor(carregar(), relogio=self.rel, downlink=lambda d, b: self.dl.append((d, b)))

    def test_enriquece_zona_e_deduplica(self):
        l = self.srv.receber_uplink(pacote(x=100.3, y=60.4), "GW1")
        self.assertEqual(l["zona_id"], "N300:Principal")
        self.assertIsNone(self.srv.receber_uplink(pacote(x=100.3, y=60.4), "GW2"))   # mesmo pacote, outro gateway
        self.assertEqual(self.srv.stats["duplicados"], 1)

    def test_fluxo_sos(self):
        self.srv.receber_uplink(pacote(seq=1, flags=FLAG_SOS, tipo=TYPE_SOS))
        al = self.srv.estado()["alertas"]
        self.assertEqual(al[0]["tipo"], "SOS")
        self.rel.t += 35
        self.srv.tick()
        self.assertEqual(self.srv.estado()["alertas"][0]["escalonamento"], 1)      # supervisor avisado
        self.assertTrue(self.srv.reconhecer(al[0]["id"], "Op"))
        self.assertEqual(self.dl[-1], (321, bytes([DL_SOS_ACK])))                  # LED verde na braçadeira
        self.assertTrue(self.srv.encerrar(al[0]["id"], "Op"))
        self.srv.receber_uplink(pacote(seq=2, flags=FLAG_SOS))                     # braçadeira ainda não soube
        self.assertEqual(self.srv.estado()["alertas"], [])

    def test_spo2_com_histerese(self):
        for i, s in enumerate([97, 85, 84, 84]):
            self.rel.t += 5
            self.srv.receber_uplink(pacote(seq=i, spo2=s, ts=int(self.rel.t)))
        self.assertTrue(any(a["tipo"] == "SPO2_BAIXO" for a in self.srv.estado()["alertas"]))
        for i, s in enumerate([91, 91, 91], 10):                                   # ainda perto do limite
            self.rel.t += 5
            self.srv.receber_uplink(pacote(seq=i, spo2=s, ts=int(self.rel.t)))
        self.assertTrue(any(a["tipo"] == "SPO2_BAIXO" for a in self.srv.estado()["alertas"]))
        for i, s in enumerate([97, 97, 97], 20):
            self.rel.t += 5
            self.srv.receber_uplink(pacote(seq=i, spo2=s, ts=int(self.rel.t)))
        self.assertFalse(any(a["tipo"] == "SPO2_BAIXO" for a in self.srv.estado()["alertas"]))

    def test_bpm_alto_so_depois_de_30s(self):
        for i in range(10):
            self.rel.t += 5
            self.srv.receber_uplink(pacote(seq=i, bpm=170, ts=int(self.rel.t)))
            tipos = [a["tipo"] for a in self.srv.estado()["alertas"]]
            self.assertEqual("BPM_ALTO" in tipos, i >= 6, f"leitura {i}")  # 30 s fora da faixa

    def test_sem_sinal(self):
        self.srv.receber_uplink(pacote())
        self.rel.t += regras.SEM_SINAL_S + 1
        self.srv.tick()
        self.assertEqual(self.srv.estado()["alertas"][0]["tipo"], "SEM_SINAL")


class TestDigitalTwin(unittest.TestCase):
    def test_ponta_a_ponta(self):
        mina = carregar()
        sim = Simulacao(mina)
        srv = Servidor(mina, relogio=sim.agora, downlink=sim.rede.agendar_downlink)
        sim.rede.entregar = srv.receber_uplink
        for s in range(100):
            sim.rodar(1)
            srv.tick()
        est = srv.estado()
        self.assertEqual(est["kpis"]["no_subsolo"], 12)
        for t in est["trabalhadores"]:   # posição bate com a real (pacote tem até 5 s, ~1 m/s)
            real = sim.trabalhadores[t["id"]].xy
            self.assertLess(math.dist(real, (t["x"], t["y"])), 6.0, t["nome"])
        sos = [a for a in est["alertas"] if a["tipo"] == "SOS"]
        self.assertTrue(sos, "SOS do roteiro chegou ao servidor")
        srv.reconhecer(sos[0]["id"])
        sim.rodar(12)
        self.assertEqual(sim.bracadeiras[321].led, "verde", "confirmação voltou até a braçadeira")


if __name__ == "__main__":
    unittest.main()
