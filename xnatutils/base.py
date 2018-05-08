from past.builtins import basestring
import os.path
import re
import errno
import stat
import getpass
from builtins import input
import xnat
from xnat.exceptions import XNATResponseError
from .exceptions import (
    XnatUtilsLookupError, XnatUtilsUsageError, XnatUtilsKeyError)
import warnings
import logging

logger = logging.getLogger('xnat-utils')


MBI_XNAT_SERVER = 'https://mbi-xnat.erc.monash.edu.au'

skip_resources = ['SNAPSHOTS']

resource_exts = {
    'NIFTI': '.nii',
    'NIFTI_GZ': '.nii.gz',
    'PDF': '.pdf',
    'MRTRIX': '.mif',
    'DICOM': '',
    'secondary': '',
    'TEXT_MATRIX': '.mat',
    'MRTRIX_GRAD': '.b',
    'FSL_BVECS': '.bvec',
    'FSL_BVALS': '.bval',
    'MATLAB': '.mat',
    'ANALYZE': '.img',
    'ZIP': '.zip',
    'RDATA': '.rdata',
    'DAT': '.dat',
    'RAW': '.rda',
    'JPG': '.JPG',
    'TEXT': '.txt',
    'TAR_GZ': '.tar.gz',
    'CSV': '.csv',
    'BINARY_FILE': '.bf'}


sanitize_re = re.compile(r'[^a-zA-Z_0-9]')
# TODO: Need to add other illegal chars here
illegal_scan_chars_re = re.compile(r'\.')

session_modality_re = re.compile(r'\w+_\w+_([A-Z]+)\d+')


def connect(user=None, loglevel='ERROR', connection=None, depth=0,
            save_netrc=True, server=MBI_XNAT_SERVER):
    """
    Opens a connection to MBI-XNAT

    Parameters
    ----------
    user : str
        The username to connect with. If None then tries to load the
        username from the $HOME/.netrc file
    loglevel : str
        The logging level to display. In order of increasing verbosity
        ERROR, WARNING, INFO, DEBUG.
    connection : xnat.Session
        An existing XnatPy session that is to be reused instead of
        creating a new session. The session is wrapped in a dummy class
        that disables the disconnection on exit, to allow the method to
        be nested in a wider connection context (i.e. reuse the same
        connection between commands).
    server: str
        URI of the XNAT server to use. Default's to MBI-XNAT.
    Returns
    -------
    connection : xnat.Session
        A XnatPy session
    """
    if connection is not None:
        return WrappedXnatSession(connection)
    netrc_path = os.path.join(os.path.expanduser('~'), '.netrc')
    saved_netrc = False
    if user is not None or not os.path.exists(netrc_path) or not save_netrc:
        if user is None:
            user = input('authcate/username: ')
        password = getpass.getpass()
        if save_netrc:
            save_netrc_response = input(
                "Would you like to save this username/password in your "
                "~/.netrc (with 600 permissions) [y/N]: ")
            if save_netrc_response.lower() in ('y', 'yes'):
                with open(netrc_path, 'w') as f:
                    f.write(
                        "machine {}\n".format(server.split('/')[-1]) +
                        "user {}\n".format(user) +
                        "password {}\n".format(password))
                os.chmod(netrc_path, stat.S_IRUSR | stat.S_IWUSR)
                print ("XNAT username and password for user '{}' "
                       "saved in {}".format(
                           user, os.path.join(os.path.expanduser('~'),
                                              '.netrc')))
                saved_netrc = True
    else:
        saved_netrc = 'existing'
    kwargs = ({'user': user, 'password': password}
              if not os.path.exists(netrc_path) else {})
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            return xnat.connect(server, loglevel=loglevel, **kwargs)
        except ValueError:  # Login failed
            if saved_netrc:
                remove_ignore_errors(netrc_path)
                if saved_netrc == 'existing':
                    print("Removing saved credentials...")
            print("Your account will be blocked for 1 hour after 3 "
                  "failed login attempts. Please contact "
                  "mbi-xnat@monash.edu to have it reset.")
            if depth < 3:
                return connect(loglevel=loglevel, connection=connection,
                               save_netrc=save_netrc, depth=depth + 1)
            else:
                raise XnatUtilsUsageError(
                    "Three failed attempts, your account '{}' is now "
                    "blocked for 1 hour. Please contact "
                    "mbi-xnat@monash.edu to reset.".format(user))


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
    return ext.lower()


def get_resource_name(filename):
    ext = extract_extension(filename)
    try:
        return next(k for k, v in resource_exts.items()
                    if v == ext)
    except StopIteration:
        if ext.startswith('.'):
            ext = ext[1:]
        return ext.upper()


def is_regex(ids):
    "Checks to see if string contains special characters"
    if isinstance(ids, basestring):
        ids = [ids]
    return not all(re.match(r'^\w+$', i) for i in ids)


def list_results(mbi_xnat, path, attr):
    try:
        response = mbi_xnat.get_json('/data/archive/' + '/'.join(path))
    except XNATResponseError as e:
        match = re.search(r'\(status (\d+)\)', str(e))
        if match:
            status_code = int(match.group(1))
        else:
            status_code = None
        if status_code == 404:
            raise XnatUtilsLookupError(path)
        else:
            raise XnatUtilsUsageError(str(e))
    if 'ResultSet' in response:
        results = [r[attr] for r in response['ResultSet']['Result']]
    else:
        children = _unpack_response(response, path[0::2])
        results = [r['data_fields'][attr] for r in children]
    return results


