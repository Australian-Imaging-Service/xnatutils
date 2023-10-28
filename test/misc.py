from xnatutils import put, get

get('subject01_FDG_1',
    server='https://dev.xnat.sydney.edu.au',
    user='admin', password='admin',
    project_id='TBP_DEMO',
    resource_name='DICOM',
    create_session=True)


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
