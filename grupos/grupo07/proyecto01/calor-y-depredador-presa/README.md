# Servidor MCP: Dinámica de Poblaciones, Difusión Térmica y Decaimiento

Servidor MCP desarrollado por el **Grupo 07** para la simulación numérica, visualización y generación de reportes HTML de ecuaciones diferenciales ordinarias (EDOs) y parciales (EDPs).

## Herramientas expuestas (`Tools`)
1. **`simular_lotka_volterra`**: Resuelve el sistema no lineal acoplado presa-depredador y genera series temporales y plano de fase.
2. **`simular_calor_2d`**: Resuelve la ecuación parabólica del calor en una placa 2D mediante diferencias finitas explícitas.
3. **`simular_decaimiento`**: Calcula la solución analítica del decaimiento radiactivo exponencial de primer orden.

## Ejecución con Docker
```bash
docker compose up --build