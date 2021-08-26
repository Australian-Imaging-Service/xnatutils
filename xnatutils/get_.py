import sys
import os.path
import pathlib
from collections import defaultdict
import subprocess as sp
from glob import glob
from functools import reduce
from operator import add
import errno
import re
import logging
import shutil
from xml.etree import ElementTree
from xnat.exceptions import XNATResponseError
from .base import (
    sanitize_re, skip_resources, resource_exts, find_executable, is_regex,
    base_parser, add_default_args, print_response_error, print_usage_error,
    print_info_message, set_logger, matching_sessions, matching_scans,
    connect, split_extension)
from .exceptions import (
    XnatUtilsUsageError, XnatUtilsMissingResourceException,
    XnatUtilsSkippedAllSessionsException, XnatUtilsException)



logger = logging.getLogger('xnat-utils')


conv_choices = ['nifti', 'nifti_gz', 'mrtrix', 'mrtrix_gz']
converter_choices = ('dcm2niix', 'mrconvert')


def get(session, download_dir, scans=None, resource_name=None,
        convert_to=None, converter=None, subject_dirs=False,
        with_scans=None, without_scans=None, strip_name=False,
        skip_downloaded=False, before=None, after=None,
        project_id=None, subject_id=None, match_scan_id=True, **kwargs):
    """
    Downloads datasets (e.g. scans) from XNAT.

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

    If there are multiple resources for a dataset on an XNAT instance (unlikely) the
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
    download_dir : str
        Path to download the scans to. If not provided the current working
        directory will be used
    scans : str | list(str)
        Name of the scans to include in the download. If not provided all scans
        from the session are downloaded. Multiple scans can be specified
    resource_name : str
        The name of the resource to download. Not required if there is only
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
        The ID of the project to get the sessions from.
    subject_id : str | None
        The ID of the subject to get the sessions from. Requires project_id
        also be provided
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
    if isinstance(scans, str):
        scans = [scans]
    if skip_downloaded:
        skip = [d for d in os.listdir(download_dir)
                if os.path.isdir(os.path.join(download_dir, d))]
    else:
        skip = []
    # Quickly skip session if not using regex (and therefore don't need to
    # connect to XNAT
    if session and all((not is_regex(s) and s in skip) for s in session):
        raise XnatUtilsSkippedAllSessionsException(
            "{} sessions are already present in the download location and "
            "--skip_downloaded was provided".format(session))
    with connect(**kwargs) as login:
        matched_sessions = matching_sessions(
            login, session, with_scans=with_scans,
            without_scans=without_scans, project_id=project_id,
            subject_id=subject_id, skip=skip, before=before, after=after)
        downloaded_resources = defaultdict(list)
        for session in matched_sessions:
            for scan in matching_scans(session, scans,
                                       match_id=match_scan_id):
                resources = []
                suffix = False
                if resource_name is not None:
                    try:
                        resource = scan.resources[resource_name]
                    except KeyError:
                        try:
                            resource = scan.resources[resource_name.upper()]
                        except KeyError:
                            logger.warning(
                                ("Did not find '%s' resource for %s:%s, "
                                 "skipping"),
                                resource_name, session.label, scan_label)
                            continue
                    resources.append(resource)
                else:
                    resource_names = [
                        r.label for r in scan.resources.values()
                        if r.label not in skip_resources]
                    if not resource_names:
                        logger.warning(
                            ("No valid scan formats for '%s-%s' in '%s' "
                             "(found '%s')"),
                            scan.id, scan.type, session,
                            "', '".join(scan.resources))
                        continue
                    if len(resource_names) > 1:
                        suffix = True
                    for resource_name in resource_names:
                        resources.append(scan.resources[resource_name])
                for resource in resources:
                    _download_resource(
                        resource, scan, session, download_dir, subject_dirs,
                        convert_to, converter, strip_name, suffix=suffix)
                    downloaded_resources[session.label].append(resource.uri)
    if not downloaded_resources:
        logger.warning(
            ("No scans matched pattern(s) '%s' in specified "
             "sessions (%s)"),
            "', '".join(scans) if scans is not None else '',
            "', '".join(s.label for s in matched_sessions))
    else:
        num_resources = reduce(add,
                               map(len, downloaded_resources.values()))
        logger.info("Successfully downloaded %s scans from %s session(s)",
                    num_resources, len(matched_sessions))
    return downloaded_resources


def get_from_xml(xml_file_path, download_dir, convert_to=None, converter=None,
                 subject_dirs=False, strip_name=False, **kwargs):
    """
    Downloads datasets (e.g. scans) from an XNAT instance based on a saved
    XML file downloaded from the XNAT UI

        >>> xnatutils.get_from_xml('/home/myuser/Downloads/saved-from-ui.xml',
                                   '/home/myuser/Downloads')

    The destination directory can be specified by the 'directory' kwarg.
    Each session will be downloaded to its own folder under the destination
    directory unless the 'subject-dir' kwarg is provided in which case the
    sessions will be grouped under separate subject directories.

    Parameters
    ----------
    xml_file_path : str
        Path to the downloaded XML file
    download_dir : str
        Path to download the scans to. If not provided the current working
        directory will be used
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
    with open(xml_file_path) as f:
        tree = ElementTree.parse(f)
    root = tree.getroot()
    downloaded = []
    with connect(**kwargs) as login:
        for entry in root.iter('{http://nrg.wustl.edu/catalog}entry'):
            uri = '/data/' + entry.attrib['URI'][1:]
            resource = login.create_object(
                re.match(r'.*/resources/[^/]+', uri).group(0))
            session = login.create_object(
                re.match(r'.*/experiments/[^/]+', uri).group(0))
            if 'scans' in uri:
                scan = login.create_object(
                    re.match(r'.*/scans/[^/]+', uri).group(0))
            else:
                scan = None
            _download_resource(
                resource, scan, session, download_dir,
                subject_dirs, convert_to, converter, strip_name)
            downloaded.append(resource.uri)
    logger.info("Successfully downloaded %s resources", len(downloaded))
    return downloaded


