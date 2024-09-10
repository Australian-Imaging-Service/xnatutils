import tempfile
import os.path
import logging
from xnatutils import put

logger = logging.getLogger("xnat-utils")
# logger.setLevel(logging.WARNING)
# handler = logging.FileHandler('test_put.log')
# handler.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)


def get_session_label(modality, visit_id):
    return session_label_template.format(modality=modality, visit=visit_id)


def get_session(modality, visit_id):
    return subject.experiments[get_session_label(modality, visit_id)]


@pytest.mark.skip(reason="Test not implemented")
def test_put(xnat_connection):

    session_label_template = project_id + "_" + subject_id + "_{modality}{visit}"
    test_files = {
        # 'MR': {
        #     'scan1': (['1.dcm', '2.dcm', '3.dcm'], 'DICOM')},
        # 'EEG': {
        #     'recording1': (['foo.els'], 'EEG')},
        "XC": {"scan1": (["foo.dat", "bar.txt", "goo.csv"], "EXT_CAM")}
    }
    modality_to_session_cls = {
        "MR": "MrSessionData",
        "XC": "XcSessionData",
        "EEG": "EegSessionData",
    }

    subject_id = "test_subject"
    project_id = "test_project"

    for modality, scans in test_files.items():
        for scan_type, (fnames, resource_name) in scans.items():
            temp_dir = tempfile.mkdtemp()
            # Create test files to upload
            fpaths = []
            for fname in fnames:
                fpath = os.path.join(temp_dir, fname)
                with open(fpath, "w") as f:
                    f.write("test")
                fpaths.append(fpath)
            # Put using filenames as arguments
            put(
                get_session_label(modality, 1),
                scan_type,
                *fpaths,
                create_session=True,
                subject_id=subject_id,
                project_id=project_id,
                modality=modality,
                resource_name=resource_name,
            )
            # Put using directory as argument
            put(
                get_session_label(modality, 2),
                scan_type,
                temp_dir,
                create_session=True,
                subject_id=subject_id,
                project_id=project_id,
                modality=modality,
                resource_name=resource_name,
            )
            for visit_id in (1, 2):
                session = get_session(modality, visit_id)
                assert sorted(
                    os.path.basename(f)
                    for f in session.scans[scan_type]
                    .resources[resource_name]
                    .files.keys()
                ) == sorted(fnames)
        scan_names = session.scans.keys()
        assert sorted(scan_names) == sorted(scans.keys())
