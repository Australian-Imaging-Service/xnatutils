from xnatutils import get_from_xml, put

get_from_xml('./test/clia6071-20200709_125713.xml', '/Users/tclose/Desktop/temp',
             server='xnat.sydney.edu.au')

# put('TEST001_TESTMISC_MR01', 'test_file',
#     '/Users/tclose/Desktop/screen-shot.png', create_session=True,
#     overwrite=True)
