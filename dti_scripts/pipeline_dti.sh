#!/bin/bash
# ===============================================
# PIPELINE DTI → MESH (Step 1: DICOM → NIfTI, Step 2: main.sh)
# ===============================================
# Author: Sara Gazzoni
# Last modified: 10/10/2025
# ===============================================

# ======== 1. CONFIGURATION ========
# MODIFY ONLY THIS SECTION
# The per-patient values (path, exam folders/dates, DTI series, masks) can also be passed from
# outside as environment variables: run_all_dti.sh does this for all patients listed in a table.
# A value passed from outside wins over the one written here.

# Path to patient directory (DICOM)
PATH_TO_PATIENT="${PATH_TO_PATIENT:-/Users/saragazzoni/Desktop/Data/Pazienti/paz3}"
BASENAME="${BASENAME:-T1_3D_AX_mdc}"  # Base name of the reference MRI file (without extension)
EXAM_FOLDER="${EXAM_FOLDER:-Rm_10-7-18}"  # Name of the exam folder to process
EXAM_DATE="${EXAM_DATE:-2018-07-10}"  # Date of the exam to process (format: YYYY-MM-DD)

DTI_SERIES="${DTI_SERIES:-DTI_20_dir_B700 DTI_40_dir_B1500 DTI_64_dir_B3000}"

# Separation tag for exams dates (e.g., "-" in "2023-01-15")
SEPARATION_TAG="-"

# Paths to Anima scripts and tools needed for main.sh
SCRIPT_PATH="/Users/saragazzoni/Desktop/Code/BrainMesh/dti_scripts"
ANIMA_BIN_PATH="/Users/saragazzoni/Documents/Anima-Binaries-4.2"
ANIMA_SCRIPT_PATH="/Users/saragazzoni/Documents/Anima-Scripts-Public"

# Path to the folder containing the mesh
PATH_TO_MESH_FOLDER="${PATH_TO_PATIENT}"

# (Optional) Map the preop DTI onto the POSTOP exam. Leave POSTOP_EXAM_FOLDER empty to disable.
# The postop exam is converted to NIfTI in ${PATH_TO_PATIENT}/images_postop/<date>.
# The T1 must be the same series used to build the postop mesh.
POSTOP_EXAM_FOLDER="${POSTOP_EXAM_FOLDER-postop}"   # DICOM exam folder NAME inside PATH_TO_PATIENT (like EXAM_FOLDER), e.g. "Rm_10-4-18"
POSTOP_EXAM_DATE="${POSTOP_EXAM_DATE-2018-07-20}"     # date of the postop exam (format: YYYY-MM-DD), e.g. "2018-04-10"
POSTOP_BASENAME="${POSTOP_BASENAME:-T1_3D_AX_mdc}"  # name of the postop T1 after conversion (without extension)
PREOP_TUMOR_MASK="${PREOP_TUMOR_MASK-/Users/saragazzoni/Desktop/Data/raidionics_out/paz3/tumor_prob.nii.gz}"     # tumor segmentation on the PREOP T1 (binary or probability map), optional
POSTOP_CAVITY_MASK="${POSTOP_CAVITY_MASK-/Users/saragazzoni/Desktop/Data/raidionics_out/paz3/postop/cavity_mask.nii.gz}"   # cavity segmentation on the POSTOP T1 (binary or probability map), optional
POSTOP_LINEAR="rigid"   # rigid | affine
POSTOP_NONLINEAR=1      # 1 = masked non-linear registration, 0 = linear only
POSTOP_MARGIN_MM=5      # dilation (mm) of the region excluded from the registration
POSTOP_CAVITY_FILL="blend"     # tensors in the cavity: blend = free water inside, smooth transition to tissue at the border; free-water = sharp border; nearest = nearest tissue
POSTOP_CAVITY_SIGMA=2          # width (mm) of the transition, only for blend
# Python environment with SimpleITK
BRAINMESH_PYTHON="/Users/saragazzoni/anaconda3/envs/brain-mesh/bin/python"

# Skip steps whose results already exist (1 = skip, 0 = always redo everything):
#  - preop DICOM -> NIfTI          if images/<EXAM_DATE>/<BASENAME>.nii.gz exists
#  - postop DICOM -> NIfTI         if images_postop/<POSTOP_EXAM_DATE>/<POSTOP_BASENAME>.nii.gz exists
#  - preop DTI processing          (main.sh, tensor estimation, projection onto the T1)
#                                  if images/<EXAM_DATE>/processed/DWI_Tensors_final.nrrd exists
# The postop projection (step 4) is always redone.
SKIP_DONE="${SKIP_DONE:-1}"

# ======== 2. FUNZIONI UTILI ========
log() {
    echo -e "\n[INFO] $(date '+%H:%M:%S') - $1"
}

