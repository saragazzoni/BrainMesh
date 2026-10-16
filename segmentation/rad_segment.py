#!/usr/bin/env python3
"""
Batch Raidionics: da cartelle DICOM a STL, senza passare da Slicer.

PRE-OP (come prima)
  Per ogni paziente in PATIENTS_DIR:
    1. cerca la T1 con contrasto (dalla "Series Description" nell'intestazione DICOM)
    2. la converte in NIfTI
    3. lancia Raidionics due volte (tumore e brain)
    4. applica la soglia alle mappe di probabilita' e salva gli STL
  Output in OUTPUT_DIR/<paziente>/

POST-OP (opzione --postop)
  Per ogni paziente che ha la sottocartella PATIENTS_DIR/<paziente>/postop (le altre sono saltate):
    1. controlla che dentro ci sia un solo esame
    2. cerca T1 con contrasto (obbligatoria) e, se ci sono, T1 senza contrasto, FLAIR e T2
    3. le converte in NIfTI
    4. lancia Raidionics per il brain (solo T1 con contrasto, come nel pre-op) e per la cavita'
       (con tutte le sequenze trovate: Raidionics sceglie da solo la variante del modello)
    5. salva mappe di probabilita', maschere binarie e STL
  Output in OUTPUT_DIR/<paziente>/postop/

Uso:
    python rad_segment.py --check            # serie scelte per ogni paziente, senza fare nulla
    python rad_segment.py --list             # tutte le serie DICOM di ogni paziente
    python rad_segment.py P01                # elabora solo P01 (per provare)
    python rad_segment.py                    # elabora tutti i pazienti
    python rad_segment.py --postop --check   # come sopra, per gli esami post-op
    python rad_segment.py --postop P01
    python rad_segment.py --postop
(--check e --list accettano anche nomi di pazienti, es. --postop --list P01)

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

# ---- POST-OP ----------------------------------------------------------------
# Nome della sottocartella dell'esame post-op dentro la cartella di ogni paziente
# (PATIENTS_DIR/<paziente>/postop). Nel pre-op questa sottocartella viene ignorata.
POSTOP_FOLDER = "postop"

# Sequenze post-op: nome -> (file di input per Raidionics, pattern, pattern da escludere, obbligatoria)
# I nomi dei file di input sono quelli che usa il plugin: Raidionics riconosce la sequenza dal nome.
# Per una sequenza facoltativa ambigua (piu' serie corrispondenti) lo script la salta e lo segnala.
# Togli una riga per non usare quella sequenza (meno sequenze = meno registrazioni = piu' veloce).
POSTOP_SEQUENCES = {
    "t1gd":  ("input_t1gd.nii.gz",  ["*t1*3d*mdc*", "*t1*mdc*"], [], True),
    "t1w":   ("input_T1w.nii.gz",   ["*t1*3d*", "*t1*"], ["*mdc*", "*gd*", "*flair*"], False),
    "flair": ("input_FLAIR.nii.gz", ["*flair*"], [], False),
    "t2":    ("input_T2.nii.gz",    ["*t2*ax*", "*t2*"], ["*flair*", "*t2[*]*", "*star*", "*swi*", "*dti*", "*dwi*"], False),
}

POSTOP_STRUCTURES = {          # nome usato nei file di output -> (modello Raidionics, sequenze da passargli)
    "brain":  ("MRI_Brain",  ["t1gd"]),
    "cavity": ("MRI_Cavity", list(POSTOP_SEQUENCES)),
}

# Eccezioni post-op (facoltativo): una riga per caso, "paziente,sequenza,valore"
#   paziente,t1w,7               -> serie per numero, descrizione esatta o cartella (relativa a .../postop)
#   paziente,t2,-                -> non usare quella sequenza
POSTOP_OVERRIDES_CSV = PATIENTS_DIR / "eccezioni_postop.csv"
# ----------------------------------------------------------------------------

RESOURCES = Path.home() / ".raidionics-slicer" / "resources"
DOCKER = "/usr/local/bin/docker"
IMAGE = "dbouget/raidionics-rads:v1.3-py39-cpu"

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


def scan_series(patient_dir, exclude=()):
    """
    Elenca tutte le serie DICOM dentro la cartella del paziente (anche nelle sottocartelle),
    ignorando le sottocartelle di primo livello con i nomi in 'exclude'.
    """
    series = []
    for root, dirs, files in os.walk(patient_dir):
        if os.path.samefile(root, patient_dir):
            dirs[:] = [d for d in dirs if d not in exclude]
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
                "date": tag("0008|0020"),
                "study": tag("0020|000d"),
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


def match_override(series, wanted):
    """Serie indicate in un'eccezione: per numero, descrizione esatta o cartella."""
    return [
        s for s in series
        if wanted == s["number"]
        or wanted.lower() == s["description"].lower()
        or os.path.normpath(wanted) == os.path.normpath(s["folder"])
    ]


