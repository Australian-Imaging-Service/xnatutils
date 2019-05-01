from past.builtins import basestring
import os.path
from collections import defaultdict
import subprocess as sp
from functools import reduce
from operator import add
import errno
import re
import shutil
from .base import (
    sanitize_re, skip_resources, resource_exts, find_executable, is_regex)
from xnat.exceptions import XNATResponseError
from .exceptions import (
    XnatUtilsUsageError, XnatUtilsMissingResourceException,
    XnatUtilsSkippedAllSessionsException)
from .base import matching_sessions, matching_scans, connect
import logging


logger = logging.getLogger('xnat-utils')


def get(session, download_dir, scans=None, resource_name=None,
        convert_to=None, converter=None, subject_dirs=False,
        with_scans=None, without_scans=None, strip_name=False,
        skip_downloaded=False, before=None, after=None,
        project_id=None, match_scan_id=True, **kwargs):
    """
    Downloads datasets (e.g. scans) from MBI-XNAT.

    By default all scans in the provided session(s) are downloaded to the
    current working directory unless they are filtered by the provided 'scan'
    kwarg. Both the session name and scan filters can be regular
    expressions, e.g.

        >>> xnatutils.get('MRH017_001_MR.*', '/home/tclose/Downloads',
                          scans='ep2d_diff.*')

    The destination directory can be specified by the 'directory' kwarg.
    Each session will be downloaded to its own folder under the destination
    directory unless the 'subject-dir' kwarg is provided in which case the
    sessions will be grouped under separate subject directories.

    If there are multiple resources for a dataset on MBI-XNAT (unlikely) the
    one to download can be specified using the 'resource_name' kwarg, otherwise
    the only recognised neuroimaging format (e.g. DICOM, NIfTI, MRtrix format).

    DICOM files (ONLY DICOM file) name can be stripped using the kwarg
    'strip_name'. If specified, the final name will be in the format
    000*.dcm.

    The downloaded images can be automatically converted to NIfTI or MRtrix
    formats using dcm2niix or mrconvert (if the tools are installed and on the
    system path) by providing the 'convert_to' kwarg and specifying the
    desired format.

        >>> xnatutils.get('TEST001_001_MR01', '/home/tclose/Downloads',
                          scans='ep2d_diff.*', convert_to='nifti_gz')

    User credentials can be stored in a ~/.netrc file so that they don't need
    to be entered each time a command is run. If a new user provided or netrc
    doesn't exist the tool will ask whether to create a ~/.netrc file with the
    given credentials.

    Parameters
    ----------
    session : str | list(str)
        Name of the sessions to download the dataset from
    target : str
        Path to download the scans to. If not provided the current working
        directory will be used
    scans : str | list(str)
        Name of the scans to include in the download. If not provided all scans
        from the session are downloaded. Multiple scans can be specified
    format : str
        The format of the resource to download. Not required if there is only
        one valid resource for each given dataset e.g. DICOM, which is
        typically the case
    convert_to : str
        Runs a conversion script on the downloaded scans to convert them to a
        given format if required converter : str
        choices=converter_choices,
    converter : str
        The conversion tool to convert the downloaded datasets. Can be one of
        '{}'. If not provided and both converters are available, dcm2niix will
        be used for DICOM->NIFTI conversion and mrconvert for other
        conversions.format ', '.joinconverter_choices
    subject_dirs : bool
         Whether to organise sessions within subject directories to hold the
         sessions in or not
    with_scans : list(str)
        A list of scans that the session is required to have (only applicable
        with datatype='session')
    without_scans : list(str)
        A list of scans that the session is required not to have (only
        applicable with datatype='session')
    strip_name : bool
        Whether to strip the default name of each dicom
         file to have just a number. Ex. 0001.dcm. It will
         work just on DICOM files, not NIFTI.
    use_scan_id: bool
        Use scan IDs rather than series type to identify scans
    skip_downloaded : bool
        Whether to ignore previously downloaded sessions (i.e. if there
        is a directory in the download directory matching the session
        name the session will be skipped)
    before : str
        Only select sessions before this date in %Y-%m-%d format
        (e.g. 2018-02-27)
    after : str
        Only select sessions after this date in %Y-%m-%d format
        (e.g. 2018-02-27)
    project_id : str | None
        The ID of the project to list the sessions from. It should only
        be required if you are attempting to list sessions that are
        shared into secondary projects and you only have access to the
        secondary project
    match_scan_id : bool
        Whether to use the scan ID to match scans with if the scan type
        is None
    user : str
        The user to connect to the server with
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
    """
    # Convert scan string to list of scan strings if only one provided
    if isinstance(scans, basestring):
        scans = [scans]
    if skip_downloaded:
        skip = [d for d in os.listdir(download_dir)
                if os.path.isdir(os.path.join(download_dir, d))]
    else:
        skip = []
    # Quickly skip session if not using regex (and therefore don't need to
    # connect to XNAT
    if all((not is_regex(s) and s in skip) for s in session):
        raise XnatUtilsSkippedAllSessionsException(
            "{} sessions are already present in the download location and "
            "--skip_downloaded was provided".format(session))
    with connect(**kwargs) as login:
        matched_sessions = matching_sessions(
            login, session, with_scans=with_scans,
            without_scans=without_scans, project_id=project_id,
            skip=skip, before=before, after=after)
        downloaded_scans = defaultdict(list)
        for session in matched_sessions:
            for scan in matching_scans(session, scans,
                                       match_id=match_scan_id):
                scan_label = scan.id
                if scan.type is not None:
                    scan_label += '-' + sanitize_re.sub('_', scan.type)
                downloaded = False
                if resource_name is not None:
                    try:
                        downloaded = _download_dataformat(
                            (resource_name.upper()
                             if resource_name != 'secondary'
                             else 'secondary'), download_dir, session.label,
                            scan_label, session, scan, subject_dirs,
                            convert_to, converter, strip_name)
                    except XnatUtilsMissingResourceException:
                        logger.warning(
                            "Did not find '{}' resource for {}:{}, "
                            "skipping".format(
                                resource_name, session.label,
                                scan_label))
                        continue
                else:
                    resource_names = [
                        r.label for r in scan.resources.values()
                        if r.label not in skip_resources]
                    if not resource_names:
                        logger.warning(
                            "No valid scan formats for '{}-{}' in '{}' "
                            "(found '{}')"
                            .format(scan.id, scan.type, session,
                                    "', '".join(scan.resources)))
                    elif len(resource_names) > 1:
                        for scan_resource_name in resource_names:
                            downloaded = _download_dataformat(
                                scan_resource_name, download_dir,
                                session.label, scan_label, session, scan,
                                subject_dirs, convert_to, converter,
                                strip_name, suffix=True)
                    else:
                        downloaded = _download_dataformat(
                            resource_names[0], download_dir, session.label,
                            scan_label, session, scan, subject_dirs,
                            convert_to, converter, strip_name)
                if downloaded:
                    downloaded_scans[session.label].append(scan.type)
        if not downloaded_scans:
            print("No scans matched pattern(s) '{}' in specified "
                  "sessions ({})".format(
                      ("', '".join(scans) if scans is not None else ''),
                      "', '".join(s.label for s in matched_sessions)))
        else:
            num_scans = reduce(add, map(len, downloaded_scans.values()))
            print("Successfully downloaded {} scans from {} session(s)"
                  .format(num_scans, len(matched_sessions)))
        return downloaded_scans


