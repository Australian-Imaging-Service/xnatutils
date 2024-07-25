from xnatutils import put

put(
    "ses-01",
    "T1w_3",
    "/Users/arkievdsouza/Desktop/FastSurferTesting/data/sub-100307_ses-01_task-T1w.nii.gz",
    create_session=True,
    project_id="OPENNEURO_T1W",
    subject_id="100307",
    overwrite=True,
    upload_method="per_file",
)
