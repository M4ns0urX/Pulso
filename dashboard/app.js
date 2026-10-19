/* Dashboard da sala de controle Pulso.
 * Recebe o estado do servidor a cada 1 s (Server-Sent Events em /api/stream). */
"use strict";

const NS = "http://www.w3.org/2000/svg";
const ESC = ["Sala de controle", "Supervisor avisado", "Brigada acionada"];
const TIPO_TXT = { SOS: "SOS", SPO2_BAIXO: "SpO2", QUEDA: "QUEDA", BPM_ALTO: "BPM", BPM_BAIXO: "BPM",
                   SEM_SINAL: "SINAL", BATERIA_BAIXA: "BATERIA", SEM_CONTATO: "SENSOR" };

let mapa = null, estado = null, nivelAtivo = null, selecionado = null;
const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, pai) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (pai) pai.appendChild(e);
  return e;
}
const hora = (t) => new Date(t * 1000).toLocaleTimeString("pt-BR");
const idade = (s) => (s < 60 ? `há ${s} s` : `há ${Math.floor(s / 60)} min ${s % 60} s`);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function post(url, corpo = {}) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });
  return r.json();
}

/* ------------------------------------------------------------------ mapa */
function desenharMapa() {
  const svg = $("svgmapa");
  svg.innerHTML = "";
  const nivel = mapa.niveis.find((n) => n.id === nivelAtivo);
  const xs = [], ys = [];
  nivel.galerias.forEach((g) => { xs.push(g.a[0], g.b[0]); ys.push(g.a[1], g.b[1]); });
  const m = 12, x0 = Math.min(...xs) - m, y0 = Math.min(...ys) - m;
  svg.setAttribute("viewBox", `${x0} ${y0} ${Math.max(...xs) - x0 + m} ${Math.max(...ys) - y0 + m}`);

  const gT = el("g", {}, svg);
  nivel.galerias.forEach((g) =>
    el("line", { x1: g.a[0], y1: g.a[1], x2: g.b[0], y2: g.b[1], class: "tunel", "stroke-width": 7 }, gT));
  const vistos = new Set();
  nivel.galerias.forEach((g) => {
    if (vistos.has(g.zona)) return;
    vistos.add(g.zona);
    const vert = Math.abs(g.b[0] - g.a[0]) < Math.abs(g.b[1] - g.a[1]);
    const t = el("text", { x: (g.a[0] + g.b[0]) / 2 + (vert ? 5 : 0), y: (g.a[1] + g.b[1]) / 2 - (vert ? 0 : 5),
                           class: "zona-txt", "text-anchor": vert ? "start" : "middle" }, gT);
    t.textContent = g.zona.toUpperCase();
  });
  nivel.ancoras.forEach((a) => el("rect", { x: a.x - 0.9, y: a.y - 0.9, width: 1.8, height: 1.8, class: "anc-svg",
                                            transform: `rotate(45 ${a.x} ${a.y})` }, gT));
  nivel.gateways.forEach(([x, y]) => el("rect", { x: x - 1.4, y: y - 1.4, width: 2.8, height: 2.8, rx: 0.6, class: "gw-svg" }, gT));
  el("g", { id: "camada-trab" }, svg);
}

function desenharTrabalhadores() {
  const camada = $("camada-trab");
  if (!camada || !estado) return;
  camada.innerHTML = "";
  const cor = { normal: "#2EA36B", aviso: "#C98A12", alto: "#D35400", critico: "#B83227" };
  estado.trabalhadores.filter((t) => t.nivel === nivelAtivo).forEach((t) => {
    const g = el("g", { class: "trab" + (t.id === selecionado ? " sel" : "") }, camada);
    g.addEventListener("click", () => selecionar(t.id));
    if (t.status === "critico") {
      el("circle", { cx: t.x, cy: t.y, r: 2.4, class: "onda", "stroke-width": 0.5 }, g);
    }
    const c = el("circle", { cx: t.x, cy: t.y, r: t.status === "critico" ? 2.6 : 2.1, class: "base",
                             fill: t.sem_sinal ? "#fff" : cor[t.status] }, g);
    if (t.sem_sinal) { c.setAttribute("stroke", "#8995A5"); c.setAttribute("stroke-dasharray", "1 .8"); c.setAttribute("stroke-width", ".7"); }
    const tx = el("text", { x: t.x + 3.4, y: t.y + 1 }, g);
    tx.textContent = t.nome;
    if (t.sos_confirmado) {
      const a = el("text", { x: t.x + 3.4, y: t.y + 4.6, class: "ajuda" }, g);
      a.textContent = "ajuda a caminho";
    }
  });
}

