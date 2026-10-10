"""Algoritmos numéricos para las familias de Métodos Numéricos I y II."""
from __future__ import annotations

import ast
import math
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import gmres as sparse_gmres



_ALLOWED_FUNCTIONS = {
    name: getattr(math, name)
    for name in (
        "sin cos tan asin acos atan sinh cosh tanh exp log log10 sqrt "
        "fabs floor ceil erf"
    ).split()
}
_ALLOWED_FUNCTIONS["abs"] = abs
_ALLOWED_CONSTANTS = {"pi": math.pi, "e": math.e}
_MAX_ITEMS = 500


def finite(value: Any, label: str = "valor") -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} debe ser numérico.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} debe ser finito.")
    return number


def safe_eval(expression: str, variables: dict[str, float]) -> float:
    """Evalúa aritmética y funciones permitidas; nunca usa eval/exec."""
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("La expresión matemática está vacía.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Expresión inválida: {exc.msg}.") from exc
    if sum(1 for _ in ast.walk(tree)) > 200:
        raise ValueError("La expresión excede el tamaño permitido.")

    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return finite(node.value)
        if isinstance(node, ast.Name):
            if node.id in variables:
                return finite(variables[node.id], node.id)
            if node.id in _ALLOWED_CONSTANTS:
                return _ALLOWED_CONSTANTS[node.id]
            raise ValueError(f"Variable no definida: {node.id}.")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                value = left + right
            elif isinstance(node.op, ast.Sub):
                value = left - right
            elif isinstance(node.op, ast.Mult):
                value = left * right
            elif isinstance(node.op, ast.Div):
                value = left / right
            elif isinstance(node.op, ast.Pow):
                if abs(right) > 100:
                    raise ValueError("El exponente debe estar entre -100 y 100.")
                value = left ** right
            elif isinstance(node.op, ast.Mod):
                value = left % right
            else:
                raise ValueError("Operador no permitido en la expresión.")
            return finite(value, "resultado de la expresión")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            function = _ALLOWED_FUNCTIONS.get(node.func.id)
            if function is None or node.keywords:
                raise ValueError(f"Función no permitida: {node.func.id}.")
            args = [visit(arg) for arg in node.args]
            return finite(function(*args), "resultado de la expresión")
        raise ValueError("La expresión contiene una operación no permitida.")

    try:
        return finite(visit(tree), "resultado")
    except (ZeroDivisionError, OverflowError, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"No se pudo evaluar la expresión: {exc}.") from exc


def normalize_points(points: list[Any]) -> list[tuple[float, float]]:
    if not isinstance(points, list) or not 2 <= len(points) <= _MAX_ITEMS:
        raise ValueError(f"Se requieren entre 2 y {_MAX_ITEMS} puntos.")
    clean = []
    for index, point in enumerate(points):
        if isinstance(point, dict):
            x, y = point.get("x"), point.get("y")
        elif isinstance(point, (list, tuple)) and len(point) == 2:
            x, y = point
        else:
            raise ValueError(f"El punto {index + 1} debe tener x e y.")
        clean.append((finite(x, f"x del punto {index + 1}"),
                      finite(y, f"y del punto {index + 1}")))
    if len({x for x, _ in clean}) != len(clean):
        raise ValueError("Los valores x no pueden repetirse.")
    return sorted(clean)


def pack_result(problem_type: str, method: str, inputs: dict[str, Any],
                result: dict[str, Any], diagnostics: dict[str, Any],
                steps: list[str] | None = None,
                tables: list[dict[str, Any]] | None = None,
                charts: list[dict[str, Any]] | None = None,
                warnings: list[str] | None = None,
                status: str = "success") -> dict[str, Any]:
    return {
        "schema_version": "1.1",
        "level": "inicial",
        "problem_type": problem_type,
        "status": status,
        "method": method,
        "inputs": inputs,
        "result": result,
        "diagnostics": diagnostics,
        "steps": steps or [],
        "tables": tables or [],
        "charts": charts or [],
        "warnings": warnings or [],
        "report": {"status": "pending"},
    }


