#!/usr/bin/env python
from argparse import ArgumentParser
import subprocess as sp
import os.path
import shutil
from nianalysis.archive.daris import DarisSession

parser = ArgumentParser()
parser.add_argument('project', type=str,
                    help='ID of the project to import')
parser.add_argument('daris_password', type=str,
                    help="System/manager password for daris")
parser.add_argument('--subjects', nargs='+', default=None, type=int,
                    help="IDs of the subjects to import")
args = parser.parse_args()

fm2darisID = {
    'MRH055': 100, 'MRH061': 101, 'MRH062': 105, 'MRH063': 106, 'MRH064': 107,
    'MRH065': 110, 'MRH066': 112, 'MRH067': 115, 'MRH068': 116, 'MRH069': 117,
    'MRH070': 118, 'MRH071': 119, 'MRH011': 12, 'MRH023': 12, 'MRH072': 120,
    'MRH073': 123, 'MRH074': 124, 'MRH075': 125, 'MRH076': 126, 'MRH077': 127,
    'MRH078': 128, 'MRH079': 129, 'MRH080': 134, 'MRH081': 137, 'MMH002': 138,
    'MRH082': 139, 'MRH012': 14, 'MRH083': 143, 'MRH084': 145, 'MMH003': 147,
    'MRH001': 17, 'MRH018': 17, 'MRH019': 21, 'MRH015': 22, 'MRH003': 23,
    'MRH006': 25, 'MRH007': 27, 'MRH028': 28, 'MRH000': 3, 'MRH024': 30,
    'MRH009': 32, 'MRH021': 33, 'MRH026': 34, 'MRH022': 36, 'MRH025': 38,
    'MRH027': 44, 'MRH031': 45, 'MRH034': 48, 'MRH033': 49, 'MRH030': 52,
    'MRH036': 53, 'MRH032': 54, 'MRH037': 56, 'MRH035': 57, 'MRH032': 58,
    'MRH038': 60, 'MRH039': 62, 'MRH040': 63, 'MRH041': 65, 'MRH042': 66,
    'MRH043': 68, 'MRH044': 69, 'MRH045': 70, 'MRH017': 71, 'MRH046': 72,
    'MRH047': 73, 'MRH048': 74, 'MRH049': 77, 'MRH051': 81, 'MRH054': 92,
    'MRH056': 95, 'MRH057': 96, 'MRH058': 97, 'MRH059': 98, 'MRH060': 99,
    'MMH000': 133}

url_prefix = 'file:/srv/mediaflux/mflux/volatile/stores/pssd/'
store_prefix = '/mnt/rdsi/mf-data/stores/pssd'
temp_dir = '/mnt/rdsi/xnat-import-temp/'


with DarisSession(domain='system', user='manager',
                  password=args.daris_password) as daris:
    proj_dir = os.path.join(temp_dir, args.project)
    shutil.rmtree(proj_dir, ignore_errors=True)
    os.mkdir(proj_dir)
    project_daris_id = fm2darisID[args.project]
    datasets = daris.query(
        "cid starts with '1008.2.{}' and model='om.pssd.dataset'"
        .format(project_daris_id), cid_index=True)
    cids = sorted(datasets.iterkeys())
    for cid in cids:
        subject_id, method_id, study_id = (int(i) for i in cid.split('.')[3:6])
        if method_id == 1 and (args.subjects is None or
                               subject_id in args.subjects):
            src_zip_path = os.path.join(store_prefix,
                                        datasets[cid].url[len(url_prefix):])
            unzip_path = os.path.join(proj_dir, cid)
            os.mkdir(unzip_path)
            # Unzip DICOMs
            sp.check_call('unzip {} -d {}'.format(src_zip_path, unzip_path),
                    shell=True)
            # Modify DICOMs to insert object identification information
            sp.check_call(
                'dcmodify -i "(0010,4000)=project: {project}; subject: '
                '{subject}; session: {session}" {path}/*.dcm'.format(
                    project=args.project, subject=subject_id,
                    session=study_id, path=unzip_path), shell=True)
            print unzip_path
            break
#     shutil.rmtree(proj_dir, ignore_errors=True)
