/* ═════════════ Módulo: Triedro de Frenet ═════════════ */
const E = R.entrada, P0 = R.en_t0, TL = E.parametro_latex, T0L = E.t0_latex;
const CT = COLOR.ac, CN = COLOR.min, CB = COLOR.sing;          // T terracota · N petróleo · B ocre
const tieneN = !!(P0 && P0.N);
const vl = v => v ? v.latex : "\\text{no definido}";
const cl = v => v ? v.componentes_latex : ["", "", ""];
const vmat = (f2, f3) => "\\begin{vmatrix} \\mathbf{i} & \\mathbf{j} & \\mathbf{k} \\\\ " + f2.join(" & ") + " \\\\ " + f3.join(" & ") + " \\end{vmatrix}";
const vmat3 = (a, b, c) => "\\begin{vmatrix} " + a.join(" & ") + " \\\\ " + b.join(" & ") + " \\\\ " + c.join(" & ") + " \\end{vmatrix}";
const dT = (n) => R.derivadas[n - 1].vector;
const approx = v => v && v.num ? "\\approx \\left(" + v.num.map(x => fmt(x, 4)).join(",\\ ") + "\\right)" : "";

$id("enunciado").innerHTML = tex("\\mathbf{r}(" + TL + ") = " + E.r_latex + "\\qquad " + TL + "_0 = " + T0L);
$id("meta").innerHTML = `<span>curva: ${esc(R.tipo)}</span><span>parámetro ${esc(E.parametro)}</span>` +
  (Object.keys(E.constantes).length ? `<span>constantes: ${Object.entries(E.constantes).map(([k, v]) => k + " = " + v).join(", ")} (gráficos)</span>` : "") +
  `<span>longitud en el rango ≈ ${fmt(D.longitud_rango, 5)}</span>`;