def table(name: str, columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    return {"name": name, "columns": columns, "rows": rows[:1000],
            "truncated": len(rows) > 1000}


def analyze_error(exact: float, approximation: float) -> dict[str, Any]:
    exact, approximation = finite(exact, "exacto"), finite(approximation, "aproximado")
    absolute = abs(exact - approximation)
    relative = absolute / abs(exact) if exact != 0 else None
    result = pack_result(
        "error", "Comparación de valor exacto y aproximado",
        {"exact": exact, "approximation": approximation},
        {"absolute_error": absolute, "relative_error": relative,
         "percentage_error": relative * 100 if relative is not None else None},
        {"exact_is_zero": exact == 0},
        ["Error absoluto = |exacto − aproximado|.",
         "Error relativo = error absoluto / |exacto|; no se define si el exacto es cero."],
        [table("Errores", ["Medida", "Valor"], [
            ["Absoluto", absolute], ["Relativo", relative],
            ["Porcentual", relative * 100 if relative is not None else None]])])
    return result


def propagate_error(a: float, b: float, error_a: float, error_b: float,
                    operation: str = "add") -> dict[str, Any]:
    """Propaga incertidumbres independientes por linealización de primer orden."""
    a, b = finite(a, "a"), finite(b, "b")
    error_a, error_b = finite(error_a, "error_a"), finite(error_b, "error_b")
    if error_a < 0 or error_b < 0:
        raise ValueError("Las incertidumbres deben ser no negativas.")
    operation = operation.lower().strip()
    if operation == "add":
        value, uncertainty = a + b, math.hypot(error_a, error_b)
    elif operation == "subtract":
        value, uncertainty = a - b, math.hypot(error_a, error_b)
    elif operation == "multiply":
        value = a * b
        uncertainty = math.hypot(b * error_a, a * error_b)
    elif operation == "divide":
        if b == 0:
            raise ValueError("No se puede propagar división por cero.")
        value = a / b
        uncertainty = math.hypot(error_a / b, a * error_b / (b * b))
    else:
        raise ValueError("operation debe ser add, subtract, multiply o divide.")
    value, uncertainty = finite(value, "resultado"), finite(uncertainty, "incertidumbre propagada")
    relative = uncertainty / abs(value) if value != 0 else None
    return pack_result(
        "error_propagation", operation,
        {"a": a, "b": b, "error_a": error_a, "error_b": error_b,
         "assumption": "independent uncertainties; first-order propagation"},
        {"value": value, "absolute_uncertainty": uncertainty,
         "relative_uncertainty": relative},
        {"independent_inputs": True, "linearized": True},
        ["Se combinaron derivadas parciales con incertidumbres independientes.",
         "La aproximación es de primer orden y no incluye correlación entre entradas."],
        [table("Propagación de incertidumbre", ["Magnitud", "Valor"], [
            ["Resultado", value], ["Incertidumbre absoluta", uncertainty],
            ["Incertidumbre relativa", relative]])])

def solve_root(expression: str, method: str = "bisection", a: float | None = None,
               b: float | None = None, x0: float | None = None,
               x1: float | None = None, g_expression: str | None = None,
               tolerance: float = 1e-10, max_iter: int = 100) -> dict[str, Any]:
    method = method.strip().lower()
    aliases = {"biseccion": "bisection", "falsa_posicion": "false_position",
               "falsa posición": "false_position", "newton_raphson": "newton",
               "punto_fijo": "fixed_point", "secante": "secant"}
    method = aliases.get(method, method)
    allowed = {"bisection", "false_position", "fixed_point", "newton", "secant"}
    if method not in allowed:
        raise ValueError(f"Método no soportado. Elige: {', '.join(sorted(allowed))}.")
    tol = finite(tolerance, "tolerancia")
    if tol <= 0 or not 1 <= int(max_iter) <= 10000:
        raise ValueError("La tolerancia debe ser positiva y max_iter entre 1 y 10000.")
    f = lambda x: safe_eval(expression, {"x": x})
    rows: list[list[Any]] = []
    status, termination = "no_convergence", "Se alcanzó el máximo de iteraciones."
    if method in {"bisection", "false_position"}:
        if a is None or b is None:
            raise ValueError("Este método requiere los extremos a y b.")
        left, right = finite(a, "a"), finite(b, "b")
        if left >= right:
            raise ValueError("Se requiere a < b.")
        fl, fr = f(left), f(right)
        if fl == 0:
            root, status, termination = left, "success", "f(a)=0."
        elif fr == 0:
            root, status, termination = right, "success", "f(b)=0."
        elif fl * fr > 0:
            raise ValueError("f(a) y f(b) deben tener signos opuestos.")
        else:
            root = (left + right) / 2
            for k in range(1, int(max_iter) + 1):
                if method == "bisection":
                    root = (left + right) / 2
                else:
                    denom = fr - fl
                    if abs(denom) < 1e-300:
                        termination = "Denominador numéricamente nulo."
                        break
                    root = right - fr * (right - left) / denom
                fx = f(root)
                rows.append([k, left, right, root, fx, right - left])
                if abs(fx) <= tol or abs(right - left) <= tol * max(1, abs(root)):
                    status, termination = "success", "Se alcanzó la tolerancia."
                    break
                if fl * fx < 0:
                    right, fr = root, fx
                else:
                    left, fl = root, fx
    else:
        if x0 is None:
            raise ValueError("El método requiere x0.")
        current = finite(x0, "x0")
        previous = finite(x1, "x1") if x1 is not None else None
        if method == "fixed_point" and not g_expression:
            raise ValueError("Punto fijo requiere g_expression.")
        g = lambda x: safe_eval(g_expression or "", {"x": x})
        root = current
        for k in range(1, int(max_iter) + 1):
            fx = f(current)
            if method == "fixed_point":
                next_x = g(current)
            elif method == "newton":
                h = math.sqrt(2.220446049250313e-16) * max(1.0, abs(current))
                derivative = (f(current + h) - f(current - h)) / (2 * h)
                if abs(derivative) < 1e-14:
                    termination = "Derivada numéricamente nula."
                    break
                next_x = current - fx / derivative
            else:
                if previous is None:
                    raise ValueError("Secante requiere x1 además de x0.")
                fprev = f(previous)
                denom = fx - fprev
                if abs(denom) < 1e-14:
                    termination = "Denominador numéricamente nulo."
                    break
                next_x = current - fx * (current - previous) / denom
            delta = abs(next_x - current)
            rows.append([k, current, fx, next_x, delta])
            root = next_x
            if delta <= tol * max(1, abs(next_x)) or abs(f(next_x)) <= tol:
                status, termination = "success", "Se alcanzó la tolerancia."
                break
            previous, current = current, next_x
    residual = abs(f(root))
    chart_x, chart_y = [], []
    if method in {"bisection", "false_position"} and a is not None and b is not None:
        lo, hi = finite(a), finite(b)
    else:
        lo, hi = root - max(2, abs(root) * 0.5), root + max(2, abs(root) * 0.5)
    for i in range(101):
        xx = lo + (hi - lo) * i / 100
        try:
            chart_x.append(xx); chart_y.append(f(xx))
        except Exception:
            pass
    iteration_columns = (["k", "a", "b", "x", "f(x)", "interval_width"]
                         if method in {"bisection", "false_position"}
                         else ["k", "x_k", "f(x_k)", "x_next", "step"])
    return pack_result(
        "roots", method, {"expression": expression, "a": a, "b": b, "x0": x0,
                          "x1": x1, "g_expression": g_expression,
                          "tolerance": tol, "max_iter": int(max_iter)},
        {"root": root, "function_value": f(root)},
        {"absolute_residual": residual, "iterations": len(rows),
         "converged": status == "success", "termination": termination, "tolerance": tol},
        ["Se iteró con el método solicitado.", termination],
        [table("Iteraciones", iteration_columns, rows)],
        [{"name": "Función y raíz", "series": [
            {"label": "f(x)", "x": chart_x, "y": chart_y},
            {"label": "raíz", "type": "scatter", "x": [root], "y": [f(root)]}]}],
        [termination] if status != "success" else [],
        status=status)


def solve_linear(matrix: list[list[float]], vector: list[float],
                 method: str = "gaussian", tolerance: float = 1e-10,
                 max_iter: int = 1000, preconditioner: str = "none") -> dict[str, Any]:
    A = np.asarray(matrix, dtype=float)
    b = np.asarray(vector, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1] or b.ndim != 1 or b.size != A.shape[0]:
        raise ValueError("A debe ser cuadrada y b debe tener la misma cantidad de filas.")
    n = b.size
    if not 1 <= n <= 250 or not np.isfinite(A).all() or not np.isfinite(b).all():
        raise ValueError("Sistema no finito o tamaño fuera del límite (1–250).")
    tol = finite(tolerance, "tolerancia")
    if tol <= 0 or not 1 <= int(max_iter) <= 10000:
        raise ValueError("Tolerancia/max_iter fuera de rango.")
    method = method.strip().lower()
    if preconditioner not in {"none", "jacobi"}:
        raise ValueError("Precondicionador debe ser none o jacobi.")
    aliases = {"eliminacion_gaussiana": "gaussian", "eliminación gaussiana": "gaussian",
               "lu": "lu", "jacobi": "jacobi", "gauss-seidel": "gauss_seidel",
               "gauss_seidel": "gauss_seidel", "cg": "conjugate_gradient"}
    method = aliases.get(method, method)
    if preconditioner == "jacobi" and method not in {"conjugate_gradient", "gmres"}:
        raise ValueError("El precondicionador Jacobi solo aplica a CG o GMRES.")
    if method not in {"gaussian", "lu", "jacobi", "gauss_seidel",
                      "conjugate_gradient", "gmres", "qr", "svd"}:
        raise ValueError("Método de sistema lineal no soportado.")
    rows: list[list[Any]] = []
    x = np.zeros(n)
    status, termination = "success", "Solución calculada."
    if method == "gaussian":
        aug = np.column_stack((A.copy(), b.copy()))
        for col in range(n):
            pivot = col + int(np.argmax(np.abs(aug[col:, col])))
            if abs(aug[pivot, col]) < 1e-14:
                raise ValueError("SINGULAR_SYSTEM: pivote nulo o matriz singular.")
            aug[[col, pivot]] = aug[[pivot, col]]
            for row in range(col + 1, n):
                factor = aug[row, col] / aug[col, col]
                aug[row, col:] -= factor * aug[col, col:]
                rows.append([col + 1, row + 1, pivot + 1, factor])
        x = np.zeros(n)
        for row in range(n - 1, -1, -1):
            x[row] = (aug[row, -1] - aug[row, row + 1:n] @ x[row + 1:n]) / aug[row, row]
    elif method == "lu":
        L = np.eye(n); U = A.copy(); P = np.eye(n)
        for col in range(n):
            pivot = col + int(np.argmax(np.abs(U[col:, col])))
            if abs(U[pivot, col]) < 1e-14:
                raise ValueError("SINGULAR_SYSTEM: matriz singular durante LU.")
            if pivot != col:
                U[[col, pivot]] = U[[pivot, col]]
                P[[col, pivot]] = P[[pivot, col]]
                if col:
                    L[[col, pivot], :col] = L[[pivot, col], :col]
            for row in range(col + 1, n):
                L[row, col] = U[row, col] / U[col, col]
                U[row, col:] -= L[row, col] * U[col, col:]
        z = np.linalg.solve(L, P @ b)
        x = np.linalg.solve(U, z)
        rows = [[k + 1, float(np.linalg.norm(A @ x - b))] for k in range(n)]
    elif method in {"jacobi", "gauss_seidel"}:
        if np.any(np.abs(np.diag(A)) < 1e-14):
            raise ValueError("La diagonal tiene ceros; no se puede iterar.")
        x = np.zeros(n)
        for k in range(1, int(max_iter) + 1):
            old = x.copy()
            for i in range(n):
                if method == "jacobi":
                    x[i] = (b[i] - (A[i, :] @ old - A[i, i] * old[i])) / A[i, i]
                else:
                    x[i] = (b[i] - A[i, :i] @ x[:i] - A[i, i + 1:] @ old[i + 1:]) / A[i, i]
            residual = float(np.linalg.norm(A @ x - b))
            rows.append([k, residual, float(np.linalg.norm(x - old))])
            if residual <= tol * (1 + float(np.linalg.norm(b))):
                break
        else:
            status, termination = "no_convergence", "Máximo de iteraciones alcanzado."
    elif method == "conjugate_gradient":
        if not np.allclose(A, A.T, atol=1e-10):
            raise ValueError("Gradiente conjugado requiere una matriz simétrica.")
        diag = np.diag(A)
        if preconditioner == "jacobi" and np.any(diag <= 0):
            raise ValueError("Precondicionador Jacobi necesita diagonal positiva.")
        x = np.zeros(n)
        r = b - A @ x
        z = r / diag if preconditioner == "jacobi" else r.copy()
        p = z.copy(); rz = float(r @ z)
        for k in range(1, int(max_iter) + 1):
            Ap = A @ p
            denom = float(p @ Ap)
            if denom <= 1e-30:
                raise ValueError("La matriz no parece definida positiva.")
            alpha = rz / denom
            x += alpha * p
            r -= alpha * Ap
            residual = float(np.linalg.norm(r))
            rows.append([k, residual])
            if residual <= tol * (1 + float(np.linalg.norm(b))):
                break
            z = r / diag if preconditioner == "jacobi" else r.copy()
            new_rz = float(r @ z)
            p = z + (new_rz / rz) * p
            rz = new_rz
        else:
            status, termination = "no_convergence", "Máximo de iteraciones alcanzado."
    elif method == "gmres":
        # GMRES con Arnoldi; Jacobi aplica precondicionamiento por la izquierda.
        operator, rhs_gmres = A, b
        if preconditioner == "jacobi":
            diagonal = np.diag(A)
            if np.any(np.abs(diagonal) < 1e-14):
                raise ValueError("Jacobi requiere una diagonal sin ceros.")
            operator = (1.0 / diagonal)[:, None] * A
            rhs_gmres = (1.0 / diagonal) * b
        x = np.zeros(n); r0 = rhs_gmres - operator @ x
        beta = float(np.linalg.norm(r0))
        if beta > 0:
            V = [r0 / beta]; H = np.zeros((n + 1, n))
            for j in range(min(n, int(max_iter))):
                w = operator @ V[j]
                for i in range(j + 1):
                    H[i, j] = float(V[i] @ w); w -= H[i, j] * V[i]
                H[j + 1, j] = float(np.linalg.norm(w))
                happy_breakdown = H[j + 1, j] <= 1e-15
                if not happy_breakdown:
                    V.append(w / H[j + 1, j])
                rhs = np.zeros(j + 2); rhs[0] = beta
                y, *_ = np.linalg.lstsq(H[:j + 2, :j + 1], rhs, rcond=None)
                x = np.column_stack(V[:j + 1]) @ y
                residual = float(np.linalg.norm(A @ x - b))
                rows.append([j + 1, residual])
                if residual <= tol * (1 + float(np.linalg.norm(b))):
                    break
                if happy_breakdown:
                    status, termination = "no_convergence", "GMRES encontró una ruptura de Arnoldi antes de alcanzar la tolerancia."
                    break
            else:
                status, termination = "no_convergence", "GMRES alcanzó el máximo de iteraciones."
    elif method == "qr":
        Q, R = np.linalg.qr(A)
        x = np.linalg.solve(R, Q.T @ b)
    elif method == "svd":
        x, *_ = np.linalg.lstsq(A, b, rcond=None)
    residual = float(np.linalg.norm(A @ x - b))
    condition_number = float(np.linalg.cond(A))
    if not math.isfinite(condition_number):
        condition_number = None
    if method in {"jacobi", "gauss_seidel", "conjugate_gradient", "gmres"} and rows:
        if residual > tol * (1 + float(np.linalg.norm(b))):
            status, termination = "no_convergence", termination if status != "success" else "Residuo sobre tolerancia."
    return pack_result(
        "linear_system", method,
        {"matrix": A.tolist(), "vector": b.tolist(), "tolerance": tol,
         "max_iter": int(max_iter), "preconditioner": preconditioner},
        {"solution": x.tolist(), "residual_norm": residual},
        {"residual_norm": residual, "condition_number": condition_number,
         "iterations": len(rows), "converged": status == "success", "termination": termination},
        ["Se resolvió A x = b.", "El residuo se calcula como ||A x − b||₂."],
        [table("Eliminación/iteraciones", ["k/columna", "residuo/fila", "pivote/paso", "factor"],
               rows)],
        [{"name": "Residuo por iteración", "series": [
            {"label": "||Ax-b||₂", "x": [r[0] for r in rows if len(r) > 1],
             "y": [r[1] for r in rows if len(r) > 1]}]}],
        status=status)



def solve_sparse_linear(size: int, entries: list[list[float]], vector: list[float],
                        method: str = "cg", tolerance: float = 1e-8,
                        max_iter: int = 2000, preconditioner: str = "none") -> dict[str, Any]:
    """Resuelve sistemas dispersos en formato COO [fila, columna, valor], índices base 0."""
    size = int(size)
    if not 1 <= size <= 5000:
        raise ValueError("El tamaño disperso debe estar entre 1 y 5000.")
    if not isinstance(entries, list) or len(entries) > 100000:
        raise ValueError("Se requieren hasta 100000 entradas dispersas.")
    if not isinstance(vector, list) or len(vector) != size:
        raise ValueError("El vector b debe tener exactamente size elementos.")
    b = np.asarray([finite(value, "valor de b") for value in vector], dtype=float)
    row_indices, col_indices, values = [], [], []
    for index, entry in enumerate(entries):
        if not isinstance(entry, (list, tuple)) or len(entry) != 3:
            raise ValueError(f"La entrada COO {index+1} debe ser [fila, columna, valor].")
        row_value, col_value = finite(entry[0], "fila"), finite(entry[1], "columna")
        if not row_value.is_integer() or not col_value.is_integer():
            raise ValueError("Los índices COO deben ser enteros, base 0.")
        row, col = int(row_value), int(col_value)
        if not 0 <= row < size or not 0 <= col < size:
            raise ValueError("Un índice COO está fuera de la matriz.")
        row_indices.append(row); col_indices.append(col)
        values.append(finite(entry[2], "valor de matriz"))
    A = coo_matrix((values, (row_indices, col_indices)), shape=(size, size)).tocsr()
    A.sum_duplicates()
    method = method.lower().strip()
    method = {"conjugate_gradient": "cg", "gradiente_conjugado": "cg"}.get(method, method)
    if method not in {"cg", "gmres"}:
        raise ValueError("El solver disperso admite cg o gmres.")
    tolerance = finite(tolerance, "tolerancia")
    if not 0 < tolerance < 1 or not 1 <= int(max_iter) <= 10000:
        raise ValueError("Tolerancia entre 0 y 1 y max_iter entre 1 y 10000 requeridos.")
    if preconditioner not in {"none", "jacobi"}:
        raise ValueError("El precondicionador debe ser none o jacobi.")
    if method == "cg":
        difference = (A - A.T).tocsr()
        if difference.nnz and np.max(np.abs(difference.data)) > 1e-10:
            raise ValueError("Gradiente conjugado requiere matriz simétrica.")
    M = None
    if preconditioner == "jacobi":
        diagonal = A.diagonal()
        if np.any(np.abs(diagonal) < 1e-14):
            raise ValueError("El precondicionador Jacobi requiere diagonal sin ceros.")
        if method == "cg" and np.any(diagonal <= 0):
            raise ValueError("Para CG, Jacobi requiere diagonal positiva.")
        M = diags(1.0 / diagonal, format="csr")
    history = []
    threshold = tolerance * (1 + float(np.linalg.norm(b)))
    if method == "cg":
        solution = np.zeros(size); residual_vector = b.copy()
        z = (M @ residual_vector) if M is not None else residual_vector.copy()
        direction = z.copy(); rz = float(residual_vector @ z)
        info = 0 if float(np.linalg.norm(residual_vector)) <= threshold else 1
        if info != 0:
            for _ in range(int(max_iter)):
                product = A @ direction
                denominator = float(direction @ product)
                if denominator <= 1e-30:
                    info = -1
                    break
                alpha = rz / denominator
                solution += alpha * direction
                residual_vector -= alpha * product
                residual_norm = float(np.linalg.norm(residual_vector))
                history.append(residual_norm)
                if residual_norm <= threshold:
                    info = 0
                    break
                z = (M @ residual_vector) if M is not None else residual_vector.copy()
                new_rz = float(residual_vector @ z)
                if abs(rz) <= 1e-300:
                    info = -1
                    break
                direction = z + (new_rz / rz) * direction
                rz = new_rz
        residual_label = "||Ax-b||₂"
    else:
        def callback(iterate):
            history.append(float(iterate))
        solution, info = sparse_gmres(A, b, rtol=tolerance, atol=0.0,
                                      restart=min(50, size), maxiter=int(max_iter),
                                      M=M, callback=callback, callback_type="legacy")
        residual_label = "residuo relativo precondicionado"
    residual = float(np.linalg.norm(A @ solution - b))
    converged = info == 0 and residual <= threshold
    if converged:
        status, termination = "success", "El residuo alcanzó la tolerancia solicitada."
    elif info > 0:
        status, termination = "no_convergence", f"Se alcanzó el límite de iteraciones (info={info})."
    else:
        status, termination = "no_convergence", "El método se detuvo por una ruptura numérica antes de alcanzar la tolerancia."
    sample_stride = max(1, math.ceil(len(history) / 1000))
    sample_indices = list(range(0, len(history), sample_stride))
    sampled = [history[index] for index in sample_indices]
    rows = [[index + 1, history[index]] for index in sample_indices]
    return pack_result(
        "sparse_linear_system", method,
        {"size": size, "entries_count": len(entries), "vector_norm": float(np.linalg.norm(b)),
         "tolerance": tolerance, "max_iter": int(max_iter),
         "preconditioner": preconditioner, "index_base": 0},
        {"solution": np.asarray(solution).tolist(), "residual_norm": residual},
        {"iterations_recorded": len(history), "converged": converged,
         "termination": termination, "nonzero_count": int(A.nnz),
         "matrix_format": "COO input / CSR computation"},
        ["La matriz dispersa se recibió como tripletas COO [fila, columna, valor] con índices base 0.",
         "La solución se calculó con operaciones dispersas, sin convertir la matriz a densa.",
         termination],
        [table("Residuo por iteración (muestreo máximo 1000 filas)", ["k", residual_label], rows)],
        [{"name": "Convergencia dispersa", "series": [{
            "label": residual_label, "x": [index + 1 for index in sample_indices], "y": sampled}]}],
        status=status)

def fit_data(points: list[Any], method: str = "least_squares", degree: int = 1,
             evaluation_points: list[float] | None = None) -> dict[str, Any]:
    pts = normalize_points(points)
    xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
    method = method.lower().strip()
    evals = [finite(x, "x de evaluación") for x in (evaluation_points or xs.tolist())]
    if method in {"least_squares", "least_squares_qr", "least_squares_svd"}:
        degree = int(degree)
        if not 0 <= degree < len(pts):
            raise ValueError("El grado debe ser >=0 y menor al número de puntos.")
        if method == "least_squares":
            coeff_desc = np.polyfit(xs, ys, degree)
            evaluate = lambda x: float(np.polyval(coeff_desc, x))
            model = {"coefficients_high_to_low": coeff_desc.tolist(), "degree": degree}
            diagnostics_extra = {}
            method_name = f"Mínimos cuadrados polinómico grado {degree}"
        else:
            center = float((xs.min() + xs.max()) / 2)
            scale = float((xs.max() - xs.min()) / 2)
            normalized_x = (xs - center) / scale
            design = np.vander(normalized_x, N=degree + 1, increasing=True)
            if method == "least_squares_qr":
                q_matrix, r_matrix = np.linalg.qr(design, mode="reduced")
                rank = int(np.linalg.matrix_rank(r_matrix))
                if rank < degree + 1:
                    raise ValueError("El diseño es deficiente en rango para el grado solicitado.")
                coefficients = np.linalg.solve(r_matrix, q_matrix.T @ ys)
                method_name = f"Mínimos cuadrados QR grado {degree}"
            else:
                coefficients, _, rank, _ = np.linalg.lstsq(design, ys, rcond=None)
                rank = int(rank)
                method_name = f"Mínimos cuadrados SVD grado {degree}"
            singular_values = np.linalg.svd(design, compute_uv=False)
            if rank < degree + 1:
                raise ValueError("El diseño es deficiente en rango para el grado solicitado.")
            evaluate = lambda x: float(np.polynomial.polynomial.polyval((x-center)/scale, coefficients))
            model = {"coefficients_low_to_high_normalized_x": coefficients.tolist(),
                     "normalized_x": "(x-center)/scale", "center": center,
                     "scale": scale, "degree": degree}
            diagnostics_extra = {"rank": rank,
                "condition_number": float(singular_values[0]/singular_values[-1]),
                "singular_values": singular_values.tolist()}
        residuals = [float(y - evaluate(x)) for x, y in pts]
        sst = float(np.sum((ys - np.mean(ys)) ** 2))
        ssr = float(sum(r*r for r in residuals))
        diagnostics = {"sum_squared_residuals": ssr,
                       "r_squared": 1.0 - ssr/sst if sst else None,
                       **diagnostics_extra}
    elif method == "cubic_spline":
        if len(pts) < 3:
            raise ValueError("El spline cúbico requiere al menos 3 puntos.")
        spline = CubicSpline(xs, ys, bc_type="natural")
        evaluate = lambda x: float(spline(x))
        model = {"knots": xs.tolist(), "boundary_condition": "natural"}
        residuals = [0.0 for _ in pts]
        diagnostics = {"interpolates_data": True}
        method_name = "Spline cúbico natural"
    elif method == "linear_piecewise":
        def evaluate(x):
            if x < xs[0]:
                i = 0
            elif x > xs[-1]:
                i = len(xs) - 2
            else:
                i = min(len(xs) - 2, max(0, int(np.searchsorted(xs, x, side="right") - 1)))
            slope = (ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i])
            return float(ys[i] + slope * (x - xs[i]))
        model = {"knots": xs.tolist()}
        residuals = [0.0 for _ in pts]
        diagnostics = {"interpolates_data": True, "extrapolation": "linear extension of nearest end segment"}
        method_name = "Interpolación lineal por tramos"
    else:
        raise ValueError("method debe ser least_squares, least_squares_qr, least_squares_svd, cubic_spline o linear_piecewise.")
    lo, hi = float(xs.min()), float(xs.max())
    chart_x = np.linspace(lo, hi, 150).tolist()
    chart_y = [evaluate(float(x)) for x in chart_x]
    warnings = []
    if any(q < lo or q > hi for q in evals):
        warnings.append("Hay evaluación fuera del intervalo de datos; el resultado es extrapolación.")
    return pack_result(
        "approximation", method_name,
        {"points": [{"x": x, "y": y} for x, y in pts], "method": method,
         "degree": degree, "evaluation_points": evals},
        {"model": model, "values": [{"x": x, "y": evaluate(x)} for x in evals],
         "residuals": residuals},
        diagnostics,
        ["Se evaluó el modelo solicitado en los puntos de consulta."],
        [table("Datos y residuos", ["x", "y", "residuo"],
               [[x, y, r] for (x, y), r in zip(pts, residuals)])],
        [{"name": "Datos y aproximación", "series": [
            {"label": "modelo", "x": chart_x, "y": chart_y},
            {"label": "datos", "type": "scatter", "x": xs.tolist(), "y": ys.tolist()}]}],
        warnings)


