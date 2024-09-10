import os
import logging
from tempfile import mkdtemp
import xnat
import tempfile
from datetime import datetime
from pathlib import Path
import pytest

# import numpy
# import nibabel
import xnat4tests

# import medimages4tests.dummy.nifti

try:
    from pydra import set_input_validator
except ImportError:
    pass
else:
    set_input_validator(True)

# For debugging in IDE's don't catch raised exceptions and let the IDE
# break at it
if os.getenv("_PYTEST_RAISE", "0") != "0":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value

    CATCH_CLI_EXCEPTIONS = False
else:
    CATCH_CLI_EXCEPTIONS = True


@pytest.fixture
def catch_cli_exceptions():
    return CATCH_CLI_EXCEPTIONS


PKG_DIR = Path(__file__).parent


log_level = logging.WARNING

logger = logging.getLogger("frametree")
logger.setLevel(log_level)

sch = logging.StreamHandler()
sch.setLevel(log_level)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
sch.setFormatter(formatter)
logger.addHandler(sch)

logger = logging.getLogger("frametree")
logger.setLevel(log_level)

sch = logging.StreamHandler()
sch.setLevel(log_level)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
sch.setFormatter(formatter)
logger.addHandler(sch)


@pytest.fixture(scope="session")
def run_prefix():
    "A datetime string used to avoid stale data left over from previous tests"
    return datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")


# @pytest.fixture
# def cli_runner(catch_cli_exceptions):
#     def invoke(*args, catch_exceptions=catch_cli_exceptions, **kwargs):
#         runner = CliRunner()
#         result = runner.invoke(*args, catch_exceptions=catch_exceptions, **kwargs)
#         return result

#     return invoke


@pytest.fixture
def work_dir() -> Path:
    work_dir = tempfile.mkdtemp()
    return Path(work_dir)


@pytest.fixture(scope="session")
def build_cache_dir():
    return Path(mkdtemp())


@pytest.fixture(scope="session")
def pkg_dir():
    return PKG_DIR


@pytest.fixture(scope="session")
def xnat4tests_config() -> xnat4tests.Config:
    xnat4tests.start_xnat()
    return xnat4tests.Config()


@pytest.fixture(scope="session")
def xnat_server(xnat4tests_config):
    return xnat4tests_config.xnat_server


@pytest.fixture(scope="session")
def xnat_user(xnat4tests_config):
    return xnat4tests_config.xnat_user


@pytest.fixture(scope="session")
def xnat_password(xnat4tests_config):
    return xnat4tests_config.xnat_password


@pytest.fixture(scope="session")
def xnat_connection(xnat4tests_config):
    return xnat.connect(
        server=xnat4tests_config.xnat_server,
        user=xnat4tests_config.xnat_user,
        password=xnat4tests_config.xnat_password,
        loglevel="DEBUG",
        logger=logger,
    )
    return xnat4tests_config.xnat_connection


@pytest.fixture(scope="session")
def xnat_root_dir(xnat4tests_config) -> Path:
    return xnat4tests_config.xnat_root_dir


@pytest.fixture(scope="session")
def xnat_archive_dir(xnat_root_dir):
    return xnat_root_dir / "archive"


@pytest.fixture(scope="session")
def xnat_respository_uri(xnat_repository):
    return xnat_repository.server


# @pytest.fixture
# def dummy_niftix(work_dir):

#     nifti_path = work_dir / "t1w.nii"
#     json_path = work_dir / "t1w.json"

#     # Create a random Nifti file to satisfy BIDS parsers
#     hdr = nibabel.Nifti1Header()
#     hdr.set_data_shape((10, 10, 10))
#     hdr.set_zooms((1.0, 1.0, 1.0))  # set voxel size
#     hdr.set_xyzt_units(2)  # millimeters
#     hdr.set_qform(numpy.diag([1, 2, 3, 1]))
#     nibabel.save(
#         nibabel.Nifti1Image(
#             numpy.random.randint(0, 1, size=[10, 10, 10]),
#             hdr.get_best_affine(),
#             header=hdr,
#         ),
#         nifti_path,
#     )

#     with open(json_path, "w") as f:
#         json.dump({"test": "json-file"}, f)

#     return NiftiX.from_fspaths(nifti_path, json_path)
