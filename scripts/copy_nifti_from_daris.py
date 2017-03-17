import os.path
import re
from argparse import ArgumentParser
from nianalysis.archive.daris import DarisLogin
from xnatutils import connect, data_format_exts

parser = ArgumentParser()
parser.add_argument('download', type=str,
                    help="The name of the downloaded dataset")
parser.add_argument('upload', type=str,
                    help="The name for the uploaded dataset")
parser.add_argument('--daris_project', default=88, type=int,
                    help="Daris project to download the datasets from")
parser.add_argument('--processed', default=False, action='store_true',
                    help="Whether the dataset is processed or acquired")
parser.add_argument('--subjects', nargs='+', type=int, default=None,
                    help="Subjects to copy the datasets from")
parser.add_argument('--sessions', nargs='+', type=int, default=None,
                    help="The sessions to copy the datasets from")
parser.add_argument('--xnat_project', default='MRH017', type=str,
                    help="The XNAT project to upload them to")
parser.add_argument('--work_dir', type=str,
                    help="Work directory to download files from")
parser.add_argument('--modality', default='MR',
                    help="Modality of dataset session for XNAT upload")
parser.add_argument('--data_format', default='nifti_gz',
                    help="The assumed data-format of the dataset")
args = parser.parse_args()

ex_method_id = args.processed + 1

ext = data_format_exts[args.data_format]

copied = []

with DarisLogin as mbi_daris, connect() as mbi_xnat:

    if args.subjects is None:
        subject_ids = [s.id for s in mbi_daris.get_subjects(
            args.daris_project)]
    else:
        subject_ids = args.subjects

    for subject_id in subject_ids:
        session_ids = set(s.id for s in mbi_daris.get_sessions(
            args.daris_project, subject_id))
        if args.sessions:
            session_ids &= set(args.sessions)
        for session_id in session_ids:
            datasets = mbi_xnat.get_datasets(args.daris_project, subject_id,
                                             session_id=session_id,
                                             ex_method_id=ex_method_id)
            matching = [d for d in datasets if re.match(args.download, d.name)]
            cid = "1008.2.{}.{}.{}".format(
                args.daris_project, subject_id, ex_method_id, session_id)
            if len(matching) > 1:
                print ("Could not distinguish between '{}' in session {}"
                       .format("', '".join(m.name for m in matching), cid))
            elif matching:
                match = matching[0]
                path = os.path.join(args.work_dir, str(match.cid))
                mbi_daris.download(path, args.daris_project, subject_id,
                                   session_id=session_id, match.id)
                xnat_session_id = '{}_{}_{}{}'.format(
                    args.xnat_project, subject_id, args.modality,
                    session_id)
                xnat_session = mbi_xnat.experiments[xnat_session_id]
                dataset = mbi_xnat.classes.MrScanData(
                    type=args.upload, parent=xnat_session)
                resource = dataset.create_resource(args.data_format)
                resource.upload(path, args.upload + ext)
                copied.append(cid)
                print "Uploaded {} to {}/{}".format(cid, xnat_session_id,
                                                    args.upload + ext)
            else:
                print ("Did not find matching dataset '{}' in {}".format(
                    args.download, cid))
print "Successfully copied {} datasets".format(len(copied))
