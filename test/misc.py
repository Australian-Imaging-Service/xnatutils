import os
from xnatutils import get

os.environ["XNAT_USER"] = "admin"
os.environ["XNAT_PASS"] = "admin"
os.environ["XNAT_HOST"] = "http://localhost:8080"

get(
    "subject02_MR01",
    download_dir="/Users/tclose/Downloads/xnat-get-test2",
    # server="http://localhost:8080",
    scans=["t1w"],
    # user="admin",
    # password="admin",
    project_id="OPENNEURO_T1W",
    method="per_file",
)


# get(server='http://localhost:8989',
#     session='.*member0',
#     download_dir='/Users/tclose/Downloads/xnat-get-test',
#     scans='.*dicom.*',
#     resource_name='DICOM',
#     convert_to='mrtrix_gz',
#     converter='mrconvert',
#     project_id='concatenate_test')

# print(ls(server='https://dev.xnat.sydney.edu.au'))

# get_from_xml('/Users/tclose/Downloads/EG_Diffusion_Data_MD_2020Nov30.xml',
#              '/Users/tclose/Desktop/temp', server='http://xnat.sydney.edu.au')

# get('TEST004_002_MR01', '/Users/tclose/Data/TEST004',
#     server='mbi-xnat.erc.monash.edu.au')
