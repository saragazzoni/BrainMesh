#!/usr/bin/env python3
"""
Controlla che le serie DTI convertite da dcm2niix siano utilizzabili.
 
Uso:
    python3 check_dti_nifti.py <cartella images/<data>> <serie1> [<serie2> ...]
 
Per ogni serie richiesta: il file 4D esiste, ha N_SLICES sezioni e tanti volumi quanti
b-values. La PA (DTI_6_dir_B700_PA) e' facoltativa: se c'e' ma e' rotta viene rinominata,
cosi' la pipeline usa la correzione delle distorsioni basata sulla T1.
Esce con codice 1 se una delle serie richieste manca o e' sbagliata.
"""
import sys
from pathlib import Path
 
import nibabel as nib
import numpy as np
 
N_SLICES = 64          # sezioni attese per le DTI di questo protocollo
 
d = Path(sys.argv[1])
series = sys.argv[2:]
ok = True
for name in series:
    img, bval = d / f"{name}.nii.gz", d / f"{name}.bval"
    if not (img.exists() and bval.exists()):
        print(f"[MANCA ] {name}")
        ok = False
        continue
    sh, nb = nib.load(img).shape, len(np.loadtxt(bval, ndmin=1))
    good = len(sh) == 4 and sh[2] == N_SLICES and sh[3] == nb
    print(f"[{'OK' if good else 'ERRATO'}{' ' * (6 - len('OK' if good else 'ERRATO'))}] {name}: {sh}, {nb} b-values")
    ok &= good
 
pa = d / "DTI_6_dir_B700_PA.nii.gz"
if pa.exists():
    sh = nib.load(pa).shape
    if len(sh) == 4 and sh[2] == N_SLICES:
        print(f"[OK    ] PA: {sh}")
    else:
        print(f"[ERRATO] PA: {sh} -> rinominata, verra' usata la correzione con la T1")
        pa.rename(pa.with_name("PA_non_valida.nii.gz"))
else:
    print("[--    ] PA assente: correzione delle distorsioni con la T1")
sys.exit(0 if ok else 1)