#!/usr/bin/env python3
"""
Proietta i tensori di diffusione dell'esame PREOP sulla T1 dell'esame POSTOP.

Passi:
  1. brain extraction della T1 postop (riorientata AXIAL come la T1 di riferimento preop)
  2. registrazione rigida T1 preop -> T1 postop (senza maschera, robusta)
  3. maschera di esclusione = (tumore preop mappato sul postop) U (cavita' postop), dilatata di --margin mm
     maschera dei blocchi = cervello postop \\ esclusione
  4. seconda registrazione lineare (rigida o affine) con la maschera dei blocchi
  5. registrazione non lineare (SVF densa) con la maschera dei blocchi: nella zona esclusa
     il campo di deformazione viene solo estrapolato dai dintorni (--fs)
  6. concatenazione di tutte le trasformazioni (B0->T1 preop, T1 preop->T1 postop) e una sola
     interpolazione + riorientazione dei tensori sulla griglia della T1 postop
  7. estrazione delle 6 componenti (Dxx, Dxy, Dyy, Dxz, Dyz, Dzz) e riempimento della cavita'
     (default: acqua libera dentro la cavita' con transizione graduale verso il tessuto al bordo;
      in alternativa bordo netto, --cavity-fill free-water, o tessuto piu' vicino, --cavity-fill nearest)

Richiede SimpleITK (es. env conda brain-mesh) e la configurazione ~/.anima/config.txt.
"""

import argparse
import configparser
import os
import shutil
import sys
from subprocess import check_call

import numpy as np
import SimpleITK as sitk

COMPONENTS = ["Dxx", "Dxy", "Dyy", "Dxz", "Dyz", "Dzz"]
DIAGONAL = {"Dxx", "Dyy", "Dzz"}

configFilePath = os.path.expanduser("~") + "/.anima/config.txt"
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = configparser.RawConfigParser()
configParser.read(configFilePath)
animaDir = configParser.get("anima-scripts", 'anima')
animaScriptsDir = configParser.get("anima-scripts", 'anima-scripts-public-root')

parser = argparse.ArgumentParser(description="Project preop diffusion tensors onto the postop T1.")
parser.add_argument('--pre-t1', required=True,
                    help="T1 preop masked (griglia dei tensori _final, es. processed/<BASENAME>_marked_masked.nrrd)")
parser.add_argument('--post-t1', required=True, help="T1 postop (nii.gz, non mascherata)")
parser.add_argument('--tensors', required=True,
                    help="Tensori: DWI_Tensors.nrrd (spazio DWI, con --b0-transforms) "
                         "oppure DWI_Tensors_final.nrrd (gia' sulla T1 preop, senza --b0-transforms)")
parser.add_argument('--b0-transforms', nargs='+', default=[],
                    help="Trasformazioni B0 -> T1 preop in ordine di stima (es. DWI_B0_rig_tr.txt DWI_B0_corr_tr.nrrd)")
parser.add_argument('--tumor-mask', default=None,
                    help="Segmentazione del tumore sul PREOP (binaria o mappa di probabilita')")
parser.add_argument('--cavity-mask', default=None,
                    help="Segmentazione della cavita' sul POSTOP (binaria o mappa di probabilita')")
parser.add_argument('--mask-threshold', type=float, default=0.5,
                    help="Soglia per binarizzare le mappe di probabilita' (default: 0.5)")
parser.add_argument('--margin', type=float, default=5.0,
                    help="Dilatazione (mm) della zona esclusa dalla registrazione (default: 5)")
parser.add_argument('--linear', choices=['rigid', 'affine'], default='rigid',
                    help="Tipo di registrazione lineare finale (default: rigid)")
parser.add_argument('--no-nonlinear', action='store_true', help="Solo registrazione lineare")
parser.add_argument('--es', type=float, default=4.0, help="Sigma regolarizzazione elastica SVF (default: 4)")
parser.add_argument('--fs', type=float, default=4.0, help="Sigma estrapolazione SVF (default: 4)")
parser.add_argument('--last-level', type=int, default=1,
                    help="Ultimo livello della piramide (0 = risoluzione piena, piu' lento; default: 1)")
