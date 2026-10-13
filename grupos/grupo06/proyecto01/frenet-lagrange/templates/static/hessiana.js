/* ═════════════ Módulo: Puntos críticos y matriz Hessiana ═════════════ */
const E = R.entrada, V = E.variables, VT = R.variables_latex, N = E.n;
const COLCL = {"mínimo local":COLOR.min, "máximo local":COLOR.max, "punto de silla":COLOR.silla};
const colorDe = p => p.tipo === "no diferenciable" ? COLOR.sing : (COLCL[p.clasificacion] || COLOR.ind);
const colorPunto = colorDe;
const TODOS = [...R.puntos_criticos, ...R.puntos_no_diferenciables, ...R.familias.filter(f => f.representante).map(f => f.representante)]
  .map((p, i) => Object.assign({id:"P" + (i + 1)}, p));
const ptTex = p => "\\left(" + V.map(v => p.coordenadas_latex[v]).join(",\\ ") + "\\right)";
const idTex = id => id.replace(/(\d+)/, "_{$1}");
const VARS = VT.join(",\\,");
const dudoso = p => (p.clasificacion_segundo_orden || "").startsWith("caso dudoso");
const hov = p => `<b>${p.id}</b> ${p.etiqueta}<br>f = ${fmt(p.f, 6)}<br>${p.clasificacion} (${p.certeza})`;
const LAM_POS = "#e0a64a", LAM_NEG = "#3f6e7d";

$id("enunciado").innerHTML = tex("f(" + VARS + ") = " + E.f_latex + "\\qquad \\text{en un abierto de }\\ \\mathbb{R}^{" + N + "}");
$id("meta").innerHTML = `<span>${N} variable(s)</span><span>${esc(R.metodo_resolucion)}</span><span>${TODOS.length} punto(s) crítico(s)</span>` +
  (R.familias.length ? `<span>${R.familias.length} familia(s)</span>` : "");

/* ─────────── 1. Resumen ─────────── */
INIT.resumen = () => {
  const cnt = c => TODOS.filter(p => p.clasificacion === c).length;
  const K = [[TODOS.length, "puntos críticos", COLOR.ac], [cnt("mínimo local"), "mínimos locales", COLOR.min],
             [cnt("máximo local"), "máximos locales", COLOR.max], [cnt("punto de silla"), "puntos de silla", COLOR.silla],
             [TODOS.filter(dudoso).length, "casos dudosos resueltos", COLOR.sing]];
  let h = `<div class="kpis">${K.map(([n, t, c]) => `<div class="kpi" style="--c:${c}"><b>${n}</b><span>${t}</span></div>`).join("")}</div>`;
  h += `<div class="card"><h2>Puntos críticos</h2><p class="sub">Soluciones reales de ∇f = 0 (y puntos donde ∇f no existe), con su clasificación y el grado de certeza.</p><div class="pts">`;
  TODOS.forEach(p => {
    h += `<div class="pt" style="--c:${colorDe(p)}"><div class="cab"><div><b>${p.id}</b>&nbsp; ${tex(ptTex(p))}</div><span class="chip">${esc(p.clasificacion)}</span></div><table class="kv">`;
    if (p.tipo !== "estacionario") h += `<tr><td>tipo</td><td><b>${esc(p.tipo)}</b></td></tr>`;
    h += `<tr><td>valor de f</td><td>${tex(p.valor_f_latex)} <span class="nota">≈ ${fmt(p.valor_f_num, 6)}</span></td></tr>`;
    if (p.D_latex !== undefined) h += `<tr><td>D · f<sub>xx</sub></td><td>${tex("D = " + p.D_latex + ",\\quad f_{xx} = " + p.fxx_latex)}</td></tr>`;
    else if (p.menores_principales) h += `<tr><td>menores Δ<sub>k</sub></td><td>${p.menores_principales.map(m => tex("\\Delta_{" + m.orden + "} = " + m.valor_latex)).join(", ")}</td></tr>`;
    if (p.autovalores) h += `<tr><td>autovalores de H</td><td>${p.autovalores.map(a => a.latex ? tex(a.latex) : fmt(a.num, 5)).join(", ")}</td></tr>`;
    h += `<tr><td>criterio</td><td>${esc(p.criterio)}</td></tr><tr><td>certeza</td><td>${esc(p.certeza)}${p.verificado_gradiente_cero ? " · ∇f(P) = 0 ✔" : ""}</td></tr>`;
    if (p.comparacion_global) h += `<tr><td>global</td><td><b>${esc(p.comparacion_global)}</b></td></tr>`;
    h += `</table></div>`;
  });
  R.familias.forEach(f => h += `<div class="pt" style="--c:${COLOR.sing}"><div class="cab"><b>Familia de puntos críticos</b><span class="chip">∞ puntos</span></div>
      ${eq("\\left(" + V.map(v => f.parametrizacion_latex[v]).join(",\\ ") + "\\right)")}<p class="nota">Parámetro(s) libre(s): ${f.parametros.join(", ")} · f en la familia = ${esc(f.valor_f)}</p></div>`);
  if (!TODOS.length && !R.familias.length) h += `<p>f no tiene puntos críticos reales.</p>`;
  h += `</div></div>`;
  const G = R.analisis_global;
  h += `<div class="card"><h2>Análisis global</h2>${G.justificacion_tex.map(j => `<p>${mt(j)}</p>`).join("")}`;
  if (G.minimo_global_latex) h += eq("\\boxed{\\min_{\\mathbb{R}^{" + N + "}} f = " + G.minimo_global_latex + "}");
  if (G.maximo_global_latex) h += eq("\\boxed{\\max_{\\mathbb{R}^{" + N + "}} f = " + G.maximo_global_latex + "}");
  h += `<p class="nota">Certeza: ${esc(G.certeza)}</p>` + R.advertencias.map(a => `<p class="warn">⚠ ${esc(a)}</p>`).join("") + `</div>`;
  $id("tab-resumen").innerHTML = h;
};