/* ─────────── 1. Resumen ─────────── */
INIT.resumen = () => {
  const n = x => x ? fmt(x.num, 5) : "—";
  const K = [[esc(R.tipo), "tipo de curva", COLOR.ac], [n(P0.curvatura), `curvatura κ(${esc(E.t0)})`, CT],
             [tieneN ? n(P0.torsion) : "—", `torsión τ(${esc(E.t0)})`, CN], [tieneN ? n(P0.radio_curvatura) : "∞", "radio de curvatura ρ", CB],
             [n(P0.rapidez), "rapidez ‖r′(t₀)‖", COLOR.silla]];
  let h = `<div class="kpis">${K.map(([v, t, c]) => `<div class="kpi" style="--c:${c}"><b style="font-size:${String(v).length > 10 ? 20 : 30}px">${v}</b><span>${t}</span></div>`).join("")}</div>`;
  h += `<div class="grid2"><div class="card"><h2>Triedro de Frenet en t₀ = ${esc(E.t0)}</h2><p class="sub">Base ortonormal móvil: T apunta hacia donde avanza la curva, N hacia donde se curva y B = T × N es perpendicular al plano en que se curva.</p><table class="kv">
    <tr><td>punto</td><td>${tex("\\mathbf r(" + T0L + ") = " + vl(P0.punto))}</td></tr>
    <tr><td><b style="color:${CT}">T</b> tangente</td><td>${tex(vl(P0.T))}<div class="nota">${tex(approx(P0.T))}</div></td></tr>
    <tr><td><b style="color:${CN}">N</b> normal</td><td>${tex(vl(P0.N))}<div class="nota">${tex(approx(P0.N))}</div></td></tr>
    <tr><td><b style="color:${CB}">B</b> binormal</td><td>${tex(vl(P0.B))}<div class="nota">${tex(approx(P0.B))}</div></td></tr></table></div>
    <div class="card"><h2>Curvatura y torsión</h2><p class="sub">κ mide cuánto se dobla la curva; τ, cuánto se “retuerce” fuera de su plano.</p><table class="kv">
    <tr><td>κ(t)</td><td>${tex("\\kappa(" + TL + ") = " + R.curvatura.latex)}</td></tr>
    ${R.torsion ? `<tr><td>τ(t)</td><td>${tex("\\tau(" + TL + ") = " + R.torsion.latex)}</td></tr>` : ""}
    <tr><td>en t₀</td><td>${tex("\\kappa = " + (P0.curvatura ? P0.curvatura.latex : "0") + (tieneN ? ",\\quad \\tau = " + P0.torsion.latex : ""))}</td></tr>
    ${tieneN ? `<tr><td>círculo osculador</td><td>${tex("\\rho = " + P0.radio_curvatura.latex + ",\\quad C = " + P0.centro_curvatura.latex)}</td></tr>` : ""}
    ${R.longitud_arco.s_t_latex ? `<tr><td>longitud de arco</td><td>${tex("s(" + TL + ") = " + R.longitud_arco.s_t_latex)}</td></tr>` : ""}</table></div></div>`;
  if (P0.planos) {
    const fila = (k, nom, perp, col) => P0.planos[k] ? `<tr><td><span class="chip" style="--c:${col}">${nom}</span></td><td>⟂ ${perp}</td><td>${tex(P0.planos[k].ecuacion_latex)}</td></tr>` : "";
    h += `<div class="card"><h2>Planos fundamentales en t₀</h2><table class="kv">${fila("osculador", "osculador", "B (contiene T y N)", CB)}${fila("normal", "normal", "T (contiene N y B)", CT)}${fila("rectificante", "rectificante", "N (contiene T y B)", CN)}</table></div>`;
  }
  const V = R.verificacion;
  h += `<div class="grid2"><div class="card"><h2>Clasificación</h2>${R.clasificacion.map(c => `<p>${esc(c)}</p>`).join("")}` +
    (R.puntos_singulares.length ? `<p>Puntos singulares: ${R.puntos_singulares.map(p => tex(TL + " = " + p.latex)).join(", ")}</p>` : "") +
    (R.puntos_inflexion.length ? `<p>Puntos de inflexión (κ = 0): ${R.puntos_inflexion.map(p => tex(TL + " = " + p.latex)).join(", ")}</p>` : "") + `</div>`;
  h += `<div class="card"><h2>Verificación independiente</h2>` + (V.frenet_serret_t0 ? `<table class="kv">` +
    Object.entries(V.frenet_serret_t0).map(([k, e]) => `<tr><td>${esc(k)}</td><td>error ${e.toExponential(1)} ${e < 1e-25 ? "✔" : "✘"}</td></tr>`).join("") +
    `<tr><td>T, N, B ortonormales, T × N = B</td><td>${V.correcto ? "✔" : "✘"}</td></tr></table><p class="nota">${esc(V.metodo || "")}</p>` : `<p class="nota">No aplica en este punto.</p>`) + `</div></div>`;
  if (R.advertencias.length) h += `<div class="card"><h2>Advertencias</h2>${R.advertencias.map(a => `<p class="warn">⚠ ${esc(a)}</p>`).join("")}</div>`;
  $id("tab-resumen").innerHTML = h;
};

