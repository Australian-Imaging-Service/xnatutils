import string
import os
import csv
import warnings
import sys

# Extracting session ids
# args{} -> str -> [str]


def getSessionIds(dict, stdin):
    sessionIds = []
    if dict["s"]:
        sessionIds.extend(unComma(dict["s"]))
    if dict["f"]:
        [sessionIds.extend(unComma(r))
         for r in readSessionFile(dict["f"])]
    sessionIds = [item for sublist in sessionIds for item in sublist]
    return list(set(sessionIds))

# str -> [str]


def unComma(sessionList):
    ret = []
    r = csv.reader([sessionList], skipinitialspace=True)
    for row in r:
        ret.append(row)
    return filter(lambda str: str is not '', ret)

# filepath -> [str]


def readSessionFile(f):
    sessions = []
    if os.path.exists(f) and os.path.isfile(f):
        infile = open(f)
        sessions = map(lambda l: l.strip(' \t\n\r'), infile.readlines())
    else:
        warnings.warn("The session file " + f + " does not exist", UserWarning)
    return filter(lambda str: str is not '', sessions)

# Output dir creation


def makeOutputDir(f):
    if not os.path.exists(f):
        if not os.path.isdirectory(f):
            raise Exception("Output directory: " + f + " is not a directory")
    else:
        os.makedirs(f)

# Tests


def unCommaTest():
    print "Testing unComma"
    assert(unComma("sess1,sess2,sess3") == ["sess1", "sess2", "sess3"])
    assert(unComma("sess1,,sess3") == ["sess1", "sess3"])
    assert(unComma("sess1,   ,sess3") == ["sess1", "sess3"])
    assert(unComma("se\ss1,se_ss2,se+ss3") == ["se\ss1", "se_ss2", "se+ss3"])


def readSessionFileTest():
    print "Testing readSessionFile"
    testfile = "test/sessionString.txt"
    assert(readSessionFile(testfile) == ["sess1,sess2,sess3"])


def getSessionIdsTest():
    print "Testing getSessionIds"
    testfile = "test/sessionString.txt"
    sessStringList = "sessA, sessB, sessC"
    dict = {"s": sessStringList, "f": testfile}
    assert(getSessionIds(dict, "") == ['sess3', 'sess2', 'sess1',
                                       'sessC', 'sessB', 'sessA'])
    sessDupString = "sess1,sess2,sess3"
    dict2 = {"s": sessDupString, "f": testfile}
    assert(getSessionIds(dict2, "") == ['sess3', 'sess2', 'sess1'])


def test():
    unCommaTest()
    readSessionFileTest()
    getSessionIdsTest()