/* ─────────── 2. Procedimiento ─────────── */
INIT.proc = () => {
  let h = `<div class="card" style="margin-bottom:22px"><h2>Procedimiento completo</h2><p class="sub" style="margin:0">Cada paso reproduce el cálculo exacto que hizo SymPy; los decimales solo aparecen como apoyo.</p></div>`, k = 0;
  const paso = (t, cuerpo) => h += `<div class="paso"><div class="num">${++k}</div><div class="cuerpo"><h3>${mt(t)}</h3>${cuerpo}</div></div>`;
  paso("Función a optimizar", eq("f(" + VARS + ") = " + E.f_latex) +
    `<div class="idea">${mt("**Teorema de Fermat.** En un dominio abierto, todo extremo local es un **punto crítico**: un punto donde $\\nabla f = 0$ o donde $\\nabla f$ no existe. Primero se hallan todos; después se clasifican.")}</div>`);
  paso("Gradiente $\\nabla f$", `<p>${mt("Se calcula cada derivada parcial de forma simbólica:")}</p>` +
    eq("\\begin{aligned}" + R.gradiente.map(g => g.lhs + " &= " + g.latex).join("\\\\[10pt]") + "\\end{aligned}"));
  let s = eq("\\nabla f = 0 \\iff \\begin{cases}" + R.gradiente.map(g => g.latex + " = 0").join("\\\\[2pt]") + "\\end{cases}");
  if (R.factores_descartados_latex.length) s += `<p>${mt("Los factores $" + R.factores_descartados_latex.join(",\\ ") + "$ **nunca se anulan**, así que se pueden eliminar sin perder soluciones. El sistema equivale a:")}</p>` +
    eq("\\begin{cases}" + R.sistema_resuelto.map(e => e.latex).join("\\\\[2pt]") + "\\end{cases}");
  s += `<p>${mt("Método: **" + esc(R.metodo_resolucion) + "**.")}</p>`;
  if (R.base_groebner_latex) s += `<p>${mt("La **base de Gröbner** (orden lexicográfico) deja el sistema *triangular*: la última ecuación tiene una sola incógnita; se resuelve y se sustituye hacia arriba. Tiene exactamente las mismas soluciones:")}</p>` +
    eq("\\begin{cases}" + R.base_groebner_latex.map(g => g + " = 0").join("\\\\[2pt]") + "\\end{cases}");
  const est = TODOS.filter(p => p.tipo === "estacionario");
  if (est.length) s += `<p>Soluciones <b>reales</b> (cada una se verificó sustituyéndola en ∇f):</p>` +
    eq("\\begin{array}{c|" + "c".repeat(VT.length) + "|c} & " + VT.join(" & ") + " & f \\\\ \\hline " +
       est.map(p => idTex(p.id) + " & " + V.map(v => p.coordenadas_latex[v]).join(" & ") + " & " + p.valor_f_latex).join(" \\\\[3pt] ") + "\\end{array}");
  R.familias.forEach(f => s += `<p>${mt("Además hay una **familia** de soluciones (infinitos puntos críticos, no aislados):")}</p>` +
    eq("\\left(" + V.map(v => f.parametrizacion_latex[v]).join(",\\ ") + "\\right),\\qquad " + f.parametros.join(",") + " \\in \\mathbb{R}"));
  if (R.soluciones_complejas_descartadas) s += `<p class="nota">Se descartaron ${R.soluciones_complejas_descartadas} soluciones complejas (no pertenecen a ℝⁿ).</p>`;
  if (R.puntos_no_diferenciables.length) s += `<p>${mt("Puntos donde $\\nabla f$ **no existe** (también son críticos): $" + TODOS.filter(p => p.tipo === "no diferenciable").map(p => idTex(p.id) + " = " + ptTex(p)).join(",\\ ") + "$.")}</p>`;
  paso("Sistema $\\nabla f = 0$ y su resolución exacta", s);
  let hs = `<p>${mt("Segundas derivadas parciales:")}</p>` + eq("\\begin{aligned}" + R.segundas_derivadas.map(d => d.lhs + " &= " + d.latex).join("\\\\[6pt]") + "\\end{aligned}") +
    eq("H(" + VARS + ") = " + R.hessiana_general_latex);
  if (R.D_general_latex) hs += `<p>${mt("El **discriminante** es el determinante de $H$:")}</p>` + eq("D(x,y) = f_{xx}\\,f_{yy} - f_{xy}^{2} = " + R.D_general_latex);
  paso("Matriz Hessiana", hs);
  let cr = "";
  if (N === 2) cr = `<table class="kv" style="max-width:560px"><tr><td>${tex("D > 0,\\ f_{xx} > 0")}</td><td>mínimo local (cuenco ∪)</td></tr>
      <tr><td>${tex("D > 0,\\ f_{xx} < 0")}</td><td>máximo local (cúpula ∩)</td></tr><tr><td>${tex("D < 0")}</td><td>punto de silla</td></tr>
      <tr><td>${tex("D = 0")}</td><td>caso dudoso → análisis de orden superior</td></tr></table>`;
  else if (N === 1) cr = `<p>${mt("$f''(P) > 0$ → mínimo; $f''(P) < 0$ → máximo; $f''(P) = 0$ → dudoso.")}</p>`;
  else cr = `<p>${mt("**Criterio de Sylvester** con los menores principales $\\Delta_k = \\det H_{k\\times k}$: todos $> 0$ → mínimo; $(-1)^k\\Delta_k > 0$ → máximo; $\\det H \\neq 0$ sin esos patrones → silla; $\\det H = 0$ → dudoso. Se confirma con el signo de los autovalores de $H$.")}</p>`;
  cr += `<div class="idea">${mt("**¿Por qué funciona?** Cerca de un punto crítico, $f(P+h) \\approx f(P) + \\tfrac{1}{2}\\,h^{T} H(P)\\, h$. El signo de esa forma cuadrática (definida positiva, negativa o indefinida) decide si $f$ sube en todas las direcciones, baja en todas, o sube en unas y baja en otras.")}</div>`;
  paso("Criterio de la segunda derivada", cr);
  let c = "";
  TODOS.forEach((p, i) => {
    const col = colorDe(p);
    c += `<details class="sp" ${i === 0 ? "open" : ""}><summary><b>${p.id}</b> ${tex(ptTex(p))} <span class="chip" style="--c:${col}">${esc(p.clasificacion)}</span>${dudoso(p) ? `<span class="chip" style="--c:${COLOR.sing}">D = 0 resuelto</span>` : ""}</summary><div class="in">`;
    c += `<p><b>a)</b> Valor de la función:</p>` + eq(p.f_evaluada_latex);
    if (p.hessiana_latex) {
      c += `<p><b>b)</b> Hessiana evaluada en el punto:</p>` + eq("H(" + idTex(p.id) + ") = " + p.hessiana_latex);
      if (p.calculo_D_latex) c += `<p><b>c)</b> Discriminante:</p>` + eq(p.calculo_D_latex) + eq("f_{xx}(" + idTex(p.id) + ") = " + p.fxx_latex);
      else if (N === 1) c += eq("f''(" + idTex(p.id) + ") = " + p.menores_principales[0].valor_latex);
      else p.menores_principales.forEach((m, j) => { if (j === 0) c += `<p><b>c)</b> Menores principales:</p>`;
        c += eq("\\Delta_{" + m.orden + "} = " + m.submatriz_latex + " = " + m.valor_latex); });
      if (p.autovalores) c += `<p><b>d)</b> Autovalores de la Hessiana (curvaturas principales):</p>` +
        eq("\\lambda(H) = \\left\\{" + p.autovalores.map(a => (a.latex || fmt(a.num, 5)) + (a.multiplicidad > 1 ? "\\ (\\times " + a.multiplicidad + ")" : "")).join(",\\ ") + "\\right\\}");
    } else c += `<p>${mt("En este punto $\\nabla f$ **no existe**, así que no hay Hessiana: se estudia directamente el signo de $f - f(P)$.")}</p>`;
    c += `<p>${mt(p.regla_tex)}</p>`;
    const a = p.analisis_orden_superior;
    if (a && a.pasos_tex && a.pasos_tex.length) c += `<div class="idea"><b>Análisis de orden superior</b><ol class="pasos">${a.pasos_tex.map(t => `<li>${mt(t)}</li>`).join("")}</ol></div>`;
    c += `<div class="concl" style="--c:${col}">${mt("⇒ $" + idTex(p.id) + " = " + ptTex(p) + "$ es **" + esc(p.clasificacion) + "** (" + esc(p.certeza) + "), con $f(" + idTex(p.id) + ") = " + p.valor_f_latex + "$." + (p.comparacion_global ? " Además es **" + esc(p.comparacion_global) + "**." : ""))}</div>`;
    const va = p.verificacion_autovalores;
    if (va && va.valores && !dudoso(p)) c += `<p class="nota">Verificación independiente por autovalores: ${va.valores.map(x => fmt(x, 4)).join(", ")} → ${va.coincide ? "coincide ✔" : "difiere ✘"}</p>`;
    c += `</div></details>`;
  });
  paso("Clasificación de cada punto crítico", c || "<p>No hay puntos que clasificar.</p>");
  const G = R.analisis_global;
  let g = G.justificacion_tex.map(j => `<p>${mt(j)}</p>`).join("");
  if (G.minimo_global_latex) g += eq("\\boxed{\\min f = " + G.minimo_global_latex + "}");
  if (G.maximo_global_latex) g += eq("\\boxed{\\max f = " + G.maximo_global_latex + "}");
  paso("Análisis global", g + `<p class="nota">Certeza: ${esc(G.certeza)}</p>`);
  $id("tab-proc").innerHTML = h;
};

