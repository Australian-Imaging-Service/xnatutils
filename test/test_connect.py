import xnat
from xnatutils import MBI_XNAT_SERVER

login = xnat.connect(MBI_XNAT_SERVER, debug=True)

print login.projects