check_dir() {
    if [ ! -d "$1" ]; then
        echo "[ERRORE] Directory non trovata: $1"
        exit 1
    fi
}

check_file() {
    if [ ! -f "$1" ]; then
        echo "[ERRORE] File non trovato: $1"
        exit 1
    fi
}

# # ======== 3. CONTROLLO INPUT ========
check_dir "$PATH_TO_PATIENT"

# # ======== 4. STEP 1 - DICOM → NIfTI ========
# log "Converto DICOM in NIfTI per il paziente in ${PATH_TO_PATIENT}"
# ./dicomToNifti.sh "$PATH_TO_PATIENT" "$EXAM_FOLDER" "$SEPARATION_TAG"
# if [ $? -ne 0 ]; then
#     echo "[ERRORE] dicomToNifti.sh non completato correttamente."
#     exit 1
# fi

# ======== 4. STEP 1 - DICOM → NIfTI ========
IMG_DIR="${PATH_TO_PATIENT}/images/${EXAM_DATE}"
if [ "$SKIP_DONE" = "1" ] && [ -f "${IMG_DIR}/${BASENAME}.nii.gz" ]; then
    log "NIfTI preop gia' presenti in ${IMG_DIR}: salto la conversione"
else
    log "Converto DICOM in NIfTI per il paziente in ${PATH_TO_PATIENT}"
    ./dicomToNifti.sh "$PATH_TO_PATIENT" "$EXAM_FOLDER" "$SEPARATION_TAG" \
        || echo "[AVVISO] dcm2niix ha segnalato errori, controllo le serie DTI..."
fi
( cd "$IMG_DIR" && for f in WIP_*; do [ -e "$f" ] && mv -n -- "$f" "${f#WIP_}"; done )

POSTOP_T1=""
if [ -n "$POSTOP_EXAM_FOLDER" ]; then
    check_dir "${PATH_TO_PATIENT}/${POSTOP_EXAM_FOLDER}"
    POSTOP_IMG_DIR="${PATH_TO_PATIENT}/images_postop/${POSTOP_EXAM_DATE}"
    POSTOP_T1="${POSTOP_IMG_DIR}/${POSTOP_BASENAME}.nii.gz"
    if [ "$SKIP_DONE" = "1" ] && [ -f "$POSTOP_T1" ]; then
        log "NIfTI postop gia' presenti in ${POSTOP_IMG_DIR}: salto la conversione"
    else
        log "Converto DICOM in NIfTI per l'esame postop ${POSTOP_EXAM_FOLDER}"
        ./dicomToNifti.sh "$PATH_TO_PATIENT" "$POSTOP_EXAM_FOLDER" "$SEPARATION_TAG" images_postop \
            || echo "[AVVISO] dcm2niix ha segnalato errori sull'esame postop"
    fi
    ( cd "$POSTOP_IMG_DIR" && for f in WIP_*; do [ -e "$f" ] && mv -n -- "$f" "${f#WIP_}"; done )
    check_file "$POSTOP_T1"
    [ -n "$PREOP_TUMOR_MASK" ] && check_file "$PREOP_TUMOR_MASK"
    [ -n "$POSTOP_CAVITY_MASK" ] && check_file "$POSTOP_CAVITY_MASK"
fi

python "$SCRIPT_PATH/check_dti_nifti.py" "$IMG_DIR" $DTI_SERIES \
    || { echo "[ERRORE] serie DTI mancanti o incomplete"; exit 1; }

# File originale
GENERATED_FILE="${PATH_TO_PATIENT}/images/${EXAM_DATE}/${BASENAME}.nii.gz"
check_file "$GENERATED_FILE"

if [ "$SKIP_DONE" = "1" ] && [ -f "${IMG_DIR}/processed/DWI_Tensors_final.nrrd" ]; then
    log "Elaborazione DTI preop gia' fatta (${IMG_DIR}/processed/DWI_Tensors_final.nrrd): salto main.sh e la stima dei tensori"
    check_file "${IMG_DIR}/processed/${BASENAME}_marked_masked.nrrd"
else
# File marcato
MARKED_FILE="${PATH_TO_PATIENT}/images/${EXAM_DATE}/${BASENAME}_marked.nii.gz"
cp "$GENERATED_FILE" "$MARKED_FILE"

log "File copiato e rinominato: $MARKED_FILE"


# ======== 5. STEP 2 - Esecuzione main.sh ========
log "Eseguo main.sh con variabili di ambiente personalizzate..."

# Esporta le variabili che main.sh si aspetta
export SCRIPT_PATH
export ANIMA_BIN_PATH
export ANIMA_SCRIPT_PATH
export DTI_SERIES

./main.sh "$PATH_TO_PATIENT" "$SCRIPT_PATH" "$ANIMA_BIN_PATH" "$ANIMA_SCRIPT_PATH"
if [ $? -ne 0 ]; then
    echo "[ERRORE] main.sh non completato correttamente."
    exit 1
