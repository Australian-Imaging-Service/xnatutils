from past.builtins import basestring
import logging
from .base import (
    connect, is_regex, matching_subjects, matching_sessions,
    list_results)
from .exceptions import XnatUtilsUsageError

logger = logging.getLogger('xnat-utils')


def ls(xnat_id, datatype=None, with_scans=None, without_scans=None,
       **kwargs):
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
    with_scans : list(str)
        A list of scans that the session is required to have (only applicable
        with datatype='session')
    without_scans : list(str)
        A list of scans that the session is required not to have (only
        applicable with datatype='session')
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
    if datatype is None:
        if not xnat_id:
            datatype = 'project'
        else:
            if is_regex(xnat_id):
                raise XnatUtilsUsageError(
                    "'datatype' option must be provided if using regular "
                    "expression id, '{}' (i.e. one with non alphanumeric + '_'"
                    " characters in it)".format("', '".join(xnat_id)))
            if isinstance(xnat_id, basestring):
                num_underscores = xnat_id.count('_')
            else:
                nu_list = [i.count('_') for i in xnat_id]
                num_underscores = nu_list[0]
                if any(n != num_underscores for n in nu_list):
                    raise XnatUtilsUsageError(
                        "Mismatching IDs (i.e. mix of project, subject "
                        "and/or session IDS) '{}'"
                        .format("', '".join(xnat_id)))
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

    with connect(**kwargs) as mbi_xnat:
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
                        mbi_xnat, ['experiments', exp.id, 'scans'],
                        'type'))
                    scans |= session_scans
                return sorted(scans)
        else:
            assert False
