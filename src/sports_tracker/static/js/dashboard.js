// dashboard.js — weight/waist charts with moving averages, the daily log form,
// the moving-average settings, and a history table.
async function renderDashboard(app) {
  app.innerHTML = `
    <section class="panel">
      <h1>Dashboard</h1>
      <div class="charts">
        <div class="chart-box">
          <h2>Metrics</h2>
          <p class="chart-hint">Click a legend entry to show or hide a series.</p>
          <div class="chart-canvas"><canvas id="main-chart"></canvas></div>
        </div>
      </div>
    </section>

    <div class="grid">
      <form class="panel" id="log-form">
        <h2>Log today</h2>
        <label>Date<input type="date" id="log-date" required></label>
        <label>Weight (kg)<input type="number" id="log-weight" step="0.1" min="0"></label>
        <label>Waist (cm)<input type="number" id="log-waist" step="0.1" min="0"></label>
        <button type="submit">Save</button>
        <p class="msg" id="log-msg"></p>
      </form>

      <form class="panel" id="settings-form">
        <h2>Metric windows</h2>
        <label>Weight MA (days)<input type="number" id="set-weight" min="1" max="365"></label>
        <label>Waist MA (days)<input type="number" id="set-waist" min="1" max="365"></label>
        <label>Recomposition (days)<input type="number" id="set-recomp" min="1" max="365"></label>
        <button type="submit">Save</button>
        <p class="msg" id="settings-msg"></p>
      </form>
    </div>

    <section class="panel">
      <h2>History</h2>
      <table>
        <thead><tr><th>Date</th><th>Weight (kg)</th><th>Waist (cm)</th><th></th></tr></thead>
        <tbody id="history-body"></tbody>
      </table>
    </section>`;

  app.querySelector("#log-date").value = localDate();
  app.querySelector("#log-form").addEventListener("submit", (e) => onLogSubmit(e));
  app.querySelector("#settings-form").addEventListener("submit", (e) => onSettingsSubmit(e));

  await refreshDashboard(app);
}

async function refreshDashboard(app) {
  const [series, settings, measurements] = await Promise.all([
    api("GET", "/api/v1/measurements/series"),
    api("GET", "/api/v1/settings"),
    api("GET", "/api/v1/measurements"),
  ]);

  app.querySelector("#set-weight").value = settings.weight_ma_window;
  app.querySelector("#set-waist").value = settings.waist_ma_window;
  app.querySelector("#set-recomp").value = settings.recomp_window;

  renderMainChart(series, settings);

  renderHistory(app, measurements);
}