fi

check_file "${IMG_DIR}/processed/DWI_preprocessed.nrrd"
check_file "${IMG_DIR}/processed/${BASENAME}_marked_masked.nrrd"

# # ======== STEP 3 - Diffusion Tensor Estimation ========
cd "${PATH_TO_PATIENT}/images/${EXAM_DATE}/processed" || exit 1
echo "Eseguo stima del tensore di diffusione..."

python $SCRIPT_PATH/animaTensorModelEstimation.py \
    -i DWI_preprocessed.nrrd \
    -g DWI_preprocessed.bvec \
    -b DWI.bval \
    -p 4

python $SCRIPT_PATH/animaProjectDiffusionToT1.py \
    -t ${BASENAME}_marked_masked.nrrd \
    -m DWI_Tensors.nrrd \
    -v DWI_Variance.nrrd \
    -b DWI_B0.nrrd
fi

# ======== STEP 4  - Extract 6 components from the diffusion tensor ========
cd "${PATH_TO_PATIENT}/images/${EXAM_DATE}/processed" || exit 1
if [ -n "$POSTOP_T1" ]; then
    # Preop tensors -> postop T1 (masked registration, cavity filled with isotropic tensor)
    check_file "$POSTOP_T1"
    POSTOP_OPTS="--linear ${POSTOP_LINEAR} --margin ${POSTOP_MARGIN_MM} --cavity-fill ${POSTOP_CAVITY_FILL} --cavity-sigma ${POSTOP_CAVITY_SIGMA}"
    [ -n "$PREOP_TUMOR_MASK" ] && POSTOP_OPTS="${POSTOP_OPTS} --tumor-mask ${PREOP_TUMOR_MASK}"
    [ -n "$POSTOP_CAVITY_MASK" ] && POSTOP_OPTS="${POSTOP_OPTS} --cavity-mask ${POSTOP_CAVITY_MASK}"
    [ "$POSTOP_NONLINEAR" = "0" ] && POSTOP_OPTS="${POSTOP_OPTS} --no-nonlinear"
    if [ -f DWI_B0_rig_tr.txt ] && [ -f DWI_B0_corr_tr.nrrd ]; then
        TENSOR_OPTS="--tensors DWI_Tensors.nrrd --b0-transforms DWI_B0_rig_tr.txt DWI_B0_corr_tr.nrrd"
    else
        TENSOR_OPTS="--tensors DWI_Tensors_final.nrrd"
    fi

    log "Proietto i tensori preop sulla T1 postop: ${POSTOP_T1}"
    $BRAINMESH_PYTHON $SCRIPT_PATH/animaProjectDiffusionToPostop.py \
        --pre-t1 ${BASENAME}_marked_masked.nrrd \
        --post-t1 "$POSTOP_T1" \
        ${TENSOR_OPTS} ${POSTOP_OPTS} \
        -o postop \
        || { echo "[ERRORE] proiezione sul postop non completata"; exit 1; }
    cd postop || exit 1
    DTI_OUT_FOLDER="${PATH_TO_MESH_FOLDER}/dti_postop"
else
    ${ANIMA_BIN_PATH}/animaCollapseImage -i DWI_Tensors_final.nrrd -o tmp.nrrd
    ${ANIMA_BIN_PATH}/animaCropImage -i tmp.nrrd -t 0 -T 0 -o Dxx.nii.gz
    ${ANIMA_BIN_PATH}/animaCropImage -i tmp.nrrd -t 1 -T 0 -o Dxy.nii.gz
    ${ANIMA_BIN_PATH}/animaCropImage -i tmp.nrrd -t 2 -T 0 -o Dyy.nii.gz
    ${ANIMA_BIN_PATH}/animaCropImage -i tmp.nrrd -t 3 -T 0 -o Dxz.nii.gz
    ${ANIMA_BIN_PATH}/animaCropImage -i tmp.nrrd -t 4 -T 0 -o Dyz.nii.gz
    ${ANIMA_BIN_PATH}/animaCropImage -i tmp.nrrd -t 5 -T 0 -o Dzz.nii.gz
    DTI_OUT_FOLDER="${PATH_TO_MESH_FOLDER}/dti"
fi

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/saragazzoni/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/saragazzoni/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/saragazzoni/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/saragazzoni/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

mkdir -p ${DTI_OUT_FOLDER}

conda activate vmtk_env
for comp in Dxx Dxy Dyy Dxz Dyz Dzz; do
    vmtk vmtkimagewriter -ifile ${comp}.nii.gz -ofile ${DTI_OUT_FOLDER}/${comp}.mhd
done
rm -fr tmp*.nrrd Dxx.nii.gz Dxy.nii.gz Dyy.nii.gz Dxz.nii.gz Dyz.nii.gz Dzz.nii.gz


