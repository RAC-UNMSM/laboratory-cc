import sys
import sympy as sp
from validacion import (
    validar_y_parsear_expresion, 
    validar_limites_numericos, 
    validar_dominio_general,
    ErrorDeEntrada
)
from matematica import integrar_simple, integrar_doble_rectangular, integrar_doble_general
from visualizacion import generar_grafico_png
from reporte_html import generar_reporte_html

def menu_principal():
    print("\n" + "="*50)
    print(" CALCULADORA DE INTEGRALES (MODO LOCAL TERMINAL)")
    print("="*50)
    print("1. Integral Simple")
    print("2. Integral Doble (Dominio Rectangular)")
    print("3. Integral Doble General (Ej: Círculos, curvas)")
    print("4. Salir")
    print("="*50)

def ejecutar_integral_simple():
    print("\n--- INTEGRAL SIMPLE ---")
    expresion = input("Expresión f(x) [ej: x**2 o sen(x)]: ")
    x_min_raw = input("Límite inferior (x_min) [ej: 0 o -pi]: ")
    x_max_raw = input("Límite superior (x_max) [ej: 3 o pi/2]: ")

    x_min, x_max = validar_limites_numericos(x_min_raw, x_max_raw, "x")
    expr_sp = validar_y_parsear_expresion(expresion, variables=('x',))
    
    resultado, latex_str = integrar_simple(expr_sp, x_min, x_max)
    png_bytes = generar_grafico_png(expr_sp, x_min, x_max, mostrar_local=False)

    print("\n[RESULTADO]")
    print(f"  LaTeX:     $${latex_str} = {sp.latex(resultado)}$$")
    print(f"  Exacto:    {resultado}")
    print(f"  Decimal:   {float(resultado):.4f}")

    # Genera y abre automáticamente el reporte interactivo en el navegador
    generar_reporte_html(
        tipo_integral="Integral Simple",
        latex_str=latex_str,
        resultado_exacto=sp.latex(resultado),
        resultado_decimal=float(resultado),
        png_bytes=png_bytes,
        nombre_archivo="reporte_integral_simple.html",
        abrir_en_navegador=True
    )
    print("  Reporte:   Generado y abierto en el navegador (reporte_integral_simple.html)")

def ejecutar_integral_doble_rectangular():
    print("\n--- INTEGRAL DOBLE RECTANGULAR ---")
    expresion = input("Expresión f(x, y) [ej: x**2 + y**2]: ")
    x_min_raw = input("Límite x_min [ej: 0]: ")
    x_max_raw = input("Límite x_max [ej: 2]: ")
    y_min_raw = input("Límite y_min [ej: 0]: ")
    y_max_raw = input("Límite y_max [ej: 4]: ")

    x_min, x_max = validar_limites_numericos(x_min_raw, x_max_raw, "x")
    y_min, y_max = validar_limites_numericos(y_min_raw, y_max_raw, "y")
    expr_sp = validar_y_parsear_expresion(expresion, variables=('x', 'y'))

    resultado, latex_str = integrar_doble_rectangular(expr_sp, x_min, x_max, y_min, y_max)
    png_bytes = generar_grafico_png(expr_sp, x_min, x_max, y_min=y_min, y_max=y_max, mostrar_local=False)

    print("\n[RESULTADO]")
    print(f"  LaTeX:     $${latex_str} = {sp.latex(resultado)}$$")
    print(f"  Exacto:    {resultado}")
    print(f"  Decimal:   {float(resultado):.4f}")

    generar_reporte_html(
        tipo_integral="Integral Doble Rectangular",
        latex_str=latex_str,
        resultado_exacto=sp.latex(resultado),
        resultado_decimal=float(resultado),
        png_bytes=png_bytes,
        nombre_archivo="reporte_integral_doble.html",
        abrir_en_navegador=True
    )
    print("  Reporte:   Generado y abierto en el navegador (reporte_integral_doble.html)")

def ejecutar_integral_doble_general():
    print("\n--- INTEGRAL DOBLE GENERAL ---")
    expresion = input("Expresión f(x, y) [ej: x**2 + y**2]: ")
    var_int = input("Variable interna [ej: y]: ").strip()
    g1 = input("Límite inferior g1(x) [ej: -sqrt(1-x**2)]: ").strip()
    g2 = input("Límite superior g2(x) [ej: sqrt(1-x**2)]: ").strip()
    var_ext = input("Variable externa [ej: x]: ").strip()
    ext_min_raw = input(f"Límite inferior para {var_ext} [ej: -1]: ")
    ext_max_raw = input(f"Límite superior para {var_ext} [ej: 1]: ")

    expr_sp, v_int, v_ext, g1_sp, g2_sp, ext_min, ext_max = validar_dominio_general(
        expresion, var_int, g1, g2, var_ext, ext_min_raw, ext_max_raw
    )

    resultado, latex_str = integrar_doble_general(
        expr_sp, str(v_int), str(g1_sp), str(g2_sp), str(v_ext), ext_min, ext_max
    )
    
    png_bytes = generar_grafico_png(
        expr_sp, ext_min, ext_max, g1_str=str(g1_sp), g2_str=str(g2_sp), mostrar_local=False
    )

    print("\n[RESULTADO]")
    print(f"  LaTeX:     $${latex_str} = {sp.latex(resultado)}$$")
    print(f"  Exacto:    {resultado}")
    print(f"  Decimal:   {float(resultado):.4f}")

    generar_reporte_html(
        tipo_integral="Integral Doble General",
        latex_str=latex_str,
        resultado_exacto=sp.latex(resultado),
        resultado_decimal=float(resultado),
        png_bytes=png_bytes,
        nombre_archivo="reporte_integral_general.html",
        abrir_en_navegador=True
    )
    print("  Reporte:   Generado y abierto en el navegador (reporte_integral_general.html)")

def main():
    while True:
        menu_principal()
        opcion = input("Selecciona una opción (1-4): ").strip()
        
        try:
            if opcion == "1":
                ejecutar_integral_simple()
            elif opcion == "2":
                ejecutar_integral_doble_rectangular()
            elif opcion == "3":
                ejecutar_integral_doble_general()
            elif opcion == "4":
                print("\n¡Hasta luego!")
                sys.exit(0)
            else:
                print("\nOpción no válida. Intenta de nuevo.")
        except ErrorDeEntrada as e:
            print(f"\n[ERROR DE VALIDACIÓN]\n{e}")
        except Exception as e:
            print(f"\n[ERROR]: {e}")

if __name__ == "__main__":
    main()