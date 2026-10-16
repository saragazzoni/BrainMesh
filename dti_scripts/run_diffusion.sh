#!/bin/bash
# Uso: run_diffusion.sh <INPUT_DIR> "<serie DTI separate da spazi>" <PA> <T1> <SCRIPT_PATH> <ANIMA_BIN_PATH> <ANIMA_SCRIPT_PATH>
 
INPUT_DIR=$1
OUTPUT_DIR=${INPUT_DIR}/processed
rm -fr ${OUTPUT_DIR}
mkdir ${OUTPUT_DIR}
DWI_SERIES=$2
DWI_PA=$3
T1=$4
SCRIPT_PATH=$5
ANIMA_BIN_PATH=$6
ANIMA_SCRIPT_PATH=$7
 
echo "Concatenating DWIs: ${DWI_SERIES}"
DWI_INPUTS=""
for s in ${DWI_SERIES}; do
    DWI_INPUTS="${DWI_INPUTS} ${INPUT_DIR}/${s}"
done
python3 ${SCRIPT_PATH}/concatenate_dwis_n.py -i ${DWI_INPUTS} -o ${OUTPUT_DIR}/DWI
 
if [ -f "${INPUT_DIR}/${DWI_PA}" ]; then
    echo "Cropping DWI PA image..."
    ${ANIMA_BIN_PATH}/animaCropImage \
        -i ${INPUT_DIR}/${DWI_PA} \
        -o ${OUTPUT_DIR}/DWI_B0_Reversed.nii.gz \
        -t 0 -T 0
    REV_OPT="-r ${OUTPUT_DIR}/DWI_B0_Reversed.nii.gz"
else
    echo "[AVVISO] PA assente: correzione delle distorsioni basata sulla T1"
    echo "${INPUT_DIR}" >> "${SCRIPT_PATH}/pazienti_senza_PA.txt"
    REV_OPT=""
fi
 
echo "Preprocessing diffusion images..."
python3 ${ANIMA_SCRIPT_PATH}/diffusion/animaDiffusionImagePreprocessing.py \
    -i ${OUTPUT_DIR}/DWI.nii.gz \
    -t ${INPUT_DIR}/${T1} \
    ${REV_OPT} \
    -g ${OUTPUT_DIR}/DWI.bvec \
    -b ${OUTPUT_DIR}/DWI.bval
 
echo "Copying marked T1 files..."
cp ${INPUT_DIR}/*T1*_marked* ${OUTPUT_DIR}/
 
echo "Estimating MCM parameters..."
${ANIMA_BIN_PATH}/animaMCMEstimator \
    -i ${OUTPUT_DIR}/DWI_preprocessed.nrrd \
    -g ${OUTPUT_DIR}/DWI_preprocessed.bvec \
    -b ${OUTPUT_DIR}/DWI.bval \
    -o ${OUTPUT_DIR}/FW_1T \
    --out-b0 ${OUTPUT_DIR}/FW_1T_B0.nrrd \
    --out-sig ${OUTPUT_DIR}/FW_1T_Variance.nrrd \
    -m ${OUTPUT_DIR}/DWI_brainMask.nrrd \
    -n 1 \
    -c 3 \
    -F \
    --optimizer levenberg \
    --ml-mode 2
echo "Script completed successfully!"