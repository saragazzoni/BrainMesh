#!/bin/bash

# run in background
docker run --name=DTI_registration  -v /Users/saragazzoni/Desktop/esempio/nifti_T1.anat/:/warps/ -v $(pwd)/:/input/ -it aldoclemente/fsl bash
cd /input/
# Find linear transform from DTI to original T1 space
for comp in Dxx Dxy Dxz Dyy Dyz Dzz; do
    flirt -in ${comp}.nii.gz \
        -ref /warps/T1_orig.nii.gz \
        -omat ${comp}2T1orig.mat \
        -out ${comp}_inT1orig.nii.gz \
        -dof 6 -cost normmi -interp trilinear

    applywarp -i ${comp}_inT1orig.nii.gz \
        -o ${comp}_inMNI.nii.gz \
        -r $FSLDIR/data/standard/MNI152_T1_2mm.nii.gz \
        -w /warps/T1_to_MNI_nonlin_field.nii.gz \
        --premat=/warps/T1_to_MNI_lin.mat
done

# stop container
docker stop DTI_registration





