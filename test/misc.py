from xnatutils import get_from_xml, put

get_from_xml('./test/tclose-20200727_155819.xml', '/Users/tclose/Desktop/temp',
             server='mbi-xnat.erc.monash.edu.au')

# put('TEST001_TESTMISC_MR01', 'test_file',
#     '/Users/tclose/Desktop/screen-shot.png', create_session=True,
#     overwrite=True)
