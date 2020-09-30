XnatUtils
=========

Xnat-utils is a collection of scripts for conveniently up/downloading and
listing data on/from XNAT based on the `XnatPy package <https://pypi.org/project/xnat/>`_.

Optional Dependencies
---------------------

The following converters are required for automatic conversions of downloaded images (using the
'--convert_to' and '--converter' options)

* dcm2niix (https://github.com/rordenlab/dcm2niix)
* MRtrix 3 (http://mrtrix.readthedocs.io/en/latest/)

Installation
------------

Install Python (>=3.4)
~~~~~~~~~~~~~~~~~~~~~~

While many systems (particularly in research contexts) will already have Python 3 installed (note that Python 2
is not sufficient), if your workstation doesn't here are some basic instructions on how to install it.

macOS
^^^^^

macOS ships with it's own, slightly modified, version of Python, which it uses
in some applications/services. For the most part it is okay for general use
but in some cases, such as with `xnat-utils`, the modifications can cause
problems. To avoid these I recommend installing an unmodified version of Python
for use in your scientific programs using Homebrew (http://brew.sh). To do this
first install Homebrew::

    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
    
then install Python with::

    brew install python3
    
If everything has gone well, when you type::

    which python3
    
it should come back with::

    /usr/local/bin/python3

If it doesn't or your run into any problems follow the instructions you receive
when you run::

    brew doctor

Note that these instructions are just recommendations so you don't have to
follow all of them, just the ones that are likely to be related to your
problem.

Windows
^^^^^^^

Download the version of Python for Windows using the most appropriate installer
for Python (>=3.4), here https://www.python.org/downloads/windows/.
 
Linux/Unix
^^^^^^^^^^

Python3 is most likely already installed but if it isn't it is best to install
it using your package manager.

Install pip
~~~~~~~~~~~

Pip is probably already be installed by default with your Python package so
check whether it is installed first::

    pip3 --version
    
Noting that it should be in /usr/local/bin if you are using Homebrew on macOS.

If pip is not installed you can install it by downloading the following script,
https://bootstrap.pypa.io/get-pip.py and::

    python3 <path-to-downloaded-file>


Install XnatUtils package
~~~~~~~~~~~~~~~~~~~~~~~~~

The XnatUtils source code can be downloaded (or cloned using git) from
https://github.com/MonashBI/xnatutils.git. To install it
``cd`` to to the directory you have downloaded and run::

    pip3 install xnatutils
    
If you get permission denied errors you may need to use ``sudo``,
or if you don't have admin access then you can install it in your
user directory with the ``--user`` flag.::

    pip3 install --user xnatutils

I have had some difficulty with the installation of ``progressbar2`` as there is a
conflict with the ``progressbar`` package (they both produce packages called
``progressbar``). In this case it is probably a good idea to install xnat-utils
in a virtual environment (https://virtualenv.readthedocs.io/en/latest/).

Authentication
--------------

The first time you use one of the utilities you will be prompted for the address
of the server would like to connect to, in addition to your username and
password. By default a alias token for these credentials will be stored in
a ~/.netrc file with the following format (with permissions set to 600 on the file)::

    machine <your-server-url>
    user <your-alias-token>
    password <your-alias-secret>

If you don't want these credentials stored, then pass the '--no_netrc'
(or '-n') option.

If you have saved your credentials in the ~/.netrc file, subsequent calls won't require
you to provide the server address or username/password until the token
expires (if you don't want deal with expiring tokens you can just save your username/password
in the ~/.netrc file instead, however, please be careful with important passwords). To reset
the saved credentials provide ``--server`` option again with the full server address
including the protocol (e.g. 'https://') or edit the ~/.netrc file directly.

To connect to an additional XNAT server, provide the new server address via the ``--server`` option.
Credentials for this server will be saved alongside the credentials for your previously saved
servers. If the ``--server`` option is not provided the first server in the file will be used. To
used the save credentials for a secondary server you only need to provide as of the secondary server
address to ``--server`` to distinguish it from the other saved servers. For example given the following
saved credentials in a ~/.netrc file::

    machine xnat.myuni.edu
    user myusername
    password mypassword
    machine xnat-dev.myuni.edu
    user mydevusername
    password mydevpassword
    
then::
    
    $ xnat-ls -s dev MYPROJECT
    
will be enough to select the development server from the saved credentials list.

Usage
-----

Six commands will be installed 

* xnat-get - download scans and resources
* xnat-put - upload scans and resources (requires write privileges to project)
* xnat-ls - list projects/subjects/sessions/scans
* xnat-rename - renames an XNAT session
* xnat-varget - retrieve a metadata field (including "custom variables")
* xnat-varput - set a metadata field (including "custom variables")

Please see the help for each tool by passing it the '-h' or '--help' option.

Help on Regular Expressions
---------------------------

The regular expression syntax used by ``xnat-get`` and ``xnat-ls`` is fully defined
here, https://docs.python.org/2/library/re.html. However, for most basic use
cases you will probably only need to use the '.' and '*' operators.

'.' matches any character so the pattern::

   MRH060_00._MR01
   
will match ::

    MRH060_001_MR01
    MRH060_002_MR01
    MRH060_003_MR01
    MRH060_004_MR01
    MRH060_005_MR01
    MRH060_006_MR01
    MRH060_007_MR01
    MRH060_008_MR01
    MRH060_009_MR01

The '*' matches 0 or more repeats of the previous character, which is most
useful in conjunction with the '.' character to match string of wildcard
characters, e.g.::

    MRH060.*
      
will match all subjects/sessions in the MRH060 project.

Note, that when using regular expressions that use '*' on the command line you
will need to enclose them in single quotes to avoid the default wilcard file search, e.g.::

    $ xnat-ls 'MRH099.*'

Probably the only other syntax that will prove useful is the
'(option1|option2|...)'. For example::

    MRH060_00(1|2|3)_MR01
   
will match ::

    MRH060_001_MR01
    MRH060_002_MR01
    MRH060_003_MR01

For more advanced syntax please refer to the numerous tutorials on regular
expressions online.

