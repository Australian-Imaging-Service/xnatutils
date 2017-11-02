import os
import shutil
import tempfile
from unittest import TestCase
from xnatutils import get


class XnatGetTest(TestCase):

    test_proj = 'TEST004'
    test_num_subjs = 6

    def test_get(self):
        tmpdir = tempfile.mkdtemp()
        get(self.test_proj, tmpdir, subject_dirs=True)
        self.assertEqual(sorted(os.listdir(tmpdir)), self._subjects)
        shutil.rmtree(tmpdir)

    def test_filtering(self):
        tmpdir = tempfile.mkdtemp()
        get('{}_..._MR01'.format(self.test_proj), tmpdir,
            with_scans=['two'], without_scans=['source'])
        matching = ['{}_{:03}_MR01'.format(self.test_proj, i)
                    for i in (3, 4, 5)]
        self.assertEqual(os.listdir(tmpdir), matching)
        shutil.rmtree(tmpdir)

    def test_select_scans(self):
        tmpdir = tempfile.mkdtemp()
        get(self.test_proj, tmpdir,
            with_scans=['source'], scans=['source'])
        matching = ['{}_{:03}_MR01'.format(self.test_proj, i)
                    for i in (1, 2, 6)]
        self.assertEqual(sorted(os.listdir(tmpdir)), matching)
        for d in matching:
            self.assertEqual(os.listdir(os.path.join(tmpdir, d)),
                             ['source-source.nii.gz'])
        shutil.rmtree(tmpdir)

    def test_non_dicom(self):
        tmpdir = tempfile.mkdtemp()
        get('MRH017_100_MR01', tmpdir)
        print os.listdir(os.path.join(tmpdir, 'MRH017_100_MR01'))
        print 'done'

    def test_secondary(self):
        tmpdir = tempfile.mkdtemp()
        get('MRH084_025_MR01', tmpdir)
        print os.listdir(os.path.join(tmpdir, 'MRH084_025_MR01'))
        print 'done'

    @property
    def _subjects(self):
        return ['{}_{:03}'.format(self.test_proj, i)
                for i in xrange(1, self.test_num_subjs + 1)]
