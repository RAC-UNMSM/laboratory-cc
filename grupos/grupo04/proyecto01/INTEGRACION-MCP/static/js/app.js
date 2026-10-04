const state = {
  points: [
    {x: 1, y: 2},
    {x: 2, y: 5},
    {x: 3, y: 10},
    {x: 4, y: 17}
  ],
  lastResult: null
};

const $ = (id) => document.getElementById(id);

function renderPoints() {
  const container = $("pointsContainer");
  container.innerHTML = "";
  state.points.forEach((p, i) => {
    const row = document.createElement("div");
    row.className = "point-row";
    row.innerHTML = `
      <input type="number" step="any" value="${p.x}" data-i="${i}" data-field="x">
      <input type="number" step="any" value="${p.y}" data-i="${i}" data-field="y">
      <button class="remove-point" data-remove="${i}" title="Eliminar punto">♜</button>
    `;
    container.appendChild(row);
  });

  container.querySelectorAll("input").forEach(input => {
    input.addEventListener("input", e => {
      const i = Number(e.target.dataset.i);
      const field = e.target.dataset.field;
      state.points[i][field] = Number(e.target.value);
    });
  });

  container.querySelectorAll("[data-remove]").forEach(btn => {
    btn.addEventListener("click", () => {
      if (state.points.length <= 2) {
        showModal("Validación", "<p>Debes conservar al menos 2 puntos.</p>");
        return;
      }
      state.points.splice(Number(btn.dataset.remove), 1);
      renderPoints();
    });
  });
}

function formatNumber(n) {
  return Number(n).toFixed(4);
}

function displayPolynomial(poly) {
  return poly
    .replace(/\^2/g, "²")
    .replace(/\^3/g, "³")
    .replace(/\^4/g, "⁴")
    .replace(/\^5/g, "⁵");
}

function renderDifferenceTable(rows) {
  const maxOrder = Math.max(...rows.map(r => Object.keys(r).filter(k => k.startsWith("d")).length), 0);
  const headers = ["x", "f(x)", ...Array.from({length: maxOrder}, (_, i) => `Δ${i+1}`)];
  let html = "<thead><tr>" + headers.map(h => `<th>${h}</th>`).join("") + "</tr></thead><tbody>";

  rows.forEach(r => {
    html += "<tr>";
    html += `<td>${formatNumber(r.x).replace(".0000","")}</td>`;
    html += `<td>${formatNumber(r.f)}</td>`;
    for (let k = 1; k <= maxOrder; k++) {
      const v = r[`d${k}`];
      html += `<td>${v === undefined ? "—" : formatNumber(v)}</td>`;
    }
    html += "</tr>";
  });
  html += "</tbody>";
  $("diffTable").innerHTML = html;
}

function renderPlot(result) {
  const pointX = result.points.map(p => p.x);
  const pointY = result.points.map(p => p.y);

  const curve = {
    x: result.curve.x, y: result.curve.y, type: "scatter",
    mode: "lines", name: "Polinomio interpolante",
    line: {color: "#53ef91", width: 3}
  };

  const points = {
    x: pointX, y: pointY, type: "scatter",
    mode: "markers", name: "Puntos originales",
    marker: {color: "#5aa5ff", size: 9, line: {color: "#d5e8ff", width: 1}}
  };

  const evalTrace = {
    x: [Number($("xEval").value)], y: [result.value], type: "scatter",
    mode: "markers+text", name: "Punto de evaluación",
    text: [`(${Number($("xEval").value)}, ${formatNumber(result.value)})`],
    textposition: "top center",
    textfont: {color: "#ff3d62", size: 13},
    marker: {color: "#ff3d62", size: 12, symbol: "star"}
  };

  const layout = {
    title: {text: `Interpolación Polinomial (${result.method})`, font: {color: "#eef5ff", size: 16}},
    paper_bgcolor: "transparent", plot_bgcolor: "#071a36",
    font: {color: "#a9bedc", family: "Segoe UI, Arial"},
    margin: {l: 62, r: 20, t: 62, b: 55},
    xaxis: {title: "x", gridcolor: "#17385e", zerolinecolor: "#365a82", color: "#a9bedc"},
    yaxis: {title: "f(x)", gridcolor: "#17385e", zerolinecolor: "#365a82", color: "#a9bedc"},
    legend: {orientation: "h", y: 1.08, x: 0.02, font: {size: 12}},
    hovermode: "x unified",
    shapes: [{
      type: "line", x0: Number($("xEval").value), x1: Number($("xEval").value),
      y0: 0, y1: result.value, line: {color: "#ff3d62", width: 1, dash: "dash"}
    }]
  };

  Plotly.newPlot("plot", [curve, points, evalTrace], layout, {
    responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d","select2d"]
  });
}