def match_patterns(series, patterns, excludes=()):
    """Serie corrispondenti al primo pattern che trova qualcosa (escluse quelle in 'excludes')."""
    for pattern in patterns:
        found = [
            s for s in series
            if fnmatch.fnmatchcase(s["description"].lower(), pattern.lower())
            and not any(fnmatch.fnmatchcase(s["description"].lower(), e.lower()) for e in excludes)
        ]
        if found:
            return found, pattern
    return [], None


def choose_series(name, series, overrides):
    """Sceglie la serie T1 con contrasto; errore se la scelta non e' univoca."""
    if not series:
        raise RuntimeError("nessuna serie DICOM trovata")

    if name in overrides:
        wanted = overrides[name]
        found = match_override(series, wanted)
        if len(found) != 1:
            raise RuntimeError(f"eccezione '{wanted}': corrisponde a {len(found)} serie invece di 1")
        return found[0], "eccezioni.csv"

    found, pattern = match_patterns(series, SERIES_PATTERNS)
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


def prepare_input(inputs, model):
    """
    Ricrea data/ e output/ come li prepara il plugin per un singolo caso.
    inputs: {nome del file per Raidionics (es. input_t1gd.nii.gz): file NIfTI da copiare}
    """
    data_dir = RESOURCES / "data"
    out_dir = RESOURCES / "output"
    for d in (data_dir / "T0", out_dir):
        if d.exists():
            shutil.rmtree(d)
    (data_dir / "T0").mkdir(parents=True)
    out_dir.mkdir(parents=True)

    for raidionics_name, source in inputs.items():
        shutil.copyfile(source, data_dir / "T0" / raidionics_name)

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
    """
    Copia la mappa prodotta dal container nella cartella del paziente.
    Si prende quella calcolata sulla T1 con contrasto (input_t1gd_...): con piu' sequenze in
    ingresso Raidionics salva anche le maschere del brain delle altre sequenze.
    """
    out_t0 = RESOURCES / "output" / "T0"
    matches = sorted(out_t0.glob(f"input_t1gd*_{model}.nii.gz"))
    if not matches:                                           # nomi diversi: criterio di prima
        matches = sorted(out_t0.glob(f"*_{model}.nii.gz"))
    if len(matches) != 1:
        found = sorted(p.name for p in out_t0.glob("*.nii.gz")) if out_t0.exists() else []
        raise RuntimeError(f"attesa 1 mappa per {model}, trovate {len(matches)} (file in output: {found})")
    shutil.copyfile(matches[0], destination)
    executed = RESOURCES / "output" / "executed_pipeline.json"   # quale variante del modello e' stata usata
    if executed.exists():
        shutil.copyfile(executed, destination.with_name(destination.name.replace("_prob.nii.gz", "_pipeline.json")))


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


def prob_to_stl(prob_file, stl_file, mask_file=None):
    """Isosuperficie della mappa di probabilita' a livello THRESHOLD, in mm (e, se richiesta, maschera binaria)."""
    img = nib.load(str(prob_file))
    prob = np.asarray(img.get_fdata(), dtype=np.float32)
    lo, hi = float(prob.min()), float(prob.max())
    info = f"range [{lo:.3g}, {hi:.3g}]"
    if hi > 1.0:
        print(f"      ATTENZIONE: valori > 1, la mappa non e' in scala 0-1 ({info}): controlla THRESHOLD")
    if hi <= THRESHOLD:
        raise RuntimeError(f"nessun voxel sopra la soglia {THRESHOLD} ({info})")

    if mask_file is not None:
        mask = nib.Nifti1Image((prob >= THRESHOLD).astype(np.uint8), img.affine, img.header)
        mask.set_data_dtype(np.uint8)
        nib.save(mask, str(mask_file))

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
        chosen, why = choose_series(name, scan_series(patient_dir, exclude=(POSTOP_FOLDER,)), overrides)
        print(f"   T1gd: {describe(chosen)}  [{why}]")
        dicom_to_nifti(chosen, t1gd)
        (out_dir / "t1gd_serie.txt").write_text(f"{describe(chosen)}\nscelta: {why}\n")

    for label, model in STRUCTURES.items():
        prob_file = out_dir / f"{label}_prob.nii.gz"
        if prob_file.exists():
            print(f"   {label}: mappa gia' presente, salto la segmentazione")
        else:
            print(f"   {label}: segmentazione in corso...")
            prepare_input({"input_t1gd.nii.gz": t1gd}, model)
            run_docker(out_dir / f"{label}_docker.log")
            collect_output(model, prob_file)
        stl_dir = out_dir / "stl"
        stl_dir.mkdir(exist_ok=True)
        prob_to_stl(prob_file, stl_dir / f"{label}.stl")


