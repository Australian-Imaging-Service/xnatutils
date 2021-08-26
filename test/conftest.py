import os
import shutil
from tempfile import mkdtemp
import pytest

TEST_DATA_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "data")
)
# temp_folder = mkdtemp()
# data_dir = os.path.join(temp_folder, "data")
# shutil.copytree(SRC_DATA_DIR, data_dir)


# @pytest.fixture(autouse=True)
# def add_np(doctest_namespace):
# #    doctest_namespace["np"] = numpy
#     doctest_namespace["os"] = os
#     doctest_namespace["pytest"] = pytest
#     doctest_namespace["datadir"] = data_dir


# @pytest.fixture(autouse=True)
# def _docdir(request):
#     """Grabbed from https://stackoverflow.com/a/46991331"""
#     # Trigger ONLY for the doctests.
#     doctest_plugin = request.config.pluginmanager.getplugin("doctest")
#     if isinstance(request.node, doctest_plugin.DoctestItem):

#         # Get the fixture dynamically by its name.
#         tmpdir = pp.local(data_dir)

#         # Chdir only for the duration of the test.
#         with tmpdir.as_cwd():
#             yield

#     else:
#         # For normal tests, we have to yield, since this is a yield-fixture.
#         yield


@pytest.fixture()
def test_data():
    return TEST_DATA_DIR


# For debugging in IDE's don't catch raised exceptions and let the IDE
# break at it
if os.getenv('_PYTEST_RAISE', "0") != "0":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value


# def pytest_unconfigure(config):
#     # Delete temp folder after session is finished
#     shutil.rmtree(temp_folder)
