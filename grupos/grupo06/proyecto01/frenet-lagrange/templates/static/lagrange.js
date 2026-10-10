/* ═════════════ Módulo: Multiplicadores de Lagrange ═════════════ */
const E = R.entrada, V = E.variables, VT = R.variables_latex, LT = R.lambdas_latex;
const CORTO = {"máximo local condicionado":"máximo local", "mínimo local condicionado":"mínimo local",
               "punto de silla condicionado (no es extremo)":"silla condicionada"};
const COLCL = {"máximo local condicionado":COLOR.max, "mínimo local condicionado":COLOR.min,
               "punto de silla condicionado (no es extremo)":COLOR.silla};
const colorDe = p => p.tipo === "singular" ? COLOR.sing : (COLCL[p.clasificacion] || COLOR.ind);
const corto = p => p.tipo === "singular" ? "punto singular" : (CORTO[p.clasificacion] || "no concluyente");
const TODOS = R.puntos_criticos.map((p, i) => Object.assign({id:"P" + (i + 1)}, p))
  .concat(R.puntos_singulares.map((p, i) => Object.assign({id:"S" + (i + 1)}, p)));
const ptTex = p => "\\left(" + V.map(v => p.coordenadas_latex[v]).join(",\\ ") + "\\right)";
const idTex = id => id.replace(/(\d+)/, "_{$1}");
const VARS = VT.join(",\\,");
const hov = p => `<b>${p.id}</b> ${p.etiqueta}<br>f = ${fmt(p.f, 6)}<br>${corto(p)}`;

$id("enunciado").innerHTML = tex("\\operatorname{optimizar}\\; f(" + VARS + ") = " + E.f_latex +
  "\\qquad \\text{sujeto a}\\qquad " + E.restricciones_latex.join(",\\quad "));
$id("meta").innerHTML = `<span>${E.n} variables</span><span>${E.m} restricción(es)</span><span>${esc(R.metodo_resolucion)}</span><span>${TODOS.length} candidato(s)</span>`;

/* ─────────── 1. Resumen ─────────── */
INIT.resumen = () => {
  const cnt = c => R.puntos_criticos.filter(p => p.clasificacion === c).length;
  const nmax = cnt("máximo local condicionado"), nmin = cnt("mínimo local condicionado");
  const K = [[TODOS.length, "candidatos analizados", COLOR.ac], [nmax, "máximos locales", COLOR.max],
             [nmin, "mínimos locales", COLOR.min], [R.puntos_criticos.length - nmax - nmin, "sillas / no concluyentes", COLOR.silla],
             [R.puntos_singulares.length, "puntos singulares", COLOR.sing]];
  let h = `<div class="kpis">${K.map(([n, t, c]) => `<div class="kpi" style="--c:${c}"><b>${n}</b><span>${t}</span></div>`).join("")}</div>`;
  h += `<div class="card"><h2>Puntos críticos</h2><p class="sub">Soluciones reales de ∇𝓛 = 0 y puntos singulares de la restricción, con su clasificación exacta.</p><div class="pts">`;
  TODOS.forEach(p => {
    h += `<div class="pt" style="--c:${colorDe(p)}"><div class="cab"><div><b>${p.id}</b>&nbsp; ${tex(ptTex(p))}</div><span class="chip">${corto(p)}</span></div><table class="kv">`;
    const lam = Object.entries(p.lambdas_latex || {}).map(([k, v]) => tex(k + " = " + v)).join(", ");
    if (lam) h += `<tr><td>multiplicador</td><td>${lam}</td></tr>`;
    h += `<tr><td>valor de f</td><td>${tex(p.valor_f_latex)} <span class="nota">≈ ${fmt(p.valor_f_num, 6)}</span></td></tr>`;
    if ((p.menores_orlados || []).length) h += `<tr><td>menores orlados</td><td>${p.menores_orlados.map(m => tex("\\Delta_{" + m.orden + "} = " + m.valor_latex)).join(", ")}</td></tr>`;
    const vt = p.verificacion_tangente;
    if (vt && vt.coincide !== undefined) h += `<tr><td>verificación</td><td>${vt.coincide ? "✔ coincide (espacio tangente)" : "✘ difiere"}</td></tr>`;
    if (p.comparacion_global) h += `<tr><td>global</td><td><b>${esc(p.comparacion_global)}</b></td></tr>`;
    h += `</table></div>`;
  });
  if (!TODOS.length) h += `<p>No se hallaron puntos críticos reales.</p>`;
  h += `</div></div>`;
  const conv = TODOS.filter(p => p.valor_f_num !== null);
  if (conv.length) {
    const vs = conv.map(p => p.valor_f_num), lo = Math.min(...vs), rg = (Math.max(...vs) - lo) || 1;
    h += `<div class="card"><h2>Comparación de valores de f</h2><p class="sub">${esc(R.nota_global)}</p><div class="barras">` +
      conv.slice().sort((a, b) => b.valor_f_num - a.valor_f_num).map(p => `<div class="barra" style="--c:${colorDe(p)}">
      <span><b>${p.id}</b> · ${corto(p)}</span><div class="t"><i style="width:${6 + 94 * (p.valor_f_num - lo) / rg}%"></i></div>
      <span>f = ${fmt(p.valor_f_num, 6)}</span></div>`).join("") + `</div></div>`;
  }
  if (R.advertencias.length) h += `<div class="card"><h2>Advertencias</h2>${R.advertencias.map(a => `<p class="warn">⚠ ${esc(a)}</p>`).join("")}</div>`;
  $id("tab-resumen").innerHTML = h;
};

