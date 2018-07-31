from setuptools import setup, find_packages
import os.path
import sys

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(
    name='ciftify',
    version='2.0.9',
    description='The tools of the Human Connectome Project (HCP) '\
            'adapted for working with non-HCP datasets',
    long_description=long_description,
    url='https://github.com/edickie/ciftify',
    author='Erin W.E. Dickie',
    author_email='erin.w.dickie@gmail.com',
    license='MIT',
    classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: MIT License',
            'Natural Language :: English',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 3'],
    keywords='PINT neuroimaging fMRI cifti gifti nifti HCP',
    packages=find_packages(exclude=['tests']),
    data_files=[('', ['LICENSE', 'README.md'])],
    entry_points={
        'console_scripts': [
            'cifti_vis_fmri=ciftify.bin.cifti_vis_fmri:main',
            'cifti_vis_PINT=ciftify.bin.cifti_vis_PINT:main',
            'cifti_vis_recon_all=ciftify.bin.cifti_vis_recon_all:main',
            'cifti_vis_map=ciftify.bin.cifti_vis_map:main',
            'ciftify_groupmask=ciftify.bin.ciftify_groupmask:main',
            'ciftify_meants=ciftify.bin.ciftify_meants:main',
            'ciftify_peaktable=ciftify.bin.ciftify_statclust_report:main',
            'ciftify_dlabel_report=ciftify.bin.ciftify_dlabel_report:main',
            'ciftify_PINT_vertices=ciftify.bin.ciftify_PINT_vertices:main',
            'ciftify_clean_img=ciftify.bin.ciftify_clean_img:main',
            'ciftify_postPINT1_concat=ciftify.bin.ciftify_postPINT1_concat:main',
            'ciftify_postPINT2_sub2sub=ciftify.bin.ciftify_postPINT2_sub2sub:main',
            'ciftify_recon_all=ciftify.bin.ciftify_recon_all:main',
            'ciftify_surface_rois=ciftify.bin.ciftify_surface_rois:main',
            'ciftify_vol_result=ciftify.bin.ciftify_vol_result:main',
            'ciftify_seed_corr=ciftify.bin.ciftify_seed_corr:main',
            'ciftify_subject_fmri=ciftify.bin.ciftify_subject_fmri:main',
            'extract_nuisance_regressors=ciftify.bin.extract_nuisance_regressors:main'
        ],
    },
    scripts=['ciftify/bin/filter_hcp.sh','ciftify/bin/cifti_vis_RSN'],
    install_requires=[
            'docopt',
            'matplotlib',
            'nibabel',
            'numpy',
            'pandas',
            'PyYaml',
            'seaborn',
            'scipy',
            'pillow',
            'nilearn',
            'sklearn',
            'pybids'],
    include_package_data=True,
)
