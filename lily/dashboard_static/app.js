// SentinelOS dashboard - fetch card data, render OS-layer cards, and chat locally.
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const attr = (s) => esc(s).replace(/"/g, "&quot;");
let currentGoal = null;

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

function pill(text, cls = "") {
  return `<span class="pill ${cls}">${esc(text)}</span>`;
}

function list(items, emptyText) {
  if (!items || !items.length) return `<span class="muted">${esc(emptyText)}</span>`;
  return `<ul>${items.join("")}</ul>`;
}

function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}

function renderStatus(d) {
  if (!d) return;
  body("card-status", row("Mode", d.mode) + row("Agents", d.agents) + row("Tools", d.tools));
  setText("summary-agents", String(d.agents || 0));
}

function renderProfile(d) {
  if (!d) return;
  const current = d.current || "passive";
  const cards = (d.profiles || []).map((profile) => {
    const active = profile.key === current ? " active" : "";
    const enabled = (profile.enabled || []).map((item) => pill(item)).join("");
    return `<article class="profile-row${active}">
      <div><strong>${esc(profile.name)}</strong><p>${esc(profile.summary)}</p></div>
      <div class="pill-row">${enabled}</div>
    </article>`;
  }).join("");
  body("card-profile", cards || `<span class="muted">no profiles</span>`);
  setText("summary-profile", current.replace("_", " "));
}

function renderGoal(d) {
  if (!d) return;
  currentGoal = d.id ? d : null;
  const queue = (d.queue || []).filter((goal) => !["completed", "cancelled"].includes(goal.status));
  const queueHtml = queue.length ? `
    <div class="goal-queue">
      <span class="section-label">Goal queue</span>
      ${queue.slice(0, 4).map((goal) => `
        <button type="button" class="queue-item" data-goal-activate="${goal.id}">
          <span><strong>${esc(goal.title)}</strong><small>${esc(goal.status)} · P${goal.priority}</small></span>
          <b>${goal.progress}%</b>
        </button>`).join("")}
    </div>` : "";

  if (!d.id) {
    const legacy = d.goal ? `<p>Legacy goal detected: <strong>${esc(d.goal)}</strong></p>` :
      "<p>Create a goal to give Sentinel a durable outcome, task list, and next action.</p>";
    body("card-goal", `
      <div class="goal-empty">${legacy}
        <button type="button" class="primary-action" data-open-goal>Create goal</button>
      </div>${queueHtml}`);
    setText("summary-goal", d.goal || "No active goal");
    return;
  }

  const progress = Number(d.progress) || 0;
  const tasks = (d.tasks || []).map((task) => `
    <label class="goal-task ${task.status === "done" ? "done" : ""}">
      <input type="checkbox" data-task-toggle data-goal-id="${d.id}" data-task-id="${task.id}"
        ${task.status === "done" ? "checked" : ""} />
      <span>${esc(task.title)}</span>
      <small>${esc(task.status)}</small>
    </label>`).join("");
  const pauseStatus = d.status === "paused" ? "active" : "paused";
  const pauseLabel = d.status === "paused" ? "Resume" : "Pause";
  const blockStatus = d.status === "blocked" ? "active" : "blocked";
  const blockLabel = d.status === "blocked" ? "Unblock" : "Block";

  body("card-goal", `
    <div class="goal-heading">
      <div><span class="status-label ${esc(d.status)}">${esc(d.status)}</span>
        <div class="goal-title">${esc(d.goal)}</div></div>
      <button type="button" class="quiet compact-button" data-open-goal="edit">Edit</button>
    </div>
    ${d.outcome ? `<p class="goal-outcome">${esc(d.outcome)}</p>` : ""}
    <div class="progress-head"><span>${d.task_summary.done}/${d.task_summary.total} tasks</span><strong>${progress}%</strong></div>
    ${meter(progress)}
    ${row("Next action", d.next_action || "not set")}
    ${d.blocker ? `<div class="blocker"><strong>Blocker</strong><span>${esc(d.blocker)}</span></div>` : ""}
    <div class="goal-controls">
      <button type="button" class="primary-action" data-goal-plan>Generate tasks</button>
      <button type="button" class="quiet" data-goal-status="${pauseStatus}">${pauseLabel}</button>
      <button type="button" class="quiet" data-goal-status="${blockStatus}">${blockLabel}</button>
      <button type="button" class="quiet danger-action" data-goal-status="completed">Complete</button>
    </div>
    <div class="goal-tasks"><span class="section-label">Tasks</span>${tasks || `<span class="muted">No tasks yet.</span>`}</div>
    <form id="goal-task-form" class="inline-form" data-goal-id="${d.id}">
      <input name="title" maxlength="240" required placeholder="Add the next concrete task" />
      <button type="submit" class="primary-action">Add</button>
    </form>
    ${queueHtml}
  `);
  setText("summary-goal", d.goal);
}

