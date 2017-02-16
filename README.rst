MBI-XNAT Utils
==============

MBI-XNAT utils are a collection of scripts for conveniently up/downloading and
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

Should be as easy switching to this directory and running  

pip install .

which should install XnatPy for you. Otherwise make sure the XnatPy is
installed, this repo is on your PYTHONPATH and the 'bin' directory is on your
PATH.

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