/* ─────────── 2. Procedimiento ─────────── */
INIT.proc = () => {
  let h = `<div class="card" style="margin-bottom:22px"><h2>Procedimiento completo</h2><p class="sub" style="margin:0">Cada paso reproduce el cálculo exacto de SymPy. Las fórmulas valen para cualquier parametrización regular (no hace falta que sea por longitud de arco).</p></div>`, k = 0;
  const paso = (t, c) => h += `<div class="paso"><div class="num">${++k}</div><div class="cuerpo"><h3>${mt(t)}</h3>${c}</div></div>`;
  paso("Curva parametrizada", eq("\\mathbf r(" + TL + ") = " + E.r_latex) +
    (E.curva_plana_entrada ? `<p class="nota">Se ingresaron 2 componentes: la curva se trata en ℝ³ con z = 0.</p>` : "") +
    `<p>${mt("Punto de estudio: $" + TL + "_0 = " + T0L + "$, que da $\\mathbf r(" + T0L + ") = " + vl(P0.punto) + "$.")}</p>`);
  paso("Derivadas sucesivas", eq("\\begin{aligned} \\mathbf r'(" + TL + ") &= " + vl(dT(1)) + "\\\\[8pt] \\mathbf r''(" + TL + ") &= " + vl(dT(2)) +
    "\\\\[8pt] \\mathbf r'''(" + TL + ") &= " + vl(dT(3)) + "\\end{aligned}"));
  let s = eq("\\lVert \\mathbf r'(" + TL + ")\\rVert = \\sqrt{" + cl(dT(1)).map(c => "\\left(" + c + "\\right)^{2}").join(" + ") + "} = " + R.rapidez.latex);
  s += `<p>${mt("Es la **rapidez** con que se recorre la curva; el elemento de longitud de arco es $ds = \\lVert \\mathbf r'\\rVert\\, d" + TL + "$.")}</p>`;
  if (R.longitud_arco.s_t_latex) s += eq("s(" + TL + ") = \\int_{" + T0L + "}^{" + TL + "} \\lVert \\mathbf r'(u)\\rVert\\, du = " + R.longitud_arco.s_t_latex);
  paso("Rapidez y longitud de arco", s);
  paso("Vector tangente unitario $\\mathbf T$", eq("\\mathbf T = \\frac{\\mathbf r'}{\\lVert \\mathbf r'\\rVert} = " + vl(R.T)));
  paso("Producto vectorial $\\mathbf r' \\times \\mathbf r''$", eq("\\mathbf r' \\times \\mathbf r'' = " + vmat(cl(dT(1)), cl(dT(2))) + " = " + vl(R.producto_cruz)) +
    eq("\\lVert \\mathbf r' \\times \\mathbf r''\\rVert = " + R.norma_cruz.latex) +
    `<p class="nota">${mt("Si $\\mathbf r' \\times \\mathbf r'' = \\mathbf 0$ la curva no se dobla en ese punto (recta o inflexión) y $\\mathbf N$, $\\mathbf B$ no existen.")}</p>`);
  if (R.B) {
    paso("Vector binormal $\\mathbf B$", eq("\\mathbf B = \\frac{\\mathbf r' \\times \\mathbf r''}{\\lVert \\mathbf r' \\times \\mathbf r''\\rVert} = " + vl(R.B)));
    paso("Vector normal principal $\\mathbf N$", `<p>${mt("Se usa $\\mathbf N = \\mathbf B \\times \\mathbf T$; con la identidad del doble producto vectorial queda una fórmula sin normalizar dos veces:")}</p>` +
      eq("\\mathbf N = \\frac{(\\mathbf r' \\times \\mathbf r'') \\times \\mathbf r'}{\\lVert \\mathbf r' \\times \\mathbf r''\\rVert\\,\\lVert \\mathbf r'\\rVert} = \\frac{(\\mathbf r'\\cdot\\mathbf r')\\,\\mathbf r'' - (\\mathbf r'\\cdot\\mathbf r'')\\,\\mathbf r'}{\\lVert \\mathbf r' \\times \\mathbf r''\\rVert\\,\\lVert \\mathbf r'\\rVert}") +
      eq("(\\mathbf r'\\cdot\\mathbf r')\\,\\mathbf r'' - (\\mathbf r'\\cdot\\mathbf r'')\\,\\mathbf r' = " + vl(R.N_numerador)) + eq("\\mathbf N = " + vl(R.N)));
  }
  paso("Curvatura $\\kappa$", eq("\\kappa(" + TL + ") = \\frac{\\lVert \\mathbf r' \\times \\mathbf r''\\rVert}{\\lVert \\mathbf r'\\rVert^{3}} = " + R.curvatura.latex));
  if (R.torsion) paso("Torsión $\\tau$", `<p>${mt("El numerador es el **triple producto escalar**, que es el determinante formado por $\\mathbf r'$, $\\mathbf r''$ y $\\mathbf r'''$:")}</p>` +
    eq("(\\mathbf r' \\times \\mathbf r'')\\cdot \\mathbf r''' = " + vmat3(cl(dT(1)), cl(dT(2)), cl(dT(3))) + " = " + R.triple_producto.latex) +
    eq("\\tau(" + TL + ") = \\frac{(\\mathbf r' \\times \\mathbf r'')\\cdot \\mathbf r'''}{\\lVert \\mathbf r' \\times \\mathbf r''\\rVert^{2}} = " + R.torsion.latex));
  let e = eq("\\begin{aligned} \\mathbf r'(" + T0L + ") &= " + vl(P0.d1) + "\\\\ \\mathbf r''(" + T0L + ") &= " + vl(P0.d2) + "\\\\ \\mathbf r'''(" + T0L + ") &= " + vl(P0.d3) + "\\end{aligned}");
  e += eq("\\lVert \\mathbf r'(" + T0L + ")\\rVert = " + (P0.rapidez ? P0.rapidez.latex : "0") + ",\\qquad \\mathbf T(" + T0L + ") = " + vl(P0.T));
  if (tieneN) e += eq("\\mathbf r' \\times \\mathbf r'' \\,(" + T0L + ") = " + vl(P0.cruz) + ",\\qquad \\lVert\\cdot\\rVert = " + P0.norma_cruz.latex) +
    eq("\\mathbf N(" + T0L + ") = " + vl(P0.N) + ",\\qquad \\mathbf B(" + T0L + ") = " + vl(P0.B)) + eq(P0.calculo_kappa_latex) + eq(P0.calculo_tau_latex) +
    `<p>${mt("**Círculo osculador:** es el círculo que mejor aproxima a la curva en $" + TL + "_0$. Radio $\\rho = 1/\\kappa$ y centro sobre la normal:")}</p>` +
    eq("\\rho = \\frac{1}{\\kappa} = " + P0.radio_curvatura.latex + ",\\qquad C = \\mathbf r(" + T0L + ") + \\rho\\,\\mathbf N(" + T0L + ") = " + vl(P0.centro_curvatura));
  paso("Evaluación en $" + TL + "_0 = " + T0L + "$", e);
  if (P0.planos) {
    const pl = (k, nom, n, col) => P0.planos[k] ? `<div class="idea" style="border-color:${col}"><b style="color:${col}">Plano ${nom}</b> — ${mt("normal $\\propto " + n + "$:")}` +
      eq("\\mathbf n = " + P0.planos[k].normal_latex + ",\\qquad \\mathbf n \\cdot (\\mathbf X - \\mathbf r(" + T0L + ")) = 0 \\;\\Longrightarrow\\; " + P0.planos[k].ecuacion_latex) + `</div>` : "";
    paso("Planos fundamentales", `<p>${mt("Cada plano pasa por $\\mathbf r(" + TL + "_0)$ y es perpendicular a uno de los vectores del triedro (se usa un múltiplo del vector con coeficientes simples):")}</p>` +
      pl("osculador", "osculador (contiene T y N)", "\\mathbf B \\propto \\mathbf r'\\times\\mathbf r''", CB) +
      pl("normal", "normal (contiene N y B)", "\\mathbf T \\propto \\mathbf r'", CT) +
      pl("rectificante", "rectificante (contiene T y B)", "\\mathbf N \\propto (\\mathbf r'\\times\\mathbf r'')\\times\\mathbf r'", CN));
  }
  if (R.verificacion.frenet_serret_t0) paso("Fórmulas de Frenet–Serret (verificación)",
    eq("\\begin{pmatrix} \\mathbf T' \\\\ \\mathbf N' \\\\ \\mathbf B' \\end{pmatrix} = \\lVert \\mathbf r'\\rVert \\begin{pmatrix} 0 & \\kappa & 0 \\\\ -\\kappa & 0 & \\tau \\\\ 0 & -\\tau & 0 \\end{pmatrix} \\begin{pmatrix} \\mathbf T \\\\ \\mathbf N \\\\ \\mathbf B \\end{pmatrix}") +
    `<p>${mt("Se comprobaron en $" + TL + "_0$ con 50 dígitos, derivando $\\mathbf T$, $\\mathbf N$, $\\mathbf B$ numéricamente (de forma independiente de las fórmulas anteriores):")}</p><table class="kv" style="max-width:520px">` +
    Object.entries(R.verificacion.frenet_serret_t0).map(([q, er]) => `<tr><td>${esc(q)}</td><td>error = ${er.toExponential(1)} ${er < 1e-25 ? "✔" : "✘"}</td></tr>`).join("") + `</table>`);
  paso("Clasificación de la curva", R.clasificacion.map(c => `<p>${esc(c)}</p>`).join("") +
    `<div class="idea">${mt("**Teorema fundamental de curvas:** $\\kappa(s)$ y $\\tau(s)$ determinan la curva salvo movimientos rígidos. $\\tau \\equiv 0$ ⇔ curva plana; $\\kappa$ y $\\tau$ constantes ⇔ hélice circular; $\\tau/\\kappa$ constante ⇔ hélice generalizada (Lancret).")}</div>` +
    R.advertencias.map(a => `<p class="warn">⚠ ${esc(a)}</p>`).join(""));
  $id("tab-proc").innerHTML = h;
};

