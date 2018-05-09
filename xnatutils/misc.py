from .base import connect
from .exceptions import XnatUtilsUsageError


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
    with connect(**kwargs) as mbi_xnat:
        try:
            session = mbi_xnat.experiments[session_name]
        except KeyError:
            raise XnatUtilsUsageError(
                "No session named '{}'".format(session_name))
        mbi_xnat.put(session.uri + '?label={}'.format(new_session_name))
    print("Successfully renamed '{}' to '{}'".format(session_name,
                                                     new_session_name))
