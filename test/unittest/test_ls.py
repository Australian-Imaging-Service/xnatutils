from unittest import TestCase
from xnatutils import ls, connect
from xnatutils.exceptions import XnatUtilsKeyError


class XnatLsTest(TestCase):

    test_proj = 'TEST004'
    test_num_subjs = 6

    def test_ls(self):
        self.assertEqual(ls(self.test_proj), self._subjects)

    def test_outer_connect(self):
        with connect() as login:
            self.assertEqual(ls(self.test_proj, connection=login),
                             self._subjects)
            # Check to see that the context hasn't been closed by the first
            # ls call
            self.assertEqual(ls(self.test_proj, connection=login),
                             self._subjects)

    def test_list_subject(self):
        self.assertEqual(
            ls('{}_001'.format(self.test_proj)),
            ['{}_001_MR01'.format(self.test_proj)])

    def test_filtering(self):
        self.assertEqual(
            ls('{}_..._MR01'.format(self.test_proj), datatype='session',
               with_scans=['two'], without_scans=['source'],
               project_id=self.test_proj),
            ['{}_{:03}_MR01'.format(self.test_proj, i) for i in (3, 4, 5)])

#     def test_date_filtering(self):
#         sessions = ls(
#             '{}_..._MR01'.format(self.test_proj), datatype='session',
#             before=None, after=None, project_id=self.test_proj)
#         self.assertEqual(
#             sessions,
#             ['{}_{:03}_MR01'.format(self.test_proj, i) for i in (3, 4, 5)])

    def test_missing(self):
        self.assertRaises(
            XnatUtilsKeyError,
            ls,
            'BOOGIE_WOOGIE_WOO')

    def test_scan_ls(self):
        self.assertEqual(
            ls('{}_001_MR01'.format(self.test_proj)),
            ['source', 'three', 'two'])

    @property
    def _subjects(self):
        return ['{}_{:03}'.format(self.test_proj, i)
                for i in range(1, self.test_num_subjs + 1)]

#     def test_with_without_scans(self):
#         print '\n'.join(
#             ls('MRH017_14(1|2)_MR01_PROC', with_scans=['fmri_melodic.*'],
#                without_scans=['fmri_fix_dir'], datatype='session'))
