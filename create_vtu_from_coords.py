#!/usr/bin/env python3
"""
Legge un file di testo con le coordinate dei punti (una riga per punto: x y z o x y)
(saltando le righe che iniziano con '#') e salva una mesh .vtu contenente i punti
con celle di tipo 'vertex'.

Uso:
    python create_vtu_from_coords.py coords.txt output.vtu

Requisiti:
    pip install meshio

Nota:
    - Se le righe hanno solo x y viene aggiunta z=0.
    - Il file .vtu risultante conterrà i punti e una cella di tipo 'vertex' per ogni punto.
"""

import argparse
import sys
from typing import Tuple

import numpy as np

try:
    import meshio
except Exception:
    print("Errore: non riesco a importare 'meshio'. Installa con: pip install meshio")
    raise


def read_coords_txt(path: str, skip_first: bool = False) -> np.ndarray:
    """Legge il file di coordinate e ritorna un array (N,3).

    Il file può contenere commenti che iniziano con '#'. Ogni riga valida deve avere
    2 o 3 numeri separati da spazi o tab.
    """
    pts = []
    with open(path, "r") as f:
        for i, line in enumerate(f, start=1):
            # Salta la prima riga se richiesto (anche se non commentata)
            if skip_first and i == 1:
                continue
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) not in (2, 3):
                raise ValueError(f"Linea {i}: attesi 2 o 3 valori (x y [z]), trovato: {line!r}")
            try:
                nums = [float(p) for p in parts]
            except ValueError:
                raise ValueError(f"Linea {i}: impossibile convertire in float: {line!r}")
            if len(nums) == 2:
                nums.append(0.0)
            pts.append(nums)

    if not pts:
        raise RuntimeError(f"Nessun punto letto dal file: {path}")

    return np.asarray(pts, dtype=float)


def write_vtu_from_points(points: np.ndarray, out_path: str) -> None:
    """Crea una mesh .vtu con i punti forniti. Usa celle di tipo 'vertex'."""
    # Forma controllata
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("'points' deve essere un array di forma (N,3)")

    n = points.shape[0]
    # meshio accetta una lista di cell tuples
    # ogni vertex è rappresentato come una cella con un singolo indice
    vertex_cells = np.arange(n, dtype=int).reshape(-1, 1)
    mesh = meshio.Mesh(points=points, cells=[("vertex", vertex_cells)])

    meshio.write(out_path, mesh)


def convert_file(in_txt: str, out_vtu: str) -> Tuple[int, int]:
    pts = read_coords_txt(in_txt)
    write_vtu_from_points(pts, out_vtu)
    return pts.shape[0], pts.shape[1]


def export_vtu_to_txt(vtu_path: str, out_txt: str) -> int:
    """Legge un file .vtu e salva le coordinate in formato testo. Ritorna numero di punti."""
    mesh = meshio.read(vtu_path)
    pts = mesh.points
    if pts is None or pts.size == 0:
        raise RuntimeError(f"Nessun punto trovato nel file: {vtu_path}")

    # Assicuriamoci 3 colonne
    if pts.shape[1] == 2:
        pts = np.hstack((pts, np.zeros((pts.shape[0], 1))))

    with open(out_txt, "w") as f:
        f.write("# x y z\n")
        for p in pts:
            f.write(f"{p[0]:.9f} {p[1]:.9f} {p[2]:.9f}\n")

    return pts.shape[0]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Converti tra file di coordinate (testo) e file .vtu contenenti punti."
    )
    parser.add_argument("input", help="File di input (.txt o .vtu)")
    parser.add_argument("output", help="File di output (.vtu o .txt)")
    parser.add_argument(
        "--skip-first-line",
        action="store_true",
        help="Se impostato, salta la prima riga del file di testo di input (utile per header).",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "txt-to-vtu", "vtu-to-txt"],
        default="auto",
        help="Modalità di conversione: 'auto' (default) decide in base alle estensioni",
    )
    args = parser.parse_args(argv)

    # Determina la modalità se auto
    mode = args.mode
    if mode == "auto":
        inp_ext = args.input.lower().rsplit(".", 1)[-1] if "." in args.input else ""
        out_ext = args.output.lower().rsplit(".", 1)[-1] if "." in args.output else ""
        if inp_ext in ("vtu", "vtk") and out_ext in ("txt", "dat"):
            mode = "vtu-to-txt"
        elif inp_ext in ("txt", "dat") and out_ext in ("vtu", "vtk"):
            mode = "txt-to-vtu"
        else:
            parser.error(
                "Impossibile determinare la conversione in modalità 'auto'. Specifica --mode o usa estensioni compatibili (.txt <-> .vtu)."
            )

    try:
        if mode == "txt-to-vtu":
            pts = read_coords_txt(args.input, skip_first=args.skip_first_line)
            n_points = pts.shape[0]
            write_vtu_from_points(pts, args.output)
            print(f"Creato: {args.output} con {n_points} punti")
        elif mode == "vtu-to-txt":
            n_points = export_vtu_to_txt(args.input, args.output)
            print(f"Esportato: {args.output} con {n_points} punti")
        else:
            raise RuntimeError("Modalità sconosciuta: {mode}")
    except Exception as e:
        print(f"Errore durante la conversione: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
