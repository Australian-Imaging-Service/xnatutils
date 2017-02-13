import os.path
import xnat

MBI_XNAT_SERVER = 'https://mbi-xnat.erc.monash.edu.au'

data_formats_by_ext = {
    'nii': 'NIFTI',
    'nii.gz': 'NIFTI_GZ',
    'mif': 'MRTRIX'}


def connect():
    return xnat.connect(MBI_XNAT_SERVER)


def get_data_format(filename):
    name_parts = os.path.basename(filename).split('.')
    if name_parts[-1] == 'gz':
        num_parts = 2
    else:
        num_parts = 1
    ext = '.'.join(name_parts[-num_parts:])
    return data_formats_by_ext[ext]
