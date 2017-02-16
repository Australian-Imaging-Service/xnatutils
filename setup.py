from setuptools import setup

# Get information about the version (polling mercurial if possible)
version = '0.1'

# Get the requirements
with open('requirements.txt', 'r') as fh:
    _requires = fh.read().splitlines()

setup(
    name='xnatutils',
    version=version,
    author='Tom G. Close',
    author_email='tom.g.close@gmail.com',
    modules=['xnatutils'],
    url='https://gitlab.erc.monash.edu.au/mbi-image/XnatUtils',
    license='The MIT License (MIT)',
    description=(
        'A collection of scripts for downloading/uploading and listing '
        'data from MBI-XNAT'),
    long_description=open('README.rst').read(),
    install_requires=_requires,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Medical Science Apps."])
