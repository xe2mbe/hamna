/* HAMNA Web — interfaz */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const REC = { ninguna: "Una sola vez", diaria: "Todos los días", semanal: "Cada semana", "lun-vie": "Lunes a viernes" };
const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];

const S = { tab: "prog", eventos: [], tipos: [], secciones: [], prog: [], evSel: null,
  status: null, cfg: null, info: null, setSec: "nodo" };
try { S.setSec = new URLSearchParams(location.search).get("set") || localStorage.getItem("hamna.set") || "nodo"; } catch {}

/* ── API ─────────────────────────────────────────────────────────────────── */
async function api(path, { method = "GET", json, form } = {}) {
  const opt = { method, headers: { "X-HAMNA": "1" }, credentials: "same-origin" };
  if (json !== undefined) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(json); }
  if (form) opt.body = form;
  const r = await fetch(path, opt);
  if (r.status === 401 && path !== "api/login") { showLogin(); throw new Error("Inicia sesión"); }
  let data = null;
  try { data = await r.json(); } catch { data = null; }
  if (!r.ok || (data && data.ok === false)) throw new Error((data && data.error) || `Error ${r.status}`);
  return data;
}

function toast(msg, isErr = false) {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast" + (isErr ? " error" : "");
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.add("hidden"), isErr ? 6000 : 2800);
}
async function run(fn, okMsg) {
  try { const r = await fn(); if (okMsg) toast(okMsg); return r; }
  catch (e) { toast(e.message, true); throw e; }
}
function busy(btn, on, label) {
  if (!btn) return;
  if (on) { btn.dataset.label = btn.innerHTML; btn.disabled = true; btn.innerHTML = label || "Procesando…"; }
  else { btn.disabled = false; if (btn.dataset.label) btn.innerHTML = btn.dataset.label; }
}

const fmt = (s) => {
  s = Math.max(0, Math.round(+s || 0));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
  return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(x).padStart(2, "0");
};
const fmtLeft = (s) => {
  if (s == null) return "";
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (d) return `${d} d ${h} h`;
  if (h) return `${h} h ${m} min`;
  if (m) return `${m} min`;
  return `${s} s`;
};

/* ── Modal ───────────────────────────────────────────────────────────────── */
function openModal(title, html) {
  $("#modalTitle").textContent = title;
  $("#modalBody").innerHTML = html;
  $("#modal").classList.remove("hidden");
  const f = $("#modalBody input:not([type=hidden]):not([type=checkbox]), #modalBody textarea");
  if (f) setTimeout(() => f.focus(), 30);
}
function closeModal() {
  $$("#modalBody audio").forEach((a) => a.pause());
  $("#modal").classList.add("hidden");
  $("#modalBody").innerHTML = "";
}
$("#modalClose").onclick = closeModal;
$("#modal").addEventListener("mousedown", (e) => { if (e.target.id === "modal") closeModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
function confirmBox(msg, okLabel = "Sí, continuar", danger = true) {
  return new Promise((res) => {
    openModal("Confirmar", `<p>${esc(msg)}</p><div class="modal-actions">
      <button class="btn" id="cNo">Cancelar</button>
      <button class="btn ${danger ? "danger" : "primary"}" id="cYes">${esc(okLabel)}</button></div>`);
    $("#cNo").onclick = () => { closeModal(); res(false); };
    $("#cYes").onclick = () => { closeModal(); res(true); };
  });
}

/* ── Sesión ──────────────────────────────────────────────────────────────── */
function showLogin() {
  $("#app").classList.add("hidden"); $("#login").classList.remove("hidden");
  S.polling = false; clearTimeout(S.pollTimer);
  clearInterval(S.clockTimer); S.clockTimer = null;
  let last = ""; try { last = localStorage.getItem("hamna.user") || ""; } catch {}
  if (last && !$("#loginUser").value) $("#loginUser").value = last;
  setTimeout(() => ($("#loginUser").value ? $("#loginPw") : $("#loginUser")).focus(), 50);
}
$$(".lang-pick button").forEach((b) => {
  b.classList.toggle("on", b.dataset.lang === window.HAMNA_LANG);
  b.onclick = () => window.hamnaSetLang(b.dataset.lang);
});
$("#loginForm").onsubmit = async (e) => {
  e.preventDefault();
  $("#loginErr").textContent = "";
  const b = $("#loginForm button"); busy(b, true, "Entrando…");
  const usuario = $("#loginUser").value.trim();
  try {
    const r = await api("api/login", { method: "POST", json: { usuario, password: $("#loginPw").value } });
    $("#loginPw").value = ""; S.me = r.usuario;
    try { localStorage.setItem("hamna.user", usuario); } catch {}
    start();
  }
  catch (err) { $("#loginErr").textContent = err.message; }
  finally { busy(b, false); }
};

async function start() {
  $("#login").classList.add("hidden"); $("#app").classList.remove("hidden");
  try { S.cfg = await api("api/ajustes"); } catch { return; }
  try { S.me = (await api("api/me")).usuario; } catch {}
  if (S.me) {
    if (S.me.idioma && S.me.idioma !== window.HAMNA_LANG) { window.hamnaSetLang(S.me.idioma); return; }
    if (!S.me.idioma) api("api/mi-idioma", { method: "PUT", json: { idioma: window.HAMNA_LANG } }).catch(() => {});
  }
  applyRole();
  updateNodeLabel();
  if (isAdmin()) api("api/actualizaciones").then(markUpdate).catch(() => {});
  S.polling = true;
  await poll();
  if (!S.clockTimer) S.clockTimer = setInterval(tickClock, 1000);
  const q = new URLSearchParams(location.search).get("tab");
  let saved = ""; try { saved = localStorage.getItem("hamna.tab") || ""; } catch {}
  const pedida = location.hash.slice(1) || q || saved || "prog";
  showTab(pedida === "sesiones" ? "conexiones" : pedida);   // nombre anterior
}

/* ── Monitor del equipo ──────────────────────────────────────────────────────
   Los datos vienen en /api/status (sin consultas extra). */
const fmtB = (b) => b == null ? "—" : b >= 1e9 ? (b / 1e9).toFixed(1) + " GB" : b >= 1e6 ? Math.round(b / 1e6) + " MB" : Math.round(b / 1e3) + " kB";
const fmtRate = (b) => b == null ? "—" : b >= 125000 ? (b * 8 / 1e6).toFixed(1) + " Mb/s" : Math.round(b * 8 / 1e3) + " kb/s";
function setBar(id, pct) {
  const el = $(id); if (!el) return;
  el.style.width = (pct == null ? 0 : Math.min(100, pct)) + "%";
  el.className = pct >= 90 ? "bad" : pct >= 75 ? "warn" : "";
}
function renderSys(d, ver) {
  if (ver && $("#appVer").textContent !== "v" + ver) $("#appVer").textContent = "v" + ver;
  if (!d) { $("#sideMon").classList.add("hidden"); return; }
  $("#sideMon").classList.remove("hidden");
  const L = (es, en) => (window.HAMNA_LANG === "es" ? es : en);
  $$("#sideMon [data-l]").forEach((el) => {
    const k = el.dataset.l, en = { "Equipo": "System", "Disco": "Disk", "Temp.": "Temp.", "Carga": "Load" }[k];
    el.textContent = window.HAMNA_LANG === "es" ? k : (en || k);
  });
  setBar("#mbCpu", d.cpu); $("#mvCpu").textContent = d.cpu == null ? "—" : Math.round(d.cpu) + " %";
  const mp = d.mem && d.mem.total ? (d.mem.usada / d.mem.total) * 100 : null;
  setBar("#mbMem", mp); $("#mvMem").textContent = d.mem ? `${fmtB(d.mem.usada)} / ${fmtB(d.mem.total)}` : "—";
  const dp = d.disco && d.disco.total ? (d.disco.usada / d.disco.total) * 100 : null;
  setBar("#mbDisk", dp); $("#mvDisk").textContent = d.disco ? `${fmtB(d.disco.usada)} / ${fmtB(d.disco.total)}` : "—";
  $("#tmCpu").textContent = d.cpu == null ? "—" : Math.round(d.cpu) + " %";
  $("#tmCpu").className = d.cpu >= 90 ? "bad" : d.cpu >= 75 ? "warn" : "";
  $("#tmTemp").textContent = d.temp == null ? "—" : Math.round(d.temp) + " °C";
  $("#tmTemp").className = d.temp >= 80 ? "bad" : d.temp >= 70 ? "warn" : "";
  $(".tm-temp").classList.toggle("hidden", d.temp == null);
  const t = $("#mvTemp");
  t.textContent = d.temp == null ? "—" : d.temp.toFixed(1) + " °C";
  t.className = d.temp >= 80 ? "bad" : d.temp >= 70 ? "warn" : "";
  const ld = $("#mvLoad");
  ld.textContent = d.carga == null ? "—" : d.carga.toFixed(2);
  ld.className = d.carga >= d.nucleos ? "bad" : d.carga >= d.nucleos * 0.75 ? "warn" : "";
  $("#mvRx").textContent = fmtRate(d.rx_bps); $("#mvTx").textContent = fmtRate(d.tx_bps);
  if (d.encendido_s != null) {
    const s = d.encendido_s, dd = Math.floor(s / 86400), hh = Math.floor((s % 86400) / 3600), mm = Math.floor((s % 3600) / 60);
    $("#monUp").textContent = L("encendido ", "up ") + (dd ? `${dd} d ${hh} h` : hh ? `${hh} h ${mm} min` : `${mm} min`);
  }
  $("#sideMon").title = L("Datos del equipo del nodo · se actualizan con el estado", "Node system data · updated with the status");
}

/* ── Logo ────────────────────────────────────────────────────────────────── */
const DEFAULT_ICON = $("#favicon").href;
function applyLogo(url) {
  S.logo = url || "";
  for (const id of ["#brandLogo", "#loginLogo", "#topLogo"]) {
    const img = $(id);
    if (url) { if (img.getAttribute("src") !== url) img.src = url; img.classList.remove("hidden"); }
    else { img.removeAttribute("src"); img.classList.add("hidden"); }
  }
  $("#favicon").href = url || DEFAULT_ICON;
  const pv = $("#logoPreview");
  if (pv) pv.innerHTML = url ? `<img src="${esc(url)}" alt="Logo">` : '<span class="muted">Sin logo</span>';
  const del = $("#btnLogoDel");
  if (del) del.classList.toggle("hidden", !url);
}
/* Reduce la imagen en el navegador (máx. 400 px) para que el nodo no procese nada */
function shrinkImage(file, max = 400) {
  return new Promise((res, rej) => {
    if (file.type === "image/gif") return res(file);           // conservar animación
    const img = new Image(), url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      const k = Math.min(1, max / Math.max(img.width, img.height));
      if (k === 1 && file.size < 300 * 1024) return res(file);
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      // WEBP conserva la transparencia; si el navegador no lo sabe hacer, devuelve PNG
      c.toBlob((b) => b ? res(b) : rej(new Error("No pude leer la imagen")), "image/webp", 0.9);
    };
    img.onerror = () => { URL.revokeObjectURL(url); rej(new Error("No pude leer la imagen")); };
    img.src = url;
  });
}
$("#logoFile").onchange = async (e) => {
  const file = e.target.files[0]; e.target.value = "";
  if (!file) return;
  try {
    const blob = await shrinkImage(file);
    const ext = { "image/webp": ".webp", "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif" }[blob.type] || ".png";
    const fd = new FormData(); fd.append("archivo", blob, "logo" + ext);
    const r = await upload("api/ajustes/logo", fd);
    applyLogo(r.logo); toast("Logo guardado");
  } catch (err) { toast(err.message, true); }
};
$("#btnLogoDel").onclick = async () => {
  if (!(await confirmBox("¿Quitar el logo?", "Quitar"))) return;
  const r = await run(() => api("api/ajustes/logo", { method: "DELETE" }), "Logo quitado");
  applyLogo(r.logo);
};

/* ── Pestañas ────────────────────────────────────────────────────────────── */
$$("#tabs button").forEach((b) => (b.onclick = () => { showTab(b.dataset.tab); closeDrawer(); }));

/* ── Menú de hamburguesa ──────────────────────────────────────────────────────
   Computadora: la barra lateral se esconde y se recuerda. Celular: cajón. */
const isMobile = () => matchMedia("(max-width: 960px)").matches;
function syncMenuBtn() {
  const open = isMobile() ? document.body.classList.contains("nav-open") : !document.body.classList.contains("nav-collapsed");
  $("#btnMenu").setAttribute("aria-expanded", String(open));
}
function closeDrawer() { document.body.classList.remove("nav-open"); syncMenuBtn(); }
$("#btnMenu").onclick = () => {
  if (isMobile()) document.body.classList.toggle("nav-open");
  else {
    document.body.classList.remove("nav-collapsed");
    try { localStorage.setItem("hamna.nav", "open"); } catch {}
  }
  syncMenuBtn();
};
$("#btnHideMenu").onclick = () => {
  if (isMobile()) return closeDrawer();
  document.body.classList.add("nav-collapsed");
  try { localStorage.setItem("hamna.nav", "collapsed"); } catch {}
  syncMenuBtn();
};
$("#scrim").onclick = closeDrawer;
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });
try { if (localStorage.getItem("hamna.nav") === "collapsed") document.body.classList.add("nav-collapsed"); } catch {}
const TABS = ["prog", "eventos", "secciones", "conexiones", "cron", "ajustes"];
window.addEventListener("hashchange", () => { const t = location.hash.slice(1); if (TABS.includes(t) && t !== S.tab) showTab(t); });
function showTab(t) {
  if (!TABS.includes(t)) t = "prog";
  if (t === "cron" && S.me && S.me.rol === "lectura") t = "prog";
  if (S.tab === "conexiones" && t !== "conexiones") stopSesiones();
  S.tab = t;
  try { localStorage.setItem("hamna.tab", t); } catch {}
  if (location.hash.slice(1) !== t) history.replaceState(null, "", "#" + t);
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === t));
  $$(".view").forEach((v) => v.classList.toggle("hidden", v.id !== "view-" + t));
  ({ prog: loadProg, eventos: loadEventos, secciones: loadSecciones, conexiones: loadSesiones, cron: loadCron, ajustes: loadAjustes })[t]();
  window.scrollTo(0, 0);
}