function renderSystem(d) {
  if (!d) return;
  let h = row("CPU", `${d.cpu_percent}% · ${d.cpu_threads} threads`) + meter(d.cpu_percent);
  h += row("RAM", `${d.ram_used_gb}/${d.ram_total_gb} GB`) + meter(d.ram_percent);
  h += row("Disk", `${d.disk_used_gb}/${d.disk_total_gb} GB`) + meter(d.disk_percent);
  if (d.battery_percent != null) {
    h += row("Battery", `${d.battery_percent}% ${d.battery_charging ? "charging" : ""}`);
  }
  body("card-system", h);
}

function renderTimeline(d) {
  if (!d) return;
  const events = (d.events || []).map((event) => `
    <article class="timeline-item">
      <time>${esc(event.time)}</time>
      <div><strong>${esc(event.title)}</strong><p>${esc(event.kind)}${event.content ? ` - ${esc(event.content)}` : ""}</p></div>
    </article>
  `).join("");
  body("card-timeline", events || `<span class="muted">No timeline events yet.</span>`);
}

function renderAgents(d) {
  if (!d) return;
  const agents = (d.agents || []).slice(0, 9).map((agent) =>
    `<li><strong>${esc(agent.name)}</strong><span>${esc(agent.description)}</span></li>`);
  body("card-agents", list(agents, "no agents loaded"));
}

function renderHabits(d) {
  if (!d) return;
  const wh = d.work_hours ? `${d.work_hours[0]}:00-${d.work_hours[1]}:00` : "-";
  let h = row("Work hours", wh) + row("Busiest day", d.busiest_weekday || "-");
  if (d.summary) h += `<div class="note">${esc(d.summary)}</div>`;
  body("card-habits", h);
}

function renderProjects(d) {
  if (!d) return;
  const items = (d.projects || []).map((p) =>
    `<li><strong>${esc(p)}</strong>${p === d.active ? "<span>active</span>" : ""}</li>`);
  body("card-projects", list(items, "no projects"));
}

function renderFacts(d) {
  if (!d) return;
  const facts = (d.facts || []).map((f) => `<li><strong>${esc(f.kind || "fact")}</strong><span>${esc(f.content || f.fact || f)}</span></li>`);
  body("card-facts", list(facts, "no memory facts yet"));
}

function renderAll(cards) {
  if (!cards) return;
  ["status", "profile", "goal", "system", "timeline", "agents", "habits", "projects", "facts"].forEach((name) => {
    const el = $(`card-${name}`);
    if (el) el.hidden = !cards[name];
  });
  renderStatus(cards.status);
  renderProfile(cards.profile);
  renderGoal(cards.goal);
  renderSystem(cards.system);
  renderTimeline(cards.timeline);
  renderAgents(cards.agents);
  renderHabits(cards.habits);
  renderProjects(cards.projects);
  renderFacts(cards.facts);
}

function setConn(text, cls) {
  const c = $("conn");
  if (c) { c.textContent = text; c.className = "badge " + (cls || ""); }
}

