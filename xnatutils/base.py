from past.builtins import basestring
import os.path
import re
import errno
import stat
import getpass
from builtins import input
from operator import attrgetter
import netrc
import xnat
from xnat.exceptions import XNATResponseError
from .exceptions import (
    XnatUtilsLookupError, XnatUtilsUsageError, XnatUtilsKeyError)
import warnings
import logging

logger = logging.getLogger('xnat-utils')

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

server_name_re = re.compile(r'(http://|https://)?([\w\-\.]+).*')


def connect(user=None, loglevel='ERROR', connection=None, server=None,
            use_netrc=True, failures=0):
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
    server : str | int | None
        URI of the XNAT server to connect to. If not provided connect
        will look inside the ~/.netrc file to get a list of saved
        servers. If there is more than one, then they can be selected
        by passing an index corresponding to the order they are listed
        in the .netrc
    use_netrc : bool
        Whether to load and save user credentials from netrc file
        located at $HOME/.netrc
    Returns
    -------
    connection : xnat.Session
        A XnatPy session
    """
    if connection is not None:
        return WrappedXnatSession(connection)
    netrc_path = os.path.join(os.path.expanduser('~'), '.netrc')
    save_netrc = False
    password = None
    if use_netrc:
        try:
            saved_servers = netrc.netrc(netrc_path).hosts
        except Exception:
            saved_servers = {}
    else:
        saved_servers = {}
    if server is None and saved_servers:
        # Get default server from first line in netrc file
        with open(netrc_path) as f:
            server = f.readline().split()[-1]
    else:
        matches = [s for s in saved_servers if server in s]
        if len(matches) == 1:
            server = matches[0]
        elif len(matches) > 1:
            raise XnatUtilsUsageError(
                "Given server name (or part thereof) '{}' matches "
                "multiple servers in ~/.netrc file ('{}')".format(
                    server, "', '".join(matches)))
        else:
            if server is None:
                server = input('XNAT server URL: ')
            # A little hack to avoid issues with the redirection
            # from monash.edu to monash.edu.au
            if server.endswith('monash.edu'):
                server += '.au'
            if user is None:
                user = input("XNAT username for '{}': ".format(server))
            password = getpass.getpass()
            if use_netrc:
                save_netrc = True
    # Ensure that the protocol is added to the server URL
    # FIXME: Should be able to handle http:// protocols as well.
    if server_name_re.match(server).group(1) is None:
        server = 'https://' + server
    kwargs = {'user': user, 'password': password}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            connection = xnat.connect(server, loglevel=loglevel,
                                      **kwargs)
        except ValueError:  # Login failed
            if password is None:
                msg = ("The user access token for {} stored in "
                       "~/.netrc has expired!".format(server))
            else:
                msg = ("Incorrect user credentials for {}!"
                       .format(server))
            msg += (" One failed login, note that your account will be "
                    "automatically blocked for 1 hour after 3 failed "
                    "login attempts. Please contact your administrator "
                    "to have it reset.")
            logger.warning(msg)
            try:
                del saved_servers[server_name_re.match(server).group(2)]
                write_netrc(netrc_path, saved_servers)
                logger.warning("Removed saved credentials for {}..."
                               .format(server))
            except KeyError:
                pass
            if failures < 3:
                return connect(server=server, loglevel=loglevel,
                               connection=connection,
                               use_netrc=use_netrc,
                               failures=failures + 1)
            else:
                raise XnatUtilsUsageError(
                    "Three failed attempts, your account '{}' is now "
                    "blocked for 1 hour. Please contact "
                    "your administrator to reset.".format(user))
        else:
            if save_netrc:
                alias, secret = connection.services.issue_token()
                # Strip protocol (i.e. https://) from server
                server_name = server_name_re.match(server).group(2)
                saved_servers[server_name] = (alias, None, secret)
                write_netrc(netrc_path, saved_servers)
                logger.warning(
                    "Saved access token for {} in {}. If this "
                    "isn't desirable (i.e. you don't want someone to be"
                    " able to access your XNAT account from this "
                    "computer account) please delete the file. "
                    "To prevent this from happening in the future pass "
                    "the '--no_netrc' or '-n' option".format(
                        server, netrc_path))
    return connection


def write_netrc(netrc_path, servers):
    """
    Writes servers back to file
    """
    with open(netrc_path, 'w') as f:
        for server, (user, _, password) in servers.items():
            f.write('machine ' + server + '\n')
            f.write('user ' + user + '\n')
            f.write('password ' + password + '\n')
    os.chmod(netrc_path, stat.S_IRUSR | stat.S_IWUSR)


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


def list_results(login, path, attr):
    try:
        response = login.get_json('/data/archive/' + '/'.join(path))
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


def matching_subjects(login, subject_ids):
    if is_regex(subject_ids):
        subjects = [s for s in login.subjects.values()
                    if any(re.match(i + '$', s.label)
                           for i in subject_ids)]
    else:
        subjects = set()
        for id_ in subject_ids:
            try:
                subjects.update(login.projects[id_].subjects.values())
            except XnatUtilsLookupError:
                raise XnatUtilsKeyError(
                    id_,
                    "No project named '{}' (that you have access to)"
                    .format(id_))
    return sorted(subjects, key=attrgetter('label'))


def matching_sessions(login, session_ids, with_scans=None,
                      without_scans=None, project_id=None, skip=()):
    """
    Parameters
    ----------
    login : xnat.Session
        The XNAT session  object (i.e. wrapper around requests.Session
        object representing a user login session not an imaging session)
    session_ids : str | list(str)
        A regex or name, or list of, with which to match the sessions
        with. Can also be a project (no underscores) or subject (exactly
        one underscore) name.
    with_scans : str | list(str)
        Regex(es) with which to match scans within sessions. Only
        sessions containing these scans will be matched
    without_scans : str | list(str)
        Regex(es) with which to match scans within sessions. Only
        sessions NOT containing these scans will be matched
    project_id : str
        The project ID to set the sessions to. Should only be required
        for projects containing sessions shared from other projects
    skip : list(str)
        Names of sessions to skip (used to skip downloading the same
        session multiple times)
    """
    if isinstance(session_ids, basestring):
        session_ids = [session_ids]
    if is_regex(session_ids):
        sessions = [s for s in login.experiments.values()
                    if any(re.match(i + '$', s.label)
                           for i in session_ids)]
    else:
        sessions = set()
        if project_id is not None:
            try:
                base = login.projects[project_id]
            except KeyError:
                raise XnatUtilsKeyError(
                    project_id,
                    "No project named '{}'".format(project_id))
        else:
            base = login
        for id_ in session_ids:
            if '_' not in id_:
                if project_id is not None:
                    if project_id == id_:
                        project = base
                    else:
                        raise XnatUtilsUsageError(
                            "Provided ID ('{}'), which is presumed to be "
                            "a project ID does not match explicit project "
                            "ID ('{}')".format(id_, project_id))
                else:
                    try:
                        project = login.projects[id_]
                    except KeyError:
                        raise XnatUtilsKeyError(
                            id_,
                            "No project named '{}'".format(id_))
                    project_id = id_
                sessions.update(project.experiments.values())
            elif id_ .count('_') == 1:
                try:
                    subject = base.subjects[id_]
                except KeyError:
                    raise XnatUtilsKeyError(
                        id_,
                        "No subject named '{}'".format(id_))
                if project_id is not None:
                    posthoc_project_id_set(subject.fulldata, project_id)
                sessions.update(subject.experiments.values())
            elif id_ .count('_') >= 2:
                try:
                    session = base.experiments[id_]
                except KeyError:
                    raise XnatUtilsKeyError(
                        id_,
                        "No session named '{}'".format(id_))
                sessions.add(session)
            else:
                raise XnatUtilsKeyError(
                    id_,
                    "Invalid ID '{}' for listing sessions "
                    .format(id_))
    if project_id is not None:
        for session in sessions:
            posthoc_project_id_set(session.fulldata, project_id)
    if skip:
        sessions = [s for s in sessions if s.label not in skip]
    if with_scans is not None or without_scans is not None:
        sessions = [s for s in sessions if matches_filter(
            login, s, with_scans, without_scans)]
    return sorted(sessions, key=attrgetter('label'))


def matches_filter(session, with_scans, without_scans):
    if isinstance(with_scans, basestring):
        with_scans = [with_scans]
    if isinstance(without_scans, basestring):
        without_scans = [without_scans]
    scans = [(s.type if s.type is not None else s.id)
             for s in session.scans.values()]
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
        key=lambda s: s.type if s.type is not None else s.id)


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


def posthoc_project_id_set(fulldata, project_id):
    """
    Sets the project_id of the fulldata dictionary tree. Used when
    dealing with shared projects where the child
    project-ids will initially be set to the project they were shared
    from.
    """
    try:
        fulldata['data_fields']['project'] = project_id
    except KeyError:
        return
    for child in fulldata['children']:
        posthoc_project_id_set(child, project_id)


class DummyContext(object):

    def __exit__(self):
        pass
