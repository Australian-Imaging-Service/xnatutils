from past.builtins import basestring
from operator import attrgetter
import logging
from .base import (
    connect, is_regex, matching_subjects, matching_sessions)
from .exceptions import XnatUtilsUsageError

logger = logging.getLogger('xnat-utils')


def ls(xnat_id, datatype=None, with_scans=None, without_scans=None,
       return_attr=None, before=None, after=None, project_id=None,
       **kwargs):
    """
    Displays available projects, subjects, sessions and scans from MBI-XNAT.

    The datatype listed (i.e. 'project', 'subject', 'session' or 'scan') is
    assumed to be the next level down the data tree if not explicitly provided
    (i.e. subjects if a project ID is provided, sessions if a subject ID is
    provided, etc...) but can be explicitly provided via the '--datatype'
    option. For example, to list all sessions within the MRH001 project

        >>> xnatutils.ls('MRH001', datatype='session')

    If '--datatype' is not provided then it will attempt to guess the
    datatype from the number of underscores in the provided xnat_id

        0   - project
        1   - subject
        >=2 - session

    This is the convention used for MBI-XNAT (which these tools were
    originally designed for) but may not be for your XNAT repository.
    In this case you will need to explicitly provide the --datatype
    (or -d) option.

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
    return_attr : str | None | False
        The attribute name to return for each matching item. If None
        defaults to 'label' for subjects and sessions, 'id' for projects
        and 'type' for scans. If False, then the XnatPy object is returned
        instead
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
        logger.info("Guessing datatype by number of underscores in "
                    "provided xnat_id ({}). 0 - project, 1 - subject "
                    ">=2 - session".format(xnat_id))
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

    if datatype != 'session':
        msg = "'{}' option is only applicable when datatype='session'"
        if with_scans is not None:
            raise XnatUtilsUsageError(msg.format('with_scans'))
        if without_scans is not None:
            raise XnatUtilsUsageError(msg.format('without_scans'))
        if before is not None:
            raise XnatUtilsUsageError(msg.format('before'))
        if after is not None:
            raise XnatUtilsUsageError(msg.format('after'))
    with connect(**kwargs) as login:
        if datatype == 'project':
            matches = sorted(login.projects.values(),
                             key=attrgetter('id'))
            return_attr = 'id' if return_attr is None else return_attr
        elif datatype == 'subject':
            matches = matching_subjects(login, xnat_id)
            return_attr = 'label' if return_attr is None else return_attr
        elif datatype == 'session':
            matches = matching_sessions(
                login, xnat_id, with_scans=with_scans,
                without_scans=without_scans, project_id=project_id,
                before=before, after=after)
            return_attr = 'label' if return_attr is None else return_attr
        elif datatype == 'scan':
            matches = set()
            for session in matching_sessions(login, xnat_id,
                                             project_id=project_id):
                matches |= (s.label for s in session.scans.values())
            return_attr = 'type' if return_attr is None else return_attr
        else:
            assert False
    if return_attr:
        matches = sorted(attrgetter(return_attr)(m) for m in matches)
    return matches
