import os.path
import hashlib
from .exceptions import (
    XnatUtilsUsageError, XnatUtilsError, XnatUtilsDigestCheckFailedError,
    XnatUtilsDigestCheckError)
from .base import (
    sanitize_re, illegal_scan_chars_re, get_resource_name,
    session_modality_re, connect)


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
    if sanitize_re.match(session) or session.count('_') < 2:
        raise XnatUtilsUsageError(
            "Session '{}' is not a valid session name (must only contain "
            "alpha-numeric characters and at least two underscores"
            .format(session))
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
        match = session_modality_re.match(session)
        if match is None or match.group(1) == 'MR':
            session_cls = login.classes.MrSessionData
            scan_cls = login.classes.MrScanData
        elif match.group(1) == 'MRPT':
            session_cls = login.classes.PetmrSessionData
            scan_cls = login.classes.MrScanData
        elif match.group(1) == 'EEG':
            session_cls = login.classes.EegSessionData
            scan_cls = login.classes.EegScanData  # Not used atm
        else:
            raise XnatUtilsUsageError(
                "Did not recognised session modality of '{}'"
                .format(session))
        # FIXME: Override datatype to MRScan as EEGScan doesn't work atm
        scan_cls = login.classes.MrScanData
        try:
            xsession = login.experiments[session]
        except KeyError:
            if create_session:
                project_id = session.split('_')[0]
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
                raise XnatUtilsUsageError(
                    "'{}' session does not exist, to automatically create it "
                    "please use '--create_session' option."
                    .format(session))
        xdataset = scan_cls(type=scan, parent=xsession)
        if overwrite:
            try:
                xdataset.resources[resource_name].delete()
                print("Deleted existing dataset at {}:{}".format(
                    session, scan))
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
            with open(fname, 'rb') as f:
                try:
                    local_digest = hashlib.md5(f.read()).hexdigest()
                except OSError:
                    raise XnatUtilsDigestCheckFailedError(
                        "Could not check digest of '{}' "
                        "(reference '{}'), possibly file too large"
                        .format(fname, remote_digest))
            if local_digest != remote_digest:
                raise XnatUtilsDigestCheckError(
                    "Remote digest does not match local ({} vs {}) "
                    "for {}. Please upload your datasets again"
                    .format(remote_digest, local_digest, fname))
            print("Successfully checked digest for {}".format(
                fname, session, scan))


def varput(subject_or_session_id, variable, value, **kwargs):
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
                "underscore  for subjects and two underscores for sessions)"
                .format(subject_or_session_id))
        # Set value
        xnat_obj.fields[variable] = value


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
