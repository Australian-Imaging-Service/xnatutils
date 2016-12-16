import Config
import Args
import sys
import time
import Utils
from TranslateLabelID import *
from pyxnat import *
import os
import string
import functools
import httplib2
import Exceptions

DEBUG = False


def createConnection(host, user, password, output_dir):
    i = Interface(
        server=Utils.removeTrailingSlash(Utils.addHTTPPrefix(host)),
        user=user,
        password=password,
        cachedir=os.path.join(output_dir, '.store')
    )
    i._memtimeout = 0
    return i


def createModel():
    dict = Args.getArgs()
    if DEBUG:
        print dict
    return Config.Model(dict, "")


def main():
    opts = createModel()
    if DEBUG:
        print Utils.addHTTPPrefix(opts.getHost())
        print opts.getUser()
        print opts.getPass()
        print os.path.join(opts.getOutputDir(), '.store')

    not os.path.exists(opts.getOutputDir()) and \
        Utils.fatal_error(
        "Output directory %s does not exist" %
        (opts.getOutputDir()))
    not os.access(opts.getOutputDir(), os.W_OK) and \
        Utils.fatal_error(
        "Output directory %s is not writeable" %
        (opts.getOutputDir()))

    Utils.print_info("Connecting to XNAT Server %s" % (opts.getHost()))
    connection = createConnection(
        opts.getHost(),
        opts.getUser(),
        opts.getPass(),
        opts.getOutputDir())
    if DEBUG:
        print connection._jsession

    err = bad_auth(connection)
    if isinstance(err, httplib2.ServerNotFoundError):
        Utils.fatal_error(str(err))
    else:
        Utils.fatal_error("Username or password is wrong.")

    # filters = {'scan' : [T1,T2...], ...}
    filters = dict([(t, f.split(',')) for (f, t) in
                    [(opts.getScanTypes(), 'scan'),
                     (opts.getAssTypes(), 'assessor'),
                     (opts.getReconTypes(), 'reconstruction')]])

    # errors = ['Error in scan constraints ...',  ...]
    _errors = [e for e in [sanity_check_filter(filters[f], f) for f in filters]
               if e is not None]
    _errors and Utils.fatal_errors(_errors)

    start = sanity_check_date(opts.getStart())
    Utils.dieIfException(start)
    end = sanity_check_date(opts.getEnd())
    Utils.dieIfException(end)

    Utils.validDateRange(
        start, end) or Utils.fatal_error(
        "%s - %s is not a valid date range" %
        (start, end))

    proj_resource = Project('project', connection)
    exp_resource = Experiment('experiment', connection)

    proj = opts.getProject()
    if proj:
        Utils.print_info(
            "Checking that project %s exists." %
            (opts.getProject()))
        if not exists(proj_resource, proj):
            Utils.fatal_error("Project %s does not exist." % (proj))
        Utils.print_info(
            "Checking that the project %s is unique in the XNAT server" %
            (proj))
        _errors = sanity_check_project(proj_resource, proj)
        _errors and Utils.fatal_error(_errors)
        _proj = to_id(proj_resource, proj)
        if _proj and _proj != proj:
            Utils.print_info(
                "Project label %s has been translated to project id %s" %
                (proj, _proj))
            proj = _proj

    if proj:
        Utils.print_info(
            "Checking that the experiments %s exist within project %s" %
            (",".join(
                opts.getSessions()),
                proj))
    else:
        Utils.print_info(
            "Checking that the specified experiments %s exist." %
            (opts.getSessions()))

    session_dict = create_session_dict(exp_resource,
                                       opts.getSessions(),
                                       proj)
    report_session_warnings(session_dict)
    unique_sessions = [s for s in session_dict if session_dict[s] == True]
    quality = opts.getQuality()
    format = opts.getFormat()

    #(<label-or-id-from-user>, <session-id>)
    sessions = filter(lambda s_sid: Utils.inRange(start, end, exp_resource.date(s_sid[1])),
                      map(lambda s: proj and (s, to_id(exp_resource, s, choose_by_project(proj)))
                          or (s, to_id(exp_resource, s)),
                          [s for s in session_dict if session_dict[s] == True]))
    candidates = {}
    for (s, sess_id) in sessions:
        candidates[s] = {}
        scan_resource = Scan(exp_resource.get(sess_id))
        assessor_resource = Assessor(exp_resource.get(sess_id))
        reconstruction_resource = Reconstruction(exp_resource.get(sess_id))
        candidates[s]['id'] = sess_id
        if proj:
            candidates[s]['project'] = proj
        else:
            candidates[s]['project'] = exp_resource.get_project_id(sess_id)

        candidates[s]['subject'] = exp_resource.get_subject_id(sess_id)
        candidates[s]['scan'] = {}
        candidates[s]['scan']['list'] = scans_matching_types(quality,
                                                             format,
                                                             filters['scan'],
                                                             scan_resource)
        candidates[s]['scan']['filename'] = sanity_check_filename(create_filename(filters,
                                                                                  opts.getLongName(),
                                                                                  proj,
                                                                                  quality,
                                                                                  format,
                                                                                  'scan',
                                                                                  s),
                                                                  opts.getOutputDir(),
                                                                  opts.overwrite())
        candidates[s]['scan']['resource'] = lambda r: r.scans()

        candidates[s]['assessor'] = {}
        candidates[s]['assessor']['list'] = assessors_matching_types(filters['assessor'],
                                                                     assessor_resource)
        candidates[s]['assessor']['filename'] = sanity_check_filename(create_filename(filters,
                                                                                      opts.getLongName(),
                                                                                      proj,
                                                                                      quality,
                                                                                      format,
                                                                                      'assessor',
                                                                                      s),
                                                                      opts.getOutputDir(),
                                                                      opts.overwrite())
        candidates[s]['assessor']['resource'] = lambda r: r.assessors()

        candidates[s]['recon'] = {}
        candidates[s]['recon']['list'] = reconstructions_matching_types(filters['reconstruction'],
                                                                        reconstruction_resource)
        candidates[s]['recon']['filename'] = sanity_check_filename(create_filename(filters,
                                                                                   opts.getLongName(),
                                                                                   proj,
                                                                                   quality,
                                                                                   format,
                                                                                   'reconstruction',
                                                                                   s),
                                                                   opts.getOutputDir(),
                                                                   opts.overwrite())
        candidates[s]['recon']['resource'] = lambda r: r.reconstructions()

    for s in candidates:
        if not candidates[s]['scan']['list']:
            Utils.print_warning(
                "No acquisitions found in experiment %s matching the constraints." %
                (s))
        if isinstance(candidates[s]['scan']['filename'], Exception):
            Utils.print_warning(str(candidates[s]['scan']['filename']))
        if not candidates[s]['assessor']['list']:
            Utils.print_warning(
                "No assessors found in experiment %s matching the constraints." %
                (s))
        if isinstance(candidates[s]['assessor']['filename'], Exception):
            Utils.print_warning(str(candidates[s]['assessor']['filename']))
        if not candidates[s]['recon']['list']:
            Utils.print_warning(
                "No reconstructions found in experiment %s matching the constraints." %
                (s))
        if isinstance(candidates[s]['recon']['filename'], Exception):
            Utils.print_warning(str(candidates[s]['recon']['filename']))
    if can_download(candidates):
        Utils.print_info(pp_download_candidates(candidates))
        download_images(candidates, opts, connection)
    else:
        Utils.fatal_error("There is nothing to download.")