/* ─────────── 2. Procedimiento ─────────── */
INIT.proc = () => {
  let h = `<div class="card" style="margin-bottom:22px"><h2>Procedimiento completo</h2><p class="sub" style="margin:0">Cada paso reproduce el cálculo exacto que hizo SymPy; los decimales solo aparecen como apoyo.</p></div>`, k = 0;
  const paso = (t, cuerpo) => h += `<div class="paso"><div class="num">${++k}</div><div class="cuerpo"><h3>${mt(t)}</h3>${cuerpo}</div></div>`;
  const grad = E.m > 1 ? "\\sum_{i=1}^{" + E.m + "} \\lambda_i \\nabla g_i" : "\\lambda\\, \\nabla g";
  paso("Planteamiento del problema",
    eq("\\begin{aligned} &\\text{optimizar} && f(" + VARS + ") = " + E.f_latex + "\\\\ &\\text{sujeto a} && " +
       E.restricciones_latex.join("\\\\ & && ") + "\\end{aligned}") +
    `<div class="idea">${mt("**Idea geométrica.** En un extremo condicionado la curva (o superficie) de nivel de $f$ es tangente a la restricción, así que los gradientes son paralelos: $\\nabla f = " + grad + "$.")}</div>`);
  paso("Función de Lagrange", `<p>${mt("Se introduce un multiplicador por cada restricción:")}</p>` +
    eq("\\mathcal{L}(" + VARS + ",\\," + LT.join(",") + ") = f - " + (E.m > 1 ? "\\sum_{i=1}^{" + E.m + "} \\lambda_i\\, g_i" : "\\lambda\\, g")) +
    eq("\\mathcal{L} = " + R.lagrangiana.latex));
  paso("Condiciones de primer orden: $\\nabla \\mathcal{L} = 0$",
    `<p>${mt("Se deriva $\\mathcal{L}$ respecto a cada variable y a cada multiplicador, y se iguala a cero:")}</p>` +
    eq("\\begin{aligned}" + R.derivadas.map(d => d.lhs + " &= " + d.rhs + " = 0").join("\\\\[10pt]") + "\\end{aligned}") +
    `<p class="nota">${mt("Las derivadas respecto a los multiplicadores devuelven las restricciones $g_i = 0$.")}</p>`);
  let r = `<p>${mt("Método: **" + esc(R.metodo_resolucion) + "**.")}</p>`;
  if (R.base_groebner_latex) r += `<p>${mt("Una **base de Gröbner** en orden lexicográfico convierte el sistema en uno *triangular*: la última ecuación tiene una sola incógnita; se resuelve y se sustituye hacia arriba (es la eliminación gaussiana generalizada a polinomios). Tiene exactamente las mismas soluciones que el sistema original:")}</p>` +
    eq("\\begin{cases}" + R.base_groebner_latex.map(g => g + " = 0").join("\\\\[2pt]") + "\\end{cases}");
  if (R.puntos_criticos.length) {
    const cab = VT.concat(LT).concat(["f"]);
    const filas = TODOS.filter(p => p.tipo !== "singular").map(p => idTex(p.id) + " & " +
      V.map(v => p.coordenadas_latex[v]).concat(LT.map(l => (p.lambdas_latex || {})[l] || "\\cdot")).concat([p.valor_f_latex]).join(" & "));
    r += `<p>Soluciones <b>reales</b> del sistema:</p>` + eq("\\begin{array}{c|" + "c".repeat(VT.length + LT.length) + "|c} & " +
      cab.join(" & ") + " \\\\ \\hline " + filas.join(" \\\\[3pt] ") + "\\end{array}");
  } else r += `<p>El sistema no tiene soluciones reales.</p>`;
  if (R.soluciones_complejas_descartadas) r += `<p class="nota">Se descartaron ${R.soluciones_complejas_descartadas} soluciones complejas (no pertenecen a ℝⁿ).</p>`;
  paso("Resolución exacta del sistema", r);
  paso("Hessiano orlado",
    `<p>${mt("Para la condición de segundo orden se usa la matriz de segundas derivadas de $\\mathcal{L}$ **orlada** (enmarcada) con el jacobiano de las restricciones $J_g$:")}</p>` +
    eq("H_{\\text{orl}} = \\begin{pmatrix} 0_{m\\times m} & J_g \\\\ J_g^{\\,T} & \\nabla^2_{x}\\mathcal{L} \\end{pmatrix} = " + R.hessiano_orlado_general_latex) +
    `<div class="idea">${mt(R.criterio_tex)}</div>`);
  let c = "";
  TODOS.filter(p => p.tipo !== "singular").forEach((p, i) => {
    const col = colorDe(p);
    c += `<details class="sp" ${i === 0 ? "open" : ""}><summary><b>${p.id}</b> ${tex(ptTex(p))} <span class="chip" style="--c:${col}">${corto(p)}</span></summary><div class="in">`;
    c += `<p><b>a)</b> Se sustituye la solución del sistema:</p>` + eq(p.sustitucion_latex) + eq(p.f_evaluada_latex);
    if (p.hessiano_orlado_latex) c += `<p><b>b)</b> Hessiano orlado evaluado en el punto:</p>` + eq("H_{\\text{orl}}(" + idTex(p.id) + ") = " + p.hessiano_orlado_latex);
    (p.menores_orlados || []).forEach((m, j) => {
      if (j === 0) c += `<p><b>c)</b> Menores principales orlados que se revisan:</p>`;
      c += eq("\\Delta_{" + m.orden + "} = " + m.submatriz_latex + " = " + m.valor_latex + (m.signo > 0 ? " > 0" : m.signo < 0 ? " < 0" : " = 0"));
    });
    c += `<p>${mt(p.regla_tex)}</p>`;
    c += `<div class="concl" style="--c:${col}">${mt("⇒ $" + idTex(p.id) + " = " + ptTex(p) + "$ es **" + esc(p.clasificacion) + "**, con $f(" + idTex(p.id) + ") = " + p.valor_f_latex + "$.")}</div>`;
    const vt = p.verificacion_tangente;
    if (vt && vt.autovalores && vt.autovalores.length) c += `<p class="nota">${mt("Verificación independiente: los autovalores de $Z^{T}\\,\\nabla^2_x\\mathcal{L}\\,Z$ (Hessiano restringido al espacio tangente $J_g\\,d = 0$) son $" + vt.autovalores.map(x => fmt(x, 4)).join(",\\ ") + "$ → " + (vt.coincide ? "coincide ✔" : "difiere ✘"))}</p>`;
    c += `</div></details>`;
  });
  paso("Clasificación de cada punto crítico", c || "<p>No hay puntos que clasificar.</p>");
  if (R.puntos_singulares.length) paso("Puntos singulares de la restricción",
    `<p>${mt("Donde $\\nabla g = 0$ (o los $\\nabla g_i$ son linealmente dependientes) el teorema de Lagrange **no aplica**: puede haber un extremo que no cumpla $\\nabla f = \\lambda\\nabla g$. Se resuelven $g = 0$ junto con los menores del jacobiano:")}</p>` +
    TODOS.filter(p => p.tipo === "singular").map(p => eq(idTex(p.id) + " = " + ptTex(p) + ",\\qquad f(" + idTex(p.id) + ") = " + p.valor_f_latex)).join(""));
  const conv = TODOS.filter(p => p.valor_f_num !== null).sort((a, b) => b.valor_f_num - a.valor_f_num);
  if (conv.length) paso("Comparación global de candidatos",
    `<p>${mt("Si el conjunto factible $\\{g = 0\\}$ es cerrado y acotado, por el **teorema de Weierstrass** $f$ alcanza su máximo y su mínimo, y deben estar entre los candidatos:")}</p>
    <table class="kv" style="max-width:640px">${conv.map(p => `<tr><td><b>${p.id}</b> ${tex(ptTex(p))}</td><td>${tex("f = " + p.valor_f_latex)}</td><td>${esc(p.comparacion_global || corto(p))}</td></tr>`).join("")}</table>`);
  $id("tab-proc").innerHTML = h;
};