# ============================================================================
# POST-OP
# ============================================================================

def load_postop_overrides():
    """Legge eccezioni_postop.csv: paziente,sequenza,valore -> {paziente: {sequenza: valore}}."""
    overrides = {}
    if POSTOP_OVERRIDES_CSV.exists():
        for n, line in enumerate(POSTOP_OVERRIDES_CSV.read_text(encoding="utf-8-sig").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip().strip('"') for p in re.split(r"[;,]", line, maxsplit=2)]
            if parts[0].lower() in ("paziente", "patient"):
                continue
            if len(parts) != 3:
                sys.exit(f"{POSTOP_OVERRIDES_CSV}, riga {n}: attese 3 colonne (paziente,sequenza,valore)")
            seq = parts[1].lower()
            if seq not in POSTOP_SEQUENCES:
                sys.exit(f"{POSTOP_OVERRIDES_CSV}, riga {n}: '{parts[1]}' non e' una sequenza "
                         f"({', '.join(POSTOP_SEQUENCES)})")
            overrides.setdefault(parts[0], {})[seq] = parts[2]
    return overrides


def check_single_exam(series):
    """Nella cartella postop deve esserci un solo esame (Study Instance UID DICOM)."""
    if not series:
        raise RuntimeError("nessuna serie DICOM trovata")
    studies = {}
    for s in series:
        studies.setdefault(s["study"], set()).add(s["date"] or "?")
    if len(studies) > 1:
        dates = ", ".join(sorted(d for ds in studies.values() for d in ds))
        raise RuntimeError(f"la cartella {POSTOP_FOLDER} contiene {len(studies)} esami diversi (date: {dates})")
    return next(iter(studies.values())).pop()


def choose_postop_series(series, overrides):
    """
    Sceglie una serie per ogni sequenza post-op.
    Restituisce {sequenza: (serie o None, motivo)}; errore solo se manca o e' ambigua la T1 con contrasto.
    """
    chosen = {}
    for seq, (_, patterns, excludes, required) in POSTOP_SEQUENCES.items():
        if seq in overrides:
            wanted = overrides[seq]
            if wanted == "-":
                chosen[seq] = (None, "esclusa in eccezioni_postop.csv")
                continue
            found = match_override(series, wanted)
            if len(found) != 1:
                raise RuntimeError(f"eccezione {seq} '{wanted}': corrisponde a {len(found)} serie invece di 1")
            chosen[seq] = (found[0], "eccezioni_postop.csv")
            continue

        found, pattern = match_patterns(series, patterns, excludes)
        if len(found) == 1:
            chosen[seq] = (found[0], f"pattern {pattern}")
        elif len(found) > 1:
            msg = (f"{len(found)} serie corrispondono a '{pattern}': "
                   + "; ".join(f"n. {s['number']} '{s['description']}'" for s in found))
            if required:
                raise RuntimeError(f"{seq}: {msg}")
            chosen[seq] = (None, f"SALTATA, ambigua ({msg})")
        else:
            if required:
                raise RuntimeError(f"{seq}: nessuna serie corrisponde ai pattern")
            chosen[seq] = (None, "non trovata")
    # la stessa serie non puo' essere usata per due sequenze diverse
    used = {}
    for seq, (s, _) in chosen.items():
        if s is not None:
            key = (s["folder"], s["number"], s["description"])
            if key in used:
                raise RuntimeError(f"la stessa serie e' stata scelta per {used[key]} e {seq}: {describe(s)}")
            used[key] = seq
    return chosen


