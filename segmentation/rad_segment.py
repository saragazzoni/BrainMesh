#!/usr/bin/env python3
"""
Batch Raidionics: da cartelle DICOM a STL (tumore + brain), senza passare da Slicer.

Per ogni paziente:
  1. cerca tra le serie DICOM la T1 con contrasto (dalla "Series Description" nell'intestazione)
  2. la converte in NIfTI
  3. lancia Raidionics due volte (tumore e brain)
  4. applica la soglia alle mappe di probabilita' e salva gli STL

Uso:
    python batch_raidionics.py --check      # mostra la serie scelta per ogni paziente, senza fare nulla
    python batch_raidionics.py --list       # elenca tutte le serie DICOM di ogni paziente
    python batch_raidionics.py P01          # elabora solo il paziente P01 (per provare)
    python batch_raidionics.py              # elabora tutti i pazienti
(--check e --list accettano anche nomi di pazienti, es. --list P01)

Requisiti: Docker Desktop aperto; pip install numpy nibabel scikit-image SimpleITK

NOTA: lo script usa la stessa cartella di lavoro del plugin
(~/.raidionics-slicer/resources). Non usare Raidionics in Slicer mentre gira.
"""

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import SimpleITK as sitk
from skimage import measure

sitk.ProcessObject.SetGlobalWarningDisplay(False)   # niente avvisi per i file non DICOM

# ----------------------------------------------------------------------------
# PARAMETRI DA IMPOSTARE
# ----------------------------------------------------------------------------
PATIENTS_DIR = Path("/Users/saragazzoni/Desktop/Data/Pazienti")    # una sottocartella per paziente
OUTPUT_DIR = Path("/Users/saragazzoni/Desktop/Data/raidionics_out")  # qui finiscono mappe e STL

# Come riconoscere la T1 con contrasto dalla Series Description (maiuscole/minuscole indifferenti,
# * = qualunque testo). Si usa il primo pattern che trova una serie; se ne trova piu' di una
# lo script si ferma su quel paziente e chiede di indicarla nel file delle eccezioni.
SERIES_PATTERNS = [
    "*t1*3d*mdc*",
    "*t1*mdc*",
]

# File delle eccezioni (facoltativo): una riga per paziente, "paziente,serie".
# "serie" puo' essere il numero di serie (es. 901), la descrizione esatta
# oppure la cartella della serie relativa alla cartella del paziente.
OVERRIDES_CSV = PATIENTS_DIR / "eccezioni.csv"

THRESHOLD = 0.5                # soglia sulla mappa di probabilita'
STL_COORDS = "LPS"             # "LPS" (default di Slicer) oppure "RAS"

STRUCTURES = {                 # nome usato nei file di output -> modello Raidionics
    "tumor": "MRI_TumorCore",
    "brain": "MRI_Brain",
}

RESOURCES = Path.home() / ".raidionics-slicer" / "resources"
DOCKER = "/usr/local/bin/docker"
IMAGE = "dbouget/raidionics-rads:v1.3-py39-cpu"
# ----------------------------------------------------------------------------

CONFIG_INI = """[Default]
task = neuro_diagnosis
caller =

[System]
gpu_id = -1
input_folder = /workspace/resources/data
output_folder = /workspace/resources/output
model_folder = /workspace/resources/models
pipeline_filename = /workspace/resources/data/rads_pipeline.json

[Runtime]
reconstruction_method = probabilities
reconstruction_order = resample_first
use_stripped_data = False
use_registered_data = False

[Neuro]

"""


def scan_series(patient_dir):
    """Elenca tutte le serie DICOM dentro la cartella del paziente (anche nelle sottocartelle)."""
    series = []
    for root, _, files in os.walk(patient_dir):
        if not any(not f.startswith(".") for f in files):
            continue
        for uid in sitk.ImageSeriesReader.GetGDCMSeriesIDs(root):
            filenames = list(sitk.ImageSeriesReader.GetGDCMSeriesFileNames(root, uid))
            if not filenames:
                continue
            reader = sitk.ImageFileReader()
            reader.SetFileName(filenames[0])
            try:
                reader.ReadImageInformation()
            except RuntimeError:
                continue

            def tag(key):
                return reader.GetMetaData(key).strip() if reader.HasMetaDataKey(key) else ""

            series.append({
                "description": tag("0008|103e"),
                "number": tag("0020|0011"),
                "folder": os.path.relpath(root, patient_dir),
                "files": filenames,
            })
    return sorted(series, key=lambda s: (s["folder"], s["number"].zfill(8), s["description"]))


def describe(s):
    return f"n. {s['number'] or '?':>5}  '{s['description']}'  ({len(s['files'])} file, cartella: {s['folder']})"