def differentiate(expression: str, x: float, h: float = 1e-4,
                  method: str = "central") -> dict[str, Any]:
    x, h = finite(x, "x"), finite(h, "h")
    if h <= 0:
        raise ValueError("h debe ser positivo.")
    f = lambda z: safe_eval(expression, {"x": z})
    method = method.lower().strip()
    formulas = {
        "forward": lambda step: (f(x + step) - f(x)) / step,
        "backward": lambda step: (f(x) - f(x - step)) / step,
        "central": lambda step: (f(x + step) - f(x - step)) / (2 * step)}
    if method == "richardson":
        d1 = formulas["central"](h); d2 = formulas["central"](h / 2)
        value = (4 * d2 - d1) / 3
        order, formula = 4, "Richardson sobre diferencia central"
    elif method in formulas:
        value = formulas[method](h)
        order, formula = (2 if method == "central" else 1), method
    else:
        raise ValueError("Método debe ser forward, backward, central o richardson.")
    rows = [[h / (2**i), formulas["central"](h / (2**i))] for i in range(7)]
    chart_x = np.linspace(x - 2*h, x + 2*h, 100).tolist()
    chart_y = [f(float(z)) for z in chart_x]
    return pack_result(
        "differentiation", formula, {"expression": expression, "x": x, "h": h},
        {"derivative": value, "order": order},
        {"method_order": order, "step": h, "step_sensitivity": abs(formulas["central"](h) - formulas["central"](h/2)) / 3},
        [f"Se aplicó {formula} con h={h}.", f"Orden formal: {order}."],
        [table("Sensibilidad al paso", ["h", "derivada central"], rows)],
        [{"name": "Función y punto", "series": [
            {"label": "f(x)", "x": chart_x, "y": chart_y},
            {"label": "evaluación", "type": "scatter", "x": [x], "y": [f(x)]}]}])


