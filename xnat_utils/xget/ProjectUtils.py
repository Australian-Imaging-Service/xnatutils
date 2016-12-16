import Args
import Sessions
import os
import XnatPass
import Utils
from functools import partial
from pyxnat import Interface


def id_to_label(conn, proj):
    """ Convert the give project ID into the label.
    Parameters
    ----------
    conn : The Interface object described in pyxnat/core/Interface.py
    exp : The project ID

    Returns:
    -------
    String or None if the project does not exist
    """
    if not proj:
        return None
    else:
        try:
            return conn.select.project(proj).xpath(
                "/xnat:Project/xnat:name")[0].text
        except Exception:
            return None


def choose_single(conn, projs, label):
    """ A simple choosing function which just returns
    the first project in the list.

    Normally a project ID is associated with one label,
    if that is the case, this function is safe.

    See label_to_id documentation for more details.

    Parameters
    ----------
    conn : An Interface object defined in pyxnat/core/Interface.py
    projs: A list of project IDs. There should only be one.

    Exceptions
    ----------
    Utils.AmbiguousLabelError : raised if there is more than one experiment in
                          given experiment list
    Returns
    -------
    String
    """
    if len(projs) > 1:
        raise Utils.AmbiguousLabelError(
            "More than one project ID associated with name " +
            str(label) +
            ": " +
            ",".join(projs))
    elif not projs:
        return None
    else:
        return projs[0]


def projects_matching_label(conn, label):
    """
    Retrieve all project ID's whose name matches the given label. Currently in XNAT two unique projects
    can have the same label.

    Parameters
    -----------
    conn : The Interface object described in pyxnat/pyxnat/core/Interface.py
    label : The name of the project

    Returns
    -------
    [String]

    """
    if not label:
        return None
    else:
        ps = conn.select.projects()
        ps._filters = {'label': label}

        def exact_match(p):
            """ Currently the REST API given a label constraint will retrieve all projects matching
                *label*. We need to make sure to keep only the exact matches
            """
            return conn.select.project(p).xpath(
                "/xnat:Project/xnat:name")[0].text == label

        return filter(exact_match, ps.get())


def label_to_id(conn, label, choose=choose_single):
    """
    Convert the give project label into the ID. Since there can be
    multiple projects with the same label across projects, the 'choose'
    function is used to pick one.

    Parameters
    ----------
    conn : The Interface object described in pyxnat/core/Interface.py
    label : The project label
    choose : A function takes:
               - an Interface object (see pyxnat/core/Interface.py),
               - list of project ids,
            picks one and outputs the chosen projects ID. See
            choose_by_project or choose_single for implementation examples.

    Returns:
    -------
    String or None if the project does not exist
    """
    if not label:
        return None
    else:
        res = projects_matching_label(conn, label)
        if res:
            proj_id = choose(conn, res, label)
            if proj_id:
                proj = conn.select.project(proj_id)
                return proj.xpath("@ID")[0]
            else:
                return None
        else:
            return None


def exists(conn, proj, choose=choose_single):
    """
    Test whether this given project exists. Differs from the exists()
    function in pyxnat by accepting both the project ID or label.

    However if the label is given, the default choosing function is
    "choose_single". See the documentation for label_to_id
    for more information on this function's interface.

    Parameters
    ----------
    conn : The Interface object described in pyxnat/core/Interface.py
    exp:   The project ID or label
    choose : A function that picks out of many possible projects.

    Exceptions
    ----------
    ValueError : is raised if it determined that 'exp' is the session label and
    \"choose\" is not provided
    Returns
    -------
    Bool
    """
    if conn.select.project(proj).exists():
        return True
    else:
        return label_to_id(conn, proj, choose) is not None


def make_proj_dict(conn, projs):
    proj_dict = Utils.tag_synonyms(projs, partial(label_id_flip, conn))


def label_id_flip(conn, proj):
    """
    If the given project is a label, return the ID and vice versa. First
    it checks if the given argument is a label, then an ID.

    Parameters
    ----------
    conn : The Interface object described in pyxnat/core/Interface.py
    proj:   The project ID or label

    Exceptions
    ----------
    Utils.AmbiguousLabelError : raised if
                           - the given argument is a label and if that
                             points to multiple projects,
                           - the given argument is a label but also matches
                             the ID of a different project

    Returns
    -------
    String or None
    """
    label = choose_single(conn, projects_matching_label(conn, proj), proj)
    if label:
        if conn.select.project(proj).exists() and id_to_label(
                conn, proj) != proj:
            raise Utils.AmbiguousLabelError(
                "The given label " +
                proj +
                " is both a name and an ID.")
        else:
            return label
    else:
        if conn.select.project(proj).exists():
            return id_to_label(conn, proj)
