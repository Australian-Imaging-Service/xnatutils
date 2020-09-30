from xnatutils import get_from_xml, put, get, ls

# get_from_xml('./test/clia6071-20200709_125713.xml', '/Users/tclose/Desktop/temp',
#              server='xnat.sydney.edu.au')

# put('TEST001_TESTMISC_MR01', 'test_file',
#     '/Users/tclose/Desktop/screen-shot.png', create_session=True,
#     overwrite=True)

# get('S01_MR1', '/Users/tclose/Desktop/temp2', project_id='PIPELINETEST',
#     server='dev.xnat.sydney.edu.au')

print(ls(subject_id='S01', project_id='PIPELINETEST', server='dev.xnat.sydney.edu.au'))