function desenharAbas() {
  const abas = $("abas");
  abas.innerHTML = "";
  mapa.niveis.forEach((n) => {
    const b = document.createElement("button");
    const qtd = estado ? estado.trabalhadores.filter((t) => t.nivel === n.id).length : 0;
    const crit = estado ? estado.trabalhadores.some((t) => t.nivel === n.id && t.status === "critico") : false;
    b.innerHTML = `${esc(n.nome)}<span class="n">${qtd}${crit ? " ⚠" : ""}</span>`;
    if (n.id === nivelAtivo) b.className = "ativo";
    b.onclick = () => { nivelAtivo = n.id; desenharAbas(); desenharMapa(); desenharTrabalhadores(); };
    abas.appendChild(b);
  });
}

/* ------------------------------------------------------------------ alertas */
function desenharAlertas() {
  const box = $("alertas");
  box.innerHTML = "";
  estado.alertas.forEach((a) => {
    const d = document.createElement("div");
    d.className = `alerta ${a.status === "recebido" ? "recebido" : a.nivel} ${a.status}`;
    const zona = (a.zona_id || "").split(":")[1] || "?";
    const etapa = a.status === "recebido" ? `Recebido por ${esc(a.atendido_por)} · resgate a caminho`
                                          : (a.nivel === "aviso" ? "" : ESC[a.escalonamento]);
    d.innerHTML = `
      <span class="ic">${TIPO_TXT[a.tipo] || a.tipo}</span>
      <div class="txt"><b>${esc(a.titulo)} · ${esc(a.nome)}</b>
        <small>Zona ${esc(zona)}${a.detalhe ? " · " + esc(a.detalhe) : ""} · ${idade(a.idade_s)}${etapa ? " · " + etapa : ""}</small></div>`;
    const btn = document.createElement("button");
    if (a.status === "aberto" && a.nivel !== "aviso") {
      btn.textContent = "RECEBIDO";
      btn.onclick = () => post(`/api/alertas/${a.id}/recebido`, { operador: "Operador" });
    } else {
      btn.textContent = "Encerrar";
      btn.onclick = () => post(`/api/alertas/${a.id}/encerrar`, { operador: "Operador" });
    }
    d.appendChild(btn);
    d.querySelector(".txt").onclick = () => { selecionar(a.bracadeira_id); };
    box.appendChild(d);
  });
}

/* ------------------------------------------------------------------ lateral */
function desenharLateral() {
  const k = estado.kpis;
  $("k-sub").textContent = k.no_subsolo;
  $("k-crit").textContent = k.alertas_criticos;
  $("k-al").textContent = k.alertas;
  $("k-ss").textContent = k.sem_sinal;
  document.querySelector(".kpi.crit").classList.toggle("ativo", k.alertas_criticos > 0);

  const ordem = { critico: 0, alto: 1, aviso: 2, normal: 3 };
  const lista = [...estado.trabalhadores].sort((a, b) => ordem[a.status] - ordem[b.status] || a.nome.localeCompare(b.nome));
  $("tabela").innerHTML = lista.map((t) => {
    const cls = t.sem_sinal ? "semsinal" : t.status;
    return `<tr data-id="${t.id}" class="${t.id === selecionado ? "sel " : ""}${t.status === "critico" ? "critico" : ""}">
      <td class="nome"><i class="pt ${cls}"></i>${esc(t.nome)}</td>
      <td>${esc(t.zona)}</td>
      <td class="${t.bpm > 150 || (t.bpm && t.bpm < 40) ? "ruim" : ""}">${t.bpm ?? "—"}</td>
      <td class="${t.spo2 && t.spo2 < 90 ? "ruim" : t.spo2 && t.spo2 < 94 ? "atencao" : ""}">${t.spo2 ? t.spo2 + "%" : "—"}</td>
      <td class="${t.bateria < 15 ? "atencao" : ""}">${t.bateria}%</td></tr>`;
  }).join("");
  document.querySelectorAll("#tabela tr").forEach((tr) => (tr.onclick = () => selecionar(+tr.dataset.id)));

  const ev = $("eventos");
  ev.innerHTML = estado.eventos.map((e) => `<li class="${e.nivel}"><time>${hora(e.horario)}</time><span>${esc(e.texto)}</span></li>`).join("");
  const r = estado.rede;
  $("rede").textContent = `${r.processados} pacotes processados · ${r.duplicados} duplicados (vários gateways) · ${r.corrompidos} corrompidos`;
  $("relogio").textContent = hora(estado.horario);
  atualizarDetalhe();
}

