import sys
import os.path
import hashlib
from xnat.exceptions import XNATResponseError
from .base import (
    sanitize_re, illegal_scan_chars_re, get_resource_name,
    session_modality_re, connect, base_parser, add_default_args,
    print_response_error, print_usage_error, print_info_message, set_logger)
from .exceptions import (
    XnatUtilsUsageError, XnatUtilsError, XnatUtilsDigestCheckFailedError,
    XnatUtilsDigestCheckError, XnatUtilsException,
    XnatUtilsNoMatchingSessionsException)

HASH_CHUNK_SIZE = 2 ** 20


def put(session, scan, *filenames, **kwargs):
    """
    Uploads datasets to an XNAT instance project (requires manager privileges for the
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
        Filenames of the dataset(s) to upload to XNAT or a directory containing
        the datasets.
    overwrite : bool
        Allow overwrite of existing dataset
    create_session : bool
        Create the required session on XNAT to upload the the dataset to
    resource_name : str
        The name of the resource (the data format) to
        upload the dataset to. If not provided the format
        will be determined from the file extension (i.e.
        in most cases it won't be necessary to specify
    project_id : str
        The ID of the project to upload the dataset to
    subject_id : str
        The ID of the subject to upload the dataset to
    scan_id : str
        The ID for the scan (defaults to the scan type)
    modality : str
        The modality of the session to upload
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
    # Set defaults for kwargs
    overwrite = kwargs.pop('overwrite', False)
    create_session = kwargs.pop('create_session', False,)
    resource_name = kwargs.pop('resource_name', None)
    project_id = kwargs.pop('project_id', None)
    subject_id = kwargs.pop('subject_id', None)
    scan_id = kwargs.pop('scan_id', None)
    modality = kwargs.pop('modality', None)
    # If a single directory is provided, upload all files in it that
    # don't start with '.'
    if len(filenames) == 1 and isinstance(filenames[0], (list, tuple)):
        filenames = filenames[0]
    if len(filenames) == 1 and os.path.isdir(filenames[0]):
        base_dir = filenames[0]
        filenames = [
            os.path.join(base_dir, f) for f in os.listdir(base_dir)
            if not f.startswith('.')]
    else:
        # Check filenames exist
        if not filenames:
            raise XnatUtilsUsageError(
                "No filenames provided to upload")
        for fname in filenames:
            if not os.path.exists(fname):
                raise XnatUtilsUsageError(
                    "The file to upload, '{}', does not exist"
                    .format(fname))
    if sanitize_re.match(session):
        raise XnatUtilsUsageError(
            "Session '{}' is not a valid session name (must only contain "
            "alpha-numeric characters and underscores)".format(session))
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
    with connect(**kwargs) as login:
        if modality is None:
            match = session_modality_re.match(session)
            if match is None:
                modality = 'MR'  # The default
            else:
                modality = match.group(1)
        if modality == 'MRPT':
            session_cls = login.classes.PetmrSessionData
            scan_cls = login.classes.MrScanData
        else:
            # session_cls = getattr(login.classes,
            #                       modality.capitalize() + 'SessionData')
            # scan_cls = getattr(login.classes,
            #                    modality.capitalize() + 'ScanData')
            # # Other datatypes don't seem to be work by default
            session_cls = login.classes.mrSessionData
            scan_cls = login.classes.mrScanData
        try:
            xsession = login.experiments[session]
        except KeyError:
            if create_session:
                if project_id is None and subject_id is None:
                    try:
                        project_id, subject_id, _ = session.split('_')
                    except ValueError:
                        raise XnatUtilsUsageError(
                            "Must explicitly provide project and subject IDs "
                            "if session ID ({}) scheme doesn't match "
                            "<project>_<subject>_<visit> convention, i.e. "
                            "have exactly 2 underscores".format(session))
                if project_id is None:
                    project_id = session.split('_')[0]
                if subject_id is None:
                    subject_id = '_'.join(session.split('_')[:2])
                try:
                    xproject = login.projects[project_id]
                except KeyError:
                    raise XnatUtilsUsageError(
                        "Cannot create session '{}' as '{}' does not exist "
                        "(or you don't have access to it)".format(session,
                                                                  project_id))
                # Creates a corresponding subject and session if they don't
                # exist
                xsubject = login.classes.SubjectData(label=subject_id,
                                                     parent=xproject)
                xsession = session_cls(
                    label=session, parent=xsubject)
                print("{} session successfully created."
                      .format(xsession.label))
            else:
                raise XnatUtilsNoMatchingSessionsException(
                    "'{}' session does not exist, to automatically create it "
                    "please use '--create_session' option."
                    .format(session))
        xdataset = scan_cls(id=(scan_id if scan_id is not None else scan),
                            type=scan, parent=xsession)
        if overwrite:
            try:
                xdataset.resources[resource_name].delete()
                print("Deleted existing resource at {}:{}/{}".format(
                    session, scan, resource_name))
            except KeyError:
                pass
        resource = xdataset.create_resource(resource_name)
        for fname in filenames:
            resource.upload(fname, os.path.basename(fname))
            print("{} uploaded to {}:{}".format(
                fname, session, scan))
        print("Uploaded files, checking digests...")
        # Check uploaded files checksums
        remote_digests = get_digests(resource)
        for fname in filenames:
            remote_digest = remote_digests[
                os.path.basename(fname).replace(' ', '%20')]
            local_digest = calculate_checksum(fname)
            if local_digest != remote_digest:
                raise XnatUtilsDigestCheckError(
                    "Remote digest does not match local ({} vs {}) "
                    "for {}. Please upload your datasets again"
                    .format(remote_digest, local_digest, fname))
            print("Successfully checked digest for {}".format(
                  fname, session, scan))


def calculate_checksum(fname):
    try:
        file_hash = hashlib.md5()
        with open(fname, 'rb') as f:
            for chunk in iter(lambda: f.read(HASH_CHUNK_SIZE), b''):
                file_hash.update(chunk)
        return file_hash.hexdigest()
    except OSError:
        raise XnatUtilsDigestCheckFailedError(
            "Could not check digest of '{}' ".format(fname))


def get_digests(resource):
    """
    Downloads the MD5 digests associated with the files in a resource.
    These are saved with the downloaded files in the cache and used to
    check if the files have been updated on the server
    """
    result = resource.xnat_session.get(resource.uri + '/files')
    if result.status_code != 200:
        raise XnatUtilsError(
            "Could not download metadata for resource {}. Files "
            "may have been uploaded but cannot check checksums"
            .format(resource.id))
    return dict((r['Name'], r['digest'])
                for r in result.json()['ResultSet']['Result'])


description = """
Uploads datasets to an XNAT instance project (requires manager privileges for the
project).

