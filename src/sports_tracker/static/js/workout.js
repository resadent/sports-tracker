// workout.js — the workout builder: sessions, sets, drop sets and supersets.
let workoutState = { selectedSessionId: null, activeGroup: null };
let exercisesCache = [];

async function renderWorkouts(app) {
  app.innerHTML = "";
  const root = document.createElement("div");

  root.innerHTML = `
    <section class="panel">
      <h1>Workouts</h1>
      <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">
        <input type="text" id="new-session-name" placeholder="Session name (e.g. Leg Day)" style="flex:1; min-width:180px; margin-top:0;">
        <button id="new-session-btn">New session</button>
        <button id="new-group-btn" class="secondary">⧉ New superset</button>
        <span class="group-badge" id="active-group-badge" hidden></span>
      </div>
      <p class="msg" id="workout-msg"></p>
    </section>

    <div id="session-list" class="session-list"></div>
    <div id="editor"></div>`;

  app.appendChild(root);

  app.querySelector("#new-session-btn").addEventListener("click", () => createSession());
  app.querySelector("#new-group-btn").addEventListener("click", () => startSuperset());

  await refreshWorkouts(root);
}

async function refreshWorkouts(root) {
  const sessions = await api("GET", "/api/v1/sessions");
  exercisesCache = await api("GET", "/api/v1/exercises");

  renderSessionList(root, sessions);

  if (!workoutState.selectedSessionId && sessions.length) {
    workoutState.selectedSessionId = sessions[0].id;
  }
  const session = sessions.find((s) => s.id === workoutState.selectedSessionId) || null;
  renderEditor(root, session);
}

function renderSessionList(root, sessions) {
  const list = root.querySelector("#session-list");
  list.innerHTML = "";
  for (const s of sessions) {
    const item = document.createElement("span");
    item.className = "session-item" + (s.id === workoutState.selectedSessionId ? " active" : "");
    item.textContent = s.name || `Session ${s.id}`;
    item.addEventListener("click", () => {
      workoutState.selectedSessionId = s.id;
      render();
    });
    list.appendChild(item);
  }
}

