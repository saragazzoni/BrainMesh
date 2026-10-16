#!/usr/bin/python3
"""
Concatena un numero qualsiasi di serie DWI (stesso comportamento di concatenate_dwis.py,
che accetta esattamente tre serie).
 
Uso:
    python3 concatenate_dwis_n.py -i <prefisso1> <prefisso2> [...] -o <prefisso output>
 
Ogni prefisso e' il percorso della serie senza estensione: devono esistere
<prefisso>.nii.gz, <prefisso>.bval e <prefisso>.bvec.
 
Come l'originale: i dati vengono letti con get_fdata() (quindi con i fattori di scala
della singola serie applicati), i b-values salvati con una cifra decimale (%.1f, quindi
ad es. 0.001 -> 0.0) e i b-vectors con sei; header e affine sono quelli della prima serie.
In piu' controlla che le serie abbiano la stessa griglia spaziale.
"""
import argparse
 
import nibabel as nib
import numpy as np
 
parser = argparse.ArgumentParser(description="Concatenates diffusion-weighted image series.")
parser.add_argument("-i", "--inputs", nargs="+", required=True,
                    help="Prefissi delle serie (senza .nii.gz/.bval/.bvec), nell'ordine voluto")
parser.add_argument("-o", "--output", required=True, help="Prefisso dei file di output")
args = parser.parse_args()
 
dwis_list, bvals_list, bvecs_list = [], [], []
first = None
for k, prefix in enumerate(args.inputs, 1):
    print(f"Open data{k} from disk... ({prefix})")
    img = nib.load(prefix + ".nii.gz")
    data = img.get_fdata()
    bvals = np.loadtxt(prefix + ".bval")
    bvecs = np.loadtxt(prefix + ".bvec")
 
    if data.ndim != 4:
        raise SystemExit(f"ERRORE: {prefix}.nii.gz non e' 4D (forma {data.shape})")
    if not (data.shape[3] == bvals.shape[0] == bvecs.shape[1]):
        raise SystemExit(f"ERRORE: {prefix}: {data.shape[3]} volumi, {bvals.shape[0]} b-values, "
                         f"{bvecs.shape[1]} b-vectors")
    if first is None:
        first = img
    elif data.shape[:3] != first.shape[:3] or not np.allclose(img.affine, first.affine, atol=1e-3):
        raise SystemExit(f"ERRORE: {prefix} ha una griglia spaziale diversa dalla prima serie")
 
    dwis_list.append(data)
    bvals_list.append(bvals)
    bvecs_list.append(bvecs)
 
print("Concatenate images and bval/bvec files.")
bvals = np.hstack([b[np.newaxis, :] for b in bvals_list])
bvecs = np.hstack(bvecs_list)
dwis = np.concatenate(dwis_list, axis=3)
 
print("Save bval and bvec file")
np.savetxt("%s.bval" % args.output, bvals, fmt="%.1f")
np.savetxt("%s.bvec" % args.output, bvecs, fmt="%.6f")
 
print("Save dwis file")
hdr = nib.Nifti1Header()
hdr.set_data_shape(dwis.shape)
hdr.set_sform(first.get_sform())
hdr.set_qform(first.get_qform())
nib.save(nib.Nifti1Image(dwis, first.affine, header=hdr), "%s.nii.gz" % args.output)
print(f"Concatenated {len(args.inputs)} series: {dwis.shape[3]} volumes in total")