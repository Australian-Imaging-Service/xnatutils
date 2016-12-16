import args
import Sessions
import os
import XnatPass
from functools import partial
from pyxnat import Interface

def label_to_id(conn,label,choose):
    """ Convert the give experiment label into the ID. Since there can be
        multiple experiments with the same label across projects, the 'choose'
        function is used to pick one.

        Parameters
        ----------
        conn : The Interface object described in pyxnat/core/Interface.py
        exp : The experiment label 
        choose : A function takes:
                    - an Interface object (see pyxnat/core/Interface.py),
                    - list of experiment ids,
                 picks one and outputs the chosen experiments ID. See
                 choose_by_project or choose_first for implementation examples.

        Returns:
        -------
        String or None if the experiment does not exist
    """
    if not label:
        return None
    if not choose:
        raise ValueError("A choose function has not been specified")
    else:
        es=conn.select.experiments()
        es._filters={'label':label}
        
        # the REST API will return all experiments with any label matching
        # *label*. We need to filter out the experiments that are not exact
        # matches
        def exact_match(e):
            return conn.select.experiment(e).xpath("@label")[0] == label
        
        res = filter(exact_match, es.get())
        if res:
            exp_id = choose(conn,res)
            if exp_id:
                exp = conn.select.experiment(choose(conn,res))
                if exp.xpath("@label")[0] == label:
                    return exp.xpath("@ID")[0]
                else:
                    return None
            else:
                return None
        else:
            return None

def experiments_matching_label(conn,label):
    """
    Retrieve all experiment ID's whose name matches the given label. Currently in XNAT two unique experiments
    can have the same label.

    Parameters
    -----------
    conn : The Interface object described in pyxnat/pyxnat/core/Interface.py
    label : The name of the experiment

    Returns
    -------
    [String]
    
    """
    if not label:
        return None
    else:
        es = conn.select.experiments()
        es._filters={'label':label}
        def exact_match(p):
            """
            Currently the REST API given a label constraint will
            retrieve all experiments matching *label*. We need to make
            sure to keep only the exact matches
            """
            return conn.select.experiment(p).xpath("@label")[0] == label
        return filter(exact_match, es.get())
    
def choose_by_experiment(proj_id):
    """ Choose the experiment to belongs the given experiment. 

        Parameters
        ----------
        proj_id : The ID of the experiment this experiment belongs to
        
        See label_to_id documentation for more details.
        
        Returns
        -------
        String
    """    
    def _choose_by_experiment(_proj_id, conn, exps):
        exp = None
        for e in exps:
            if conn.select.experiment(e).xpath("@ID")[0] == _proj_id:
                exp = e
                break
        return exp
    return partial(_choose_by_experiment, proj_id) 

def choose_first(conn, exps):
    """ A simple choosing function which just returns
        the first experiment in the list.

        Use this function if you are sure the given label
        has only one associated experiment ID. Since this is a
        pretty unsafe assumption, use this function only for
        testing.
        
        See label_to_id documentation for more details.
    """
    if len(exps) > 1:
        raise Utils.AmbiguousLabelError("More than one experiment " + str(exps) + " associated with label.")
    else:
        return exps[0]
        
def id_to_label(conn,exp):
    """ Convert the give experiment ID into the label.
        Parameters
        ----------
        conn : The Interface object described in pyxnat/core/Interface.py
        exp : The experiment ID

        Returns:
        -------
        String or None if the experiment does not exist
    """    
    if not exp:
        return None
    else:
        try:
            return conn.select.experiment(exp).xpath("@label")[0]
        except Exception:
            return None

def exists(conn,exp,choose=None):
    """ Test whether this given experiment exists. Differs from the exists()
        function in pyxnat by accepting both the project ID or label.

        However if the label is given, an implementation of the
        \"choose\" function that picks one experiment out of a list
        should also be given.  See the documentation for label_to_id
        for more information on this function's interface.
        
        Parameters
        ----------
        conn : The Interface object described in pyxnat/core/Interface.py
        exp:   The experiment ID or label
        choose : A function that picks out of many possible experiments. Required
                 only if 'exp' is the session label.

        Exceptions
        ----------
        ValueError : is raised if it determined that 'exp' is the session label and
                     \"choose\" is not provided
        Returns
        -------
        String
    """
    if conn.select.experiment(exp).exists():
        return True
    else:
        if choose is None:
            raise ValueError("Querying on session label, but a \"choose\" function was not provided")
        else:
            return label_to_id(conn,exp,choose) is not None

def label_id_flip(conn,exp,choose=None):
    """ If the given experiment is a label, return the ID and vice versa

        However if the label is given, an implementation of the
        \"choose\" function that picks one experiment out of a list
        should also be given.  See the documentation for label_to_id
        for more information on this function's interface.
        
        Parameters
        ----------
        conn : The Interface object described in pyxnat/core/Interface.py
        exp:   The experiment ID or label
        choose : A function that picks out of many possible experiments. Required
                 only if 'exp' is the session label.

        Exceptions
        ----------
        ValueError : is raised if it determined that 'exp' is the session label and
                     \"choose\" is not provided
        Returns
        -------
        String
    """
    if conn.select.experiment(exp).exists():
        return id_to_label(conn,exp)
    else:
        if choose is None:
            raise ValueError("Converting a session label to ID, but a \"choose\" function was not provided")
        else:
            return label_to_id(conn,exp,choose)