def differentiate_data(points: list[Any], method: str = "central") -> dict[str, Any]:
    pts = normalize_points(points)
    if len(pts) < 3:
        raise ValueError("La derivación tabular requiere al menos 3 puntos.")
    xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
    method = method.lower().strip()
    if method == "forward":
        out_x = xs[:-1]; values = np.diff(ys) / np.diff(xs)
    elif method == "backward":
        out_x = xs[1:]; values = np.diff(ys) / np.diff(xs)
    elif method == "central":
        left = xs[1:-1] - xs[:-2]; right = xs[2:] - xs[1:-1]
        values = (-right / (left * (left + right)) * ys[:-2]
                  + (right - left) / (left * right) * ys[1:-1]
                  + left / (right * (left + right)) * ys[2:])
        out_x = xs[1:-1]
    else:
        raise ValueError("method debe ser forward, backward o central.")
    rows = [[float(x), float(y), float(d)] for x,y,d in zip(out_x,ys[:-1] if method == "forward" else (ys[1:] if method == "backward" else ys[1:-1]),values)]
    return pack_result(
        "tabular_differentiation", method,
        {"points": [{"x": x, "y": y} for x,y in pts], "method": method},
        {"derivatives": [{"x": float(x), "value": float(d)} for x,d in zip(out_x,values)]},
        {"point_count": len(pts), "derivative_count": len(values),
         "spacing": "nonuniform formula supported"},
        ["Se aproximó la primera derivada a partir de los valores tabulados.",
         "La fórmula central de malla no uniforme es de segundo orden local." if method == "central" else "La diferencia unilateral es de primer orden local."],
        [table("Derivadas tabuladas", ["x", "y asociado", "dy/dx aproximada"], rows)],
        [{"name": "Datos originales", "series": [{"label": "y", "x": xs.tolist(), "y": ys.tolist()}]},
         {"name": "Derivada aproximada", "series": [{"label": "dy/dx", "x": out_x.tolist(), "y": values.tolist()}]}])