function renderEditor(root, session) {
  const editor = root.querySelector("#editor");
  editor.innerHTML = "";

  const badge = root.querySelector("#active-group-badge");
  if (workoutState.activeGroup) {
    badge.hidden = false;
    badge.textContent = `Superset active: ${workoutState.activeGroup.slice(0, 8)}`;
  } else {
    badge.hidden = true;
  }

  if (!session) {
    editor.innerHTML = '<div class="panel" style="color:var(--muted)">No sessions yet — create one above.</div>';
    return;
  }

  const groups = [...new Set(session.workout_sets.map((s) => s.superset_group).filter(Boolean))];

  const panel = document.createElement("div");
  panel.className = "panel";
  panel.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem;">
      <h2 style="margin:0">${session.name || `Session ${session.id}`}</h2>
      <button class="danger small" id="delete-session-btn">Delete session</button>
    </div>
    <div id="set-rows"></div>
    <div style="display:flex; gap:0.5rem; margin-top:0.75rem; align-items:center;">
      <select id="add-exercise" style="flex:1;">${exerciseOptions()}</select>
      <button id="add-set-btn">+ Add set</button>
    </div>`;

  editor.appendChild(panel);

  panel.querySelector("#delete-session-btn").addEventListener("click", () => deleteSession(session.id));
  panel.querySelector("#add-set-btn").addEventListener("click", () => addSet(session.id));

  const rows = panel.querySelector("#set-rows");
  session.workout_sets.forEach((set, index) => {
    rows.appendChild(buildSetRow(session, set, index));
  });
}

function exerciseOptions(selectedId) {
  return exercisesCache
    .map((e) => `<option value="${e.id}"${selectedId === e.id ? " selected" : ""}>${e.name}</option>`)
    .join("");
}

function groupOptions(session, groups, selectedGroup) {
  let opts = `<option value="">(none)</option>`;
  for (const g of groups) {
    opts += `<option value="${g}"${selectedGroup === g ? " selected" : ""}>${g.slice(0, 8)}</option>`;
  }
  if (workoutState.activeGroup && !groups.includes(workoutState.activeGroup)) {
    opts += `<option value="${workoutState.activeGroup}"${selectedGroup === workoutState.activeGroup ? " selected" : ""}>${workoutState.activeGroup.slice(0, 8)} (new)</option>`;
  }
  return opts;
}

function buildSetRow(session, set, index) {
  const groups = [...new Set(session.workout_sets.map((s) => s.superset_group).filter(Boolean))];
  const row = document.createElement("div");
  row.className = "set-row" + (set.superset_group ? " grouped" : "");
  row.innerHTML = `
    <span class="exercise-label">${set.exercise_name || `Exercise ${set.exercise_id}`}</span>
    <input type="number" class="set-reps" min="1" value="${set.reps}" title="Reps">
    <input type="number" class="set-weight" min="0" step="0.5" value="${set.weight}" title="Weight">
    <select class="set-type">
      <option value="normal"${set.set_type === "normal" ? " selected" : ""}>Normal</option>
      <option value="warmup"${set.set_type === "warmup" ? " selected" : ""}>Warm-up</option>
      <option value="drop"${set.set_type === "drop" ? " selected" : ""}>Drop</option>
      <option value="failure"${set.set_type === "failure" ? " selected" : ""}>Failure</option>
    </select>
    <select class="set-group">${groupOptions(session, groups, set.superset_group)}</select>
    <div class="set-actions">
      <button class="small secondary" data-act="up" title="Move up">↑</button>
      <button class="small secondary" data-act="down" title="Move down">↓</button>
      <button class="small danger" data-act="del" title="Delete">✕</button>
    </div>`;

  row.querySelector(".set-reps").addEventListener("change", (e) => patchSet(session.id, set.id, { reps: Number(e.target.value) }));
  row.querySelector(".set-weight").addEventListener("change", (e) => patchSet(session.id, set.id, { weight: Number(e.target.value) }));
  row.querySelector(".set-type").addEventListener("change", (e) => patchSet(session.id, set.id, { set_type: e.target.value }));
  row.querySelector(".set-group").addEventListener("change", (e) => {
    const value = e.target.value || null;
    patchSet(session.id, set.id, { superset_group: value }).then(() => {
      row.classList.toggle("grouped", Boolean(value));
    });
  });

  const actions = row.querySelectorAll("[data-act]");
  actions.forEach((btn) => {
    btn.addEventListener("click", () => {
      const act = btn.dataset.act;
      if (act === "up" || act === "down") reorder(session, set.id, act);
      else if (act === "del") deleteSet(session.id, set.id);
    });
  });

  return row;
}

async function patchSet(sessionId, setId, changes) {
  try {
    await api("PATCH", `/api/v1/sessions/${sessionId}/workout-sets/${setId}`, changes);
  } catch (err) {
    const msg = document.getElementById("workout-msg");
    if (msg) { msg.className = "msg error"; msg.textContent = err.message; }
  }
}

async function addSet(sessionId) {
  const select = document.getElementById("add-exercise");
  const exerciseId = Number(select.value);
  const body = { exercise_id: exerciseId, reps: 10, weight: 0, set_type: "normal" };
  if (workoutState.activeGroup) body.superset_group = workoutState.activeGroup;
  await api("POST", `/api/v1/sessions/${sessionId}/workout-sets`, body);
  render();
}

async function deleteSet(sessionId, setId) {
  await api("DELETE", `/api/v1/sessions/${sessionId}/workout-sets/${setId}`);
  render();
}

async function reorder(session, setId, direction) {
  const ids = session.workout_sets.map((s) => s.id);
  const i = ids.indexOf(setId);
  const j = direction === "up" ? i - 1 : i + 1;
  if (j < 0 || j >= ids.length) return;
  [ids[i], ids[j]] = [ids[j], ids[i]];
  await api("PUT", `/api/v1/sessions/${session.id}/workout-sets/order`, { set_ids: ids });
  render();
}

async function createSession() {
  const input = document.getElementById("new-session-name");
  const name = input.value.trim() || null;
  const session = await api("POST", "/api/v1/sessions", { name, workout_sets: [] });
  workoutState.selectedSessionId = session.id;
  render();
}

async function deleteSession(sessionId) {
  if (!confirm("Delete this session and all its sets?")) return;
  await api("DELETE", `/api/v1/sessions/${sessionId}`);
  workoutState.selectedSessionId = null;
  render();
}

function startSuperset() {
  workoutState.activeGroup = crypto.randomUUID();
  render();
}
