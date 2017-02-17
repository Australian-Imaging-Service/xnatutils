import os.path
from setuptools import setup

# Get information about the version (polling mercurial if possible)
version = '0.1'

setup(
    name='xnatutils',
    version=version,
    author='Tom G. Close',
    author_email='tom.g.close@gmail.com',
    py_modules=['xnatutils'],
    scripts=[os.path.join('bin', 'xnat-ls'),
             os.path.join('bin', 'xnat-get'),
             os.path.join('bin', 'xnat-put')],
    url='https://gitlab.erc.monash.edu.au/mbi-image/XnatUtils',
    license='The MIT License (MIT)',
    description=(
        'A collection of scripts for downloading/uploading and listing '
        'data from MBI-XNAT'),
    long_description=open('README.md').read(),
    dependency_links=[
        'https://bitbucket.org/bigr_erasmusmc/xnatpy/get/default.tar.gz'],
#     install_requires=['xnat'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Medical Science Apps."])
