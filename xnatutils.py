import os.path
import re
import stat
import getpass
import xnat

MBI_XNAT_SERVER = 'https://mbi-xnat.erc.monash.edu.au'

data_format_exts = {
    'NIFTI': '.nii',
    'NIFTI_GZ': '.nii.gz',
    'MRTRIX': '.mif',
    'DICOM': ''}


class XnatUtilsUsageError(Exception):
    pass


def connect(user=None):
    netrc_path = os.path.join(os.environ['HOME'], '.netrc')
    if user is not None or not os.path.exists(netrc_path):
        if user is None:
            user = raw_input('username: ')
        password = getpass.getpass()
        save_netrc = raw_input(
            "Would you like to save this username/password in your ~/.netrc "
            "(with 600 permissions) [Y/n]: ")
        if save_netrc.lower() not in ('n', 'no'):
            with open(netrc_path, 'w') as f:
                f.write(
                    "machine {}\n".format(MBI_XNAT_SERVER.split('/')[-1]) +
                    "user {}\n".format(user) +
                    "password {}\n".format(password))
            os.chmod(netrc_path, stat.S_IRUSR | stat.S_IWUSR)
    kwargs = ({'user': user, 'password': password}
              if not os.path.exists(netrc_path) else {})
    return xnat.connect(MBI_XNAT_SERVER, **kwargs)


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
        raise XnatUtilsUsageError(
            "No format matching extension '{}' (of '{}')"
            .format(extract_extension(filename), filename))


def get_extension(data_format):
    return data_format_exts[data_format]


def is_regex(string):
    "Checks to see if string contains special characters"
    return not bool(re.match(r'\w+', string))


def list_results(mbi_xnat, path):
    return mbi_xnat.get('/data/archive/' + path).json()['ResultSet']['Result']


def matching_sessions(mbi_xnat, session_ids):
    if isinstance(session_ids, basestring):
        session_ids = [session_ids]
    all_sessions = [s['label'] for s in list_results(mbi_xnat, 'experiments')]
    return [s for s in all_sessions
            if any(re.match(i, s) for i in session_ids)]


if __name__ == '__main__':
    with connect() as mbi_xnat:
        print '\n'.join(matching_sessions(mbi_xnat, 'MRH06.*_MR01'))
