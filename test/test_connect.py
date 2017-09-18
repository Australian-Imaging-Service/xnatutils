import os
import shutil
from xnatutils import connect, remove_ignore_errors
from os.path import expanduser
import errno

netrc_path = os.path.join(expanduser("~"), '.netrc')

user = 'unittest'
password = 'Test123!'

bad_netrc = """machine mbi-xnat.erc.monash.edu.au
user unittest
password bad_pass"""

try:
    shutil.move(netrc_path, netrc_path + '.good')
except IOError as e:
    if e.errno != errno.ENOENT:
        raise
try:
    # Create bad netrc file to test login failure
    with open(netrc_path, 'w') as f:
        f.write(bad_netrc)
    with connect() as mbi_xnat:
        print mbi_xnat.projects
finally:
    remove_ignore_errors(netrc_path)
    shutil.move(netrc_path + '.good', netrc_path)
