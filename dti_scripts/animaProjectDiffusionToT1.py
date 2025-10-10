#!/usr/bin/env python3

# Warning: works only on unix-like systems, not windows where "python
# animaAtlasBasedBrainExtraction.py ..." has to be run

import sys
import argparse
import tempfile

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import os
import shutil
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
    description="Project diffusion model image, B0 image and noise variance image into the MNI space.")
parser.add_argument('-t', '--t1', type=str, required=True,
                    help="T1 image")
parser.add_argument('-m', '--models', type=str, required=True,
                    help="diffusion model image")
parser.add_argument('-v', '--variance', type=str,
                    required=True, help='Noise Variance Image')
parser.add_argument('-b', '--b0', type=str,
                    required=True, help='B0 Image')

args = parser.parse_args()

tmpFolder = tempfile.mkdtemp()

b0Image = args.b0
b0ImagePrefix = os.path.splitext(b0Image)[0]
if os.path.splitext(b0Image)[1] == '.gz':
    b0ImagePrefix = os.path.splitext(b0ImagePrefix)[0]

tmpB0ImagePrefix = os.path.join(tmpFolder, os.path.basename(b0ImagePrefix))

varianceImage = args.variance
varianceImagePrefix = os.path.splitext(varianceImage)[0]
if os.path.splitext(varianceImage)[1] == '.gz':
    varianceImagePrefix = os.path.splitext(varianceImagePrefix)[0]

t1Image = args.t1
t1ImagePrefix = os.path.splitext(t1Image)[0]
if os.path.splitext(t1Image)[1] == '.gz':
    t1ImagePrefix = os.path.splitext(t1ImagePrefix)[0]

modelImage = args.models
modelImagePrefix = os.path.splitext(modelImage)[0]
if os.path.splitext(modelImage)[1] == '.gz':
    modelImagePrefix = os.path.splitext(modelImagePrefix)[0]

########################
print("Patient B0 to Patient T1 Space")
########################

command = [animaDir + "animaPyramidalBMRegistration", "-r", t1Image, "-m", b0Image, "-o",
           tmpB0ImagePrefix + "_rig.nrrd", "-O", tmpB0ImagePrefix + "_rig_tr.txt", "-p", "4", "-l", "1"]
call(command)

command = [animaDir + "animaDenseSVFBMRegistration", "-r", t1Image, "-m", tmpB0ImagePrefix + "_rig.nrrd", "-o",
           tmpB0ImagePrefix + "_corr.nrrd", "-O", tmpB0ImagePrefix + "_corr_tr.nrrd", "-l", "1", "--es", "4", "--fs", "4"]
call(command)

########################
print("Projection")
########################

command = [animaDir + "animaTransformSerieXmlGenerator", "-i", tmpB0ImagePrefix + "_rig_tr.txt", "-i", tmpB0ImagePrefix +
           "_corr_tr.nrrd", "-o", tmpB0ImagePrefix + "_all_tr.xml"]
call(command)

command = [animaDir + "animaApplyTransformSerie", "-i", b0Image, "-t",
           tmpB0ImagePrefix + "_all_tr.xml", "-o", b0ImagePrefix + "_final.nrrd", "-g", t1Image]
call(command)

command = [animaDir + "animaApplyTransformSerie", "-i", varianceImage, "-t",
           tmpB0ImagePrefix + "_all_tr.xml", "-o", varianceImagePrefix + "_final.nrrd", "-g", t1Image]
call(command)

command = [animaDir + "animaTensorApplyTransformSerie", "-i", modelImage, "-t",
           tmpB0ImagePrefix + "_all_tr.xml", "-o", modelImagePrefix + "_final.nrrd", "-g", t1Image]
call(command)

shutil.rmtree(tmpFolder)
#print(tmpFolder)
