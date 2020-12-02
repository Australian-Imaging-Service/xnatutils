from xnatutils import get_from_xml, put, get, ls

get_from_xml('/Users/tclose/Downloads/EG_Diffusion_Data_MD_2020Nov30.xml',
             '/Users/tclose/Desktop/temp', server='http://xnat.sydney.edu.au')

# get('TEST004_002_MR01', '/Users/tclose/Data/TEST004',
#     server='mbi-xnat.erc.monash.edu.au')
