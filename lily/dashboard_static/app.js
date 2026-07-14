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
  ["status", "system", "habits", "projects", "facts"].forEach((name) => {
    const el = $(`card-${name}`);
    if (el) el.hidden = !cards[name];
  });
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

function addMessage(role, content) {
  const messages = $("messages");
  const empty = $("empty-chat");
  if (empty) empty.remove();
  const article = document.createElement("article");
  article.className = `message ${role}`;
  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : "Lily";
  const text = document.createElement("div");
  text.className = "message-text";
  text.textContent = content || "…";
  article.append(label, text);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
}

async function loadHistory() {
  try {
    const res = await fetch("/api/chat/history?limit=40");
    if (!res.ok) return;
    const data = await res.json();
    (data.messages || []).forEach((message) => addMessage(message.role, message.content));
  } catch (e) { /* The cards already show connection state. */ }
}

async function sendMessage(message) {
  const input = $("chat-input");
  const send = $("send");
  const status = $("chat-status");
  addMessage("user", message);
  input.value = "";
  input.disabled = true;
  send.disabled = true;
  status.textContent = "Lily is thinking locally…";
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Lily could not reply.");
    addMessage("assistant", data.reply);
    status.textContent = "Local only · your data stays on this machine";
  } catch (error) {
    addMessage("error", error.message || "Lily could not reply.");
    status.textContent = "Check that Ollama is running and the configured model is installed.";
  } finally {
    input.disabled = false;
    send.disabled = false;
    input.focus();
  }
}

$("chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const message = $("chat-input").value.trim();
  if (message) sendMessage(message);
});

$("chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("chat-form").requestSubmit();
  }
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.dataset.prompt));
});

$("clear-view").addEventListener("click", () => {
  $("messages").replaceChildren();
  addMessage("assistant", "Fresh view. Your saved memory is unchanged.");
});

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
loadHistory();
setInterval(poll, 5000);
