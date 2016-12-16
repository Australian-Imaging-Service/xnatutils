import argparse
import string
import os
import csv
import warnings
import Utils
import sys
import XnatPass
import sys


parser = argparse.ArgumentParser(
    description="Download files from an XNAT Instance - TODO make this better.")
parser.add_argument('-u', type=str,
                    help="USERNAME")  # required unless -user_session
parser.add_argument('-passfile', type=str, default=os.path.expanduser('~/.xnatPass'),
                    help="Location of your XNAT pass file. Defaults to ~/.xnatPass")
parser.add_argument('-p', type=str,
                    help="PASSWORD")  # required unless -user_session
parser.add_argument('-host', type=str,
                    help="URL to XNAT based website. (i.e http://localhost/xnat)")
parser.add_argument("-s", type=str,
                    help="Session id of the desired session(s).  For multiple sessions, use comma separated ids.")
parser.add_argument("-format", nargs='?', type=str,
                    help="Image format (eg. DICOM/NIFTI)", default="ALL")
parser.add_argument("-f", type=str,
                    help="File containing session ids. One id per line")
parser.add_argument("-o", type=str,
                    help="Output directory.")
parser.add_argument("-proj", type=str,
                    help="Retrieves only sessions in this project")
parser.add_argument("-acq", nargs='?', type=str, default="ALL",
                    help="Retrieves acquired image data of the specified scan type. Takes a comma separated list of scan types. Defaults to ALL")
parser.add_argument("-start", nargs='?', type=str,
                    help="Retrieve experiments created on and AFTER this date. Uses DAYMONTHYEAR format eg.01012011 is January 1st 2010.")
parser.add_argument("-end", nargs='?', type=str,
                    help=("Retrieve experiments created on and BEFORE this date. Uses DAYMONTHYEAR format eg.01012011 is January 1st 2010."))
parser.add_argument("-ass", nargs='?', type=str, default="ALL",
                    help="Retrieves assessors for the specified sessions.Takes a comma separated list of assessor types. Defaults to ALL")
parser.add_argument("-recon", nargs='?', type=str, default="ALL",
                    help="Retrieves processed image data for the specified sessions.Takes a comma separated list of reconstruction types. Defaults to ALL")
parser.add_argument("-z", action="store_true",
                    help="Extract the downloaded zips. True if this flag is present.")
parser.add_argument("-quality", nargs="?", type=str, default='ALL',
                    help="Qualities of scans to include (usable,questionable, unusable).Defaults to ALL if not present.")
parser.add_argument("-overwrite", action="store_true", default=False,
                    help="If present overwrite an existing file, defaults to False")
parser.add_argument("-longname", action="store_true", default=False,
                    help="By default it is " +
                         "set to \"short\" meaning the zip names will be " +
                         "<session id/label + {acq|ass|recon}>.zip.\n It can also be " +
                         "set to \"long\" the behavior of which is described " +
                         "in the manual.")

# Command line argument parsing
# args{} -> ()


def validateArgs(args):
    dict = vars(args)

    # XNAT connection information
    userAuth = argGroup(dict, ["u", "p"])
    sessionAuth = arg(dict, "user_session")
    xnatPass = arg(dict, "passfile")
    authCheck = argOr([userAuth, sessionAuth, xnatPass])
    hostCheck = argOr([xnatPass, arg(dict, "host")])
    outputDirCheck = argOr([argGroup(dict, ["o"])])

    # Session ID/Label
    # Require at least one session ID/Label at the command line or in a file
    sessionCheck = argOr([arg(dict, "s"),
                          arg(dict, "f"), ])

    # Check for mandatory arguments
    argTry(mandatoryArgsCheck(
        [authCheck, hostCheck, outputDirCheck, sessionCheck]))
    return dict

# {result:bool, log:str} -> Exception | ()


def argTry(check):
    if not check['result']:
        sys.stderr.write(
            "Illegal/Missing arguments: Required args : " +
            check['log'] +
            "\n")
        sys.exit()

# [{result:bool, log:str}] -> ()


def argWarn(argGroups):
    warningArgs = getAll(argGroups, True)
    print consolidateLogs(warningArgs)

# [{result:bool,log:str}] -> {result:bool, log:str}


def mandatoryArgsCheck(argGroups):
    errors = getAll(argGroups, False)
    if len(errors) > 0:
        return {'result': False, 'log': consolidateLogs(errors)}
    else:
        return {'result': True, 'log': ""}

# args{} -> str -> {result: bool, log: str}


def arg(dict, arg):
    return argGroup(dict, arg.split())

# [{result: bool, ...}] -> [{result: bool, ...}]


def getAll(argGroups, bool):
    return filter(lambda group: group['result'] == bool, argGroups)

# [{needed: [str] ...}] -> [{needed: [str] ...}]


def getAllBut(argGroups, arg):
    return filter(lambda group: group['result'] and (
        group['needed'] != arg['needed']), argGroups)

# [{result: bool, log:str}] -> {result:bool, log:str}


def consolidateLogs(argGroups):
    logList = []
    for ind in argGroups:
        logList.append(ind['log'])
    return string.join(logList, ' , ')

# [{result: bool, ...}] -> bool


def allGroups(argGroups, bool):
    return len(getAll(argGroups, bool)) == len(argGroups)

# [{result: bool,...}] -> bool


def someGroups(argGroups):
    return (not allGroups(argGroups, False)) or (
        not allGroups(argGroups, True))

# [{result: bool, missing: str, needed: str}] -> {result: bool, log:str}


def argOr(argGroups):
    first = lambda bool: getAll(argGroups, bool)[0]
    if allGroups(argGroups, False):
        return {'result': False, 'log': ppFlags(argGroups, "needed")}
    else:
        return {'result': first(True) != [], 'log': ""}

