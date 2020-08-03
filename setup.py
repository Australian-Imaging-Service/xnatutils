import sys
import os.path
from setuptools import setup, find_packages

PKG_NAME = 'xnatutils'

# Extract version number from module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), PKG_NAME))
from version_ import __version__  # @IgnorePep8 @UnresolvedImport
sys.path.pop(0)

setup(
    name=PKG_NAME,
    version=__version__,
    author='Tom G. Close',
    author_email='tom.g.close@gmail.com',
    packages=find_packages(),
    entry_points={
        'console_scripts': ['xnat-get = xnatutils.get_:cmd',
                            'xnat-put = xnatutils.put_:cmd',
                            'xnat-ls = xnatutils.ls_:cmd',
                            'xnat-varget = xnatutils.varget_:cmd',
                            'xnat-varput = xnatutils.varput_:cmd',
                            'xnat-rename = xnatutils.rename_:cmd']},
    url='http://github.com/MonashBI/xnatutils',
    license='The MIT License (MIT)',
    description=(
        'A collection of scripts for downloading/uploading and listing '
        'data from XNAT repositories.'),
    long_description=open('README.rst').read(),
    install_requires=['xnat>=0.3.17',
                      'progressbar2>=3.16.0',
                      'future>=0.16'],
    python_requires='>=3.4',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Medical Science Apps."])
