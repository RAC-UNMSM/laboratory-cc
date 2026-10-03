from __future__ import annotations
from typing import Iterable

def _normalize_points(points):
    if not isinstance(points, list):
        raise ValueError("Los puntos deben ser una lista.")
    clean = []
    for p in points:
        if isinstance(p, dict):
            x, y = p.get("x"), p.get("y")
        else:
            x, y = p[0], p[1]
        x, y = float(x), float(y)
        clean.append((x, y))

    if len(clean) < 2:
        raise ValueError("Se necesitan al menos 2 puntos.")
    xs = [p[0] for p in clean]
    if len(set(xs)) != len(xs):
        raise ValueError("Los valores de x no pueden repetirse.")
    return clean

def lagrange(points, x_eval):
    points = _normalize_points(points)
    x_eval = float(x_eval)
    total = 0.0
    basis = []
    for i, (xi, yi) in enumerate(points):
        li = 1.0
        for j, (xj, _) in enumerate(points):
            if i != j:
                li *= (x_eval - xj) / (xi - xj)
        basis.append(li)
        total += yi * li
    return total, basis

def divided_differences(points):
    points = _normalize_points(points)
    xs = [p[0] for p in points]
    table = [[p[1] for p in points]]

    for order in range(1, len(points)):
        previous = table[-1]
        current = []
        for i in range(len(previous) - 1):
            current.append((previous[i + 1] - previous[i]) / (xs[i + order] - xs[i]))
        table.append(current)
    return xs, table

def newton(points, x_eval):
    xs, table = divided_differences(points)
    x_eval = float(x_eval)
    value = table[0][0]
    product = 1.0
    for order in range(1, len(xs)):
        product *= (x_eval - xs[order - 1])
        value += table[order][0] * product
    return value, table

def polynomial_coefficients(points):
    # Construcción del polinomio en base monomial mediante productos
    # de (x - xj), sin depender de NumPy.
    points = _normalize_points(points)
    coeffs = [0.0]  # constante primero

    def add_poly(a, b):
        n = max(len(a), len(b))
        out = [0.0] * n
        for i, v in enumerate(a): out[i] += v
        for i, v in enumerate(b): out[i] += v
        return out

    def scale(a, s):
        return [v * s for v in a]

    for i, (xi, yi) in enumerate(points):
        basis = [1.0]
        denominator = 1.0
        for j, (xj, _) in enumerate(points):
            if i == j:
                continue
            # basis *= (x - xj)
            new = [0.0] * (len(basis) + 1)
            for k, c in enumerate(basis):
                new[k] += -xj * c
                new[k + 1] += c
            basis = new
            denominator *= (xi - xj)
        term = scale(basis, yi / denominator)
        coeffs = add_poly(coeffs, term)

    return coeffs

def format_polynomial(coeffs):
    pieces = []
    for power, coef in reversed(list(enumerate(coeffs))):
        if abs(coef) < 1e-10:
            continue
        sign = "-" if coef < 0 else "+"
        value = abs(coef)
        if power == 0:
            body = f"{value:.4g}"
        elif power == 1:
            body = "x" if abs(value - 1) < 1e-10 else f"{value:.4g}x"
        else:
            body = f"x^{power}" if abs(value - 1) < 1e-10 else f"{value:.4g}x^{power}"
        if not pieces:
            pieces.append(("-" if coef < 0 else "") + body)
        else:
            pieces.append(f" {sign} {body}")
    return "".join(pieces) if pieces else "0"

def curve_data(points, coeffs, samples=160):
    xs = [p[0] for p in points]
    lo, hi = min(xs), max(xs)
    if lo == hi:
        lo -= 1
        hi += 1

    def evaluate_coeffs(x):
        value = 0.0
        for c in reversed(coeffs):
            value = value * x + c
        return value

    x_values = [lo + (hi - lo) * i / (samples - 1) for i in range(samples)]
    return x_values, [evaluate_coeffs(x) for x in x_values]

def solve_interpolation(points, x_eval, method="lagrange"):
    points = _normalize_points(points)
    x_eval = float(x_eval)

    lag_value, basis = lagrange(points, x_eval)
    newton_value, table = newton(points, x_eval)
    coeffs = polynomial_coefficients(points)
    polynomial = format_polynomial(coeffs)
    curve_x, curve_y = curve_data(points, coeffs)

    value = lag_value if method.lower() == "lagrange" else newton_value
    difference = abs(lag_value - newton_value)

    rows = []
    xs, dd = divided_differences(points)
    for i, x in enumerate(xs):
        row = {"x": x, "f": points[i][1]}
        for order in range(1, len(xs) - i):
            row[f"d{order}"] = dd[order][i]
        rows.append(row)

    return {
        "method": "Lagrange" if method.lower() == "lagrange" else "Newton",
        "value": value,
        "lagrange_value": lag_value,
        "newton_value": newton_value,
        "difference": difference,
        "error": difference,
        "polynomial": polynomial,
        "coefficients": coeffs,
        "basis": basis,
        "points": [{"x": x, "y": y} for x, y in points],
        "curve": {"x": curve_x, "y": curve_y},
        "difference_table": rows,
        "divided_differences": dd,
    }
