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

/* ── API ─────────────────────────────────────────────────────────────────── */
async function api(path, { method = "GET", json, form } = {}) {
  const opt = { method, headers: { "X-HAMNA": "1" }, credentials: "same-origin" };
  if (json !== undefined) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(json); }
  if (form) opt.body = form;
  const r = await fetch(path, opt);
  if (r.status === 401 && path !== "/api/login") { showLogin(); throw new Error("Inicia sesión"); }
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
  clearInterval(S.poll); S.poll = null;
  setTimeout(() => $("#loginPw").focus(), 50);
}
$("#loginForm").onsubmit = async (e) => {
  e.preventDefault();
  $("#loginErr").textContent = "";
  const b = $("#loginForm button"); busy(b, true, "Entrando…");
  try { await api("/api/login", { method: "POST", json: { password: $("#loginPw").value } }); $("#loginPw").value = ""; start(); }
  catch (err) { $("#loginErr").textContent = err.message; }
  finally { busy(b, false); }
};

async function start() {
  $("#login").classList.add("hidden"); $("#app").classList.remove("hidden");
  try { S.cfg = await api("/api/ajustes"); } catch { return; }
  updateNodeLabel();
  await poll();
  if (!S.poll) S.poll = setInterval(poll, 1000);
  showTab(localStorage.getItem("hamna.tab") || "prog");
}

/* ── Pestañas ────────────────────────────────────────────────────────────── */
$$("#tabs button").forEach((b) => (b.onclick = () => showTab(b.dataset.tab)));
function showTab(t) {
  if (!["prog", "eventos", "secciones", "ajustes"].includes(t)) t = "prog";
  S.tab = t;
  try { localStorage.setItem("hamna.tab", t); } catch {}
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === t));
  $$(".view").forEach((v) => v.classList.toggle("hidden", v.id !== "view-" + t));
  ({ prog: loadProg, eventos: loadEventos, secciones: loadSecciones, ajustes: loadAjustes })[t]();
}

function updateNodeLabel() {
  const c = S.cfg || {};
  const be = c.backend === "auto" ? "" : (c.backend || "").toUpperCase();
  $("#nodeLabel").textContent = [c.station_name, c.node ? `Nodo ${c.node}` : "", be].filter(Boolean).join(" · ");
}

/* ── Estado al aire (cada segundo) ───────────────────────────────────────── */
async function poll() {
  let s;
  try { s = await api("/api/status"); } catch { return; }
  S.status = s;
  $("#clockLocal").textContent = s.now.slice(11);
  $("#clockUtc").textContent = "UTC " + s.utc;
  const live = s.on_air;
  $("#onair").classList.toggle("live", live && s.state === "tx");
  $("#brandDot").classList.toggle("live", live && s.state === "tx");
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
  $("#airSecTime").textContent = live && sec ? `${fmt(s.sec_pos)} / ${fmt(sec.duracion)}` : "";
  $("#airTotalTime").textContent = live ? `Total ${fmt(s.elapsed)} / ${fmt(s.total)}` : "";
  $("#ctlPause").classList.toggle("hidden", s.state === "manual_pause");
  $("#ctlResume").classList.toggle("hidden", s.state !== "manual_pause");
  $("#ctlPause").disabled = !(live && s.state === "tx");
  $("#ctlSkip").disabled = !(live && (s.state === "paused" || s.state === "gap"));
  $("#ctlNext").disabled = !live || s.origen === "prueba";
  $("#ctlStop").disabled = !live;
  $("#airLog").innerHTML = s.log.map((l) => `<div class="${l.level}">${esc(l.t)}  ${esc(l.msg)}</div>`).join("");
  // Resaltar la sección al aire en el detalle del evento
  $$("#eventoDetail .sec-row").forEach((r) =>
    r.classList.toggle("on", live && s.evento_id === S.evSel && +r.dataset.idx === s.cur_sec));
  if (S.wasLive !== live) { S.wasLive = live; if (S.tab === "prog") loadProg(); }
  tickProg();
}
const txCmd = (c) => run(() => api("/api/tx/" + c, { method: "POST" }));
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
  await run(() => api("/api/tx/start", { method: "POST", json: { evento_id: eid } }), "Iniciando transmisión");
}