async function apiJson(url, options = {}) {
  const config = { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } };
  const response = await fetch(url, config);
  let data = {};
  try { data = await response.json(); } catch (error) { /* Empty response. */ }
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status}).`);
  return data;
}

async function runGoalMutation(work, pendingText) {
  const status = $("chat-status");
  status.textContent = pendingText;
  try {
    await work();
    await poll();
    status.textContent = "Goal state saved locally.";
    return true;
  } catch (error) {
    addMessage("error", error.message || "Goal update failed.");
    status.textContent = "The goal update was not saved.";
    return false;
  }
}

function openGoalDialog(goal = null) {
  const dialog = $("goal-dialog");
  const item = goal || {};
  $("goal-dialog-title").textContent = goal ? "Edit goal" : "Create goal";
  $("goal-id").value = item.id || "";
  $("goal-title").value = item.goal || item.title || "";
  $("goal-outcome").value = item.outcome || "";
  $("goal-success").value = item.success_criteria || "";
  $("goal-next-action").value = item.next_action || "";
  $("goal-blocker").value = item.blocker || "";
  $("goal-due").value = item.due_at || "";
  $("goal-priority").value = String(item.priority || 3);
  dialog.showModal();
  $("goal-title").focus();
}

function closeGoalDialog() {
  const dialog = $("goal-dialog");
  if (dialog.open) dialog.close();
}

$("goal-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  const goalId = payload.id;
  delete payload.id;
  payload.priority = Number(payload.priority || 3);
  const ok = await runGoalMutation(
    () => apiJson(goalId ? `/api/goals/${goalId}` : "/api/goals", {
      method: goalId ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    }),
    goalId ? "Updating goal..." : "Creating goal...",
  );
  if (ok) closeGoalDialog();
});

function addMessage(role, content) {
  const messages = $("messages");
  const empty = $("empty-chat");
  if (empty) empty.remove();
  const article = document.createElement("article");
  article.className = `message ${role}`;
  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : role === "error" ? "Error" : "Lily";
  const text = document.createElement("div");
  text.className = "message-text";
  text.textContent = content || "...";
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
  status.textContent = "Lily is thinking locally...";
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Lily could not reply.");
    addMessage("assistant", data.reply);
    status.textContent = "Local only. Your data stays on this machine.";
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

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-prompt]");
  if (button) {
    sendMessage(button.dataset.prompt);
    return;
  }
  if (event.target.closest("#new-goal") || event.target.closest("[data-open-goal]")) {
    const edit = event.target.closest('[data-open-goal="edit"]');
    openGoalDialog(edit ? currentGoal : null);
    return;
  }
  if (event.target.closest("[data-close-goal]")) {
    closeGoalDialog();
    return;
  }
  const activate = event.target.closest("[data-goal-activate]");
  if (activate) {
    await runGoalMutation(
      () => apiJson(`/api/goals/${activate.dataset.goalActivate}/activate`, { method: "POST" }),
      "Switching active goal...",
    );
    return;
  }
  const planButton = event.target.closest("[data-goal-plan]");
  if (planButton && currentGoal) {
    planButton.disabled = true;
    $("chat-status").textContent = "Lily is turning the goal into concrete tasks...";
    try {
      const result = await apiJson(`/api/goals/${currentGoal.id}/plan`, { method: "POST" });
      await poll();
      const count = (result.added || []).length;
      const skipped = Number(result.skipped) || 0;
      $("chat-status").textContent = count
        ? `Added ${count} planned task${count === 1 ? "" : "s"}${skipped ? `; skipped ${skipped} duplicate${skipped === 1 ? "" : "s"}` : ""}.`
        : "The generated plan already exists in this goal.";
    } catch (error) {
      addMessage("error", error.message || "Lily could not generate tasks.");
      $("chat-status").textContent = "Check that Ollama is running and the configured model is installed.";
    } finally {
      planButton.disabled = false;
    }
    return;
  }
  const statusButton = event.target.closest("[data-goal-status]");
  if (statusButton && currentGoal) {
    const nextStatus = statusButton.dataset.goalStatus;
    const payload = { status: nextStatus };
    if (nextStatus === "blocked") {
      const blocker = window.prompt("What is blocking this goal?", currentGoal.blocker || "");
      if (blocker === null) return;
      payload.blocker = blocker.trim();
    } else if (currentGoal.status === "blocked") {
      payload.blocker = "";
    }
    if (nextStatus === "completed" && !window.confirm("Mark this goal complete?")) return;
    await runGoalMutation(
      () => apiJson(`/api/goals/${currentGoal.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
      "Updating goal status...",
    );
  }
});

document.addEventListener("change", async (event) => {
  const checkbox = event.target.closest("[data-task-toggle]");
  if (!checkbox) return;
  checkbox.disabled = true;
  await runGoalMutation(
    () => apiJson(`/api/goals/${checkbox.dataset.goalId}/tasks/${checkbox.dataset.taskId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: checkbox.checked ? "done" : "todo" }),
    }),
    "Updating task...",
  );
});

document.addEventListener("submit", async (event) => {
  const form = event.target.closest("#goal-task-form");
  if (!form) return;
  event.preventDefault();
  const title = new FormData(form).get("title").trim();
  if (!title) return;
  const ok = await runGoalMutation(
    () => apiJson(`/api/goals/${form.dataset.goalId}/tasks`, {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
    "Adding task...",
  );
  if (ok) form.reset();
});

$("clear-view").addEventListener("click", () => {
  $("messages").replaceChildren();
  addMessage("assistant", "Fresh view. Saved memory is unchanged.");
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

poll();
loadHistory();
setInterval(poll, 5000);
