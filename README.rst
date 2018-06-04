XnatUtils
=========

Xnat-utils is a collection of scripts for conveniently up/downloading and
listing data on/from XNAT.

Optional Dependencies
---------------------

The following converters are required for automatic conversions of downloaded images (using the
'--convert_to' and '--converter' options)

* dcm2niix (https://github.com/rordenlab/dcm2niix)
* MRtrix 3 (http://mrtrix.readthedocs.io/en/latest/)

Installation
------------

Install Python (>=2.7, >=3.4)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

    brew install python
    
If everything has gone well, when you type::

    which python
    
it should come back with::

    /usr/local/bin/python 

If it doesn't or your run into any problems follow the instructions you receive
when you run::

    brew doctor

Note that these instructions are just recommendations so you don't have to
follow all of them, just the ones that are likely to be related to your
problem.

Windows
^^^^^^^

Download the version of Python for Windows using the most appropriate installer
for Python (>=2.7, >=3.4), here https://www.python.org/downloads/windows/.
 
Linux/Unix
^^^^^^^^^^

Python is most likely already installed but if it isn't it is best to install
it using your package manager.

Install pip
~~~~~~~~~~~

Pip could already be installed by default with your Python package so it is
best to check whether it is installed first::

    pip --version
    
Noting that it should be in /usr/local/bin if you are using Homebrew on macOS.

If pip is not installed you can install it using ``easy_install``::

    easy_install pip
    
or by following the instructions at https://pip.pypa.io/en/stable/installing/#do-i-need-to-install-pip.

Install XnatUtils package
~~~~~~~~~~~~~~~~~~~~~~~~~

The XnatUtils source code can be downloaded (or cloned using git) from
https://github.com/monashbiomedicalimaging/xnatutils.git. To install it
``cd`` to to the directory you have downloaded and run::

    pip install xnatutils
    
If you get permission denied errors and you may need to use ``sudo``,
or if you don't have admin access to the box then you can install it in your
user directory with the ``--user`` flag.::

    pip install --user xnatutils

which should install XnatPy for you. If ``pip`` is not installed you should can
install it with `easy_install pip` (you may need to use ``sudo`` for both these
commands).

I have had some difficulty with the installation of ``progressbar2`` as there is a
conflict with the ``progressbar`` package (they both produce packages called
``progressbar``). If you have a problem try uninstalling ``progressbar`` with::

    pip uninstall progressbar
    
and then reinstalling ``progressbar2``::

    pip install progressbar2

If you don't want to use ``pip``, make sure that XnatPy is installed, and the 
xnat-utils repository directory is on your ``PYTHONPATH`` and the ``bin`` directory
of the repo is on your ``PATH`` variable
(see https://www.cyberciti.biz/faq/unix-linux-adding-path/).

Authentication
--------------

The first time you use one of the utilities you will need to provide the ``--server``
(or ``-s`` for short) option with the full server address of the XNAT server you
would like to connect to. To authenticate with the server you will be prompted to enter
your username and password. By default a alias token for these credentials will be stored in
a ~/.netrc file with the following format (with permissions set to 600 on the file)::

    machine <your-server-url>
    user <your-alias-token-or-username>
    password <your-alias-secret-or-password>

If you don't want these credentials stored, then pass the '--no_netrc' (or '-n') option.

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
* xnat-varget - set a metadata field (including "custom variables")
* xnat-varput - retrieve a metadata field (including "custom variables")

Please see the help for each tool by passing it the '-h' option.

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

