import re
import os.path
from setuptools import setup

MODULE_NAME = 'xnatutils'

# Extract version number from module
with open(os.path.join(os.path.dirname(__file__),
                       MODULE_NAME + '.py')) as f:
    contents = f.read()
found_versions = re.findall(r'__version__ == (.*)', contents)
if len(found_versions) != 1:
    raise Exception("Could not extract version number from module file")
version = found_versions[0]

setup(
    name='xnatutils',
    version=version,
    author='Tom G. Close',
    author_email='tom.g.close@gmail.com',
    py_modules=[MODULE_NAME],
    scripts=[os.path.join('scripts', 'xnat-ls'),
             os.path.join('scripts', 'xnat-get'),
             os.path.join('scripts', 'xnat-put'),
             os.path.join('scripts', 'xnat-varget'),
             os.path.join('scripts', 'xnat-varput')],
    url='https://gitlab.erc.monash.edu.au/mbi-image/XnatUtils',
    license='The MIT License (MIT)',
    description=(
        'A collection of scripts for downloading/uploading and listing '
        'data from MBI-XNAT'),
    long_description=open('README.rst').read(),
    install_requires=['xnat>=0.3',
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
