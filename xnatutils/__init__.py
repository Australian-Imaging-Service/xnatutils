import os.path
import xnat

MBI_XNAT_SERVER = 'https://mbi-xnat.erc.monash.edu.au'

data_formats_by_ext = {
    '.nii': 'NIFTI',
    '.nii.gz': 'NIFTI_GZ',
    '.mif': 'MRTRIX'}


def connect():
    return xnat.connect(MBI_XNAT_SERVER)


def get_data_format(filename):
    ext = os.path.splitext(filename)[1]
    return data_formats_by_ext[ext]