# arg{} -> [str] -> {'result' : bool, missing : [str] , 'needed' : [str]}


def argGroup(dict, args):
    nones = filter(lambda arg: arg in args and dict[arg] is None, dict)
    return {'result': nones == [], 'missing': nones, 'needed': args}

# Pretty printing utilites
# str -> str


def addSwitch(arg):
    if arg == "":
        return arg
    else:
        return "-" + arg

# [str] -> [str]


def withSwitches(flags):
    return map(addSwitch, flags)

# [str] -> str


def pp(flags):
    return "[" + ','.join(withSwitches(flags)) + "]"

# [{result: bool, missing: str, needed: str}] -> str -> str


def ppFlags(groups, flag):
    return "( " + " | ".join(map(lambda group: pp(group[flag]), groups)) + " )"

# Tests
testResults = [{'result': False, 'log': "Error One"},
               {'result': False, 'log': "Error Two"},
               {'result': True, 'log': "Warning One"},
               {'result': True, 'log': "Warning Two"},
               {'result': True, 'log': ""}]


def addSwitchTest():
    print "Testing addSwitch"
    assert (addSwitch("p") == "-p")
    assert (addSwitch("") == "")


def withSwitchesTest():
    print "Testing withSwitches"
    assert (withSwitches(["u", "p"]) == ["-u", "-p"])
    assert (withSwitches([]) == [])


def ppTest():
    print "Testing pp"
    assert (pp(["u", "p"]) == "[-u,-p]")


def ppFlagsTest():
    print "Testing ppFlags"
    groups = [{"result": True, "missing": [], "needed": ["a"]},
              {"result": True, "missing": [], "needed": ["u", "p"]}]
    assert (ppFlags(groups, "needed") == "( [-a] | [-u,-p] )")


def someGroupsTest():
    print "Testing someGroups"
    assert(someGroups([{'result': False}, {'result': True}]) == True)
    assert(someGroups([{'result': False}, {'result': False}]) == True)


def allGroupsTest():
    print "Testing allGroups"
    assert(allGroups([{'result': True}, {'result': True}], True) == True)
    assert(allGroups([{'result': True}, {'result': False}], True) == False)


def argGroupTest():
    print("Testing argGroup")
    assert(argGroup({'p': "testPassword", 'u': "testUser"}, ['u', 'p']) == {
           'result': True, 'missing': [], 'needed': ["u", "p"]})
    assert(argGroup({'p': None, 'u': "testUser"}, ['u', 'p']) == {
           'result': False, 'missing': ["p"], 'needed': ["u", "p"]})
    assert(argGroup({'p': None, 'u': None}, ['u', 'p']) == {
           'result': False, 'needed': ['u', 'p'], 'missing': ['p', 'u']})


def getAllTest():
    print("Testing getAll")
    assert(getAll(testResults, True) == [{'result': True, 'log': "Warning One"},
                                         {'result': True,
                                          'log': "Warning Two"},
                                         {'result': True, 'log': ""}])
    assert(getAll(testResults, False) == [{'result': False, 'log': "Error One"},
                                          {'result': False, 'log': "Error Two"}])


def getAllButTest():
    print("Testing getAllBut")
    assert(getAllBut([{'result': True, 'needed': "a"},
                      {'result': True, 'needed': "b"},
                      {'result': True, 'needed': "c"}], {'needed': "a"})
           ==
           [{'result': True, 'needed': "b"},
            {'result': True, 'needed': "c"}])
    assert(getAllBut([{'result': True, 'needed': "a"},
                      {'result': True, 'needed': "b"},
                      {'result': True, 'needed': "c"}], {'needed': "d"})
           ==
           [{'result': True, 'needed': "a"},
            {'result': True, 'needed': "b"},
            {'result': True, 'needed': "c"}])
    assert((getAllBut([{'result': True, 'needed': "a"},
                       {'result': False, 'needed': "b"},
                       {'result': True, 'needed': "c"}], {'needed': "a"})
            ==
            [{'result': True, 'needed': "c"}]))


def argOrTest():
    print("Testing argOr")
    useUP = argOr([argGroup({'p': "testPassword", 'u': "tesUser"}, ['p', 'u']),
                   arg({'alt': "alternateFlag"}, 'alt')])
    useA = argOr([arg({'alt': "alternateFlag"}, 'alt'),
                  argGroup({'p': "testPassword", 'u': "tesUser"}, ['p', 'u'])])
    useSecond = argOr([argGroup({'c': "c", 'd': None}, ['c', 'd']),
                       arg({'alt': "alternateFlag"}, 'alt')])
    assert(useUP == {'result': True, 'log': ''})
    assert(useA == {'result': True, 'log': ''})
    assert(useSecond == {'result': True, 'log': ''})


def consolidateLogTest():
    print("Testing consolidateLog")
    assert(consolidateLogs([]) == "")
    assert(consolidateLogs([testResults[0]]) == "Error One")
    assert(consolidateLogs(testResults) ==
           "Error One , Error Two , Warning One , Warning Two , ")


def argTryTest():
    print "testing argTry"
    try:
        argTry(testResults[0])
        print "FAIL! Should have thrown an Exception"
    except Exception as e:
        ()


def mandatoryArgsCheckTest():
    print "Testing mandatoryArgsCheck"
    assert (len((mandatoryArgsCheck(testResults))) == 2)


def test():
    consolidateLogTest()
    mandatoryArgsCheckTest()
    addSwitchTest()
    withSwitchesTest()
    ppTest()
    ppFlagsTest()
    argTryTest()
    argGroupTest()
    getAllTest()
    getAllButTest()
    allGroupsTest()
    someGroupsTest()
    argOrTest()


def getArgs():
    return validateArgs(parser.parse_args())
