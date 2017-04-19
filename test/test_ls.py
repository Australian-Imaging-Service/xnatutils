from unittest import TestCase
from xnatutils import ls, connect


class XnatLsTest(TestCase):

    test003_sess = [
        'MRH017_011', 'MRH017_037', 'MRH017_038', 'MRH017_048', 'MRH017_086',
        'MRH017_088', 'MRH017_135', 'MRH017_210', 'MRH017_228', 'MRH017_292',
        'MRH017_302', 'MRH017_303', 'MRH017_368', 'MRH017_391', 'MRH017_425',
        'MRH017_450', 'MRH017_488', 'MRH017_491', 'MRH017_512', 'MRH017_550']

    def test_ls(self):
        self.assertEqual(ls('TEST003'), self.test003_sess)

    def test_outer_connect(self):
        with connect() as mbi_xnat:
            self.assertEqual(ls('TEST003', connection=mbi_xnat),
                             self.test003_sess)
            # Check to see that the context hasn't been closed by the first
            # ls call
            self.assertEqual(ls('TEST003', connection=mbi_xnat),
                             self.test003_sess)
        self.assertRaises(
            AttributeError,
            ls,
            'TEST003',
            connection=mbi_xnat)