def get_extension(resource_name):
    ext = ''
    try:
        ext = resource_exts[resource_name]
    except KeyError:
        try:
            ext = resource_exts[resource_name.upper()]
        except KeyError:
            pass
    return ext


def _download_resource(resource, scan, session, download_dir, subject_dirs,
                       convert_to, converter, strip_name, suffix=False):
    if scan is not None:
        scan_label = scan.id
        if scan.type is not None:
            scan_label += '-' + sanitize_re.sub('_', scan.type)
    else:
        scan_label = 'RESOURCES'
    # Get the target location for the downloaded scan
    if subject_dirs:
        target_dir = os.path.join(download_dir,
                                  _get_subject_from_session(session).label)
    else:
        target_dir = os.path.join(download_dir, session.label)
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
            except KeyError as e:
                raise XnatUtilsUsageError(
                    "Cannot convert to unrecognised format '{}'"
                    .format(convert_to)) from e
    else:
        target_ext = ''
    target_path = os.path.join(target_dir, scan_label)
    if suffix:
        target_path += '-' + resource.label
    target_path += target_ext
    tmp_dir = target_path + '.download'
    # Download the scan from XNAT
    print('Downloading {}: {}-{}'.format(
        session.label, scan_label,
        resource.label))
    try:
        resource.download_dir(tmp_dir)
    except KeyError as e:
        raise XnatUtilsMissingResourceException(
            resource.label, session.label, scan_label,
            available=[r.label for r in scan.resources]) from e
    except XNATResponseError as e:
        # Check for 404 status
        try:
            status = int(
                re.match(r'.*\(status (\d+)\).*', str(e)).group(1))
            if status == 404:
                logger.warning(
                    "Did not find any files for resource '%s' in '%s' "
                    "session", resource.label, session.label)
                return True
        except Exception:  # pylint: disable=broad-except
            pass
        raise e
    # Remove existing files/dirs at target_path before redownloading
    if os.path.exists(target_path):
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        else:
            os.remove(target_path)
    # Extract the relevant data from the download dir and move to
    # target location
    src_path = glob(tmp_dir + '/**/files', recursive=True)[0]
    if (convert_to is None or convert_to.upper() == resource.label): # No conversion required
        if strip_name and resource.label in ('DICOM', 'secondary'):
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
    else:
        # Convert or move downloaded dir/files to target path
        mrconvert = dcm2niix = None
        if convert_to is not None:
            if converter is None:
                if (convert_to in ('nifti', 'nifti_gz')
                        and resource.label == 'DICOM'):
                    converter = 'dcm2niix'
                else:
                    converter = 'mrconvert'
            if converter == 'dcm2niix':
                dcm2niix = find_executable('dcm2niix')
                if dcm2niix is None:
                    raise XnatUtilsUsageError(
                        "Selected converter 'dcm2niix' is not available, "
                        "please make sure it is installed and on your "
                        "path")
            elif converter == 'mrconvert':
                mrconvert = find_executable('mrconvert')
                if mrconvert is None:
                    raise XnatUtilsUsageError(
                        "Selected converter 'mrconvert' is not available, "
                        "please make sure it is installed and on your "
                        "path")
            else:
                assert False
        try:
            if converter == 'dcm2niix':
                # convert between dicom and nifti using dcm2niix.
                # mrconvert can do this as well but there have been
                # some problems losing TR from the dicom header.
                zip_opt = 'y' if convert_to == 'nifti_gz' else 'n'
                convert_cmd = '{} -z {} -o "{}" -f "{}" "{}"'.format(
                    dcm2niix, zip_opt, target_dir,
                    (scan_label if scan is not None else resource.label),
                    src_path)
                sp.check_call(convert_cmd, shell=True)
            elif converter == 'mrtrix':
                # If dcm2niix format is not installed or another is
                # required use mrconvert instead.
                sp.check_call('{} "{}" "{}"'.format(
                    mrconvert, src_path, target_path), shell=True)
            else:
                if (resource.label == 'DICOM' and convert_to in ('nifti',
                                                                'nifti_gz')):
                    msg = 'either dcm2niix or '
                else:
                    msg = ''
                raise XnatUtilsUsageError(
                    "Please install {} mrconvert to convert between {}"
                    "and {} formats".format(
                        msg, resource.label.lower(), convert_to))
        except sp.CalledProcessError as e:
            shutil.move(src_path, os.path.join(
                target_dir,
                (scan_label if scan is not None else resource.label)
                + get_extension(resource.label)))
            logger.warning(
                "Could not convert %s:%s to %s format (%s)",
                session.label, scan.type, convert_to,
                e.output.strip() if e.output is not None else '')
    # Clean up download dir
    shutil.rmtree(tmp_dir)
    return True