parser.add_argument('--cavity-fill', choices=['blend', 'free-water', 'nearest'], default='blend',
                    help="Come riempire i tensori nella cavita': "
                         "'blend' = acqua libera dentro, tessuto fuori, transizione graduale al bordo (default); "
                         "'free-water' = tensore isotropo con diffusivita' --cavity-md, bordo netto; "
                         "'nearest' = tensore del tessuto piu' vicino (cavita' trattata come tessuto)")
parser.add_argument('--cavity-md', type=float, default=None,
                    help="Diffusivita' isotropa dell'acqua libera nella cavita' "
                         "(default: 3e-3 mm^2/s, con le unita' rilevate dai tensori)")
parser.add_argument('--cavity-sigma', type=float, default=2.0,
                    help="Solo con --cavity-fill blend: ampiezza (mm) della transizione al bordo della cavita' (default: 2)")
parser.add_argument('-o', '--out-dir', required=True, help="Cartella di output")
args = parser.parse_args()

out = os.path.abspath(args.out_dir)
os.makedirs(out, exist_ok=True)


def p(name):
    return os.path.join(out, name)


def anima(tool, *opts):
    command = [os.path.join(animaDir, tool)] + [str(o) for o in opts]
    print(" ".join(command))
    check_call(command)


def xml(path, transforms):
    opts = []
    for t in transforms:
        opts += ["-i", t]
    anima("animaTransformSerieXmlGenerator", *opts, "-o", path)


def read_binary(path, reference):
    """Legge una maschera (o mappa di probabilita'), la soglia e la porta sulla griglia di reference."""
    img = sitk.ReadImage(path, sitk.sitkFloat32)
    if img.GetDimension() == 4:
        size = list(img.GetSize())
        img = sitk.Extract(img, size[:3] + [0], [0, 0, 0, 0])
    binary = sitk.Cast(img > args.mask_threshold, sitk.sitkUInt8)
    if reference is not None:
        binary = sitk.Resample(binary, reference, sitk.Transform(), sitk.sitkNearestNeighbor, 0, sitk.sitkUInt8)
    return binary


def read_scalar(path):
    img = sitk.ReadImage(path, sitk.sitkFloat64)
    if img.GetDimension() == 4:
        size = list(img.GetSize())
        img = sitk.Extract(img, size[:3] + [0], [0, 0, 0, 0])
    return img


########################
print("1. Postop T1 brain extraction")
########################
postT1 = p("post_T1.nii.gz")
shutil.copyfile(args.post_t1, postT1)
postMasked = p("post_T1_masked.nrrd")
postBrainMask = p("post_T1_brainMask.nrrd")
check_call([sys.executable, os.path.join(animaScriptsDir, "brain_extraction", "animaAtlasBasedBrainExtraction.py"),
            "-i", postT1, "-m", postBrainMask, "-b", postMasked])
anima("animaConvertImage", "-i", postMasked, "-o", postMasked, "-R", "AXIAL")

reference = sitk.ReadImage(postMasked)
brainMask = read_binary(postBrainMask, reference)

########################
print("2. Rigid registration preop T1 -> postop T1")
########################
rigTr = p("pre_to_post_rig_tr.txt")
anima("animaPyramidalBMRegistration", "-r", postMasked, "-m", args.pre_t1, "-o", p("pre_to_post_rig.nrrd"),
      "-O", rigTr, "-p", 4, "-l", 1, "--sp", 2)

########################
print("3. Exclusion mask (tumor / cavity)")
########################
exclusion = sitk.Image(reference.GetSize(), sitk.sitkUInt8)
exclusion.CopyInformation(reference)

