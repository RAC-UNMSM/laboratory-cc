from validacion import parse

from tools.common import iterated, pack


def run(p):
    names = [b["variable"] for b in p["limites"]]
    e = parse(p["expresion"], names)
    r, steps = iterated(e, p["limites"])
    return pack(
        r,
        steps,
        [
            "Integral iterada en el orden suministrado, con signo. Cada frontera depende solo de variables exteriores. No certifica Fubini ni la geometría global del dominio."
        ],
    )