def _get_subject_from_session(session):
    # if 'subjects' in resource_uri:
    #     subject_json = login.get_json(re.match(r'.*/subject/[^\]+',
    #                                            resource_uri))
    # else:
    subject = session.subject
    if subject is None:
        subject = session.xnat_session.create_object(
            re.match(r'(.*)(?=/experiments)', session.uri).group(1)
            + '/subjects/' + session.subject_id)
    return subject


description = """
Downloads datasets (e.g. scans) from an XNAT instance.

If you have downloaded an XML file with the list of resources you would like to 
download from your XNAT UI, then simply provide it to xnat-get and it will
download the resources you selected, e.g.

    $ xnat-get <your-downloaded-xml-file>.xml

Otherwise you can specifiy the sessions/scans to download

    $ xnat-get MRH017_001_MR01 MRH017_002_MR01

If you would like to download data from a range of sessions you can use a
(regular expression) search patterns. For example the following command

    $ xnat-get 'MRH017_0.*_MR01'

will download the first imaging session of subjects 1-99 in the project 'MRH017'.
Note the single quotes around the pattern string, as these stop the '*' being interpreted
as a filename glob. Please refer to https://docs.python.org/3/library/re.html for the complete
regular expression syntax you can use. However, most of the time
just need the '.*' wildcard to match any string of characters or perhaps '|'
to specify a list of options. For example the following command

   $ xnat-get 'MRH017_00(1|2|3|9)_MR0(1|3)'

will download sessions 1 & 3 for subjects 1, 2, 3 & 9.

By default all scans in the provided session(s) are downloaded to the current
working directory unless they are filtered by the provided '--scan' option(s).
Both the session name and scan filters can be regular expressions, e.g.

    $ xnat-get 'MRH017_001_MR.*' --scan 'ep2d_diff.*'

The destination directory can be specified by the '--directory' option.
Each session will be downloaded to its own folder under the destination
directory unless the '--subject-dir' option is provided in which case the
sessions will be grouped under separate subject directories.

If there are multiple resources for a dataset on an XNAT instance (unlikely) the one to
download can be specified using the '--format' option, otherwise the only
recognised neuroimaging format (e.g. DICOM, NIfTI, MRtrix format).

DICOM files (ONLY DICOM file) name can be stripped using the option
--strip_name or -sn. If specified, the final name will be in the format
000*.dcm.

The downloaded images can be automatically converted to NIfTI or MRtrix formats
using dcm2niix or mrconvert (if the tools are installed and on the system path)
by providing the '--convert_to' option and specifying the desired format.

    $ xnat-get TEST001_001_MR01 --scan 'ep2d_diff.*' --convert_to nifti_gz

User credentials can be stored in a ~/.netrc file so that they don't need to be
entered each time a command is run. If a new user provided or netrc doesn't
exist the tool will ask whether to create a ~/.netrc file with the given
credentials.
"""