/* ─────────── 3. Gráfico 3D dinámico ─────────── */
const arr = a => a.map(v => v === null ? NaN : v);
const nPts = D.t.length;
const pt = i => [D.x[i], D.y[i], D.z[i]];
const vec3 = (M, i) => [M[0][i], M[1][i], M[2][i]];
const suma = (a, b, s) => a.map((q, j) => q + s * b[j]);
const valido = v => v.every(q => q !== null && isFinite(q));

INIT.g3d = () => {
  const P = $id("tab-g3d");
  const L = 0.2 * D.diag;
  P.innerHTML = `<div class="card"><h2>El triedro de Frenet recorriendo la curva</h2>
    <p class="sub">La curva está coloreada según su curvatura κ (más claro = se dobla más). Al reproducir, el triedro <b style="color:${CT}">T</b>, <b style="color:${CN}">N</b>, <b style="color:${CB}">B</b> viaja por la curva; el círculo punteado es el círculo osculador (el que mejor la aproxima) y los planos se mueven con el punto.</p>
    <div class="visor"><div id="g3" class="plot alto"></div><div class="ctrl">
      <div class="bloque"><label class="t">Recorrer la curva</label><div class="fila"><button class="btn pri" id="bFr">▶ Reproducir</button><button class="btn" id="bT0">ir a t₀</button></div>
        <input type="range" id="sFr" min="0" max="${nPts - 1}" value="${D.t0.indice}"><div class="lectura" id="lFr"></div></div>
      <div class="bloque"><label class="t">κ(t) y τ(t)</label><div id="perfil" class="plot bajo"></div></div>
      <div class="bloque"><label class="t">Mostrar</label>
        <label class="chk"><input type="checkbox" id="cTri" checked> triedro T, N, B</label>
        <label class="chk"><input type="checkbox" id="cCir" checked> círculo osculador</label>
        <label class="chk"><input type="checkbox" id="cPO" checked> plano osculador <i style="color:${CB}">●</i></label>
        <label class="chk"><input type="checkbox" id="cPN"> plano normal <i style="color:${CT}">●</i></label>
        <label class="chk"><input type="checkbox" id="cPR"> plano rectificante <i style="color:${CN}">●</i></label>
        <label class="chk"><input type="checkbox" id="cEvo"> evoluta (centros de curvatura)</label>
        <label class="t" style="margin-top:10px">Color de la curva</label><select id="sCol"><option value="kappa">curvatura κ</option><option value="tau">torsión τ</option><option value="rapidez">rapidez ‖r′‖</option></select></div>
    </div></div></div>`;
  const X = arr(D.x), Y = arr(D.y), Z = arr(D.z);
  const tr = [];
  tr.push({type:"scatter3d", mode:"lines", x:X, y:Y, z:Z, name:"r(t)", hoverinfo:"skip",
    line:{width:8, color:arr(D.kappa), colorscale:TERRA, showscale:true, colorbar:{title:{text:"κ"}, thickness:12, len:0.55, x:1.0}}});
  tr.push({type:"scatter3d", mode:"lines", x:arr(D.centro[0]), y:arr(D.centro[1]), z:arr(D.centro[2]), line:{color:CN, width:3, dash:"dot"}, name:"evoluta", visible:false, hoverinfo:"skip"});
  const I0 = tr.length;                      // 0..2: ejes T N B · 3..5: conos · 6: círculo · 7..9: planos · 10: punto
  [["T", CT], ["N", CN], ["B", CB]].forEach(([nm, c]) => tr.push({type:"scatter3d", mode:"lines+text", x:[0, 0], y:[0, 0], z:[0, 0], text:["", nm],
    textposition:"top center", textfont:{color:c, size:15}, line:{color:c, width:9}, name:nm, hoverinfo:"skip"}));
  [CT, CN, CB].forEach(c => tr.push({type:"cone", x:[0], y:[0], z:[0], u:[1], v:[0], w:[0], anchor:"tip", sizemode:"absolute", sizeref:L * 0.28,
    colorscale:[[0, c], [1, c]], showscale:false, hoverinfo:"skip", name:"", showlegend:false}));
  tr.push({type:"scatter3d", mode:"lines", x:[], y:[], z:[], line:{color:CN, width:4, dash:"dash"}, name:"círculo osculador", hoverinfo:"skip"});
  [[CB, "plano osculador", true], [CT, "plano normal", false], [CN, "plano rectificante", false]].forEach(([c, nm, vis]) =>
    tr.push({type:"mesh3d", x:[0, 0, 0, 0], y:[0, 0, 0, 0], z:[0, 0, 0, 0], i:[0, 0], j:[1, 2], k:[2, 3], color:c, opacity:0.28, name:nm, visible:vis, hoverinfo:"skip", flatshading:true}));
  tr.push({type:"scatter3d", mode:"markers", x:[0], y:[0], z:[0], marker:{size:7, color:"#fff", line:{color:"#2b2420", width:3}}, name:"punto", hoverinfo:"skip"});
  if (D.t0.r) tr.push({type:"scatter3d", mode:"markers+text", x:[D.t0.r[0]], y:[D.t0.r[1]], z:[D.t0.r[2]], text:["t₀"], textposition:"bottom center",
    textfont:{color:COLOR.tx, size:13}, marker:{size:5, color:COLOR.tx}, name:"t₀", hoverinfo:"skip"});
  // rango y proporciones que respetan la geometría (con un mínimo para curvas planas)
  const lim = (A) => { const f = A.filter(isFinite); return [Math.min(...f) - L * 1.2, Math.max(...f) + L * 1.2]; };
  const rx = lim(X), ry = lim(Y), rz = lim(Z), ex = [rx, ry, rz].map(r => r[1] - r[0]), m = Math.max(...ex);
  const ar = ex.map(e => Math.max(e / m, 0.3));
  const g3 = reg("g3d", $id("g3"));
  Plotly.newPlot(g3, tr, lay({margin:{l:0, r:0, t:10, b:0}, legend:{orientation:"h", y:0.02, x:0.02},
    scene:{xaxis:Object.assign(ejes3("x"), {range:rx}), yaxis:Object.assign(ejes3("y"), {range:ry}), zaxis:Object.assign(ejes3("z"), {range:rz}),
           aspectmode:"manual", aspectratio:{x:ar[0] * 1.2, y:ar[1] * 1.2, z:ar[2] * 1.2}, camera:{eye:{x:1.15, y:-1.15, z:0.75}}}}), CFG);
  // perfil κ, τ
  const perf = reg("g3d", $id("perfil"));
  const pTr = [{x:D.t, y:D.kappa, mode:"lines", line:{color:CT, width:2.5}, name:"κ"}];
  if (!D.plana) pTr.push({x:D.t, y:D.tau, mode:"lines", line:{color:CN, width:2.5}, name:"τ"});
  pTr.push({x:[D.t[D.t0.indice]], y:[D.kappa[D.t0.indice]], mode:"markers", marker:{size:10, color:"#fff", line:{color:"#2b2420", width:2.5}}, showlegend:false});
  const vline = x => ({type:"line", x0:x, x1:x, yref:"paper", y0:0, y1:1, line:{color:COLOR.mu, width:1, dash:"dot"}});
  Plotly.newPlot(perf, pTr, lay({margin:{l:36, r:8, t:6, b:28}, legend:{orientation:"h", y:1.15, x:0}, shapes:[vline(D.t[D.t0.indice])],
    xaxis:{title:{text:E.parametro, font:{size:11}}, gridcolor:COLOR.bd}, yaxis:{gridcolor:COLOR.bd, zerolinecolor:COLOR.mu}}), {displayModeBar:false, responsive:true});
  const iPer = pTr.length - 1;
  const mover = i => {
    const p = pt(i), T = vec3(D.T, i), N = vec3(D.N, i), B = vec3(D.B, i), k = D.kappa[i];
    const ok = valido(p) && valido(T), okN = ok && valido(N) && valido(B);
    const fx = [], fy = [], fz = [], cu = [];
    [T, N, B].forEach((v, j) => { const q = (j === 0 ? ok : okN) ? suma(p, v, L) : p; fx.push([p[0], q[0]]); fy.push([p[1], q[1]]); fz.push([p[2], q[2]]);
      cu.push((j === 0 ? ok : okN) ? v : [0, 0, 0]); });
    Plotly.restyle(g3, {x:fx, y:fy, z:fz}, [I0, I0 + 1, I0 + 2]);
    Plotly.restyle(g3, {x:[[fx[0][1]], [fx[1][1]], [fx[2][1]]], y:[[fy[0][1]], [fy[1][1]], [fy[2][1]]], z:[[fz[0][1]], [fz[1][1]], [fz[2][1]]],
      u:cu.map(v => [v[0]]), v:cu.map(v => [v[1]]), w:cu.map(v => [v[2]])}, [I0 + 3, I0 + 4, I0 + 5]);
    // círculo osculador
    let cx = [], cy = [], cz = [];
    const rho = 1 / k, C = vec3(D.centro, i);
    if (okN && isFinite(rho) && valido(C)) for (let a = 0; a <= 96; a++) { const th = 2 * Math.PI * a / 96;
      const q = p.map((_, j) => C[j] + rho * (-Math.cos(th) * N[j] + Math.sin(th) * T[j])); cx.push(q[0]); cy.push(q[1]); cz.push(q[2]); }
    Plotly.restyle(g3, {x:[cx], y:[cy], z:[cz]}, [I0 + 6]);
    // planos: cuadrados centrados en el punto, generados por dos vectores del triedro
    const s = L * 0.95, cuad = (u, v) => [suma(suma(p, u, -s), v, -s), suma(suma(p, u, s), v, -s), suma(suma(p, u, s), v, s), suma(suma(p, u, -s), v, s)];
    const pls = okN ? [cuad(T, N), cuad(N, B), cuad(T, B)] : [[p, p, p, p], [p, p, p, p], [p, p, p, p]];
    Plotly.restyle(g3, {x:pls.map(q => q.map(w => w[0])), y:pls.map(q => q.map(w => w[1])), z:pls.map(q => q.map(w => w[2]))}, [I0 + 7, I0 + 8, I0 + 9]);
    Plotly.restyle(g3, {x:[[p[0]]], y:[[p[1]]], z:[[p[2]]]}, [I0 + 10]);
    Plotly.restyle(perf, {x:[[D.t[i]]], y:[[k]]}, [iPer]); Plotly.relayout(perf, {shapes:[vline(D.t[i])]});
    $id("lFr").innerHTML = `${esc(E.parametro)} = ${fmt(D.t[i], 5)}<br>r = (${p.map(q => fmt(q, 4)).join(", ")})<br>‖r′‖ = ${fmt(D.rapidez[i], 5)}<br>` +
      `<span style="color:${CT}">κ = ${fmt(k, 5)}</span>` + (D.plana ? "" : ` · <span style="color:${CN}">τ = ${fmt(D.tau[i], 5)}</span>`) +
      `<br>ρ = ${okN && isFinite(rho) ? fmt(rho, 5) : "∞"}` + (okN ? "" : `<br><b class="warn">κ = 0: N y B no existen aquí</b>`);
  };
  reproductor($id("bFr"), $id("sFr"), mover, Math.max(1, Math.round(nPts / 320)));
  mover(D.t0.indice);
  $id("bT0").onclick = () => { $id("sFr").value = D.t0.indice; mover(D.t0.indice); };
  $id("cTri").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [I0, I0 + 1, I0 + 2, I0 + 3, I0 + 4, I0 + 5]);
  $id("cCir").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [I0 + 6]);
  [["cPO", 7], ["cPN", 8], ["cPR", 9]].forEach(([id, j]) => $id(id).onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [I0 + j]));
  $id("cEvo").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [1]);
  $id("sCol").onchange = e => { const k = e.target.value;
    Plotly.restyle(g3, {"line.color":[arr(D[k])], "line.colorbar.title.text":[{kappa:"κ", tau:"τ", rapidez:"‖r′‖"}[k]]}, [0]); };
};

