let dashboardSeries = [];
let dashboardSettings = null;
let dashboardMeasurements = [];
let editingMeasurement = null;
let undoMeasurementId = null;
let importPreview = null;
const MEASUREMENT_DAY = 86400000;

function measurementUnit(metric) { return metric === "weight" ? dashboardSettings.weight_unit : dashboardSettings.waist_unit; }
function measurementFactor(metric) { return measurementUnit(metric) === "lb" ? 1 / 0.45359237 : measurementUnit(metric) === "in" ? 1 / 2.54 : 1; }
function measurementDisplay(value, metric) { return value == null ? "" : String(Number((value * measurementFactor(metric)).toFixed(2))); }
function measurementStamp(date) { return Date.parse(`${date}T00:00:00Z`); }
function measurementISO(stamp) { return new Date(stamp).toISOString().slice(0, 10); }

async function renderDashboard(app) {
  editingMeasurement = null;
  undoMeasurementId = null;
  importPreview = null;
  app.innerHTML = `
    <p id="reminder-msg" class="msg" role="status"></p>
    <div class="grid">
      <form class="panel" id="log-form">
        <h2 id="log-heading">Log measurements</h2>
        <p class="chart-hint" id="entry-context"></p>
        <label>Date<input type="date" id="log-date" required></label>
        <label>Weight (<span data-unit="weight">kg</span>)<input type="number" id="log-weight" step="any" min="0.01"></label>
        <label>Waist (<span data-unit="waist">cm</span>)<input type="number" id="log-waist" step="any" min="0.01"></label>
        <details><summary>Repeat waist readings and notes</summary>
          <label>2–5 waist readings (<span data-unit="waist">cm</span>), separated by commas
            <input id="log-repeats" placeholder="82.0, 82.4" inputmode="decimal"></label>
          <p class="chart-hint">Repeat readings are saved individually; their average becomes the waist value.</p>
          <label>Notes<textarea id="log-notes" maxlength="1000" rows="2" placeholder="Optional context or measurement method"></textarea></label>
        </details>
        <details class="measurement-guide"><summary>Keep measurements consistent</summary>
          <p class="chart-hint">Use the same scale, tape position, and similar conditions each time. For waist, keep the tape level without pulling it tight, and record the method in your notes. You can repeat a reading to check consistency.</p>
        </details>
        <div class="row-actions"><button type="submit" id="log-save">Save</button><button type="button" class="secondary" id="log-cancel" hidden>Cancel edit</button></div>
        <p class="msg" id="log-msg" role="status"></p>
      </form>
      <details class="panel measurement-settings">
        <summary>Measurement settings</summary>
        <form id="settings-form">
          <label>Weight average (calendar days)<input type="number" id="set-weight" min="1" max="365" required></label>
          <label>Waist average (calendar days)<input type="number" id="set-waist" min="1" max="365" required></label>
          <label>Recomposition lookback (readings)<input type="number" id="set-recomp" min="1" max="365" required></label>
          <label>Weight unit<select id="set-weight-unit"><option value="kg">kg</option><option value="lb">lb</option></select></label>
          <label>Waist unit<select id="set-waist-unit"><option value="cm">cm</option><option value="in">in</option></select></label>
          <label>Weight reminder interval (days; 0 = off)<input type="number" id="set-weight-reminder" min="0" max="365" required></label>
          <label>Waist reminder interval (days; 0 = off)<input type="number" id="set-waist-reminder" min="0" max="365" required></label>
          <p class="chart-hint">Reminders appear here when you open the dashboard. Changing units only changes display and entry units.</p>
          <button type="submit">Save settings</button><p class="msg" id="settings-msg" role="status"></p>
        </form>
      </details>
    </div>
    <section class="panel">
      <h2>Progress</h2>
      <div class="month-nav">
        <button type="button" id="month-prev" class="small secondary" aria-label="Previous window">◀</button>
        <select id="chart-window" aria-label="Chart window"></select>
        <button type="button" id="month-next" class="small secondary" aria-label="Next window">▶</button>
      </div>
      <div id="measurement-summary" class="grid"></div>
      <p id="measurement-comparison" class="chart-hint"></p>
      <p class="chart-hint">Dots are readings; dashed lines are calendar-day averages. Long gaps break the lines. Click a legend entry to show or hide a series.</p>
      <h2>Weight (<span data-unit="weight">kg</span>)</h2>
      <div class="chart-canvas"><canvas id="weight-chart" role="img" aria-label="Weight readings and trend"></canvas></div>
      <h2>Waist (<span data-unit="waist">cm</span>)</h2>
      <div class="chart-canvas"><canvas id="waist-chart" role="img" aria-label="Waist readings and trend"></canvas></div>
      <h2>Recomposition index</h2>
      <p class="chart-hint">Original formula: 100 × (weight / earlier weight − waist / earlier waist). The lookback counts readings for each metric, so their baseline dates can differ.</p>
      <p id="recomposition-status" class="chart-hint" role="status"></p>
      <div class="chart-canvas"><canvas id="recomposition-chart" role="img" aria-label="Recomposition index over time"></canvas></div>
    </section>
    <section class="panel">
      <h2>History</h2>
      <p id="history-msg" class="msg" role="status"></p>
      <button type="button" id="undo-delete" class="secondary" hidden>Undo last deletion</button>
      <div class="measurement-table"><table>
        <thead><tr><th>Date</th><th>Weight (<span data-unit="weight">kg</span>)</th><th>Waist (<span data-unit="waist">cm</span>)</th><th>Notes / repeats</th><th>Actions</th></tr></thead>
        <tbody id="history-body"></tbody>
      </table></div>
      <nav class="history-pagination" aria-label="Measurement history pages">
        <button type="button" id="history-prev" class="small secondary">Previous</button>
        <span id="history-page-status" role="status" aria-live="polite"></span>
        <button type="button" id="history-next" class="small secondary">Next</button>
      </nav>
    </section>
    <details class="panel"><summary>Deleted entries</summary>
      <p class="chart-hint">Deleted measurements stay recoverable, including after you close the app.</p>
      <button type="button" id="load-deleted" class="secondary">Show deleted entries</button>
      <p id="deleted-msg" class="msg" role="status"></p><ul id="deleted-list"></ul>
    </details>
    <details class="panel"><summary>Import / export measurements</summary>
      <p class="chart-hint">Export includes your complete active history in kg/cm, with notes and repeat readings. Imports accept date (YYYY-MM-DD), weight_kg or weight_lb, waist_cm or waist_in, notes, and waist_readings (cm, separated by |). Preview before importing.</p>
      <button type="button" id="export-measurements" class="secondary">Export CSV</button>
      <form id="import-form">
        <label>CSV file<input type="file" id="import-file" accept=".csv,text/csv" required></label>
        <label>Existing dates<select id="import-conflict"><option value="skip">Keep existing entries (recommended)</option><option value="update">Update supplied fields on existing dates</option></select></label>
        <button type="submit">Preview import</button>
        <button type="button" id="confirm-import" hidden>Import previewed file</button>
      </form>
      <p id="import-msg" class="msg" role="status"></p><ul id="import-preview"></ul>
    </details>`;
  app.querySelector("#log-date").value = localDate();
  app.querySelector("#log-form").addEventListener("submit", onLogSubmit);
  app.querySelector("#log-date").addEventListener("change", () => { if (!editingMeasurement) loadMeasurementDate(); });
  app.querySelector("#log-cancel").onclick = () => { editingMeasurement = null; app.querySelector("#log-date").value = localDate(); loadMeasurementDate(); };
  app.querySelector("#settings-form").addEventListener("submit", onSettingsSubmit);
  app.querySelector("#month-prev").onclick = () => shiftMonth(-1);
  app.querySelector("#month-next").onclick = () => shiftMonth(1);
  app.querySelector("#chart-window").onchange = renderMainChart;
  app.querySelector("#undo-delete").onclick = undoMeasurementDeletion;
  app.querySelector("#load-deleted").onclick = loadDeletedMeasurements;
  app.querySelector("#export-measurements").onclick = exportMeasurementCSV;
  app.querySelector("#import-form").onsubmit = previewMeasurementImport;
  app.querySelector("#confirm-import").onclick = commitMeasurementImport;
  for (const id of ["import-file", "import-conflict"]) app.querySelector(`#${id}`).onchange = () => {
    importPreview = null; app.querySelector("#confirm-import").hidden = true;
    app.querySelector("#import-msg").textContent = "Preview the selected file and options before importing.";
    app.querySelector("#import-preview").replaceChildren();
  };
  try { await refreshDashboard(app); loadMeasurementDate(); }
  catch (err) { app.querySelector("#log-msg").textContent = err.message; }
}