def process_postop_patient(patient_dir, overrides):
    name = patient_dir.name
    out_dir = OUTPUT_DIR / name / "postop"
    out_dir.mkdir(parents=True, exist_ok=True)

    niftis = {seq: out_dir / f"{seq}.nii.gz" for seq in POSTOP_SEQUENCES}
    info_file = out_dir / "serie_postop.txt"
    if niftis["t1gd"].exists() and info_file.exists():
        print("   NIfTI gia' presenti, salto la conversione (cancella la cartella postop per rifarla)")
    else:
        series = scan_series(patient_dir / POSTOP_FOLDER)
        date = check_single_exam(series)
        chosen = choose_postop_series(series, overrides)
        lines = [f"esame del {date}"]
        print(f"   {lines[0]}")
        for seq, (s, why) in chosen.items():
            line = f"{seq:>6}: {describe(s) if s else '-'}  [{why}]"
            print(f"   {line}")
            lines.append(line)
            if s is not None:
                dicom_to_nifti(s, niftis[seq])
        info_file.write_text("\n".join(lines) + "\n")

    available = {seq: f for seq, f in niftis.items() if f.exists()}
    for label, (model, sequences) in POSTOP_STRUCTURES.items():
        prob_file = out_dir / f"{label}_prob.nii.gz"
        if prob_file.exists():
            print(f"   {label}: mappa gia' presente, salto la segmentazione")
        else:
            inputs = {POSTOP_SEQUENCES[seq][0]: available[seq] for seq in sequences if seq in available}
            print(f"   {label}: segmentazione in corso con {', '.join(s for s in sequences if s in available)}...")
            prepare_input(inputs, model)
            run_docker(out_dir / f"{label}_docker.log")
            collect_output(model, prob_file)
        stl_dir = out_dir / "stl"
        stl_dir.mkdir(exist_ok=True)
        prob_to_stl(prob_file, stl_dir / f"{label}.stl", out_dir / f"{label}_mask.nii.gz")


def check_postop(patients, list_all):
    overrides = load_postop_overrides()
    problems = []
    for p in patients:
        series = scan_series(p / POSTOP_FOLDER)
        chosen = {}
        try:
            date = check_single_exam(series)
            chosen = choose_postop_series(series, overrides.get(p.name, {}))
            print(f"{p.name}: esame del {date}")
            for seq, (s, why) in chosen.items():
                print(f"      {seq:>6}: {describe(s) if s else '-'}  [{why}]")
            ok = True
        except RuntimeError as err:
            ok = False
            problems.append(p.name)
            print(f"{p.name}: PROBLEMA - {err}")
        if list_all or not ok:
            picked = {id(s) for s, _ in chosen.values() if s is not None}
            for s in series:
                print(f"         {'->' if id(s) in picked else '  '} {describe(s)}")
    print(f"\n{len(patients) - len(problems)} pazienti a posto, {len(problems)} da sistemare.")
    if problems:
        print("Da sistemare:", ", ".join(problems))
        print(f"Per questi, aggiungi righe 'paziente,sequenza,serie' in {POSTOP_OVERRIDES_CSV}")


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    list_all = "--list" in args
    postop = "--postop" in args
    selected = [a for a in args if not a.startswith("--")]

    patients = sorted(p for p in PATIENTS_DIR.iterdir() if p.is_dir())
    if selected:
        patients = [p for p in patients if p.name in selected]
    if not patients:
        sys.exit(f"Nessun paziente trovato in {PATIENTS_DIR}")

    if postop:
        missing = [p.name for p in patients if not (p / POSTOP_FOLDER).is_dir()]
        patients = [p for p in patients if (p / POSTOP_FOLDER).is_dir()]
        if missing:
            print(f"Senza cartella '{POSTOP_FOLDER}' (saltati): {', '.join(missing)}\n")
        if not patients:
            sys.exit(f"Nessun paziente con la cartella '{POSTOP_FOLDER}'")

        if check_only or list_all:
            check_postop(patients, list_all)
            return

        overrides = load_postop_overrides()
        failed = []
        for i, p in enumerate(patients, 1):
            print(f"[{i}/{len(patients)}] {p.name} (post-op)")
            try:
                process_postop_patient(p, overrides.get(p.name, {}))
            except Exception as err:  # un caso fallito non blocca gli altri
                print(f"   ERRORE: {err}")
                failed.append(p.name)
        print(f"\nFinito: {len(patients) - len(failed)} riusciti, {len(failed)} falliti.")
        if failed:
            print("Falliti:", ", ".join(failed))
        return

    overrides = load_overrides()

    if check_only or list_all:
        problems = []
        for p in patients:
            series = scan_series(p, exclude=(POSTOP_FOLDER,))
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
