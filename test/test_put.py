import tempfile
import os.path
from unittest import TestCase
from xnatutils import put, connect


class XnatPutTest(TestCase):

    session_label_template = 'TEST006_S099_{}0{}'
    test_files = {
        'EEG': {
            'NH': (['foo.dat', 'bar.cnt', 'wee.prs'], 'EEG_FRMT')}}
    modality_to_session_cls = {'MR': 'MrSessionData',
                               'EEG': 'EegSessionData'}

    def setUp(self):
        self.mbi_xnat = connect()
        self.delete_subject()

    def tearDown(self):
        self.delete_subject()
        self.mbi_xnat.disconnect()

    def test_put(self):
        for modality, datasets in self.test_files.items():
            for dname, (fnames, resource_name) in datasets.items():
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
                    dname, *fpaths, create_session=True,
                    resource_name=resource_name)
                # Put using directory as argument
                put(self.get_session_label(modality, 2),
                    dname, temp_dir, create_session=True,
                    resource_name=resource_name)
                for visit_id in (1, 2):
                    session = self.get_session(modality, visit_id)
                    self.assertEqual(
                        sorted(
                            os.path.basename(f)
                            for f in session.scans[
                                dname].resources[resource_name].files.keys()),
                        sorted(fnames))
            dataset_names = session.scans.keys()
            self.assertEqual(
                sorted(dataset_names), sorted(datasets.keys()))

    def get_session_label(self, modality, visit_id):
        return self.session_label_template.format(modality, visit_id)

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
        return self.mbi_xnat.projects[self.project_id]

    @property
    def subject(self):
        return self.mbi_xnat.classes.SubjectData(
            label=self.subject_id, parent=self.project)

    @property
    def project_id(self):
        return self.session_label_template.split('_')[0]

    @property
    def subject_id(self):
        return '_'.join(self.session_label_template.split('_')[:2])
