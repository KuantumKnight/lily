// Lily dashboard — fetch card data and render. (E21 polls; E22 adds a websocket.)
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

function body(cardId, html) {
  const el = $(cardId);
  if (el) el.querySelector(".body").innerHTML = html;
}

function row(k, v) {
  return `<div class="row"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></div>`;
}

function meter(pct) {
  const p = Math.max(0, Math.min(100, Number(pct) || 0));
  return `<div class="meter"><span style="width:${p}%"></span></div>`;
}

function renderStatus(d) {
  if (!d) return;
  body("card-status", row("Mode", d.mode) + row("Agents", d.agents) + row("Tools", d.tools));
}

function renderSystem(d) {
  if (!d) return;
  let h = row("CPU", `${d.cpu_percent}% · ${d.cpu_threads} threads`) + meter(d.cpu_percent);
  h += row("RAM", `${d.ram_used_gb}/${d.ram_total_gb} GB`) + meter(d.ram_percent);
  h += row("Disk", `${d.disk_used_gb}/${d.disk_total_gb} GB`) + meter(d.disk_percent);
  if (d.battery_percent != null) {
    h += row("Battery", `${d.battery_percent}% ${d.battery_charging ? "(charging)" : ""}`);
  }
  body("card-system", h);
}

function renderHabits(d) {
  if (!d) return;
  const wh = d.work_hours ? `${d.work_hours[0]}:00–${d.work_hours[1]}:00` : "—";
  let h = row("Work hours", wh) + row("Busiest day", d.busiest_weekday || "—");
  if (d.summary) h += `<div class="muted" style="margin-top:8px">${esc(d.summary)}</div>`;
  body("card-habits", h);
}

function renderProjects(d) {
  if (!d) return;
  const list = (d.projects || []).map((p) =>
    `<li>${esc(p)}${p === d.active ? " <span class='muted'>(active)</span>" : ""}</li>`).join("");
  body("card-projects", list ? `<ul>${list}</ul>` : `<span class="muted">no projects</span>`);
}

function renderFacts(d) {
  if (!d) return;
  const facts = (d.facts || []).map((f) => `<li>${esc(f.content || f.fact || f)}</li>`).join("");
  body("card-facts", facts ? `<ul>${facts}</ul>` : `<span class="muted">no facts yet</span>`);
}

function renderAll(cards) {
  if (!cards) return;
  renderStatus(cards.status);
  renderSystem(cards.system);
  renderHabits(cards.habits);
  renderProjects(cards.projects);
  renderFacts(cards.facts);
}

function setConn(text, cls) {
  const c = $("conn");
  if (c) { c.textContent = text; c.className = "badge " + (cls || ""); }
}

async function poll() {
  try {
    const res = await fetch("/api/cards");
    if (!res.ok) throw new Error(res.status);
    renderAll(await res.json());
    setConn("live", "live");
  } catch (e) {
    setConn("offline", "dead");
  }
}

// E22 will replace this polling with a websocket; renderAll() is the shared sink.
poll();
setInterval(poll, 5000);
