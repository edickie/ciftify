from setuptools import setup, find_packages
import os.path
import sys

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()

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
    packages=find_packages(exclude=['tests']),
    data_files=[('', ['LICENSE', 'README.md'])],
    install_requires=[
            'docopt',
            'matplotlib',
            'nibabel',
            'numpy',
            'pandas',
            'PyYaml',
            'seaborn',
            'scipy'],
    include_package_data=True,
)