async function refreshDashboard(app) {
  const [series, settings, measurements] = await Promise.all([
    api("GET", "/api/v1/measurements/series"), api("GET", "/api/v1/settings"), api("GET", "/api/v1/measurements"),
  ]);
  if (!app.querySelector("#log-form")) return;
  dashboardSeries = series; dashboardSettings = settings; dashboardMeasurements = measurements;
  for (const [id, field] of [["set-recomp", "recomp_window"], ["set-weight", "weight_ma_window"], ["set-waist", "waist_ma_window"], ["set-weight-unit", "weight_unit"], ["set-waist-unit", "waist_unit"], ["set-weight-reminder", "weight_reminder_days"], ["set-waist-reminder", "waist_reminder_days"]]) {
    app.querySelector(`#${id}`).value = settings[field];
  }
  app.querySelectorAll("[data-unit]").forEach((el) => { el.textContent = measurementUnit(el.dataset.unit); });
  refreshWindowSelect(); renderMainChart(); renderHistory(app, measurements); renderMeasurementReminders();
}
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

function measurementBounds() {
  const mode = document.getElementById("chart-window").value;
  const today = measurementStamp(localDate());
  if (mode === "last30") return [today - 29 * MEASUREMENT_DAY, today];
  const [year, month] = mode.split("-").map(Number);
  const start = Date.UTC(year, month - 1, 1);
  const end = Date.UTC(year, month, 0);
  return [start, start <= today ? Math.min(end, today) : end];
}
function filterByWindow(series) {
  const [start, end] = measurementBounds();
  return series.filter((point) => measurementStamp(point.date) >= start && measurementStamp(point.date) <= end);
}
function renderMainChart() {
  syncMonthNav();
  const series = filterByWindow(dashboardSeries);
  const [start, end] = measurementBounds();
  const byDate = new Map(series.map((point) => [point.date, point]));
  for (const metric of ["weight", "waist"]) {
    const canvas = document.getElementById(`${metric}-chart`);
    Chart.getChart(canvas)?.destroy();
    const field = metric === "weight" ? "weight_kg" : "waist_cm";
    const windowDays = dashboardSettings[`${metric}_ma_window`];
    const raw = [], trend = [];
    for (let date = start; date <= end; date += MEASUREMENT_DAY) {
      const point = byDate.get(measurementISO(date));
      raw.push({x: date, y: point?.[field] == null ? null : point[field] * measurementFactor(metric)});
      trend.push({x: date, y: point?.[`${metric}_ma`] == null ? null : point[`${metric}_ma`] * measurementFactor(metric), count: point?.[`${metric}_count`] || 0});
    }
    const color = metric === "weight" ? "#2563eb" : "#b45309";
    new Chart(canvas, {
      type: "line", data: {datasets: [
        {label: `Readings (${measurementUnit(metric)})`, data: raw, borderColor: color, backgroundColor: color, pointRadius: 3, borderWidth: 1, spanGaps: 7 * MEASUREMENT_DAY, tension: 0},
        {label: `${windowDays}-day average`, data: trend, borderColor: color, borderDash: [5,5], borderWidth: 2, pointRadius: 0, pointHitRadius: 8, spanGaps: windowDays * MEASUREMENT_DAY, tension: 0},
      ]},
      options: {
        responsive: true, maintainAspectRatio: false, parsing: false,
        plugins: {legend: {position: "bottom"}, tooltip: {callbacks: {
          title: (items) => items.length ? measurementISO(items[0].parsed.x) : "",
          label: (context) => `${context.dataset.label}: ${context.parsed.y.toFixed(2)}${context.raw.count ? ` · ${context.raw.count} reading${context.raw.count === 1 ? "" : "s"}` : ""}`,
        }}},
        scales: {x: {type: "linear", min: start, max: Math.max(end, start + MEASUREMENT_DAY), ticks: {maxTicksLimit: 6, callback: (value) => measurementISO(value).slice(5)}}, y: {title: {display: true, text: measurementUnit(metric)}}},
      },
    });
  }
  renderRecompositionChart(series, start, end);
  renderMeasurementSummary(series, end);
}
function renderRecompositionChart(series, start, end) {
  const canvas = document.getElementById("recomposition-chart");
  Chart.getChart(canvas)?.destroy();
  const byDate = new Map(series.map((point) => [point.date, point.recomposition]));
  const data = [];
  for (let date = start; date <= end; date += MEASUREMENT_DAY) {
    data.push({x: date, y: byDate.get(measurementISO(date)) ?? null});
  }
  const lookback = dashboardSettings.recomp_window;
  const available = data.filter((point) => point.y != null);
  const status = document.getElementById("recomposition-status");
  status.textContent = available.length
    ? `Latest index in this window: ${available.at(-1).y.toFixed(2)} (${measurementISO(available.at(-1).x)}) · lookback: ${lookback} readings.`
    : `Insufficient data in this window. The index needs both metrics on a date and ${lookback} earlier readings of each metric.`;
  new Chart(canvas, {
    type: "line",
    data: {datasets: [{label: `Recomposition (${lookback}-reading lookback)`, data,
      borderColor: "#059669", backgroundColor: "#059669", pointRadius: 3,
      spanGaps: 7 * MEASUREMENT_DAY, tension: 0}]},
    options: {
      responsive: true, maintainAspectRatio: false, parsing: false,
      plugins: {legend: {position: "bottom"}, tooltip: {callbacks: {
        title: (items) => items.length ? measurementISO(items[0].parsed.x) : "",
        label: (context) => `Recomposition index: ${context.parsed.y.toFixed(2)}`,
      }}},
      scales: {
        x: {type: "linear", min: start, max: Math.max(end, start + MEASUREMENT_DAY),
          ticks: {maxTicksLimit: 6, callback: (value) => measurementISO(value).slice(5)}},
        y: {title: {display: true, text: "Recomposition index"}},
      },
    },
  });
}
function renderMeasurementSummary(series, end) {
  const summary = document.getElementById("measurement-summary");
  summary.replaceChildren();
  for (const metric of ["weight", "waist"]) {
    const field = metric === "weight" ? "weight_kg" : "waist_cm";
    const readings = dashboardSeries.filter((point) => measurementStamp(point.date) <= end && point[field] != null);
    const latest = readings.at(-1);
    const days = dashboardSettings[`${metric}_ma_window`];
    const stale = latest && end - measurementStamp(latest.date) >= days * MEASUREMENT_DAY;
    const card = document.createElement("div"); card.className = "measurement-stat";
    const title = document.createElement("h3"); title.textContent = metric === "weight" ? "Weight" : "Waist"; card.append(title);
    const current = document.createElement("p"); current.className = "measurement-value";
    current.textContent = latest ? `${measurementDisplay(latest[field], metric)} ${measurementUnit(metric)}` : "No readings yet"; card.append(current);
    const detail = document.createElement("p"); detail.className = "chart-hint";
    detail.textContent = latest ? `Latest as of ${measurementISO(end)}: ${latest.date}${stale ? " · stale" : ""}` : "Add a measurement to start."; card.append(detail);
    const average = document.createElement("p"); average.className = "chart-hint";
    const recent = readings.filter((point) => point[field] > 0 && measurementStamp(point.date) >= end - (days - 1) * MEASUREMENT_DAY);
    const count = recent.length;
    const mean = count ? recent.reduce((sum, point) => sum + point[field], 0) / count : null;
    average.textContent = mean != null ? `${days}-day average: ${measurementDisplay(mean, metric)} ${measurementUnit(metric)} · ${count} reading${count === 1 ? "" : "s"}${count < 2 ? " · insufficient data for a trend" : ""}` : "No recent average available."; card.append(average);
    const period = series.filter((point) => point[field] != null && point[field] > 0);
    const change = document.createElement("p"); change.className = "chart-hint";
    if (period.length >= 2) {
      const delta = period.at(-1)[field] - period[0][field];
      change.textContent = `Selected period: ${delta > 0 ? "+" : ""}${measurementDisplay(delta, metric)} ${measurementUnit(metric)} (${period[0].date} → ${period.at(-1).date})`;
    } else change.textContent = "Selected period: insufficient data for a change.";
    card.append(change); summary.append(card);
  }
  const paired = series.filter((p) => p.weight_kg > 0 && p.waist_cm > 0);
  const comparison = document.getElementById("measurement-comparison");
  if (paired.length < 2) comparison.textContent = "Same-period comparison: insufficient data. Log both metrics on at least two dates in this window.";
  else {
    const first = paired[0], last = paired.at(-1);
    const describe = (value, metric) => `${value > 0 ? "+" : ""}${measurementDisplay(value, metric)} ${measurementUnit(metric)}`;
    comparison.textContent = `Same dates (${first.date} → ${last.date}): weight ${describe(last.weight_kg - first.weight_kg, "weight")}; waist ${describe(last.waist_cm - first.waist_cm, "waist")}. These are measurement changes, not estimates of fat or muscle.`;
  }
}
function renderMeasurementReminders() {
  const messages = [];
  for (const metric of ["weight", "waist"]) {
    const days = dashboardSettings[`${metric}_reminder_days`];
    const field = metric === "weight" ? "weight_kg" : "waist_cm";
    const latest = dashboardMeasurements.filter((m) => m.date <= localDate() && m[field] > 0).at(-1);
    if (days && (!latest || measurementStamp(localDate()) - measurementStamp(latest.date) >= days * MEASUREMENT_DAY)) messages.push(`Time to log ${metric}${latest ? ` (last recorded ${latest.date})` : ""}.`);
  }
  document.getElementById("reminder-msg").textContent = messages.join(" ");
}

