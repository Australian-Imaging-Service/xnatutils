#!/usr/bin/env python
from argparse import ArgumentParser
import subprocess as sp
import os.path
from collections import defaultdict
from itertools import groupby, product
import dicom
import shutil
import tempfile
import getpass
import logging
import sys
from nianalysis.archive.daris.login import DarisLogin

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
parser.add_argument('--session', type=int, nargs=2, default=[],
                    METAVAR=('SUBJECT', 'SESSION'),
                    help=("The subject and session to check. If not provided "
                          "all sessions are checked"))
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


if args.project.startswith('MRH'):
    modality = 'MR'
elif args.project.startswith('MMH'):
    modality = 'MRPT'
else:
    assert False, "Unrecognised modality {}".format(args.project)


def dataset_sort_key(daris_id):
    return tuple(int(p) for p in daris_id.split('.'))


def session_group_key(daris_id):
    return tuple(int(p) for p in daris_id.split('.')[:6])


def run_check(args, modality):
    tmp_dir = tempfile.mkdtemp()
    try:
        with open('{}/.daris_password'.format(os.environ['HOME'])) as f:
            password = f.read()
    except OSError:
        password = getpass.getpass("DaRIS manager password: ")
    with DarisLogin(domain='system', user='manager',
                    password=password) as daris:
        project_daris_id = mbi_to_daris[args.project]
        datasets = daris.query(
            "cid starts with '1008.2.{}{}' and model='om.pssd.dataset'"
            .format(project_daris_id), '.'.join(args.session), cid_index=True)
        cids = sorted(datasets.iterkeys(),
                      key=dataset_sort_key)
        for session_id, dataset_cids in groupby(cids, key=session_group_key):
            dataset_cids = list(dataset_cids)  # Convert iterator to list
            subject_id, method_id, study_id = (
                int(p) for p in session_id.split('.')[3:])
            if method_id != 1:
                continue
            match = True
            # Create dictionary mapping study-id to archive paths
            xnat_session = '{}_{:03}_{}{:02}'.format(
                args.project, subject_id, modality, study_id)
            xnat_session_path = xnat_path = os.path.join(
                xnat_store_prefix, args.project, 'arc001', xnat_session,
                'SCANS')
            if not os.path.exists(xnat_session_path):
                logger.error('1008.2.{}.{}.1.{}: missing session {}'
                             .format(args.project, subject_id, method_id,
                                     study_id, xnat_session))
                continue
            study2xnat = {}
            for dataset_id in os.listdir(xnat_session_path):
                xnat_dataset_path = os.path.join(str(dataset_id), 'DICOM')
                try:
                    study_id = os.listdir(xnat_dataset_path)[0].split('-')[0]
                except IndexError:
                    logger.error('{} directory empty'
                                 .format(xnat_dataset_path))
                    continue
                study2xnat[study_id] = xnat_dataset_path
            # Unzip DaRIS datasets and compare with XNAT
            match = True
            for cid in dataset_cids:
                src_zip_path = os.path.join(
                    daris_store_prefix,
                    datasets[cid].url[len(url_prefix):])
                unzip_path = os.path.join(tmp_dir, cid)
                os.mkdir(unzip_path)
                sp.check_call('unzip -q {} -d {}'.format(src_zip_path,
                                                         unzip_path),
                              shell=True)
                study_id = sp.check_output(
                    "dcmdump {}/0001.dcm | grep '(0020,000d)' | head -n 1  | "
                    "awk '{print $3}' | sed 's/[][]//g'".format(unzip_path),
                    shell=True)
                try:
                    xnat_path = study2xnat[study_id]
                except KeyError:
                    logger.error('{}: missing dataset {}.{} ({})'.format(
                        cid, xnat_session, cid.split('.')[-1], study_id))
                    match = False
                    continue
                if not compare_datasets(xnat_path, unzip_path, cid,
                                        xnat_session, dataset_id):
                    match = False
                shutil.rmtree(unzip_path, ignore_errors=True)
            if match:
                logger.info('{}: matches ({})'.format(cid, xnat_session))
        shutil.rmtree(tmp_dir)


class WrongEchoTimeException(Exception):
    pass