def parser():
    parser = base_parser(description)
    parser.add_argument('session_or_regex_or_xml_file', type=str, nargs='*',
                        help=("Name or regular expression of the session(s) "
                              "to download the dataset from, or name of an "
                              "\"download images\" XML file downloaded from "
                              "the GUI"))
    parser.add_argument('--target', '-t', type=str, default=None,
                        help=("Path to download the scans to. If not provided "
                              "the current working directory will be used"))
    parser.add_argument('--scans', '-x', type=str, default=None, nargs='+',
                        help=("Name of the scans to include in the download. "
                              "If not provided all scans from the session are "
                              "downloaded. Multiple scans can be specified"))
    parser.add_argument('--resource', '-r', type=str, default=None,
                        help=("The name of the resource to download. Not "
                              "required if there is only one valid resource "
                              "for each given dataset (e.g. DICOM), which is "
                              "typically the case"))
    parser.add_argument('--with_scans', '-w', type=str, default=None,
                        nargs='+',
                        help=("Only download from sessions containing the "
                              "specified scans"))
    parser.add_argument('--without_scans', '-o', type=str, default=None,
                        nargs='+',
                        help=("Only download from sessions that don't contain "
                              "the specified scans"))
    parser.add_argument('--convert_to', '-c', type=str, default=None,
                        choices=conv_choices,
                        help=("Runs a conversion script on the downloaded "
                              "scans to convert them to a given format if "
                              "required"))
    parser.add_argument('--converter', '-v', type=str, default=None,
                        choices=converter_choices,
                        help=("The conversion tool to convert the downloaded "
                              "datasets. Can be one of '{}'. If not provided "
                              "and both converters are available, dcm2niix "
                              "will be used for DICOM->NIFTI conversion and "
                              "mrconvert for other conversions".format(
                                  "', '".join(converter_choices))))
    parser.add_argument('--subject_dirs', '-d', action='store_true',
                        default=False, help=(
                            "Whether to organise sessions within subject "
                            "directories to hold the sessions in or not"))
    parser.add_argument('--skip_downloaded', '-k', action='store_true',
                        help=("Whether to ignore previously downloaded "
                              "sessions (i.e. if there is a directory in "
                              "the target path matching the session name "
                              "it will be skipped"))
    parser.add_argument('--before', '-b', default=None, type=str,
                        help=("Only select sessions before this date "
                              "(in Y-m-d format, e.g. 2018-02-27)"))
    parser.add_argument('--after', '-a', default=None, type=str,
                        help=("Only select sessions after this date "
                              "(in Y-m-d format, e.g. 2018-02-27)"))
    parser.add_argument('--project', '-p', type=str, default=None,
                        help=("The ID of the project to list the sessions "
                              "from."))
    parser.add_argument('--subject', '-j', type=str, default=None,
                        help=("The ID of the subject to list the sessions "
                              "from. Requires '--project' to be also "
                              "provided"))
    parser.add_argument('--dont_match_scan_id', action='store_true',
                        default=False, help=(
                            "To disable matching on scan ID if the scan "
                            "type is None"))
    parser.add_argument('--strip_name', '-i', action='store_true',
                        default=False,
                        help=("Whether to strip the default name of each dicom"
                              " file to have just a number. Ex. 0001.dcm. It "
                              "will work just on DICOM files, not NIFTI."))
    add_default_args(parser)
    return parser


def cmd(argv=sys.argv[1:]):

    args = parser().parse_args(argv)

    set_logger(args.loglevel)

    if args.target is None:
        download_dir = os.getcwd()
    else:
        download_dir = os.path.expanduser(args.target)
    try:    
        if (len(args.session_or_regex_or_xml_file) == 1
                and args.session_or_regex_or_xml_file[0].endswith('.xml')):
            get_from_xml(args.session_or_regex_or_xml_file[0],
                         download_dir, convert_to=args.convert_to,
                         converter=args.converter, subject_dirs=args.subject_dirs,
                         user=args.user, strip_name=args.strip_name,
                         server=args.server, use_netrc=(not args.no_netrc))
        else:
            get(args.session_or_regex_or_xml_file, download_dir, scans=args.scans,
                resource_name=args.resource, with_scans=args.with_scans,
                without_scans=args.without_scans, convert_to=args.convert_to,
                converter=args.converter, subject_dirs=args.subject_dirs,
                user=args.user, strip_name=args.strip_name, server=args.server,
                use_netrc=(not args.no_netrc),
                match_scan_id=(not args.dont_match_scan_id),
                skip_downloaded=args.skip_downloaded,
                project_id=args.project, subject_id=args.subject,
                before=args.before, after=args.after)
    except XnatUtilsUsageError as e:
        print_usage_error(e)
    except XNATResponseError as e:
        print_response_error(e)
    except XnatUtilsException as e:
        print_info_message(e)