function updateNodeLabel() {
  const c = S.cfg || {};
  $("#topStation").textContent = c.station_name || (c.node ? "Nodo " + c.node : "HAMNA Web");
  const be = c.backend === "auto" ? "" : (c.backend || "").toUpperCase();
  $("#nodeLabel").innerHTML = (c.station_name ? `<b>${esc(c.station_name)}</b>` : "") +
    esc([c.node ? `Nodo ${c.node}` : "", be].filter(Boolean).join(" · "));
}

/* ── Estado al aire ──────────────────────────────────────────────────────────
   Para no cargar la Raspberry: cada segundo solo mientras hay algo al aire,
   cada 5 s el resto del tiempo y nada con la pestaña oculta. El reloj avanza
   solo en el navegador con la hora que mandó el nodo. */
const POLL_LIVE = 1000, POLL_IDLE = 5000;
function schedulePoll() {
  clearTimeout(S.pollTimer);
  if (!S.polling || document.hidden) return;
  S.pollTimer = setTimeout(poll, S.status && S.status.on_air ? POLL_LIVE : POLL_IDLE);
}
document.addEventListener("visibilitychange", () => {
  if (!S.polling) return;
  if (document.hidden) { clearTimeout(S.pollTimer); stopSesiones(); }
  else { poll(); if (S.tab === "conexiones") loadSesiones(); }
});
const pad2 = (n) => String(n).padStart(2, "0");
function tickClock() {
  if (S.tzOff == null || document.hidden) return;
  const now = Date.now() + S.skew;
  const loc = new Date(now + S.tzOff), utc = new Date(now);
  $("#clockLocal").textContent = `${pad2(loc.getUTCHours())}:${pad2(loc.getUTCMinutes())}:${pad2(loc.getUTCSeconds())}`;
  $("#clockUtc").textContent = `UTC ${pad2(utc.getUTCHours())}:${pad2(utc.getUTCMinutes())}`;
  $("#clockTop").textContent = $("#clockLocal").textContent;
  if (!(S.status && S.status.on_air)) tickProg();
}
async function poll() {
  clearTimeout(S.pollTimer);
  let s;
  try { s = await api("api/status"); } catch { schedulePoll(); return; }
  S.status = s;
  renderSys(s.sys, s.version);
  if (s.ts) {
    // Hora del nodo: s.now (hora local) y s.ts (época UTC) → desfase y zona horaria
    const [d, t] = s.now.split(" "), [Y, M, D] = d.split("-").map(Number), [h, m, x] = t.split(":").map(Number);
    S.skew = s.ts * 1000 - Date.now();
    S.tzOff = Math.round((Date.UTC(Y, M - 1, D, h, m, x) - s.ts * 1000) / 60000) * 60000;
    tickClock();
  } else {
    $("#clockLocal").textContent = s.now.slice(11);
    $("#clockUtc").textContent = "UTC " + s.utc;
  }
  schedulePoll();
  const live = s.on_air;
  $("#onair").classList.toggle("live", live && s.state === "tx");
  $("#brandDot").classList.toggle("live", live && s.state === "tx");
  $("#topDot").classList.toggle("live", live && s.state === "tx");
  const pill = $("#airPill");
  const map = { tx: ["AL AIRE", "tx"], gap: ["INTERVALO", "wait"], paused: ["PAUSA", "wait"],
    manual_pause: ["EN PAUSA", "wait"], preparing: ["PREPARANDO", "prep"], idle: ["FUERA DEL AIRE", ""] };
  const [txt, cls] = map[live ? s.state : "idle"] || map.idle;
  pill.textContent = txt; pill.className = "pill " + cls;
  $("#airCountdown").textContent = s.countdown != null && s.state !== "manual_pause" ? s.countdown + " s" : "";
  const sec = s.secciones[s.cur_sec];
  $("#airEvento").textContent = live ? s.evento : (s.error ? "Error: " + s.error : "—");
  $("#airSeccion").textContent = live && sec ? `Sección ${s.cur_sec + 1}/${s.secciones.length} · ${sec.nombre}` : "";
  const sp = sec && sec.duracion ? (s.sec_pos / sec.duracion) * 100 : 0;
  $("#barSec").style.width = (live ? Math.min(100, sp) : 0) + "%";
  $("#barTotal").style.width = (live && s.total ? Math.min(100, (s.elapsed / s.total) * 100) : 0) + "%";
  // Tiempo restante / duración (sección y evento completo)
  const left = (a, b) => fmt(Math.max(0, (b || 0) - (a || 0)));
  $("#airSecTime").textContent = live && sec ? `Sección: faltan ${left(s.sec_pos, sec.duracion)} / ${fmt(sec.duracion)}` : "";
  $("#airTotalTime").textContent = live ? `Evento: faltan ${left(s.elapsed, s.total)} / ${fmt(s.total)}` : "";
  $("#ctlPause").classList.toggle("hidden", s.state === "manual_pause");
  $("#ctlResume").classList.toggle("hidden", s.state !== "manual_pause");
  $("#ctlPause").disabled = !(live && s.state === "tx");
  $("#ctlSkip").disabled = !(live && (s.state === "paused" || s.state === "gap"));
  $("#ctlNext").disabled = !live || s.origen === "prueba";
  $("#ctlStop").disabled = !live;
  const logKey = s.log.length ? s.log.length + s.log[s.log.length - 1].t + s.log[s.log.length - 1].msg : "";
  if (logKey !== S.logKey) {   // reconstruir la bitácora solo si cambió
    S.logKey = logKey;
    $("#airLog").innerHTML = s.log.map((l) => `<div class="${l.level}">${esc(l.t)}  ${esc(l.msg)}</div>`).join("");
  }
  // Resaltar la sección al aire en el detalle del evento
  $$("#eventoDetail .sec-row").forEach((r) =>
    r.classList.toggle("on", live && s.evento_id === S.evSel && +r.dataset.idx === s.cur_sec));
  if (S.wasLive !== live) { S.wasLive = live; if (S.tab === "prog") loadProg(); }
  tickProg();
}
const txCmd = (c) => run(() => api("api/tx/" + c, { method: "POST" })).then(() => setTimeout(poll, 300), () => {});
$("#ctlPause").onclick = () => txCmd("pause");
$("#ctlResume").onclick = () => txCmd("resume");
$("#ctlSkip").onclick = () => txCmd("skip_pause");
$("#ctlNext").onclick = () => txCmd("next");
$("#ctlStop").onclick = async () => { if (await confirmBox("¿Detener la transmisión?", "Detener")) txCmd("stop"); };
$("#ctlLog").onclick = () => $("#airLog").classList.toggle("hidden");

async function txStart(eid, nombre) {
  const s = S.status;
  const msg = s && s.on_air ? `Hay una transmisión al aire («${s.evento}»). Se detendrá para iniciar «${nombre}». ¿Continuar?`
    : `¿Transmitir «${nombre}» ahora?`;
  if (!(await confirmBox(msg, "📡 Transmitir"))) return;
  await run(() => api("api/tx/start", { method: "POST", json: { evento_id: eid } }), "Iniciando transmisión");
  setTimeout(poll, 300);
}

