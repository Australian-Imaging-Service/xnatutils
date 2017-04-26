#!/usr/bin/env python
from argparse import ArgumentParser
import subprocess as sp
import os.path
import shutil
import tempfile
import getpass
import logging
import hashlib
import sys
from nianalysis.archive.daris import DarisLogin

resources_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '_resources'))
sys.path.insert(0, resources_path)
from mbi_to_daris_number import mbi_to_daris  # @IgnorePep8 @UnresolvedImport


url_prefix = 'file:/srv/mediaflux/mflux/volatile/stores/pssd/'
daris_store_prefix = '/mnt/rdsi/mf-data/stores/pssd'
xnat_store_prefix = '/mnt/vicnode/archive/'


def checksum(fpath):
    return hashlib.md5(open(fpath, 'rb').read()).hexdigest()

parser = ArgumentParser()
parser.add_argument('project', type=str,
                    help='ID of the project to import')
parser.add_argument('--log_file', type=str, default=None,
                    help='Path of the logfile to record discrepencies')
parser.add_argument('--display_log', action='store_true',
                    help="Whether to print log to screen")
args = parser.parse_args()

if args.project.startswith('MRH'):
    modality = 'MR'
elif args.project.startswith('MMH'):
    modality = 'MRPT'
else:
    assert False, "Unrecognised modality {}".format(args.project)

tmp_dir = tempfile.mkdtemp()

password = getpass.getpass("DaRIS manager password: ")

log_path = args.log_file if args.log_file else os.path.join(
    os.getcwd(), '{}_checksum.log'.format(args.project))
logger = logging.getLogger('check_imported')


file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(file_handler)


if args.display_log:
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(logging.Formatter(
        "%(levelname)s - %(message)s"))
    logger.addHandler(stdout_handler)

with DarisLogin(domain='system', user='manager',
                password=password) as daris, open(log_path, 'w') as log_file:
    project_daris_id = mbi_to_daris[args.project]
    datasets = daris.query(
        "cid starts with '1008.2.{}' and model='om.pssd.dataset'"
        .format(project_daris_id), cid_index=True)
    cids = sorted(datasets.iterkeys(),
                  key=lambda x: tuple(int(p) for p in x.split('.')))
    for cid in cids:
        subject_id, method_id, study_id, dataset_id = (
            int(i) for i in cid.split('.')[3:])
        if method_id == 1:
            xnat_session = '{}_{:03}_{}{:02}'.format(
                args.project, subject_id, modality, study_id)
            xnat_path = os.path.join(
                xnat_store_prefix, args.project, 'arc001', xnat_session,
                'SCANS', str(dataset_id), 'DICOM')
            if not os.path.exists(xnat_path):
                logger.error('{}: missing dataset ({} - {})\n'.format(
                    cid, xnat_session, xnat_path))
                continue
            src_zip_path = os.path.join(daris_store_prefix,
                                        datasets[cid].url[len(url_prefix):])
            unzip_path = os.path.join(tmp_dir, cid)
            shutil.rmtree(unzip_path, ignore_errors=True)
            os.mkdir(unzip_path)
            # Unzip DICOMs
            sp.check_call('unzip {} -d {}'.format(src_zip_path, unzip_path),
                          shell=True)
            match = True
            for fname in os.listdir(unzip_path):
                if fname.endswith('.dcm'):
                    daris_md5 = checksum(os.path.join(unzip_path, fname))
                    try:
                        xnat_md5 = checksum(os.path.join(xnat_path, fname))
                    except OSError:
                        logger.error('{}: missing file ({}.{})\n'.format(
                            cid, xnat_session, fname))
                        match = False
                    if daris_md5 != xnat_md5:
                        logger.error('{}: incorrect checksum ({}.{})\n'
                                     .format(cid, xnat_session, fname))
                        match = False
            if match:
                logger.info('{}: matches ({})'.format(cid, xnat_session))
            shutil.rmtree(unzip_path, ignore_errors=True)
    shutil.rmtree(tmp_dir)
