from past.builtins import basestring
import sys
from operator import attrgetter
import logging
from .base import (
    connect, is_regex, matching_subjects, matching_sessions,
    base_parser, add_default_args, print_response_error, print_usage_error,
    print_info_message, set_logger)
from xnat.exceptions import XNATResponseError
from .exceptions import XnatUtilsUsageError, XnatUtilsException

logger = logging.getLogger('xnat-utils')


def ls(xnat_id=(), datatype=None, with_scans=None, without_scans=None,
       return_attr=None, before=None, after=None, project_id=None,
       subject_id=None, **kwargs):
    """
    Displays available projects, subjects, sessions and scans from an XNAT instance.

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

    This is the convention used for an XNAT instance (which these tools were
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
        The ID of the project to list the sessions/subjects/scans from.
    subject_id : str | None
        The ID of the subject to list the sessions/scans. Requires that
        project ID is also supplied.
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
        if is_regex(xnat_id):
            raise XnatUtilsUsageError(
                "'datatype' option must be provided if using regular "
                "expression id, '{}' (i.e. one with non alphanumeric "
                "+ '_' characters in it)".format("', '".join(xnat_id)))
        if subject_id is not None:
            if project_id is None:
                raise XnatUtilsUsageError(
                    "project_id (\"-p\") must be provided if subject_id is "
                    "('{}')".format(subject_id))
            datatype = 'session'
        elif project_id is not None:
            datatype = 'subject'
        elif not xnat_id:
            datatype = 'project'
        else:
            logger.warning(
                "Guessing datatype by number of underscores in "
                "provided xnat_id (%s). 0 - project, 1 - subject "
                ">=2 - session. This will only be valid for XNAT "
                "repositories with matching naming conventions "
                "(e.g. Monash University). To suppress this message provide "
                "the \"datatype\" (\"-d\") flag", xnat_id)
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
                project_id = xnat_id
            elif num_underscores == 1:
                datatype = 'session'
                subject_id = xnat_id.split('_')[0]
            else:
                project_id, subject_id = xnat_id.split('_')[:2]
                datatype = 'scan'

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
            matches = matching_subjects(login, xnat_id, project_id=project_id)
            return_attr = 'label' if return_attr is None else return_attr
        elif datatype == 'session':
            matches = matching_sessions(
                login, xnat_id, with_scans=with_scans,
                without_scans=without_scans, project_id=project_id,
                subject_id=subject_id, before=before, after=after)
            return_attr = 'label' if return_attr is None else return_attr
        elif datatype == 'scan':
            matches = set()
            for session in matching_sessions(login, xnat_id,
                                             project_id=project_id,
                                             subject_id=subject_id):
                matches |= set(session.scans.values())
            return_attr = 'type' if return_attr is None else return_attr
        else:
            assert False
        if return_attr:
            matches = sorted(getattr(m, return_attr) for m in matches
                             if getattr(m, return_attr) is not None)
    return matches


description = """
Displays available projects, subjects, sessions and scans from an XNAT instance.

The datatype listed (i.e. 'project', 'subject', 'session' or 'scan') is assumed
to be the next level down the data tree if not explicitly provided (i.e.
subjects if a project ID is provided, sessions if a subject ID is provided,
etc...) but can be explicitly provided via the '--datatype' option. For
example, to list all sessions within the MRH001 project

    $ xnat-ls MRH001 --datatype session


If '--datatype' is not provided then it will attempt to guess the
datatype from the number of underscores in the provided xnat_id

    0   - project
    1   - subject
    >=2 - session

This is the convention used for an XNAT instance (which these tools were
originally designed for) but may not be for your XNAT repository.
In this case you will need to explicitly provide the --datatype
(or -d) option.

Scans listed over multiple sessions will be added to a set, so the list
returned is the list of unique scan types within the specified sessions. If no
arguments are provided the projects the user has access to will be listed.

Multiple subject or session IDs can be provided as a sequence or using regular
expression syntax (e.g. MRH000_.*_MR01 will match the first session for each
subject in project MRH000). Note that if regular expressions are used then an
explicit datatype must also be provided.

User credentials can be stored in a ~/.netrc file so that they don't need to be
entered each time a command is run. If a new user provided or netrc doesn't
exist the tool will ask whether to create a ~/.netrc file with the given
credentials.
"""


DATATYPES = ('project', 'subject', 'session', 'scan')


def parser():
    parser = base_parser(description)
    parser.add_argument('id_or_regex', type=str, nargs='*',
                        help=("The ID or regular expression of the "
                              "project/subject/session to list from."))
    parser.add_argument('--datatype', '-d', type=str, choices=DATATYPES,
                        default=None, help=(
                            "The data type to list, can be one of '{}'"
                            .format("', '".join(DATATYPES))))
    parser.add_argument('--with_scans', '-w', type=str, default=None,
                        nargs='+',
                        help=("Only download from sessions containing the "
                              "specified scans"))
    parser.add_argument('--without_scans', '-o', type=str, default=None,
                        nargs='+',
                        help=("Only download from sessions that don't contain "
                              "the specified scans"))
    parser.add_argument('--return_attr', '-t', type=str, default=None,
                        help=("The attribute name to return for each "
                              "matching item. If None defaults to 'label' "
                              "for subjects and sessions, 'id' for projects"
                              " and 'type' for scans."))
    parser.add_argument('--project', '-p', type=str, default=None,
                        help=("The ID of the project to list the "
                              "sessions/subjects/scans from."))
    parser.add_argument('--subject', '-j', type=str, default=None,
                        help=("The ID of the subject to list the sessions "
                              "from. Requires that project_id is also "
                              "supplied"))
    parser.add_argument('--before', '-b', default=None, type=str,
                        help=("Only select sessions before this date "
                              "(in Y-m-d format, e.g. 2018-02-27)"))
    parser.add_argument('--after', '-a', default=None, type=str,
                        help=("Only select sessions after this date "
                              "(in Y-m-d format, e.g. 2018-02-27)"))
    add_default_args(parser)
    return parser


def cmd(argv=sys.argv[1:]):

    args = parser().parse_args(argv)

    set_logger(args.loglevel)

    try:
        print('\n'.join(ls(args.id_or_regex, datatype=args.datatype,
                           user=args.user, with_scans=args.with_scans,
                           without_scans=args.without_scans,
                           server=args.server, project_id=args.project,
                           subject_id=args.subject,
                           return_attr=args.return_attr, before=args.before,
                           after=args.after,
                           use_netrc=(not args.no_netrc))))
    except XnatUtilsUsageError as e:
        print_usage_error(e)
    except XNATResponseError as e:
        print_response_error(e)
    except XnatUtilsException as e:
        print_info_message(e)
