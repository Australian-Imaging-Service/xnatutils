from unittest import TestCase
from xnatutils import ls, connect


class XnatLsTest(TestCase):

    test_proj = 'TEST004'
    test_num_subjs = 6

    def test_ls(self):
        self.assertEqual(ls(self.test_proj), self._subjects)

    def test_outer_connect(self):
        with connect() as mbi_xnat:
            self.assertEqual(ls(self.test_proj, connection=mbi_xnat),
                             self._subjects)
            # Check to see that the context hasn't been closed by the first
            # ls call
            self.assertEqual(ls(self.test_proj, connection=mbi_xnat),
                             self._subjects)
        self.assertRaises(
            AttributeError,
            ls,
            self.test_proj,
            connection=mbi_xnat)

    def test_list_subject(self):
        self.assertEqual(
            ls('{}_001'.format(self.test_proj)),
            ['{}_001_MR01'.format(self.test_proj)])

    def test_filtering(self):
        self.assertEqual(
            ls('{}_..._MR01'.format(self.test_proj), datatype='session',
               with_scans=['two'], without_scans=['source']),
            ['{}_{:03}_MR01'.format(self.test_proj, i) for i in (3, 4, 5)])

    @property
    def _subjects(self):
        return ['{}_{:03}'.format(self.test_proj, i)
                for i in xrange(1, self.test_num_subjs + 1)]

#     def test_with_without_scans(self):
#         print '\n'.join(
#             ls('MRH017_14(1|2)_MR01_PROC', with_scans=['fmri_melodic.*'],
#                without_scans=['fmri_fix_dir'], datatype='session'))