def load_overrides():
    """Legge il file delle eccezioni: paziente,serie (separatore virgola o punto e virgola)."""
    overrides = {}
    if OVERRIDES_CSV.exists():
        for line in OVERRIDES_CSV.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"[;,]", line, maxsplit=1)
            if len(parts) == 2 and parts[0].strip().lower() not in ("paziente", "patient"):
                overrides[parts[0].strip()] = parts[1].strip().strip('"')
    return overrides


def choose_series(name, series, overrides):
    """Sceglie la serie T1 con contrasto; errore se la scelta non e' univoca."""
    if not series:
        raise RuntimeError("nessuna serie DICOM trovata")

    if name in overrides:
        wanted = overrides[name]
        found = [
            s for s in series
            if wanted == s["number"]
            or wanted.lower() == s["description"].lower()
            or os.path.normpath(wanted) == os.path.normpath(s["folder"])
        ]
        if len(found) != 1:
            raise RuntimeError(f"eccezione '{wanted}': corrisponde a {len(found)} serie invece di 1")
        return found[0], "eccezioni.csv"

    for pattern in SERIES_PATTERNS:
        found = [s for s in series if fnmatch.fnmatchcase(s["description"].lower(), pattern.lower())]
        if len(found) == 1:
            return found[0], f"pattern {pattern}"
        if len(found) > 1:
            raise RuntimeError(
                f"{len(found)} serie corrispondono a '{pattern}': "
                + "; ".join(f"n. {s['number']} '{s['description']}'" for s in found)
            )
    raise RuntimeError("nessuna serie corrisponde ai pattern")


def dicom_to_nifti(s, nifti_file):
    """Converte la serie DICOM in NIfTI mantenendo posizione e orientamento."""
    if len(s["files"]) == 1:
        image = sitk.ReadImage(s["files"][0])
    else:
        reader = sitk.ImageSeriesReader()
        reader.SetFileNames(s["files"])
        image = reader.Execute()
    if image.GetNumberOfComponentsPerPixel() != 1 or image.GetDimension() != 3:
        raise RuntimeError("la serie non e' un volume 3D scalare")
    size, spacing = image.GetSize(), image.GetSpacing()
    if min(size) < 2:
        raise RuntimeError(f"la serie non e' un volume 3D (dimensioni {size})")
    sitk.WriteImage(image, str(nifti_file))
    print(f"   volume {size[0]}x{size[1]}x{size[2]}, voxel "
          f"{spacing[0]:.2f}x{spacing[1]:.2f}x{spacing[2]:.2f} mm")


def prepare_input(t1gd, model):
    """Ricrea data/ e output/ come li prepara il plugin per un singolo caso."""
    data_dir = RESOURCES / "data"
    out_dir = RESOURCES / "output"
    for d in (data_dir / "T0", out_dir):
        if d.exists():
            shutil.rmtree(d)
    (data_dir / "T0").mkdir(parents=True)
    out_dir.mkdir(parents=True)

    shutil.copyfile(t1gd, data_dir / "T0" / "input_t1gd.nii.gz")

    pipeline = {
        "1": {
            "task": "Model selection",
            "model": model,
            "timestamp": 0,
            "format": "probabilities",
            "description": f"Identifying the best segmentation model for existing inputs for {model}",
        }
    }
    (data_dir / "rads_pipeline.json").write_text(json.dumps(pipeline, indent=4))
    (data_dir / "rads_config.ini").write_text(CONFIG_INI)


def run_docker(log_file):
    """Stesso comando lanciato dal plugin; l'output del container va nel file di log."""
    cmd = [
        DOCKER, "run", "-t", "--user", str(os.getuid()),
        "-v", f"{RESOURCES}:/workspace/resources",
        IMAGE,
        "-c", "/workspace/resources/data/rads_config.ini",
        "-v", "debug",
    ]
    with open(log_file, "w") as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        raise RuntimeError(f"docker ha restituito il codice {result.returncode} (vedi {log_file})")


def collect_output(model, destination):
    """Copia la mappa prodotta dal container nella cartella del paziente."""
    matches = sorted((RESOURCES / "output" / "T0").glob(f"*_{model}.nii.gz"))
    if len(matches) != 1:
        raise RuntimeError(f"attesa 1 mappa per {model}, trovate {len(matches)}")
    shutil.copyfile(matches[0], destination)


def write_binary_stl(path, vertices, faces):
    tri = vertices[faces].astype(np.float32)                 # (n, 3, 3)
    normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)
    record = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])
    data = np.zeros(len(tri), dtype=record)
    data["n"] = normals
    data["v"] = tri
    with open(path, "wb") as f:
        f.write(b"batch_raidionics".ljust(80, b" "))
        f.write(np.uint32(len(tri)).tobytes())
        f.write(data.tobytes())


