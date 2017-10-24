from xnat.exceptions import XNATValueError
import tempfile
from unittest import TestCase
from xnatutils import put, connect


class XnatPutTest(TestCase):

    session_label_template = 'TEST006_S001_{}01'
    test_files = {'MR': ['foo.dat', 'bar.cnt', 'wee.prs']}
    modality_to_session_cls = {'MR': 'MrSessionData',
                               'EEG': 'EegSessionData'}

    def setUp(self):
        self.mbi_xnat = connect()
        project_id, subj_id = self.session_label_template.split('_')[:2]
        self.subject = self.mbi_xnat.projects[project_id].subjects[
            '_'.join((project_id, subj_id))]
        self.delete_sessions()

    def tearDown(self):
        self.delete_sessions()
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
            self.assertEqual(scan_names, self.test_files[modality])

    def get_session_label(self, modality):
        return self.session_label_template.format(modality)

    def get_session(self, modality):
        return self.subject.experiments[self.get_session_label(modality)]

    def delete_sessions(self):
        for modality in self.test_files:
            try:
                self.get_session(modality).delete()
            except KeyError:
                pass
