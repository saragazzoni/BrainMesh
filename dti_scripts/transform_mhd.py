import vtk
import numpy as np
import meshio
import SimpleITK as sitk

path="/Users/saragazzoni/Desktop/Data/Campanini_Maria_paz23/Campanini_Maria/images/2018-02-26/processed"
# Matrice 4x4 affine
img = sitk.ReadImage(f"{path}/Dxx.mhd")
M = np.array([
    [-1, 0, 0, 0],
    [ 0,-1, 0, 252],
    [ 0, 0, 1, 0],
    [ 0, 0, 0, 1]
])

aff = sitk.AffineTransform(3)
aff.SetMatrix(M[:3,:3].flatten().tolist())
aff.SetTranslation(M[:3,3].tolist())

# ITK vuole la trasformazione inversa
resampled = sitk.Resample(img, img, aff.GetInverse(), sitk.sitkLinear, 0.0, img.GetPixelID())
sitk.WriteImage(resampled, f"{path}/Dxx_affine_itk.mhd")