/* ─────────── 3. Gráfico 3D dinámico ─────────── */
const colorPunto = p => colorDe(p);
INIT.g3d = () => {
  const P = $id("tab-g3d");
  if (D.tipo === "sin_grafico") { P.innerHTML = `<div class="card"><h2>Sin representación geométrica</h2><p class="sub">Con más de 3 variables no hay gráfico; revisa el procedimiento y el JSON.</p></div>`; return; }
  if (D.tipo === "2d") g3dPlano(P); else g3dEspacio(P);
};

function g3dPlano(P) {
  const REC = [], pX = [], pY = [];
  let s = 0;
  D.curvas_restriccion.forEach(c => {
    let prev = null;
    c.x.forEach((x, i) => {
      const y = c.y[i], z = c.z[i];
      if (x === null || y === null || z === null) { prev = null; pX.push(null); pY.push(null); return; }
      if (prev) s += Math.hypot(x - prev[0], y - prev[1]);
      prev = [x, y]; REC.push({x, y, z, s}); pX.push(s); pY.push(z);
    });
    pX.push(null); pY.push(null);
  });
  const zs = D.z.flat().filter(v => v !== null).sort((a, b) => a - b), qz = t => zs[Math.floor(t * (zs.length - 1))];
  const [x0, x1] = D.rango[0], [y0, y1] = D.rango[1];
  const fr = REC.length ? REC.map(r => r.z) : zs;
  const zBot = zs[0], zTop = zs[zs.length - 1], rM = Math.max(...fr), rm = Math.min(...fr);
  const zCap = Math.min(zTop, Math.max(qz(0.55), rM + 0.25 * (rM - rm) + 0.12 * (zTop - zBot)));
  const zLow = Math.max(zBot, Math.min(qz(0.45), rm - 0.25 * (rM - rm) - 0.12 * (zTop - zBot)));
  const zmin = zLow, zmax = zCap;
  const Zc = D.z.map(f => f.map(v => v === null || v > zCap || v < zLow ? null : v));
  /* recorte limpio: fuera de [zLow, zCap] la superficie se aplana en el borde y se vuelve transparente */
  const Sb = D.z_rango || D.z, scV = Sb.flat().filter((v, k) => v !== null && Zc[Math.floor(k / D.x.length)][k % D.x.length] !== null);
  const scMin = Math.min(...scV), scMax = Math.max(...scV), SEN = scMin - 0.03 * ((scMax - scMin) || 1);
  const Zs = D.z.map(f => f.map(v => v === null ? null : Math.min(zCap, Math.max(zLow, v))));
  const Sc = Sb.map((f, i) => f.map((v, j) => Zc[i][j] === null ? SEN : v));
  const OPAC = [[0, 0], [0.02, 0], [0.03, 1], [1, 1]];
  let cmin = Math.min(...fr), cmax = Math.max(...fr); const pad = 0.12 * ((cmax - cmin) || 1); cmin -= pad; cmax += pad;
  const cDe = v => cmin + (cmax - cmin) * v / 400, vDe = c => Math.round(400 * (c - cmin) / (cmax - cmin));
  const c0 = D.puntos.length ? D.puntos[0].f : cDe(200);
  P.innerHTML = `<div class="card"><h2>Superficie z = f(${V.join(", ")}) y la restricción</h2>
    <p class="sub">La curva terracota es la restricción g = 0 “levantada” sobre la superficie: sus puntos más altos y más bajos son los extremos condicionados. Recórrela con el punto blanco o mueve el plano de nivel z = c: en un extremo, el plano <b>toca</b> la curva sin cruzarla (tangencia).</p>
    <div class="visor"><div id="g3" class="plot alto"></div><div class="ctrl">
      <div class="bloque"><label class="t">Recorrer la restricción</label><button class="btn pri" id="bRec">▶ Reproducir</button>
        <input type="range" id="sRec" min="0" max="${Math.max(REC.length - 1, 0)}" value="0"><div class="lectura" id="lRec"></div></div>
      <div class="bloque"><label class="t">Perfil de f a lo largo de g = 0</label><div id="perfil" class="plot bajo"></div></div>
      <div class="bloque"><label class="t">Plano de nivel z = c</label><label class="chk"><input type="checkbox" id="cPlano" checked> mostrar plano</label>
        <input type="range" id="sC" min="0" max="400" value="${vDe(c0)}"><div class="lectura" id="lC"></div><div class="fila" id="saltos" style="margin-top:8px"></div></div>
      <div class="bloque"><label class="t">Capas</label><label class="chk"><input type="checkbox" id="cMuro" checked> muro vertical sobre g = 0</label>
        <label class="chk"><input type="checkbox" id="cSup" checked> superficie z = f</label>
        <label class="chk"><input type="checkbox" id="cRec" checked> recortar la superficie a ${fmt(zLow, 3)} ≤ z ≤ ${fmt(zCap, 3)}</label></div>
    </div></div></div>`;
  const EPS = 0.012 * (zmax - zmin), up = a => a.map(v => v === null ? null : v + EPS);
  const tr = [{type:"surface", x:D.x, y:D.y, z:Zs, surfacecolor:Sc, cmin:SEN, cmax:scMax, opacityscale:OPAC,
    colorscale:TERRA3D, opacity:1, showscale:false, name:"z = f", hoverinfo:"x+y+z",
    lighting:{ambient:0.78, diffuse:0.5, specular:0.06, roughness:0.95, fresnel:0.1}}];
  const iMuros = [];
  D.curvas_restriccion.forEach(c => { const n = c.x.length; iMuros.push(tr.length);
    tr.push({type:"surface", x:[c.x, c.x], y:[c.y, c.y], z:[Array(n).fill(zmin), Array(n).fill(zmax)],
      surfacecolor:[Array(n).fill(0), Array(n).fill(1)], colorscale:[[0, "#d9b99b"], [1, "#d9b99b"]], cmin:0, cmax:1,
      showscale:false, opacity:0.3, hoverinfo:"skip", name:"muro g = 0"}); });
  D.curvas_restriccion.forEach((c, i) => tr.push({type:"scatter3d", mode:"lines", x:c.x, y:c.y, z:up(c.z),
    line:{color:COLOR.ac, width:9}, name:"f sobre g = 0", showlegend:i === 0, hoverinfo:"x+y+z"}));
  tr.push({type:"scatter3d", mode:"markers+text", x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.coords[1]),
    z:up(D.puntos.map(p => p.f)), text:D.puntos.map(p => p.id), textposition:"top center", textfont:{color:COLOR.tx, size:13},
    marker:{size:9, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos críticos"});
  const iPlano = tr.length;
  tr.push({type:"surface", x:[x0, x1], y:[y0, y1], z:[[c0, c0], [c0, c0]], colorscale:[[0, "#f0d3bd"], [1, "#f0d3bd"]],
    showscale:false, opacity:0.5, hoverinfo:"skip", name:"plano z = c", showlegend:true});
  const iMov = tr.length, r0 = REC[0] || {x:0, y:0, z:0, s:0};
  tr.push({type:"scatter3d", mode:"markers", x:[r0.x], y:[r0.y], z:[r0.z], marker:{size:9, color:"#ffffff", line:{color:COLOR.ac2, width:4}},
    name:"punto móvil", hoverinfo:"skip", visible:REC.length > 0});
  tr.push({type:"scatter3d", mode:"lines", x:[r0.x, r0.x], y:[r0.y, r0.y], z:[zmin, r0.z], line:{color:COLOR.ac2, width:4, dash:"dash"},
    showlegend:false, hoverinfo:"skip", visible:REC.length > 0});
  const g3 = reg("g3d", $id("g3"));
  Plotly.newPlot(g3, tr, lay({margin:{l:0, r:0, t:10, b:0}, legend:{orientation:"h", y:0.02, x:0.02},
    scene:{xaxis:ejes3(V[0]), yaxis:ejes3(V[1]), zaxis:Object.assign(ejes3("f"), {range:[zmin - 0.04 * (zmax - zmin), zmax + 0.06 * (zmax - zmin)]}),
           aspectmode:"manual", aspectratio:{x:1, y:1, z:0.75}, camera:{eye:{x:1.25, y:-1.3, z:1.2}}}}), CFG);
  $id("cRec").onchange = e => { Plotly.restyle(g3, e.target.checked ? {z:[Zs], surfacecolor:[Sc], cmin:[SEN], cmax:[scMax], opacityscale:[OPAC]} : {z:[D.z], surfacecolor:[Sb], cmin:[null], cmax:[null], opacityscale:[null]}, [0]);
    Plotly.relayout(g3, {"scene.zaxis.autorange": !e.target.checked, "scene.zaxis.range": e.target.checked ? [zmin - 0.04 * (zmax - zmin), zmax + 0.06 * (zmax - zmin)] : undefined}); };
  const perf = reg("g3d", $id("perfil"));
  const crit = D.puntos.map(p => { let b = -1, bd = Infinity;
    REC.forEach((r, i) => { const d = Math.hypot(r.x - p.coords[0], r.y - p.coords[1]); if (d < bd) { bd = d; b = i; } });
    return bd < 0.03 * (x1 - x0) ? {p, s:REC[b].s} : null; }).filter(Boolean);
  const lineaC = c => ({type:"line", xref:"paper", x0:0, x1:1, y0:c, y1:c, line:{color:COLOR.ac2, width:1.5, dash:"dot"}});
  Plotly.newPlot(perf, [{x:pX, y:pY, mode:"lines", line:{color:COLOR.ac, width:2.5}, hoverinfo:"x+y"},
    {x:crit.map(c => c.s), y:crit.map(c => c.p.f), mode:"markers+text", text:crit.map(c => c.p.id), textposition:"top center",
     textfont:{size:11, color:COLOR.tx}, marker:{size:9, color:crit.map(c => colorPunto(c.p)), line:{color:"#fff", width:1.5}}, hoverinfo:"skip"},
    {x:[r0.s], y:[r0.z], mode:"markers", marker:{size:11, color:"#fff", line:{color:COLOR.ac2, width:3}}, hoverinfo:"skip"}],
    lay({margin:{l:42, r:8, t:8, b:34}, showlegend:false, shapes:[lineaC(c0)],
         xaxis:{title:{text:"longitud de arco s", font:{size:11}}, gridcolor:COLOR.bd}, yaxis:{title:{text:"f", font:{size:11}}, gridcolor:COLOR.bd}}),
    {displayModeBar:false, responsive:true});
  const sTot = REC.length ? REC[REC.length - 1].s : 1;
  const mover = i => { const r = REC[i]; if (!r) return;
    Plotly.restyle(g3, {x:[[r.x], [r.x, r.x]], y:[[r.y], [r.y, r.y]], z:[[r.z + 2 * EPS], [zmin, r.z]]}, [iMov, iMov + 1]);
    Plotly.restyle(perf, {x:[[r.s]], y:[[r.z]]}, [2]);
    const cerca = crit.find(c => Math.abs(c.s - r.s) < 0.012 * sTot);
    $id("lRec").innerHTML = `${V[0]} = ${fmt(r.x, 4)}<br>${V[1]} = ${fmt(r.y, 4)}<br>f = ${fmt(r.z, 6)}` +
      (cerca ? `<br><b style="color:${colorPunto(cerca.p)}">≈ ${cerca.p.id}: ${corto(cerca.p)}</b>` : ""); };
  if (REC.length) { reproductor($id("bRec"), $id("sRec"), mover, Math.max(1, Math.round(REC.length / 360))); mover(0); }
  else $id("lRec").textContent = "La restricción no tiene un trazo continuo en este rango.";
  const plano = v => { const c = cDe(v);
    Plotly.restyle(g3, {z:[[[c, c], [c, c]]]}, [iPlano]); Plotly.relayout(perf, {shapes:[lineaC(c)]});
    const toca = crit.filter(q => Math.abs(q.p.f - c) < 0.004 * (cmax - cmin));
    $id("lC").innerHTML = `c = ${fmt(c, 6)}` + (toca.length ? `<br><b>tangente en ${toca.map(q => q.p.id).join(", ")}</b>` : ""); };
  $id("sC").oninput = e => plano(+e.target.value);
  $id("saltos").innerHTML = D.puntos.map((p, i) => `<button class="btn mini" data-i="${i}">c = f(${p.id})</button>`).join("");
  $id("saltos").querySelectorAll("button").forEach(b => b.onclick = () => { const p = D.puntos[+b.dataset.i];
    $id("sC").value = vDe(p.f); plano(vDe(p.f)); });
  plano(vDe(c0));
  $id("cPlano").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [iPlano]);
  $id("cMuro").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, iMuros);
  $id("cSup").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [0]);
}

