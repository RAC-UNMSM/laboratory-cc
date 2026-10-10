# Historial de cambios

## 0.2.0 — Ampliación inicial a Métodos Numéricos I y II
- Se mantienen las herramientas Newton/Lagrange.
- Se agrega análisis de punto flotante/redondeo, error y propagación, raíces, sistemas densos/dispersos, ajustes QR/SVD, derivación e integración de funciones/tablas, ODE, valores propios, optimización, BVP y PDE 1D.
- Se añade evaluador seguro de expresiones, contrato común de resultados y vista genérica.
- Se agrega solver disperso COO/CSR para CG y GMRES, además de informes PDF ReportLab para las nuevas familias y enlaces preview/download.
- requirements.txt incorpora NumPy, SciPy y ReportLab; Dockerfile copia el módulo nuevo.
- storage.py y reports_data conservan informes.

## Límites conocidos
Matrices densas; BVP finite_difference solo y''=f(x); PDE limitada a calor/onda explícitos y Laplace 1D; no hay PDE 2D ni fuente.


## 2026-10-10 — 27 herramientas y verificación integrada

- Agregadas siete tools de Métodos Numéricos II y docstrings MCP descriptivos para las 27.
- Corregido `resolver_pde`; normalizada la salida de interpolación y el nivel inicial/intermedio.
- Migrados los PDF de interpolación a ReportLab, serializado su renderizado y validada la vista previa/descarga.
- Adaptadas la UI, Docker y las guías; build y llamadas MCP reales completados.
