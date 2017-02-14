import os.path
import xnat

MBI_XNAT_SERVER = 'https://mbi-xnat.erc.monash.edu.au'

data_format_exts = {
    'NIFTI': '.nii',
    'NIFTI_GZ': '.nii.gz',
    'MRTRIX': '.mif',
    'DICOM': ''}


class XnatUtilsUsageException(Exception):
    pass


def connect(user=None):
    if user is not None:
        raise NotImplementedError(
            "Specifying a different username is not currently supported. "
            " Please store authcate and password in ~/.netrc (with permissions"
            " 600) in the format (see https://xnat.readthedocs.io/en/latest/"
            "static/tutorial.html#credentials):\n"
            "\n"
            "machine mbi-xnat.erc.monash.edu.au\n"
            "user <your-authcate>\n"
            "password <your-authcate-password>\n")
    return xnat.connect(MBI_XNAT_SERVER)


def extract_extension(filename):
    name_parts = os.path.basename(filename).split('.')
    if len(name_parts) == 1:
        ext = ''
    else:
        if name_parts[-1] == 'gz':
            num_parts = 2
        else:
            num_parts = 1
        ext = '.' + '.'.join(name_parts[-num_parts:])
    return ext


def get_data_format(filename):
    try:
        return next(k for k, v in data_format_exts.iteritems()
                    if v == extract_extension(filename))
    except StopIteration:
        raise XnatUtilsUsageException(
            "No format matching extension '{}' (of '{}')"
            .format(extract_extension(filename), filename))


def get_extension(data_format):
    return data_format_exts[data_format]
