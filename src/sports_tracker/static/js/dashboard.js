// dashboard.js — weight/waist charts (a selectable month or the last 30 days
// at a time) with moving averages, the daily log form, the moving-average
// settings, and a history table.
async function renderDashboard(app) {
  app.innerHTML = `
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
      <h2>Metrics</h2>
      <div class="month-nav">
        <button type="button" id="month-prev" class="small secondary" aria-label="Previous window">◀</button>
        <select id="chart-window" aria-label="Chart window"></select>
        <button type="button" id="month-next" class="small secondary" aria-label="Next window">▶</button>
      </div>
      <p class="chart-hint">Click a legend entry to show or hide a series.</p>
      <div class="chart-canvas"><canvas id="main-chart"></canvas></div>
    </section>

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
  app.querySelector("#month-prev").addEventListener("click", () => shiftMonth(-1));
  app.querySelector("#month-next").addEventListener("click", () => shiftMonth(1));
  app.querySelector("#chart-window").addEventListener("change", () => renderMainChart());

  await refreshDashboard(app);
}

// Cached between refreshes so the month selector can redraw the chart
// without refetching.
let dashboardSeries = [];
let dashboardSettings = null;

async function refreshDashboard(app) {
  const [series, settings, measurements] = await Promise.all([
    api("GET", "/api/v1/measurements/series"),
    api("GET", "/api/v1/settings"),
    api("GET", "/api/v1/measurements"),
  ]);

  dashboardSeries = series;
  dashboardSettings = settings;

  app.querySelector("#set-weight").value = settings.weight_ma_window;
  app.querySelector("#set-waist").value = settings.waist_ma_window;
  app.querySelector("#set-recomp").value = settings.recomp_window;

  refreshWindowSelect();
  renderMainChart();

  renderHistory(app, measurements);
}

// Rebuild the window dropdown ("Last 30 days" plus one entry per month with
// data, most recent first, the current month always included) while keeping
// the selection when it still exists. Defaults to the last 30 days.
function refreshWindowSelect() {
  const select = document.getElementById("chart-window");
  const previous = select.value;

  const months = [...new Set(dashboardSeries.map((p) => p.date.slice(0, 7)))]
    .sort()
    .reverse();
  const currentYm = localDate().slice(0, 7);
  if (!months.includes(currentYm)) months.unshift(currentYm);

  const values = ["last30", ...months];
  select.innerHTML = values
    .map((v) => `<option value="${v}">${windowLabel(v)}</option>`)
    .join("");
  select.value = values.includes(previous) ? previous : "last30";

  syncMonthNav();
}

function windowLabel(value) {
  if (value === "last30") return "Last 30 days";
  const [y, m] = value.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });
}

function shiftMonth(delta) {
  const select = document.getElementById("chart-window");
  const target = select.selectedIndex + delta;
  if (target < 0 || target >= select.options.length) return;
  select.selectedIndex = target;
  syncMonthNav();
  renderMainChart();
}

function syncMonthNav() {
  const select = document.getElementById("chart-window");
  document.getElementById("month-next").disabled = select.selectedIndex === 0;
  document.getElementById("month-prev").disabled =
    select.selectedIndex === select.options.length - 1;
}

// Window filter: "last30" is a rolling 30-day window ending today; anything
// else is a YYYY-MM calendar month. Dates are YYYY-MM-DD strings, so they
// compare chronologically as strings.
function filterByWindow(series, mode) {
  if (mode !== "last30") {
    return series.filter((p) => p.date.slice(0, 7) === mode);
  }
  const start = new Date();
  start.setDate(start.getDate() - 29);
  const startStr = localDate(start);
  const endStr = localDate();
  return series.filter((p) => p.date >= startStr && p.date <= endStr);
}

// One chart holds every series (weight, waist, recomposition — raw and moving
// average) for the window picked in #chart-window. The moving averages are
// computed server-side over the full history, so slicing the series to the
// window here keeps their values correct. Clicking a legend entry toggles a
// series on/off (Chart.js default).
function renderMainChart() {
  const canvas = document.getElementById("main-chart");
  // Chart.getChart(canvas) returns the chart instance bound to this canvas.
  // (Don't track charts on `window[canvasId]`: the id collides with the
  // browser's named access to the <canvas> element, which has no .destroy.)
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();

  const series = filterByWindow(
    dashboardSeries,
    document.getElementById("chart-window").value,
  );
  const settings = dashboardSettings;
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