async function calculate() {
  const button = $("calculate");
  button.disabled = true;
  button.innerHTML = "⏳ Calculando...";

  try {
    const response = await fetch("/api/interpolate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        points: state.points,
        x_eval: Number($("xEval").value),
        method: $("method").value,
        report_name: $("reportName").value || "reporte_interpolacion",
        generate_report: true
      })
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "No se pudo calcular.");

    state.lastResult = result;
    renderResult(result);
    renderReportLinks(result.reports);
    saveHistory(result);
  } catch (error) {
    showModal("Error de cálculo", `<p>${error.message}</p>`);
  } finally {
    button.disabled = false;
    button.innerHTML = '<span class="play">▶</span> Calcular';
  }
}

function renderReportLinks(reports) {
  const box = $("reportLinks");
  box.innerHTML = "";
  box.hidden = !reports;
  if (!reports) return;

  if (reports.html_url) {
    const htmlLink = document.createElement("a");
    htmlLink.href = reports.html_url;
    htmlLink.target = "_blank";
    htmlLink.rel = "noopener";
    htmlLink.textContent = "▧ Abrir reporte HTML";
    box.appendChild(htmlLink);
  }

  if (reports.graph_url) {
    const graphLink = document.createElement("a");
    graphLink.href = reports.graph_url;
    graphLink.target = "_blank";
    graphLink.rel = "noopener";
    graphLink.textContent = "▱ Ver gráfica SVG";
    box.appendChild(graphLink);
  }

  if (reports.pdf_url) {
    const pdfLink = document.createElement("a");
    pdfLink.href = reports.pdf_url;
    pdfLink.download = reports.pdf_name || "reporte.pdf";
    pdfLink.textContent = "⇩ Descargar PDF";
    box.appendChild(pdfLink);
  } else {
    const note = document.createElement("span");
    note.className = "report-note";
    note.textContent = "PDF no disponible";
    box.appendChild(note);
  }
}

function renderResult(result) {
  const x = Number($("xEval").value);
  $("bigResult").textContent = `P(${x}) = ${formatNumber(result.value)}`;
  $("methodResult").textContent = result.method;
  $("polyResult").textContent = `P(x) = ${displayPolynomial(result.polynomial)}`;
  $("coeffResult").textContent = `[${result.coefficients.map(c => Number(c.toFixed(6))).join(", ")}]`;
  $("polyBox").textContent = `P(x) = ${displayPolynomial(result.polynomial)}`;

  $("lagValue").textContent = formatNumber(result.lagrange_value);
  $("newValue").textContent = formatNumber(result.newton_value);
  $("lagError").textContent = formatNumber(Math.abs(result.lagrange_value - result.value));
  $("newError").textContent = formatNumber(Math.abs(result.newton_value - result.value));
  $("difference").textContent = formatNumber(result.difference);

  $("matchTitle").textContent = result.difference < 1e-9
    ? "Ambos métodos coinciden"
    : "Los métodos presentan diferencia";

  renderDifferenceTable(result.difference_table);
  renderPlot(result);
}

function saveHistory(result) {
  const history = JSON.parse(localStorage.getItem("interpolacionHistory") || "[]");
  history.unshift({
    date: new Date().toLocaleString("es-PE"),
    method: result.method,
    value: result.value,
    polynomial: result.polynomial,
    points: result.points.length
  });
  localStorage.setItem("interpolacionHistory", JSON.stringify(history.slice(0, 10)));
  renderHistory();
}

function renderHistory() {
  const history = JSON.parse(localStorage.getItem("interpolacionHistory") || "[]");
  const box = $("historyList");
  if (!history.length) {
    box.innerHTML = '<p style="color:#9eb6d5">Todavía no hay cálculos guardados.</p>';
    return;
  }
  box.innerHTML = history.map(item => `
    <div class="history-item">
      <span>${item.date} · ${item.method} · ${item.points} puntos</span>
      <strong>P(x) = ${displayPolynomial(item.polynomial)} → ${formatNumber(item.value)}</strong>
    </div>
  `).join("");
}

