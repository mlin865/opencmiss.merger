import io
import os
import re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'src', 'opencmiss', 'merger', '__init__.py')) as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Cannot find version information')


def readfile(filename, split=False):
    with io.open(filename, encoding="utf-8") as stream:
        if split:
            return stream.read().split("\n")
        return stream.read()


readme = readfile("README.rst", split=True)
readme.append('License')
readme.append('=======')
readme.append('')
readme.append('::')
readme.append('')
readme.append('')

software_licence = readfile("LICENSE")

requires = ['opencmiss.zinc']

setup(
    name='opencmiss.merger',
    version=version,
    description='OpenCMISS Merger functions.',
    long_description='\n'.join(readme) + software_licence,
    long_description_content_type='text/x-rst',
    classifiers=[],
    author='Hugh Sorby',
    author_email='h.sorby@auckland.ac.nz',
    url='https://github.com/OpenCMISS-Bindings/opencmiss.merger',
    license='Apache Software License',
    license_files=("LICENSE",),
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
)