def prob_to_stl(prob_file, stl_file):
    """Isosuperficie della mappa di probabilita' a livello THRESHOLD, in mm."""
    img = nib.load(str(prob_file))
    prob = np.asarray(img.get_fdata(), dtype=np.float32)
    lo, hi = float(prob.min()), float(prob.max())
    info = f"range [{lo:.3g}, {hi:.3g}]"
    if hi > 1.0:
        print(f"      ATTENZIONE: valori > 1, la mappa non e' in scala 0-1 ({info}): controlla THRESHOLD")
    if hi <= THRESHOLD:
        raise RuntimeError(f"nessun voxel sopra la soglia {THRESHOLD} ({info})")

    # bordo di zeri: la superficie resta chiusa anche se la struttura tocca il bordo del volume
    padded = np.pad(prob, 1, mode="constant", constant_values=0.0)
    verts, faces, _, _ = measure.marching_cubes(padded, level=THRESHOLD)
    verts -= 1.0                                              # toglie lo spostamento del bordo

    affine = img.affine                                       # voxel -> mm, sistema RAS
    verts = verts @ affine[:3, :3].T + affine[:3, 3]
    if np.linalg.det(affine[:3, :3]) > 0:                     # mantiene le normali verso l'esterno
        faces = faces[:, ::-1]
    if STL_COORDS.upper() == "LPS":
        verts[:, :2] *= -1.0

    write_binary_stl(stl_file, verts, faces)
    voxel_volume = abs(np.linalg.det(affine[:3, :3]))
    volume_ml = float((prob >= THRESHOLD).sum()) * voxel_volume / 1000.0
    print(f"      {stl_file.name}: {len(faces)} triangoli, volume {volume_ml:.1f} mL, {info}")


def process_patient(patient_dir, overrides):
    name = patient_dir.name
    out_dir = OUTPUT_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)

    t1gd = out_dir / "t1gd.nii.gz"
    if t1gd.exists():
        print("   T1gd: NIfTI gia' presente, salto la conversione")
    else:
        chosen, why = choose_series(name, scan_series(patient_dir), overrides)
        print(f"   T1gd: {describe(chosen)}  [{why}]")
        dicom_to_nifti(chosen, t1gd)
        (out_dir / "t1gd_serie.txt").write_text(f"{describe(chosen)}\nscelta: {why}\n")

    for label, model in STRUCTURES.items():
        prob_file = out_dir / f"{label}_prob.nii.gz"
        if prob_file.exists():
            print(f"   {label}: mappa gia' presente, salto la segmentazione")
        else:
            print(f"   {label}: segmentazione in corso...")
            prepare_input(t1gd, model)
            run_docker(out_dir / f"{label}_docker.log")
            collect_output(model, prob_file)
        stl_dir = out_dir / "stl"
        stl_dir.mkdir(exist_ok=True)
        prob_to_stl(prob_file, stl_dir / f"{label}.stl")


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    list_all = "--list" in args
    selected = [a for a in args if not a.startswith("--")]

    patients = sorted(p for p in PATIENTS_DIR.iterdir() if p.is_dir())
    if selected:
        patients = [p for p in patients if p.name in selected]
    if not patients:
        sys.exit(f"Nessun paziente trovato in {PATIENTS_DIR}")
    overrides = load_overrides()

    if check_only or list_all:
        problems = []
        for p in patients:
            series = scan_series(p)
            try:
                chosen, why = choose_series(p.name, series, overrides)
                print(f"{p.name}: {describe(chosen)}  [{why}]")
            except RuntimeError as err:
                chosen = None
                problems.append(p.name)
                print(f"{p.name}: PROBLEMA - {err}")
            if list_all or chosen is None:
                for s in series:
                    print(f"      {'->' if s is chosen else '  '} {describe(s)}")
        print(f"\n{len(patients) - len(problems)} pazienti a posto, {len(problems)} da sistemare.")
        if problems:
            print("Da sistemare:", ", ".join(problems))
            print(f"Per questi, aggiungi una riga 'paziente,numero di serie' in {OVERRIDES_CSV}")
        return

    failed = []
    for i, p in enumerate(patients, 1):
        print(f"[{i}/{len(patients)}] {p.name}")
        try:
            process_patient(p, overrides)
        except Exception as err:  # un caso fallito non blocca gli altri
            print(f"   ERRORE: {err}")
            failed.append(p.name)

    print(f"\nFinito: {len(patients) - len(failed)} riusciti, {len(failed)} falliti.")
    if failed:
        print("Falliti:", ", ".join(failed))


if __name__ == "__main__":
    main()