def compare_dicom_elements(xnat_elem, daris_elem, prefix, ns=None):
    if ns is None:
        ns = []
    name = '.'.join(ns)
    if isinstance(daris_elem, dicom.dataset.Dataset):
        # Check to see if echo times match and throw WrongEchoTimeException
        # if they don't
        if ('0018', '0081') in daris_elem:
            try:
                if (daris_elem[('0018', '0081')].value !=
                        xnat_elem[('0018', '0081')].value):
                    raise WrongEchoTimeException
            except KeyError:
                logger.error(
                    "{}xnat scan does not have echo time while daris does")
                return False
        for d in daris_elem:
            try:
                x = xnat_elem[d.tag]
            except KeyError:
                logger.error("{}missing {}".format(prefix, d.name))
                return False
            if not compare_dicom_elements(x, d, prefix, ns=ns + [d.name]):
                return False
    elif isinstance(daris_elem.value, dicom.sequence.Sequence):
        if len(xnat_elem.value) != len(daris_elem.value):
            logger.error(
                "{}mismatching length of '{}' sequence (xnat:{} vs "
                "daris:{})".format(prefix, name, len(xnat_elem.value),
                                   len(daris_elem.value)))
            return False
        for x, d in zip(xnat_elem.value, daris_elem.value):
            if not compare_dicom_elements(x, d, prefix, ns=ns):
                return False
    else:
        if xnat_elem.name == 'Patient Comments':
            # Skip patient comments containing xnat id string
            return True
        xnat_value = xnat_elem.value
        daris_value = daris_elem.value
        try:
            xnat_value = xnat_value.strip()
            daris_value = daris_value.strip()
        except AttributeError:
            pass
        if xnat_value != daris_value:
            include_diff = True
            try:
                if max(len(xnat_value), len(daris_value)) > 100:
                    include_diff = False
            except TypeError:
                pass
            if include_diff:
                diff = ('(xnat:{} vs daris:{})'
                              .format(xnat_value, daris_value))
            else:
                diff = ''
            logger.error("{}mismatching value for '{}'{}".format(
                prefix, name, diff))
            return False
    return True


def compare_datasets(xnat_path, daris_path, cid, xnat_session, dataset_id):
    daris_files = [f for f in os.listdir(daris_path)
                   if f.endswith('.dcm')]
    xnat_files = [f for f in os.listdir(xnat_path)
                  if f.endswith('.dcm')]
    if len(daris_files) != len(xnat_files):
        logger.error("{}: mismatching number of dicoms in dataset "
                     "{}.{} (xnat {} vs daris {})"
                     .format(cid, xnat_session, dataset_id,
                             len(xnat_files), len(daris_files)))
        return False
    xnat_fname_map = defaultdict(list)
    for fname in xnat_files:
        dcm_num = int(fname.split('-')[-2])
        xnat_fname_map[dcm_num].append(fname)
    max_mult = max(len(v) for v in xnat_fname_map.itervalues())
    min_mult = max(len(v) for v in xnat_fname_map.itervalues())
    if max_mult != min_mult:
        logger.error("{}: Inconsistent numbers of echos in {}.{}"
                     .format(cid, xnat_session, dataset_id))
        return False
    daris_fname_map = defaultdict(list)
    for fname in daris_files:
        dcm_num = int(sp.check_output(
            "dcmdump {} | grep '(0020,0013)' | head -n 1  | awk '{print $3}' |"
            " sed 's/[][]//g'".format(fname),
            shell=True))
        daris_fname_map[dcm_num].append(fname)
    if sorted(xnat_fname_map.keys()) != sorted(daris_fname_map.keys()):
        logger.error("{}: DICOM instance IDs don't match "
                     "{}.{}:\nxnat: {}\ndaris: {}\n".format(
                         cid, xnat_session, dataset_id,
                         xnat_fname_map.keys(),
                         daris_fname_map.keys()))
        return False
    print xnat_path
    print daris_path
    for dcm_num in daris_fname_map:
        num_echoes = len(daris_fname_map[dcm_num])
        assert len(xnat_fname_map[dcm_num]) == num_echoes
        # Try all combinations of echo times
        for i, j in product(range(num_echoes), range(num_echoes)):
            try:
                daris_fpath = os.path.join(daris_path,
                                           daris_fname_map[dcm_num][i])
                try:
                    xnat_fpath = os.path.join(
                        xnat_path, xnat_fname_map[dcm_num][j])
                except KeyError:
                    logger.error('{}: missing file ({}.{}.{})'.format(
                        cid, xnat_session, dataset_id, dcm_num))
                    return False
                xnat_elem = dicom.read_file(xnat_fpath)
                daris_elem = dicom.read_file(daris_fpath)
                if not compare_dicom_elements(
                    xnat_elem, daris_elem,
                        '{}: dicom mismatch in {}.{}.{}({}) -'.format(
                            cid, xnat_session, dataset_id, dcm_num, 0)):
                    return False
            except WrongEchoTimeException:
                # Try a different combination until echo times match
                pass
    return True


run_check(args, modality)
