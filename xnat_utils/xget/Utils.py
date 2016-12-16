import copy
import sys
import warnings
from functools import partial
from pyxnat import *
import time
from datetime import datetime
import zipfile
import os
from functools import reduce


def p(res):
    print res
    return res

# the identity function
identity = lambda x: x
# (f1,f2,f3,...) -> lambda x: ... f3((f2(f1(id(x)))))
compose = lambda *fs: reduce(lambda i, f:
                             lambda x: f(i(x)), fs, identity)
# ["a","b","c",...] -> "abc..."
concat = lambda xs: reduce(lambda x, y: x + y, xs)
# ["a","b","c" ...] -> ["a","ab","abc" ...]
inits = lambda xs: [concat(es) for es in
                    [xs[0:i + 1]
                     for i in range(0, len(xs))]]

# [[1,2,3],[4,5,6],...] -> [1,2,3,4,5,6,...]
flatten = lambda xxs: sum(xxs, [])


def get_ids(res, xpath):
    ret = []
    for e in res.xpath(xpath):
        ret.append(e.attrib['ID'])
    return ret

# filter_xml_by(res,"//scans","@type",


def filter_xml_by(*narrowing_xpaths):
    fq_paths = inits(narrowing_xpaths)

    def elem_list(xp, res):
        return res.xpath(xp)

    elem_iter = lambda xp, e: [e.iter(xp)]
    head, tail = narrowing_xpaths[0], narrowing_xpaths[1:]

    def choose_f(xp, e):
        if isinstance(e, list):
            return partial(map, lambda _e: elem_iter(xp, _e))
    fs = [partial(elem_list, head)] + [partial(choose_f, xp) for xp in tail]
    return compose(*fs)


def unzip(fzip,
          dest_dir,
          check=None):
    """
    Extracts the given zip file to the given directory, but only if all members of the
    archive pass the given check.

        Parameters
        ----------
        src: fzip
            zipfile
        dest_dir: string
            directory into which to extract the archive
        check: dict
            An dictionary that has the keys:
                 'run' : A function that takes a filename and parent directory and returns Bool. By default
                         this function always returns True.
                 'dest' : A string description of this test. By default this is empty.

        Returns a tuple of type (bool,[string]) where if the extraction ran successfully the first is true and the
        second is a list of files that were extracted, and if not the first is false and the second is the name
        of the failing member.
    """
    if not check:
        check = {'run': lambda z, d: True,
                 'desc': ""}
    for member in fzip.namelist():
        if not check['run'](member, dest_dir):
            return (False, member)

    fzip.extractall(path=dest_dir)
    return (True, map(lambda f: os.path.join(dest_dir, f), fzip.namelist()))


def extractZip(zip_location, overwrite, dest_dir):
    fzip = zipfile.ZipFile(zip_location, 'r')
    check = {'run': lambda f, d: not os.path.exists(os.path.join(d, f)),
             'desc': 'File exists.'}

    def safeUnzip():
        if not overwrite:
            return unzip(fzip, dest_dir, check)
        else:
            return unzip(fzip, dest_dir)
    (unzipped, paths) = safeUnzip()
    if not unzipped:
        fzip.close()
        raise EnvironmentError(
            "Unable to extract " +
            zip_location +
            " because file " +
            paths +
            " : " +
            check['desc'])
    else:
        return paths

#[a] -> [a]
# str -> str


def tail(xs):
    l = list(xs)
    if len(l) == 1:
        return []
    else:
        tmp = []
        for i in range(len(l)):
            if i != 0:
                tmp.append(l[i])
        if isinstance(xs, str):
            return "".join(tmp)
        else:
            return tmp

# str -> [str]


def split(tok, str):
    return map(lambda x: x.strip(' \t\n\r'), str.split(tok))

# dict -> dict


def merge(d1, d2):
    ret = copy.deepcopy(d2)
    keys = set(d1.keys()).union(d2.keys())
    common = set(d1.keys()).intersection(d2.keys())
    for k in keys:
        if k in common:
            if d1[k] == None:
                ret[k] = d2[k]
            else:
                ret[k] = d1[k]
        else:
            if k in d1:
                ret[k] = d1[k]
    return ret

# dict -> [str] -> dict | None | Exception