/* ─────────── 3. Gráfico 3D dinámico ─────────── */
INIT.g3d = () => {
  const P = $id("tab-g3d");
  if (D.tipo === "sin_grafico") { P.innerHTML = `<div class="card"><h2>Sin representación geométrica</h2><p class="sub">Con más de 3 variables no hay gráfico; revisa el procedimiento y el JSON.</p></div>`; return; }
  if (D.tipo === "1d") { P.innerHTML = `<div class="card"><h2>Una sola variable</h2><p class="sub">La gráfica de f es una curva plana: está en la pestaña «Gráficos 2D».</p></div>`; return; }
  if (D.tipo === "2d") g3dSuperficie(P); else g3dVolumen(P);
};

/* curva de nivel f = c por "marching squares" sobre la malla (x, y, Z) */
function nivelSegs(xs, ys, Z, c) {
  const X = [], Y = [];
  for (let j = 0; j < ys.length - 1; j++) for (let i = 0; i < xs.length - 1; i++) {
    const v = [Z[j][i], Z[j][i + 1], Z[j + 1][i + 1], Z[j + 1][i]];
    if (v.some(q => q === null)) continue;
    const P = [[xs[i], ys[j]], [xs[i + 1], ys[j]], [xs[i + 1], ys[j + 1]], [xs[i], ys[j + 1]]], cut = [];
    for (let e = 0; e < 4; e++) { const a = v[e] - c, b = v[(e + 1) % 4] - c;
      if ((a < 0 && b >= 0) || (a >= 0 && b < 0)) { const t = a / (a - b), p = P[e], q = P[(e + 1) % 4];
        cut.push([p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])]); } }
    for (let k = 0; k + 1 < cut.length; k += 2) { X.push(cut[k][0], cut[k + 1][0], null); Y.push(cut[k][1], cut[k + 1][1], null); }
  }
  return [X, Y];
}

