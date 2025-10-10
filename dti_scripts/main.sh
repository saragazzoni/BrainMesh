#!/bin/bash

CASE_FOLDER=$1
SCRIPT_PATH=$2
ANIMA_BIN_PATH=$3
ANIMA_SCRIPT_PATH=$4

echo "**********************************************************"
echo "***             Diffusion Preprocessing                ***"
echo "*** (in all exams in which the sequence was performed) ***"
echo "**********************************************************"
echo ""

# You need to manually choose a reference T1 in each of the following folders
# You do that by copying it and appending _marked to the filename
DATES=`find ${CASE_FOLDER}/images -type f -name '*DTI_20_dir*' | sed -r 's|/[^/]+$||' | sort | uniq`
# echo $DATES

 for date in ${DATES}; do
 	IMAGE_PATH=${date}
 	echo "-------------------------------------"
 	echo "- Dealing with $IMAGE_PATH -"
 	echo "-------------------------------------"
 	sh ${SCRIPT_PATH}/run_diffusion.sh \
 		${IMAGE_PATH} \
 		DTI_20_dir_B700 \
 		DTI_40_dir_B1500 \
 		DTI_64_dir_B3000 \
 		DTI_6_dir_B700_PA.nii.gz \
 		*T1*_marked.nii.gz \
 		${SCRIPT_PATH} \
 		${ANIMA_BIN_PATH} \
 		${ANIMA_SCRIPT_PATH}
 done

echo "***********************************************************************************"
echo "***                                Registration Step                            ***"
echo "*** (in all exams in which either a T1 or a FLAIR or a DWI sequence was marked) ***"
echo "***********************************************************************************"
echo ""

IMAGE_PATHS=`find ${CASE_FOLDER}/images -maxdepth 2 -type f  \( -name "*DTI_64_dir*" -o -name "*FLAIR*_marked.nii.gz" -o -name "*T1*_marked.nii.gz" \) | sed -r 's|/[^/]+$||' | sort | uniq`

# Set overall reference T1
REF_T1="`echo $DATES | cut -d' ' -f1`/processed/*T1*_masked.nrrd"
echo "Dates found: $DATES" 
echo "Reference T1: $REF_T1"
${ANIMA_BIN_PATH}/animaConvertImage -i $REF_T1 -o $REF_T1 -R AXIAL

for date in ${IMAGE_PATHS}; do
	IMAGE_PATH=${date}
	DIFFUSION_PATH=`find ${IMAGE_PATH} -type d -name "processed"`
	if [ ! -z "$DIFFUSION_PATH" ]; then
		echo "Registration of diffusion data in ${DIFFUSION_PATH} onto reference T1"
		sh ${SCRIPT_PATH}/run_diffusion_registration.sh \
			${DIFFUSION_PATH}/FW_1T_B0.nrrd \
			${REF_T1} \
			${DIFFUSION_PATH}/DWI_Tensors.nrrd \
			${DIFFUSION_PATH}/FW_1T.mcm \
			${ANIMA_BIN_PATH}
	fi
	T1_PATH=`find ${IMAGE_PATH} -maxdepth 1 -type f -name "*T1*_marked.nii.gz"`
	if [ ! -z "$T1_PATH" ]; then
		echo "Registration of T1 data in ${T1_PATH} onto reference T1"
		sh ${SCRIPT_PATH}/run_single_registration.sh ${T1_PATH} ${REF_T1} ${ANIMA_BIN_PATH} ${ANIMA_SCRIPT_PATH}
	fi
	FLAIR_PATH=`find ${IMAGE_PATH} -maxdepth 1 -type f -name "*FLAIR*_marked.nii.gz"`
	if [ ! -z "$FLAIR_PATH" ]; then
		echo "Registration of FLAIR data in ${FLAIR_PATH} onto reference T1"
		sh ${SCRIPT_PATH}/run_single_registration.sh ${FLAIR_PATH} ${REF_T1} ${ANIMA_BIN_PATH} ${ANIMA_SCRIPT_PATH}
	fi
done