def extract(d, ks):
    ret = {}
    if d is not None:
        common = set(d.keys()).intersection(ks)
        if len(common) != len(ks):
            raise Exception(
                "All keys : " +
                ks +
                " not found in dictionary " +
                d)
        else:
            for k in ks:
                ret[k] = d[k]
        return ret
    else:
        return None

# csv -> string


def remove_csv_whitespace_dupes(csv, sep=","):
    entries = []
    for t in csv.split(','):
        cleaned = t.strip()
        if cleaned != "" and cleaned not in entries:
            entries.append(cleaned)
    return sep.join(entries)

# str -> str


def addHTTPPrefix(str):
    prefix = "http"
    if not str.startswith(prefix) and str != "":
        return "http://" + str
    else:
        return str

# str -> str


def removeTrailingSlash(str):
    if str is not None and str != "":
        l = list(str)
        if l.pop() == "/":
            return "".join(l)
    return str

# datetime -> datetime -> Bool


def onOrBefore(t1, t2):
    get_time = lambda t: datetime.fromtimestamp(time.mktime(t))
    return (get_time(t1) <= get_time(t2))

# datetime -> datetime -> Bool


def validDateRange(start, end):
    get_time = lambda t, d: t and datetime.fromtimestamp(time.mktime(t)) or d
    (s, e) = (get_time(start, datetime.fromtimestamp(0)),
              get_time(end, datetime.today()))
    return s <= e

# datetime -> datetime -> datetime -> bool


def inRange(start, end, date):
    if date:
        get_time = lambda t, d: t and datetime.fromtimestamp(
            time.mktime(t)) or d
        (s, e) = (get_time(start, datetime.fromtimestamp(0)),
                  get_time(end, datetime.today()))
        return s <= get_time(date, None) <= e
    else:
        return True

# [a] -> (a -> (a, String)) -> {a : Bool | a | Exception}


def tag_synonyms(xs, conv):
    xs_set = list(set(xs))
    ret_dict = {}
    for x in xs_set:
        converted = conv(x)
        if converted is not None:
            if (converted != x and (converted in ret_dict)) \
                    or isinstance(converted, Exception):
                ret_dict[x] = converted
            elif (converted not in ret_dict):
                ret_dict[x] = True
        else:
            ret_dict[x] = False
    return ret_dict


def assert_or_print(statement, expected):
    if statement != expected:
        print str(statement)
    else:
        return True


def fatal_error(msg):
    fatal_errors([msg])


def fatal_errors(msgs):
    sys.stderr.write("\n".join([("FATAL ERROR : " + str(m)) for m in msgs]))
    sys.stderr.write("\n")
    sys.exit()


def print_warning(msg):
    print_warnings([msg])


def print_warnings(msgs):
    if msgs:
        print "\n".join([("WARNING : " + str(m)) for m in msgs])


def print_info(msg):
    print_infos([msg])


def print_infos(msgs):
    print "\n".join(["INFO : " + str(m) for m in msgs])

# Tests


def testRemove_csv_whitespace_dupes():
    print "Testing remove_csv_whitespace_dupes"
    assert (remove_csv_whitespace_dupes("1,2,3") == "1,2,3")
    assert (remove_csv_whitespace_dupes("1,1,2,3") == "1,2,3")
    assert (remove_csv_whitespace_dupes("1,1,2,2,3") == "1,2,3")
    assert (remove_csv_whitespace_dupes("1,1,1,1") == "1")
    assert (remove_csv_whitespace_dupes("") == "")
    assert (remove_csv_whitespace_dupes("1,,,3") == "1,3")


def removeTrailingSlashTest():
    print "Testing removeTrailingSlash"
    assert (removeTrailingSlash("localhost:8080") == "localhost:8080")
    assert (removeTrailingSlash("/") == "")
    assert (removeTrailingSlash("localhost:8080/") == "localhost:8080")
    assert (removeTrailingSlash("") == "")
    assert (removeTrailingSlash("//") == "/")


def addHTTPPrefixTest():
    print "Testing addHTTPPrefix"
    assert(addHTTPPrefix("http://localhost:8080") == "http://localhost:8080")
    assert(addHTTPPrefix("") == "")
    assert(addHTTPPrefix("localhost:8080") == "http://localhost:8080")


