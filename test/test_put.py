import tempfile
from unittest import TestCase
from xnatutils import put, connect


class XnatPutTest(TestCase):

    session_label_template = 'TEST006_S001_{}01'
    test_files = {'EEG': ['foo.dat', 'bar.cnt', 'wee.prs']}
    modality_to_session_cls = {'MR': 'MrSessionData',
                               'EEG': 'EegSessionData'}

    def setUp(self):
        self.mbi_xnat = connect()
        self.delete_subject()

    def tearDown(self):
        self.delete_subject()
        self.mbi_xnat.disconnect()

    def test_put(self):
        for modality, fnames in self.test_files.iteritems():
            for fname in fnames:
                base, ext = fname.split('.')
                _, fpath = tempfile.mkstemp('.' + ext, base)
                with open(fpath, 'w') as f:
                    f.write('test')
                put(fpath, self.get_session_label(modality),
                    base, create_session=True)
            session = self.get_session(modality)
            scan_names = session.scans.keys()
            self.assertEqual(
                scan_names,
                [f.split('.')[0] for f in self.test_files[modality]])

    def get_session_label(self, modality):
        return self.session_label_template.format(modality)

    def get_session(self, modality):
        return self.subject.experiments[self.get_session_label(modality)]

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
