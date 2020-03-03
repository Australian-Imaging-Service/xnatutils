#!/usr/bin/env python3
import os.path as op
from operator import itemgetter
import re
import argparse
import pydicom
import xnatutils

parser = argparse.ArgumentParser()
parser.add_argument('xnat_id',
                    help="The XNAT session with the duplicates")
parser.add_argument('scan_ids', nargs='+',
                    help="The scans to strip enhanced mr images from")
parser.add_argument('--download_dir', default='.',
                    help=("A directory to download the scans to"))
parser.add_argument('--dry_run', action='store_true', default=False,
                    help=("Don't actually delete anything just display what "
                          "would be deleted"))
args = parser.parse_args()

ENHANCED_MR_STORAGE = '1.2.840.10008.5.1.4.1.1.4.1'


with xnatutils.connect() as xlogin:
    
    xsession = xlogin.experiments[args.xnat_id]  # noqa pylint:disable=no-member
    
    for scan_id in args.scan_ids:
        
        xscan = xsession.scans[scan_id]

        xscan.download_dir(args.download_dir)
        files_path = op.join(
            args.download_dir, args.xnat_id, 'scans',
            '{}-{}'.format(xscan.id, re.sub(r'[^a-zA-Z_0-9]', '_',
                                            xscan.type)),
            'resources', 'DICOM', 'files')
        
        for fname, xfile in sorted(xscan.files.items(), key=itemgetter(0)):
            fpath = op.join(files_path, fname)
            with open(fpath, 'rb') as f:
                dcm = pydicom.dcmread(fpath)
            if dcm.file_meta.MediaStorageSOPClassUID == ENHANCED_MR_STORAGE:
                print("Deleting '{}".format(fname))
                if not args.dry_run:
                    xfile.delete()

if args.dry_run:
    print('Would delete proceeding "Enhanced MR Image Storage" from {}:[{}]'
          .format(args.xnat_id, ', '.join(args.scan_ids)))
else:
    print('Deleted all "Enhanced MR Image Storage" from {}:[{}]'
        .format(args.xnat_id, ', '.join(args.scan_ids)))