def tailTest():
    assert(tail([1, 2, 3]) == [2, 3])
    assert(tail([]) == [])
    assert(tail("hello world") == "ello world")
    assert(tail("") == "")


def splitTest():
    print "Testing split"
    assert(split(',', ' hello, world') == ['hello', 'world'])
    assert(split(',', ' ,world') == ['', 'world'])
    assert(split(',', ' ,') == ['', ''])


def dieIfException(v):
    if isinstance(v, Exception):
        fatal_error(v)


def extractTest():
    print "Testing extract"
    d1 = {'k1': 'a', 'k2': 'b', 'k3': 'c'}
    assert(extract(d1, ['k1', 'k2']) == {'k2': 'b', 'k1': 'a'})
    try:
        extract(d1, [])
        print('Should have thrown Exception')
        return
    except Exception:
        ()
    try:
        extract(d1, ['k1', 'k10'])
        print ('Should have thrown Exception')
        return
    except Exception:
        ()


def mergeTest():
    print "Testing merge"
    d1 = {'k1': 'a', 'k2': 'b', 'k3': 'c'}
    d2 = {'k1': None, 'k2': 'b', 'k3': 'c'}
    assert(merge(d1, d2) == {'k3': 'c', 'k2': 'b', 'k1': 'a'})
    d3 = {'k1': 'a', 'k2': 'b', 'k3': 'c', 'k4': 'd'}
    assert(merge(d3, d2) == {'k4': 'd', 'k3': 'c', 'k2': 'b', 'k1': 'a'})
    d4 = {}
    assert(merge(d1, d4) == {'k3': 'c', 'k2': 'b', 'k1': 'a'})
    d5 = {'k4': 'd'}
    assert(merge(d1, d5) == {'k4': 'd', 'k3': 'c', 'k2': 'b', 'k1': 'a'})


def test_tag_synonyms():
    print "Testing tag_synonyms"
    test_dict = {'a': 1, 'b': 2, 'c': 3, 'd': None, 1: 'a', 2: 'b', 3: 'c'}

    def conv(a):
        try:
            return test_dict[a]
        except Exception as e:
            return e
    ret_dict = {'a': True,
                1: 'a',
                'b': True,
                'e': KeyError('e'),
                'd': False,
                3: True}
    assert(
        str(tag_synonyms(['a', 1, 'b', 3, 'd', 'e'], conv)) == str(ret_dict))


def test_compose():
    print "Testing compose"
    add = lambda x: x + 1
    assert(compose()(1) == 1)
    assert(compose(add)(1) == 2)
    assert(compose(add, add, add)(1) == 4)


def test_validDateRange():
    print "Testing validDateRange"
    jan1 = time.strptime("01012010", "%d%m%Y")
    jan2 = time.strptime("02012010", "%d%m%Y")
    assert_or_print(validDateRange(jan1, jan2), True)
    assert_or_print(validDateRange(jan1, jan1), True)
    assert_or_print(validDateRange(None, None), True)
    assert_or_print(validDateRange(jan2, jan1), False)


def test_onOrBefore():
    print "Testing onOrBefore"
    jan1 = time.strptime("01012010", "%d%m%Y")
    jan2 = time.strptime("02012010", "%d%m%Y")
    assert_or_print(onOrBefore(jan1, jan2), True)
    assert_or_print(onOrBefore(jan1, jan1), True)
    assert_or_print(onOrBefore(jan2, jan1), False)


def test_inRange():
    print "Testing inRange"
    jan1 = time.strptime("01012010", "%d%m%Y")
    jan2 = time.strptime("02012010", "%d%m%Y")
    dec31 = time.strptime("31122009", "%d%m%Y")
    assert_or_print(inRange(jan1, jan2, jan2), True)
    assert_or_print(inRange(jan1, jan2, jan1), True)
    assert_or_print(inRange(jan1, jan1, dec31), False)
    assert_or_print(inRange(None, jan1, dec31), True)
    assert_or_print(inRange(jan1, None, jan2), True)
    assert_or_print(inRange(None, None, jan2), True)


def test():
    tailTest()
    splitTest()
    mergeTest()
    extractTest()
    addHTTPPrefixTest()
    removeTrailingSlashTest()
    test_tag_synonyms()
    testRemove_csv_whitespace_dupes()
    test_compose()
    test_inRange()
    test_validDateRange()
    test_onOrBefore()