function g3dEspacio(P) {
  const fr = D.f_en_restriccion.filter(v => v !== null);
  let cmin = Math.min(...fr), cmax = Math.max(...fr); const pad = 0.06 * ((cmax - cmin) || 1); cmin -= pad; cmax += pad;
  const cDe = v => cmin + (cmax - cmin) * v / 300, vDe = c => Math.round(300 * (c - cmin) / (cmax - cmin));
  const c0 = D.puntos.length ? D.puntos[0].f : cDe(150);
  P.innerHTML = `<div class="card"><h2>${esc(D.descripcion)} y superficies de nivel de f</h2>
    <p class="sub">Los puntos forman la restricción, coloreados según el valor de f. La superficie translúcida es el nivel f = c: al barrer c, el primer y el último contacto con la restricción (contacto <b>tangente</b>) dan el mínimo y el máximo condicionados.</p>
    <div class="visor"><div id="g3" class="plot alto"></div><div class="ctrl">
      <div class="bloque"><label class="t">Superficie de nivel f = c</label><button class="btn pri" id="bIso">▶ Barrer c</button>
        <input type="range" id="sIso" min="0" max="300" value="${vDe(c0)}"><div class="lectura" id="lIso"></div><div class="fila" id="saltos" style="margin-top:8px"></div></div>
      <div class="bloque"><label class="t">Capas</label><label class="chk"><input type="checkbox" id="cIso" checked> superficie f = c</label>
        <label class="chk"><input type="checkbox" id="cNube" checked> restricción (nube de puntos)</label></div>
    </div></div></div>`;
  const [ex, ey, ez] = D.vol.ejes, X = [], Y = [], Z = [];
  ex.forEach(a => ey.forEach(b => ez.forEach(c => { X.push(a); Y.push(b); Z.push(c); })));
  const val = D.vol.valor.map(v => v === null ? NaN : v);
  const tr = [{type:"scatter3d", mode:"markers", x:D.x, y:D.y, z:D.z, name:"restricción", hoverinfo:"skip",
      marker:{size:2.6, color:D.f_en_restriccion, colorscale:TERRA, opacity:0.8, colorbar:{title:{text:"f"}, len:0.6, thickness:14}}},
    {type:"scatter3d", mode:"markers+text", x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.coords[1]), z:D.puntos.map(p => p.coords[2]),
      text:D.puntos.map(p => p.id), textposition:"top center", textfont:{color:COLOR.tx, size:13},
      marker:{size:8, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos críticos"},
    {type:"isosurface", x:X, y:Y, z:Z, value:val, isomin:c0, isomax:c0, surface:{count:1}, showscale:false, opacity:0.32,
      colorscale:[[0, COLOR.min], [1, COLOR.min]], caps:{x:{show:false}, y:{show:false}, z:{show:false}}, name:"f = c", hoverinfo:"skip", showlegend:true}];
  const g3 = reg("g3d", $id("g3"));
  Plotly.newPlot(g3, tr, lay({margin:{l:0, r:0, t:10, b:0}, legend:{orientation:"h", y:0.02, x:0.02},
    scene:{xaxis:ejes3(V[0]), yaxis:ejes3(V[1]), zaxis:ejes3(V[2]), aspectmode:"cube", camera:{eye:{x:1.6, y:-1.5, z:1.0}}}}), CFG);
  const iso = v => { const c = cDe(v); Plotly.restyle(g3, {isomin:[c], isomax:[c]}, [2]);
    const tol = 0.01 * (cmax - cmin), n = fr.filter(q => Math.abs(q - c) < tol).length;
    const t = D.puntos.filter(p => Math.abs(p.f - c) < 0.004 * (cmax - cmin));
    $id("lIso").innerHTML = `c = ${fmt(c, 6)}<br>` + (n ? `corta la restricción (~${n} puntos)` : "no toca la restricción") +
      (t.length ? `<br><b>contacto tangente en ${t.map(p => p.id).join(", ")}</b>` : ""); };
  reproductor($id("bIso"), $id("sIso"), iso, 2); iso(vDe(c0));
  $id("saltos").innerHTML = D.puntos.map((p, i) => `<button class="btn mini" data-i="${i}">c = f(${p.id})</button>`).join("");
  $id("saltos").querySelectorAll("button").forEach(b => b.onclick = () => { const p = D.puntos[+b.dataset.i]; $id("sIso").value = vDe(p.f); iso(vDe(p.f)); });
  $id("cIso").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [2]);
  $id("cNube").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [0]);
}