function loadMeasurementDate(measurement = null) {
  const app = document.getElementById("app");
  const date = app.querySelector("#log-date").value;
  const entry = measurement || dashboardMeasurements.find((m) => m.date === date);
  // Date selection loads an existing entry; explicit Edit allows its date to be corrected.
  editingMeasurement = measurement;
  app.querySelector("#log-weight").value = entry ? measurementDisplay(entry.weight_kg, "weight") : "";
  app.querySelector("#log-waist").value = entry ? measurementDisplay(entry.waist_cm, "waist") : "";
  app.querySelector("#log-repeats").value = (entry?.waist_readings || []).map((v) => measurementDisplay(v, "waist")).join(", ");
  app.querySelector("#log-notes").value = entry?.notes || "";
  app.querySelector("#log-heading").textContent = measurement ? "Edit measurement" : "Log measurements";
  app.querySelector("#log-save").textContent = entry ? "Update entry" : "Save entry";
  app.querySelector("#log-cancel").hidden = !measurement;
  app.querySelector("#entry-context").textContent = entry ? `Editing the entry from ${entry.date}. Blank fields clear that metric.` : "Add either metric, or both.";
}
function renderHistory(app, measurements, requestedPage) {
  const body = app.querySelector("#history-body");
  const pageSize = 10, pages = Math.max(1, Math.ceil(measurements.length / pageSize));
  const page = Math.min(pages, Math.max(1, requestedPage ?? Number(body.dataset.page || 1)));
  body.dataset.page = page;
  const start = (page - 1) * pageSize;
  for (const [id, delta] of [["history-prev", -1], ["history-next", 1]]) {
    const button = app.querySelector(`#${id}`); button.disabled = delta < 0 ? page === 1 : page === pages;
    button.onclick = () => renderHistory(app, measurements, page + delta);
  }
  app.querySelector("#history-page-status").textContent = measurements.length ? `${start + 1}–${Math.min(start + pageSize, measurements.length)} of ${measurements.length} · Page ${page} of ${pages}` : "0 entries";
  body.replaceChildren();
  if (!measurements.length) { body.innerHTML = '<tr><td colspan="5">No entries yet.</td></tr>'; return; }
  for (const m of [...measurements].sort((a,b) => b.date.localeCompare(a.date)).slice(start, start + pageSize)) {
    const tr = document.createElement("tr");
    for (const text of [m.date, measurementDisplay(m.weight_kg, "weight") || "—", measurementDisplay(m.waist_cm, "waist") || "—", [m.notes, m.waist_readings?.length ? `Repeats: ${m.waist_readings.map((v) => measurementDisplay(v, "waist")).join(", ")} ${measurementUnit("waist")}` : ""].filter(Boolean).join(" · ")]) {
      const td = document.createElement("td"); td.textContent = text; tr.append(td);
    }
    const td = document.createElement("td"), actions = document.createElement("div"); actions.className = "row-actions";
    for (const [label, action] of [["Edit", () => { app.querySelector("#log-date").value = m.date; loadMeasurementDate(m); app.querySelector("#log-date").focus(); app.querySelector("#log-form").scrollIntoView({behavior: "smooth"}); }], ["Delete", () => deleteMeasurement(m.id)]]) {
      const button = document.createElement("button"); button.type = "button"; button.className = label === "Delete" ? "small danger" : "small secondary"; button.textContent = label; button.onclick = action; actions.append(button);
    }
    td.append(actions); tr.append(td); body.append(tr);
  }
}
function measurementChangeWarnings(body, existing) {
  const warnings = [];
  for (const [field, metric, threshold] of [["weight_kg", "weight", 0.1], ["waist_cm", "waist", 0.1]]) {
    if (body[field] == null) continue;
    const baseline = existing?.[field] ?? dashboardMeasurements.filter((m) => m.date <= body.date && m[field] > 0).at(-1)?.[field];
    if (baseline > 0 && Math.abs(body[field] - baseline) / baseline > threshold) warnings.push(`${metric} changes by more than ${threshold * 100}%`);
  }
  return warnings;
}
async function onLogSubmit(e) {
  e.preventDefault();
  const app = document.getElementById("app"), msg = app.querySelector("#log-msg"), button = app.querySelector("#log-save");
  msg.className = "msg"; msg.textContent = "";
  const date = app.querySelector("#log-date").value;
  const existing = editingMeasurement || dashboardMeasurements.find((m) => m.date === date);
  const body = {date};
  try {
    for (const metric of ["weight", "waist"]) {
      const field = metric === "weight" ? "weight_kg" : "waist_cm";
      const value = app.querySelector(`#log-${metric}`).value;
      if (!existing || value !== measurementDisplay(existing[field], metric)) body[field] = value === "" ? null : Number(value) / measurementFactor(metric);
    }
    const repeatsText = app.querySelector("#log-repeats").value.trim();
    const originalRepeats = (existing?.waist_readings || []).map((v) => measurementDisplay(v, "waist")).join(", ");
    if (repeatsText !== originalRepeats) {
      body.waist_readings = repeatsText ? repeatsText.split(/[,;\s]+/).map((v) => Number(v) / measurementFactor("waist")) : null;
      if (body.waist_readings) {
        if (body.waist_readings.length < 2 || body.waist_readings.length > 5 || body.waist_readings.some((v) => !Number.isFinite(v) || v <= 0)) throw new Error("Enter 2–5 positive waist readings.");
        body.waist_cm = Math.round(body.waist_readings.reduce((a,b) => a+b,0) / body.waist_readings.length * 100) / 100;
      }
    } else if ("waist_cm" in body && existing?.waist_readings) body.waist_readings = null;
    const notes = app.querySelector("#log-notes").value;
    if (!existing || notes !== (existing.notes || "")) body.notes = notes || null;
    const finalWeight = "weight_kg" in body ? body.weight_kg : existing?.weight_kg;
    const finalWaist = "waist_cm" in body ? body.waist_cm : existing?.waist_cm;
    if (finalWeight == null && finalWaist == null) throw new Error("Enter a weight or waist measurement.");
    for (const field of ["weight_kg", "waist_cm"]) if (body[field] != null && (!Number.isFinite(body[field]) || body[field] <= 0)) throw new Error("Measurements must be greater than zero.");
    const warnings = measurementChangeWarnings(body, existing);
    if (warnings.length && !window.confirm(`${warnings.join("; ")}. Save these values?`)) return;
    if (existing && body.date === existing.date) delete body.date;
    button.disabled = true;
    if (Object.keys(body).length) await api(existing ? "PATCH" : "POST", existing ? `/api/v1/measurements/${existing.id}` : "/api/v1/measurements", body);
    editingMeasurement = null;
    app.querySelector("#history-body").dataset.page = 1;
    await refreshDashboard(app); loadMeasurementDate();
    msg.className = "msg ok"; msg.textContent = "Saved ✓";
  } catch (err) { msg.className = "msg error"; msg.textContent = err.message; }
  finally { button.disabled = false; }
}
async function onSettingsSubmit(e) {
  e.preventDefault();
  const app = document.getElementById("app"), msg = app.querySelector("#settings-msg");
  // Saving display units reloads entry values; avoid discarding an unsaved entry.
  const originalUnit = {weight: dashboardSettings.weight_unit, waist: dashboardSettings.waist_unit};
  const unitChanged = app.querySelector("#set-weight-unit").value !== originalUnit.weight || app.querySelector("#set-waist-unit").value !== originalUnit.waist;
  const draft = {weight: app.querySelector("#log-weight").value, waist: app.querySelector("#log-waist").value, repeats: app.querySelector("#log-repeats").value};
  try {
    await api("PATCH", "/api/v1/settings", {
      recomp_window: Number(app.querySelector("#set-recomp").value),
      weight_ma_window: Number(app.querySelector("#set-weight").value), waist_ma_window: Number(app.querySelector("#set-waist").value),
      weight_unit: app.querySelector("#set-weight-unit").value, waist_unit: app.querySelector("#set-waist-unit").value,
      weight_reminder_days: Number(app.querySelector("#set-weight-reminder").value), waist_reminder_days: Number(app.querySelector("#set-waist-reminder").value),
    });
    await refreshDashboard(app);
    if (unitChanged) {
      const oldFactor = (metric) => originalUnit[metric] === "lb" ? 1 / 0.45359237 : originalUnit[metric] === "in" ? 1 / 2.54 : 1;
      const entry = editingMeasurement || dashboardMeasurements.find((m) => m.date === app.querySelector("#log-date").value);
      const oldDisplay = (value, metric) => value == null ? "" : String(Number((value * oldFactor(metric)).toFixed(2)));
      for (const metric of ["weight", "waist"]) {
        const field = metric === "weight" ? "weight_kg" : "waist_cm";
        const canonical = entry && draft[metric] === oldDisplay(entry[field], metric) ? entry[field] : draft[metric] === "" ? null : Number(draft[metric]) / oldFactor(metric);
        app.querySelector(`#log-${metric}`).value = measurementDisplay(canonical, metric);
      }
      const unchangedRepeats = draft.repeats === (entry?.waist_readings || []).map((v) => oldDisplay(v, "waist")).join(", ");
      app.querySelector("#log-repeats").value = unchangedRepeats ? (entry?.waist_readings || []).map((v) => measurementDisplay(v, "waist")).join(", ") : draft.repeats ? draft.repeats.split(/[,;\s]+/).map((v) => measurementDisplay(Number(v) / oldFactor("waist"), "waist")).join(", ") : "";
    }
    msg.className = "msg ok"; msg.textContent = "Settings saved ✓";
  } catch (err) { msg.className = "msg error"; msg.textContent = err.message; }
}
async function deleteMeasurement(id) {
  const msg = document.getElementById("history-msg");
  try {
    await api("DELETE", `/api/v1/measurements/${id}`); undoMeasurementId = id;
    await refreshDashboard(document.getElementById("app"));
    if (editingMeasurement?.id === id) { editingMeasurement = null; loadMeasurementDate(); }
    document.getElementById("undo-delete").hidden = false; msg.textContent = "Entry deleted. You can undo this deletion.";
  } catch (err) { msg.textContent = err.message; }
}
async function undoMeasurementDeletion() {
  const msg = document.getElementById("history-msg");
  try {
    await api("POST", `/api/v1/measurements/${undoMeasurementId}/restore`);
    undoMeasurementId = null; document.getElementById("undo-delete").hidden = true;
    await refreshDashboard(document.getElementById("app")); loadMeasurementDate(); msg.textContent = "Entry restored.";
  } catch (err) { msg.textContent = err.message; }
}
async function exportMeasurementCSV() {
  const msg = document.getElementById("import-msg");
  try {
    const result = await api("GET", "/api/v1/measurements/export");
    const url = URL.createObjectURL(new Blob([result.csv_text], {type: "text/csv;charset=utf-8"}));
    const link = document.createElement("a"); link.href = url; link.download = `measurements-${localDate()}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    msg.textContent = "Exported all active measurements in kg/cm.";
  } catch (err) { msg.textContent = err.message; }
}
async function previewMeasurementImport(e) {
  e.preventDefault(); importPreview = null;
  const msg = document.getElementById("import-msg"), confirm = document.getElementById("confirm-import"), list = document.getElementById("import-preview");
  confirm.hidden = true; list.replaceChildren();
  try {
    const file = document.getElementById("import-file").files[0];
    if (!file || file.size > 1000000) throw new Error("Choose a CSV file no larger than 1 MB.");
    const body = {csv_text: await file.text(), conflict: document.getElementById("import-conflict").value, dry_run: true};
    const result = await api("POST", "/api/v1/measurements/import", body);
    if (document.getElementById("import-file").files[0] !== file || document.getElementById("import-conflict").value !== body.conflict) return;
    importPreview = body;
    msg.textContent = `Preview: ${result.created} new, ${result.updated} updated, ${result.skipped} kept. Nothing changed yet. Deleted entries are always kept deleted.`;
    for (const row of result.preview) { const li = document.createElement("li"); li.textContent = `${row.date}: ${row.action}`; list.append(li); }
    confirm.hidden = result.created + result.updated === 0;
  } catch (err) { msg.textContent = err.message; }
}
async function commitMeasurementImport() {
  if (!importPreview) return;
  const button = document.getElementById("confirm-import"), msg = document.getElementById("import-msg"); button.disabled = true;
  try {
    const result = await api("POST", "/api/v1/measurements/import", {...importPreview, dry_run: false});
    importPreview = null; button.hidden = true;
    await refreshDashboard(document.getElementById("app")); loadMeasurementDate();
    msg.textContent = `Imported: ${result.created} new, ${result.updated} updated, ${result.skipped} kept.`;
  } catch (err) { msg.textContent = err.message; }
  finally { button.disabled = false; }
}

async function loadDeletedMeasurements() {
  const msg = document.getElementById("deleted-msg"), list = document.getElementById("deleted-list");
  try {
    const rows = await api("GET", "/api/v1/measurements/deleted");
    list.replaceChildren(); msg.textContent = rows.length ? `${rows.length} deleted entries` : "No deleted entries.";
    for (const row of rows) {
      const li = document.createElement("li"), button = document.createElement("button");
      li.textContent = `${row.date}: weight ${measurementDisplay(row.weight_kg, "weight") || "—"} ${measurementUnit("weight")}, waist ${measurementDisplay(row.waist_cm, "waist") || "—"} ${measurementUnit("waist")} `;
      button.type = "button"; button.className = "small secondary"; button.textContent = "Restore";
      button.onclick = async () => {
        button.disabled = true;
        try {
          await api("POST", `/api/v1/measurements/${row.id}/restore`);
          await refreshDashboard(document.getElementById("app")); await loadDeletedMeasurements();
          if (undoMeasurementId === row.id) { undoMeasurementId = null; document.getElementById("undo-delete").hidden = true; }
        } catch (err) { msg.textContent = err.message; button.disabled = false; }
      };
      li.append(button); list.append(li);
    }
  } catch (err) { msg.textContent = err.message; }
}
