#!/usr/bin/env python
# Warning: works only on unix-like systems, not windows where "python animaMultiCompartmentModelEstimation.py ..." has
# to be run



import sys
import argparse


if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import os
from subprocess import call


configFilePath = os.path.expanduser("~") + "/.anima/config.txt"
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')

# Argument parsing
parser = argparse.ArgumentParser(
    description="Performs diffusion tensor estimation from preprocessed diffusion-weighted images.")
parser.add_argument('-p', '--nthreads', type=int, default=1,
                    help="Number of threads to run the estimation on (default = 1)")
parser.add_argument('--no-bval-scale', action='store_true',
                    help="Do not scale b-values when normalizing diffusion gradients")

parser.add_argument('-i', '--input', type=str,
                    required=True, help='DWI file to process')
parser.add_argument('-b', '--bval', type=str, required=True,
                    help='DWI b-value or bval file')
parser.add_argument('-g', '--bvec', type=str,
                    required=True, help='DWI gradients file')

# Get parameters from arguments parser
args = parser.parse_args()

dwiImage = args.input
print("Estimating tensor model for image " + dwiImage)

dwiImagePrefix = os.path.splitext(dwiImage)[0]
if os.path.splitext(dwiImage)[1] == '.gz':
    dwiImagePrefix = os.path.splitext(dwiImagePrefix)[0]

l = dwiImagePrefix.split("_")
if l[-1] == "preprocessed":
    outputPrefix = "_".join(l[:-1])
else:
    outputPrefix = dwiImagePrefix

dtiEstimationCommand = [animaDir + "animaDTIEstimator", "-i", dwiImage, "-o", outputPrefix + "_Tensors.nrrd", "-O", outputPrefix + "_B0.nrrd",
                        "-N", outputPrefix + "_Variance.nrrd", "-g", args.bvec, "-b", args.bval, "-m", outputPrefix + "_brainMask.nrrd", "-p", str(args.nthreads)]
if args.no_bval_scale is True:
    dtiEstimationCommand += ["-B"]
call(dtiEstimationCommand)

maskCommand = [animaDir + "animaMaskImage", "-i", outputPrefix + "_Tensors.nrrd",
               "-m", outputPrefix + "_brainMask.nrrd", "-o", outputPrefix + "_Tensors.nrrd"]
call(maskCommand)

maskCommand = [animaDir + "animaMaskImage", "-i", outputPrefix + "_B0.nrrd",
               "-m", outputPrefix + "_brainMask.nrrd", "-o", outputPrefix + "_B0.nrrd"]
call(maskCommand)

maskCommand = [animaDir + "animaMaskImage", "-i", outputPrefix + "_Variance.nrrd",
               "-m", outputPrefix + "_brainMask.nrrd", "-o", outputPrefix + "_Variance.nrrd"]
call(maskCommand)
