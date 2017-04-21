from unittest import TestCase
from xnatutils import ls, connect


class XnatLsTest(TestCase):

    test_proj = 'TEST004'
    test_num_subjs = 3

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
        pass

    @property
    def _subjects(self):
        return ['{}_{:03}'.format(self.test_proj, i)
                for i in xrange(1, self.test_num_subjs + 1)]
