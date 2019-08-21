import sys
from .base import (print_response_error, print_usage_error, connect,
                   print_info_message, base_parser, add_default_args,
                   set_logger)
from xnatutils.exceptions import XnatUtilsUsageError, XnatUtilsException
from xnat.exceptions import XNATResponseError


def rename(session_name, new_session_name, **kwargs):
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
        try:
            session = login.experiments[session_name]
        except KeyError:
            raise XnatUtilsUsageError(
                "No session named '{}'".format(session_name))
        login.put(session.uri + '?label={}'.format(new_session_name))
    print("Successfully renamed '{}' to '{}'".format(session_name,
                                                     new_session_name))


description = """
Renames a session from the command line (if there has been a mistake in its
name for example).

    $ xnat-rename MMA003_001_MR01 MMA003_001_MRPT01
"""


def parser():
    parser = base_parser(description)
    parser.add_argument('session_name', type=str,
                        help=("Name of the session to rename"))
    parser.add_argument('new_session_name', type=str,
                        help=("The new name of the session"))
    add_default_args(parser)
    return parser


def cmd(argv=sys.argv[1:]):

    args = parser().parse_args(argv)

    set_logger(args.loglevel)

    try:
        rename(args.session_name, args.new_session_name,
               user=args.user, server=args.server,
               use_netrc=(not args.no_netrc))
    except XnatUtilsUsageError as e:
        print_usage_error(e)
    except XNATResponseError as e:
        print_response_error(e)
    except XnatUtilsException as e:
        print_info_message(e)