/* ── Programación ────────────────────────────────────────────────────────── */
async function loadProg() {
  const [prog, ev] = await Promise.all([api("api/programacion"), api("api/eventos")]);
  S.prog = prog; S.eventos = ev.eventos; S.tipos = ev.tipos;
  S.progLoaded = Date.now();
  renderProg();
  loadCronEntries().then((ch) => { if (ch && S.tab === "prog") renderProg(); });
}
function recText(p) {
  if (p.recurrencia === "semanal") return "Cada " + DIAS[new Date(p.fecha + "T12:00").getDay()];
  if (p.recurrencia === "ninguna") return "Una vez · " + p.fecha;
  return REC[p.recurrencia] || p.recurrencia;
}
function renderProg() {
  const live = S.status && S.status.on_air ? S.status.evento_id : null;
  const today = (S.status ? S.status.now : "").slice(0, 10);
  const el = $("#progList");
  if (!S.prog.length) {
    el.innerHTML = `<p class="empty">No hay nada programado.<br>Crea primero un evento con sus secciones y luego prográmalo aquí.</p>`;
    $("#nextCard").classList.add("hidden");
    return;
  }
  // Primero lo que está al aire; luego por la próxima hora (lo que sigue arriba);
  // al final lo desactivado o sin fechas.
  const rank = (p) => (live && p.evento_id === live ? -1 : p.activo && p.faltan_s != null ? p.faltan_s : Infinity);
  S.prog = S.prog.slice().sort((a, b) => rank(a) - rank(b));
  // La franja del próximo evento va pegada encima de su tarjeta
  const nxt = S.prog.find((p) => p.activo && p.faltan_s != null && p.evento_id !== live);
  el.innerHTML = S.prog.map((p) => {
    const isToday = p.proxima && p.proxima.startsWith(today);
    const strip = p === nxt ? `<div class="next-strip"><div><span class="lbl">Próximo evento</span>
        <small>${esc(p.proxima)}</small></div><div class="cd" id="nextLeft" data-left="${p.faltan_s}"></div></div>` : "";
    return `<div class="prog-slot ${p === nxt ? "is-next" : ""}">${strip}<div class="card ${!p.activo ? "off" : ""} ${live === p.evento_id ? "live" : isToday ? "today" : ""}">
      <div class="row" style="justify-content:space-between"><span class="when">${esc(p.hora)}${p.zona ? `<small class="zone">${esc(zoneShort(p))}</small>` : ""}</span>
        ${live === p.evento_id ? '<span class="chip live">AL AIRE</span>' : isToday ? '<span class="chip ok">HOY</span>' : ""}</div>
      <h3>${esc(p.evento_nombre)}</h3>
      <div class="meta">${esc(recText(p))}${p.evento_tipo ? " · " + esc(p.evento_tipo) : ""}</div>
      ${p.zona ? `<div class="meta here">Aquí (hora del nodo): <b>${esc(p.hora_local)}</b></div>` : ""}
      ${p.cambio ? `<div class="meta tz-warn">⚠ Desde el ${esc(p.cambio.fecha)} será a las ${esc(p.cambio.hora_local)} aquí (cambio de horario)</div>` : ""}
      <div class="meta" data-left="${p.faltan_s ?? ""}">${p.activo ? (p.proxima ? "Próxima: " + esc(p.proxima) + " · en <b class='left'>" + fmtLeft(p.faltan_s) + "</b>" : "Sin próximas fechas") : "Desactivada"}</div>
      ${progTimeline(p)}
      <div class="actions">
        <button class="btn sm primary" data-act="tx" data-id="${p.evento_id}" data-n="${esc(p.evento_nombre)}">📡 Transmitir ahora</button>
        <button class="btn sm" data-act="edit" data-id="${p.id}">Editar</button>
        <button class="btn sm" data-act="toggle" data-id="${p.id}">${p.activo ? "Desactivar" : "Activar"}</button>
        <button class="btn sm ghost" data-act="del" data-id="${p.id}">Borrar</button>
      </div></div></div>`;
  }).join("");
  $("#nextCard").classList.add("hidden");
  tickProg();
}
function tickProg() {
  if (S.tab !== "prog" || !S.progLoaded) return;
  const passed = Math.floor((Date.now() - S.progLoaded) / 1000);
  const nl = $("#nextLeft");
  if (nl) {
    const left = +nl.dataset.left - passed;
    if (left < -5) { S.progLoaded = 0; loadProg(); return; }
    nl.textContent = left > 86400 ? fmtLeft(left) : fmt(Math.max(0, left));
  }
  $$("#progList [data-left]").forEach((m) => {
    const b = $(".left", m);
    if (b && m.dataset.left !== "") b.textContent = fmtLeft(Math.max(0, +m.dataset.left - passed));
  });
}
$("#progList").onclick = async (e) => {
  const b = e.target.closest("button[data-act]"); if (!b) return;
  const id = +b.dataset.id, p = S.prog.find((x) => x.id === id);
  if (b.dataset.act === "tx") return txStart(id, b.dataset.n);
  if (b.dataset.act === "edit") return progForm(p);
  if (b.dataset.act === "toggle") {
    await run(() => api("api/programacion/" + id, { method: "PUT", json: { ...p, activo: !p.activo } }));
    return loadProg();
  }
  if (b.dataset.act === "del" && (await confirmBox(`¿Borrar la programación de «${p.evento_nombre}» a las ${p.hora}?`, "Borrar"))) {
    await run(() => api("api/programacion/" + id, { method: "DELETE" }), "Borrada"); loadProg();
  }
};
$("#btnNewProg").onclick = async () => {
  if (!S.eventos.length) await loadProg();
  if (!S.eventos.length) return toast("Primero crea un evento en la pestaña Eventos", true);
  progForm(null);
};
/* "2026-11-08", "20:00", "America/Chicago" → "02:00" (hora UTC); +1/-1 si cambia de día */
function zonedToUtc(fecha, hora, zone) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(fecha || ""), h = /^(\d{2}):(\d{2})/.exec(hora || "");
  if (!m || !h) return "";
  const guess = Date.UTC(+m[1], +m[2] - 1, +m[3], +h[1], +h[2]);
  let utc = guess;
  try {
    if (zone) {
      const fmt = new Intl.DateTimeFormat("en-US", { timeZone: zone, hourCycle: "h23",
        year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
      const off = (t) => {   // minutos que la zona va adelantada a UTC en el instante t
        const p = Object.fromEntries(fmt.formatToParts(new Date(t)).map((x) => [x.type, x.value]));
        return (Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute) - t) / 60000;
      };
      utc = guess - off(guess) * 60000;
      utc = guess - off(utc) * 60000;         // segunda vuelta por si cruza el cambio de horario
    }
  } catch { return ""; }
  const d = new Date(utc), dd = Math.round((Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) -
    Date.UTC(+m[1], +m[2] - 1, +m[3])) / 86400000);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}` +
    (dd ? (window.HAMNA_LANG === "es" ? (dd > 0 ? " del día siguiente" : " del día anterior")
      : (dd > 0 ? " next day" : " previous day")) : "");
}
/* Diferencia con UTC de una zona: "(UTC−6)" o "(UTC−6, verano UTC−5)" */
function utcOffsetMin(zone, t) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: zone, hourCycle: "h23",
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
    .formatToParts(new Date(t)).map((x) => [x.type, x.value]));
  return Math.round((Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute) - Math.floor(t / 60000) * 60000) / 60000);
}
function fmtOff(min) {
  const s = min < 0 ? "−" : "+", a = Math.abs(min);
  return "UTC" + (a ? s + Math.floor(a / 60) + (a % 60 ? ":" + String(a % 60).padStart(2, "0") : "") : "");
}
function utcLabel(zone) {
  if (!zone) return "";
  try {
    const y = new Date().getUTCFullYear();
    const a = utcOffsetMin(zone, Date.UTC(y, 0, 15, 12)), b = utcOffsetMin(zone, Date.UTC(y, 6, 15, 12));
    if (a === b) return `(${fmtOff(a)})`;
    const std = Math.min(a, b), dst = Math.max(a, b);
    return `(${fmtOff(std)}, ${window.HAMNA_LANG === "es" ? "verano" : "summer"} ${fmtOff(dst)})`;
  } catch { return ""; }
}
function zoneShort(p) {
  const n = p.zona_nombre || p.zona;
  return n.split(" · ")[0].split(" (")[0];
}
async function progForm(p) {
  const today = (S.status ? S.status.now : new Date().toISOString()).slice(0, 10);
  p = p || { evento_id: S.evSel || S.eventos[0].id, fecha: today, hora: "20:00", recurrencia: "semanal", activo: 1, zona: "" };
  if (!S.zonas) { try { S.zonas = await api("api/zonas"); } catch { S.zonas = { nodo: "", zonas: [] }; } }
  const zs = S.zonas.zonas.slice();
  if (p.zona && !zs.some((z) => z.id === p.zona)) zs.push({ id: p.zona, nombre: p.zona });
  openModal(p.id ? "Editar programación" : "Programar evento", `
    <form id="pf">
      <label>Evento<select name="evento_id">${S.eventos.map((e) =>
        `<option value="${e.id}" ${e.id === p.evento_id ? "selected" : ""}>${esc(e.nombre)}</option>`).join("")}</select></label>
      <div class="grid2">
        <label>Fecha (o primera fecha)<input type="date" name="fecha" value="${esc(p.fecha)}" required></label>
        <label>Hora <span class="utc-hint" id="utcHint" translate="no"></span><input type="time" name="hora" value="${esc(p.hora)}" required></label>
      </div>
      <label>Zona horaria del programa<select name="zona">${zs.map((z) =>
        `<option value="${esc(z.id)}" ${z.id === (p.zona || "") ? "selected" : ""}>${esc(z.nombre)} ${esc(utcLabel(z.id || S.zonas.nodo))}</option>`).join("")}</select>
        <small>La hora y el día se toman en esa zona y HAMNA los convierte a la hora del nodo para cada fecha: si esa zona cambia de horario, el evento se recorre solo. Zona del nodo: ${esc(S.zonas.nodo || "—")}.</small></label>
      <label>Se repite<select name="recurrencia">${Object.entries(REC).map(([k, v]) =>
        `<option value="${k}" ${k === p.recurrencia ? "selected" : ""}>${v}</option>`).join("")}</select>
        <small id="recHint"></small></label>
      <label class="check"><input type="checkbox" name="activo" ${p.activo ? "checked" : ""}> Activa</label>
      <div class="modal-actions"><button type="button" class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn primary">Guardar</button></div>
    </form>`);
  const f = $("#pf");
  const hint = () => { const d = new Date(f.fecha.value + "T12:00");
    $("#recHint").textContent = f.recurrencia.value === "semanal" && !isNaN(d) ? "Cada " + DIAS[d.getDay()] + " a las " + f.hora.value : ""; };
  // Hora en UTC entre paréntesis (respeta el horario de verano de esa fecha y zona)
  const utc = () => {
    const z = f.zona.value || S.zonas.nodo || "", u = zonedToUtc(f.fecha.value, f.hora.value, z);
    $("#utcHint").textContent = u ? "(" + u.replace(/^(\d\d:\d\d)/, "$1 UTC") + ")" : "";
  };
  f.oninput = () => { hint(); utc(); }; f.onchange = utc; hint(); utc();
  f.onsubmit = async (e) => {
    e.preventDefault();
    const data = { evento_id: +f.evento_id.value, fecha: f.fecha.value, hora: f.hora.value,
      recurrencia: f.recurrencia.value, activo: f.activo.checked, zona: f.zona.value };
    await run(() => api("api/programacion" + (p.id ? "/" + p.id : ""), { method: p.id ? "PUT" : "POST", json: data }), "Guardado");
    closeModal(); loadProg();
  };
}

/* ── Eventos ─────────────────────────────────────────────────────────────── */
async function loadEventos() {
  const ev = await api("api/eventos");
  S.eventos = ev.eventos; S.tipos = ev.tipos;
  const el = $("#eventosList");
  el.innerHTML = S.eventos.length ? S.eventos.map((e) => `
    <button class="list-item ${e.id === S.evSel ? "active" : ""}" data-id="${e.id}">
      <b>${esc(e.nombre)}</b>${e.numero ? ` <span class="chip">#${e.numero}</span>` : ""}
      <small>${evSummary(e)}</small>
    </button>`).join("") : `<p class="empty">Aún no hay eventos.</p>`;
  if (S.evSel && S.eventos.some((e) => e.id === S.evSel)) loadEvento(S.evSel);
  else { S.evSel = null; $("#eventoDetail").innerHTML = `<p class="empty">Elige un evento para ver y ordenar sus secciones.</p>`; }
}
$("#eventosList").onclick = (e) => {
  const b = e.target.closest(".list-item"); if (!b) return;
  S.evSel = +b.dataset.id;
  $$("#eventosList .list-item").forEach((x) => x.classList.toggle("active", x === b));
  loadEvento(S.evSel);
};
async function loadEvento(id) {
  const ev = await api("api/eventos/" + id);
  S.evDet = ev;
  const secs = ev.secciones;
  const tot = secs.reduce((a, s) => a + (s.duracion || 0), 0);
  const cont = secs.filter((s) => s.contabilizable);
  $("#eventoDetail").innerHTML = `
    <div class="detail-head">
      <div><h2>${esc(ev.nombre)} ${ev.numero ? `<span class="chip">#${ev.numero}</span>` : ""}</h2>
      <div class="muted">${esc(ev.tipo || "")}</div></div>
      <div class="row gap wrap">
        <button class="btn primary" id="evTx">📡 Transmitir ahora</button>
        <button class="btn" id="evEdit">Editar</button>
        <button class="btn ghost" id="evDel">Borrar</button>
      </div>
    </div>
    <div class="totals"><span>Duración total <b>${fmt(tot)}</b></span>
      <span>Contabilizables <b>${cont.length}</b> · ${fmt(cont.reduce((a, s) => a + (s.duracion || 0), 0))}</span></div>
    <div id="evSecs">${secs.length ? secs.map((s, i) => `
      <div class="sec-row" data-idx="${i}" data-id="${s.id}">
        <span class="n">${i + 1}</span>
        <span class="name"><span class="chip ${s.tipo}">${s.tipo}</span> ${esc(s.nombre)}${s.regenerar_antes ? " 🔄" : ""}
          <small>${fmt(s.duracion)}${s.tiene_audio ? "" : " · ⚠ sin audio"}</small></span>
        <label class="check" title="Cuenta para {num_secciones}" style="margin:0"><input type="checkbox" data-cont ${s.contabilizable ? "checked" : ""}></label>
        <span class="mini">
          <button class="btn" data-mv="-1" ${i === 0 ? "disabled" : ""} title="Mover arriba">↑</button>
          <button class="btn" data-mv="1" ${i === secs.length - 1 ? "disabled" : ""} title="Mover abajo">↓</button>
          <button class="btn" data-rm title="Quitar del evento">✕</button>
        </span>
      </div>`).join("") : `<p class="empty">Este evento no tiene secciones.</p>`}</div>
    <div class="row gap" style="margin-top:12px"><button class="btn" id="evAdd">+ Agregar secciones</button></div>
    <div class="links" id="evLinks"></div>`;
  renderLinks(ev);
  $("#evTx").onclick = () => txStart(ev.id, ev.nombre);
  $("#evEdit").onclick = () => eventoForm(ev);
  $("#evDel").onclick = async () => {
    if (!(await confirmBox(`¿Borrar el evento «${ev.nombre}» y su programación? Las secciones se conservan en la biblioteca.`, "Borrar"))) return;
    await run(() => api("api/eventos/" + ev.id, { method: "DELETE" }), "Evento borrado");
    S.evSel = null; loadEventos();
  };
  $("#evAdd").onclick = () => addSecciones(ev);
  $("#evSecs").onclick = async (e) => {
    const row = e.target.closest(".sec-row"); if (!row) return;
    const sid = +row.dataset.id;
    const b = e.target.closest("button");
    if (b && b.dataset.mv) {
      const ids = secs.map((s) => s.id), i = ids.indexOf(sid), j = i + +b.dataset.mv;
      [ids[i], ids[j]] = [ids[j], ids[i]];
      await run(() => api(`api/eventos/${ev.id}/orden`, { method: "PUT", json: { ids } }));
      loadEvento(ev.id);
    } else if (b && "rm" in b.dataset) {
      await run(() => api(`api/eventos/${ev.id}/secciones/${sid}`, { method: "DELETE" }));
      loadEventos();
    }
  };
  $("#evSecs").onchange = async (e) => {
    if (!("cont" in e.target.dataset)) return;
    const sid = +e.target.closest(".sec-row").dataset.id;
    await run(() => api(`api/eventos/${ev.id}/secciones/${sid}/contabilizable`, { method: "PUT", json: { value: e.target.checked } }));
    loadEvento(ev.id);
  };
}
/* ── Conexiones automáticas de un evento ─────────────────────────────────── */
const ACC = { conectar: "Conectar", desconectar: "Desconectar", desconectar_todo: "Desconectar todo" };
const MODO = { transceptor: "transceptor", monitor: "solo monitor", permanente: "permanente" };
const evSummary = (e) => `${e.num_secciones} secciones · ${fmt(e.duracion_total)}${e.tipo ? " · " + esc(e.tipo) : ""}${e.num_conexiones ? " · 🔗 " + e.num_conexiones : ""}`;
function linkText(a) {
  if (a.sistema === "irlp") return a.accion === "conectar" ? `Conectar a ${esc(a.destino)}` : "Desconectar (end)";
  if (a.accion === "desconectar_todo") return "Desconectar todos los enlaces";
  if (a.accion === "desconectar") return `Desconectar ${esc(a.destino)}`;
  return `Conectar a ${esc(a.destino)}${a.modo && a.modo !== "transceptor" ? ` <span class="muted">(${MODO[a.modo]})</span>` : ""}`;
}
function linkWhen(a) {
  const m = +a.minutos || 0;
  if (a.momento === "antes") return m ? `${m} min antes` : "Al iniciar";
  return m ? `${m} min después` : "Al terminar";
}
async function renderLinks(ev) {
  const info = await getInfo();
  const sis = info.sistemas || {};
  const list = ev.conexiones || [];
  const none = !sis.asl && !sis.irlp;
  const det = [sis.asl && "ASL" + (sis.asl_nodo ? " " + sis.asl_nodo : ""), sis.irlp && "IRLP"].filter(Boolean).join(" y ");
  $("#evLinks").innerHTML = `
    <h3>Conexiones automáticas</h3>
    <p class="muted" style="margin:0 0 8px">Se ejecutan al lanzar el evento (a mano o programado) y al terminar, aunque lo detengas.
      «N min antes» solo se adelanta cuando el evento está programado; a mano se hace al iniciar.
      <br>${none ? "⚠ No detecté ASL ni IRLP en este equipo: las acciones no podrán ejecutarse." : "Detectado en este nodo: " + esc(det) + "."}</p>
    <div id="lkList">${list.length ? list.map((a, i) => `
      <div class="link-row" data-i="${i}">
        <span class="when">${linkWhen(a)}</span>
        <span><span class="chip ${a.sistema}">${a.sistema.toUpperCase()}</span> ${linkText(a)}</span>
        <span class="mini">
          <button class="btn" data-act="test" title="Ejecutar ahora">▶</button>
          <button class="btn" data-act="edit" title="Editar">✎</button>
          <button class="btn" data-act="rm" title="Quitar">✕</button>
        </span>
      </div>`).join("") : `<p class="muted">Este evento no conecta ni desconecta nada.</p>`}</div>
    <div class="row gap" style="margin-top:8px"><button class="btn" id="lkAdd">+ Agregar conexión o desconexión</button></div>`;
  const save = async (items) => {
    const r = await run(() => api(`api/eventos/${ev.id}/conexiones`, { method: "PUT", json: { items } }), "Conexiones guardadas");
    ev.conexiones = r.conexiones; renderLinks(ev); refreshEventosList();
  };
  $("#lkAdd").onclick = () => linkForm(null, sis, (a) => save([...list, a]));
  $("#lkList").onclick = async (e) => {
    const b = e.target.closest("button[data-act]"); if (!b) return;
    const i = +b.closest(".link-row").dataset.i, a = list[i];
    if (b.dataset.act === "rm") {
      if (await confirmBox("¿Quitar esta acción del evento?", "Quitar")) save(list.filter((_, j) => j !== i));
    } else if (b.dataset.act === "edit") {
      linkForm(a, sis, (n) => save(list.map((x, j) => (j === i ? n : x))));
    } else if (b.dataset.act === "test") {
      const what = a.sistema.toUpperCase() + ": " + linkText(a).replace(/<[^>]+>/g, "");
      if (!(await confirmBox(`¿Ejecutar ahora «${what}»? Esto cambia los enlaces reales del nodo.`, "Ejecutar"))) return;
      busy(b, true, "…");
      try { const r = await api("api/conexiones/probar", { method: "POST", json: a }); toast("Hecho: " + r.comando); }
      catch (err) { toast(err.message, true); }
      finally { busy(b, false); }
    }
  };
}
async function refreshEventosList() {
  const ev = await api("api/eventos");
  S.eventos = ev.eventos;
  $$("#eventosList .list-item").forEach((b) => {
    const e = S.eventos.find((x) => x.id === +b.dataset.id);
    if (e) b.querySelector("small").innerHTML = evSummary(e);
  });
}
function linkForm(a, sis, onSave) {
  const avail = ["asl", "irlp"].filter((x) => sis[x]);
  const opts = avail.length ? avail : ["asl", "irlp"];
  a = a || { sistema: opts[0], accion: "conectar", destino: "", modo: "transceptor", momento: "antes", minutos: 0 };
  if (!opts.includes(a.sistema)) opts.push(a.sistema);
  openModal("Conexión o desconexión", `
    <form id="lf">
      <div class="grid2">
        <label>Sistema<select name="sistema">${opts.map((x) => `<option value="${x}" ${x === a.sistema ? "selected" : ""}>${x.toUpperCase()}</option>`).join("")}</select></label>
        <label>Acción<select name="accion"></select></label>
      </div>
      <div class="grid2">
        <label id="lfDest">Nodo<input name="destino" inputmode="numeric" value="${esc(a.destino)}" placeholder="2000"><small id="lfHint"></small></label>
        <label id="lfModo">Modo<select name="modo">${Object.entries(MODO).map(([k, v]) => `<option value="${k}" ${k === (a.modo || "transceptor") ? "selected" : ""}>${v}</option>`).join("")}</select></label>
      </div>
      <div class="grid2">
        <label>Cuándo<select name="momento"><option value="antes" ${a.momento === "antes" ? "selected" : ""}>Antes de iniciar</option><option value="despues" ${a.momento === "despues" ? "selected" : ""}>Al terminar</option></select></label>
        <label>Minutos<input name="minutos" type="number" min="0" max="120" step="1" value="${+a.minutos || 0}"><small id="lfMin"></small></label>
      </div>
      <p class="err" id="lfErr"></p>
      <div class="modal-actions"><button type="button" class="btn" onclick="closeModal()">Cancelar</button><button class="btn primary">Guardar</button></div>
    </form>`);
  const f = $("#lf");
  let acc = a.accion;
  const sync = () => {
    const irlp = f.sistema.value === "irlp";
    const accs = irlp ? { conectar: "Conectar", desconectar_todo: "Desconectar (end)" } : ACC;
    if (f.accion.value) acc = f.accion.value;
    if (!accs[acc]) acc = irlp && acc === "desconectar" ? "desconectar_todo" : "conectar";
    f.accion.innerHTML = Object.entries(accs).map(([k, v]) => `<option value="${k}" ${k === acc ? "selected" : ""}>${v}</option>`).join("");
    $("#lfDest").classList.toggle("hidden", acc === "desconectar_todo");
    $("#lfModo").classList.toggle("hidden", irlp || acc !== "conectar");
    $("#lfHint").textContent = irlp ? "Nodo (4 dígitos) o reflector, p. ej. 9050" : "Nodo AllStar, o EchoLink (3xxxxxx)";
    const m = +f.minutos.value || 0;
    $("#lfMin").textContent = f.momento.value === "antes" ? (m ? `${m} min antes de la hora programada` : "Justo al iniciar")
      : (m ? `${m} min después de terminar` : "En cuanto termina");
  };
  f.onchange = sync; f.minutos.oninput = sync; sync();
  f.onsubmit = (e) => {
    e.preventDefault();
    const n = { sistema: f.sistema.value, accion: f.accion.value, destino: f.destino.value.trim(),
      modo: f.modo.value, momento: f.momento.value, minutos: +f.minutos.value || 0 };
    const re = n.sistema === "irlp" ? /^\d{4,6}$/ : /^\d{3,7}$/;
    if (n.accion !== "desconectar_todo" && !re.test(n.destino)) { $("#lfErr").textContent = "Escribe un número de nodo válido"; return; }
    closeModal(); onSave(n);
  };
}

async function addSecciones(ev) {
  const all = await api("api/secciones");
  const have = new Set(ev.secciones.map((s) => s.id));
  const avail = all.filter((s) => !have.has(s.id));
  if (!avail.length) return toast("Todas las secciones de la biblioteca ya están en este evento. Crea más en la pestaña Secciones.", true);
  openModal("Agregar secciones", `
    <input type="search" id="pkSearch" placeholder="Buscar…" style="margin-bottom:10px">
    <div class="pick" id="pk">${avail.map((s) => `<label data-n="${esc(s.nombre.toLowerCase())}"><input type="checkbox" value="${s.id}">
      <span class="chip ${s.tipo}">${s.tipo}</span> ${esc(s.nombre)} <span class="muted" style="margin-left:auto">${fmt(s.duracion)}</span></label>`).join("")}</div>
    <div class="modal-actions"><button class="btn" onclick="closeModal()">Cancelar</button><button class="btn primary" id="pkOk">Agregar</button></div>`);
  $("#pkSearch").oninput = (e) => $$("#pk label").forEach((l) => l.classList.toggle("hidden", !l.dataset.n.includes(e.target.value.toLowerCase())));
  $("#pkOk").onclick = async () => {
    const ids = $$("#pk input:checked").map((c) => +c.value);
    if (!ids.length) return closeModal();
    await run(() => api(`api/eventos/${ev.id}/secciones`, { method: "POST", json: { ids } }), "Agregadas");
    closeModal(); loadEventos();
  };
}
$("#btnNewEvento").onclick = () => eventoForm(null);
function eventoForm(ev) {
  ev = ev || { nombre: "", tipo_evento_id: "", numero: "" };
  openModal(ev.id ? "Editar evento" : "Nuevo evento", `
    <form id="ef">
      <label>Nombre<input name="nombre" value="${esc(ev.nombre)}" required placeholder="Boletín dominical"></label>
      <div class="grid2">
        <label>Tipo<select name="tipo_evento_id"><option value="">—</option>${S.tipos.map((t) =>
          `<option value="${t.id}" ${t.id === ev.tipo_evento_id ? "selected" : ""}>${esc(t.nombre)}</option>`).join("")}</select></label>
        <label>Número de edición<input name="numero" type="number" min="0" value="${esc(ev.numero ?? "")}"><small>Opcional. Se lee con {numero}.</small></label>
      </div>
      <div class="modal-actions"><button type="button" class="btn" onclick="closeModal()">Cancelar</button><button class="btn primary">Guardar</button></div>
    </form>`);
  $("#ef").onsubmit = async (e) => {
    e.preventDefault();
    const f = e.target, data = { nombre: f.nombre.value, tipo_evento_id: f.tipo_evento_id.value, numero: f.numero.value };
    const r = await run(() => api("api/eventos" + (ev.id ? "/" + ev.id : ""), { method: ev.id ? "PUT" : "POST", json: data }), "Guardado");
    if (!ev.id) S.evSel = r.id;
    closeModal(); loadEventos();
  };
}

/* ── Secciones ───────────────────────────────────────────────────────────── */
async function loadSecciones() {
  S.secciones = await api("api/secciones");
  renderSecciones();
}
function renderSecciones() {
  const q = $("#secSearch").value.toLowerCase(), t = $("#secFilter").value;
  const list = S.secciones.filter((s) => (!t || s.tipo === t) &&
    (!q || (s.nombre + " " + (s.texto_tts || "") + " " + (s.titulo || "")).toLowerCase().includes(q)));
  $("#secList").innerHTML = `<div class="trow head"><span>Tipo</span><span>Nombre</span><span>Duración</span><span>Eventos</span><span></span></div>` +
    (list.length ? list.map((s) => `
    <div class="trow" data-id="${s.id}">
      <span class="chipcol"><span class="chip ${s.tipo}">${s.tipo}</span></span>
      <span class="name"><b>${esc(s.nombre)}</b>${s.regenerar_antes ? " 🔄" : ""}
        <small>${esc(s.tipo === "TTS" ? s.texto_tts : s.ruta_archivo || "")}</small></span>
      <span class="num">${s.tiene_audio ? fmt(s.duracion) : "⚠"}</span>
      <span class="num">${s.usos}</span>
      <span class="mini">
        <button class="btn ro" data-act="play" title="Escuchar aquí" ${s.tiene_audio ? "" : "disabled"}>▶</button>
        <button class="btn" data-act="air" title="Transmitir por el nodo" ${s.tiene_audio ? "" : "disabled"}>📡</button>
        <button class="btn" data-act="edit" title="Editar">✎</button>
        <button class="btn" data-act="del" title="Borrar">🗑</button>
      </span>
    </div>`).join("") : `<p class="empty">${S.secciones.length ? "Nada coincide con la búsqueda." : "La biblioteca está vacía. Crea una sección TTS o sube un audio."}</p>`);
}
$("#secSearch").oninput = renderSecciones;
$("#secFilter").onchange = renderSecciones;
$("#btnNewSec").onclick = () => seccionForm(null);
$("#secList").onclick = async (e) => {
  const b = e.target.closest("button[data-act]"); if (!b) return;
  const s = S.secciones.find((x) => x.id === +b.closest(".trow").dataset.id);
  if (b.dataset.act === "play") {
    openModal(s.nombre, `<audio controls autoplay src="api/secciones/${s.id}/audio" style="width:100%"></audio>
      ${s.tipo === "TTS" ? `<p class="muted">${esc(s.texto_tts)}</p>` : ""}`);
  } else if (b.dataset.act === "air") {
    if (await confirmBox(`¿Transmitir «${s.nombre}» (${fmt(s.duracion)}) por el nodo ahora?`, "📡 Transmitir"))
      run(() => api(`api/secciones/${s.id}/aire`, { method: "POST" }), "Transmitiendo…");
  } else if (b.dataset.act === "edit") seccionForm(s);
  else if (b.dataset.act === "del") {
    const warn = s.usos ? ` Se quitará de ${s.usos} evento(s).` : "";
    if (await confirmBox(`¿Borrar «${s.nombre}»?${warn}`, "Borrar")) {
      await run(() => api("api/secciones/" + s.id, { method: "DELETE" }), "Borrada"); loadSecciones();
    }
  }
};
async function getInfo() { if (!S.info) S.info = await api("api/info"); return S.info; }

async function seccionForm(s) {
  const info = await getInfo();
  const isNew = !s;
  s = s || { tipo: "TTS", nombre: "", texto_tts: "", titulo: "", descripcion: "", regenerar_antes: 0 };
  openModal(isNew ? "Nueva sección" : "Editar sección", `
    <form id="sf">
      ${isNew ? `<div class="seg" id="sfTipo">${["TTS", "Audio", "Sonido"].map((t) =>
        `<button type="button" class="btn ${t === s.tipo ? "active" : ""}" data-t="${t}">${t === "TTS" ? "🗣 Texto a voz" : t === "Audio" ? "🎵 Audio" : "🔔 Sonido"}</button>`).join("")}</div>` : ""}
      <label>Nombre<input name="nombre" value="${esc(s.nombre)}" required placeholder="Bienvenida"></label>
      <div class="only-tts">
        <div class="grid2">
          <label>Título<input name="titulo" value="${esc(s.titulo || "")}"><small>Se lee con {titulo}</small></label>
          <label>Descripción<input name="descripcion" value="${esc(s.descripcion || "")}"><small>Se lee con {descripcion}</small></label>
        </div>
        <label>Texto<textarea name="texto_tts" rows="6">${esc(s.texto_tts || "")}</textarea></label>
        <div class="vars">${info.variables.map(([v, d]) => `<button type="button" title="${esc(d)}">${v}</button>`).join("")}</div>
        <label class="check"><input type="checkbox" name="regenerar_antes" ${s.regenerar_antes ? "checked" : ""}> 🔄 Regenerar justo antes de transmitir (para {hora}, {fecha}, etc.)</label>
        <div class="row gap"><button type="button" class="btn" id="sfPrev">▶ Escuchar prueba</button><audio id="sfAudio" controls class="hidden" style="flex:1"></audio></div>
        <p class="muted" id="sfResolved" style="font-size:.85rem"></p>
      </div>
      <div class="only-file">
        <label>Archivo de audio<input type="file" name="archivo" accept="${info.formatos.join(",")}">
          <small>${!isNew && s.ruta_archivo ? "Actual: " + esc(s.ruta_archivo) + " · " + fmt(s.duracion) + ". Sube otro solo si quieres reemplazarlo." : info.formatos.map((f) => f.slice(1).toUpperCase()).join(", ") + ". Se convierte solo al formato del nodo."}</small></label>
        <div id="sfProg" class="bar hidden"><div></div></div>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn" onclick="closeModal()">Cancelar</button>
        <button class="btn primary" id="sfSave">${isNew ? "Crear" : "Guardar"}</button>
      </div>
    </form>`);
  const f = $("#sf");
  let tipo = s.tipo;
  const apply = () => {
    $$(".only-tts", f).forEach((x) => x.classList.toggle("hidden", tipo !== "TTS"));
    $$(".only-file", f).forEach((x) => x.classList.toggle("hidden", tipo === "TTS"));
  };
  apply();
  if (isNew) $("#sfTipo").onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    tipo = b.dataset.t; $$("#sfTipo button").forEach((x) => x.classList.toggle("active", x === b)); apply();
  };
  $(".vars", f).onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const ta = f.texto_tts, p = ta.selectionStart ?? ta.value.length;
    ta.value = ta.value.slice(0, p) + b.textContent + ta.value.slice(ta.selectionEnd ?? p);
    ta.focus(); ta.selectionStart = ta.selectionEnd = p + b.textContent.length;
  };
  $("#sfPrev").onclick = async () => {
    const b = $("#sfPrev"); busy(b, true, "Generando…");
    try {
      const r = await api("api/tts/preview", { method: "POST", json: { texto: f.texto_tts.value, titulo: f.titulo.value || f.nombre.value, descripcion: f.descripcion.value } });
      const a = $("#sfAudio"); a.src = r.url; a.classList.remove("hidden"); a.play();
      $("#sfResolved").textContent = "Se leerá: " + r.texto;
    } catch (e) { toast(e.message, true); } finally { busy(b, false); }
  };
  f.onsubmit = (e) => {
    e.preventDefault();
    const fd = new FormData();
    fd.append("nombre", f.nombre.value);
    fd.append("tipo", tipo);
    if (tipo === "TTS") {
      ["titulo", "descripcion", "texto_tts"].forEach((k) => fd.append(k, f[k].value));
      fd.append("regenerar_antes", f.regenerar_antes.checked ? "1" : "0");
      const changed = isNew || f.texto_tts.value !== (s.texto_tts || "") || f.titulo.value !== (s.titulo || "") || f.descripcion.value !== (s.descripcion || "") || !s.tiene_audio;
      fd.append("generar", changed ? "1" : "0");
    } else if (f.archivo.files[0]) fd.append("archivo", f.archivo.files[0]);
    upload(isNew ? "api/secciones" : "api/secciones/" + s.id, fd, $("#sfSave"), $("#sfProg"))
      .then(() => { toast(isNew ? "Sección creada" : "Guardada"); closeModal(); loadSecciones(); S.info = null; })
      .catch((err) => toast(err.message, true));
  };
}
/* Subida con barra de progreso (fetch no informa el avance) */
function upload(url, fd, btn, bar) {
  return new Promise((res, rej) => {
    const x = new XMLHttpRequest();
    x.open("POST", url); x.setRequestHeader("X-HAMNA", "1");
    busy(btn, true, "Subiendo…");
    if (bar) { bar.classList.remove("hidden"); x.upload.onprogress = (e) => { if (e.lengthComputable) $("div", bar).style.width = (e.loaded / e.total * 100) + "%"; }; }
    x.upload.onload = () => busy(btn, true, "Procesando…");
    x.onload = () => {
      busy(btn, false);
      let d = {}; try { d = JSON.parse(x.responseText); } catch {}
      if (x.status === 401) { showLogin(); return rej(new Error("Inicia sesión")); }
      if (x.status >= 400 || d.ok === false) rej(new Error(d.error || "Error " + x.status)); else res(d);
    };
    x.onerror = () => { busy(btn, false); rej(new Error("Se perdió la conexión con el nodo")); };
    x.send(fd);
  });
}

/* ── Ajustes ─────────────────────────────────────────────────────────────── */
$$("#setNav button").forEach((b) => (b.onclick = () => showSet(b.dataset.set)));
function showSet(k) {
  if (!isAdmin()) k = "seguridad";
  S.setSec = k;
  try { localStorage.setItem("hamna.set", k); } catch {}
  $$("#setNav button").forEach((b) => b.classList.toggle("active", b.dataset.set === k));
  $$("#setForm fieldset").forEach((f) => f.classList.toggle("hidden", f.dataset.set !== k));
  $("#saveBar").classList.toggle("hidden", ["seguridad", "sistema", "usuarios"].includes(k));
  if (k === "sistema") loadSistema();
  if (k === "seguridad") loadMyAccount();
  if (k === "usuarios") loadUsers();
}
async function loadAjustes() {
  S.cfg = await api("api/ajustes");
  const info = await getInfo();
  const f = $("#setForm");
  for (const el of f.elements) {
    if (!el.name || !(el.name in S.cfg)) continue;
    if (el.type === "checkbox") el.checked = !!S.cfg[el.name];
    else if (el.name !== "azure_key") el.value = S.cfg[el.name] ?? "";
  }
  f.azure_key.placeholder = S.cfg.azure_key_set ? "•••••• (guardada; escribe para cambiarla)" : "Pega aquí tu clave";
  f.azure_key.value = "";
  $("#detectHint").textContent = `Detectado en este equipo: ${info.detectado.toUpperCase()}${info.nodo_detectado ? " · nodo " + info.nodo_detectado : ""}`;
  const names = { azure: "Azure", piper: "Piper", espeak: "eSpeak" };
  $("#ttsHint").textContent = "Disponibles en este nodo: " + info.motores_tts.map((m) => names[m]).join(", ");
  $$("#setForm [name=tts_engine] option").forEach((o) => (o.disabled = !info.motores_tts.includes(o.value)));
  syncSetVis();
  renderPauseSounds();
  applyLogo(S.logo);
  showSet(S.setSec);
}
function syncSetVis() {
  const f = $("#setForm");
  const be = f.backend.value === "auto" ? (S.info ? S.info.detectado : "") : f.backend.value;
  $$(".only-asl", f).forEach((x) => x.classList.toggle("hidden", be !== "asl"));
  $$(".only-irlp", f).forEach((x) => x.classList.toggle("hidden", be !== "irlp"));
  $$(".only-azure", f).forEach((x) => x.classList.toggle("hidden", f.tts_engine.value !== "azure"));
  $$(".only-espeak", f).forEach((x) => x.classList.toggle("hidden", f.tts_engine.value !== "espeak"));
}
$("#setForm").addEventListener("change", syncSetVis);
$("#setForm").onsubmit = async (e) => {
  e.preventDefault();
  const f = e.target, data = {};
  for (const el of f.elements) {
    if (!el.name || el.closest("#pauseSounds")) continue;
    if (el.type === "checkbox") data[el.name] = el.checked;
    else if (el.name === "azure_key") { if (el.value.trim()) data.azure_key = el.value.trim(); }
    else data[el.name] = el.value;
  }
  const r = await run(() => api("api/ajustes", { method: "PUT", json: data }), "Ajustes guardados");
  S.cfg = r.ajustes; S.info = null; updateNodeLabel(); loadAjustes();
};
$("#btnCompactar").onclick = async () => {
  if (!(await confirmBox("Se van a convertir todas las secciones al formato del aire y se borrarán los audios originales. Esto no se puede deshacer.", "Sí, convertir y borrar"))) return;
  const b = $("#btnCompactar"); busy(b, true, "Convirtiendo…");
  try {
    const r = await api("api/secciones/compactar", { method: "POST" });
    if (r.errores.length) toast("No se pudieron convertir: " + r.errores.join(", "), true);
    else toast(r.convertidas ? `${r.convertidas} secciones convertidas · ${r.liberado_mb} MB liberados` : "No había originales que convertir");
  } catch (e) { toast(e.message, true); }
  finally { busy(b, false); }
};
function renderPauseSounds() {
  const items = [["alerta", "pause_alert_file", "🔔 Alerta", "Suena encima del audio, segundos antes de la pausa"],
    ["pausa", "pause_announcement_file", "⏸ Anuncio de pausa", "Al cortar, antes de soltar el PTT"],
    ["continuamos", "pause_resume_file", "▶ Continuamos", "Al regresar de la pausa"]];
  $("#pauseSounds").innerHTML = items.map(([k, key, label, hint]) => `
    <div class="psound" data-k="${k}">
      <div><b>${label}</b><br><small class="muted">${hint}</small></div>
      <div>${S.cfg[key] ? `<audio controls preload="none" src="api/ajustes/sonido/${k}?t=${encodeURIComponent(S.cfg[key])}"></audio>` : '<span class="muted">Sin audio</span>'}</div>
      <div class="row gap"><label class="btn sm" style="margin:0">Subir<input type="file" accept="audio/*" hidden></label>
        ${S.cfg[key] ? '<button type="button" class="btn sm ghost" data-del>Quitar</button>' : ""}</div>
    </div>`).join("");
}
$("#pauseSounds").onchange = async (e) => {
  if (e.target.type !== "file" || !e.target.files[0]) return;
  const k = e.target.closest(".psound").dataset.k, fd = new FormData();
  fd.append("archivo", e.target.files[0]);
  try { await upload("api/ajustes/sonido/" + k, fd); toast("Audio guardado"); S.cfg = await api("api/ajustes"); renderPauseSounds(); }
  catch (err) { toast(err.message, true); }
};
$("#pauseSounds").onclick = async (e) => {
  if (!e.target.closest("[data-del]")) return;
  const k = e.target.closest(".psound").dataset.k;
  await run(() => api("api/ajustes/sonido/" + k, { method: "DELETE" }), "Quitado");
  S.cfg = await api("api/ajustes"); renderPauseSounds();
};
$("#btnTestNode").onclick = async () => {
  const b = $("#btnTestNode"); busy(b, true, "Probando…");
  try { const r = await api("api/prueba/nodo", { method: "POST" });
    $("#testNodeMsg").textContent = (r.ok ? "✅ " : "❌ ") + r.mensaje; }
  catch (e) { $("#testNodeMsg").textContent = "❌ " + e.message; } finally { busy(b, false); }
};
$("#btnTestAir").onclick = async () => {
  if (!(await confirmBox("Se va a activar el transmisor del nodo con un mensaje de prueba. ¿Continuar?", "📡 Transmitir"))) return;
  const b = $("#btnTestAir"); busy(b, true, "Generando…");
  try { await run(() => api("api/prueba/aire", { method: "POST", json: { texto: $("#testAirText").value } }), "Prueba al aire"); setTimeout(poll, 300); }
  catch {} finally { busy(b, false); }
};
$("#btnTtsTest").onclick = async () => {
  const b = $("#btnTtsTest"); busy(b, true, "Generando…");
  try {
    await api("api/ajustes", { method: "PUT", json: collectVoice() });
    const r = await api("api/tts/preview", { method: "POST", json: { texto: $("#ttsTestText").value } });
    const a = $("#ttsTestAudio"); a.src = r.url; a.classList.remove("hidden"); a.play();
  } catch (e) { toast(e.message, true); } finally { busy(b, false); }
};
function collectVoice() {
  const f = $("#setForm"), d = {};
  ["tts_engine", "azure_region", "azure_voice", "azure_style", "azure_rate", "azure_pitch", "espeak_voice", "espeak_speed", "espeak_pitch"]
    .forEach((k) => (d[k] = f[k].value));
  if (f.azure_key.value.trim()) d.azure_key = f.azure_key.value.trim();
  return d;
}
$("#btnVoices").onclick = async () => {
  const f = $("#setForm"), b = $("#btnVoices"); busy(b, true, "…");
  try {
    const r = await api("api/azure/voces", { method: "POST", json: { azure_key: f.azure_key.value, azure_region: f.azure_region.value } });
    $("#azureVoices").innerHTML = r.voces.map((v) => `<option value="${esc(v.name)}">${esc(v.display)} · ${esc(v.locale)} · ${esc(v.gender)}</option>`).join("");
    toast(`${r.voces.length} voces en español`);
  } catch (e) { toast(e.message, true); } finally { busy(b, false); }
};
$("#btnPw").onclick = async () => {
  try {
    await run(() => api("api/ajustes/password", { method: "POST", json: { actual: $("#pwOld").value, nueva: $("#pwNew").value } }), "Contraseña cambiada; tus otras sesiones se cerraron");
    $("#pwOld").value = $("#pwNew").value = ""; loadMyAccount();
  } catch {}
};
/* ── Actualizaciones (GitHub) ─────────────────────────────────────────────── */
function updCmd(d) {
  const tgz = `${d.url}/archive/refs/heads/main.tar.gz`;
  if (d.sabor === "hamvoip")
    return `cd /tmp && rm -rf hamna-main && curl -sL ${tgz} | tar xz && bash hamna-main/install.sh --sin-paquetes`;
  return `cd /tmp && rm -rf hamna-main && curl -sL ${tgz} | tar xz && sudo bash hamna-main/install.sh --sin-paquetes`;
}
async function loadUpdates(force) {
  const box = $("#updBox");
  if (!box) return;
  if (!isAdmin()) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  if (force) box.innerHTML = '<p class="muted">Buscando actualizaciones…</p>';
  let d;
  try { d = await api("api/actualizaciones" + (force ? "?forzar=1" : "")); }
  catch (e) {
    box.className = "upd-box";
    box.innerHTML = `<div class="upd-head"><span class="muted">${esc(e.message)}</span>
      <button type="button" class="btn sm" id="btnUpd">↻ Buscar de nuevo</button></div>`;
    $("#btnUpd").onclick = () => loadUpdates(true); return;
  }
  markUpdate(d);
  box.className = "upd-box" + (d.hay_actualizacion ? " new" : "");
  box.innerHTML = `<div class="upd-head">
      <div>${d.hay_actualizacion ? `<b>Hay una versión nueva: v${esc(d.ultima)}</b>` : `<b>HAMNA Web está al día</b>`}
        <div class="muted" style="font-size:.84rem">Instalada: v${esc(d.instalada)} · En GitHub: v${esc(d.ultima || "?")} · Consultado: ${esc(d.consultado)}</div></div>
      <div class="row gap"><a class="btn sm ghost" href="${esc(d.url)}" target="_blank" rel="noopener">GitHub ↗</a>
        <button type="button" class="btn sm" id="btnUpd">↻ Buscar de nuevo</button></div></div>
    ${d.cambios.length ? `<ul class="upd-list">${d.cambios.map((c) =>
      `<li><span class="d">${esc(c.fecha)}</span><span>${esc(c.titulo)}</span></li>`).join("")}</ul>` : ""}
    ${d.hay_actualizacion ? `<div class="upd-cmd">Para instalarla, en la terminal del nodo:
      <pre translate="no">${esc(updCmd(d))}</pre>
      <span class="muted">Conserva los datos, usuarios y ajustes. Antes de correrlo, revisa que nada esté al aire.</span></div>` : ""}`;
  $("#btnUpd").onclick = () => loadUpdates(true);
}
function markUpdate(d) {
  const v = $("#appVer");
  v.classList.toggle("has-update", !!(d && d.hay_actualizacion));
  v.title = d && d.hay_actualizacion ? `Hay una versión nueva: v${d.ultima}` : "";
}
$("#appVer").onclick = () => { if ($("#appVer").classList.contains("has-update")) { S.setSec = "sistema"; showTab("ajustes"); } };

async function loadSistema() {
  S.info = null;
  loadUpdates(false);
  const i = await getInfo();
  const be = i.backend || {};
  const rows = [["Versión", "HAMNA Web " + i.version], ["Salida al aire", (be.backend || "").toUpperCase() + (be.mode ? " · " + be.mode : "")],
    ["Nodo", be.node || be.stationid || "—"], ["Asterisk", be.asterisk], ["Nodo responde", be.nodo_ok == null ? null : be.nodo_ok ? "Sí" : "No"],
    ["Enlazado con", be.enlaces || be.conectado_a], ["Zona horaria", i.zona_horaria], ["Espacio libre", i.disco_libre_mb + " MB"],
    ["Sistema", { asl3: "AllStarLink 3", hamvoip: "HamVOIP", asl: "AllStarLink" }[i.sabor] || i.detectado],
    ["Audio", Object.entries(i.herramientas).filter(([, v]) => v).map(([k]) => k).join(", ") || "sin herramientas"],
    ["Formatos que acepta", i.formatos.map((f) => f.slice(1).toUpperCase()).join(", ")], ["Error", be.error]].filter((r) => r[1] != null && r[1] !== "");
  $("#sysInfo").innerHTML = `<dl>${rows.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
    <h3>Últimas transmisiones</h3>
    <div class="hist">${i.historial.length ? i.historial.map((h) => `<div><span>${esc(h.inicio)}</span><b>${esc(h.evento)}</b><span class="muted">${esc(h.origen)}</span><span>${esc(h.resultado || "en curso")}</span></div>`).join("") : '<p class="muted">Todavía no hay transmisiones.</p>'}</div>`;
}

/* ── Cron ────────────────────────────────────────────────────────────────── */
const CRON_F = [/^[\d*,\/-]+$/, /^[\d*,\/-]+$/, /^[\d*,\/-]+$/, /^[\d*,\/a-z-]+$/i, /^[\d*,\/a-z-]+$/i];
const CRON_SP = { "@reboot": "Al arrancar el equipo", "@hourly": "Cada hora", "@daily": "Cada día a medianoche",
  "@midnight": "Cada día a medianoche", "@weekly": "Cada domingo a medianoche", "@monthly": "El día 1 de cada mes",
  "@yearly": "Cada 1 de enero", "@annually": "Cada 1 de enero" };
function cronParse(raw) {
  if (!raw.trim()) return { kind: "blank", raw };
  let on = true, body = raw;
  const c = raw.match(/^\s*#\s?(.*)$/);
  if (c) { on = false; body = c[1]; }
  const sp = body.match(/^\s*(@(?:reboot|yearly|annually|monthly|weekly|daily|midnight|hourly))\s+(\S.*)$/);
  if (sp) return { kind: "entry", on, sched: sp[1], cmd: sp[2], raw };
  const m = body.match(/^\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S.*)$/);
  if (m && m.slice(1, 6).every((x, i) => CRON_F[i].test(x))) return { kind: "entry", on, sched: m.slice(1, 6).join(" "), cmd: m[6], raw };
  if (!on) return { kind: "comment", raw, text: body };
  return { kind: "other", raw };
}
const cronLine = (e) => (e.on ? "" : "#") + e.sched + " " + e.cmd;
function expandDow(d) {
  if (d === "*") return [0, 1, 2, 3, 4, 5, 6];
  const out = new Set();
  for (const part of d.split(",")) {
    const r = part.match(/^(\d)(?:-(\d))?$/);
    if (!r) return null;
    const a = +r[1], b = r[2] != null ? +r[2] : a;
    for (let i = a; i <= b; i++) out.add(i % 7);
  }
  return [...out].sort();
}
function dowText(d) {
  const days = expandDow(d);
  if (!days) return "días " + d;
  if (days.length === 7) return "Todos los días";
  const cap = (x) => x.charAt(0).toUpperCase() + x.slice(1);
  const contiguous = days.length >= 3 && days.every((d, i) => !i || d === days[i - 1] + 1);
  if (contiguous) return cap(`${DIAS[days[0]]} a ${DIAS[days[days.length - 1]]}`);
  const t = days.map((i) => DIAS[i]).join(", ");
  return t.charAt(0).toUpperCase() + t.slice(1);
}
function cronDesc(s) {
  if (CRON_SP[s]) return CRON_SP[s];
  const [m, h, dom, mon, dow] = s.split(" ");
  const num = (x) => /^\d+$/.test(x), nums = (x) => /^\d+(,\d+)*$/.test(x);
  const p2 = (x) => String(x).padStart(2, "0");
  let when;
  if (num(m) && nums(h)) when = "a las " + h.split(",").map((x) => `${p2(x)}:${p2(m)}`).join(" y ");
  else if (/^\*\/\d+$/.test(m) && h === "*") when = `cada ${m.slice(2)} min`;
  else if (num(m) && h === "*") when = `cada hora, al minuto ${m}`;
  else if (m === "*" && h === "*") when = "cada minuto";
  else if (nums(m)) when = `a los minutos ${m}` + (h === "*" ? "" : ` (horas ${h})`);
  else when = `min ${m}, hora ${h}`;
  let days;
  if (dom === "*" && mon === "*") days = dowText(dow);
  else if (mon === "*" && dow === "*" && nums(dom)) days = `Día ${dom} de cada mes`;
  else days = `Día ${dom}, mes ${mon}, semana ${dow}`;
  return `${days} ${when}`;
}
async function loadCron() {
  const el = $("#cronList");
  let r;
  try {
    const [c, prog] = await Promise.all([api("api/cron"), api("api/programacion").catch(() => null)]);
    r = c; if (prog) S.prog = prog;
  }
  catch (e) { el.innerHTML = `<p class="err">${esc(e.message)}</p>`; return; }
  if (!r.disponible) {
    el.innerHTML = `<p class="empty">Este equipo no tiene el ayudante de cron. Vuelve a ejecutar <code>install.sh</code> en el nodo.</p>`;
    return;
  }
  S.cron = r.tablas;
  S.cronEntries = cronEntries(r.tablas);
  const rel = cronRelations(S.cronEntries, S.prog || []);
  el.innerHTML = r.tablas.map((t, ti) => {
    if (t.error) return `<div class="cron-card"><header><h2>${esc(t.titulo)}</h2></header><p class="note err">${esc(t.error)}</p></div>`;
    const lines = t.texto.split("\n").map(cronParse);
    const rows = lines.map((l, li) => {
      if (l.kind === "entry") return `
        <div class="cron-row ${l.on ? "" : "off"}" data-li="${li}">
          <label class="check" style="margin:0" title="${l.on ? "Activa" : "Desactivada"}"><input type="checkbox" data-tog ${l.on ? "checked" : ""} ${t.editable ? "" : "disabled"}></label>
          <span class="when"><b>${esc(cronDesc(l.sched))}</b><small>${esc(l.sched)}</small></span>
          <code>${esc(l.cmd)}</code>
          <span class="mini">${t.editable ? `<button class="btn" data-edit title="Editar">✎</button><button class="btn" data-del title="Borrar">✕</button>` : ""}</span>
          ${cronTags(l, rel.get(t.id + ":" + li))}
        </div>`;
      if (l.kind === "comment" && l.text.trim()) return `<div class="cron-row comment"># ${esc(l.text)}</div>`;
      if (l.kind === "other") return `<div class="cron-row comment"><code>${esc(l.raw)}</code></div>`;
      return "";
    }).join("");
    const n = lines.filter((l) => l.kind === "entry").length;
    return `<div class="cron-card" data-ti="${ti}">
      <header><h2>${esc(t.titulo)} <span class="chip">${n} tareas</span></h2>
        ${t.editable ? `<div class="row gap wrap"><button class="btn" data-raw>Editar como texto</button><button class="btn primary" data-add>+ Agregar tarea</button></div>` : `<span class="muted">solo lectura</span>`}</header>
      ${t.nota ? `<p class="note">${esc(t.nota)}</p>` : ""}
      <div>${rows || `<p class="muted" style="padding:10px 14px">Sin tareas.</p>`}</div>
    </div>`;
  }).join("");
}
async function cronSave(t, text, msg) {
  try {
    await api("api/cron", { method: "PUT", json: { id: t.id, hash: t.hash, texto: text } });
    toast(msg || "Cron guardado");
  } catch (e) { toast(e.message, true); }
  loadCron();
}
function cronLines(t) { return t.texto.split("\n").map(cronParse); }
const cronJoin = (lines) => lines.map((l) => l.raw).join("\n");
$("#btnCronReload").onclick = loadCron;
$("#cronList").onclick = async (e) => {
  const card = e.target.closest(".cron-card"); if (!card || card.dataset.ti == null) return;
  const t = S.cron[+card.dataset.ti];
  const b = e.target.closest("button");
  if (!b || !t.editable) return;
  const lines = cronLines(t);
  if ("add" in b.dataset) return cronForm(t, null, (entry, comment) => {
    const add = [];
    if (comment) add.push({ raw: "# " + comment });
    add.push({ raw: cronLine(entry) });
    while (lines.length && lines[lines.length - 1].kind === "blank") lines.pop();
    cronSave(t, cronJoin([...lines, ...add]) + "\n", "Tarea agregada");
  });
  if ("raw" in b.dataset) return cronRaw(t);
  const li = +b.closest(".cron-row").dataset.li, l = lines[li];
  if ("del" in b.dataset) {
    if (!(await confirmBox(`¿Borrar esta tarea?\n\n${l.sched} ${l.cmd}`, "Borrar"))) return;
    lines.splice(li, 1);
    cronSave(t, cronJoin(lines), "Tarea borrada");
  } else if ("edit" in b.dataset) {
    cronForm(t, l, (entry) => { lines[li] = { raw: cronLine(entry) }; cronSave(t, cronJoin(lines), "Tarea guardada"); });
  }
};
$("#cronList").onchange = (e) => {
  if (!("tog" in e.target.dataset)) return;
  const t = S.cron[+e.target.closest(".cron-card").dataset.ti];
  const lines = cronLines(t), li = +e.target.closest(".cron-row").dataset.li, l = lines[li];
  l.on = e.target.checked; lines[li] = { raw: cronLine(l) };
  cronSave(t, cronJoin(lines), l.on ? "Tarea activada" : "Tarea desactivada");
};
function cronForm(t, l, onSave) {
  l = l || { on: true, sched: "0 8 * * *", cmd: "" };
  const f5 = l.sched.split(" ");
  const simple = f5.length === 5 && /^\d+$/.test(f5[0]) && /^\d+$/.test(f5[1]) && f5[2] === "*" && f5[3] === "*" && expandDow(f5[4]);
  const days = simple ? expandDow(f5[4]) : [0, 1, 2, 3, 4, 5, 6];
  const hhmm = simple ? `${f5[1].padStart(2, "0")}:${f5[0].padStart(2, "0")}` : "08:00";
  openModal(l.cmd ? "Editar tarea" : "Nueva tarea de cron", `
    <form id="cf">
      <div class="seg" id="cfMode"><button type="button" data-m="s" class="${simple ? "active" : ""}">Hora y días</button><button type="button" data-m="a" class="${simple ? "" : "active"}">Avanzado</button></div>
      <div id="cfS" class="${simple ? "" : "hidden"}">
        <label>Hora<input name="hora" type="time" value="${hhmm}"></label>
        <label>Días</label>
        <div class="days">${[1, 2, 3, 4, 5, 6, 0].map((i) => `<label><input type="checkbox" name="d" value="${i}" ${days.includes(i) ? "checked" : ""}> ${DIAS[i].slice(0, 3)}</label>`).join("")}</div>
      </div>
      <div id="cfA" class="${simple ? "hidden" : ""}">
        <label>Programación (minuto hora día-del-mes mes día-de-semana)<input name="sched" value="${esc(l.sched)}" class="cron-raw" style="min-height:0"><small id="cfDesc"></small></label>
      </div>
      <label>Comando<textarea name="cmd" rows="3" class="cron-raw" style="min-height:0" placeholder="/usr/sbin/asterisk -rx &quot;rpt cmd 59624 ilink 3 2000&quot;">${esc(l.cmd)}</textarea></label>
      ${l.cmd ? "" : `<label>Comentario (opcional)<input name="comment" placeholder="Conectar al boletín dominical"></label>`}
      <label class="check"><input type="checkbox" name="on" ${l.on ? "checked" : ""}> Activa</label>
      <p class="err" id="cfErr"></p>
      <div class="modal-actions"><button type="button" class="btn" onclick="closeModal()">Cancelar</button><button class="btn primary">Guardar</button></div>
    </form>`);
  const f = $("#cf");
  let mode = simple ? "s" : "a";
  const build = () => {
    if (mode === "a") return f.sched.value.trim().replace(/\s+/g, " ");
    const [h, m] = (f.hora.value || "00:00").split(":").map(Number);
    const d = $$("input[name=d]:checked", f).map((x) => +x.value).sort();
    return `${m} ${h} * * ${d.length === 7 || !d.length ? "*" : d.join(",")}`;
  };
  const desc = () => { const s = build(); $("#cfDesc").textContent = cronParse(s + " x").kind === "entry" ? cronDesc(s) : "Formato no válido"; };
  $("#cfMode").onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.m === "a" && mode === "s") f.sched.value = build();
    mode = b.dataset.m;
    $$("#cfMode button").forEach((x) => x.classList.toggle("active", x === b));
    $("#cfS").classList.toggle("hidden", mode !== "s"); $("#cfA").classList.toggle("hidden", mode !== "a");
    desc();
  };
  f.oninput = desc; desc();
  f.onsubmit = (e) => {
    e.preventDefault();
    const sched = build(), cmd = f.cmd.value.replace(/\s*\n\s*/g, " ").trim();
    if (mode === "s" && !$$("input[name=d]:checked", f).length) { $("#cfErr").textContent = "Elige al menos un día"; return; }
    if (!cmd) { $("#cfErr").textContent = "Escribe el comando"; return; }
    if (cronParse(sched + " " + cmd).kind !== "entry") { $("#cfErr").textContent = "La programación no es válida"; return; }
    closeModal();
    onSave({ on: f.on.checked, sched, cmd }, f.comment ? f.comment.value.trim().replace(/\n/g, " ") : "");
  };
}
function cronRaw(t) {
  openModal("Editar " + t.titulo, `
    <p class="muted">Texto completo de la tabla. Se valida antes de guardar y se respalda la versión anterior.</p>
    <textarea id="crTxt" class="cron-raw" spellcheck="false">${esc(t.texto)}</textarea>
    <div class="modal-actions"><button class="btn" onclick="closeModal()">Cancelar</button><button class="btn primary" id="crOk">Guardar</button></div>`);
  $("#crOk").onclick = () => {
    const text = $("#crTxt").value;
    closeModal();
    cronSave(t, text, "Cron guardado");
  };
}

