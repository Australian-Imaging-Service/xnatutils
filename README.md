MBI-XNAT Utils
==============

MBI-XNAT utils is a collection of scripts for conveniently up/downloading and
listing data on/from MBI-XNAT.

Prequisites
-----------

* XnatPy (https://bitbucket.org/bigr_erasmusmc/xnatpy)
* MRtrix 3 (http://mrtrix.readthedocs.io/en/latest/)
  (optional for automatic-conversion of downloaded images)
* dcm2nii (https://www.nitrc.org/projects/dcm2nii/)
  (optional for automatic-conversion of downloaded images)

Installation
------------

Either (download)[https://gitlab.erc.monash.edu.au/mbi-image/XnatUtils/repository/archive.zip?ref=master]
or clone this repository, `cd` to the root of the unzipped directory and run

    pip install -r requirements.txt .

which should install XnatPy for you. If `pip` is not installed you should can
install it with `easy_install pip` (you may need to use `sudo` for both these
commands). Otherwise make sure the XnatPy is installed, this repo is on your
PYTHONPATH and the 'bin' directory is on your PATH.

I have had some difficulty with the installation of progressbar2 as their is a
conflict with progressbar (they both produce packages called 'progressbar').
If you have a problem try uninstalling both then reinstalling 'progressbar2'.

Authentication
--------------

To authenticate with MBI-XNAT you will need to store your login details in the
file ~/.netrc with the following format (with permissions set to 600 on the
file)

    machine mbi-xnat.erc.monash.edu.au
    user your-authcate
    password your-authcate-password

If ~/.netrc is not created the utils will prompt to create it for each user

Usage
-----

There are three commands that download, upload and list data to/from MBI-XNAT

* xnat-get
* xnat-put
* xnat-ls

respectively. Please see the help for each tool by passing it the '-h' option.

Help on Regular Expressions
---------------------------

The regular expression syntax used by xnat-get and xnat-ls is fully defined
here, https://docs.python.org/2/library/re.html. However, for most basic use
cases you will probably only need to use the '.' and '*' operators.

'.' matches any character so the pattern 

  MRH060_00._MR01
   
will match 

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
characters, e.g.


    MRH060.*
      
will match all subjects/sessions in the MRH060 project.

Probably the only other syntax that will prove useful is the
'(option1|option2|...)'. For example

    MRH060_00(1|2|3)_MR01
   
will match 
  
    MRH060_001_MR01
    MRH060_002_MR01
    MRH060_003_MR01

For more advanced syntax please refer to the numerous tutorials on regular
expressions online.