/* ------------------------------------------------------------------ detalhe */
function selecionar(id) {
  selecionado = id;
  const t = estado && estado.trabalhadores.find((x) => x.id === id);
  if (t && t.nivel !== nivelAtivo) { nivelAtivo = t.nivel; desenharAbas(); desenharMapa(); }
  desenharTrabalhadores();
  desenharLateral();
  carregarHistorico();
}

function atualizarDetalhe() {
  const t = estado.trabalhadores.find((x) => x.id === selecionado);
  document.querySelectorAll(".botoes button").forEach((b) => (b.disabled = !t));
  if (!t) return;
  $("d-nome").textContent = t.nome;
  $("d-func").textContent = `${t.funcao} · braçadeira #${String(t.id).padStart(4, "0")} · ${t.zona}`;
  const st = $("d-status");
  st.className = "chip " + (t.status !== "normal" ? t.status : "");
  st.textContent = t.sem_sinal ? "sem sinal" : { normal: "normal", aviso: "aviso", alto: "atenção", critico: "emergência" }[t.status];
  $("d-bpm").textContent = t.bpm ? `${t.bpm} BPM` : "—";
  $("d-spo2").textContent = t.spo2 ? `${t.spo2} %` : "—";
}

function linha(svg, pts, min, max, cor, limite) {
  svg.innerHTML = "";
  if (limite !== undefined) {
    const y = 70 - ((limite - min) / (max - min)) * 70;
    el("line", { x1: 0, x2: 300, y1: y, y2: y, stroke: "#E7B3AE", "stroke-dasharray": "4 3", "stroke-width": 1 }, svg);
  }
  if (pts.length < 2) return;
  const t0 = pts[0][0], t1 = pts[pts.length - 1][0] || t0 + 1;
  const d = pts.map(([t, v], i) => `${i ? "L" : "M"}${((t - t0) / (t1 - t0 || 1)) * 300} ${70 - ((Math.min(Math.max(v, min), max) - min) / (max - min)) * 70}`).join(" ");
  el("path", { d, fill: "none", stroke: cor, "stroke-width": 2, "vector-effect": "non-scaling-stroke", "stroke-linejoin": "round" }, svg);
}

async function carregarHistorico() {
  if (!selecionado) return;
  const h = await (await fetch(`/api/historico?dispositivo=${selecionado}&minutos=5`)).json();
  linha($("g-bpm"), h.filter((r) => r.bpm).map((r) => [r.horario, r.bpm]), 40, 180, "#B83227", 150);
  linha($("g-spo2"), h.filter((r) => r.spo2).map((r) => [r.horario, r.spo2]), 80, 100, "#1F6FB2", 90);
}

document.querySelectorAll(".botoes button").forEach((b) =>
  (b.onclick = () => selecionado && post(`/api/sim/${b.dataset.acao}/${selecionado}`)));

/* ------------------------------------------------------------------ início */
async function iniciar() {
  mapa = await (await fetch("/api/mapa")).json();
  $("mina").textContent = mapa.nome;
  nivelAtivo = mapa.niveis[mapa.niveis.length - 1].id;
  estado = await (await fetch("/api/estado")).json();
  desenharAbas(); desenharMapa(); desenharTrabalhadores(); desenharAlertas(); desenharLateral();

  const fonte = new EventSource("/api/stream");
  fonte.onopen = () => $("conexao").classList.add("on");
  fonte.onerror = () => $("conexao").classList.remove("on");
  let tick = 0;
  fonte.onmessage = (m) => {
    const antes = estado.alertas.filter((a) => a.nivel === "critico").length;
    estado = JSON.parse(m.data);
    desenharAbas(); desenharTrabalhadores(); desenharAlertas(); desenharLateral();
    const depois = estado.alertas.filter((a) => a.nivel === "critico" && a.status === "aberto").length;
    if (depois > antes) bip();
    if (++tick % 5 === 0) carregarHistorico();
  };
}

function bip() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    [0, 0.25, 0.5].forEach((t) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.value = 880; g.gain.value = 0.08;
      o.connect(g).connect(ctx.destination);
      o.start(ctx.currentTime + t); o.stop(ctx.currentTime + t + 0.15);
    });
  } catch (e) { /* navegador sem áudio */ }
}

iniciar();
