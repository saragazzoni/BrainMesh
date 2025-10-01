#!/bin/bash

INPUT_DIR=$1
OUTPUT_DIR=${INPUT_DIR}/processed
rm -fr ${OUTPUT_DIR}
mkdir ${OUTPUT_DIR}
DWI1=$2
DWI2=$3
DWI3=$4
DWI_PA=$5
T1=$6
SCRIPT_PATH=$7
ANIMA_BIN_PATH=$8
ANIMA_SCRIPT_PATH=$9
echo "Concatenating DWIs..."
python3 ${SCRIPT_PATH}/concatenate_dwis.py \
	--k1 ${INPUT_DIR}/${DWI1}.nii.gz \
	--b1 ${INPUT_DIR}/${DWI1}.bval \
	--r1 ${INPUT_DIR}/${DWI1}.bvec \
	--k2 ${INPUT_DIR}/${DWI2}.nii.gz \
	--b2 ${INPUT_DIR}/${DWI2}.bval \
	--r2 ${INPUT_DIR}/${DWI2}.bvec \
	--k3 ${INPUT_DIR}/${DWI3}.nii.gz \
	--b3 ${INPUT_DIR}/${DWI3}.bval \
	--r3 ${INPUT_DIR}/${DWI3}.bvec \
	-o ${OUTPUT_DIR}/DWI
echo "Cropping DWI PA image..."
${ANIMA_BIN_PATH}/animaCropImage \
	-i ${INPUT_DIR}/${DWI_PA} \
	-o ${OUTPUT_DIR}/DWI_B0_Reversed.nii.gz \
	-t 0 -T 0
echo "Preprocessing diffusion images..."
python3 ${ANIMA_SCRIPT_PATH}/diffusion/animaDiffusionImagePreprocessing.py \
	-i ${OUTPUT_DIR}/DWI.nii.gz \
	-t ${INPUT_DIR}/${T1} \
	-r ${OUTPUT_DIR}/DWI_B0_Reversed.nii.gz \
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