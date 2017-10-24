from xnat.exceptions import XNATValueError
import tempfile
from unittest import TestCase
from xnatutils import put, connect


class XnatGetTest(TestCase):

    test_eeg_session = 'TEST006_S001_EEG01'
    test_scan_name = 'test_scan'

    def setUp(self):
        self.mbi_xnat = connect()
        self._delete_session()

    def tearDown(self):
        self._delete_session()
        self.mbi_xnat.disconnect()

    def test_put(self):
        _, fpath = tempfile.mkstemp('.dat', 'foo')
        with open(fpath, 'w') as f:
            f.write('test')
        put(fpath, self.test_eeg_session, self.test_scan_name,
            create_session=True)
        session = self._get_session()
        scan_names = session.scans.keys()
        self.assertEqual(scan_names, self.test_scan_name)

    def _get_session(self):
        return self.mbi_xnat.classes.EegSessionData(self.test_eeg_session)

    def _delete_session(self):
        try:
            self._get_session().delete()
        except XNATValueError:
            pass