/* ── Programación ────────────────────────────────────────────────────────── */
async function loadProg() {
  const [prog, ev] = await Promise.all([api("/api/programacion"), api("/api/eventos")]);
  S.prog = prog; S.eventos = ev.eventos; S.tipos = ev.tipos;
  S.progLoaded = Date.now();
  renderProg();
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
  el.innerHTML = S.prog.map((p) => {
    const isToday = p.proxima && p.proxima.startsWith(today);
    return `<div class="card ${!p.activo ? "off" : ""} ${live === p.evento_id ? "live" : isToday ? "today" : ""}">
      <div class="row" style="justify-content:space-between"><span class="when">${esc(p.hora)}</span>
        ${live === p.evento_id ? '<span class="chip live">AL AIRE</span>' : isToday ? '<span class="chip ok">HOY</span>' : ""}</div>
      <h3>${esc(p.evento_nombre)}</h3>
      <div class="meta">${esc(recText(p))}${p.evento_tipo ? " · " + esc(p.evento_tipo) : ""}</div>
      <div class="meta" data-left="${p.faltan_s ?? ""}">${p.activo ? (p.proxima ? "Próxima: " + esc(p.proxima) + " · en <b class='left'>" + fmtLeft(p.faltan_s) + "</b>" : "Sin próximas fechas") : "Desactivada"}</div>
      <div class="actions">
        <button class="btn sm primary" data-act="tx" data-id="${p.evento_id}" data-n="${esc(p.evento_nombre)}">📡 Transmitir ahora</button>
        <button class="btn sm" data-act="edit" data-id="${p.id}">Editar</button>
        <button class="btn sm" data-act="toggle" data-id="${p.id}">${p.activo ? "Desactivar" : "Activar"}</button>
        <button class="btn sm ghost" data-act="del" data-id="${p.id}">Borrar</button>
      </div></div>`;
  }).join("");
  const nxt = S.prog.find((p) => p.activo && p.faltan_s != null);
  const nc = $("#nextCard");
  if (nxt) {
    nc.classList.remove("hidden");
    nc.innerHTML = `<div><div class="muted">Próximo evento</div><h2>${esc(nxt.evento_nombre)}</h2>
      <div class="muted">${esc(nxt.proxima)} · ${esc(recText(nxt))}</div></div>
      <div class="big" id="nextLeft" data-left="${nxt.faltan_s}"></div>`;
  } else nc.classList.add("hidden");
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
    await run(() => api("/api/programacion/" + id, { method: "PUT", json: { ...p, activo: !p.activo } }));
    return loadProg();
  }
  if (b.dataset.act === "del" && (await confirmBox(`¿Borrar la programación de «${p.evento_nombre}» a las ${p.hora}?`, "Borrar"))) {
    await run(() => api("/api/programacion/" + id, { method: "DELETE" }), "Borrada"); loadProg();
  }
};
$("#btnNewProg").onclick = async () => {
  if (!S.eventos.length) await loadProg();
  if (!S.eventos.length) return toast("Primero crea un evento en la pestaña Eventos", true);
  progForm(null);
};
function progForm(p) {
  const today = (S.status ? S.status.now : new Date().toISOString()).slice(0, 10);
  p = p || { evento_id: S.evSel || S.eventos[0].id, fecha: today, hora: "20:00", recurrencia: "semanal", activo: 1 };
  openModal(p.id ? "Editar programación" : "Programar evento", `
    <form id="pf">
      <label>Evento<select name="evento_id">${S.eventos.map((e) =>
        `<option value="${e.id}" ${e.id === p.evento_id ? "selected" : ""}>${esc(e.nombre)}</option>`).join("")}</select></label>
      <div class="grid2">
        <label>Fecha (o primera fecha)<input type="date" name="fecha" value="${esc(p.fecha)}" required></label>
        <label>Hora del nodo<input type="time" name="hora" value="${esc(p.hora)}" required></label>
      </div>
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
  f.oninput = hint; hint();
  f.onsubmit = async (e) => {
    e.preventDefault();
    const data = { evento_id: +f.evento_id.value, fecha: f.fecha.value, hora: f.hora.value,
      recurrencia: f.recurrencia.value, activo: f.activo.checked };
    await run(() => api("/api/programacion" + (p.id ? "/" + p.id : ""), { method: p.id ? "PUT" : "POST", json: data }), "Guardado");
    closeModal(); loadProg();
  };
}

/* ── Eventos ─────────────────────────────────────────────────────────────── */
async function loadEventos() {
  const ev = await api("/api/eventos");
  S.eventos = ev.eventos; S.tipos = ev.tipos;
  const el = $("#eventosList");
  el.innerHTML = S.eventos.length ? S.eventos.map((e) => `
    <button class="list-item ${e.id === S.evSel ? "active" : ""}" data-id="${e.id}">
      <b>${esc(e.nombre)}</b>${e.numero ? ` <span class="chip">#${e.numero}</span>` : ""}
      <small>${e.num_secciones} secciones · ${fmt(e.duracion_total)}${e.tipo ? " · " + esc(e.tipo) : ""}</small>
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
  const ev = await api("/api/eventos/" + id);
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
          <button class="btn" data-mv="-1" ${i === 0 ? "disabled" : ""} title="Subir">↑</button>
          <button class="btn" data-mv="1" ${i === secs.length - 1 ? "disabled" : ""} title="Bajar">↓</button>
          <button class="btn" data-rm title="Quitar del evento">✕</button>
        </span>
      </div>`).join("") : `<p class="empty">Este evento no tiene secciones.</p>`}</div>
    <div class="row gap" style="margin-top:12px"><button class="btn" id="evAdd">+ Agregar secciones</button></div>`;
  $("#evTx").onclick = () => txStart(ev.id, ev.nombre);
  $("#evEdit").onclick = () => eventoForm(ev);
  $("#evDel").onclick = async () => {
    if (!(await confirmBox(`¿Borrar el evento «${ev.nombre}» y su programación? Las secciones se conservan en la biblioteca.`, "Borrar"))) return;
    await run(() => api("/api/eventos/" + ev.id, { method: "DELETE" }), "Evento borrado");
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
      await run(() => api(`/api/eventos/${ev.id}/orden`, { method: "PUT", json: { ids } }));
      loadEvento(ev.id);
    } else if (b && "rm" in b.dataset) {
      await run(() => api(`/api/eventos/${ev.id}/secciones/${sid}`, { method: "DELETE" }));
      loadEventos();
    }
  };
  $("#evSecs").onchange = async (e) => {
    if (!("cont" in e.target.dataset)) return;
    const sid = +e.target.closest(".sec-row").dataset.id;
    await run(() => api(`/api/eventos/${ev.id}/secciones/${sid}/contabilizable`, { method: "PUT", json: { value: e.target.checked } }));
    loadEvento(ev.id);
  };
}
async function addSecciones(ev) {
  const all = await api("/api/secciones");
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
    await run(() => api(`/api/eventos/${ev.id}/secciones`, { method: "POST", json: { ids } }), "Agregadas");
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
    const r = await run(() => api("/api/eventos" + (ev.id ? "/" + ev.id : ""), { method: ev.id ? "PUT" : "POST", json: data }), "Guardado");
    if (!ev.id) S.evSel = r.id;
    closeModal(); loadEventos();
  };
}