/* ── Cron ↔ programación ─────────────────────────────────────────────────── */
// Cruza las tareas del cron con los eventos programados: qué corre antes,
// durante y después de cada evento, y cuánto tiempo queda conectado un nodo.
const WEEK = 7 * 1440;
const MARGEN = 60; // minutos antes y después del evento en los que se busca
const CRON_ALIAS = { "@hourly": "0 * * * *", "@daily": "0 0 * * *", "@midnight": "0 0 * * *", "@weekly": "0 0 * * 0" };
const DOW_N = { sun: 0, mon: 1, tue: 2, wed: 3, thu: 4, fri: 5, sat: 6 };
function cronSet(f, lo, hi, names) {
  const out = new Set();
  for (let part of f.toLowerCase().split(",")) {
    if (names) part = part.replace(/[a-z]{3}/g, (x) => (x in names ? names[x] : x));
    const m = part.match(/^(\*|(\d+)(?:-(\d+))?)(?:\/(\d+))?$/);
    if (!m) return null;
    const a = m[1] === "*" ? lo : +m[2];
    const b = m[1] === "*" ? hi : m[3] != null ? +m[3] : m[4] ? hi : a;
    const st = m[4] ? +m[4] : 1;
    if (!st || a < lo || b > hi || a > b) return null;
    for (let i = a; i <= b; i += st) out.add(i);
  }
  return out;
}
// Minutos de la semana (0 = domingo 00:00) en que corre la tarea; null si no es semanal.
function cronTimes(sched) {
  const f = (CRON_ALIAS[sched] || sched).split(" ");
  if (f.length !== 5 || f[2] !== "*" || f[3] !== "*") return null;
  const mi = cronSet(f[0], 0, 59), ho = cronSet(f[1], 0, 23), dw = cronSet(f[4], 0, 7, DOW_N);
  if (!mi || !ho || !dw) return null;
  const out = [];
  for (const d of new Set([...dw].map((x) => x % 7))) for (const h of ho) for (const m of mi) out.push(d * 1440 + h * 60 + m);
  return out.sort((a, b) => a - b);
}
// Qué hace un comando, lo que se pueda adivinar. Lo que va después de un # no lo ejecuta el shell.
function cronWhat(cmd) {
  const run = cmd.replace(/(^|[\s;&|])#.*$/, "$1").trim();
  const r = { act: "", text: "", ignorado: run.length < cmd.trim().length ? cmd.trim().slice(run.length).trim() : "" };
  let m;
  if ((m = run.match(/ilink\s+(\d+)(?:\s+(\d+))?/))) {
    const c = +m[1];
    if (c === 6) Object.assign(r, { act: "off", node: "*", text: "Desconecta todos los enlaces" });
    else if ((c === 1 || c === 11) && m[2]) Object.assign(r, { act: "off", node: m[2], text: "Desconecta " + m[2] });
    else if ([2, 3, 12, 13].includes(c) && m[2]) Object.assign(r, { act: "on", node: m[2], text: "Conecta a " + m[2] + (c % 10 === 2 ? " (monitor)" : "") });
  } else if ((m = run.match(/disconnect[_-]?(?:from[_-]?|to[_-]?)?(\d{3,7})/i))) Object.assign(r, { act: "off", node: m[1], text: "Desconecta " + m[1] });
  else if ((m = run.match(/connect[_-]?(?:to[_-]?)?(\d{3,7})/i))) Object.assign(r, { act: "on", node: m[1], text: "Conecta a " + m[1] });
  else if ((m = run.match(/\bdecode\s+(\d{4,6})/))) Object.assign(r, { act: "on", node: "irlp", text: "IRLP: conecta a " + m[1] });
  else if (/(^|[\/\s])end(\s|$)/.test(run) && /irlp|SCRIPT/i.test(run)) Object.assign(r, { act: "off", node: "irlp", text: "IRLP: desconecta" });
  else if ((m = run.match(/duplex[_-]?(\d)/i))) Object.assign(r, { act: "duplex", text: "Cambia a duplex=" + m[1] });
  else if (/saytime/i.test(run)) Object.assign(r, { act: "audio", text: "Anuncia la hora" });
  else if (/random\.sh|playback|localplay|\.wav\b|\.ul\b|\.gsm\b|say_/i.test(run)) Object.assign(r, { act: "audio", text: "Reproduce audio" });
  return r;
}
function cronEntries(tablas) {
  const out = [];
  for (const t of tablas || []) {
    if (t.error || !t.texto) continue;
    t.texto.split("\n").forEach((raw, li) => {
      const l = cronParse(raw);
      if (l.kind !== "entry" || !l.on) return;
      const times = cronTimes(l.sched);
      if (!times || !times.length) return;
      const days = new Set(times.map((x) => Math.floor(x / 1440))).size;
      out.push({ key: t.id + ":" + li, tabla: t.titulo, l, times, periodic: times.length / days > 3, what: cronWhat(l.cmd) });
    });
  }
  return out;
}
async function loadCronEntries() {
  try {
    if (!(await getInfo()).cron) return false;
    const r = await api("api/cron");
    S.cron = r.tablas; S.cronEntries = cronEntries(r.tablas);
    return true;
  } catch { return false; }
}
const hm = (s) => { const [h, m] = s.split(":").map(Number); return h * 60 + m; };
function progDays(p) {
  if (p.recurrencia === "diaria") return [0, 1, 2, 3, 4, 5, 6];
  if (p.recurrencia === "lun-vie") return [1, 2, 3, 4, 5];
  return [new Date((p.fecha_local || p.fecha) + "T12:00").getDay()];
}
const durMin = (p) => Math.round((p.duracion || 0) / 60);
// Tareas que caen cerca de un evento: {spec: [{e, off, days}], periodic: [{e, n}]}
function progCrons(p, entries) {
  const dur = durMin(p), cx = p.conexiones || [];
  const pre = Math.max(MARGEN, ...cx.filter((a) => a.momento === "antes").map((a) => +a.minutos + 15));
  const post = Math.max(MARGEN, ...cx.filter((a) => a.momento !== "antes").map((a) => +a.minutos + 15));
  const pd = progDays(p), spec = [], periodic = [];
  for (const e of entries) {
    const hits = new Map();
    let n = 0;
    for (const d of pd) {
      const s = d * 1440 + hm(p.hora_local || p.hora);
      for (const t of e.times) {
        let off = (((t - s) % WEEK) + WEEK) % WEEK;
        if (off > WEEK / 2) off -= WEEK;
        if (e.periodic) { if (off >= 0 && off <= dur) n++; }
        else if (off >= -pre && off <= dur + post) {
          if (!hits.has(off)) hits.set(off, new Set());
          hits.get(off).add(d);
        }
      }
    }
    if (n) periodic.push({ e, n: Math.round(n / pd.length) || 1 });
    hits.forEach((days, off) => spec.push({ e, off, days: days.size < pd.length ? [...days] : null }));
  }
  return { spec, periodic };
}
const p2 = (x) => String(x).padStart(2, "0");
function clock(p, off) {
  const t = hm(p.hora_local || p.hora) + off, d = Math.floor(t / 1440), m = ((t % 1440) + 1440) % 1440;
  return `${p2(Math.floor(m / 60))}:${p2(m % 60)}` + (d < 0 ? " (día anterior)" : d > 0 ? " (día siguiente)" : "");
}
const fmtMin = (m) => (m >= 60 ? `${Math.floor(m / 60)} h` + (m % 60 ? ` ${m % 60} min` : "") : `${m} min`);
const diasTxt = (days) => (days ? " · solo " + days.map((d) => DIAS[d]).join(", ") : "");
function linkAct(a) {
  if (a.accion === "conectar") return { act: "on", node: a.sistema === "irlp" ? "irlp" : a.destino };
  return { act: "off", node: a.sistema === "irlp" || a.accion === "desconectar_todo" ? "*" : a.destino };
}
function progTimeline(p) {
  const dur = durMin(p), cx = p.conexiones || [];
  const rel = progCrons(p, S.cronEntries || []);
  if (!cx.length && !rel.spec.length && !rel.periodic.length) return "";
  // rango para ordenar empates: antes → cron → inicio → fin → después
  const items = [{ off: 0, r: 2, ico: "▶", cls: "ev", html: `Inicia «${esc(p.evento_nombre)}»` },
    { off: dur, r: 3, ico: "⏹", cls: "ev", html: `Termina · dura ${fmt(p.duracion)} aprox.` }];
  for (const a of cx) {
    const antes = a.momento === "antes";
    items.push({ off: antes ? -(+a.minutos || 0) : dur + (+a.minutos || 0), r: antes ? 0 : 4, ico: "🔗", lk: linkAct(a),
      html: `<span class="chip ${a.sistema}">${a.sistema.toUpperCase()}</span> ${linkText(a)} <span class="muted">· del evento</span>` });
  }
  for (const s of rel.spec) {
    const w = s.e.what;
    items.push({ off: s.off, r: 1, ico: "⏰", lk: w.act === "on" || w.act === "off" ? w : null, title: s.e.l.cmd,
      html: `<span class="chip cron">CRON</span> ${esc(w.text || s.e.l.cmd.slice(0, 60))}${diasTxt(s.days)}` });
  }
  items.sort((a, b) => a.off - b.off || a.r - b.r);
  // Tramos conectados: de cada "conecta" al siguiente "desconecta" de ese nodo (o de todos)
  const open = new Map(), spans = [];
  for (const it of items) {
    if (!it.lk) continue;
    if (it.lk.act === "on" && !open.has(it.lk.node)) open.set(it.lk.node, it.off);
    if (it.lk.act === "off") {
      for (const [node, from] of [...open]) if (it.lk.node === "*" || it.lk.node === node) { spans.push({ node, from, to: it.off }); open.delete(node); }
    }
  }
  open.forEach((from, node) => spans.push({ node, from, to: null }));
  const nodeTxt = (n) => (n === "irlp" ? "IRLP" : n);
  const sum = spans.map((s) => `<div class="tl-span">🔗 Conectado a <b>${esc(nodeTxt(s.node))}</b> de ${clock(p, s.from)} ` +
    (s.to == null ? `<span class="warn-t">sin desconexión programada</span>` : `a ${clock(p, s.to)} · <b>${fmtMin(s.to - s.from)}</b>`) + `</div>`).join("");
  const warn = rel.periodic.map((x) => `<div class="tl-warn" title="${esc(x.e.l.cmd)}">⚠ Durante el evento también corre (cron) ~${x.n} ${x.n === 1 ? "vez" : "veces"}:
    ${esc(x.e.what.text || x.e.l.cmd.slice(0, 50))} · <span class="muted">${esc(cronDesc(x.e.l.sched))}</span></div>`).join("");
  const rows = items.map((it) => `<div class="tl-row ${it.cls || ""}"${it.title ? ` title="${esc(it.title)}"` : ""}>
      <span class="t">${clock(p, it.off)}</span><span>${it.ico}</span><span>${it.html}</span></div>`).join("");
  return `<details class="tl"${spans.length || rel.periodic.length ? " open" : ""}>
    <summary>Línea de tiempo${spans.length ? " · " + spans.map((s) => "🔗 " + esc(nodeTxt(s.node)) + (s.to == null ? "" : " " + fmtMin(s.to - s.from))).join(", ") : ""}</summary>
    ${sum}${rows}${warn}</details>`;
}
// Para la pestaña Cron: clave de tarea → [{p, off, periodic, days}]
function cronRelations(entries, prog) {
  const out = new Map();
  for (const p of prog) {
    if (!p.activo) continue;
    const rel = progCrons(p, entries);
    const add = (k, v) => { if (!out.has(k)) out.set(k, []); out.get(k).push(v); };
    rel.spec.forEach((s) => add(s.e.key, { p, off: s.off, days: s.days }));
    rel.periodic.forEach((s) => add(s.e.key, { p, periodic: true, n: s.n }));
  }
  return out;
}
function cronTags(l, rels) {
  const w = l.kind === "entry" ? cronWhat(l.cmd) : null;
  const tags = [];
  if (w && w.text) tags.push(`<span class="chip cron-what ${w.act}">${w.act === "on" || w.act === "off" ? "🔗 " : ""}${esc(w.text)}</span>`);
  for (const r of rels || []) {
    const name = esc(r.p.evento_nombre), dur = durMin(r.p);
    let txt;
    if (r.periodic) txt = `⚠ suena durante «${name}»`;
    else if (r.off < 0) txt = `📅 ${fmtMin(-r.off)} antes de «${name}»`;
    else if (r.off === 0) txt = `📅 al iniciar «${name}»`;
    else if (r.off <= dur) txt = `📅 durante «${name}»`;
    else txt = `📅 ${fmtMin(r.off - dur)} después de «${name}»`;
    tags.push(`<span class="chip ev-rel ${r.periodic ? "warn" : ""}" title="${esc(recText(r.p))} a las ${esc(r.p.hora)}">${txt} · ${esc(r.p.hora)}${esc(diasTxt(r.days))}</span>`);
  }
  if (w && w.ignorado && /\S/.test(w.ignorado)) tags.push(`<span class="chip muted-chip" title="${esc(w.ignorado)}">lo que va después de # no se ejecuta</span>`);
  return tags.length ? `<div class="cron-rel">${tags.join("")}</div>` : "";
}

/* ── Tema claro / oscuro ─────────────────────────────────────────────────── */
function applyTheme(th) {
  if (th === "light" || th === "dark") document.documentElement.dataset.theme = th;
  else delete document.documentElement.dataset.theme;
}
try { applyTheme(localStorage.getItem("hamna.theme")); } catch {}
$("#btnTheme").onclick = () => {
  const cur = document.documentElement.dataset.theme ||
    (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  const next = cur === "light" ? "dark" : "light";
  applyTheme(next);
  try { localStorage.setItem("hamna.theme", next); } catch {}
};

/* ── Conexiones: nodos conectados ──────────────────────────────────────────────
   Se consulta cada 4 s solo con esta pestaña abierta y visible. */
const SES_EVERY = 4000;
const ICON_NODE = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 0 1 0 8.4M7.8 16.2a6 6 0 0 1 0-8.4"/></svg>';
function stopSesiones() { clearTimeout(S.sesTimer); clearInterval(S.sesTick); S.sesTimer = S.sesTick = null; }
async function loadSesiones() {
  clearTimeout(S.sesTimer);
  if (S.tab !== "conexiones" || document.hidden) return;
  try {
    const q = S.sesNodo ? "?nodo=" + encodeURIComponent(S.sesNodo) : "";
    S.ses = await api("api/sesiones" + q); S.sesAt = Date.now();
    renderSesiones();
  } catch (e) {
    $("#sesList").innerHTML = `<p class="empty">${esc(e.message)}</p>`;
  }
  if (!S.sesTick) S.sesTick = setInterval(tickSesiones, 1000);
  S.sesTimer = setTimeout(loadSesiones, SES_EVERY);
}
const fmtUp = (s) => {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d ? `${d} d ${h} h` : h ? `${h} h ${String(m).padStart(2, "0")} min` : `${m} min ${String(s % 60).padStart(2, "0")} s`;
};
function tickSesiones() {
  if (!S.ses || document.hidden) return;
  const add = Math.floor((Date.now() - S.sesAt) / 1000);
  $$("#sesList [data-secs]").forEach((el) => (el.textContent = fmtUp(+el.dataset.secs + add)));
}
function renderSesiones() {
  const s = S.ses;
  const sel = $("#sesNodo");
  if ((s.nodos_locales || []).length > 1) {
    sel.innerHTML = s.nodos_locales.map((n) => `<option ${n === s.nodo ? "selected" : ""}>${esc(n)}</option>`).join("");
    sel.classList.remove("hidden");
  } else sel.classList.add("hidden");
  $("#sesConnect").classList.toggle("hidden", s.sistema !== "asl");
  if (s.sistema !== "asl" && s.sistema !== "irlp") {
    $("#sesStats").innerHTML = "";
    $("#sesList").innerHTML = `<p class="empty">En modo simulado no hay enlaces que mostrar.</p>`;
    $("#sesRedWrap").classList.add("hidden");
    return;
  }
  const loc = s.local || {};
  $("#sesSub").textContent = `Nodo ${s.nodo}${loc.indicativo ? " · " + loc.indicativo : ""} — nodos conectados en este momento`;
  const estado = s.tx ? ["Transmitiendo", "tx"] : s.rx ? ["Recibiendo", "rx"] : ["En reposo", ""];
  const talking = s.enlaces.filter((e) => e.transmitiendo);
  $("#sesStats").innerHTML = s.sistema === "irlp" ? `
    <div class="stat"><div class="k">IRLP</div><div class="v sm">${s.activo ? "Conectado a " + esc(s.activo) : "Sin conexión"}</div></div>` : `
    <div class="stat"><div class="k">Enlaces directos</div><div class="v">${s.enlaces.length}</div>
      <div class="d">${s.enlaces.filter((e) => e.direccion === "IN").length} entrantes · ${s.enlaces.filter((e) => e.direccion === "OUT").length} salientes</div></div>
    <div class="stat"><div class="k">Nodos en la red</div><div class="v">${s.total_red}</div><div class="d">alcanzables a través de los enlaces</div></div>
    <div class="stat ${estado[1]}"><div class="k">Estado del nodo</div><div class="v sm">${estado[0]}</div>
      <div class="d">${talking.length ? "Habla: " + talking.map((e) => esc(e.indicativo || e.nodo)).join(", ") : "Nadie transmitiendo"}</div></div>`;
  if (!s.enlaces.length) {
    $("#sesList").innerHTML = `<p class="empty">No hay nodos conectados.</p>`;
  } else {
    $("#sesList").innerHTML = s.enlaces.map((e) => {
      const desc = [e.descripcion, e.ubicacion].filter(Boolean).join(" · ");
      const dir = e.direccion === "IN" ? "↘ Entrante" : e.direccion === "OUT" ? "↗ Saliente" : "";
      const disc = s.sistema === "asl" ? `<button class="btn sm danger-soft" data-disc="${esc(e.nodo)}" title="Desconectar">Desconectar</button>` : "";
      return `<div class="lnk ${e.modo === "monitor" ? "monitor" : ""} ${e.transmitiendo ? "keyed" : ""}">
        <div class="av">${ICON_NODE}</div>
        <div class="who"><b>${esc(e.indicativo || "Nodo " + e.nodo)}</b><span class="num">${esc(e.nodo)}</span>
          <small>${esc(desc || e.ip || "")}</small></div>
        <div class="tags">
          ${e.transmitiendo ? '<span class="chip ok talk">Hablando</span>' : ""}
          ${e.modo ? `<span class="chip ${e.modo === "monitor" ? "warn" : ""}">${esc(e.modo[0].toUpperCase() + e.modo.slice(1))}</span>` : ""}
          ${dir ? `<span class="chip">${dir}</span>` : ""}
          ${e.estado && e.estado !== "ESTABLISHED" ? `<span class="chip warn">${esc(e.estado)}</span>` : ""}
        </div>
        <div class="row gap"><div class="time">${e.segundos != null ? `<span data-secs="${e.segundos}">${fmtUp(e.segundos)}</span>` : ""}<small>${esc(e.ip || "")}</small></div>${disc}</div>
      </div>`;
    }).join("");
  }
  const red = s.red || [];
  $("#sesRedWrap").classList.toggle("hidden", !red.length);
  $("#sesRedTitle").textContent = `Red completa · ${red.length} nodos más`;
  $("#sesRed").innerHTML = red.map((r) => `<span class="nchip" title="${esc([r.descripcion, r.ubicacion].filter(Boolean).join(" · "))}">
    <b>${esc(r.nodo)}</b><small>${esc(r.indicativo || "—")}</small></span>`).join("");
}
$("#sesNodo").onchange = (e) => { S.sesNodo = e.target.value; loadSesiones(); };
$("#btnSesReload").onclick = () => loadSesiones();
$("#sesList").onclick = async (e) => {
  const b = e.target.closest("[data-disc]"); if (!b) return;
  const n = b.dataset.disc;
  if (!(await confirmBox(`¿Desconectar el nodo ${n}? Dejará de oír y de mandar audio por este enlace.`, "Desconectar"))) return;
  try {
    await run(() => api("api/sesiones/desconectar", { method: "POST", json: { destino: n, nodo: S.ses.nodo } }), "Desconectando " + n);
    setTimeout(loadSesiones, 1500);
  } catch {}
};
$("#sesConnect").onsubmit = async (e) => {
  e.preventDefault();
  const f = e.target, n = f.destino.value.trim();
  const b = $("button", f); busy(b, true, "Conectando…");
  try {
    await run(() => api("api/sesiones/conectar", { method: "POST", json: { destino: n, modo: f.modo.value, nodo: S.ses && S.ses.nodo } }), "Conectando " + n);
    f.destino.value = "";
    setTimeout(loadSesiones, 2500);
  } catch {} finally { busy(b, false); }
};

/* ── Usuarios, roles y sesiones ─────────────────────────────────────────────── */
const ROL_TXT = { admin: "Administrador", operador: "Operador", lectura: "Solo lectura" };
const isAdmin = () => S.me && S.me.rol === "admin";
const initials = (u) => ((u.nombre || u.usuario || "?").trim().split(/\s+/).map((w) => w[0]).join("").slice(0, 2) || "?").toUpperCase();
function applyRole() {
  const u = S.me || {};
  document.body.classList.remove("rol-admin", "rol-operador", "rol-lectura");
  if (u.rol) document.body.classList.add("rol-" + u.rol);
  $("#userAvatar").textContent = initials(u);
  $("#userName").textContent = u.nombre || u.usuario || "";
  $("#userRole").textContent = (u.usuario ? u.usuario + " · " : "") + (ROL_TXT[u.rol] || "");
}
async function logoutNow() {
  await api("api/logout", { method: "POST" }).catch(() => {});
  S.me = null; showLogin();
}
$("#btnSideLogout").onclick = logoutNow;
$("#btnLogout").onclick = logoutNow;

function uaShort(ua) {
  ua = ua || "";
  const b = /Edg\//.test(ua) ? "Edge" : /OPR\//.test(ua) ? "Opera" : /Firefox\//.test(ua) ? "Firefox"
    : /Chrome\//.test(ua) ? "Chrome" : /Safari\//.test(ua) ? "Safari" : /curl|python/i.test(ua) ? "Programa" : "Navegador";
  const o = /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iPhone/iPad" : /Windows/.test(ua) ? "Windows"
    : /Mac OS X/.test(ua) ? "Mac" : /Linux/.test(ua) ? "Linux" : "";
  return o ? `${b} en ${o}` : b;
}
function ago(ts) {
  const s = Math.max(0, Math.round((Date.now() + (S.skew || 0)) / 1000 - ts));
  if (s < 90) return "ahora";
  if (s < 3600) return `hace ${Math.round(s / 60)} min`;
  if (s < 86400) return `hace ${Math.round(s / 3600)} h`;
  return `hace ${Math.round(s / 86400)} d`;
}
function sessionRows(list, mine, showUser) {
  if (!list.length) return '<p class="muted">No hay sesiones abiertas.</p>';
  return list.map((s) => `<div class="srow">
      <div class="sico"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg></div>
      <div class="sinfo"><b>${esc(uaShort(s.agente))}</b>${s.id === mine ? ' <span class="chip ok">Esta sesión</span>' : ""}
        <small>${showUser ? `<b>${esc(s.nombre || s.usuario)}</b> (${esc(s.usuario)}) · ` : ""}${esc(s.ip || "IP desconocida")} · activa ${ago(s.ultima)} · entró ${ago(s.creada)}</small></div>
      ${s.id === mine ? "" : `<button type="button" class="btn sm danger-soft" data-close-ses="${s.id}">Cerrar</button>`}
    </div>`).join("");
}
$("#meLang").onchange = async (e) => {
  const l = e.target.value;
  try { await api("api/mi-idioma", { method: "PUT", json: { idioma: l } }); window.hamnaSetLang(l); }
  catch (err) { toast(err.message, true); }
};
async function loadMyAccount() {
  const u = S.me || {};
  $("#meLang").value = window.HAMNA_LANG;
  $("#meAvatar").textContent = initials(u);
  $("#meName").textContent = u.nombre || u.usuario || "";
  $("#meRole").textContent = `${u.usuario || ""} · ${ROL_TXT[u.rol] || ""}`;
  try {
    const r = await api("api/mis-sesiones");
    $("#mySessions").innerHTML = sessionRows(r.sesiones, r.mi_sesion, false);
  } catch (e) { $("#mySessions").innerHTML = `<p class="muted">${esc(e.message)}</p>`; }
}
async function loadUsers() {
  let r;
  try { r = await api("api/usuarios"); } catch (e) { $("#userList").innerHTML = `<p class="muted">${esc(e.message)}</p>`; return; }
  S.users = r.usuarios;
  $("#userList").innerHTML = r.usuarios.map((u) => `<div class="urow ${u.activo ? "" : "off"}">
      <div class="avatar">${esc(initials(u))}</div>
      <div class="uinfo"><b>${esc(u.nombre || u.usuario)}</b>${u.id === r.yo ? ' <span class="chip ok">Tú</span>' : ""}
        <small>${esc(u.usuario)} · ${u.ultimo_acceso ? "último acceso " + esc(u.ultimo_acceso.slice(0, 16)) : "nunca ha entrado"}${u.sesiones ? ` · ${u.sesiones} sesión${u.sesiones > 1 ? "es" : ""} abierta${u.sesiones > 1 ? "s" : ""}` : ""}</small></div>
      <span class="chip rol-${u.rol}">${esc(u.rol_nombre)}</span>
      ${u.activo ? "" : '<span class="chip warn">Desactivado</span>'}
      <div class="mini"><button type="button" class="btn" data-uedit="${u.id}" title="Editar">✎</button>
        ${u.id === r.yo ? "" : `<button type="button" class="btn" data-udel="${u.id}" title="Borrar">🗑</button>`}</div>
    </div>`).join("");
  $("#allSessions").innerHTML = sessionRows(r.sesiones, r.mi_sesion, true);
  const lk = r.bloqueos || [];
  $("#lockBox").classList.toggle("hidden", !lk.length);
  $("#lockBox").innerHTML = lk.length ? `<div class="tl-warn row gap wrap" style="justify-content:space-between;margin-top:14px">
      <span>🔒 Bloqueados por intentos fallidos: ${lk.map((l) => esc(l.clave.replace("|", " desde ")) + ` (${Math.ceil(l.segundos / 60)} min)`).join(", ")}</span>
      <button type="button" class="btn sm" id="btnUnlock">Desbloquear</button></div>` : "";
}
function userForm(u) {
  const isNew = !u;
  u = u || { usuario: "", nombre: "", rol: "operador", activo: 1 };
  openModal(isNew ? "Nuevo usuario" : "Editar usuario", `<form id="ufForm" autocomplete="off">
      <div class="grid2">
        <label>Usuario<input name="usuario" value="${esc(u.usuario)}" ${isNew ? "required" : "disabled"} pattern="[A-Za-z0-9._\\-]{2,32}" autocapitalize="off" spellcheck="false">
          <small>Para entrar. Letras, números, punto o guion.</small></label>
        <label>Nombre<input name="nombre" value="${esc(u.nombre || "")}" placeholder="Pedro · XE2ABC"></label>
      </div>
      <label>Rol<select name="rol">${Object.entries(ROL_TXT).map(([k, v]) => `<option value="${k}" ${u.rol === k ? "selected" : ""}>${v}</option>`).join("")}</select></label>
      <label>${isNew ? "Contraseña" : "Contraseña nueva"}<input name="password" type="password" autocomplete="new-password" minlength="8" ${isNew ? "required" : ""} placeholder="${isNew ? "" : "Déjala vacía para no cambiarla"}">
        <small>Al menos 8 caracteres.${isNew ? "" : " Si la cambias, se cierran sus sesiones."}</small></label>
      ${isNew ? "" : `<label class="check"><input type="checkbox" name="activo" ${u.activo ? "checked" : ""}> Activo (si lo desactivas, sale de inmediato y no puede entrar)</label>`}
      <div class="modal-actions"><button type="button" class="btn" onclick="closeModal()">Cancelar</button>
        <button class="btn primary">${isNew ? "Crear usuario" : "Guardar"}</button></div>
    </form>`);
  $("#ufForm").onsubmit = async (e) => {
    e.preventDefault();
    const f = e.target, body = { nombre: f.nombre.value, rol: f.rol.value };
    if (f.password.value) body.password = f.password.value;
    try {
      if (isNew) { body.usuario = f.usuario.value.trim(); await api("api/usuarios", { method: "POST", json: body }); }
      else { body.activo = f.activo.checked; await api("api/usuarios/" + u.id, { method: "PUT", json: body }); }
      closeModal(); toast(isNew ? "Usuario creado" : "Usuario guardado"); loadUsers();
    } catch (err) { toast(err.message, true); }
  };
}
$("#btnUserNew").onclick = () => userForm(null);
$("#userList").onclick = async (e) => {
  const ed = e.target.closest("[data-uedit]"), del = e.target.closest("[data-udel]");
  if (ed) return userForm(S.users.find((u) => u.id === +ed.dataset.uedit));
  if (del) {
    const u = S.users.find((x) => x.id === +del.dataset.udel);
    if (!(await confirmBox(`¿Borrar el usuario «${u.usuario}»? Se cierran sus sesiones. Si solo quieres quitarle el acceso por un tiempo, mejor desactívalo.`, "Borrar"))) return;
    try { await run(() => api("api/usuarios/" + u.id, { method: "DELETE" }), "Usuario borrado"); loadUsers(); } catch {}
  }
};
$("#lockBox").onclick = async (e) => {
  if (!e.target.closest("#btnUnlock")) return;
  try { await run(() => api("api/usuarios/desbloquear", { method: "POST" }), "Desbloqueado"); loadUsers(); } catch {}
};
document.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-close-ses]"); if (!b) return;
  try {
    await run(() => api("api/mis-sesiones/" + b.dataset.closeSes, { method: "DELETE" }), "Sesión cerrada");
    if (S.setSec === "usuarios") loadUsers(); else loadMyAccount();
  } catch {}
});
$("#btnCloseOthers").onclick = async () => {
  if (!(await confirmBox("¿Cerrar todas tus sesiones en otros equipos?", "Cerrar las demás"))) return;
  try { await run(() => api("api/mis-sesiones/otras", { method: "POST" }), "Listo: solo queda esta sesión"); loadMyAccount(); } catch {}
};

/* ── Arranque ────────────────────────────────────────────────────────────── */
(async () => {
  try {
    const me = await (await fetch("api/me", { credentials: "same-origin" })).json();
    if (me.station) {
      document.title = "HAMNA Web · " + me.station;
      $("#loginStation").textContent = me.station; $("#loginStation").classList.remove("hidden");
    }
    applyLogo(me.logo);
    if (me.version) $("#loginVer").textContent = "HAMNA Web v" + me.version;
    me.auth ? start() : showLogin();
  } catch { showLogin(); }
})();