if args.tumor_mask:
    sitk.WriteImage(read_binary(args.tumor_mask, None), p("pre_tumor_bin.nrrd"))
    xml(p("pre_to_post_rig_tr.xml"), [rigTr])
    anima("animaApplyTransformSerie", "-i", p("pre_tumor_bin.nrrd"), "-t", p("pre_to_post_rig_tr.xml"),
          "-g", postMasked, "-o", p("pre_tumor_on_post_rig.nrrd"), "-n", "nearest")
    exclusion = exclusion | read_binary(p("pre_tumor_on_post_rig.nrrd"), reference)

cavity = None
if args.cavity_mask:
    cavity = read_binary(args.cavity_mask, reference)
    sitk.WriteImage(cavity, p("cavity_mask.nrrd"))
    exclusion = exclusion | cavity

if not args.tumor_mask and not args.cavity_mask:
    print("[AVVISO] Nessuna maschera tumore/cavita': la registrazione non lineare usa tutto il cervello")

if args.margin > 0:
    radius = [max(1, int(round(args.margin / s))) for s in reference.GetSpacing()]
    exclusion = sitk.BinaryDilate(exclusion, radius)
sitk.WriteImage(exclusion, p("exclusion_mask.nrrd"))

blockMask = brainMask & (exclusion == 0)
blockMaskPath = p("registration_mask.nrrd")
sitk.WriteImage(blockMask, blockMaskPath)

########################
print("4. Masked %s registration" % args.linear)
########################
linTr = p("pre_to_post_lin_tr.txt")
anima("animaPyramidalBMRegistration", "-r", postMasked, "-m", args.pre_t1, "-o", p("pre_to_post_lin.nrrd"),
      "-O", linTr, "-i", rigTr, "--ot", 2 if args.linear == 'affine' else 0, "-M", blockMaskPath,
      "-p", 4, "-l", 1, "--sp", 2)
preToPost = [linTr]

########################
if not args.no_nonlinear:
    print("5. Masked non-linear registration")
    nlTr = p("pre_to_post_nl_tr.nrrd")
    anima("animaDenseSVFBMRegistration", "-r", postMasked, "-m", p("pre_to_post_lin.nrrd"),
          "-o", p("pre_to_post_nl.nrrd"), "-O", nlTr, "-M", blockMaskPath,
          "--es", args.es, "--fs", args.fs, "-p", 4, "-l", args.last_level)
    preToPost.append(nlTr)

########################
print("6. Tensors -> postop T1 (single interpolation)")
########################
if not args.b0_transforms:
    print("[AVVISO] Nessuna trasformazione B0 -> T1: i tensori (gia' sulla T1 preop) vengono interpolati due volte")
fullXml = p("tensors_to_post_tr.xml")
xml(fullXml, args.b0_transforms + preToPost)
xml(p("pre_to_post_tr.xml"), preToPost)

tensorsPost = p("DWI_Tensors_postop.nrrd")
anima("animaTensorApplyTransformSerie", "-i", args.tensors, "-t", fullXml, "-g", postMasked, "-o", tensorsPost)
anima("animaDTIScalarMaps", "-i", tensorsPost, "-f", p("FA_postop.nrrd"))
anima("animaApplyTransformSerie", "-i", args.pre_t1, "-t", p("pre_to_post_tr.xml"),
      "-g", postMasked, "-o", p("pre_T1_on_post.nrrd"))

########################
print("7. Tensor components and cavity filling")
########################
anima("animaCollapseImage", "-i", tensorsPost, "-o", p("tmp_collapsed.nrrd"))
comps = {}
for k, comp in enumerate(COMPONENTS):
    anima("animaCropImage", "-i", p("tmp_collapsed.nrrd"), "-t", k, "-T", 0, "-o", p("tmp_%s.nii.gz" % comp))
    comps[comp] = read_scalar(p("tmp_%s.nii.gz" % comp))
    os.remove(p("tmp_%s.nii.gz" % comp))
os.remove(p("tmp_collapsed.nrrd"))

