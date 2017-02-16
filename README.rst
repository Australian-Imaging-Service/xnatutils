MBI-XNAT Utils
==============

MBI-XNAT utils are a collection of scripts for conveniently up/downloading and
listing data on/from MBI-XNAT.

Prequisites
-----------

* XnatPy (https://bitbucket.org/bigr_erasmusmc/xnatpy)
* MRtrix 2 or 3 (optional)
* dcm2nii (optional)

Installation
------------

It should be as easy as 

pip install https://gitlab.erc.monash.edu.au/mbi-image/XnatUtils.git

Otherwise make sure the XnatPy is installed, this repo is on your PYTHONPATH
and the 'bin' directory is on your PATH.

Authentication
--------------

To authenticate with MBI-XNAT you will need to store your login details in the
file ~/.netrc with the following format (with permissions set to 600 on the
file)

machine mbi-xnat.erc.monash.edu.au
user your-authcate
password your-authcate-password

If ~/.netrc is not created the utils will prompt to create it for each user