function g3dSuperficie(P) {
  const zs = D.z.flat().filter(v => v !== null).sort((a, b) => a - b), qz = t => zs[Math.floor(t * (zs.length - 1))];
  const fcr = D.puntos.map(p => p.f).filter(v => v !== null);
  const fM = fcr.length ? Math.max(...fcr) : qz(0.5), fm = fcr.length ? Math.min(...fcr) : qz(0.5);
  const zBot = zs[0], zTop = zs[zs.length - 1];
  const zCap = Math.min(zTop, Math.max(qz(0.55), fM + 0.8 * (fM - fm) + 0.12 * (zTop - zBot)));
  const zLow = Math.max(zBot, Math.min(qz(0.45), fm - 0.8 * (fM - fm) - 0.12 * (zTop - zBot)));
  const dentro = v => v !== null && v <= zCap && v >= zLow;
  const recorta = M => M.map(f => f.map(v => dentro(v) ? v : null));
  const zmin = zLow, zmax = zCap;
  const [x0, x1] = D.rango[0], [y0, y1] = D.rango[1];
  const cDe = v => zmin + (zmax - zmin) * v / 500, vDe = c => Math.round(500 * (c - zmin) / ((zmax - zmin) || 1));
  const c0 = D.puntos.length ? D.puntos[0].f : cDe(250);
  const flujos = D.flujo.filter(l => l.x.length > 3);
  const bol = flujos.filter((_, i) => i % Math.max(1, Math.ceil(flujos.length / 60)) === 0);
  const T = Math.max(1, ...bol.map(l => l.x.length));
  const opts = D.puntos.filter(p => p.taylor);
  P.innerHTML = `<div class="card"><h2>Superficie z = f(${V.join(", ")})</h2>
    <p class="sub">Suelta bolitas sobre la superficie: ruedan siguiendo −∇f (máximo descenso) y se acumulan en los mínimos; cada color es una cuenca de atracción. Mueve la curva de nivel f = c: al pasar por un punto de silla la curva cambia de forma (se cruza consigo misma).</p>
    <div class="visor"><div id="g3" class="plot alto"></div><div class="ctrl">
      <div class="bloque"><label class="t">Descenso por el gradiente</label><div class="fila"><button class="btn pri" id="bDesc">▶ Reproducir</button><button class="btn" id="bRein">⟲ Reiniciar</button></div>
        <input type="range" id="sT" min="0" max="${T - 1}" value="0"><div class="lectura" id="lT"></div></div>
      <div class="bloque"><label class="t">Curva de nivel f = c</label><label class="chk"><input type="checkbox" id="cPlano"> mostrar plano z = c</label>
        <input type="range" id="sC" min="0" max="500" value="${vDe(c0)}"><div class="lectura" id="lC"></div><div class="fila" id="saltos" style="margin-top:8px"></div></div>
      <div class="bloque"><label class="t">Aproximación de Taylor</label><select id="sel"><option value="-1">ninguna</option>${opts.map((p, i) => `<option value="${i}">${p.id} — ${p.clasificacion}</option>`).join("")}</select>
        <p class="nota" style="margin:8px 0 0">${mt("Superficie $f(P) + \\tfrac12 h^{T}H(P)\\,h$: paraboloide en un extremo, silla en un punto de silla.")}</p></div>
      <div class="bloque"><label class="t">Capas</label><label class="chk"><input type="checkbox" id="cTray" checked> trayectorias de descenso</label>
        <label class="chk"><input type="checkbox" id="cCurv" checked> curvas principales (autovectores)</label><label class="chk"><input type="checkbox" id="cSup" checked> superficie</label>
        <label class="chk"><input type="checkbox" id="cRec" checked> recortar la superficie a ${fmt(zLow, 3)} ≤ z ≤ ${fmt(zCap, 3)}</label></div>
    </div></div></div>`;
  const EPS = 0.012 * (zmax - zmin), up = a => a.map(v => dentro(v) ? v + EPS : null);
  const Zc = recorta(D.z);
  /* recorte limpio: fuera de [zLow, zCap] la superficie se aplana en el borde y se vuelve transparente */
  const Sb = D.z_rango || D.z, scV = Sb.flat().filter((v, k) => v !== null && Zc[Math.floor(k / D.x.length)][k % D.x.length] !== null);
  const scMin = Math.min(...scV), scMax = Math.max(...scV), SEN = scMin - 0.03 * ((scMax - scMin) || 1);
  const Zs = D.z.map(f => f.map(v => v === null ? null : Math.min(zCap, Math.max(zLow, v))));
  const Sc = Sb.map((f, i) => f.map((v, j) => Zc[i][j] === null ? SEN : v));
  const OPAC = [[0, 0], [0.02, 0], [0.03, 1], [1, 1]];
  const tr = [{type:"surface", x:D.x, y:D.y, z:Zs, surfacecolor:Sc, cmin:SEN, cmax:scMax, opacityscale:OPAC,
    colorscale:TERRA3D, opacity:1, showscale:false, name:"z = f", hoverinfo:"x+y+z",
    lighting:{ambient:0.78, diffuse:0.5, specular:0.06, roughness:0.95, fresnel:0.1}}];
  tr.push({type:"scatter3d", mode:"markers+text", x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.coords[1]), z:D.puntos.map(p => p.f),
    text:D.puntos.map(p => p.id), textposition:"top center", textfont:{color:COLOR.tx, size:13},
    marker:{size:9, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos críticos"});
  tr[1].z = up(tr[1].z);
  const cx = [], cy = [], cz = [], nx = [], ny = [], nz = [];
  D.puntos.forEach(p => (p.curvas_principales || []).forEach(c => { const [a, b, d] = c.lam >= 0 ? [cx, cy, cz] : [nx, ny, nz];
    a.push(...c.x, null); b.push(...c.y, null); d.push(...up(c.z), null); }));
  const iCurv = tr.length;
  tr.push({type:"scatter3d", mode:"lines", x:cx, y:cy, z:cz, line:{color:LAM_POS, width:8}, name:"dirección con λ > 0 (sube)", hoverinfo:"skip"});
  tr.push({type:"scatter3d", mode:"lines", x:nx, y:ny, z:nz, line:{color:LAM_NEG, width:8}, name:"dirección con λ < 0 (baja)", hoverinfo:"skip"});
  const tx = [], ty = [], tz = [];
  bol.forEach(l => { tx.push(...l.x, null); ty.push(...l.y, null); tz.push(...up(l.z), null); });
  const iTray = tr.length;
  tr.push({type:"scatter3d", mode:"lines", x:tx, y:ty, z:tz, line:{color:OSCURO ? "rgba(240,225,210,.45)" : "rgba(60,35,25,.35)", width:2}, name:"trayectorias −∇f", hoverinfo:"skip"});
  const minimos = D.puntos.filter(p => p.clasificacion === "mínimo local");
  const colB = bol.map(l => l.destino === null ? "#ffffff" : CUENCAS[l.destino % CUENCAS.length]);
  const iBol = tr.length;
  tr.push({type:"scatter3d", mode:"markers", x:[], y:[], z:[], marker:{size:6, color:colB, line:{color:"#fff", width:1.5}}, name:"bolitas", hoverinfo:"skip"});
  const iPlano = tr.length;
  tr.push({type:"surface", x:[x0, x1], y:[y0, y1], z:[[c0, c0], [c0, c0]], colorscale:[[0, "#f0d3bd"], [1, "#f0d3bd"]], showscale:false,
    opacity:0.45, hoverinfo:"skip", name:"plano z = c", visible:false});
  const iNivel = tr.length;
  tr.push({type:"scatter3d", mode:"lines", x:[], y:[], z:[], line:{color:"#ffffff", width:7}, name:"curva de nivel f = c", hoverinfo:"skip"});
  const iTay = tr.length;
  opts.forEach(p => tr.push({type:"surface", x:p.taylor.x, y:p.taylor.y, z:p.taylor.z, visible:false, showscale:false, opacity:0.85,
    colorscale:[[0, LAM_NEG], [1, "#bcd2d8"]], name:"Taylor " + p.id, hoverinfo:"skip"}));
  const g3 = reg("g3d", $id("g3"));
  Plotly.newPlot(g3, tr, lay({margin:{l:0, r:0, t:10, b:0}, legend:{orientation:"h", y:0.02, x:0.02},
    scene:{xaxis:ejes3(V[0]), yaxis:ejes3(V[1]), zaxis:Object.assign(ejes3("f"), {range:[zmin - 0.04 * (zmax - zmin), zmax + 0.06 * (zmax - zmin)]}),
           aspectmode:"manual", aspectratio:{x:1, y:1, z:0.75}, camera:{eye:{x:1.25, y:-1.3, z:1.2}}}}), CFG);
  $id("cRec").onchange = e => { Plotly.restyle(g3, e.target.checked ? {z:[Zs], surfacecolor:[Sc], cmin:[SEN], cmax:[scMax], opacityscale:[OPAC]} : {z:[D.z], surfacecolor:[Sb], cmin:[null], cmax:[null], opacityscale:[null]}, [0]);
    Plotly.relayout(g3, {"scene.zaxis.autorange": !e.target.checked, "scene.zaxis.range": e.target.checked ? [zmin - 0.04 * (zmax - zmin), zmax + 0.06 * (zmax - zmin)] : undefined}); };
  const pos = t => { const X = [], Y = [], Z = [], C = [];
    bol.forEach((l, j) => { let k = Math.min(t, l.x.length - 1); while (k > 0 && l.z[k] === null) k--;
      if (dentro(l.z[k])) { X.push(l.x[k]); Y.push(l.y[k]); Z.push(l.z[k] + 1.5 * EPS); C.push(colB[j]); } });
    return [X, Y, Z, C]; };
  const paso = t => { const [X, Y, Z, C] = pos(t); Plotly.restyle(g3, {x:[X], y:[Y], z:[Z], "marker.color":[C]}, [iBol]);
    const lleg = bol.filter(l => l.destino !== null && t >= l.x.length - 1).length, tot = bol.filter(l => l.destino !== null).length;
    $id("lT").innerHTML = `paso t = ${t} / ${T - 1}<br>bolitas: ${bol.length}<br>llegaron a un mínimo: ${lleg} / ${tot}` +
      (minimos.length ? "<br>" + minimos.map((m, i) => `<span style="color:${CUENCAS[i % CUENCAS.length]}">●</span> cuenca de ${m.id}`).join(" &nbsp;") : ""); };
  const parar = reproductor($id("bDesc"), $id("sT"), paso, 1); paso(0);
  $id("bRein").onclick = () => { parar(); $id("sT").value = 0; paso(0); };
  const nivel = v => { const c = cDe(v);
    const [lx, ly] = nivelSegs(D.x, D.y, Zc, c);
    Plotly.restyle(g3, {x:[[x0, x1], lx], y:[[y0, y1], ly], z:[[[c, c], [c, c]], lx.map(v => v === null ? null : c + EPS)]}, [iPlano, iNivel]);
    const t = D.puntos.filter(p => Math.abs(p.f - c) < 0.003 * (zmax - zmin));
    $id("lC").innerHTML = `c = ${fmt(c, 6)}` + (t.length ? `<br><b>pasa por ${t.map(p => p.id + " (" + p.clasificacion + ")").join(", ")}</b>` : ""); };
  $id("sC").oninput = e => nivel(+e.target.value); nivel(vDe(c0));
  $id("saltos").innerHTML = D.puntos.map((p, i) => `<button class="btn mini" data-i="${i}">c = f(${p.id})</button>`).join("");
  $id("saltos").querySelectorAll("button").forEach(b => b.onclick = () => { const p = D.puntos[+b.dataset.i]; $id("sC").value = vDe(p.f); nivel(vDe(p.f)); });
  $id("sel").onchange = e => { const k = +e.target.value; if (opts.length) Plotly.restyle(g3, {visible:opts.map((_, i) => i === k)}, opts.map((_, i) => iTay + i)); };
  $id("cPlano").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [iPlano]);
  $id("cTray").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [iTray]);
  $id("cCurv").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [iCurv, iCurv + 1]);
  $id("cSup").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [0]);
}

