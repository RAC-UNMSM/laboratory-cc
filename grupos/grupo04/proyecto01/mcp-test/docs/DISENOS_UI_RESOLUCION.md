# Diseños de las páginas resolutivas

## 1. Marco común

Encabezado con familia, método, estado y resumen de entrada. La primera vista prioriza resultado y diagnóstico. Pestañas: **Resultado, Desarrollo, Tabla, Gráfica, Diagnóstico e Informe**. Adaptar a escritorio/móvil, permitir desplazamiento de tablas, rotular unidades y no depender solo del color.

Estados: éxito; éxito con advertencias; no convergió; entrada inválida; límite excedido; informe no disponible. No mostrar guiones silenciosos como si fueran resultados.

## 2. Raíces

**Entrada:** función permitida, intervalo/punto inicial, método, tolerancia y máximo de iteraciones. **Resumen:** raíz y f(raíz). **Desarrollo:** k, x, f(x), paso/error y criterio. **Gráfica:** función, raíz e intervalo; Newton/secante muestran la secuencia de aproximaciones. **Diagnóstico:** convergencia, parada y sensibilidad inicial. No ejecutar código arbitrario.

## 3. Sistemas lineales

**Entrada:** matriz A, vector b, método, tolerancia. **Resumen:** solución y norma del residuo. **Desarrollo:** eliminación/factorización o tabla iterativa. **Gráfica:** norma del residuo por iteración. **Diagnóstico:** matriz singular, pivote pequeño, condicionamiento y límites. En matrices dispersas resumir dimensiones y elementos no nulos.

## 4. Interpolación y ajuste

**Entrada:** puntos, método, x a evaluar; para ajuste, familia/grado. **Resumen:** polinomio, aproximante y valor. **Desarrollo:** bases de Lagrange o tabla de diferencias divididas. **Gráfica:** puntos, curva y evaluación. **Diagnóstico:** interpolación frente a extrapolación, oscilación, residuos y métricas; en splines, tramos y continuidad.

## 5. Derivación

**Entrada:** función/tabla, x, h y fórmula. **Resumen:** derivada, orden y paso. **Desarrollo:** fórmula sustituida y valores usados. **Tabla/gráfica:** aproximaciones con varios h, función, tangente y punto. **Diagnóstico:** truncamiento frente a redondeo.

## 6. Integración

**Entrada:** función/tabla, límites, subintervalos, regla. **Resumen:** integral y error estimado. **Desarrollo:** nodos, pesos y contribuciones. **Gráfica:** área aproximada y paneles. **Diagnóstico:** requisitos de Simpson, discontinuidades y dominio inválido.

## 7. Ecuaciones diferenciales ordinarias

**Entrada:** ecuación/sistema admitido, condición inicial, intervalo, paso/tolerancia y método. **Resumen:** estado final y variables. **Tabla:** t, y, derivadas y error. **Gráfica:** serie por variable. **Diagnóstico:** pasos adaptativos aceptados/rechazados y rigidez. La gráfica no se presenta como prueba de exactitud.

## 8. Valores propios

**Entrada:** matriz y método. **Resumen:** valores/vectores y residuo ||Av−λv||. **Desarrollo:** iteraciones y criterio. **Gráfica:** convergencia o magnitudes. **Diagnóstico:** multiplicidad probable y convergencia lenta.

## 9. Optimización

**Entrada:** función permitida, punto inicial y método. La versión implementada es no restringida. **Resumen:** punto, objetivo, gradiente y estado. **Tabla/gráfica:** iteraciones y trayectoria; curvas de nivel si hay dos variables. **Diagnóstico:** mínimo local, falta de descenso y escala.

## 10. Frontera y PDE

Primera versión 1D. **Entrada:** ecuación, dominio, malla y condiciones. **Resumen:** solución nodal y estabilidad. **Desarrollo:** esquema discretizado. **Gráfica:** perfil espacial; calor/onda muestran mapa espacio-tiempo y cortes. **Diagnóstico:** refinamiento y estabilidad. Nombrar supuestos y rechazar formatos fuera del alcance.

## 11. Informe

Pestaña con estado, preview PDF y botón descargar. Si el host no permite visor integrado, ofrecer abrir/descargar. Un fallo de PDF no oculta el resultado. La interfaz debe aceptar structuredContent, JSON textual y bloques de texto.

## 12. Punto flotante y propagación de incertidumbre

**Entrada:** operaciones de suma/redondeo o dos mediciones con incertidumbres absolutas. **Resumen:** aproximaciones float, suma compensada o valor e incertidumbre propagada. **Tabla/gráfica:** acumulación por término y error de redondeo. **Diagnóstico:** cancelación y supuesto de independencia/linealización; no presentar como cota rigurosa.

## Presentación inicial e intermedia

La UI numérica muestra familia, método, estado y nivel. El panel de resultado incluye una interpretación breve adaptada a raíces, sistemas, condicionamiento, EDO, PDE, integración y optimización. Las pestañas de desarrollo, tablas, gráficas, diagnóstico y PDF conservan los datos específicos que entrega cada método.

El nivel inicial explica qué significa el resultado y cómo leerlo. El nivel intermedio conserva además iteraciones, residuos, error estimado, factibilidad o estabilidad cuando el algoritmo los calcula. No se inventan campos ausentes. Si la respuesta MCP viene en una envoltura no reconocida, la interfaz lo indica y muestra una parte del contenido recibido en lugar de dejar guiones silenciosos.

Las gráficas 2D etiquetan sus ejes; el PDF dibuja líneas mediante trazos vectoriales y reduce mapas de calor a una cuadrícula de presentación de hasta 30 por 30.
