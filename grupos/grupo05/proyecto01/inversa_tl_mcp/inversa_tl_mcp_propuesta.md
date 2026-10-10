# Inversa de una transformación lineal

## Tema

Sistema MCP para el análisis de invertibilidad y cálculo paso a paso de la inversa de transformaciones lineales de R^n en R^n.

## Descripción

El proyecto recibe la dimensión y la regla de correspondencia de una transformación lineal. Valida la entrada, construye la matriz estándar a partir de las imágenes de la base canónica y calcula su determinante para determinar si la transformación es invertible.

Cuando la transformación es invertible, calcula la matriz inversa mediante el método de Gauss-Jordan mostrando las operaciones elementales paso a paso. Luego construye la regla de correspondencia de T^(-1) y verifica las composiciones T(T^(-1)(x)) = x y T^(-1)(T(x)) = x.

El sistema está implementado como un servidor MCP modular, con separación entre validación, cálculo matricial, Gauss-Jordan, construcción de la transformación inversa, presentación, almacenamiento y visualización.

## Herramienta MCP

- calcular_inversa_tl: analiza una transformación T: R^n -> R^n y, cuando es invertible, obtiene su inversa paso a paso.

## Límites de cómputo

El servidor limita la dimensión máxima y la complejidad de las expresiones recibidas para evitar solicitudes excesivamente costosas.
