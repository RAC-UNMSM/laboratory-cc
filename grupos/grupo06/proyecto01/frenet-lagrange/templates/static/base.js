/* Utilidades comunes: KaTeX, pestañas, visor JSON, reproductor (lo usan los tres métodos) */
/* ───────── utilidades comunes ───────── */
const $id = i => document.getElementById(i);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const COLOR = {min:css("--min"), max:css("--max"), silla:css("--silla"), ind:css("--ind"), sing:css("--sing"), ac:css("--ac"),
               ac2:css("--ac2"), sand:css("--sand"), tx:css("--tx"), mu:css("--mu"), bd:css("--bd"), soft:css("--soft")};
const TERRA = [[0,"#2c2420"],[0.15,"#4c2c21"],[0.32,"#7a3a24"],[0.5,"#ab4f2c"],[0.67,"#cf8660"],[0.83,"#e7bf9e"],[1,"#f7ece0"]];
const TERRA3D = [[0,"#3b1f17"],[0.2,"#6a3020"],[0.42,"#a0462a"],[0.62,"#c86d45"],[0.82,"#e3a47c"],[1,"#f1cfae"]];
const CUENCAS = ["#3f6e7d","#6b7a4f","#a07b4f","#5f6f8a","#8a5a44","#7a5873","#4f7d6a"];
const OSCURO = matchMedia("(prefers-color-scheme: dark)").matches;
const MACROS = {"\\R":"\\mathbb{R}"};
const tex = (s, d) => { try { return katex.renderToString(String(s), {displayMode:!!d, throwOnError:false, macros:MACROS}); } catch(e) { return String(s); } };
const esc = s => String(s).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const mt = s => String(s).replace(/\$\$([^$]+)\$\$/g, (_, m) => tex(m, true)).replace(/\$([^$]+)\$/g, (_, m) => tex(m))
                         .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<i>$2</i>");
const eq = s => `<div class="eq">${tex(s, true)}</div>`;
const fmt = (v, p) => (v === null || v === undefined) ? "—" : (+v).toPrecision(p || 5).replace(/\.?0+(e|$)/, "$1");
const ejes3 = (t) => ({title:{text:t}, backgroundcolor:OSCURO ? "#221d19" : "#f8f2eb", showbackground:true, gridcolor:COLOR.bd, zerolinecolor:COLOR.mu});
const lay = extra => Object.assign({paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)",
    font:{family:"Inter, sans-serif", color:COLOR.tx, size:12}, margin:{l:52, r:20, t:20, b:44},
    legend:{orientation:"h", y:-0.14, font:{size:12}}, hoverlabel:{font:{family:"JetBrains Mono, monospace", size:12}},
    xaxis:{gridcolor:COLOR.bd, zerolinecolor:COLOR.mu}, yaxis:{gridcolor:COLOR.bd, zerolinecolor:COLOR.mu}}, extra || {});
const CFG = {responsive:true, displaylogo:false, modeBarButtonsToRemove:["lasso2d", "select2d"]};
/* ───────── pestañas (los gráficos se construyen al abrir su pestaña) ───────── */
const INIT = {}, HECHO = {}, PLOTS = {};
function mostrar(id) {
  if (!document.getElementById("tab-" + id)) id = "resumen";
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("activo", b.dataset.tab === id));
  document.querySelectorAll(".panel").forEach(p => p.classList.toggle("activo", p.id === "tab-" + id));
  if (!HECHO[id] && INIT[id]) { HECHO[id] = true; INIT[id](); }
  else (PLOTS[id] || []).forEach(d => Plotly.Plots.resize(d));
  try { history.replaceState(null, "", "#" + id); } catch (e) {}
}
document.querySelectorAll(".tab").forEach(b => b.onclick = () => mostrar(b.dataset.tab));