function g3dVolumen(P) {
  const [ex, ey, ez] = D.ejes, X = [], Y = [], Z = [];
  ex.forEach(a => ey.forEach(b => ez.forEach(c => { X.push(a); Y.push(b); Z.push(c); })));
  const val = D.valor.map(v => v === null ? NaN : v);
  const fin = D.valor.filter(v => v !== null).sort((a, b) => a - b), q = t => fin[Math.floor(t * (fin.length - 1))];
  const fc = D.puntos.map(p => p.f);
  let cmin = fc.length ? Math.min(...fc) : q(0.05), cmax = fc.length ? Math.max(...fc) : q(0.6);
  const sp = Math.max((cmax - cmin) * 0.8, (q(0.6) - q(0.02)) * 0.35, 1e-6);
  cmin = Math.max(q(0.005), cmin - sp); cmax = Math.min(q(0.9), cmax + sp);
  const cDe = v => cmin + (cmax - cmin) * v / 300, vDe = c => Math.round(300 * (c - cmin) / ((cmax - cmin) || 1));
  const c0 = D.puntos.length ? D.puntos[0].f + 0.02 * (cmax - cmin) : cDe(150);
  P.innerHTML = `<div class="card"><h2>Superficies de nivel f(${V.join(", ")}) = c</h2>
    <p class="sub">En tres variables la “gráfica” vive en ℝ⁴, así que se muestran las superficies de nivel. Barre c: cerca de un mínimo la superficie es una pequeña esfera que nace en el punto; al cruzar el valor de un punto de silla la superficie cambia de forma y en ese instante tiene un vértice cónico en el punto.</p>
    <div class="visor"><div id="g3" class="plot alto"></div><div class="ctrl">
      <div class="bloque"><label class="t">Nivel c</label><button class="btn pri" id="bIso">▶ Barrer c</button>
        <input type="range" id="sIso" min="0" max="300" value="${vDe(c0)}"><div class="lectura" id="lIso"></div><div class="fila" id="saltos" style="margin-top:8px"></div></div>
      <div class="bloque"><label class="t">Capas</label><label class="chk"><input type="checkbox" id="cPts" checked> puntos críticos</label></div>
    </div></div></div>`;
  const tr = [{type:"isosurface", x:X, y:Y, z:Z, value:val, isomin:c0, isomax:c0, surface:{count:1}, showscale:false, opacity:0.55,
      colorscale:[[0, COLOR.ac], [1, COLOR.ac]], caps:{x:{show:false}, y:{show:false}, z:{show:false}},
      lighting:{ambient:0.55, diffuse:0.8, specular:0.2}, name:"f = c", hoverinfo:"skip", showlegend:true},
    {type:"scatter3d", mode:"markers+text", x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.coords[1]), z:D.puntos.map(p => p.coords[2]),
      text:D.puntos.map(p => p.id), textposition:"top center", textfont:{color:COLOR.tx, size:13},
      marker:{size:8, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos críticos"}];
  const g3 = reg("g3d", $id("g3"));
  Plotly.newPlot(g3, tr, lay({margin:{l:0, r:0, t:10, b:0}, legend:{orientation:"h", y:0.02, x:0.02},
    scene:{xaxis:ejes3(V[0]), yaxis:ejes3(V[1]), zaxis:ejes3(V[2]), aspectmode:"cube", camera:{eye:{x:1.55, y:-1.45, z:1.0}}}}), CFG);
  const iso = v => { const c = cDe(v); Plotly.restyle(g3, {isomin:[c], isomax:[c]}, [0]);
    const t = D.puntos.filter(p => Math.abs(p.f - c) < 0.004 * (cmax - cmin));
    const bajo = D.puntos.filter(p => p.f < c).map(p => p.id);
    $id("lIso").innerHTML = `c = ${fmt(c, 6)}` + (t.length ? `<br><b>pasa por ${t.map(p => p.id + " (" + p.clasificacion + ")").join(", ")}</b>` : "") +
      (bajo.length ? `<br>encierra: ${bajo.join(", ")}` : ""); };
  reproductor($id("bIso"), $id("sIso"), iso, 2); iso(vDe(c0));
  $id("saltos").innerHTML = D.puntos.map((p, i) => `<button class="btn mini" data-i="${i}">c = f(${p.id})</button>`).join("");
  $id("saltos").querySelectorAll("button").forEach(b => b.onclick = () => { const p = D.puntos[+b.dataset.i]; $id("sIso").value = vDe(p.f); iso(vDe(p.f)); });
  $id("cPts").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [1]);
}

/* ─────────── 4. Gráficos 2D ─────────── */
INIT.g2d = () => {
  const P = $id("tab-g2d");
  if (D.tipo === "sin_grafico") { P.innerHTML = `<div class="card"><h2>Sin gráfico</h2><p class="sub">Más de 3 variables.</p></div>`; return; }
  const leyenda = `<div class="leyenda"><span><i style="background:${COLOR.min}"></i>mínimo</span><span><i style="background:${COLOR.max}"></i>máximo</span><span><i style="background:${COLOR.silla}"></i>silla</span><span><i style="background:${COLOR.ind}"></i>indeterminado</span><span><i style="background:${COLOR.sing}"></i>no diferenciable</span></div>`;
  if (D.tipo === "1d") {
    P.innerHTML = `<div class="card"><h2>Gráfica de f</h2>${leyenda}<div id="g1" class="plot medio"></div></div>`;
    Plotly.newPlot(reg("g2d", $id("g1")), [{x:D.x, y:D.y, mode:"lines", line:{color:COLOR.ac, width:3}, name:"f"},
      {x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.f), mode:"markers+text", text:D.puntos.map(p => p.id), textposition:"top center",
       marker:{size:13, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos críticos"}],
      lay({xaxis:{title:{text:V[0]}, gridcolor:COLOR.bd}, yaxis:{title:{text:"f"}, gridcolor:COLOR.bd}}), CFG);
    return;
  }
  if (D.tipo === "3d_volumen") {
    P.innerHTML = `<div class="card"><h2>Cortes planos de f</h2><p class="sub">Curvas de nivel de f en los tres planos que pasan por el punto elegido.</p>
      <div style="max-width:320px;margin-bottom:12px"><select id="selC">${D.puntos.map((p, i) => `<option value="${i}">${p.id} ${p.etiqueta} — ${p.clasificacion}</option>`).join("")}</select></div>
      <div class="grid2" id="cortes"></div></div>`;
    const divs = [0, 1, 2].map(() => { const d = document.createElement("div"); d.className = "plot medio"; $id("cortes").appendChild(d); return reg("g2d", d); });
    const dibuja = () => { const k = +$id("selC").value || 0, cs = D.cortes[Math.min(k, D.cortes.length - 1)];
      cs.forEach((c, n) => {
        const fl = c.z.flat().filter(v => v !== null).sort((u, w) => u - w), q = t => fl[Math.floor(t * (fl.length - 1))];
        const en = D.puntos.filter(p => Math.abs(p.coords[c.fijo] - c.valor_fijo) < 1e-9);
        Plotly.react(divs[n], [{type:"contour", x:c.A, y:c.B, z:c.z, colorscale:TERRA, zmin:q(0), zmax:q(0.75), ncontours:30,
            contours:{coloring:"heatmap", showlines:true}, line:{width:0.4, color:"rgba(255,255,255,.3)"}, colorbar:{thickness:12}},
          {type:"scatter", mode:"markers+text", x:en.map(p => p.coords[c.a]), y:en.map(p => p.coords[c.b]), text:en.map(p => p.id), textposition:"top right",
           textfont:{color:"#fff"}, marker:{size:13, color:en.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:en.map(hov), hoverinfo:"text"}],
          lay({showlegend:false, title:{text:`corte ${V[c.fijo]} = ${fmt(c.valor_fijo, 4)}`, font:{size:13}}, margin:{l:50, r:10, t:40, b:44},
               xaxis:{title:{text:V[c.a]}, gridcolor:COLOR.bd}, yaxis:{title:{text:V[c.b]}, gridcolor:COLOR.bd, scaleanchor:"x"}}), CFG); }); };
    $id("selC").onchange = dibuja; dibuja(); return;
  }
  P.innerHTML = `<div class="card"><h2>Curvas de nivel, flujo del gradiente y cuencas de atracción</h2>
    <p class="sub">Colores por cuantiles de f. Cada línea sigue −∇f y su color indica a qué mínimo cae. En cada punto: direcciones principales de H (ocre λ &gt; 0, petróleo λ &lt; 0). La línea blanca discontinua es la curva de nivel que pasa por cada punto crítico.</p>${leyenda}
    <div id="g2" class="plot"></div></div>
    <div class="card"><h2>Mapa del discriminante D(x, y)</h2><p class="sub">Dónde la superficie tiene forma de cuenco, de cúpula o de silla.</p>
    <div class="leyenda"><span><i style="background:#8fb3bd"></i>D &gt; 0, f<sub>xx</sub> &gt; 0 (cuenco ∪)</span><span><i style="background:#e0a58a"></i>D &gt; 0, f<sub>xx</sub> &lt; 0 (cúpula ∩)</span><span><i style="background:#c3a8bd"></i>D &lt; 0 (silla)</span><span><i style="background:#ddd3c8"></i>D = 0</span></div>
    <div id="g4" class="plot medio"></div></div>`;
  const cb = D.ticks_color ? {title:{text:"f"}, tickvals:D.ticks_color.vals, ticktext:D.ticks_color.text, thickness:14} : {title:{text:"f"}};
  const tr = [{type:"contour", x:D.x, y:D.y, z:D.z_rango || D.z, text:D.z, colorscale:TERRA, ncontours:36, colorbar:cb,
    contours:{coloring:"heatmap", showlines:true}, line:{width:0.4, color:"rgba(255,255,255,.3)"}, name:"f",
    hovertemplate:"x = %{x:.3f}<br>y = %{y:.3f}<br>f = %{text}<extra></extra>"}];
  const grupos = {};
  D.flujo.forEach(l => { const k = l.destino === null ? "x" : l.destino; (grupos[k] = grupos[k] || {x:[], y:[]}); grupos[k].x.push(...l.x, null); grupos[k].y.push(...l.y, null); });
  const minimos = D.puntos.filter(p => p.clasificacion === "mínimo local");
  Object.entries(grupos).forEach(([k, g]) => tr.push({type:"scatter", mode:"lines", x:g.x, y:g.y, hoverinfo:"skip",
    line:{width:1.3, color:k === "x" ? "rgba(255,245,235,.55)" : CUENCAS[k % CUENCAS.length]}, name:k === "x" ? "flujo −∇f (sin mínimo)" : `cuenca de ${minimos[k] ? minimos[k].id : k}`}));
  D.familias.forEach(f => tr.push({type:"scatter", mode:"lines", x:f.x, y:f.y, line:{color:COLOR.sing, width:5, dash:"dot"}, name:"familia crítica"}));
  [...new Set(D.niveles_criticos)].forEach((lv, i) => tr.push({type:"contour", x:D.x, y:D.y, z:D.z, showscale:false, hoverinfo:"skip",
    contours:{coloring:"none", start:lv, end:lv, size:1}, line:{color:"#fff", width:2, dash:"dash"}, name:"nivel f = f(P)", showlegend:i === 0}));
  D.puntos.forEach(p => (p.curvas_testigo || []).forEach(c => tr.push({type:"scatter", mode:"lines", x:c.x, y:c.y,
    line:{color:c.comportamiento === "sube" ? "#8fa06a" : c.comportamiento === "baja" ? "#e07a52" : COLOR.sing, width:4}, name:`curva de prueba (${c.comportamiento})`})));
  const L = (D.rango[0][1] - D.rango[0][0]) * 0.07;
  D.puntos.forEach(p => {
    (p.autovectores || []).forEach((v, j) => { const lam = p.autovalores[j];
      tr.push({type:"scatter", mode:"lines", x:[p.coords[0] - L * v[0], p.coords[0] + L * v[0]], y:[p.coords[1] - L * v[1], p.coords[1] + L * v[1]],
        line:{color:lam > 0 ? LAM_POS : lam < 0 ? LAM_NEG : "#bdb2a6", width:5}, hoverinfo:"text", text:`λ = ${fmt(lam, 4)}`, showlegend:false}); });
    tr.push({type:"scatter", mode:"markers+text", x:[p.coords[0]], y:[p.coords[1]], text:[p.id], textposition:"top right", textfont:{color:"#fff", size:13},
      marker:{size:15, color:colorPunto(p), line:{color:"#fff", width:2}}, hovertext:[hov(p)], hoverinfo:"text", showlegend:false});
  });
  Plotly.newPlot(reg("g2d", $id("g2")), tr, lay({xaxis:{title:{text:V[0]}, range:D.rango[0], constrain:"domain", gridcolor:COLOR.bd},
    yaxis:{title:{text:V[1]}, range:D.rango[1], scaleanchor:"x", constrain:"domain", gridcolor:COLOR.bd}}), CFG);
  const cs = [[0, "#c3a8bd"], [0.33, "#c3a8bd"], [0.33, "#ddd3c8"], [0.5, "#ddd3c8"], [0.5, "#8fb3bd"], [0.75, "#8fb3bd"], [0.75, "#e0a58a"], [1, "#e0a58a"]];
  Plotly.newPlot(reg("g2d", $id("g4")), [{type:"heatmap", x:D.x, y:D.y, z:D.clase_D, zmin:-1, zmax:2, colorscale:cs, showscale:false, hoverinfo:"skip"},
    {type:"contour", x:D.x, y:D.y, z:D.z, contours:{coloring:"none"}, line:{color:"rgba(43,36,32,.35)", width:1}, ncontours:18, showscale:false, hoverinfo:"skip", showlegend:false},
    {type:"scatter", mode:"markers+text", x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.coords[1]), text:D.puntos.map(p => p.id), textposition:"top right",
     marker:{size:13, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", showlegend:false}],
    lay({showlegend:false, xaxis:{title:{text:V[0]}, range:D.rango[0], constrain:"domain"}, yaxis:{title:{text:V[1]}, range:D.rango[1], scaleanchor:"x", constrain:"domain"}}), CFG);
};