// One chart holds every series (weight, waist, recomposition — raw and moving
// average). Clicking a legend entry toggles a series on/off (Chart.js default).
function renderMainChart(series, settings) {
  const canvas = document.getElementById("main-chart");
  // Chart.getChart(canvas) returns the chart instance bound to this canvas.
  // (Don't track charts on `window[canvasId]`: the id collides with the
  // browser's named access to the <canvas> element, which has no .destroy.)
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();

  const labels = series.map((p) => p.date);

  new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Weight (kg)",
          data: series.map((p) => p.weight_kg),
          borderColor: "#2563eb",
          backgroundColor: "#2563eb",
          spanGaps: true,
          tension: 0.2,
          yAxisID: "y",
        },
        {
          label: `Weight ${settings.weight_ma_window}d avg`,
          data: series.map((p) => p.weight_ma),
          borderColor: "#2563eb",
          backgroundColor: "#2563eb",
          borderDash: [5, 5],
          spanGaps: true,
          tension: 0.2,
          pointRadius: 0,
          yAxisID: "y",
        },
        {
          label: "Waist (cm)",
          data: series.map((p) => p.waist_cm),
          borderColor: "#f59e0b",
          backgroundColor: "#f59e0b",
          spanGaps: true,
          tension: 0.2,
          yAxisID: "y",
        },
        {
          label: `Waist ${settings.waist_ma_window}d avg`,
          data: series.map((p) => p.waist_ma),
          borderColor: "#f59e0b",
          backgroundColor: "#f59e0b",
          borderDash: [5, 5],
          spanGaps: true,
          tension: 0.2,
          pointRadius: 0,
          yAxisID: "y",
        },
        {
          label: "Recomposition",
          data: series.map((p) => p.recomposition),
          borderColor: "#10b981",
          backgroundColor: "#10b981",
          spanGaps: true,
          tension: 0.2,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
      scales: {
        // Weight and waist are numerically comparable (kg vs cm); recomposition
        // is a small ratio score so it gets its own right-hand axis.
        y: { title: { display: true, text: "kg / cm" } },
        y1: {
          position: "right",
          title: { display: true, text: "Recomposition" },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

function renderHistory(app, measurements) {
  const body = app.querySelector("#history-body");
  if (!measurements.length) {
    body.innerHTML = '<tr><td colspan="4" style="color:var(--muted)">No entries yet.</td></tr>';
    return;
  }

  body.innerHTML = "";
  // Most recent first.
  const rows = [...measurements].sort((a, b) => (a.date < b.date ? 1 : -1));
  for (const m of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${m.date}</td>
      <td>${m.weight_kg == null ? "—" : m.weight_kg}</td>
      <td>${m.waist_cm == null ? "—" : m.waist_cm}</td>
      <td>
        <div class="row-actions">
          <button class="small secondary btn-edit">Edit</button>
          <button class="danger small btn-delete">Delete</button>
        </div>
      </td>`;
    tr.querySelector(".btn-edit").addEventListener("click", () => enterEditMode(tr, m));
    tr.querySelector(".btn-delete").addEventListener("click", () => deleteMeasurement(m.id));
    body.appendChild(tr);
  }
}

function enterEditMode(tr, m) {
  const [, weightCell, waistCell, actionsCell] = tr.children;
  weightCell.innerHTML = `<input type="number" step="0.1" min="0" value="${m.weight_kg ?? ""}" class="edit-weight" aria-label="Weight">`;
  waistCell.innerHTML = `<input type="number" step="0.1" min="0" value="${m.waist_cm ?? ""}" class="edit-waist" aria-label="Waist">`;
  actionsCell.innerHTML = editActions();
  actionsCell.querySelector(".save-edit").addEventListener("click", () => saveEdit(tr, m));
  actionsCell.querySelector(".cancel-edit").addEventListener("click", () => refreshDashboard(document.getElementById("app")));
}

function editActions(error) {
  return (error ? `<span class="msg error">${error}</span>` : "") +
    '<button class="small save-edit">Save</button>' +
    '<button class="small secondary cancel-edit">Cancel</button>';
}

async function saveEdit(tr, m) {
  const actionsCell = tr.lastElementChild;
  const weight = tr.querySelector(".edit-weight").value;
  const waist = tr.querySelector(".edit-waist").value;
  const weightKg = weight === "" ? null : Number(weight);
  const waistCm = waist === "" ? null : Number(waist);

  if (weightKg == null && waistCm == null) {
    actionsCell.innerHTML = editActions("Enter a weight or waist.");
    actionsCell.querySelector(".cancel-edit").addEventListener("click", () => refreshDashboard(document.getElementById("app")));
    return;
  }

  try {
    await api("PATCH", `/api/v1/measurements/${m.id}`, { weight_kg: weightKg, waist_cm: waistCm });
    await refreshDashboard(document.getElementById("app"));
  } catch (err) {
    actionsCell.innerHTML = editActions(err.message);
    actionsCell.querySelector(".cancel-edit").addEventListener("click", () => refreshDashboard(document.getElementById("app")));
  }
}

async function onLogSubmit(e) {
  e.preventDefault();
  const app = document.getElementById("app");
  const msg = app.querySelector("#log-msg");
  msg.className = "msg";
  msg.textContent = "";

  const date = app.querySelector("#log-date").value;
  const weight = app.querySelector("#log-weight").value;
  const waist = app.querySelector("#log-waist").value;

  if (!weight && !waist) {
    msg.className = "msg error";
    msg.textContent = "Enter a weight or a waist.";
    return;
  }

  const body = { date };
  if (weight) body.weight_kg = Number(weight);
  if (waist) body.waist_cm = Number(waist);

  try {
    await api("POST", "/api/v1/measurements", body);
    msg.className = "msg ok";
    msg.textContent = "Saved ✓";
    await refreshDashboard(app);
  } catch (err) {
    msg.className = "msg error";
    msg.textContent = err.message;
  }
}

async function onSettingsSubmit(e) {
  e.preventDefault();
  const app = document.getElementById("app");
  const msg = app.querySelector("#settings-msg");
  msg.className = "msg";
  msg.textContent = "";

  try {
    await api("PATCH", "/api/v1/settings", {
      weight_ma_window: Number(app.querySelector("#set-weight").value),
      waist_ma_window: Number(app.querySelector("#set-waist").value),
      recomp_window: Number(app.querySelector("#set-recomp").value),
    });
    msg.className = "msg ok";
    msg.textContent = "Saved ✓";
    await refreshDashboard(app);
  } catch (err) {
    msg.className = "msg error";
    msg.textContent = err.message;
  }
}

async function deleteMeasurement(id) {
  await api("DELETE", `/api/v1/measurements/${id}`);
  await refreshDashboard(document.getElementById("app"));
}
