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
    scripts=[os.path.join('scripts', 'xnat-ls'),
             os.path.join('scripts', 'xnat-get'),
             os.path.join('scripts', 'xnat-put'),
             os.path.join('scripts', 'xnat-varget'),
             os.path.join('scripts', 'xnat-varput'),
             os.path.join('scripts', 'xnat-rename')],
    url='http://github.com/monashbiomedicalimaging/xnatutils',
    license='The MIT License (MIT)',
    description=(
        'A collection of scripts for downloading/uploading and listing '
        'data from XNAT repositories.'),
    long_description=open('README.rst').read(),
    install_requires=['xnat>=0.3.9',
                      'progressbar2>=3.16.0',
                      'future>=0.16'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Medical Science Apps."])
