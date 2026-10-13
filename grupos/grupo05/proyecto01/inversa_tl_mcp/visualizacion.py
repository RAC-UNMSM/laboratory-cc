"""PNG en memoria para transformaciones de R2 y R3, sin almacenamiento externo."""
from io import BytesIO
from threading import Lock

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from validacion import ErrorDeEntrada

_LOCK = Lock()


def generar_grafico_png(A, vector):
    if A.shape not in ((2,2),(3,3)):
        raise ErrorDeEntrada("La visualización geométrica admite matrices 2x2 o 3x3.")
    a, v = np.array(A,dtype=float), np.array(vector,dtype=float).reshape(-1)
    if not np.isfinite(a).all() or not np.isfinite(v).all() or max(np.max(np.abs(a)),np.max(np.abs(v))) > 1000:
        raise ErrorDeEntrada("Para graficar, usa valores finitos con magnitud <= 1000.")
    with _LOCK, plt.rc_context({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}):
        fig = plt.figure(figsize=(12,5),layout="constrained")
        try:
            if A.rows == 2:
                axs = fig.subplots(1,2)
                for ax,mat,titulo in zip(axs,[np.eye(2),a],["Plano original", "Imagen bajo T"]):
                    extremos = []
                    for k in range(-3,4):
                        for linea in (np.array([[-3,k],[3,k]]).T,np.array([[k,-3],[k,3]]).T):
                            puntos = mat@linea
                            ax.plot(*puntos,color="#cad5e0",linewidth=.7)
                            extremos.extend(puntos.T)
                    for e,color,nombre in zip([np.array([1,0]),np.array([0,1]),v],["#2563eb","#0d9488","#d97706"],["e1","e2","v"]):
                        imagen = mat@e
                        etiqueta = nombre if titulo == "Plano original" else f"T({nombre})"
                        ax.quiver(0,0,*imagen,angles="xy",scale_units="xy",scale=1,color=color,label=etiqueta)
                        extremos.append(imagen)
                    limite = max(1.5,float(np.max(np.abs(extremos)))*1.12)
                    ax.set(xlim=(-limite,limite),ylim=(-limite,limite),xlabel="x1",ylabel="x2",title=titulo)
                    ax.axhline(0,color="#64748b",linewidth=.7); ax.axvline(0,color="#64748b",linewidth=.7)
                    ax.set_aspect("equal"); ax.legend()
            else:
                for pos,mat,titulo in [(121,np.eye(3),"Vectores originales"),(122,a,"Imagen bajo T")]:
                    ax = fig.add_subplot(pos,projection="3d")
                    elementos = [mat[:,j] for j in range(3)] + [mat@v]
                    for e,color,nombre in zip(elementos,["#2563eb","#0d9488","#a855f7","#d97706"],["e1","e2","e3","v"]):
                        etiqueta = nombre if pos == 121 else f"T({nombre})"
                        ax.quiver(0,0,0,*e,color=color,label=etiqueta)
                    limite=max(1.5,float(np.max(np.abs(elementos)))*1.15)
                    ax.set(xlim=(-limite,limite),ylim=(-limite,limite),zlim=(-limite,limite),xlabel="x1",ylabel="x2",zlabel="x3",title=titulo)
                    ax.set_box_aspect((1,1,1)); ax.legend()
            imagen = A*vector
            recorrido = f"v = {list(vector)}  ->  T(v) = {list(imagen)}"
            if A.det() != 0:
                recorrido += f"  ->  T^(-1)(T(v)) = {list(A.inv()*imagen)}"
            else:
                recorrido += "  |  Matriz singular: sin inversa global"
            fig.suptitle("Transformación lineal: base, vector y geometría\n" + recorrido,fontsize=11)
            salida=BytesIO(); fig.savefig(salida,format="png",dpi=140)
            return salida.getvalue()
        finally:
            plt.close(fig)