def _unpack_response(response_part, types):
    if isinstance(response_part, dict):
        if 'children' in response_part:
            value = response_part['children']
        elif 'items' in response_part:
            value = response_part['items']
            if not types:
                return value  # End recursion
        else:
            assert False
        unpacked = _unpack_response(value, types)
    elif isinstance(response_part, list):
        if len(response_part) == 1:
            item = response_part[0]
        else:
            try:
                item = next(i for i in response_part
                            if i['field'].startswith(types[0]))
            except StopIteration:
                assert False, (
                    "Did not find '{}' in {}, even though search "
                    "returned results")
        unpacked = _unpack_response(item, types[1:])
    else:
        assert False
    return unpacked


def matching_subjects(mbi_xnat, subject_ids):
    if is_regex(subject_ids):
        all_subjects = list_results(mbi_xnat, ['subjects'],
                                    attr='label')
        subjects = [s for s in all_subjects
                    if any(re.match(i + '$', s) for i in subject_ids)]
    elif isinstance(subject_ids, basestring) and '_' not in subject_ids:
        subjects = list_results(mbi_xnat,
                                ['projects', subject_ids, 'subjects'],
                                attr='label')
    else:
        subjects = set()
        for id_ in subject_ids:
            try:
                subjects.update(
                    list_results(mbi_xnat,
                                 ['projects', id_, 'subjects'],
                                 'label'))
            except XnatUtilsLookupError:
                raise XnatUtilsKeyError(
                    id_,
                    "No project named '{}' (that you have access to)"
                    .format(id_))
    return sorted(subjects)


def matching_sessions(mbi_xnat, session_ids, with_scans=None,
                      without_scans=None):
    if isinstance(session_ids, basestring):
        session_ids = [session_ids]
    if isinstance(with_scans, basestring):
        with_scans = [with_scans]
    if isinstance(without_scans, basestring):
        without_scans = [without_scans]
    if is_regex(session_ids):
        all_sessions = list_results(mbi_xnat, ['experiments'],
                                    attr='label')
        sessions = [s for s in all_sessions
                    if any(re.match(i + '$', s) for i in session_ids)]
    else:
        sessions = set()
        for id_ in session_ids:
            if '_' not in id_:
                try:
                    project = mbi_xnat.projects[id_]
                except KeyError:
                    raise XnatUtilsKeyError(
                        id_,
                        "No project named '{}'".format(id_))
                sessions.update(list_results(
                    mbi_xnat, ['projects', project.id, 'experiments'],
                    'label'))
            elif id_ .count('_') == 1:
                try:
                    subject = mbi_xnat.subjects[id_]
                except KeyError:
                    raise XnatUtilsKeyError(
                        id_,
                        "No subject named '{}'".format(id_))
                sessions.update(list_results(
                    mbi_xnat, ['subjects', subject.id, 'experiments'],
                    attr='label'))
            elif id_ .count('_') >= 2:
                try:
                    subject = mbi_xnat.experiments[id_]
                except KeyError:
                    raise XnatUtilsKeyError(
                        id_,
                        "No session named '{}'".format(id_))
                sessions.add(id_)
            else:
                raise XnatUtilsKeyError(
                    id_,
                    "Invalid ID '{}' for listing sessions "
                    .format(id_))
    if with_scans is not None or without_scans is not None:
        sessions = [s for s in sessions if matches_filter(
            mbi_xnat, s, with_scans, without_scans)]
    return sorted(sessions)


def matches_filter(mbi_xnat, session, with_scans, without_scans):
    scans = [(s.type if s.type is not None else s.id)
             for s in mbi_xnat.experiments[session].scans.values()]
    if without_scans is not None:
        for scan in scans:
            if any(re.match(w + '$', scan) for w in without_scans):
                return False
    if with_scans is not None:
        for scan_type in with_scans:
            if not any(re.match(scan_type + '$', s) for s in scans):
                return False
    return True


def matching_scans(session, scan_types):
    return sorted(
        (s for s in session.scans.values() if (
            scan_types is None or
            any(re.match(i + '$',
                         (s.type if s.type is not None else s.id))
                for i in scan_types))),
        key=lambda s: s.type)


def find_executable(name):
    """
    Finds the location of an executable on the system path

    Parameters
    ----------
    name : str
        Name of the executable to search for on the system path
    """
    path = None
    for path_prefix in os.environ['PATH'].split(os.path.pathsep):
        prov_path = os.path.join(path_prefix, name)
        if os.path.exists(prov_path):
            path = prov_path
    return path


class WrappedXnatSession(object):
    """
    Wraps a XnatPy session in a way that it can be used in a 'with'
    context and not disconnect upon exit of the context

    Parameters
    ----------
    xnat_session : xnat.Session
        The XnatPy session to wrap
    """

    def __init__(self, xnat_session):
        self._session = xnat_session

    def __enter__(self):
        return self._session

    def __exit__(self, *args, **kwargs):
        pass


def remove_ignore_errors(path):
    try:
        os.remove(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def print_usage_error(e):
    print('ERROR! {}'.format(e))


def print_response_error(e):
    "Parses a HTML response to extract a clean error message"
    msg = str(e)  # Get message from exception if necessary
    try:
        url = re.match(
            r".* url ([A-Za-z0-9\-\._~:/\?\#\[\]@!\$&'\(\)\*\+,;=]+)",
            msg).group(1)
        status = re.match(r'.*\(status ([0-9]+)\)', msg).group(1)
        explanation = re.search(r'.*<h3>(.*)</h3>', msg).group(1)
        print("ERROR! Response ({}): {} ({})".format(status,
                                                     explanation, url))
    except Exception:
        print(msg)


class DummyContext(object):

    def __exit__(self):
        pass
