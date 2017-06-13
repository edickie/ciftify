from setuptools import setup, find_packages
import os.path
import sys

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()

# seaborn 0.7.1,
# scipy 0.19.0 (anaconda 0.18.1), pandas 0.19.2 (ana version: 0.15.2),
# numpy 1.12.1 (ana 1.12.0),
# nibabel 2.1.0 (ana 2.0.0), matplotlib 2.0.0 (and 1.4.2),
# docopt 0.6.2

setup(
    name='ciftify',
    version='0.1.0',
    description='The tools of the Human Connectome Project (HCP) '\
            'adapted for working with non-HCP datasets',
    long_description=long_description,
    url='https://github.com/edickie/ciftify',
    author='Erin W.E. Dickie',
    author_email='Erin.Dickie@camh.ca',
    license='MIT',
    classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: MIT License',
            'Natural Language :: English',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3'],
    keywords='PINT neuroimaging fMRI cifti gifti nifti HCP',
    packages=find_packages(exclude=['deprecated', 'tests']),
    install_requires=[
            'docopt',
            'matplotlib',
            'nibabel',
            'numpy',
            'pandas',
            'seaborn',
            'scipy',
            'PyYaml'],
    package_data={
            'data': ['*'],
            'bin': ['*']}
)
