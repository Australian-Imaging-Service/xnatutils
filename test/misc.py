from xnatutils import get, put

# get('MMH008_FA19FA008_MRPT01', '/Users/tclose/Desktop',
#     scans=['Head_Head_t1_mp2rage_sag_p3_iso_INV1'])

put('TEST001_TESTMISC_MR01', 'test_file',
    '/Users/tclose/Desktop/screen-shot.png', create_session=True,
    overwrite=True)