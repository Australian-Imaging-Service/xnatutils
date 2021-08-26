from past.builtins import basestring
import argparse
import os.path
import pathlib
import re
import errno
from datetime import datetime
import stat
import getpass
from builtins import input
from operator import attrgetter
from netrc import netrc
import xnat
from xnat.exceptions import XNATResponseError
from .exceptions import (
    XnatUtilsLookupError, XnatUtilsUsageError, XnatUtilsKeyError,
    XnatUtilsNoMatchingSessionsException,
    XnatUtilsSkippedAllSessionsException, XnatUtilsError)
import warnings
import logging
from .version_ import __version__

logger = logging.getLogger('xnat-utils')

skip_resources = ['SNAPSHOTS']

resource_exts = {
    'NIFTI': '.nii',
    'NIFTI_GZ': '.nii.gz',
    'PDF': '.pdf',
    'MRTRIX': '.mif',
    'MRTRIX_GZ': '.mif.gz',
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

server_name_re = re.compile(r'(https?://)?([\w\-\.]+).*')


def connect(server=None, user=None, loglevel='ERROR', logger=logger,
            connection=None, use_netrc=True, failures=0, password=None):
    """
    Opens a connection to an XNAT instance

    Parameters
    ----------
    user : str
        The username to connect with. If None then tries to load the
        username from the netrc file (either $HOME/.netrc or $HOME/_netrc on
        Windows OS)
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
    password : str
        Password provided to login. Will be ignored unless 'user' and 'server'
        are not also provided
    Returns
    -------
    connection : xnat.Session
        A XnatPy session
    """
    if connection is not None:
        return WrappedXnatSession(connection)
    netrc_path = os.path.join(os.path.expanduser('~'),
                              ('.netrc' if os.name != 'nt' else '_netrc'))
    netrc_match = False
    # Extract server name from netrc file if 'use_netrc' flag is set and either
    # the server is not provided or it doesn't include the protocol (in which
    # case it will be considered as a potential name fragment)
    if use_netrc and os.path.exists(netrc_path):
        # Read netrc file and return the server addresses saved within it
        with open(netrc_path) as f:
            lines = f.read().split('\n')
        server_names = []
        for line in lines:
            if line.startswith('machine'):
                server_names.append(line.split()[-1])
        if not server_names:
            raise XnatUtilsError(
                "Malformed Netrc file ({}), please delete or flag "
                "use_netrc==False")
        if server is None:
            # Default to the first saved server
            server = server_names[0]
            netrc_match = True
        else:
            # Check whether the provided server name is in the netrc or not
            protocol, dn = server_name_re.match(server).groups()
            # If protocol (e.g. http://) is included in server name, treat as
            # a complete hostname
            if protocol is not None:
                netrc_match = dn in server_names
            # Otherwise treat host name as a potential fragment that can
            # match any of the save servers
            else:
                matches = [s for s in server_names if dn in s]
                if len(matches) == 1:
                    server = matches[0]
                    netrc_match = True
                elif len(matches) > 1:
                    raise XnatUtilsUsageError(
                        "Given server name (or part thereof) '{}' matches "
                        "multiple servers in {} file ('{}')".format(
                            server, netrc_path, "', '".join(matches)))
        saved_servers = netrc(file=netrc_path).hosts
    else:
        saved_servers = {}
    if server is None:
        server = input(
            'XNAT server hostname (e.g. mbi-xnat.erc.monash.edu.au): ')
    if not netrc_match:
        if user is None:
            user = input("XNAT username for '{}': ".format(server))
        if password is None:
            password = getpass.getpass()
    # Prepend default HTTP protcol if protocol is not present
    if server_name_re.match(server).group(1) is None:
        server = 'http://' + server
    kwargs = {'user': user, 'password': password}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            connection = xnat.connect(server, loglevel=loglevel,
                                      logger=logger, **kwargs)
        except ValueError:  # Login failed
            if password is None:
                msg = ("The user access token for {} stored in "
                       "{} has expired!".format(server, netrc_path))
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
            except KeyError:
                pass
            else:
                if saved_servers:
                    write_netrc(netrc_path, saved_servers)
                else:
                    os.remove(netrc_path)
                logger.warning("Removed saved credentials for {}..."
                               .format(server))
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
            if use_netrc and not netrc_match:
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


def matching_subjects(base, subject_ids, project_id=None):
    if isinstance(subject_ids, basestring):
        subject_ids = [subject_ids]
    if project_id is not None:
        try:
            base = base.projects[project_id]
        except KeyError:
            raise XnatUtilsKeyError(
                project_id, "No project named '{}'".format(project_id))
    if not subject_ids:
        if project_id is None:
            raise XnatUtilsUsageError(
                "project_id (\"-p\") must be provided to use empty IDs string")
        subjects = base.subjects.values()
    elif is_regex(subject_ids):
        subjects = [s for s in base.subjects.values()
                    if any(re.match(i + '$', s.label)
                           for i in subject_ids)]
    else:
        subjects = set()
        for id_ in subject_ids:
            try:
                subjects.update(base.projects[id_].subjects.values())
            except XnatUtilsLookupError:
                raise XnatUtilsKeyError(
                    id_,
                    "No project named '{}' (that you have access to)"
                    .format(id_))
    return sorted(subjects, key=attrgetter('label'))


def matching_sessions(login, session_ids, with_scans=None,
                      without_scans=None, skip=(), before=None,
                      after=None, project_id=None, subject_id=None):
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
    skip : list(str)
        Filter out sessions in this list (used to skip downloading the
        same session multiple times)
    before : str | datetime.Date
        Filter out sessions after this date
    after : str | datetime.Date
        Filter out sessions before this date
    project_id : str
        The project ID to retrieve the sessions from, for accounts with
        access to many projects this can considerably boost performance.
    subject_id : str
        The subject ID to retrieve the sessions from. Requires project_id to
        also be supplied
    """
    if isinstance(session_ids, basestring):
        session_ids = [session_ids]
    if isinstance(before, basestring):
        before = datetime.strptime(before, '%Y-%m-%d').date()
    if isinstance(after, basestring):
        after = datetime.strptime(after, '%Y-%m-%d').date()
    if isinstance(with_scans, basestring):
        with_scans = [with_scans]
    elif with_scans is None:
        with_scans = ()
    if isinstance(without_scans, basestring):
        without_scans = [without_scans]
    elif without_scans is None:
        without_scans = ()

    def valid(session):
        if before is not None and session.date > before:
            return False
        if after is not None and session.date < after:
            return False
        if with_scans or without_scans:
            scans = [(s.type if s.type is not None else s.id)
                     for s in session.scans.values()]
            for scan_type in with_scans:
                if not any(re.match(scan_type + '$', s) for s in scans):
                    return False
            for scan_type in without_scans:
                if any(re.match(scan_type + '$', s) for s in scans):
                    return False
        return True

    if project_id is not None:
        try:
            base = login.projects[project_id]
        except KeyError:
            raise XnatUtilsKeyError(
                project_id,
                "No project named '{}'".format(project_id))
        else:
            if subject_id is not None:
                try:
                    base = base.subjects[subject_id]
                except KeyError:
                    raise XnatUtilsKeyError(
                        subject_id,
                        "No subject named '{}' in project '{}'"
                        .format(subject_id, project_id))
    else:
        if subject_id is not None:
            raise XnatUtilsUsageError(
                "Must provide project_id if subject_id is provided ('{}')"
                .format(subject_id))
        base = login
    if not session_ids:
        if project_id is None:
            raise XnatUtilsUsageError(
                "project_id (\"-p\") must be provided to use empty IDs string")
        sessions = set(base.experiments.values())
    elif is_regex(session_ids):
        sessions = set(s for s in base.experiments.values()
                       if any(re.match(i + '$', s.label)
                              for i in session_ids))
    else:
        sessions = set()
        for id_ in session_ids:
            try:
                session = base.experiments[id_]
            except KeyError:
                raise XnatUtilsKeyError(
                    id_, "No session named '{}'".format(id_))
            sessions.add(session)
    filtered = [s for s in sessions if valid(s)]
    if not filtered:
        raise XnatUtilsNoMatchingSessionsException(
            "No accessible sessions matched pattern(s) '{}'"
            .format("', '".join(session_ids)))
    if skip is not None:
        not_skipped = [s for s in filtered if s.label not in skip]
        if not not_skipped:
            raise XnatUtilsSkippedAllSessionsException(
                "All accessible sessions that matched pattern(s) '{}' "
                "were skipped:\n{}"
                .format("', '".join(session_ids),
                        '\n'.join(s.label for s in filtered)))
        filtered = not_skipped
    return sorted(filtered, key=attrgetter('label'))


def matching_scans(session, scan_types, match_id=True):
    def label(scan):
        if scan.type is not None:
            label = scan.type
        elif match_id:
            label = scan.id
        else:
            label = ''
        return label
    matches = session.scans.values()
    if scan_types is not None:
        matches = (s for s in matches if any(
            re.match(i + '$', label(s)) for i in scan_types))
    return sorted(matches, key=label)


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


def print_info_message(e):
    print('INFO: {}'.format(e))


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

    def __exit__(self, *args):
        pass


def base_parser(description):
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawTextHelpFormatter)
    return parser


def add_default_args(parser):
    parser.add_argument('--user', '-u', type=str, default=None,
                        help=("The user to connect to an XNAT instance with"))
    parser.add_argument('--version', '-V', action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument('--server', '-s', type=str, default=None,
                        help=("The XNAT server to connect to. If not "
                              "provided the first server found in the "
                              "~/.netrc file will be used, and if it is "
                              "empty the user will be prompted to enter an "
                              "address for the server. Multiple URLs "
                              "stored in the ~/.netrc file can be "
                              "distinguished by passing part of the URL"))
    parser.add_argument('--loglevel', type=int, default=logging.INFO,
                        help="The logging level to use")
    parser.add_argument('--no_netrc', '-n', action='store_true',
                        default=False,
                        help=("Don't use or store user access tokens in "
                              "~/.netrc. Useful if using a public account"))


def set_logger(level=logging.INFO):
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def split_extension(fpath):
    ext = ''.join(pathlib.Path(fpath).suffixes)
    return fpath[:-len(ext)], ext