/* ── Secciones ───────────────────────────────────────────────────────────── */
async function loadSecciones() {
  S.secciones = await api("/api/secciones");
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
        <button class="btn" data-act="play" title="Escuchar aquí" ${s.tiene_audio ? "" : "disabled"}>▶</button>
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
    openModal(s.nombre, `<audio controls autoplay src="/api/secciones/${s.id}/audio" style="width:100%"></audio>
      ${s.tipo === "TTS" ? `<p class="muted">${esc(s.texto_tts)}</p>` : ""}`);
  } else if (b.dataset.act === "air") {
    if (await confirmBox(`¿Transmitir «${s.nombre}» (${fmt(s.duracion)}) por el nodo ahora?`, "📡 Transmitir"))
      run(() => api(`/api/secciones/${s.id}/aire`, { method: "POST" }), "Transmitiendo…");
  } else if (b.dataset.act === "edit") seccionForm(s);
  else if (b.dataset.act === "del") {
    const warn = s.usos ? ` Se quitará de ${s.usos} evento(s).` : "";
    if (await confirmBox(`¿Borrar «${s.nombre}»?${warn}`, "Borrar")) {
      await run(() => api("/api/secciones/" + s.id, { method: "DELETE" }), "Borrada"); loadSecciones();
    }
  }
};
async function getInfo() { if (!S.info) S.info = await api("/api/info"); return S.info; }

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
      const r = await api("/api/tts/preview", { method: "POST", json: { texto: f.texto_tts.value, titulo: f.titulo.value || f.nombre.value, descripcion: f.descripcion.value } });
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
    upload(isNew ? "/api/secciones" : "/api/secciones/" + s.id, fd, $("#sfSave"), $("#sfProg"))
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
  S.setSec = k;
  $$("#setNav button").forEach((b) => b.classList.toggle("active", b.dataset.set === k));
  $$("#setForm fieldset").forEach((f) => f.classList.toggle("hidden", f.dataset.set !== k));
  $("#saveBar").classList.toggle("hidden", k === "seguridad" || k === "sistema");
  if (k === "sistema") loadSistema();
}
async function loadAjustes() {
  S.cfg = await api("/api/ajustes");
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
  const r = await run(() => api("/api/ajustes", { method: "PUT", json: data }), "Ajustes guardados");
  S.cfg = r.ajustes; S.info = null; updateNodeLabel(); loadAjustes();
};
$("#btnCompactar").onclick = async () => {
  if (!(await confirmBox("Se van a convertir todas las secciones al formato del aire y se borrarán los audios originales. Esto no se puede deshacer.", "Sí, convertir y borrar"))) return;
  const b = $("#btnCompactar"); busy(b, true, "Convirtiendo…");
  try {
    const r = await api("/api/secciones/compactar", { method: "POST" });
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
      <div>${S.cfg[key] ? `<audio controls preload="none" src="/api/ajustes/sonido/${k}?t=${encodeURIComponent(S.cfg[key])}"></audio>` : '<span class="muted">Sin audio</span>'}</div>
      <div class="row gap"><label class="btn sm" style="margin:0">Subir<input type="file" accept="audio/*" hidden></label>
        ${S.cfg[key] ? '<button type="button" class="btn sm ghost" data-del>Quitar</button>' : ""}</div>
    </div>`).join("");
}
$("#pauseSounds").onchange = async (e) => {
  if (e.target.type !== "file" || !e.target.files[0]) return;
  const k = e.target.closest(".psound").dataset.k, fd = new FormData();
  fd.append("archivo", e.target.files[0]);
  try { await upload("/api/ajustes/sonido/" + k, fd); toast("Audio guardado"); S.cfg = await api("/api/ajustes"); renderPauseSounds(); }
  catch (err) { toast(err.message, true); }
};
$("#pauseSounds").onclick = async (e) => {
  if (!e.target.closest("[data-del]")) return;
  const k = e.target.closest(".psound").dataset.k;
  await run(() => api("/api/ajustes/sonido/" + k, { method: "DELETE" }), "Quitado");
  S.cfg = await api("/api/ajustes"); renderPauseSounds();
};
$("#btnTestNode").onclick = async () => {
  const b = $("#btnTestNode"); busy(b, true, "Probando…");
  try { const r = await api("/api/prueba/nodo", { method: "POST" });
    $("#testNodeMsg").textContent = (r.ok ? "✅ " : "❌ ") + r.mensaje; }
  catch (e) { $("#testNodeMsg").textContent = "❌ " + e.message; } finally { busy(b, false); }
};
$("#btnTestAir").onclick = async () => {
  if (!(await confirmBox("Se va a activar el transmisor del nodo con un mensaje de prueba. ¿Continuar?", "📡 Transmitir"))) return;
  const b = $("#btnTestAir"); busy(b, true, "Generando…");
  try { await run(() => api("/api/prueba/aire", { method: "POST", json: { texto: $("#testAirText").value } }), "Prueba al aire"); }
  catch {} finally { busy(b, false); }
};
$("#btnTtsTest").onclick = async () => {
  const b = $("#btnTtsTest"); busy(b, true, "Generando…");
  try {
    await api("/api/ajustes", { method: "PUT", json: collectVoice() });
    const r = await api("/api/tts/preview", { method: "POST", json: { texto: $("#ttsTestText").value } });
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
    const r = await api("/api/azure/voces", { method: "POST", json: { azure_key: f.azure_key.value, azure_region: f.azure_region.value } });
    $("#azureVoices").innerHTML = r.voces.map((v) => `<option value="${esc(v.name)}">${esc(v.display)} · ${esc(v.locale)} · ${esc(v.gender)}</option>`).join("");
    toast(`${r.voces.length} voces en español`);
  } catch (e) { toast(e.message, true); } finally { busy(b, false); }
};
$("#btnPw").onclick = async () => {
  await run(() => api("/api/ajustes/password", { method: "POST", json: { actual: $("#pwOld").value, nueva: $("#pwNew").value } }), "Contraseña cambiada");
  $("#pwOld").value = $("#pwNew").value = "";
};
$("#btnLogout").onclick = async () => { await api("/api/logout", { method: "POST" }).catch(() => {}); showLogin(); };
async function loadSistema() {
  S.info = null;
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

/* ── Arranque ────────────────────────────────────────────────────────────── */
(async () => {
  try {
    const me = await (await fetch("/api/me", { credentials: "same-origin" })).json();
    if (me.station) document.title = "HAMNA Web · " + me.station;
    me.auth ? start() : showLogin();
  } catch { showLogin(); }
})();
