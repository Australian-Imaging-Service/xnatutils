from .base import connect
from .exceptions import XnatUtilsUsageError


def rename(session_name, new_session_name, user=None, connection=None,
           loglevel='ERROR', server=None):
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
    server: str
        URI of the XNAT server to use. Default's to MBI-XNAT.
    """
    with connect(user, loglevel=loglevel, connection=connection,
                 server=server) as mbi_xnat:
        try:
            session = mbi_xnat.experiments[session_name]
        except KeyError:
            raise XnatUtilsUsageError(
                "No session named '{}'".format(session_name))
        mbi_xnat.put(session.uri + '?label={}'.format(new_session_name))
    print("Successfully renamed '{}' to '{}'".format(session_name,
                                                     new_session_name))
