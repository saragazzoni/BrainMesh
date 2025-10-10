#!/bin/bash
# ===============================================
# PIPELINE DTI → MESH (Step 1: DICOM → NIfTI, Step 2: main.sh)
# ===============================================
# Author: Sara Gazzoni
# Last modified: 10/10/2025
# ===============================================

# ======== 1. CONFIGURATION ========
# MODIFY ONLY THIS SECTION

# Path to patient directory (DICOM)
PATH_TO_PATIENT="/Users/saragazzoni/Desktop/Data/Campanini_Maria_paz23/Campanini_Maria"
BASENAME="T1_3D_AX_mdc"  # Base name of the reference MRI file (without extension)
EXAM_FOLDER="Rm_6-7-18"  # Name of the exam folder to process
EXAM_DATE="2018-07-06"  # Date of the exam to process (format: YYYY-MM-DD)

# Separation tag for exams dates (e.g., "-" in "2023-01-15")
SEPARATION_TAG="-"

# Paths to Anima scripts and tools needed for main.sh
SCRIPT_PATH="/Users/saragazzoni/Desktop/Code/BrainMesh/dti_scripts"
ANIMA_BIN_PATH="/Users/saragazzoni/Documents/Anima-Binaries-4.2"
ANIMA_SCRIPT_PATH="/Users/saragazzoni/Documents/Anima-Scripts-Public"


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

# ======== 3. CONTROLLO INPUT ========
check_dir "$PATH_TO_PATIENT"

# ======== 4. STEP 1 - DICOM → NIfTI ========
log "Converto DICOM in NIfTI per il paziente in ${PATH_TO_PATIENT}"
./dicomToNifti.sh "$PATH_TO_PATIENT" "$EXAM_FOLDER" "$SEPARATION_TAG"
if [ $? -ne 0 ]; then
    echo "[ERRORE] dicomToNifti.sh non completato correttamente."
    exit 1
fi

# File originale
GENERATED_FILE="${PATH_TO_PATIENT}/images/${EXAM_DATE}/${BASENAME}.nii.gz"
check_file "$GENERATED_FILE"

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

./main.sh "$PATH_TO_PATIENT" "$SCRIPT_PATH" "$ANIMA_BIN_PATH" "$ANIMA_SCRIPT_PATH"
if [ $? -ne 0 ]; then
    echo "[ERRORE] main.sh non completato correttamente."
    exit 1
fi

# ======== STEP 3 - Diffusion Tensor Estimation ========
cd "${PATH_TO_PATIENT}/images/${EXAM_DATE}/processed" || exit 1
log "Eseguo stima del tensore di diffusione..."

python $SCRIPT_PATH/animaTensorModelEstimation.py \
    -i DWI_preprocessed.nrrd \
    -g DWI_preprocessed.bvec \
    -b DWI.bval \
    -p 4

python $SCRIPT_PATH/animaProjectDiffusionToT1.py \
    -t ${BASENAME}_masked.nrrd \
    -m DWI_Tensors.nrrd \
    -v DWI_Variance.nrrd \
    -b DWI_B0.nrrd

# ======== STEP 4  - Extract 6 components from the diffusion tensor ========
${ANIMA_BIN_PATH}/animaCollapseImage -i DWI_Tensors.nrrd -o tmp.nrrd
animaCropImage -i tmp.nrrd -t 0 -T 0 -o Dxx.nii.gz
animaCropImage -i tmp.nrrd -t 1 -T 0 -o Dxy.nii.gz
animaCropImage -i tmp.nrrd -t 2 -T 0 -o Dyy.nii.gz
animaCropImage -i tmp.nrrd -t 3 -T 0 -o Dxz.nii.gz
animaCropImage -i tmp.nrrd -t 4 -T 0 -o Dyz.nii.gz
animaCropImage -i tmp.nrrd -t 5 -T 0 -o Dzz.nii.gz

conda activate vmtk-env
vmtk vmtkimagewriter -ifile Dxx.nii.gz -ofile Dxx.mhd
vmtk vmtkimagewriter -ifile Dxy.nii.gz -ofile Dxy.mhd
vmtk vmtkimagewriter -ifile Dyy.nii.gz -ofile Dyy.mhd
vmtk vmtkimagewriter -ifile Dxz.nii.gz -ofile Dxz.mhd
vmtk vmtkimagewriter -ifile Dyz.nii.gz -ofile Dyz.mhd
vmtk vmtkimagewriter -ifile Dzz.nii.gz -ofile Dzz.mhd
rm -fr tmp*.nrrd Dxx.nii.gz Dxy.nii.gz Dyy.nii.gz Dxz.nii.gz Dyz.nii.gz Dzz.nii.gz
conda deactivate

# ======== STEP 5  - Projection on the mesh ========


# ======== 6. FINE ========
log "Step completati con successo! Output disponibile nella directory del paziente."