const reg = (tab, div) => ((PLOTS[tab] = PLOTS[tab] || []).push(div), div);
/* ───────── visor JSON ───────── */
function hojaJ(v) {
  if (v === null) return `<span class="jz">null</span>`;
  if (typeof v === "string") return `<span class="js">"${esc(v)}"</span>`;
  if (typeof v === "number") return `<span class="jn">${v}</span>`;
  return `<span class="jb">${v}</span>`;
}
function nodoJ(v, k, nivel) {
  const kk = k === undefined ? "" : `<span class="jk">"${esc(k)}"</span>: `;
  if (v === null || typeof v !== "object") return `<div>${kk}${hojaJ(v)}</div>`;
  const arr = Array.isArray(v), n = arr ? v.length : Object.keys(v).length, a = arr ? "[" : "{", c = arr ? "]" : "}";
  if (n === 0) return `<div>${kk}${a}${c}</div>`;
  if (arr && n <= 8 && v.every(x => x === null || typeof x !== "object")) return `<div>${kk}[${v.map(hojaJ).join(", ")}]</div>`;
  let hijos;
  if (arr && n > 40) hijos = `<div class="jc">… ${n} elementos, se muestran los 12 primeros …</div>` + v.slice(0, 12).map(x => nodoJ(x, undefined, nivel + 1)).join("");
  else hijos = (arr ? v.map(x => nodoJ(x, undefined, nivel + 1)) : Object.entries(v).map(([q, w]) => nodoJ(w, q, nivel + 1))).join("");
  return `<details ${nivel < 2 ? "open" : ""}><summary>${kk}${a} <span class="jc">${n} ${arr ? "elementos" : "claves"}</span></summary>${hijos}<div class="h">${c}</div></details>`;
}
INIT.json = () => {
  const P = $id("tab-json");
  P.innerHTML = `<div class="card"><h2>JSON generado</h2>
    <p class="sub">Salida exacta de <code>${FUNCION_MCP}</code>: es el objeto que el servidor MCP devolverá al modelo. Los valores exactos van como texto SymPy y LaTeX; los aproximados, como números.</p>
    <div class="json-bar"><button class="btn pri" id="jcop">Copiar</button><button class="btn" id="jbaj">Descargar .json</button>
    <button class="btn" id="jexp">Expandir todo</button><button class="btn" id="jcon">Contraer todo</button>
    <label class="fila" style="margin-left:auto;font-size:13px;color:var(--mu)"><input type="checkbox" id="jgra"> incluir los arreglos del gráfico</label></div>
    <div class="json" id="jarb"></div><p class="nota" id="jtam"></p></div>`;
  const obj = () => $id("jgra").checked ? Object.assign({}, R, {grafico: D}) : R;
  const pinta = () => { const o = obj(); $id("jarb").innerHTML = nodoJ(o, undefined, 0);
    $id("jtam").textContent = `Tamaño: ${(JSON.stringify(o).length / 1024).toFixed(1)} KB · ${Object.keys(o).length} claves de primer nivel`; };
  pinta(); $id("jgra").onchange = pinta;
  $id("jcop").onclick = () => { const t = JSON.stringify(obj(), null, 2), b = $id("jcop");
    const ok = () => { b.textContent = "¡Copiado!"; setTimeout(() => b.textContent = "Copiar", 1600); };
    if (navigator.clipboard) navigator.clipboard.writeText(t).then(ok, () => respaldo(t, ok)); else respaldo(t, ok); };
  const respaldo = (t, ok) => { const a = document.createElement("textarea"); a.value = t; document.body.appendChild(a); a.select();
    try { document.execCommand("copy"); ok(); } catch (e) {} a.remove(); };
  $id("jbaj").onclick = () => { const b = new Blob([JSON.stringify(obj(), null, 2)], {type:"application/json"});
    const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = NOMBRE_JSON; a.click(); };
  $id("jexp").onclick = () => $id("jarb").querySelectorAll("details").forEach(d => d.open = true);
  $id("jcon").onclick = () => $id("jarb").querySelectorAll("details").forEach(d => d.open = false);
};
/* ───────── reproductor genérico (botón ▶ + slider) ───────── */
function reproductor(boton, slider, alCambiar, paso) {
  let t = null;
  const parar = () => { clearInterval(t); t = null; boton.textContent = "▶ Reproducir"; };
  boton.onclick = () => {
    if (t) return parar();
    boton.textContent = "⏸ Pausar";
    t = setInterval(() => { let v = +slider.value + (paso || 1); if (v > +slider.max) v = +slider.min;
      slider.value = v; alCambiar(v); }, 40);
  };
  slider.oninput = () => alCambiar(+slider.value);
  return parar;
}