if cavity is not None:
    cavityArr = sitk.GetArrayFromImage(cavity).astype(bool)
    brainArr = sitk.GetArrayFromImage(brainMask).astype(bool) & ~cavityArr
    md = sum(sitk.GetArrayFromImage(comps[c]) for c in DIAGONAL) / 3.0
    medianMD = float(np.median(md[brainArr & (md > 0)]))
    isoMD = args.cavity_md
    if isoMD is None:
        # acqua libera a 37 C: 3e-3 mm^2/s; se i tensori sono in m^2/s (MD ~1e-9) si scala
        isoMD = 3e-3 if medianMD > 1e-6 else 3e-9
    arrs = {comp: sitk.GetArrayFromImage(comps[comp]) for comp in COMPONENTS}

    if args.cavity_fill in ('nearest', 'blend'):
        # ogni voxel della cavita' prende il tensore (tutte e 6 le componenti) del voxel di tessuto
        # piu' vicino: cervello, fuori dalla cavita', con tensore non nullo. Distanze in mm.
        from scipy.ndimage import distance_transform_edt
        tissue = brainArr & (md > 0)
        spacing = comps[COMPONENTS[0]].GetSpacing()[::-1]          # ordine dell'array: (z, y, x)
        dist, idx = distance_transform_edt(~tissue, sampling=spacing, return_indices=True)
        src = tuple(i[cavityArr] for i in idx)
        for comp in COMPONENTS:
            arrs[comp][cavityArr] = arrs[comp][src]

    if args.cavity_fill == 'free-water':
        print("MD mediana nel cervello: %.3g -> cavita' riempita con acqua libera, MD %.3g (%d voxel)"
              % (medianMD, isoMD, cavityArr.sum()))
        for comp in COMPONENTS:
            arrs[comp][cavityArr] = isoMD if comp in DIAGONAL else 0.0
    elif args.cavity_fill == 'nearest':
        print("MD mediana nel cervello: %.3g -> cavita' riempita con il tessuto piu' vicino (%d voxel)"
              % (medianMD, cavityArr.sum()))
    else:
        # modello a due compartimenti (tessuto + acqua libera): D = (1 - w) D_tessuto + w D_acqua,
        # con w = maschera della cavita' lisciata da una gaussiana di sigma --cavity-sigma mm.
        # Lontano dal bordo, dentro la cavita' w = 1 (acqua), fuori w = 0 (tessuto); vicino al bordo,
        # dove la segmentazione e' incerta, la transizione e' graduale. Combinazione con pesi positivi:
        # i tensori restano definiti positivi.
        from scipy.ndimage import gaussian_filter
        sigma_vox = [args.cavity_sigma / s for s in spacing]
        w = gaussian_filter(cavityArr.astype(np.float64), sigma=sigma_vox)
        w[~(brainArr | cavityArr)] = 0.0
        print("MD mediana nel cervello: %.3g -> cavita' con transizione graduale tessuto/acqua libera "
              "(MD acqua %.3g, sigma %.1f mm, %d voxel nella cavita', %d voxel con 0.05 < w < 0.95)"
              % (medianMD, isoMD, args.cavity_sigma, cavityArr.sum(), ((w > 0.05) & (w < 0.95)).sum()))
        for comp in COMPONENTS:
            water = isoMD if comp in DIAGONAL else 0.0
            arrs[comp] = (1.0 - w) * arrs[comp] + w * water
        wImg = sitk.GetImageFromArray(w.astype(np.float32))
        wImg.CopyInformation(comps[COMPONENTS[0]])
        sitk.WriteImage(wImg, p("free_water_fraction.nii.gz"))

    for comp in COMPONENTS:
        filled = sitk.GetImageFromArray(arrs[comp])
        filled.CopyInformation(comps[comp])
        comps[comp] = filled

for comp in COMPONENTS:
    sitk.WriteImage(comps[comp], p("%s.nii.gz" % comp))

print("Output in %s" % out)
print("Controllo qualita': sovrapporre pre_T1_on_post.nrrd e FA_postop.nrrd a post_T1_masked.nrrd")