/* ─────────── 4. Gráficos 2D ─────────── */
INIT.g2d = () => {
  const P = $id("tab-g2d");
  P.innerHTML = `<div class="grid2"><div class="card"><h2>Curvatura y torsión</h2><p class="sub">La línea vertical marca t₀; los puntos grises, inflexiones (κ = 0).</p><div id="gk" class="plot medio"></div></div>
    <div class="card"><h2>Rapidez ‖r′(t)‖</h2><p class="sub">Área bajo la curva = longitud de arco (≈ ${fmt(D.longitud_rango, 6)} en el rango mostrado).</p><div id="gv" class="plot medio"></div></div></div>
    <div class="card"><h2>Proyecciones en los planos coordenados</h2><p class="sub">Curva coloreada por κ, evoluta punteada y, en t₀, T (terracota) y N (petróleo) proyectados con su círculo osculador.</p><div class="grid2" id="proy"></div></div>`;
  const t0 = D.t0, vl2 = x => ({type:"line", x0:x, x1:x, yref:"paper", y0:0, y1:1, line:{color:COLOR.mu, width:1.2, dash:"dash"}});
  const kt = [{x:D.t, y:D.kappa, mode:"lines", line:{color:CT, width:3}, name:"κ(t)"}];
  if (!D.plana) kt.push({x:D.t, y:D.tau, mode:"lines", line:{color:CN, width:3}, name:"τ(t)"});
  if (D.inflexiones.length) kt.push({x:D.inflexiones, y:D.inflexiones.map(() => 0), mode:"markers", marker:{size:10, color:COLOR.ind}, name:"inflexión"});
  Plotly.newPlot(reg("g2d", $id("gk")), kt, lay({shapes:t0.t !== null ? [vl2(t0.t)] : [], xaxis:{title:{text:E.parametro}, gridcolor:COLOR.bd}, yaxis:{gridcolor:COLOR.bd, zerolinecolor:COLOR.mu}}), CFG);
  Plotly.newPlot(reg("g2d", $id("gv")), [{x:D.t, y:D.rapidez, mode:"lines", fill:"tozeroy", fillcolor:"rgba(176,80,44,.15)", line:{color:CT, width:3}, name:"‖r′‖"}],
    lay({shapes:t0.t !== null ? [vl2(t0.t)] : [], xaxis:{title:{text:E.parametro}, gridcolor:COLOR.bd}, yaxis:{gridcolor:COLOR.bd, rangemode:"tozero"}}), CFG);
  const L = 0.16 * D.diag, C3 = [D.x, D.y, D.z];
  [[0, 1], [0, 2], [1, 2]].forEach(([a, b]) => {
    const d = document.createElement("div"); d.className = "plot medio"; $id("proy").appendChild(d);
    const nm = ["x", "y", "z"], tr = [{type:"scatter", mode:"markers", x:C3[a], y:C3[b], marker:{size:3.5, color:arr(D.kappa), colorscale:TERRA}, name:"r(t)", hoverinfo:"skip"},
      {type:"scatter", mode:"lines", x:D.centro[a], y:D.centro[b], line:{color:CN, width:1.5, dash:"dot"}, name:"evoluta", hoverinfo:"skip"}];
    if (t0.r && t0.T) {
      const p = t0.r;
      [[t0.T, CT, "T"], [t0.N, CN, "N"]].forEach(([v, c, n]) => { if (v && valido(v)) tr.push({type:"scatter", mode:"lines+markers", x:[p[a], p[a] + L * v[a]], y:[p[b], p[b] + L * v[b]],
        line:{color:c, width:4}, marker:{size:[0, 10], symbol:"arrow", angleref:"previous", color:c}, name:n}); });
      if (t0.N && valido(t0.N) && t0.rho && t0.rho < 3 * D.diag) { const cx = [], cy = [];
        for (let q = 0; q <= 120; q++) { const th = 2 * Math.PI * q / 120; cx.push(t0.centro[a] + t0.rho * (-Math.cos(th) * t0.N[a] + Math.sin(th) * t0.T[a]));
          cy.push(t0.centro[b] + t0.rho * (-Math.cos(th) * t0.N[b] + Math.sin(th) * t0.T[b])); }
        tr.push({type:"scatter", mode:"lines", x:cx, y:cy, line:{color:CN, width:1.5, dash:"dash"}, name:"círculo osculador (proyección)"}); }
      tr.push({type:"scatter", mode:"markers", x:[p[a]], y:[p[b]], marker:{size:10, color:"#fff", line:{color:"#2b2420", width:2}}, name:"r(t₀)"});
    }
    Plotly.newPlot(reg("g2d", d), tr, lay({showlegend:false, title:{text:`plano ${nm[a]}${nm[b]}`, font:{size:13}}, margin:{l:46, r:10, t:40, b:40},
      xaxis:{title:{text:nm[a]}, gridcolor:COLOR.bd}, yaxis:{title:{text:nm[b]}, gridcolor:COLOR.bd, scaleanchor:"x"}}), CFG);
  });
};