function showModal(title, content) {
  $("modalTitle").textContent = title;
  $("modalContent").innerHTML = content;
  $("modal").classList.add("show");
}

function showDetails() {
  if (!state.lastResult) return;
  const r = state.lastResult;
  const basis = r.basis.map((v, i) => `L${i+1}(x_eval) = ${formatNumber(v)}`).join("<br>");
  showModal("Detalles de la interpolación", `
    <div class="details-grid">
      <div class="detail-box"><b>Método seleccionado</b>${r.method}</div>
      <div class="detail-box"><b>Valor calculado</b>${formatNumber(r.value)}</div>
      <div class="detail-box"><b>Polinomio</b><span class="math">P(x) = ${displayPolynomial(r.polynomial)}</span></div>
      <div class="detail-box"><b>Coeficientes</b>[${r.coefficients.map(c => Number(c.toFixed(6))).join(", ")}]</div>
    </div>
    <div class="detail-box" style="margin-top:12px"><b>Pesos de Lagrange en el punto de evaluación</b>${basis}</div>
  `);
}

function showFullTable() {
  if (!state.lastResult) return;
  const r = state.lastResult;
  const maxOrder = r.divided_differences.length - 1;
  let html = `<table><thead><tr><th>x</th><th>f(x)</th>`;
  for (let i = 1; i <= maxOrder; i++) html += `<th>Δ${i}</th>`;
  html += "</tr></thead><tbody>";

  r.difference_table.forEach(row => {
    html += `<tr><td>${formatNumber(row.x)}</td><td>${formatNumber(row.f)}</td>`;
    for (let i = 1; i <= maxOrder; i++) {
      html += `<td>${row[`d${i}`] === undefined ? "—" : formatNumber(row[`d${i}`])}</td>`;
    }
    html += "</tr>";
  });
  html += "</tbody></table>";
  showModal("Tabla completa de diferencias divididas", html);
}

function initNavigation() {
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
      item.classList.add("active");
      const target = item.dataset.target;

      if (target === "historial") {
        $("historial").style.display = "block";
        $("historial").scrollIntoView({behavior: "smooth"});
      } else if (target === "ayuda") {
        showModal("Ayuda", `
          <p>1. Ingresa los pares (x, y).</p>
          <p>2. Selecciona Lagrange o Newton.</p>
          <p>3. Indica el valor de x que quieres evaluar.</p>
          <p>4. Pulsa <b>Calcular</b> para actualizar el polinomio, la gráfica,
          la tabla de diferencias y la comparación.</p>
        `);
      } else {
        $("historial").style.display = "none";
        document.getElementById(target)?.scrollIntoView({behavior: "smooth"});
      }
    });
  });
}

async function checkServer() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    if (!data.mcp && !Array.isArray(data.mcp_tools)) throw new Error();
    $("statusDot").style.background = "#54f29a";
    $("statusText").textContent = "INTERPOLA-MCP y MCP-TEST integrados";
  } catch {
    $("statusDot").style.background = "#ff3d62";
    $("statusText").textContent = "Servidor desconectado";
  }
}

$("addPoint").addEventListener("click", () => {
  const last = state.points[state.points.length - 1];
  state.points.push({x: Number(last.x) + 1, y: Number(last.y) + 2});
  renderPoints();
});

$("calculate").addEventListener("click", calculate);
$("showDetails").addEventListener("click", showDetails);
$("showFullTable").addEventListener("click", showFullTable);
$("closeModal").addEventListener("click", () => $("modal").classList.remove("show"));
$("modal").addEventListener("click", e => {
  if (e.target === $("modal")) $("modal").classList.remove("show");
});
$("btnSettings").addEventListener("click", () => showModal("INTERPOLA-MCP", `
  <p><b>Proyectos integrados:</b></p>
  <p>• <b>INTERPOLA-MCP:</b> interfaz web y motor de interpolación Newton/Lagrange.</p>
  <p>• <b>MCP-TEST:</b> herramientas MCP y generación de informes HTML/PDF.</p>
  <p><b>Backend:</b> Python + Flask.</p>
  <p><b>Servidor MCP:</b> herramientas disponibles en <code>mcp_server.py</code>.</p>
  <p><b>Informes:</b> HTML autónomo y PDF opcional, guardados en <code>reports/</code>.</p>
  <p><b>Despliegue:</b> la interfaz web y el servidor MCP pueden iniciarse por separado.</p>
`));

renderPoints();
renderHistory();
checkServer();
calculate();
