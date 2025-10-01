#!/usr/bin/python3
import numpy as np
import nibabel as nib
from optparse import OptionParser

# We override the OptionParser class, and add a method to check for required options.
class OptionParser(OptionParser):
    """
    Command-line arguments parser: add control for required options.
    """
    def check_required (self, opt):
        option = self.get_option(opt)

        # Assumes the option's 'default' is set to None!
        if getattr(self.values, option.dest) is None:
            self.error("%s option not supplied" % option)


# Parse command-line arguments
usage = """usage: %prog --k1=<dwi filename> --b1=<bval> --r1=<bvec>
                        --k2=<dwi filename> --b2=<bval> --r2=<bvec>
                        -o <output prefix>
Concatenates two sets of diffusion-weighted images.

%prog -h displays a complete help message.
"""
parser = OptionParser(usage=usage)
parser.add_option("--k1", "--data1", dest="data1", type="string",
                  help="Input dwis data file (Nifti or Analyze format).")
parser.add_option("--b1", "--bvals1", dest="bvals1", type="string",
                  help="B-values (.bval file).")
parser.add_option("--r1", "--bvecs1", dest="bvecs1", type="string",
                  help="B-vectors (.bvec file).")
parser.add_option("--k2", "--data2", dest="data2", type="string",
                  help="Input dwis data file (Nifti or Analyze format).")
parser.add_option("--b2", "--bvals2", dest="bvals2", type="string",
                  help="B-values (.bval file).")
parser.add_option("--r2", "--bvecs2", dest="bvecs2", type="string",
                  help="B-vectors (.bvec file).")
parser.add_option("--k3", "--data3", dest="data3", type="string",
                  help="Input dwis data file (Nifti or Analyze format).")
parser.add_option("--b3", "--bvals3", dest="bvals3", type="string",
                  help="B-values (.bval file).")
parser.add_option("--r3", "--bvecs3", dest="bvecs3", type="string",
                  help="B-vectors (.bvec file).")
parser.add_option("-o", "--output", dest="output", type="string",
                  help="Output prefix name for dwis and bval/bvec.")

(options, args) = parser.parse_args()

# All options are required
parser.check_required("--k1")
parser.check_required("--b1")
parser.check_required("--r1")
parser.check_required("--k2")
parser.check_required("--b2")
parser.check_required("--r2")
parser.check_required("--k3")
parser.check_required("--b3")
parser.check_required("--r3")
parser.check_required("-o")

print("Open data1 from disk...")
dwis_filename1 = options.data1
dwis_img1 = nib.load(dwis_filename1)
dwis1 = dwis_img1.get_fdata()
sform = dwis_img1.get_sform()
qform = dwis_img1.get_qform()
affine = dwis_img1.affine
dim_x, dim_y, dim_z, _ = dwis1.shape

print("Open data2 from disk...")
dwis_filename2 = options.data2
dwis_img2 = nib.load(dwis_filename2)
dwis2 = dwis_img2.get_fdata()

print("Open data3 from disk...")
dwis_filename3 = options.data3
dwis_img3 = nib.load(dwis_filename3)
dwis3 = dwis_img3.get_fdata()

print("Open bval1 and bvec1 files...")
bvals_filename1 = options.bvals1
bvecs_filename1 = options.bvecs1
bvals1 = np.loadtxt(bvals_filename1)
bvecs1 = np.loadtxt(bvecs_filename1)

print("Open bval2 and bvec2 files...")
bvals_filename2 = options.bvals2
bvecs_filename2 = options.bvecs2
bvals2 = np.loadtxt(bvals_filename2)
bvecs2 = np.loadtxt(bvecs_filename2)

print("Open bval3 and bvec3 files...")
bvals_filename3 = options.bvals3
bvecs_filename3 = options.bvecs3
bvals3 = np.loadtxt(bvals_filename3)
bvecs3 = np.loadtxt(bvecs_filename3)

k1, k2, k3 = bvals1.shape[0], bvals2.shape[0], bvals3.shape[0]

print("Concatenate images and bval/bvec files.")
bvals = np.hstack((bvals1[np.newaxis, :], bvals2[np.newaxis, :], bvals3[np.newaxis, :]))
bvecs = np.hstack((bvecs1, bvecs2, bvecs3))
dwis = np.zeros((dim_x, dim_y, dim_z, k1 + k2 + k3), dtype=dwis1.dtype)
dwis[..., :k1] = dwis1
dwis[..., k1:(k1+k2)] = dwis2
dwis[..., (k1+k2):] = dwis3

output_prefix = options.output
print("Save bval and bvec file")
np.savetxt("%s.bval" % output_prefix, bvals, fmt="%.1f")
np.savetxt("%s.bvec" % output_prefix, bvecs, fmt="%.6f")

print("Save dwis file")
hdr = nib.Nifti1Header()
hdr.set_data_shape(dwis.shape)
hdr.set_sform(sform)
hdr.set_qform(qform)
dwis_img = nib.Nifti1Image(dwis, affine, header=hdr)
nib.save(dwis_img, "%s.nii.gz" % output_prefix)
