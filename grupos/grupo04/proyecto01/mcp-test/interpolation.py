from __future__ import annotations
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
            value = (
                previous[i + 1] - previous[i]
            ) / (
                xs[i + order] - xs[i]
            )
            current.append(value)
        table.append(current)
    return xs, table
def newton(points, x_eval):
    xs, table = divided_differences(points)
    x_eval = float(x_eval)
    value = table[0][0]
    product = 1.0
    for order in range(1, len(xs)):
        product *= x_eval - xs[order - 1]
        value += table[order][0] * product
    return value, table
def polynomial_coefficients(points):
    points = _normalize_points(points)
    coeffs = [0.0]
    def add_poly(a, b):
        n = max(len(a), len(b))
        out = [0.0] * n
        for i, v in enumerate(a):
            out[i] += v
        for i, v in enumerate(b):
            out[i] += v
        return out
    def scale(poly, scalar):
        return [v * scalar for v in poly]
    for i, (xi, yi) in enumerate(points):
        basis = [1.0]
        denominator = 1.0
        for j, (xj, _) in enumerate(points):
            if i == j:
                continue
            new_basis = [0.0] * (len(basis) + 1)
            for k, c in enumerate(basis):
                new_basis[k] += -xj * c
                new_basis[k + 1] += c
            basis = new_basis
            denominator *= xi - xj
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
            body = f"{value:.6g}"
        elif power == 1:
            body = (
                "x"
                if abs(value - 1) < 1e-10
                else f"{value:.6g}x"
            )
        else:
            body = (
                f"x^{power}"
                if abs(value - 1) < 1e-10
                else f"{value:.6g}x^{power}"
            )
        if not pieces:
            pieces.append(
                ("-" if coef < 0 else "") + body
            )
        else:
            pieces.append(
                f" {sign} {body}"
            )
    return "".join(pieces) if pieces else "0"
def curve_data(points, coeffs, samples=200):
    points = _normalize_points(points)
    xs = [p[0] for p in points]
    lo = min(xs)
    hi = max(xs)
    if lo == hi:
        lo -= 1
        hi += 1
    margin = (hi - lo) * 0.10
    lo -= margin
    hi += margin
    def evaluate_coeffs(x):
        value = 0.0
        for c in reversed(coeffs):
            value = value * x + c
        return value
    x_values = [
        lo + (hi - lo) * i / (samples - 1)
        for i in range(samples)
    ]
    y_values = [
        evaluate_coeffs(x)
        for x in x_values
    ]
    return x_values, y_values
def lagrange_development(points, x_eval):
    points = _normalize_points(points)
    x_eval = float(x_eval)
    development = []
    for i, (xi, yi) in enumerate(points):
        numerator_terms = []
        denominator_terms = []
        numerator = 1.0
        denominator = 1.0
        for j, (xj, _) in enumerate(points):
            if i == j:
                continue
            numerator_terms.append(
                f"({x_eval:.6g} - {xj:.6g})"
            )
            denominator_terms.append(
                f"({xi:.6g} - {xj:.6g})"
            )
            numerator *= x_eval - xj
            denominator *= xi - xj
        li = numerator / denominator
        contribution = yi * li
        development.append({
            "index": i,
            "xi": xi,
            "yi": yi,
            "numerator": " · ".join(numerator_terms),
            "denominator": " · ".join(denominator_terms),
            "basis_value": li,
            "contribution": contribution
        })
    return development
def newton_development(points):
    points = _normalize_points(points)
    xs, table = divided_differences(points)
    terms = []
    terms.append({
        "order": 0,
        "coefficient": table[0][0],
        "factors": [],
        "text": f"{table[0][0]:.6g}"
    })
    for order in range(1, len(xs)):
        coefficient = table[order][0]
        factors = [
            xs[i]
            for i in range(order)
        ]
        factor_text = "".join(
            f"(x - {x:.6g})"
            for x in factors
        )
        terms.append({
            "order": order,
            "coefficient": coefficient,
            "factors": factors,
            "text": f"{coefficient:.6g}{factor_text}"
        })
    return terms
def build_difference_table(points):
    points = _normalize_points(points)
    xs, dd = divided_differences(points)
    rows = []
    for i, x in enumerate(xs):
        row = {
            "x": x,
            "f": points[i][1]
        }
        for order in range(1, len(xs) - i):
            row[f"d{order}"] = dd[order][i]
        rows.append(row)
    return rows
def solve_interpolation(
    points,
    x_eval,
    method="lagrange"
):
    points = _normalize_points(points)
    x_eval = float(x_eval)
    method = method.lower().strip()
    if method not in ("lagrange", "newton"):
        raise ValueError(
            "El método debe ser 'lagrange' o 'newton'."
        )
    lagrange_value, basis = lagrange(
        points,
        x_eval
    )
    newton_value, dd_table = newton(
        points,
        x_eval
    )
    coeffs = polynomial_coefficients(points)
    polynomial = format_polynomial(coeffs)
    curve_x, curve_y = curve_data(
        points,
        coeffs
    )
    selected_value = (
        lagrange_value
        if method == "lagrange"
        else newton_value
    )
    difference = abs(
        lagrange_value - newton_value
    )
    return {
        "method": (
            "Lagrange"
            if method == "lagrange"
            else "Newton"
        ),
        "x_eval": x_eval,
        "value": selected_value,
        "lagrange_value": lagrange_value,
        "newton_value": newton_value,
        "difference": difference,
        "error": difference,
        "polynomial": polynomial,
        "coefficients": coeffs,
        "basis": basis,
        "points": [
            {
                "x": x,
                "y": y
            }
            for x, y in points
        ],
        "curve": {
            "x": curve_x,
            "y": curve_y
        },
        "difference_table":
            build_difference_table(points),
        "divided_differences":
            dd_table,
        "lagrange_development":
            lagrange_development(
                points,
                x_eval
            ),
        "newton_development":
            newton_development(points)
    }