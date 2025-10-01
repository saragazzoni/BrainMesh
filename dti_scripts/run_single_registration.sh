#!/bin/bash

# moving=$1
# reference=$2
# ANIMA_BIN_PATH=$3
# ANIMA_SCRIPT_PATH=$4
moving=Paziente1_a/images/2018-02-06/processed/Dxx.nii.gz
reference=Paziente1_a/images/2018-02-06/processed/*T1*_masked.nrrd
ANIMA_BIN_PATH=.././../../../../../../../home/saragazzoni/Software/Anima/build/bin
ANIMA_SCRIPT_PATH=../../../../../../../../../home/saragazzoni/Software/Anima/Anima-Scripts-Public
python3 ${ANIMA_SCRIPT_PATH}/brain_extraction/animaAtlasBasedBrainExtraction.py -i $moving
moving=${moving%.nii.gz}_masked.nrrd
${ANIMA_BIN_PATH}/animaPyramidalBMRegistration -r $reference -m $moving -o $moving -p 4 -l 1 --sp 2 -I 0
