#!/usr/bin/env python3
"""
Semplice script per leggere una mesh .vtu e salvare le coordinate dei punti
in un file di testo (una riga per punto: x y z).

Uso:
    python export_vtu_points.py input.vtu output.txt

Requisiti:
    pip install meshio

Autore: generato automaticamente
"""

import argparse
import sys

try:
    import meshio
except Exception as e:
    print("Errore: non riesco a importare 'meshio'. Installa con: pip install meshio")
    raise


def export_points(vtu_path: str, out_path: str, fmt: str = "auto"):
    """Legge la mesh .vtu e salva le coordinate dei punti in out_path.

    Ogni riga del file di output contiene le coordinate di un punto separate da spazi.
    Se la mesh è 2D, vengono comunque stampate 3 colonne (z=0 se mancante).
    """
    mesh = meshio.read(vtu_path)

    if mesh.points is None or mesh.points.size == 0:
        raise RuntimeError(f"Nessun punto trovato nel file: {vtu_path}")

    pts = mesh.points

    # Assicuriamoci che abbiano 3 colonne; se 2 -> aggiungiamo z=0
    if pts.shape[1] == 2:
        import numpy as _np
        pts = _np.hstack((pts, _np.zeros((pts.shape[0], 1))))

    # Scriviamo il file di testo
    with open(out_path, "w") as f:
        f.write("# x y z\n")
        for p in pts:           
            # Usa formato a virgola fissa per evitare la notazione esponenziale (es. 1.23e+02)
            f.write(f"{p[0]:.9f} {p[1]:.9f} {p[2]:.9f}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Esporta le coordinate dei punti da un file .vtu in un file di testo")
    parser.add_argument("input_vtu", help="Percorso al file .vtu di input")
    parser.add_argument("output_txt", help="Percorso del file di testo di output")
    args = parser.parse_args(argv)

    try:
        export_points(args.input_vtu, args.output_txt)
    except Exception as e:
        print(f"Errore durante l'esportazione: {e}")
        sys.exit(1)

    print(f"Coordinate esportate in: {args.output_txt}")


if __name__ == "__main__":
    main()