The format of the uploaded file is guessed from the file extension (recognised
extensions are '.nii', '.nii.gz', '.mif'), the scan entry is created in the
session and if '--create_session' option is passed the subject and session are
created if they are not already present, e.g.

    $ xnat-put TEST001_001_MR01 a_dataset --create_session test.nii.gz

NB: If the scan already exists the '--overwrite' option must be provided to
overwrite it.

User credentials can be stored in a ~/.netrc file so that they don't need to be
entered each time a command is run. If a new user provided or netrc doesn't
exist the tool will ask whether to create a ~/.netrc file with the given
credentials.
"""


def parser():
    parser = base_parser(description)
    parser.add_argument('session', type=str,
                        help="Name of the session to upload the dataset to")
    parser.add_argument('scan', type=str,
                        help="Name for the dataset on XNAT")
    parser.add_argument('filenames', type=str, nargs='+',
                        help="Filename(s) of the dataset to upload to XNAT")
    parser.add_argument('--overwrite', '-o', action='store_true',
                        default=False,
                        help="Allow overwrite of existing dataset")
    parser.add_argument('--create_session', '-c', action='store_true',
                        default=False, help=(
                            "Create the required session on XNAT to upload "
                            "the the dataset to"))
    parser.add_argument('--resource', '-r', type=str, default=None,
                        help=("The name of the resource (the data format) to "
                              "upload the dataset to. If not provided the "
                              "format will be determined from the file "
                              "extension (i.e. in most cases it won't be "
                              "necessary to specify"))
    parser.add_argument('--project_id', '-p',
                        help="Provide the project ID if session doesn't exist")
    parser.add_argument('--subject_id', '-b',
                        help="Provide the subject ID if session doesn't exist")
    parser.add_argument('--scan_id', type=str,
                        help="Provide the scan ID (defaults to the scan type)")
    add_default_args(parser)
    return parser


def cmd(argv=sys.argv[1:]):

    args = parser().parse_args(argv)

    set_logger(args.loglevel)

    try:
        put(args.session, args.scan, *args.filenames, overwrite=args.overwrite,
            create_session=args.create_session, resource_name=args.resource,
            project_id=args.project_id, subject_id=args.subject_id,
            scan_id=args.scan_id, user=args.user, server=args.server,
            use_netrc=(not args.no_netrc))
    except XnatUtilsUsageError as e:
        print_usage_error(e)
    except XNATResponseError as e:
        print_response_error(e)
    except XnatUtilsException as e:
        print_info_message(e)
