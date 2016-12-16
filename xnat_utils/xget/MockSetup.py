
import Main
import Config
import ProjectUtils
import SessionUtils
from pyxnat import *

dict = {'proc': None,
        'quality': 'ALL',
        'f': 'test/sessionString.txt',
        's': None,
        'quiet': False,
        'o': 'tmp',
        'p': 'testuser',
        'host': 'localhost:8080/xnat',
        'r': None,
        'u': 'testuser',
        'proj': None,
        'readme': False,
        'z': False,
        'user_session': None,
        'passfile': xpass.path(),
        't': None}


def mock():
    return Config.Model(dict, "")
args = mock()
conn = Main.createConnection(
    args.getHost(),
    args.getUser(),
    args.getPass(),
    args.getOutputDir())
