import os
import shutil
import tempfile
import shutil
from unittest import TestCase
from xnatutils.get_ import get_from_xml
from xnatutils import get

TEST_DATA_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "data"))


class XnatGetTest(TestCase):

    test_proj = 'TEST004'
    test_num_subjs = 6

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_get(self):
        get(self.test_proj, self.tmpdir, subject_dirs=True)
        self.assertEqual(sorted(os.listdir(self.tmpdir)), self._subjects)

    def test_filtering(self):
        get('{}_..._MR01'.format(self.test_proj), self.tmpdir,
            with_scans=['two'], without_scans=['source'],
            project_id=self.test_proj)
        matching = ['{}_{:03}_MR01'.format(self.test_proj, i)
                    for i in (3, 4, 5)]
        self.assertEqual(sorted(os.listdir(self.tmpdir)), matching)

    def test_select_scans(self):
        get(self.test_proj, self.tmpdir,
            with_scans=['source'], scans=['source'])
        matching = ['{}_{:03}_MR01'.format(self.test_proj, i)
                    for i in (1, 2, 6)]
        self.assertEqual(sorted(os.listdir(self.tmpdir)), matching)
        for d in matching:
            self.assertEqual(os.listdir(os.path.join(self.tmpdir, d)),
                             ['source-source.nii.gz'])

    def test_non_dicom(self):
        get('MRH017_100_MR01', self.tmpdir)
        print(os.listdir(os.path.join(self.tmpdir, 'MRH017_100_MR01')))
        print('done')

    def test_secondary(self):
        get('MRH084_025_MR01', self.tmpdir)
        print(os.listdir(os.path.join(self.tmpdir, 'MRH084_025_MR01')))
        print('done')

    @property
    def _subjects(self):
        return ['{}_{:03}'.format(self.test_proj, i)
                for i in range(1, self.test_num_subjs + 1)]

    def test_no_scan_id(self):
        self.tmpdir = tempfile.mkdtemp()
        get('MMH008_CON007_MRPT01', self.tmpdir, scans='JPG_.*')
        get('MMH008_CON007_MRPT01', self.tmpdir, scans='Localiser')
        print(os.listdir(os.path.join(self.tmpdir, 'MMH008_CON007_MRPT01')))


    def test_xml_get(self):
        get_from_xml(os.path.join(TEST_DATA_DIR, 'noBIDS0020.xml'),
                     self.tmpdir, keep_original_filenames=True)
        print(os.listdir(self.tmpdir))