def get_extension(resource_name):
    try:
        ext = resource_exts[resource_name]
    except KeyError:
        ext = ''
    return ext


def _download_dataformat(resource_name, download_dir, session_label,
                         scan_label, exp, scan, subject_dirs, convert_to,
                         converter, strip_name, suffix=False):
    # Get the target location for the downloaded scan
    if subject_dirs:
        parts = session_label.split('_')
        target_dir = os.path.join(download_dir,
                                   '_'.join(parts[:2]), parts[-1])
    else:
        target_dir = os.path.join(download_dir, session_label)
    try:
        os.makedirs(target_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    if convert_to:
        try:
            target_ext = resource_exts[convert_to.upper()]
        except KeyError:
            try:
                target_ext = resource_exts[convert_to]
            except KeyError:
                raise XnatUtilsUsageError(
                    "Cannot convert to unrecognised format '{}'"
                    .format(convert_to))
    else:
        target_ext = get_extension(resource_name)
    target_path = os.path.join(target_dir, scan_label)
    if suffix:
        target_path += '-' + resource_name.lower()
    target_path += target_ext
    tmp_dir = target_path + '.download'
    # Download the scan from XNAT
    print('Downloading {}: {}'.format(exp.label, scan_label))
    try:
        scan.resources[resource_name].download_dir(tmp_dir)
    except KeyError:
        raise XnatUtilsMissingResourceException(
            resource_name, session_label, scan_label)
    except XNATResponseError as e:
        # Check for 404 status
        try:
            status = int(
                re.match('.*\(status (\d+)\).*', str(e)).group(1))
            if status == 404:
                logger.warning(
                    "Did not find any files for resource '{}' in '{}' "
                    "session".format(resource_name, session_label))
                return True
        except Exception:
            pass
        raise e
    # Extract the relevant data from the download dir and move to
    # target location
    src_path = os.path.join(tmp_dir, session_label, 'scans',
                            (scan_label[:-1]
                             if scan_label.endswith('-') else scan_label),
                            'resources', resource_name, 'files')
    fnames = os.listdir(src_path)
    # Link directly to the file if there is only one in the folder
    if len(fnames) == 1:
        src_path = os.path.join(src_path, fnames[0])
    # Convert or move downloaded dir/files to target path
    dcm2niix = find_executable('dcm2niix')
    mrconvert = find_executable('mrconvert')
    if converter == 'dcm2niix':
        if dcm2niix is None:
            raise XnatUtilsUsageError(
                "Selected converter 'dcm2niix' is not available, "
                "please make sure it is installed and on your "
                "path")
        mrconvert = None
    elif converter == 'mrconvert':
        if mrconvert is None:
            raise XnatUtilsUsageError(
                "Selected converter 'mrconvert' is not available, "
                "please make sure it is installed and on your "
                "path")
        dcm2niix = None
    else:
        assert converter is None
    # Clear target path if it exists
    if os.path.exists(target_path):
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        else:
            os.remove(target_path)
    try:
        if (convert_to is None or convert_to.upper() == resource_name):
            # No conversion required
            if strip_name and resource_name in ('DICOM', 'secondary'):
                dcmfiles = sorted(os.listdir(src_path))
                os.mkdir(target_path)
                for f in dcmfiles:
                    dcm_num = int(f.split('-')[-2])
                    file_src_path = os.path.join(src_path, f)
                    file_target_path = os.path.join(
                        target_path, str(dcm_num).zfill(4) + '.dcm')
                    shutil.move(file_src_path, file_target_path)
            else:
                shutil.move(src_path, target_path)
        elif (convert_to in ('nifti', 'nifti_gz') and
              resource_name == 'DICOM' and dcm2niix is not None):
            # convert between dicom and nifti using dcm2niix.
            # mrconvert can do this as well but there have been
            # some problems losing TR from the dicom header.
            zip_opt = 'y' if convert_to == 'nifti_gz' else 'n'
            convert_cmd = '{} -z {} -o "{}" -f "{}" "{}"'.format(
                dcm2niix, zip_opt, target_dir, scan_label,
                src_path)
            sp.check_call(convert_cmd, shell=True)
        elif mrconvert is not None:
            # If dcm2niix format is not installed or another is
            # required use mrconvert instead.
            sp.check_call('{} "{}" "{}"'.format(
                mrconvert, src_path, target_path), shell=True)
        else:
            if (resource_name == 'DICOM' and convert_to in ('nifti',
                                                            'nifti_gz')):
                msg = 'either dcm2niix or '
            raise XnatUtilsUsageError(
                "Please install {} mrconvert to convert between {}"
                "and {} formats".format(
                    msg, resource_name.lower(), convert_to))
    except sp.CalledProcessError as e:
        shutil.move(src_path, os.path.join(
            target_dir,
            scan_label + get_extension(resource_name)))
        logger.warning(
            "Could not convert {}:{} to {} format ({})"
            .format(exp.label, scan.type, convert_to,
                    (e.output.strip() if e.output is not None else '')))
    # Clean up download dir
    shutil.rmtree(tmp_dir)
    return True


def varget(subject_or_session_id, variable, default='', **kwargs):
    """
    Gets the value of a variable (custom or otherwise) of a session or subject
    in a MBI-XNAT project

    User credentials can be stored in a ~/.netrc file so that they don't need
    to be entered each time a command is run. If a new user provided or netrc
    doesn't exist the tool will ask whether to create a ~/.netrc file with the
    given credentials.

    Parameters
    ----------
    subject_or_session_id : str
        Name of subject or session to set the variable of
    variable : str
        Name of the variable to set
    default : str
        Default value if object does not have a value
    user : str
        The user to connect to the server with
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
    """
    with connect(**kwargs) as login:
        # Get XNAT object to set the field of
        if subject_or_session_id.count('_') == 1:
            xnat_obj = login.subjects[subject_or_session_id]
        elif subject_or_session_id.count('_') >= 2:
            xnat_obj = login.experiments[subject_or_session_id]
        else:
            raise XnatUtilsUsageError(
                "Invalid ID '{}' for subject or sessions (must contain one "
                "underscore for subjects and two underscores for sessions)"
                .format(subject_or_session_id))
        # Get value
        try:
            return xnat_obj.fields[variable]
        except KeyError:
            return default
