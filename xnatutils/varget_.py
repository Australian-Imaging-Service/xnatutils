import sys
from .base import (connect, print_response_error, print_usage_error,
                   print_info_message, set_logger, base_parser,
                   add_default_args)
from xnatutils.exceptions import XnatUtilsUsageError, XnatUtilsException
from xnat.exceptions import XNATResponseError


def varget(subject_or_session_id, variable, default='', **kwargs):
    """
    Gets the value of a variable (custom or otherwise) of a session or subject
    in an XNAT instance project

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


description = """
Gets the value of a variable (custom or otherwise) of a session or subject in a
an XNAT instance project

User credentials can be stored in a ~/.netrc file so that they don't need to be
entered each time a command is run. If a new user provided or netrc doesn't
exist the tool will ask whether to create a ~/.netrc file with the given
credentials.
"""


def parser():
    parser = base_parser(description)
    parser.add_argument('subject_or_session_id', type=str,
                        help=("Name of subject or session to get the variable "
                              "from"))
    parser.add_argument('variable', type=str,
                        help="Name of the variable to get")
    parser.add_argument('--default', type=str, default='',
                        help="Default value if object does not have a value")
    add_default_args(parser)
    return parser


def cmd(argv=sys.argv[1:]):

    args = parser().parse_args(argv)

    set_logger(args.loglevel)

    try:
        print(varget(args.subject_or_session_id, args.variable,
                     default=args.default, user=args.user,
                     server=args.server, use_netrc=(not args.no_netrc)),
                     end='')
    except XnatUtilsUsageError as e:
        print_usage_error(e)
    except XNATResponseError as e:
        print_response_error(e)
    except XnatUtilsException as e:
        print_info_message(e)