def can_download(candidates):
    return candidates and any([candidates[s][t]['list'] and not isinstance(candidates[s][t]['filename'], Exception)
                               for t in ['scan', 'assessor', 'recon']
                               for s in candidates])


def sanity_check_date(date):
    def extract_time(t):
        if t:
            time_format = "%d%m%Y"
            try:
                return time.strptime(t, time_format)
            except ValueError as e:
                return e
        else:
            return None
    return extract_time(date)


def sanity_check_filename(filename, outputdir, overwrite):
    location = os.path.join(outputdir, filename + ".zip")
    if os.path.exists(location) and not overwrite:
        return Exception(
            "Cannot download to %s because it already exists. Specify another output directory or set the -overwrite flag." % (location))
    else:
        return filename


def pp_download_candidates(candidates):
    s = "Download Candidates:\n"
    pp_list = lambda c, t: not isinstance(
        candidates[c][t]['filename'], Exception) and str(
        candidates[c][t]['list']) or str(
            [])
    for c in candidates:
        s += "         " + c + ":\n"
        s += "           acquisitions:" + pp_list(c, 'scan') + "\n"
        s += "           assessors:" + pp_list(c, 'assessor') + "\n"
        s += "           reconstructions:" + pp_list(c, 'recon') + "\n"
    return s


def create_filename(filters, longname, proj, quality, format, downloadtype, s):
    xs = []
    if longname:
        if proj:
            xs.append("p_%s" % (proj))
        xs.append("sess_%s" % (s))
    if downloadtype == 'scan':
        if longname:
            xs.append(
                "acq_%s_q_%s_f_%s" %
                ("_".join(
                    filters['scan']),
                    quality,
                    format))
        else:
            xs.append(s + "_acq")
    elif downloadtype == 'assessor':
        if longname:
            xs.append("ass_%s" % ("_".join(filters['assessor'])))
        else:
            xs.append(s + "_ass")
    elif downloadtype == 'reconstruction':
        if longname:
            xs.append("recon_%s" % ("_".join(filters['reconstruction'])))
        else:
            xs.append(s + "_recon")
    return "_".join(xs)


