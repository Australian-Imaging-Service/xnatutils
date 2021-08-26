import sys
import tempfile
import os.path
import logging
from unittest import TestCase
from xnatutils import put, connect

logger = logging.getLogger('xnat-utils')
# logger.setLevel(logging.WARNING)
# handler = logging.FileHandler('test_put.log')
# handler.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)

class XnatPutTest(TestCase):

    server = 'https://xnat.sydney.edu.au'
    project_id = 'XNATUTILSTEST'
    subject_id = 'S04'
    session_label_template = (
        project_id + '_' + subject_id + '_{modality}{visit}')
    test_files = {
        # 'MR': {
        #     'scan1': (['1.dcm', '2.dcm', '3.dcm'], 'DICOM')},
        # 'EEG': {
        #     'recording1': (['foo.els'], 'EEG')},
        'XC': {
            'scan1': (['foo.dat', 'bar.txt', 'goo.csv'], 'EXT_CAM')}
        }
    modality_to_session_cls = {'MR': 'MrSessionData',
                               'XC': 'XcSessionData',
                               'EEG': 'EegSessionData'}

    def setUp(self):
        self.xnat_login = connect(server=self.server, loglevel='DEBUG',
                                  logger=logger)
        self.delete_subject()

    def tearDown(self):
        # self.delete_subject()
        self.xnat_login.disconnect()

    def test_put(self):
        for modality, scans in self.test_files.items():
            for scan_type, (fnames, resource_name) in scans.items():
                temp_dir = tempfile.mkdtemp()
                # Create test files to upload
                fpaths = []
                for fname in fnames:
                    fpath = os.path.join(temp_dir, fname)
                    with open(fpath, 'w') as f:
                        f.write('test')
                    fpaths.append(fpath)
                # Put using filenames as arguments
                put(self.get_session_label(modality, 1),
                    scan_type, *fpaths, create_session=True,
                    subject_id=self.subject_id,
                    project_id=self.project_id,
                    modality=modality,
                    resource_name=resource_name)
                # Put using directory as argument
                put(self.get_session_label(modality, 2),
                    scan_type, temp_dir, create_session=True,
                    subject_id=self.subject_id,
                    project_id=self.project_id,
                    modality=modality,
                    resource_name=resource_name)
                for visit_id in (1, 2):
                    session = self.get_session(modality, visit_id)
                    self.assertEqual(
                        sorted(
                            os.path.basename(f)
                            for f in session.scans[
                                scan_type].resources[
                                    resource_name].files.keys()),
                        sorted(fnames))
            scan_names = session.scans.keys()
            self.assertEqual(
                sorted(scan_names), sorted(scans.keys()))

    def get_session_label(self, modality, visit_id):
        return self.session_label_template.format(modality=modality,
                                                  visit=visit_id)

    def get_session(self, modality, visit_id):
        return self.subject.experiments[
            self.get_session_label(modality, visit_id)]

    def delete_subject(self):
        try:
            self.project.subjects[self.subject_id].delete()
        except KeyError:
            pass

    @property
    def project(self):
        return self.xnat_login.projects[self.project_id]

    @property
    def subject(self):
        return self.xnat_login.classes.SubjectData(
            label=self.subject_id, parent=self.project)
