/* Arranque: aviso si Plotly no cargó y apertura de la pestaña inicial */
if (!window.Plotly) {
  const aviso = `<div class="card" style="border-color:var(--ac)"><h2>No se pudo cargar la librería de gráficos</h2>
    <p class="sub">Plotly.js se descarga de internet y no respondió (sin conexión, firewall o bloqueo del navegador). Las pestañas de Resumen, Procedimiento y JSON funcionan igual.</p>
    <p>Para ver los gráficos sin internet, genera la página en modo <b>offline</b>:</p>
    <p><code>pip install plotly</code><br><code>python cli.py ${NOMBRE_JSON.replace("_resultado.json", "")} --demo 1 --html pagina.html --offline</code></p></div>`;
  INIT.g3d = () => { $id("tab-g3d").innerHTML = aviso; }; INIT.g2d = () => { $id("tab-g2d").innerHTML = aviso; };
}
mostrar(location.hash.slice(1) || "resumen");
