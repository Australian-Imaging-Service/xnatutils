#!/usr/bin/env python
from argparse import ArgumentParser
import subprocess as sp
import os.path
from collections import defaultdict
import dicom
import shutil
import tempfile
import getpass
import logging
import sys
from nianalysis.archive.daris import DarisLogin

resources_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '_resources'))
sys.path.insert(0, resources_path)
from mbi_to_daris_number import mbi_to_daris  # @IgnorePep8 @UnresolvedImport


url_prefix = 'file:/srv/mediaflux/mflux/volatile/stores/pssd/'
daris_store_prefix = '/mnt/rdsi/mf-data/stores/pssd'
xnat_store_prefix = '/mnt/vicnode/archive/'


parser = ArgumentParser()
parser.add_argument('project', type=str,
                    help='ID of the project to import')
parser.add_argument('--log_file', type=str, default=None,
                    help='Path of the logfile to record discrepencies')
args = parser.parse_args()

log_path = args.log_file if args.log_file else os.path.join(
    os.getcwd(), '{}_checksum.log'.format(args.project))
logger = logging.getLogger('check_imported')


file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(file_handler)

stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(logging.Formatter(
    "%(levelname)s - %(message)s"))
logger.addHandler(stdout_handler)


def compare_dicoms(xnat_elem, daris_elem, prefix, ns=None, log=True):
    if ns is None:
        ns = []
    name = '.'.join(ns)
    match = True
    if isinstance(daris_elem, dicom.dataset.Dataset):
        for d in daris_elem:
            try:
                x = xnat_elem[d.tag]
            except KeyError:
                if log:
                    logger.error("{}missing {}".format(prefix,
                                                       daris_elem.name))
            if not compare_dicoms(x, d, prefix, ns=ns + [d.name]):
                match = False
    elif isinstance(daris_elem.value, dicom.sequence.Sequence):
        if len(xnat_elem.value) != len(daris_elem.value):
            if log:
                logger.error(
                    "{}mismatching length of '{}' sequence (xnat:{} vs "
                    "daris:{})".format(prefix, name, len(xnat_elem.value),
                                       len(daris_elem.value)))
        for x, d in zip(xnat_elem.value, daris_elem.value):
            if not compare_dicoms(x, d, prefix, ns=ns):
                match = False
    else:
        if xnat_elem.value != daris_elem.value:
            include_diff = True
            try:
                if max(len(xnat_elem.value), len(daris_elem.value)) > 100:
                    include_diff = False
            except TypeError:
                pass
            if include_diff:
                diff = ('(xnat:{} vs daris:{})'
                              .format(xnat_elem.value, daris_elem.value))
            else:
                diff = ''
            if log:
                logger.error("{}mismatching value for '{}'{}".format(
                    prefix, name, diff))
            match = False
    return match


if args.project.startswith('MRH'):
    modality = 'MR'
elif args.project.startswith('MMH'):
    modality = 'MRPT'
else:
    assert False, "Unrecognised modality {}".format(args.project)

tmp_dir = tempfile.mkdtemp()

password = getpass.getpass("DaRIS manager password: ")


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
            src_zip_path = os.path.join(daris_store_prefix,
                                        datasets[cid].url[len(url_prefix):])
            logger.info("Checking {} ({})".format(cid, src_zip_path))
            xnat_session = '{}_{:03}_{}{:02}'.format(
                args.project, subject_id, modality, study_id)
            xnat_path = os.path.join(
                xnat_store_prefix, args.project, 'arc001', xnat_session,
                'SCANS', str(dataset_id), 'DICOM')
            if not os.path.exists(xnat_path):
                logger.error('{}: missing dataset {}.{} ({})'.format(
                    cid, xnat_session, dataset_id, xnat_path))
                continue
            unzip_path = os.path.join(tmp_dir, cid)
            shutil.rmtree(unzip_path, ignore_errors=True)
            os.mkdir(unzip_path)
            # Unzip DICOMs
            logger.info("Unzipping {}".format(src_zip_path))
            sp.check_call('unzip -q {} -d {}'.format(src_zip_path, unzip_path),
                          shell=True)
            daris_files = [f for f in os.listdir(unzip_path)
                           if f.endswith('.dcm')]
            xnat_files = [f for f in os.listdir(xnat_path)
                          if f.endswith('.dcm')]
            if len(daris_files) != len(xnat_files):
                logger.error("{}: mismatching number of dicoms in dataset "
                             "{}.{} (xnat {} vs daris {})"
                             .format(cid, xnat_session, dataset_id,
                                     len(xnat_files), len(daris_files)))
                continue
            xnat_fname_map = defaultdict(list)
            for fname in xnat_files:
                dcm_num = int(fname.split('-')[-2])
                xnat_fname_map[dcm_num].append(fname)
            max_mult = max(len(v) for v in xnat_fname_map.itervalues())
            min_mult = max(len(v) for v in xnat_fname_map.itervalues())
            if max_mult != min_mult:
                logger.error("{}: Inconsistent numbers of echos in {}.{}"
                             .format(cid, xnat_session, dataset_id))
                continue
            daris_fname_map = defaultdict(list)
            for fname in daris_files:
                dcm_num = (int(fname.split('.')[0]) + 1) // max_mult
                daris_fname_map[dcm_num].append(fname)
            if sorted(xnat_fname_map.keys()) != sorted(daris_fname_map.keys()):
                logger.error("{}: Something strange with numbers of echos in "
                             "{}.{}".format(cid, xnat_session, dataset_id))
                continue
            match = True
            if max_mult > 1:
                print unzip_path
                print xnat_path
                exit()
            for dcm_num in daris_fname_map:
                daris_fpath = os.path.join(unzip_path,
                                           daris_fname_map[dcm_num][0])
                try:
                    xnat_fpath = os.path.join(xnat_path,
                                              xnat_fname_map[dcm_num][0])
                except KeyError:
                    logger.error('{}: missing file ({}.{}.{})'.format(
                        cid, xnat_session, dataset_id, dcm_num))
                    match = False
                    continue
                xnat_elem = dicom.read_file(xnat_fpath)
                daris_elem = dicom.read_file(daris_fpath)
                match = compare_dicoms(xnat_elem, daris_elem,
                                       '{}: dicom mismatch in {}.{}.{}({}) -'
                                       .format(cid, xnat_session,
                                               dataset_id, dcm_num, 0))
            if match:
                logger.info('{}: matches ({})'.format(cid, xnat_session))
            shutil.rmtree(unzip_path, ignore_errors=True)
    shutil.rmtree(tmp_dir)