def integrate_data(points: list[Any], method: str = "trapezoid") -> dict[str, Any]:
    pts = normalize_points(points)
    if len(pts) < 2:
        raise ValueError("La integración tabular requiere al menos 2 puntos.")
    xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
    method = method.lower().strip()
    widths = np.diff(xs)
    if method == "trapezoid":
        contributions = widths * (ys[:-1] + ys[1:]) / 2
        panels = [[float(xs[i]), float(xs[i+1]), float(contributions[i])] for i in range(len(widths))]
        value = float(np.sum(contributions))
    elif method == "simpson":
        if len(pts) < 3 or (len(pts) - 1) % 2:
            raise ValueError("Simpson compuesto requiere un número par de subintervalos y al menos 3 puntos.")
        step = float(widths[0])
        if not np.allclose(widths, step, rtol=1e-9, atol=1e-12):
            raise ValueError("Simpson compuesto tabular requiere abscisas equiespaciadas.")
        panel_values = []
        for i in range(0, len(pts)-1, 2):
            panel_values.append(step/3 * (ys[i] + 4*ys[i+1] + ys[i+2]))
        value = float(np.sum(panel_values))
        panels = [[float(xs[i]), float(xs[i+2]), float(panel_values[i//2])]
                  for i in range(0, len(pts)-1, 2)]
    else:
        raise ValueError("method debe ser trapezoid o simpson.")
    return pack_result(
        "tabular_quadrature", method,
        {"points": [{"x": x, "y": y} for x,y in pts], "method": method},
        {"integral": value},
        {"interval_count": len(widths), "panel_count": len(panels),
         "error_estimate": None},
        ["Se integró a partir de los valores tabulados.",
         "No se estima error sin datos de refinamiento o una referencia independiente."],
        [table("Aportes por panel", ["inicio", "fin", "aporte"], panels)],
        [{"name": "Datos integrados", "series": [{"label": "y(x)", "x": xs.tolist(), "y": ys.tolist()}]}],
        ["No se dispone de una estimación de error a partir de una sola tabla."])

def integrate(expression: str, a: float, b: float, n: int = 100,
              method: str = "simpson") -> dict[str, Any]:
    a, b = finite(a, "a"), finite(b, "b")
    if a == b or not 1 <= int(n) <= 20000:
        raise ValueError("Se requiere a != b y 1 <= n <= 20000.")
    method = method.lower().strip(); n = int(n)
    f = lambda x: safe_eval(expression, {"x": x})
    xs = np.linspace(a, b, n + 1); ys = np.array([f(float(x)) for x in xs])
    if method == "trapezoid":
        value = float((b-a)/n * (0.5*ys[0] + np.sum(ys[1:-1]) + 0.5*ys[-1]))
        weights = np.ones(n + 1); weights[[0, -1]] = 0.5
        contributions = (b-a)/n * weights * ys
    elif method == "simpson":
        if n % 2:
            raise ValueError("Simpson compuesto requiere n par.")
        weights = np.ones(n + 1); weights[1:-1:2] = 4; weights[2:-1:2] = 2
        contributions = (b-a)/(3*n) * weights * ys
        value = float(np.sum(contributions))
    elif method == "gauss_legendre":
        if n > 64:
            raise ValueError("Gauss-Legendre admite n máximo 64.")
        nodes, weights = np.polynomial.legendre.leggauss(n)
        mapped = (b-a)*nodes/2 + (a+b)/2
        values = np.array([f(float(x)) for x in mapped])
        value = float((b-a)/2 * np.dot(weights, values))
        xs, ys, contributions = mapped, values, (b-a)/2*weights*values
    else:
        raise ValueError("Método debe ser trapezoid, simpson o gauss_legendre.")
    error_estimate = None
    if method in {"trapezoid", "simpson"}:
        fine_n = n * 2
        fine_x = np.linspace(a, b, fine_n + 1)
        fine_y = np.array([f(float(xx)) for xx in fine_x])
        if method == "trapezoid":
            fine_value = float((b-a)/fine_n * (0.5*fine_y[0] + np.sum(fine_y[1:-1]) + 0.5*fine_y[-1]))
            error_estimate = abs(fine_value - value) / 3
        else:
            fine_weights = np.ones(fine_n + 1)
            fine_weights[1:-1:2] = 4; fine_weights[2:-1:2] = 2
            fine_value = float((b-a)/(3*fine_n) * np.sum(fine_weights * fine_y))
            error_estimate = abs(fine_value - value) / 15
    elif method == "gauss_legendre" and n < 64:
        fine_n = min(2*n, 64)
        fine_nodes, fine_weights = np.polynomial.legendre.leggauss(fine_n)
        fine_x = (b-a)*fine_nodes/2 + (a+b)/2
        fine_y = np.array([f(float(xx)) for xx in fine_x])
        fine_value = float((b-a)/2 * np.dot(fine_weights, fine_y))
        error_estimate = abs(fine_value - value)
    chart_x = np.linspace(min(a,b), max(a,b), 150).tolist()
    chart_y = [f(float(x)) for x in chart_x]
    return pack_result(
        "quadrature", method, {"expression": expression, "a": a, "b": b, "n": n},
        {"integral": value},
        {"panels": n, "method": method, "error_estimate": error_estimate},
        [f"Se aproximó la integral en [{a}, {b}] con {method}."],
        [table("Nodos y contribuciones", ["x", "f(x)", "aporte"],
               [[float(x), float(y), float(c)] for x,y,c in zip(xs,ys,contributions)])],
        [{"name": "Integrando", "series": [
            {"label": "f(x)", "x": chart_x, "y": chart_y}]}])


def solve_ode(equations: list[str], initial_state: list[float], t0: float,
              t_end: float, step: float = 0.1, method: str = "rk4",
              state_names: list[str] | None = None,
              tolerance: float = 1e-8) -> dict[str, Any]:
    if not equations or len(equations) != len(initial_state) or len(equations) > 10:
        raise ValueError("Debe haber una ecuación por cada variable de estado (1–10).")
    y0 = np.array([finite(v, "estado inicial") for v in initial_state])
    t0, t_end, step = finite(t0, "t0"), finite(t_end, "t_end"), finite(step, "paso")
    if t0 == t_end or step <= 0:
        raise ValueError("Intervalo no vacío y paso positivo requeridos.")
    tolerance = finite(tolerance, "tolerancia")
    if not 0 < tolerance < 1:
        raise ValueError("La tolerancia debe estar entre 0 y 1.")
    names = state_names or [f"y{i}" for i in range(len(y0))]
    if (len(names) != len(y0) or any(not n.isidentifier() for n in names)
            or len(set(names)) != len(names) or any(n in {"t", "x", "pi", "e"} for n in names)):
        raise ValueError("state_names debe usar identificadores únicos que no sean t, x, pi o e.")
    if abs(t_end-t0)/step > 10000:
        raise ValueError("RESOURCE_LIMIT: reduzca el intervalo o aumente el paso.")
    method = method.lower().strip()
    def rhs(t, y):
        variables = {"t": float(t), "x": float(t)}
        variables.update({name: float(value) for name, value in zip(names, y)})
        return np.array([safe_eval(expr, variables) for expr in equations])
    if method in {"rk45", "bdf"}:
        sol = solve_ivp(rhs, (t0, t_end), y0, method=method.upper(),
                        rtol=tolerance, atol=tolerance, max_step=step)
        if not sol.success:
            status = "no_convergence"
        else:
            status = "success"
        ts, values = sol.t, sol.y.T
        steps = int(len(ts)-1)
        termination = sol.message
    elif method in {"euler", "heun", "midpoint", "rk4"}:
        count = min(10000, int(math.ceil(abs(t_end-t0)/step)))
        ts = np.linspace(t0, t_end, count+1); values = [y0.copy()]
        y = y0.copy()
        for i in range(count):
            h = ts[i+1]-ts[i]; t = ts[i]
            k1 = rhs(t, y)
            if method == "euler":
                y = y + h*k1
            elif method == "heun":
                k2 = rhs(t+h, y+h*k1); y = y + h*(k1+k2)/2
            elif method == "midpoint":
                k2 = rhs(t+h/2, y+h*k1/2); y = y+h*k2
            else:
                k2 = rhs(t+h/2, y+h*k1/2)
                k3 = rhs(t+h/2, y+h*k2/2)
                k4 = rhs(t+h, y+h*k3)
                y = y+h*(k1+2*k2+2*k3+k4)/6
            values.append(y.copy())
        values = np.asarray(values); steps = count
        status, termination = "success", "Se completaron los pasos fijos."
    else:
        raise ValueError("Método ODE: euler, heun, midpoint, rk4, rk45 o bdf.")
    rows = [[float(t), *[float(v) for v in row]] for t,row in zip(ts,values)]
    series = [{"label": name, "x": [float(t) for t in ts],
               "y": [float(row[i]) for row in values]}
              for i,name in enumerate(names)]
    return pack_result(
        "ode", method, {"equations": equations, "initial_state": y0.tolist(),
                        "t0": t0, "t_end": t_end, "step": step,
                        "state_names": names, "tolerance": tolerance},
        {"final_time": float(ts[-1]), "final_state": values[-1].tolist()},
        {"steps": steps, "converged": status == "success", "termination": termination},
        ["Se integró el sistema de valores iniciales en el intervalo indicado."],
        [table("Trayectoria", ["t", *names], rows)],
        [{"name": "Solución", "series": series}], status=status)


def eigen_solve(matrix: list[list[float]], method: str = "qr",
                count: int = 1, tolerance: float = 1e-10,
                max_iter: int = 1000, shift: float = 0.0) -> dict[str, Any]:
    A = np.asarray(matrix,dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1] or not 1 <= A.shape[0] <= 100:
        raise ValueError("La matriz debe ser cuadrada de tamaño máximo 100.")
    if not np.isfinite(A).all(): raise ValueError("La matriz debe ser finita.")
    count = int(count)
    if not 1 <= count <= A.shape[0]:
        raise ValueError("count debe estar entre 1 y el tamaño de la matriz.")
    if not 1e-14 < finite(tolerance, "tolerancia") < 1:
        raise ValueError("La tolerancia debe estar entre 1e-14 y 1.")
    if not 1 <= int(max_iter) <= 10000:
        raise ValueError("max_iter debe estar entre 1 y 10000.")
    method=method.lower().strip()
    if method in {"power", "inverse"} and not np.allclose(A, A.T, atol=1e-10):
        raise ValueError("Los métodos power/inverse requieren matriz simétrica; use qr para matrices generales.")
    rows=[]; vectors=[]; vals=[]
    if method == "power":
        v=np.ones(A.shape[0]); v/=np.linalg.norm(v)
        for k in range(1,min(int(max_iter),10000)+1):
            w=A@v; norm=float(np.linalg.norm(w))
            if norm < 1e-15: raise ValueError("Iteración de potencia encontró vector nulo.")
            vnew=w/norm; lam=float(vnew@(A@vnew))
            residual=float(np.linalg.norm(A@vnew-lam*vnew))
            rows.append([k,lam,residual]); v=vnew
            if residual<=tolerance: break
        vals=[lam]; vectors=[v.tolist()]
    elif method == "inverse":
        v=np.ones(A.shape[0]); v/=np.linalg.norm(v)
        shifted=A-finite(shift,"shift")*np.eye(A.shape[0])
        for k in range(1,min(int(max_iter),10000)+1):
            vnew=np.linalg.solve(shifted,v); vnew/=np.linalg.norm(vnew)
            lam=float(vnew@(A@vnew)); residual=float(np.linalg.norm(A@vnew-lam*vnew))
            rows.append([k,lam,residual]); v=vnew
            if residual<=tolerance: break
        vals=[lam]; vectors=[v.tolist()]
    elif method in {"qr","all"}:
        vals0, vecs0=np.linalg.eig(A)
        order=np.argsort(-np.abs(vals0))[:max(1,min(int(count),A.shape[0]))]
        vals=[complex(vals0[i]) for i in order]
        vectors=[vecs0[:,i] for i in order]
    else: raise ValueError("Método debe ser power, inverse o qr.")
    formatted=[]
    for value, vector in zip(vals, vectors):
        eigenvalue = complex(value)
        vector = np.asarray(vector, dtype=complex)
        formatted.append({
            "value": {"real": float(eigenvalue.real), "imag": float(eigenvalue.imag)},
            "vector": {"real": np.real(vector).tolist(), "imag": np.imag(vector).tolist()},
            "residual": float(np.linalg.norm(A @ vector - eigenvalue * vector)),
        })
    status="success" if not rows or rows[-1][2] <= tolerance else "no_convergence"
    return pack_result(
        "eigenvalues",method,{"matrix":A.tolist(),"count":count,"shift":shift,
                             "tolerance":tolerance,"max_iter":max_iter},
        {"eigenpairs":formatted},
        {"iterations":len(rows),"converged":status=="success"},
        ["Se ordenaron los valores propios por magnitud para el método QR."],
        [table("Pares propios",["valor","vector","residuo"],
               [[p["value"],p["vector"],p["residual"]] for p in formatted]),
         table("Iteraciones",["k","lambda","residuo"],rows)],
        [{"name":"Residuo", "series":[{"label":"||Av-lambda v||",
             "x":[r[0] for r in rows],"y":[r[2] for r in rows]}]}],
        status=status)


def optimize(expression: str, initial: list[float], variables: list[str] | None = None,
             method: str = "bfgs", tolerance: float = 1e-7,
             max_iter: int = 500) -> dict[str, Any]:
    x=np.array([finite(v,"punto inicial") for v in initial],dtype=float)
    if not 1<=len(x)<=5: raise ValueError("Optimización admite de 1 a 5 variables.")
    tolerance=finite(tolerance,"tolerancia")
    if tolerance<=0 or not 1<=int(max_iter)<=5000:
        raise ValueError("Tolerancia positiva y max_iter entre 1 y 5000 requeridos.")
    names=variables or [f"x{i}" for i in range(len(x))]
    if len(names)!=len(x) or any(not n.isidentifier() for n in names):
        raise ValueError("Indique un nombre válido para cada variable.")
    f=lambda z:safe_eval(expression,dict(zip(names,z)))
    def grad(z):
        out=np.zeros(len(z))
        for i in range(len(z)):
            h=1e-6*max(1,abs(z[i])); p=z.copy(); m=z.copy(); p[i]+=h; m[i]-=h
            out[i]=(f(p)-f(m))/(2*h)
        return out
    method=method.lower().strip()
    if method not in {"gradient_descent", "newton", "bfgs"}:
        raise ValueError("Método debe ser gradient_descent, newton o bfgs.")
    H=np.eye(len(x)); rows=[]; status="no_convergence"
    termination="Se alcanzó el máximo de iteraciones."
    for k in range(1,min(int(max_iter),5000)+1):
        g=grad(x); norm=float(np.linalg.norm(g)); fx=f(x)
        if norm<=tolerance:
            status="success"; termination="La norma del gradiente alcanzó la tolerancia."; break
        if method=="gradient_descent":
            direction=-g
        elif method in {"bfgs","newton"}:
            if method=="newton":
                eps=1e-4; n=len(x); hess=np.zeros((n,n))
                for i in range(n):
                    ei=np.zeros(n); ei[i]=eps
                    for j in range(n):
                        ej=np.zeros(n); ej[j]=eps
                        hess[i,j]=(f(x+ei+ej)-f(x+ei-ej)-f(x-ei+ej)+f(x-ei-ej))/(4*eps*eps)
                try: direction=-np.linalg.solve(hess,g)
                except np.linalg.LinAlgError: direction=-g
            else: direction=-(H@g)
        else: raise ValueError("Método debe ser gradient_descent, newton o bfgs.")
        if float(direction@g)>=0: direction=-g
        alpha=1.0; accepted=False
        for _ in range(30):
            candidate=x+alpha*direction
            if f(candidate)<=fx+1e-4*alpha*float(g@direction):
                accepted=True
                break
            alpha*=0.5
        if not accepted:
            termination="La búsqueda de paso no encontró descenso suficiente."
            break
        xnew=candidate; gnew=grad(xnew)
        if method=="bfgs":
            s=xnew-x; y=gnew-g; ys=float(y@s)
            if ys>1e-14:
                rho=1/ys; I=np.eye(len(x))
                H=(I-rho*np.outer(s,y))@H@(I-rho*np.outer(y,s))+rho*np.outer(s,s)
        rows.append([k,*xnew.tolist(),f(xnew),float(np.linalg.norm(gnew)),alpha])
        if np.linalg.norm(xnew-x)<=tolerance*(1+np.linalg.norm(xnew)):
            x=xnew; status="success"; termination="El desplazamiento alcanzó la tolerancia."; break
        x=xnew
    return pack_result(
        "optimization",method,{"expression":expression,"initial":initial,
            "variables":names,"tolerance":tolerance,"max_iter":max_iter},
        {"minimizer":dict(zip(names,x.tolist())),"objective":f(x)},
        {"gradient_norm":float(np.linalg.norm(grad(x))),"iterations":len(rows),
         "converged":status=="success", "termination":termination},
        ["Gradiente aproximado mediante diferencias centrales.",
         "Se usó búsqueda lineal con condición de Armijo.", termination],
        [table("Iteraciones",["k",*names,"f","||grad f||","alpha"],rows)],
        [{"name":"Convergencia", "series":[{"label":"f(xk)",
            "x":[r[0] for r in rows],"y":[r[-3] for r in rows]}]}],
        status=status)


def solve_bvp(rhs_expression: str, a: float, b: float, alpha: float, beta: float,
              n: int = 40, method: str = "shooting") -> dict[str, Any]:
    a,b,alpha,beta=map(finite,(a,b,alpha,beta))
    n=int(n)
    if a>=b or not 3<=n<=300: raise ValueError("Se requiere a<b y 3<=n<=300.")
    h=(b-a)/n; xs=np.linspace(a,b,n+1)
    if method=="finite_difference":
        # Alcance: y''=f(x), por lo que la discretización es lineal.
        rhs=np.array([safe_eval(rhs_expression,{"x":float(x)}) for x in xs[1:-1]])
        M=np.diag(np.full(n-1,-2.0))+np.diag(np.ones(n-2),1)+np.diag(np.ones(n-2),-1)
        vec=h*h*rhs; vec[0]-=alpha; vec[-1]-=beta
        ys=np.r_[alpha,np.linalg.solve(M,vec),beta]
    elif method=="shooting":
        def integrate_slope(slope):
            y,v=alpha,slope; sol=[y]
            def fun(x,y,v): return safe_eval(rhs_expression,{"x":x,"y":y,"yp":v})
            for i in range(n):
                x=xs[i]
                k1y,k1v=v,fun(x,y,v)
                k2y,k2v=v+h*k1v/2,fun(x+h/2,y+h*k1y/2,v+h*k1v/2)
                k3y,k3v=v+h*k2v/2,fun(x+h/2,y+h*k2y/2,v+h*k2v/2)
                k4y,k4v=v+h*k3v,fun(x+h,y+h*k3y,v+h*k3v)
                y+=h*(k1y+2*k2y+2*k3y+k4y)/6
                v+=h*(k1v+2*k2v+2*k3v+k4v)/6
                sol.append(y)
            return np.array(sol)
        s0,s1=0.0,1.0; y0=integrate_slope(s0); y1=integrate_slope(s1)
        shooting_converged=False; shooting_iterations=0
        for shooting_iterations in range(1,101):
            d0=y0[-1]-beta; d1=y1[-1]-beta
            if abs(d1)<1e-8:
                shooting_converged=True
                break
            if abs(d1-d0)<1e-14: raise ValueError("Disparo secante: denominador nulo.")
            s2=s1-d1*(s1-s0)/(d1-d0); s0,s1=s1,s2; y0,y1=y1,integrate_slope(s1)
        ys=y1
    else: raise ValueError("Método BVP debe ser shooting o finite_difference.")
    return pack_result(
        "boundary_value",method,{"rhs_expression":rhs_expression,"a":a,"b":b,
            "alpha":alpha,"beta":beta,"n":n},
        {"x":xs.tolist(),"y":ys.tolist()},
        {"boundary_residual":float(abs(ys[-1]-beta)),
         "iterations": locals().get("shooting_iterations", 0),
         "converged": method=="finite_difference" or locals().get("shooting_converged", False)},
        ["Se resolvió el problema y'' = f(...), y(a)=alpha, y(b)=beta.",
         "finite_difference admite f(x); shooting admite f(x,y,y')."],
        [table("Solución",["x","y"],[[float(x),float(y)] for x,y in zip(xs,ys)])],
        [{"name":"Solución de frontera","series":[{"label":"y(x)",
            "x":xs.tolist(),"y":ys.tolist()}]}],
        [] if method=="finite_difference" or locals().get("shooting_converged", False)
        else ["Shooting agotó 100 iteraciones; revise la función y condiciones."],
        status="success" if method=="finite_difference" or locals().get("shooting_converged", False)
        else "no_convergence")


def solve_pde(problem_type: str, length: float, nx: int, nt: int,
              diffusivity: float = 1.0, speed: float = 1.0,
              initial_values: list[float] | None = None,
              initial_expression: str = "sin(pi*x)",
              boundary_left: float = 0.0, boundary_right: float = 0.0,
              dt: float | None = None) -> dict[str, Any]:
    length=finite(length,"length"); nx=int(nx); nt=int(nt)
    if length<=0 or not 4<=nx<=100 or not 2<=nt<=300:
        raise ValueError("Requiere length>0, 4<=nx<=100 y 2<=nt<=300.")
    kind=problem_type.lower().strip(); x=np.linspace(0,length,nx+1)
    dx=length/nx; dt=finite(dt if dt is not None else 1.0/nt,"dt")
    if dt<=0: raise ValueError("dt debe ser positivo.")
    if initial_values is not None:
        if len(initial_values)!=nx+1: raise ValueError("initial_values debe tener nx+1 valores.")
        u0=np.array([finite(v,"valor inicial") for v in initial_values])
    else:
        u0=np.array([safe_eval(initial_expression,{"x":float(xx),"pi":math.pi})
                     for xx in x])
    u0[0]=finite(boundary_left,"boundary_left"); u0[-1]=finite(boundary_right,"boundary_right")
    times=np.arange(nt+1)*dt
    if kind=="heat":
        diffusivity=finite(diffusivity,"diffusivity")
        if diffusivity<=0: raise ValueError("diffusivity debe ser positiva.")
        r=diffusivity*dt/(dx*dx)
        if r>0.5: raise ValueError(f"Inestabilidad explícita: alpha*dt/dx²={r:.4g} > 0.5.")
        U=np.zeros((nt+1,nx+1)); U[0]=u0
        for j in range(nt):
            U[j+1,1:-1]=U[j,1:-1]+r*(U[j,2:]-2*U[j,1:-1]+U[j,:-2])
            U[j+1,0]=boundary_left; U[j+1,-1]=boundary_right
        description=f"Ecuación del calor explícita, r={r:.5g}."
    elif kind=="wave":
        speed=finite(speed,"speed")
        if speed<=0: raise ValueError("speed debe ser positiva.")
        r=speed*dt/dx
        if r>1: raise ValueError(f"Condición CFL incumplida: c*dt/dx={r:.4g} > 1.")
        U=np.zeros((nt+1,nx+1)); U[0]=u0
        U[1,1:-1]=u0[1:-1]+0.5*r*r*(u0[2:]-2*u0[1:-1]+u0[:-2])
        U[:,0]=boundary_left; U[:,-1]=boundary_right
        for j in range(1,nt):
            U[j+1,1:-1]=2*U[j,1:-1]-U[j-1,1:-1]+r*r*(U[j,2:]-2*U[j,1:-1]+U[j,:-2])
        description=f"Ecuación de onda explícita, CFL={r:.5g}."
    elif kind=="laplace":
        U=np.linspace(boundary_left,boundary_right,nx+1)[None,:]
        times=np.array([0.0]); description="Ecuación de Laplace 1D; solución lineal."
    else: raise ValueError("problem_type debe ser heat, wave o laplace.")
    spatial_indices=sorted(set(np.linspace(0,nx,min(nx+1,7),dtype=int).tolist()))
    time_indices=sorted(set(np.linspace(0,len(times)-1,min(len(times),21),dtype=int).tolist()))
    heat_rows=[[float(times[j]),*[float(U[j,i]) for i in spatial_indices]] for j in time_indices]
    profile_rows=[[float(xx),float(value)] for xx,value in zip(x,U[-1])]
    profile_chart={"name":"Perfil final u(x)","series":[
        {"label":"u(x)","x":x.tolist(),"y":U[-1].tolist()}]}
    if kind=="laplace":
        charts=[profile_chart]
    else:
        heatmap={"name":description,"type":"heatmap","x":x.tolist(),
                 "y":times.tolist(),"z":U.tolist()}
        charts=[heatmap,profile_chart]
    return pack_result(
        "pde",kind,{"length":length,"nx":nx,"nt":nt,"dt":dt,
            "diffusivity":diffusivity,"speed":speed,"boundary_left":boundary_left,
            "boundary_right":boundary_right,"initial_expression":initial_expression},
        {"x":x.tolist(),"time":times.tolist(),"solution":U.tolist(),
         "final_profile":U[-1].tolist()},
        {"dx":dx,"dt":dt,"stability":description},
        [description,"Método de diferencias finitas 1D."],
        [table("Perfiles temporales en posiciones representativas",
               ["t",*[f"u(x={x[i]:.4g})" for i in spatial_indices]],heat_rows),
         table("Perfil espacial final",["x","u(x)"],profile_rows)],
        charts)
def analyze_float_arithmetic(values: list[float], precision_digits: int = 8) -> dict[str, Any]:
    """Compara suma IEEE-754, suma compensada y acumulación decimal redondeada."""
    from decimal import Decimal, localcontext

    if not isinstance(values, list) or not 1 <= len(values) <= _MAX_ITEMS:
        raise ValueError(f"Se requiere una lista de 1 a {_MAX_ITEMS} valores.")
    numbers = [finite(v, f"valor {i+1}") for i,v in enumerate(values)]
    precision_digits = int(precision_digits)
    if not 1 <= precision_digits <= 50:
        raise ValueError("precision_digits debe estar entre 1 y 50.")
    with localcontext() as reference_context:
        reference_context.prec = 1000
        exact_decimal = sum((Decimal(str(v)) for v in numbers), Decimal(0))
    naive = 0.0
    rounded = Decimal(0)
    exact_prefix = Decimal(0)
    rows = []
    float_errors = []
    with localcontext() as ctx:
        ctx.prec = precision_digits
        for i, value in enumerate(numbers, 1):
            naive += value
            if not math.isfinite(naive):
                raise ValueError("La suma float desbordó el rango finito.")
            term = Decimal(str(value))
            rounded += term
            with localcontext() as reference_context:
                reference_context.prec = 1000
                exact_prefix += term
                float_errors.append(abs(float(Decimal.from_float(naive) - exact_prefix)))
            rows.append([i, value, naive, str(+rounded)])
        rounded = +rounded
    try:
        stable = math.fsum(numbers)
    except OverflowError as exc:
        raise ValueError("La suma compensada desbordó el rango finito.") from exc
    with localcontext() as reference_context:
        reference_context.prec = 1000
        naive_error = abs(Decimal.from_float(naive) - exact_decimal)
        stable_error = abs(Decimal.from_float(stable) - exact_decimal)
        rounded_error = abs(rounded - exact_decimal)
    return pack_result(
        "floating_point", "Suma secuencial y redondeo decimal",
        {"values": numbers, "precision_digits": precision_digits},
        {"decimal_reference": str(exact_decimal), "sequential_float_sum": naive,
         "compensated_float_sum": stable, "rounded_decimal_sum": str(rounded)},
        {"sequential_absolute_error": float(naive_error),
         "compensated_absolute_error": float(stable_error),
         "rounded_absolute_error": float(rounded_error),
         "precision_digits": precision_digits},
        ["La referencia suma los decimales de entrada con Decimal.",
         "La suma secuencial usa float IEEE-754; math.fsum reduce pérdida acumulada.",
         "La suma decimal redondea en cada operación a la precisión indicada."],
        [table("Acumulación", ["k", "término", "suma float", "suma decimal redondeada"], rows)],
        [{"name": "Error absoluto acumulado", "series": [
            {"label": "float secuencial", "x": list(range(1, len(rows)+1)),
             "y": float_errors}]}])



def solve_nonlinear_system(equations: list[str], variables: list[str],
                           initial: list[float], tolerance: float = 1e-8,
                           max_iter: int = 100, damping: bool = True) -> dict[str, Any]:
    """Resuelve F(x)=0 con Newton multivariable y Jacobiano por diferencias centrales."""
    if not isinstance(equations, list) or not 1 <= len(equations) <= 5:
        raise ValueError("Se requieren entre 1 y 5 ecuaciones.")
    if not isinstance(variables, list) or len(variables) != len(equations):
        raise ValueError("Indique una variable distinta por ecuación.")
    if not isinstance(initial, list) or len(initial) != len(variables):
        raise ValueError("initial debe tener un valor por variable.")
    if (any(not isinstance(name, str) or not name.isidentifier() for name in variables)
            or len(set(variables)) != len(variables)
            or any(name in {"pi", "e", "x", "y", "t"} for name in variables)):
        raise ValueError("Use nombres de variables únicos y no reservados.")
    x = np.asarray([finite(value, "estimación inicial") for value in initial], dtype=float)
    tol = finite(tolerance, "tolerancia")
    max_iter = int(max_iter)
    if not 0 < tol < 1 or not 1 <= max_iter <= 500:
        raise ValueError("Se requiere 0<tolerance<1 y 1<=max_iter<=500.")

    def residual(point: np.ndarray) -> np.ndarray:
        values = dict(zip(variables, point.tolist()))
        return np.asarray([safe_eval(eq, values) for eq in equations], dtype=float)

    def jacobian(point: np.ndarray, base: np.ndarray) -> np.ndarray:
        matrix = np.empty((len(equations), len(point)), dtype=float)
        for col in range(len(point)):
            h = np.cbrt(np.finfo(float).eps) * max(1.0, abs(float(point[col])))
            plus, minus = point.copy(), point.copy()
            plus[col] += h
            minus[col] -= h
            matrix[:, col] = (residual(plus) - residual(minus)) / (2.0 * h)
        return matrix

    rows: list[list[Any]] = []
    status, termination = "no_convergence", "Se alcanzó el máximo de iteraciones."
    for iteration in range(max_iter + 1):
        fval = residual(x)
        norm = float(np.linalg.norm(fval, ord=2))
        if norm <= tol:
            status, termination = "success", "La norma del residuo alcanzó la tolerancia."
            break
        if iteration == max_iter:
            break
        jac = jacobian(x, fval)
        delta, _, rank, _ = np.linalg.lstsq(jac, -fval, rcond=None)
        if rank < len(variables):
            termination = "El Jacobiano es singular o deficiente en rango."
            break
        alpha, accepted = 1.0, False
        for _ in range(24 if damping else 1):
            candidate = x + alpha * delta
            try:
                candidate_norm = float(np.linalg.norm(residual(candidate)))
            except (ValueError, ArithmeticError, OverflowError):
                candidate_norm = math.inf
            if math.isfinite(candidate_norm) and (candidate_norm < norm or not damping):
                accepted = True
                break
            alpha *= 0.5
        if not accepted:
            termination = "La búsqueda amortiguada no encontró una reducción del residuo."
            break
        rows.append([iteration + 1, *candidate.tolist(), candidate_norm, alpha])
        x = candidate

    final_residual = residual(x)
    final_norm = float(np.linalg.norm(final_residual))
    return pack_result(
        "nonlinear_system", "Newton multivariable",
        {"equations": equations, "variables": variables, "initial": initial,
         "tolerance": tol, "max_iter": max_iter, "damping": bool(damping)},
        {"solution": dict(zip(variables, x.tolist())),
         "residual": final_residual.tolist()},
        {"residual_norm": final_norm, "iterations": len(rows),
         "converged": status == "success", "termination": termination},
        ["Se aproximó el Jacobiano con diferencias centrales.",
         "Se aplicó amortiguamiento para reducir la norma del residuo." if damping
          else "Se usó el paso completo de Newton.", termination],
        [table("Iteraciones de Newton", ["k", *variables, "||F(x)||", "alpha"], rows)],
        [{"name": "Residuo", "series": [{"label": "||F(xk)||",
          "x": [row[0] for row in rows], "y": [row[-2] for row in rows]}]}],
        [] if status == "success" else [termination], status=status)


def analyze_conditioning(matrix: list[list[float]], vector: list[float] | None = None,
                         perturbation: list[float] | None = None,
                         norm: str = "2") -> dict[str, Any]:
    """Estima el número de condición de A y, opcionalmente, la sensibilidad de Ax=b."""
    A = np.asarray(matrix, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1] or not 1 <= A.shape[0] <= 150:
        raise ValueError("matrix debe ser cuadrada y tener tamaño entre 1 y 150.")
    if not np.isfinite(A).all():
        raise ValueError("La matriz debe contener valores finitos.")
    norms = {"1": 1, "2": 2, "inf": np.inf, "infinity": np.inf}
    norm_key = str(norm).lower().strip()
    if norm_key not in norms:
        raise ValueError("norm debe ser '1', '2' o 'inf'.")
    norm_key = "inf" if norm_key == "infinity" else norm_key
    condition = float(np.linalg.cond(A, p=norms[norm_key]))
    result: dict[str, Any] = {"condition_number": condition, "norm": norm_key}
    diagnostics: dict[str, Any] = {"singular": not math.isfinite(condition),
                                   "interpretation": "alta sensibilidad" if condition > 1e8 else "condicionamiento moderado o bajo"}
    steps = ["Se calculó κ(A)=||A||·||A⁻¹|| en la norma seleccionada.",
             "Un número de condición alto indica que pequeñas perturbaciones pueden amplificarse."]
    tables = [table("Resumen de condición", ["Medida", "Valor"],
                    [["Norma", norm_key], ["Número de condición", condition]])]
    if vector is not None:
        b = np.asarray([finite(v, "vector b") for v in vector], dtype=float)
        if b.shape != (A.shape[0],):
            raise ValueError("vector debe tener el mismo tamaño que matrix.")
        try:
            solution = np.linalg.solve(A, b)
        except np.linalg.LinAlgError as exc:
            raise ValueError("A es singular; no se puede analizar Ax=b.") from exc
        result["solution"] = solution.tolist()
        result["relative_residual"] = float(np.linalg.norm(A @ solution - b) /
            max(np.linalg.norm(b), np.finfo(float).tiny))
        if perturbation is not None:
            delta_b = np.asarray([finite(v, "perturbación") for v in perturbation], dtype=float)
            if delta_b.shape != b.shape:
                raise ValueError("perturbation debe tener el mismo tamaño que vector.")
            x_perturbed = np.linalg.solve(A, b + delta_b)
            input_rel = float(np.linalg.norm(delta_b) /
                max(np.linalg.norm(b), np.finfo(float).tiny))
            output_rel = float(np.linalg.norm(x_perturbed - solution) /
                max(np.linalg.norm(solution), np.finfo(float).tiny))
            result.update({"perturbed_solution": x_perturbed.tolist(),
                           "relative_input_perturbation": input_rel,
                           "relative_solution_change": output_rel,
                           "observed_amplification": output_rel / input_rel if input_rel else 0.0})
            diagnostics["condition_bound"] = condition * input_rel
            tables.append(table("Sensibilidad observada", ["Medida", "Valor"], [
                ["Perturbación relativa de b", input_rel],
                ["Cambio relativo de x", output_rel],
                ["Cota aproximada κ(A)·perturbación", condition * input_rel]]))
            steps.append("Se resolvió también A(x+Δx)=b+Δb para medir el cambio observado.")
    return pack_result("conditioning", "Número de condición y sensibilidad",
        {"matrix": A.tolist(), "vector": vector, "perturbation": perturbation, "norm": norm_key},
        result, diagnostics, steps, tables,
        [{"name": "Sensibilidad", "series": []}])


def solve_ode_multistep(equations: list[str], initial_state: list[float],
                        t0: float, t_end: float, step: float = 0.1,
                        method: str = "ab4", state_names: list[str] | None = None) -> dict[str, Any]:
    """Resuelve un PVI con Adams-Bashforth 2/4 o predictor-corrector ABM4."""
    if not equations or len(equations) != len(initial_state) or len(equations) > 8:
        raise ValueError("Debe haber una ecuación por variable de estado (1–8).")
    y0 = np.asarray([finite(v, "estado inicial") for v in initial_state], dtype=float)
    t0, t_end, step = finite(t0, "t0"), finite(t_end, "t_end"), finite(step, "paso")
    if t_end <= t0 or step <= 0:
        raise ValueError("Se requiere t_end>t0 y paso positivo.")
    count = int(math.ceil((t_end - t0) / step))
    if not 1 <= count <= 5000:
        raise ValueError("El número de pasos debe estar entre 1 y 5000.")
    method = method.lower().strip()
    if method not in {"ab2", "ab4", "abm4"}:
        raise ValueError("method debe ser 'ab2', 'ab4' o 'abm4'.")
    names = state_names or [f"y{i}" for i in range(len(y0))]
    if len(names) != len(y0) or len(set(names)) != len(names) or any(not isinstance(n, str) or not n.isidentifier() for n in names):
        raise ValueError("state_names debe tener identificadores únicos, uno por estado.")
    if any(n in {"t", "x", "pi", "e"} for n in names):
        raise ValueError("state_names no puede usar t, x, pi o e.")
    ts = np.linspace(t0, t_end, count + 1)
    h = float(ts[1] - ts[0])

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        env = {"t": float(t), "x": float(t)}
        env.update(dict(zip(names, y.tolist())))
        return np.asarray([safe_eval(eq, env) for eq in equations], dtype=float)

    values = [y0.copy()]
    derivatives = [rhs(float(ts[0]), y0)]
    startup_count = min(count, 1 if method == "ab2" else 3)
    for i in range(startup_count):
        t, y = float(ts[i]), values[-1]
        k1 = rhs(t, y); k2 = rhs(t+h/2, y+h*k1/2)
        k3 = rhs(t+h/2, y+h*k2/2); k4 = rhs(t+h, y+h*k3)
        next_y = y + h*(k1+2*k2+2*k3+k4)/6
        values.append(next_y)
        derivatives.append(rhs(float(ts[i+1]), next_y))
    rows: list[list[Any]] = []
    for i in range(startup_count, count):
        current = values[-1]
        if method == "ab2":
            next_y = current + h*(3*derivatives[-1]-derivatives[-2])/2
        else:
            if len(derivatives) < 4:
                raise ValueError("No hay suficientes pasos de inicio para AB4.")
            predictor = current + h*(55*derivatives[-1]-59*derivatives[-2]+
                        37*derivatives[-3]-9*derivatives[-4])/24
            if method == "abm4":
                f_predictor = rhs(float(ts[i+1]), predictor)
                next_y = current + h*(9*f_predictor+19*derivatives[-1]-
                             5*derivatives[-2]+derivatives[-3])/24
            else:
                next_y = predictor
        values.append(next_y)
        derivatives.append(rhs(float(ts[i+1]), next_y))
        rows.append([float(ts[i+1]), *next_y.tolist()])
    matrix = np.asarray(values)
    return pack_result("ode_multistep", method,
        {"equations": equations, "initial_state": y0.tolist(), "t0": t0,
         "t_end": t_end, "step": h, "state_names": names, "startup_method": "RK4"},
        {"final_time": float(ts[-1]), "final_state": matrix[-1].tolist()},
        {"steps": count, "startup_steps": startup_count, "converged": True,
         "error_estimate": None},
        [f"Se resolvió el PVI con {method.upper()} y arranque RK4.",
         "El método usa paso fijo; no calcula una estimación automática del error global."],
        [table("Trayectoria multipaso", ["t", *names],
               [[float(t), *row.tolist()] for t, row in zip(ts, matrix)])],
        [{"name": "Solución multipaso", "series": [
            {"label": name, "x": ts.tolist(), "y": matrix[:, j].tolist()}
            for j, name in enumerate(names)]}])


def solve_pde_2d(problem_type: str, length_x: float, length_y: float,
                 nx: int, ny: int, source_expression: str = "0",
                 boundary_left: list[float] | None = None,
                 boundary_right: list[float] | None = None,
                 boundary_bottom: list[float] | None = None,
                 boundary_top: list[float] | None = None,
                 method: str = "sor", omega: float = 1.5,
                 tolerance: float = 1e-6, max_iter: int = 3000) -> dict[str, Any]:
    """Resuelve Laplace/Poisson 2D en rectángulo con diferencias finitas y frontera Dirichlet."""
    lx, ly = finite(length_x, "length_x"), finite(length_y, "length_y")
    nx, ny = int(nx), int(ny)
    if lx <= 0 or ly <= 0 or not 4 <= nx <= 50 or not 4 <= ny <= 50:
        raise ValueError("Se requieren longitudes positivas y 4<=nx,ny<=50.")
    kind, method = problem_type.lower().strip(), method.lower().strip()
    if kind not in {"laplace", "poisson"}:
        raise ValueError("problem_type debe ser 'laplace' o 'poisson'.")
    if method not in {"sor", "gauss_seidel"}:
        raise ValueError("method debe ser 'sor' o 'gauss_seidel'.")
    tol, max_iter = finite(tolerance, "tolerance"), int(max_iter)
    w = finite(omega, "omega")
    if not 0 < tol < 1 or not 1 <= max_iter <= 10000 or not 0 < w < 2:
        raise ValueError("Se requiere 0<tolerance<1, 1<=max_iter<=10000 y 0<omega<2.")
    dx, dy = lx/nx, ly/ny
    xs, ys = np.linspace(0, lx, nx+1), np.linspace(0, ly, ny+1)
    def boundary(values: list[float] | None, length: int, label: str) -> np.ndarray:
        raw = values if values is not None else [0.0] * length
        if len(raw) != length:
            raise ValueError(f"{label} debe tener {length} valores.")
        return np.asarray([finite(v, label) for v in raw], dtype=float)
    left = boundary(boundary_left, ny+1, "boundary_left")
    right = boundary(boundary_right, ny+1, "boundary_right")
    bottom = boundary(boundary_bottom, nx+1, "boundary_bottom")
    top = boundary(boundary_top, nx+1, "boundary_top")
    for a, b, label in ((left[0], bottom[0], "esquina inferior izquierda"),
                        (right[0], bottom[-1], "esquina inferior derecha"),
                        (left[-1], top[0], "esquina superior izquierda"),
                        (right[-1], top[-1], "esquina superior derecha")):
        if not math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError(f"Los valores de frontera no coinciden en la {label}.")
    u = np.zeros((ny+1, nx+1), dtype=float)
    u[:, 0], u[:, -1], u[0, :], u[-1, :] = left, right, bottom, top
    if kind == "laplace" and source_expression.strip() not in {"", "0", "0.0"}:
        raise ValueError("Para Laplace, source_expression debe ser 0.")
    f = np.zeros((ny-1, nx-1), dtype=float)
    if kind == "poisson":
        f = np.asarray([[safe_eval(source_expression, {"x": float(x), "y": float(y)})
                         for x in xs[1:-1]] for y in ys[1:-1]])
    ax, ay = 1/(dx*dx), 1/(dy*dy)
    denominator = 2*ax + 2*ay
    rows: list[list[Any]] = []
    sample_every = max(1, max_iter // 50)
    converged = False
    for iteration in range(1, max_iter+1):
        max_change = 0.0
        for j in range(1, ny):
            for i in range(1, nx):
                old = u[j, i]
                gs = (ax*(u[j, i-1]+u[j, i+1]) + ay*(u[j-1, i]+u[j+1, i]) - f[j-1, i-1])/denominator
                u[j, i] = old + (w if method == "sor" else 1.0)*(gs-old)
                max_change = max(max_change, abs(u[j, i]-old))
        if iteration == 1 or iteration % sample_every == 0 or iteration == max_iter:
            residual = ax*(u[1:-1, :-2]+u[1:-1, 2:]-2*u[1:-1, 1:-1]) + \
                       ay*(u[:-2, 1:-1]+u[2:, 1:-1]-2*u[1:-1, 1:-1]) - f
            residual_norm = float(np.max(np.abs(residual)))
            rows.append([iteration, residual_norm, max_change])
            if residual_norm <= tol:
                converged = True
                break
    residual = ax*(u[1:-1, :-2]+u[1:-1, 2:]-2*u[1:-1, 1:-1]) + \
               ay*(u[:-2, 1:-1]+u[2:, 1:-1]-2*u[1:-1, 1:-1]) - f
    residual_norm = float(np.max(np.abs(residual)))
    status = "success" if converged else "no_convergence"
    return pack_result("pde_2d", kind.upper()+" 2D por " + method.upper(),
        {"problem_type": kind, "length_x": lx, "length_y": ly, "nx": nx, "ny": ny,
         "source_expression": source_expression, "method": method, "omega": w,
         "tolerance": tol, "max_iter": max_iter},
        {"x": xs.tolist(), "y": ys.tolist(), "solution": u.tolist()},
        {"iterations": rows[-1][0] if rows else 0, "residual_inf_norm": residual_norm,
         "converged": converged, "grid_shape": [ny+1, nx+1]},
        ["Se resolvió Δu=f en un rectángulo con condiciones de Dirichlet.",
         "La aproximación usa diferencias finitas de cinco puntos.",
         "La matriz se actualiza con Gauss-Seidel o relajación SOR."],
        [table("Convergencia", ["iteración", "norma infinito del residuo", "cambio máximo"], rows)],
        [{"name": "Mapa u(x,y)", "type": "heatmap", "x": xs.tolist(),
          "y": ys.tolist(), "z": u.tolist(), "x_label": "x", "y_label": "y"}],
        [] if converged else ["No se alcanzó la tolerancia antes de max_iter."], status=status)


def optimize_constrained(expression: str, initial: list[float],
                         variables: list[str] | None = None,
                         bounds: list[list[float | None]] | None = None,
                         equality_constraints: list[str] | None = None,
                         inequality_constraints: list[str] | None = None,
                         tolerance: float = 1e-7, max_iter: int = 500) -> dict[str, Any]:
    """Minimiza una función con restricciones g(x)=0 y h(x)>=0 mediante SLSQP."""
    from scipy.optimize import minimize
    x0 = np.asarray([finite(v, "punto inicial") for v in initial], dtype=float)
    if not 1 <= len(x0) <= 5:
        raise ValueError("Se admiten entre 1 y 5 variables.")
    names = variables or [f"x{i}" for i in range(len(x0))]
    if len(names) != len(x0) or len(set(names)) != len(names) or any(not isinstance(n, str) or not n.isidentifier() for n in names):
        raise ValueError("Indique nombres únicos y válidos para cada variable.")
    if any(n in {"pi", "e", "x", "y", "t"} for n in names):
        raise ValueError("No use nombres reservados como pi, e, x, y o t.")
    eqs, ineqs = equality_constraints or [], inequality_constraints or []
    if len(eqs) + len(ineqs) > 10:
        raise ValueError("Se admiten como máximo 10 restricciones.")
    tol, max_iter = finite(tolerance, "tolerance"), int(max_iter)
    if tol <= 0 or not 1 <= max_iter <= 2000:
        raise ValueError("Tolerancia positiva y 1<=max_iter<=2000 requeridos.")
    env = lambda point: dict(zip(names, np.asarray(point, dtype=float).tolist()))
    objective = lambda point: safe_eval(expression, env(point))
    constraints = ([{"type": "eq", "fun": lambda point, e=e: safe_eval(e, env(point))} for e in eqs] +
                   [{"type": "ineq", "fun": lambda point, e=e: safe_eval(e, env(point))} for e in ineqs])
    normalized_bounds = None
    if bounds is not None:
        if len(bounds) != len(x0):
            raise ValueError("bounds debe incluir un par por variable.")
        normalized_bounds = []
        for pair in bounds:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError("Cada bound debe ser [mínimo,máximo].")
            low = None if pair[0] is None else finite(pair[0], "límite inferior")
            high = None if pair[1] is None else finite(pair[1], "límite superior")
            if low is not None and high is not None and low > high:
                raise ValueError("El límite inferior no puede superar al superior.")
            normalized_bounds.append((low, high))
    result = minimize(objective, x0, method="SLSQP", bounds=normalized_bounds,
                      constraints=constraints,
                      options={"ftol": tol, "maxiter": max_iter, "disp": False})
    point = np.asarray(result.x, dtype=float)
    eq_residuals = [safe_eval(e, env(point)) for e in eqs]
    ineq_values = [safe_eval(e, env(point)) for e in ineqs]
    feasible = all(abs(v) <= max(tol*10, 1e-6) for v in eq_residuals) and all(v >= -max(tol*10, 1e-6) for v in ineq_values)
    status = "success" if result.success and feasible else "no_convergence"
    return pack_result("constrained_optimization", "SLSQP",
        {"expression": expression, "initial": x0.tolist(), "variables": names,
         "bounds": bounds, "equality_constraints": eqs,
         "inequality_constraints": ineqs, "tolerance": tol, "max_iter": max_iter},
        {"minimizer": dict(zip(names, point.tolist())), "objective": float(result.fun),
         "equality_values": eq_residuals, "inequality_values": ineq_values},
        {"converged": bool(result.success), "feasible": feasible,
         "iterations": int(getattr(result, "nit", 0)), "termination": str(result.message)},
        ["SLSQP trata g(x)=0 como igualdad y h(x)>=0 como desigualdad.",
         "La convergencia numérica no garantiza un mínimo global."],
        [table("Restricciones en la solución", ["tipo", "expresión", "valor"],
               [["igualdad", e, v] for e, v in zip(eqs, eq_residuals)] +
               [["desigualdad >= 0", e, v] for e, v in zip(ineqs, ineq_values)])],
        [{"name": "Restricciones", "series": []}],
        [] if status == "success" else ["SLSQP no confirmó simultáneamente convergencia y factibilidad."],
        status=status)


def solve_sparse_eigenvalues(size: int, entries: list[list[float]], count: int = 1,
                             which: str = "LM", tolerance: float = 1e-8,
                             max_iter: int = 1000) -> dict[str, Any]:
    """Calcula pares propios dominantes de una matriz simétrica en formato COO disperso."""
    from scipy.sparse.linalg import eigsh
    size, count, max_iter = int(size), int(count), int(max_iter)
    if not 2 <= size <= 10000 or not 1 <= count <= min(20, size-1):
        raise ValueError("Se requiere 2<=size<=10000 y 1<=count<=min(20,size-1).")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 200000:
        raise ValueError("entries debe contener entre 1 y 200000 tripletas COO.")
    row_ids, col_ids, values = [], [], []
    for index, item in enumerate(entries):
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise ValueError(f"La entrada {index+1} debe ser [fila,columna,valor].")
        row, col = int(item[0]), int(item[1])
        if row != item[0] or col != item[1] or not 0 <= row < size or not 0 <= col < size:
            raise ValueError("Los índices COO deben ser enteros base 0 dentro de la matriz.")
        row_ids.append(row); col_ids.append(col); values.append(finite(item[2], "valor COO"))
    matrix = coo_matrix((values, (row_ids, col_ids)), shape=(size, size)).tocsr()
    matrix.sum_duplicates()
    difference = matrix - matrix.T
    if difference.nnz and float(np.max(np.abs(difference.data))) > 1e-10:
        raise ValueError("eigsh requiere una matriz simétrica.")
    which = which.upper().strip()
    if which not in {"LM", "SM", "LA", "SA"}:
        raise ValueError("which debe ser LM, SM, LA o SA.")
    tol, max_iter = finite(tolerance, "tolerance"), int(max_iter)
    if tol <= 0 or not 1 <= max_iter <= 10000:
        raise ValueError("Tolerancia positiva y max_iter entre 1 y 10000 requeridos.")
    vals, vectors = eigsh(matrix, k=count, which=which, tol=tol, maxiter=max_iter)
    if which == "LM":
        order = np.argsort(-np.abs(vals))
    elif which == "SM":
        order = np.argsort(np.abs(vals))
    elif which == "LA":
        order = np.argsort(-vals)
    else:
        order = np.argsort(vals)
    pairs = []
    for i in order:
        vector = vectors[:, i]
        value = float(vals[i])
        pairs.append({"value": value, "vector": vector.tolist(),
                      "residual": float(np.linalg.norm(matrix @ vector - value * vector))})
    return pack_result("sparse_eigenvalues", "Lanczos / ARPACK (eigsh)",
        {"size": size, "entries": entries, "count": count, "which": which,
         "tolerance": tol, "max_iter": max_iter},
        {"eigenpairs": pairs},
        {"converged": True, "residuals": [pair["residual"] for pair in pairs],
         "nonzero_entries": int(matrix.nnz)},
        ["La matriz se mantuvo dispersa durante el cálculo.",
         "Se requiere simetría real; ARPACK puede fallar si k es cercano al tamaño de la matriz."],
        [table("Pares propios", ["valor", "vector", "residuo"],
               [[p["value"], p["vector"], p["residual"]] for p in pairs])],
        [{"name": "Residuos propios", "series": [{"label": "residuo",
          "x": list(range(1, len(pairs)+1)), "y": [p["residual"] for p in pairs]}]}])


def integrate_adaptive(expression: str, a: float, b: float,
                       absolute_tolerance: float = 1e-9,
                       relative_tolerance: float = 1e-9,
                       max_subintervals: int = 200) -> dict[str, Any]:
    """Integra adaptativamente con cuadratura Gauss-Kronrod y estima el error."""
    from scipy.integrate import quad
    a, b = finite(a, "a"), finite(b, "b")
    epsabs, epsrel = finite(absolute_tolerance, "absolute_tolerance"), finite(relative_tolerance, "relative_tolerance")
    limit = int(max_subintervals)
    if a == b or epsabs <= 0 or epsrel <= 0 or not 1 <= limit <= 500:
        raise ValueError("Se requiere a!=b, tolerancias positivas y 1<=max_subintervals<=500.")
    function = lambda x: safe_eval(expression, {"x": float(x)})
    output = quad(function, a, b, epsabs=epsabs, epsrel=epsrel, limit=limit,
                  full_output=1)
    value, error, info = float(output[0]), float(output[1]), output[2]
    message = str(output[3]) if len(output) > 3 else "Convergencia estimada por Gauss-Kronrod."
    intervals = int(info.get("last", 0))
    rows = [[float(info["alist"][i]), float(info["blist"][i]),
             float(info["rlist"][i]), float(info["elist"][i])]
            for i in range(min(intervals, 100))]
    status = "success" if len(output) == 3 else "no_convergence"
    chart_x = np.linspace(min(a, b), max(a, b), 120).tolist()
    chart_y = [function(float(x)) for x in chart_x]
    return pack_result("adaptive_quadrature", "Gauss-Kronrod adaptativa",
        {"expression": expression, "a": a, "b": b,
         "absolute_tolerance": epsabs, "relative_tolerance": epsrel,
         "max_subintervals": limit},
        {"integral": value, "estimated_absolute_error": error},
        {"function_evaluations": int(info.get("neval", 0)),
         "subintervals": intervals, "converged": status == "success",
         "termination": message},
        ["Se subdividió el intervalo de forma adaptativa mediante Gauss-Kronrod.",
         "La estimación de error es numérica y puede ser optimista para integrandos singulares."],
        [table("Subintervalos adaptativos", ["a_i", "b_i", "aporte", "error estimado"], rows)],
        [{"name": "Integrando", "series": [{"label": "f(x)", "x": chart_x, "y": chart_y}]}],
        [] if status == "success" else [message], status=status)
