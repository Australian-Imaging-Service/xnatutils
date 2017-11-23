from builtins import basestring
import os.path
import re
import subprocess as sp
import errno
import shutil
import stat
import getpass
import xnat
from xnat.exceptions import XNATResponseError
import warnings
import logging

logger = logging.getLogger('XNAT-Utils')

__version__ = '0.2.8'

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


class XnatUtilsUsageError(Exception):
    pass


class XnatUtilsLookupError(XnatUtilsUsageError):

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return ("Could not find asset corresponding to '{}' (please make sure"
                " you have access to it if it exists)".format(self.path))


def get(session, download_dir, scans=None, resource_name=None,
        convert_to=None, converter=None, subject_dirs=False,
        with_scans=None, without_scans=None, user=None,
        strip_name=False, connection=None, loglevel='ERROR'):
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
    user : str
        The user to connect to MBI-XNAT with
    strip_name : bool
        Whether to strip the default name of each dicom
         file to have just a number. Ex. 0001.dcm. It will
         work just on DICOM files, not NIFTI.
    connection : xnat.Session
        A XnatPy session to reuse for the command instead of creating a new one
    loglevel : str
        The logging level used for the xnat connection
    """
    # Convert scan string to list of scan strings if only one provided
    if isinstance(scans, basestring):
        scans = [scans]
    with connect(user, loglevel=loglevel, connection=connection) as mbi_xnat:
        matched_sessions = matching_sessions(mbi_xnat, session,
                                             with_scans=with_scans,
                                             without_scans=without_scans)
        if not matched_sessions:
            raise XnatUtilsUsageError(
                "No accessible sessions matched pattern(s) '{}'"
                .format("', '".join(session)))
        num_scans = 0
        for session_label in matched_sessions:
            exp = mbi_xnat.experiments[session_label]
            for scan in matching_scans(exp, scans):
                scan_name = sanitize_re.sub('_', scan.type)
                scan_label = scan.id + '-' + scan_name
                if resource_name is not None:
                    _download_dataformat(
                        (resource_name.upper() if resource_name != 'secondary'
                         else 'secondary'), download_dir, session_label,
                        scan_label, exp, scan, subject_dirs,
                        convert_to, converter, strip_name)
                    num_scans += 1
                else:
                    resource_names = [
                        r.label for r in scan.resources.itervalues()
                        if r.label not in skip_resources]
                    if not resource_names:
                        logger.warning(
                            "No valid scan formats for '{}-{}' in '{}' "
                            "(found '{}')"
                            .format(scan.id, scan.type, session,
                                    "', '".join(scan.resources)))
                    elif len(resource_names) > 1:
                        for scan_resource_name in resource_names:
                            _download_dataformat(
                                scan_resource_name, download_dir,
                                session_label, scan_label, exp, scan,
                                subject_dirs, convert_to, converter,
                                strip_name, suffix=True)
                            num_scans += 1
                    else:
                        _download_dataformat(
                            resource_names[0], download_dir, session_label,
                            scan_label, exp, scan, subject_dirs,
                            convert_to, converter, strip_name)
                        num_scans += 1
        if not num_scans:
            print ("No scans matched pattern(s) '{}' in specified sessions ({}"
                   ")".format(("', '".join(scans) if scans is not None
                               else ''), "', '".join(matched_sessions)))
        else:
            print "Successfully downloaded {} scans from {} sessions".format(
                num_scans, len(matched_sessions))


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
    print 'Downloading {}: {}'.format(exp.label, scan_label)
    scan.resources[resource_name].download_dir(tmp_dir)
    # Extract the relevant data from the download dir and move to
    # target location
    src_path = os.path.join(tmp_dir, session_label, 'scans',
                            scan_label, 'resources',
                            resource_name, 'files')
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
            print convert_cmd
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
        print ("WARNING! Could not convert {}:{} to {} format ({})"
               .format(exp.label, scan.type, convert_to,
                       (e.output.strip() if e.output is not None
                        else '')))
    # Clean up download dir
    shutil.rmtree(tmp_dir)


def ls(xnat_id, datatype=None, with_scans=None, without_scans=None, user=None,
       connection=None, loglevel='ERROR'):
    """
    Displays available projects, subjects, sessions and scans from MBI-XNAT.

    The datatype listed (i.e. 'project', 'subject', 'session' or 'scan') is
    assumed to be the next level down the data tree if not explicitly provided
    (i.e. subjects if a project ID is provided, sessions if a subject ID is
    provided, etc...) but can be explicitly provided via the '--datatype'
    option. For example, to list all sessions within the MRH001 project

        >>> xnatutils.ls('MRH001', datatype='session')

    Scans listed over multiple sessions will be added to a set, so the list
    returned is the list of unique scan types within the specified sessions. If
    no arguments are provided the projects the user has access to will be
    listed.

    Multiple subject or session IDs can be provided as a sequence or using
    regular expression syntax (e.g. MRH000_.*_MR01 will match the first session
    for each subject in project MRH000). Note that if regular expressions are
    used then an explicit datatype must also be provided.

    User credentials can be stored in a ~/.netrc file so that they don't need
    to be entered each time a command is run. If a new user provided or netrc
    doesn't exist the tool will ask whether to create a ~/.netrc file with the
    given credentials.

    Parameters
    ----------
    xnat_id : str
        The ID of the project/subject/session to list from
    datatype : str
        The data type to list, can be one of 'project', 'subject', 'session'
        or 'scan'
    user : str
        The user to connect to MBI-XNAT with
    with_scans : list(str)
        A list of scans that the session is required to have (only applicable
        with datatype='session')
    without_scans : list(str)
        A list of scans that the session is required not to have (only
        applicable with datatype='session')
    connection : xnat.Session
        A XnatPy session to reuse for the command instead of creating a new one
    loglevel : str
        The logging level used for the xnat connection
    """
    if datatype is None:
        if not xnat_id:
            datatype = 'project'
        else:
            if is_regex(xnat_id):
                raise XnatUtilsUsageError(
                    "'datatype' option must be provided if using regular "
                    "expression id, '{}' (i.e. one with non alphanumeric + '_'"
                    " characters in it)".format("', '".join(xnat_id)))
            num_underscores = max(i.count('_') for i in xnat_id)
            if num_underscores == 0:
                datatype = 'subject'
            elif num_underscores == 1:
                datatype = 'session'
            elif num_underscores == 2:
                datatype = 'scan'
            else:
                raise XnatUtilsUsageError(
                    "Invalid ID(s) provided '{}'".format(
                        "', '".join(i for i in xnat_id if i.count('_') > 2)))
    else:
        datatype = datatype
        if datatype == 'project':
            if xnat_id:
                raise XnatUtilsUsageError(
                    "IDs should not be provided for 'project' datatypes ('{}')"
                    .format("', '".join(xnat_id)))
        else:
            if not xnat_id:
                raise XnatUtilsUsageError(
                    "IDs must be provided for '{}' datatype listings"
                    .format(datatype))

    if datatype != 'session' and (with_scans is not None or
                                  without_scans is not None):
        raise XnatUtilsUsageError(
            "'with_scans' and 'without_scans' options are only applicable when"
            "datatype='session'")

    with connect(user, loglevel=loglevel, connection=connection) as mbi_xnat:
        if datatype == 'project':
            return sorted(list_results(mbi_xnat, ['projects'], 'ID'))
        elif datatype == 'subject':
            return sorted(matching_subjects(mbi_xnat, xnat_id))
        elif datatype == 'session':
            return sorted(matching_sessions(mbi_xnat, xnat_id,
                                            with_scans=with_scans,
                                            without_scans=without_scans))
        elif datatype == 'scan':
            if not is_regex(xnat_id) and len(xnat_id) == 1:
                exp = mbi_xnat.experiments[xnat_id[0]]
                return sorted(list_results(
                    mbi_xnat, ['experiments', exp.id, 'scans'], 'type'))
            else:
                scans = set()
                for session in matching_sessions(mbi_xnat, xnat_id):
                    exp = mbi_xnat.experiments[session]
                    session_scans = set(list_results(
                        mbi_xnat, ['experiments', exp.id, 'scans'], 'type'))
                    scans |= session_scans
                return sorted(scans)
        else:
            assert False


def put(session, scan, *filenames, **kwargs):
    """
    Uploads datasets to a MBI-XNAT project (requires manager privileges for the
    project).

    The format of the uploaded file is guessed from the file extension
    (recognised extensions are '.nii', '.nii.gz', '.mif'), the scan entry is
    created in the session and if 'create_session' kwarg is True the
    subject and session are created if they are not already present, e.g.

        >>> xnatutils.put('TEST001_001_MR01', 'a_dataset', ['test.nii.gz'],
                          create_session=True)

    NB: If the scan already exists the 'overwrite' kwarg must be provided to
    overwrite it.

    User credentials can be stored in a ~/.netrc file so that they don't need
    to be entered each time a command is run. If a new user provided or netrc
    doesn't exist the tool will ask whether to create a ~/.netrc file with the
    given credentials.

    Parameters
    ----------
    session : str
        Name of the session to upload the dataset to
    scan : str
        Name for the dataset on XNAT
    filenames : list(str)
        Filenames of the dataset(s) to upload to XNAT
    overwrite : bool
        Allow overwrite of existing dataset
    create_session : bool
        Create the required session on XNAT to upload the the dataset to
    resource_name : str
        The name of the resource (the data format) to
        upload the dataset to. If not provided the format
        will be determined from the file extension (i.e.
        in most cases it won't be necessary to specify
    user : str
        The user to connect to MBI-XNAT with
    connection : xnat.Session
        A XnatPy session to reuse for the command instead of creating a new one
    loglevel : str
        The logging level used for the xnat connection
    """
    # Set defaults for kwargs
    overwrite = kwargs.pop('overwrite', False)
    create_session = kwargs.pop('create_session', False,)
    resource_name = kwargs.pop('resource_name', None)
    user = kwargs.pop('user', None)
    connection = kwargs.pop('connection', None)
    loglevel = kwargs.pop('loglevel', 'ERROR')
    # Check filenames exist
    if not filenames:
        raise XnatUtilsUsageError(
            "No filenames provided to upload")
    for fname in filenames:
        if not os.path.exists(fname):
            raise XnatUtilsUsageError(
                "The file to upload, '{}', does not exist".format(fname))
    if sanitize_re.match(session) or session.count('_') < 2:
        raise XnatUtilsUsageError(
            "Session '{}' is not a valid session name (must only contain "
            "alpha-numeric characters and at least two underscores")
    if illegal_scan_chars_re.search(scan) is not None:
        raise XnatUtilsUsageError(
            "Scan name '{}' contains illegal characters".format(scan))

    if resource_name is None:
        if len(filenames) == 1:
            resource_name = get_resource_name(filenames[0])
        else:
            raise XnatUtilsUsageError(
                "'resource_name' option needs to be provided when uploading "
                "multiple files")
    else:
        resource_name = resource_name.upper()
    with connect(user, loglevel=loglevel, connection=connection) as mbi_xnat:
        match = session_modality_re.match(session)
        if match is None or match.group(1) == 'MR':
            session_cls = mbi_xnat.classes.MrSessionData
            scan_cls = mbi_xnat.classes.MrScanData
        elif match.group(1) == 'MRPT':
            session_cls = mbi_xnat.classes.PetMrSessionData
            scan_cls = mbi_xnat.classes.MrScanData
        elif match.group(1) == 'EEG':
            session_cls = mbi_xnat.classes.EegSessionData
            scan_cls = mbi_xnat.classes.EegScanData
        else:
            raise XnatUtilsUsageError(
                "Unrecognised session modality '{}'".format(modality))
        # Override datatype to MRScan as EEGScan doesn't work currently
        scan_cls = mbi_xnat.classes.MrScanData
        try:
            xsession = mbi_xnat.experiments[session]
        except KeyError:
            if create_session:
                project_id = session.split('_')[0]
                subject_id = '_'.join(session.split('_')[:2])
                try:
                    xproject = mbi_xnat.projects[project_id]
                except KeyError:
                    raise XnatUtilsUsageError(
                        "Cannot create session '{}' as '{}' does not exist "
                        "(or you don't have access to it)".format(session,
                                                                  project_id))
                # Creates a corresponding subject and session if they don't
                # exist
                xsubject = mbi_xnat.classes.SubjectData(label=subject_id,
                                                        parent=xproject)
                xsession = session_cls(
                    label=session, parent=xsubject)
                print "{} session successfully created.".format(xsession.label)
            else:
                raise XnatUtilsUsageError(
                    "'{}' session does not exist, to automatically create it "
                    "please use '--create_session' option."
                    .format(session))
        xdataset = scan_cls(type=scan, parent=xsession)
        if overwrite:
            try:
                xdataset.resources[resource_name].delete()
                print "Deleted existing dataset at {}:{}".format(
                    session, scan)
            except KeyError:
                pass
        resource = xdataset.create_resource(resource_name)
        for fname in filenames:
            resource.upload(fname, os.path.basename(fname))
            print "{} successfully uploaded to {}:{}".format(
                fname, session, scan)


def rename(session_name, new_session_name, user=None, connection=None,
           loglevel='ERROR'):
    """
    Renames a session from the command line (if there has been a mistake in its
    name for example).

        >>> xnatutils.rename('MMA003_001_MR01', 'MMA003_001_MRPT01')

    Parameters
    ----------
    session_name : str
        Name of the session to rename
    new_session_name : str
        The new name of the session
    user : str
        The user to connect to MBI-XNAT with
    connection : xnat.Session
        A XnatPy session to reuse for the command instead of creating a new one
    loglevel : str
        The logging level used for the xnat connection
    """
    with connect(user, loglevel=loglevel, connection=connection) as mbi_xnat:
        try:
            session = mbi_xnat.experiments[session_name]
        except KeyError:
            raise XnatUtilsUsageError(
                "No session named '{}'".format(session_name))
        mbi_xnat.put(session.uri + '?label={}'.format(new_session_name))
    print "Successfully renamed '{}' to '{}'".format(session_name,
                                                     new_session_name)


def varget(subject_or_session_id, variable, default='', user=None,
           connection=None, loglevel='ERROR'):
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
        The user to connect to MBI-XNAT with
    connection : xnat.Session
        A XnatPy session to reuse for the command instead of creating a new one
    loglevel : str
        The logging level used for the xnat connection
    """
    with connect(user, loglevel=loglevel, connection=connection) as mbi_xnat:
        # Get XNAT object to set the field of
        if subject_or_session_id.count('_') == 1:
            xnat_obj = mbi_xnat.subjects[subject_or_session_id]
        elif subject_or_session_id.count('_') >= 2:
            xnat_obj = mbi_xnat.experiments[subject_or_session_id]
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


def varput(subject_or_session_id, variable, value, user=None, connection=None,
           loglevel='ERROR'):
    """
    Sets variables (custom or otherwise) of a session or subject in a MBI-XNAT
    project

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
    value : str
        Value to set the variable to
    user : str
        The user to connect to MBI-XNAT with
    connection : xnat.Session
        A XnatPy session to reuse for the command instead of creating a new one
    loglevel : str
        The logging level used for the xnat connection
    """
    with connect(user, loglevel=loglevel, connection=connection) as mbi_xnat:
        # Get XNAT object to set the field of
        if subject_or_session_id.count('_') == 1:
            xnat_obj = mbi_xnat.subjects[subject_or_session_id]
        elif subject_or_session_id.count('_') >= 2:
            xnat_obj = mbi_xnat.experiments[subject_or_session_id]
        else:
            raise XnatUtilsUsageError(
                "Invalid ID '{}' for subject or sessions (must contain one "
                "underscore  for subjects and two underscores for sessions)"
                .format(subject_or_session_id))
        # Set value
        xnat_obj.fields[variable] = value


def connect(user=None, loglevel='ERROR', connection=None, depth=0,
            save_netrc=True):
    """
    Opens a connection to MBI-XNAT

    Parameters
    ----------
    user : str
        The username to connect with. If None then tries to load the username
        from the $HOME/.netrc file
    loglevel : str
        The logging level to display. In order of increasing verbosity ERROR,
        WARNING, INFO, DEBUG.
    connection : xnat.Session
        An existing XnatPy session that is to be reused instead of creating
        a new session. The session is wrapped in a dummy class that disables
        the disconnection on exit, to allow the method to be nested in a
        wider connection context (i.e. reuse the same connection between
        commands).
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
            user = raw_input('authcate/username: ')
        password = getpass.getpass()
        if save_netrc:
            save_netrc_response = raw_input(
                "Would you like to save this username/password in your "
                "~/.netrc (with 600 permissions) [y/N]: ")
            if save_netrc_response.lower() in ('y', 'yes'):
                with open(netrc_path, 'w') as f:
                    f.write(
                        "machine {}\n".format(MBI_XNAT_SERVER.split('/')[-1]) +
                        "user {}\n".format(user) +
                        "password {}\n".format(password))
                os.chmod(netrc_path, stat.S_IRUSR | stat.S_IWUSR)
                print ("MBI-XNAT username and password for user '{}' saved in "
                       "{}".format(user, os.path.join(os.path.expanduser('~'),
                                                      '.netrc')))
                saved_netrc = True
    else:
        saved_netrc = 'existing'
    kwargs = ({'user': user, 'password': password}
              if not os.path.exists(netrc_path) else {})
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            return xnat.connect(MBI_XNAT_SERVER, loglevel=loglevel,
                                **kwargs)
        except ValueError:  # Login failed
            if saved_netrc:
                remove_ignore_errors(netrc_path)
                if saved_netrc == 'existing':
                    print("Removing saved credentials...")
            print("Your account will be blocked for 1 hour after 3 failed "
                  "login attempts. Please contact mbi-xnat@monash.edu "
                  "to have it reset.")
            if depth < 3:
                return connect(loglevel=loglevel, connection=connection,
                               save_netrc=save_netrc, depth=depth + 1)
            else:
                raise XnatUtilsUsageError(
                    "Three failed attempts, your account '{}' is now blocked "
                    "for 1 hour. Please contact mbi-xnat@monash.edu to reset."
                    .format(user))


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
        return next(k for k, v in resource_exts.iteritems()
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
                    "Did not find '{}' in {}, even though search returned"
                    "results")
        unpacked = _unpack_response(item, types[1:])
    else:
        assert False
    return unpacked


def matching_subjects(mbi_xnat, subject_ids):
    if is_regex(subject_ids):
        all_subjects = list_results(mbi_xnat, ['subjects'], attr='label')
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
                                 ['projects', id_, 'subjects'], 'label'))
            except XnatUtilsLookupError:
                raise XnatUtilsUsageError(
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
        all_sessions = list_results(mbi_xnat, ['experiments'], attr='label')
        sessions = [s for s in all_sessions
                    if any(re.match(i + '$', s) for i in session_ids)]
    else:
        sessions = set()
        for id_ in session_ids:
            if '_' not in id_:
                try:
                    project = mbi_xnat.projects[id_]
                except KeyError:
                    raise XnatUtilsUsageError(
                        "No project named '{}'".format(id_))
                sessions.update(list_results(
                    mbi_xnat, ['projects', project.id, 'experiments'],
                    'label'))
            elif id_ .count('_') == 1:
                try:
                    subject = mbi_xnat.subjects[id_]
                except KeyError:
                    raise XnatUtilsUsageError(
                        "No subject named '{}'".format(id_))
                sessions.update(list_results(
                    mbi_xnat, ['subjects', subject.id, 'experiments'],
                    attr='label'))
            elif id_ .count('_') >= 2:
                sessions.add(id_)
            else:
                raise XnatUtilsUsageError(
                    "Invalid ID '{}' for listing sessions "
                    .format(id_))
    if with_scans is not None or without_scans is not None:
        sessions = [s for s in sessions if matches_filter(
            mbi_xnat, s, with_scans, without_scans)]
    return sorted(sessions)


def matches_filter(mbi_xnat, session, with_scans, without_scans):
    scans = [s.type for s in mbi_xnat.experiments[session].scans.itervalues()]
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
    return sorted(s for s in session.scans.itervalues() if (
        scan_types is None or
        any(re.match(i + '$', s.type) for i in scan_types)))


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
    Wraps a XnatPy session in a way that it can be used in a 'with' context
    and not disconnect upon exit of the context

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


class DummyContext(object):

    def __exit__(self):
        pass
