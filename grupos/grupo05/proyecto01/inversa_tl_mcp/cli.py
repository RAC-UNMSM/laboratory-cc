"""Demostración local y comandos de terminal sin cliente MCP."""
import argparse
import json
from pathlib import Path
import sys

from criptografia import cifrar, descifrar
from matematica import analizar, preparar_transformacion
from reporte_html import generar_reporte
from validacion import ErrorDeEntrada, matriz_validada, vector_validado
from visualizacion import generar_grafico_png


def main():
    if hasattr(sys.stdout,"reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description="Álgebra lineal y cifrado Hill - grupo 05")
    sub=parser.add_subparsers(dest="comando",required=True)
    demo=sub.add_parser("demo",help="Genera reporte HTML, PNG y resultados JSON de los ejemplos")
    demo.add_argument("--salida",default="reportes")
    inv=sub.add_parser("inversa",help="Analiza una transformación y calcula su inversa")
    inv.add_argument("--dominio",required=True); inv.add_argument("--codominio",required=True)
    entrada=inv.add_mutually_exclusive_group(required=True)
    entrada.add_argument("--regla"); entrada.add_argument("--matriz")
    inv.add_argument("--base-dominio",default=""); inv.add_argument("--base-codominio",default="")
    for nombre in ("cifrar","descifrar"):
        p=sub.add_parser(nombre,help=f"{nombre.capitalize()} un mensaje mediante Hill")
        p.add_argument("texto"); p.add_argument("--clave",required=True)
        p.add_argument("--alfabeto",default="ABCDEFGHIJKLMNOPQRSTUVWXYZ"); p.add_argument("--relleno",default="X")
        if nombre == "descifrar":
            p.add_argument("--cantidad-relleno",type=int,default=0)
    args=parser.parse_args()
    try:
        if args.comando == "demo":
            carpeta=Path(args.salida); carpeta.mkdir(parents=True,exist_ok=True)
            T=preparar_transformacion("R2","R2",regla='["2*x1+x2","x1-x2"]')
            r=analizar(T,incluir_inversa=True)
            hill=cifrar("HOLA","[[3,3],[2,5]]")
            recuperado=descifrar(hill["texto_cifrado"],"[[3,3],[2,5]]",cantidad_relleno=hill["cantidad_relleno"])
            png=generar_grafico_png(T.M,vector_validado("[1,2]",2))
            (carpeta/"transformacion.png").write_bytes(png)
            resultado={"transformacion":r,"cifrado":hill,"descifrado":recuperado}
            (carpeta/"demo.json").write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding="utf-8")
            reporte=generar_reporte(r,hill,recuperado,png,carpeta/"demostracion.html")
            print(f"Reporte: {reporte.resolve()}\nVerificación de inversa: {r['inversa']['verificacion']['ambas_identidades']}")
            print(f"Hill: HOLA -> {hill['texto_cifrado']} -> {recuperado['texto_descifrado']}")
            return
        if args.comando == "inversa":
            resultado=analizar(preparar_transformacion(args.dominio,args.codominio,args.regla or "",args.matriz or "",args.base_dominio,args.base_codominio),True)
        elif args.comando == "cifrar":
            resultado=cifrar(args.texto,args.clave,args.alfabeto,args.relleno)
        else:
            resultado=descifrar(args.texto,args.clave,args.alfabeto,args.cantidad_relleno,args.relleno)
        print(json.dumps(resultado,ensure_ascii=False,indent=2))
    except ErrorDeEntrada as exc:
        parser.exit(2,f"Error de entrada: {exc}\n")


if __name__ == "__main__":
    main()
