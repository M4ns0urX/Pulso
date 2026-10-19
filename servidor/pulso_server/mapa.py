"""Mapa da mina: níveis, galerias, zonas, âncoras UWB e gateways LoRa.

Carregado de um JSON (servidor/config/mina_exemplo.json). Usado pelo
servidor para descobrir a zona de cada leitura e pelo dashboard para
desenhar o mapa. O digital twin usa o mesmo arquivo para simular a mina.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_PADRAO = Path(__file__).resolve().parent.parent / "config" / "mina_exemplo.json"


@dataclass
class Galeria:
    zona: str
    a: tuple[float, float]
    b: tuple[float, float]

    @property
    def comprimento(self) -> float:
        return math.dist(self.a, self.b)

    def ponto(self, t: float) -> tuple[float, float]:
        return (self.a[0] + (self.b[0] - self.a[0]) * t, self.a[1] + (self.b[1] - self.a[1]) * t)

    def projetar(self, p: tuple[float, float]) -> tuple[float, tuple[float, float], float]:
        """Retorna (distância, ponto mais próximo, t) de p até a galeria."""
        ax, ay = self.a
        dx, dy = self.b[0] - ax, self.b[1] - ay
        L2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        q = (ax + dx * t, ay + dy * t)
        return math.dist(p, q), q, t


@dataclass
class Ancora:
    id: int
    nivel: str
    x: float
    y: float
    z: float


@dataclass
class Nivel:
    id: str
    nome: str
    z: float
    galerias: list[Galeria]
    gateways: list[tuple[float, float]]
    ancoras: list[Ancora] = field(default_factory=list)

    def zona_de(self, x: float, y: float) -> tuple[str, float]:
        """Zona da galeria mais próxima e a distância até ela (m)."""
        melhor = min(self.galerias, key=lambda g: g.projetar((x, y))[0])
        return melhor.zona, melhor.projetar((x, y))[0]

    def encaixar(self, x: float, y: float) -> tuple[float, float]:
        """Map-matching: leva o ponto para dentro da galeria mais próxima."""
        g = min(self.galerias, key=lambda g: g.projetar((x, y))[0])
        return g.projetar((x, y))[1]

    @property
    def zonas(self) -> list[str]:
        return sorted({g.zona for g in self.galerias})


@dataclass
class Mina:
    nome: str
    niveis: dict[str, Nivel]
    trabalhadores: list[dict]

    def nivel_por_z(self, z: float) -> Nivel:
        return min(self.niveis.values(), key=lambda n: abs(n.z - z))

    def para_json(self) -> dict:
        return {
            "nome": self.nome,
            "niveis": [
                {
                    "id": n.id, "nome": n.nome, "z": n.z, "zonas": n.zonas,
                    "galerias": [{"zona": g.zona, "a": g.a, "b": g.b} for g in n.galerias],
                    "gateways": n.gateways,
                    "ancoras": [{"id": a.id, "x": a.x, "y": a.y} for a in n.ancoras],
                }
                for n in self.niveis.values()
            ],
        }


def _gerar_ancoras(nivel: Nivel, esp: float, desloc: float, teto: float, prox_id: int) -> int:
    """Âncoras a cada `esp` metros, alternando entre as paredes (zigue-zague)."""
    vistos: list[tuple[float, float]] = []
    lado = 1
    for g in nivel.galerias:
        n = max(1, int(g.comprimento // esp))
        dx, dy = g.b[0] - g.a[0], g.b[1] - g.a[1]
        L = g.comprimento or 1
        nx, ny = -dy / L, dx / L  # normal à galeria
        for i in range(n + 1):
            px, py = g.ponto(i / n)
            if any(math.dist((px, py), v) < esp * 0.5 for v in vistos):
                continue
            vistos.append((px, py))
            nivel.ancoras.append(Ancora(prox_id, nivel.id, round(px + nx * desloc * lado, 2),
                                        round(py + ny * desloc * lado, 2), nivel.z + teto))
            prox_id += 1
            lado = -lado
    return prox_id


def carregar(caminho: str | Path = CONFIG_PADRAO) -> Mina:
    cfg = json.loads(Path(caminho).read_text(encoding="utf-8"))
    niveis = {}
    prox = 1
    ac = cfg.get("ancoras", {})
    for n in cfg["niveis"]:
        nivel = Nivel(
            id=n["id"], nome=n["nome"], z=float(n["z"]),
            galerias=[Galeria(g["zona"], tuple(g["de"]), tuple(g["ate"])) for g in n["galerias"]],
            gateways=[tuple(p) for p in n["gateways"]],
        )
        prox = _gerar_ancoras(nivel, ac.get("espacamento_m", 20), ac.get("deslocamento_parede_m", 2),
                              ac.get("altura_teto_m", 3.0), prox)
        niveis[nivel.id] = nivel
    return Mina(cfg["nome"], niveis, cfg.get("trabalhadores", []))