def select_id(scan_resource, constraint):
    if scan_resource.is_id_and_type(constraint):
        return [Exception("User constraint: %s is both a scan ID and type."
                          % str(constraint))]
    if scan_resource.is_id(constraint):
        return [constraint]
    else:
        return scan_resource.get_type(constraint)

# [check_filter(f,s) for f in filters for s in sessions]


def scans_matching_types(quality, format, types, scan_resource):
    both = set.intersection
    quality_matches = set(scan_resource.get_quality(quality))
    format_matches = set(scan_resource.with_format(format))
    ls = []
    for s in list(both(quality_matches, format_matches)):
        for t in types:
            if scan_resource.is_id(t):
                ls.append(t)
            elif scan_resource.has_type(s, t):
                ls.append(s)
    return list(set(ls))


def assessors_matching_types(types, assessor_resource):
    ls = []
    for t in types:
        if assessor_resource.is_id(t):
            ls.append([t])
        else:
            ls.append([a for a in assessor_resource.get_type(t)
                       if assessor_resource.has_files(a)])
    return list(set(sum(ls, [])))


def reconstructions_matching_types(types, reconstruction_resource):
    ls = []
    for t in types:
        if reconstruction_resource.is_id(t):
            ls.append([t])
        else:
            ls.append([a for a in reconstruction_resource.get_type(t)
                       if reconstruction_resource.has_files(a)])
    return list(set(sum(ls, [])))


def report_session_warnings(sd):
    exceptions = [sd[s] for s in sd if isinstance(sd[s], Exception)]
    dupes = ["%s is a duplicate of %s" % (d, o)
             for (o, d) in [(s, sd[s]) for s in sd if sd[s] != True and
                            not isinstance(sd[s], Exception) and
                            not isinstance(sd[s], bool)]]
    Utils.print_warnings(dupes + exceptions)


def sanity_check_project(proj_resource, proj):
    if proj:
        try:
            exists(proj_resource, proj) and label_id_flip(proj_resource, proj)
        except AmbiguousLabelError as e:
            return e


def sanity_check_filter(constraints, constraint_type):
    if len(constraints) > 1 and 'ALL' in constraints:
        return ('Error in %s constraint: \"ALL\" cannot be used with any other constraint' % (
            constraint_type))


def bad_auth(conn):
    try:
        conn._get_entry_point()
        if conn._jsession == "authentication_by_credentials":
            raise errors.OperationalError("Authentication Failed")
    except httplib2.ServerNotFoundError as e:
        return e
    except Exception as e:
        return e


def create_session_dict(exp, sessions, proj=None):
    def conv(s):
        def in_proj():
            return exists(exp, s, choose_by_project(proj))

        def in_xnat():
            try:
                return exists(exp, s)
            except AmbiguousLabelError as e:
                return e
        if proj:
            if not in_proj():
                return LookupError(
                    "Experiment %s either doesn't exist in project %s or in the XNAT server" % (s, proj))
            else:
                return True
        elif not in_xnat():
            return LookupError("Experiment %s does not exist" % (s))
        else:
            try:
                # return the synonym of this session
                return label_id_flip(exp, s)
            except AmbiguousLabelError as e:
                return e
    return Utils.tag_synonyms(sessions, conv)


def download_images(candidates, opts, conn):
    for s in candidates:
        proj = candidates[s]['project']
        subj = candidates[s]['subject']
        sess_id = candidates[s]['id']
        exp_obj = conn.select.project(proj).subject(subj).experiment(sess_id)
        for t in ['scan', 'assessor', 'recon']:
            if candidates[s][t]['list'] and not isinstance(
                    candidates[s][t]['filename'], Exception):
                res_ids = candidates[s][t]['list']
                Utils.print_info("Downloading experiment %s's %s to %s.zip"
                                 % (s,
                                    t is "scan" and "acquisitions" or t + "s",
                                    os.path.join(opts.getOutputDir(),
                                                 candidates[s][t]['filename'])))

                objs = candidates[s][t]['resource'](exp_obj)
                try:
                    (status, zip_location) = objs.download(opts.getOutputDir(),
                                                           res_ids,
                                                           opts.getFormat(),
                                                           candidates[s][t][
                                                               'filename'],
                                                           False,
                                                           opts.overwrite())
                    if opts.extractZip():
                        Utils.print_info("Extracting ...")
                        try:
                            paths = Utils.extractZip(
                                zip_location,
                                opts.overwrite(),
                                opts.getOutputDir())
                            Utils.print_info("Extracted to : " + str(paths))
                            Utils.print_info(
                                "Removing zip file : " +
                                str(zip_location))
                            os.remove(zip_location)
                        except EnvironmentError as e:
                            Utils.print_warning(e)
                    else:
                        Utils.print_info("Download successful.")
                except EnvironmentError as e:
                    Utils.fatal_error(e)