/* ─────────── 4. Gráficos 2D ─────────── */
INIT.g2d = () => {
  const P = $id("tab-g2d");
  if (D.tipo === "sin_grafico") { P.innerHTML = `<div class="card"><h2>Sin gráfico</h2><p class="sub">Más de 3 variables.</p></div>`; return; }
  if (D.tipo === "2d") {
    P.innerHTML = `<div class="card"><h2>Curvas de nivel, restricción y gradientes</h2>
      <p class="sub">Colores por cuantiles de f. En cada punto crítico ∇f (ocre) y ∇g (petróleo) son <b>paralelos</b>: esa es la condición ∇f = λ∇g. La línea discontinua es la curva de nivel de f que pasa por el punto: es tangente a la restricción.</p>
      <div class="leyenda"><span><i style="background:${COLOR.max}"></i>máximo</span><span><i style="background:${COLOR.min}"></i>mínimo</span><span><i style="background:${COLOR.silla}"></i>silla</span><span><i style="background:${COLOR.ind}"></i>no concluyente</span><span><i style="background:${COLOR.sing}"></i>singular</span></div>
      <div id="g2" class="plot"></div></div>`;
    const cb = D.ticks_color ? {title:{text:"f"}, tickvals:D.ticks_color.vals, ticktext:D.ticks_color.text, thickness:14} : {title:{text:"f"}};
    const tr = [{type:"contour", x:D.x, y:D.y, z:D.z_rango || D.z, text:D.z, colorscale:TERRA, ncontours:34, colorbar:cb,
      contours:{coloring:"heatmap", showlines:true}, line:{width:0.4, color:"rgba(255,255,255,.3)"}, name:"f",
      hovertemplate:"x = %{x:.3f}<br>y = %{y:.3f}<br>f = %{text}<extra></extra>"}];
    [...new Set(D.niveles_criticos)].forEach((lv, i) => tr.push({type:"contour", x:D.x, y:D.y, z:D.z, showscale:false, hoverinfo:"skip",
      contours:{coloring:"none", start:lv, end:lv, size:1}, line:{color:"#fff", width:1.8, dash:"dash"}, name:"nivel f = f(P)", showlegend:i === 0}));
    D.curvas_restriccion.forEach((c, i) => tr.push({type:"scatter", mode:c.dispersa ? "markers" : "lines", x:c.x, y:c.y,
      line:{color:OSCURO ? "#f3e6d8" : "#2b2420", width:3.5}, marker:{size:2, color:"#2b2420"}, name:"g = 0", showlegend:i === 0}));
    const L = (D.rango[0][1] - D.rango[0][0]) * 0.11;
    const flecha = (px, py, v, col, nm, w) => { const n = Math.hypot(v[0], v[1]); if (!n) return;
      tr.push({type:"scatter", mode:"lines+markers", x:[px, px + L * v[0] / n], y:[py, py + L * v[1] / n], name:nm, showlegend:false,
        line:{color:col, width:w}, marker:{size:[0, 11], symbol:"arrow", angleref:"previous", color:col}, hoverinfo:"name"}); };
    D.puntos.forEach(p => { const [px, py] = p.coords;
      p.grad_g.forEach(g => flecha(px, py, g, COLOR.min, "∇g", 6)); flecha(px, py, p.grad_f, "#e0a64a", "∇f", 3);
      tr.push({type:"scatter", mode:"markers+text", x:[px], y:[py], text:[p.id], textposition:"top right", textfont:{color:"#fff", size:13},
        marker:{size:15, color:colorPunto(p), line:{color:"#fff", width:2}}, hovertext:[hov(p)], hoverinfo:"text", showlegend:false}); });
    Plotly.newPlot(reg("g2d", $id("g2")), tr, lay({xaxis:{title:{text:V[0]}, range:D.rango[0], constrain:"domain", gridcolor:COLOR.bd},
      yaxis:{title:{text:V[1]}, range:D.rango[1], scaleanchor:"x", constrain:"domain", gridcolor:COLOR.bd}}), CFG);
  } else {
    P.innerHTML = `<div class="card"><h2>Proyecciones de la restricción</h2><p class="sub">La restricción vista desde los tres planos coordenados, coloreada por f.</p><div class="grid2" id="proys"></div></div>`;
    [[0, 1], [0, 2], [1, 2]].forEach(([a, b]) => { const d = document.createElement("div"); d.className = "plot medio"; $id("proys").appendChild(d);
      const ej = [D.x, D.y, D.z];
      Plotly.newPlot(reg("g2d", d), [{type:"scattergl", mode:"markers", x:ej[a], y:ej[b], marker:{size:4, color:D.f_en_restriccion, colorscale:TERRA, opacity:0.75}, hoverinfo:"skip", name:"g = 0"},
        {type:"scatter", mode:"markers+text", x:D.puntos.map(p => p.coords[a]), y:D.puntos.map(p => p.coords[b]), text:D.puntos.map(p => p.id), textposition:"top right",
         marker:{size:13, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos"}],
        lay({showlegend:false, xaxis:{title:{text:V[a]}, gridcolor:COLOR.bd}, yaxis:{title:{text:V[b]}, gridcolor:COLOR.bd, scaleanchor:"x"}}), CFG); });
  }
};
