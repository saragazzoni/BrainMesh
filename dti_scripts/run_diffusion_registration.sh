#!/bin/bash

moving=$1
reference=$2
DTM=$3
MCM=$4
ANIMA_BIN_PATH=$5
${ANIMA_BIN_PATH}/animaPyramidalBMRegistration -r $reference -m $moving -o tmp.nrrd -p 4 -l 1 --sp 2 -I 0 -O tmp_trsf.txt
${ANIMA_BIN_PATH}/animaTransformSerieXmlGenerator -i tmp_trsf.txt -o tmp_trsf.xml
${ANIMA_BIN_PATH}/animaTensorApplyTransformSerie -i $DTM -t tmp_trsf.xml -o ${DTM%.nrrd}_common.nrrd -g $reference
${ANIMA_BIN_PATH}/animaMCMApplyTransformSerie -i $MCM -t tmp_trsf.xml -o ${MCM%.mcm}_common.mcm -g $reference
rm -fr tmp*
