#!/usr/bin/env python
"""
Runs all posible ciftify functions on some test data

Usage:
    run_ABIDE_NYU_tests [options] <testing_dir>

Arguments:
    <testing_dir>    The directory to run the tests inside

Options:
    --outputs-dir PATH     The directory to write the gerated outputs into
    --stages LIST          stage to run (see details)
    -h, --help             Prints this message

DETAILS
If '--outputs-dir' is not given, outputs will be written to
the following <testing_dir>/run-YYYY-MM-DD



Written by Erin W Dickie
"""

import ciftify
from ciftify.utils import run
import os
import pandas as pd
import datetime
import logging
import glob
from docopt import docopt

logger = logging.getLogger('ciftify')
logger.setLevel(logging.DEBUG)


def download_file(web_address, local_filename):
    '''download file if it does not exist'''
    if not os.path.isfile(local_filename):
        run(['wget', web_address, '-O', local_filename])
    if not os.path.getsize(local_filename) > 0:
        os.remove(local_filename)

def download_abide_freesurfer(subid, src_data_dir):
    '''download the subject from the amazon web a address'''
    abide_amazon_addy = 'https://s3.amazonaws.com/fcp-indi/data/Projects/ABIDE_Initiative/Outputs/freesurfer/5.1'

    abide_freesurfer = os.path.join(src_data_dir, 'abide', 'freesurfer')

    fs_subdir = os.path.join(abide_freesurfer, subid)
    if not os.path.exists(fs_subdir):
        run(['mkdir', '-p', fs_subdir])

    for subdir in ['mri', 'surf','label','scripts']:
        localdir = os.path.join(fs_subdir, subdir)
        if not os.path.exists(localdir):
            run(['mkdir', '-p', localdir])

    for filename in ['T1.mgz', 'wmparc.mgz', 'brain.finalsurfs.mgz']:
        download_file(os.path.join(abide_amazon_addy, subid, 'mri', filename.replace('+','%20')),
                                   os.path.join(fs_subdir, 'mri', filename))

    for surface in ['pial', 'white', 'sphere.reg', 'sphere', 'curv', 'sulc', 'thickness']:
        for hemi in ['lh', 'rh']:
            download_file(os.path.join(abide_amazon_addy, subid, 'surf', '{}.{}'.format(hemi,surface)),
                          os.path.join(fs_subdir, 'surf', '{}.{}'.format(hemi,surface)))

    for labelname in ['aparc', 'aparc.a2009s', 'BA']:
        for hemi in ['lh', 'rh']:
            download_file(os.path.join(abide_amazon_addy, subid, 'label', '{}.{}.annot'.format(hemi,labelname)),
                          os.path.join(fs_subdir, 'label', '{}.{}.annot'.format(hemi,labelname)))

    for script in ['recon-all.done', 'build-stamp.txt']:
        download_file(os.path.join(abide_amazon_addy, subid, 'scripts', script),
                      os.path.join(fs_subdir, 'scripts', script))
    return(abide_freesurfer)


# In[5]:

## functions I wrote to help test that folder contents exist, still working on it
def get_recon_all_outputs(hcp_data_dir, subid):
    recon_all_out = folder_contents_list(os.path.join(hcp_data_dir, subid))
    recon_all_out = [x.replace(subid, 'subid') for x in recon_all_out]
    return(recon_all_out)


def folder_contents_list(path):
    '''returns a list of folder contents'''
    folder_contents = glob.glob(os.path.join(path, '**'), recursive = True)
    folder_contents = [x.replace('{}/'.format(path),'') for x in folder_contents ]
    folder_contents = folder_contents[1:] ## the first element is the path name
    return(folder_contents)

def download_vmhc(subid):
    amazon_addy = 'https://s3.amazonaws.com/fcp-indi/data/Projects/ABIDE_Initiative/Outputs/cpac/filt_global/vmhc/{}_vmhc.nii.gz'.format(subid)
    sub_vmhc = os.path.join(src_vmhc, '{}_vmhc.nii.gz'.format(subid))
    download_file(amazon_addy, sub_vmhc)

def run_cifti_vis_recon_all(subid, ciftify_work_dir):
    '''runs both subject and index stages of the cifti_vis_recon_all'''
    run(['cifti_vis_recon_all', 'subject', '--ciftify-work-dir',ciftify_work_dir, subid])
    run(['cifti_vis_recon_all', 'index', '--ciftify-work-dir', ciftify_work_dir])

def run_ciftify_recon_all_test(subid, fs_dir, ciftify_work_dir, surf_reg,
            resample_to_T1w32k, no_symlinks=False):
    run(['mkdir','-p',ciftify_work_dir])
    run_cmd = ['ciftify_recon_all',
            '--ciftify-work-dir', ciftify_work_dir,
            '--fs-subjects-dir', fs_dir,
            '--surf-reg', surf_reg,
            subid]
    if resample_to_T1w32k:
        run_cmd.insert(1,'--resample-to-T1w32k')
    if no_symlinks:
        run_cmd.insert(1,'--no-symlinks')
    run(run_cmd)
    run(['cifti_vis_recon_all', 'subject', '--ciftify-work-dir',ciftify_work_dir, subid])
    run(['cifti_vis_recon_all', 'index', '--ciftify-work-dir', ciftify_work_dir])

def run_cifti_vis_maps_tests(subjects, ciftify_work_dir, src_data_dir):
    logger.info(ciftify.utils.section_header('Download ABIDE PCP data for ciftify_vol_result tests'))

    # ## Download ABIDE PCP data for ciftify_vol_result tests

    src_vmhc = os.path.join(src_data_dir, 'abide', 'vmhc')
    if not os.path.exists(src_vmhc):
        run(['mkdir', src_vmhc])

    for subid in subjects:
        download_vmhc(subid)

    qcdir = os.path.join(ciftify_work_dir, 'abide_vmhc_vis')

    ## run the tests
    run(['cifti_vis_map', 'nifti-snaps',
            '--ciftify-work-dir', ciftify_work_dir,
            '--qcdir', qcdir,
            '--resample-nifti', '--colour-palette', 'fidl',
            os.path.join(src_vmhc, '{}_vmhc.nii.gz'.format(subjects[0])), subjects[0], '{}_vmhc'.format(subjects[0])])

    run(['cifti_vis_map', 'nifti-snaps',
            '--ciftify-work-dir', ciftify_work_dir,
            '--qcdir', qcdir,
            '--resample-nifti',
            os.path.join(src_vmhc, '{}_vmhc.nii.gz'.format(subjects[0])), subjects[0], '{}_vmhc_dcol'.format(subjects[0])])

    run(['cifti_vis_map', 'nifti-snaps',
            '--qcdir', qcdir,
            '--resample-nifti', '--colour-palette', 'fidl',
            os.path.join(src_vmhc, '{}_vmhc.nii.gz'.format(subjects[0])), 'HCP_S1200_GroupAvg', '{}_vmhc'.format(subjects[0])])

    run(['cifti_vis_map', 'nifti-snaps',
            '--qcdir', qcdir,
            '--resample-nifti',
            os.path.join(src_vmhc, '{}_vmhc.nii.gz'.format(subjects[1])), 'HCP_S1200_GroupAvg', '{}_vmhc'.format(subjects[1])])

    run(['cifti_vis_map', 'index',
            '--hcp-data-dir', '/tmp',
            '--qcdir', os.path.join(ciftify_work_dir, 'abide_vmhc_vis')])

def run_ciftify_recon_all_tests(subid, src_data_dir, new_outputs):
    logger.info(ciftify.utils.section_header('Getting ABIDE and running recon-all'))
    # # Getting ABIDE and running recon-all

    fs_dir = download_abide_freesurfer(subid, src_data_dir)

    ## loop over all the tests
    for surf_reg in ['FS', 'MSMSulc']:
        for i,resample_to_T1w32k in [('t1', True), ('no',False)]:
            ciftify_work_dir = os.path.join(new_outputs, 'cfy_{}_{}'.format(surf_reg, i))
            run_ciftify_recon_all_test(subid, fs_dir, ciftify_work_dir, surf_reg,
                        resample_to_T1w32k, no_symlinks=False)


def main():
    arguments  = docopt(__doc__)

    #working_dir = '/home/edickie/Documents/ciftify_tests/'
    working_dir = arguments['<testing_dir>']
    work_from = arguments['--outputs-dir']

    src_data_dir= os.path.join(working_dir,'src_data')

    if work_from:
        new_outputs = work_from
    else:
        new_outputs= os.path.join(working_dir,'run_{}'.format(datetime.date.today()))

    logger = logging.getLogger('ciftify')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if not os.path.exists(new_outputs):
        run(['mkdir','-p', new_outputs])
    # Get settings, and add an extra handler for the subject log
    fh = logging.FileHandler(os.path.join(new_outputs, 'ciftify_ABIDE_NYU_tests.log'))
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


    logger.info(ciftify.utils.section_header('Starting ABIDE tests'))
    subjects=['NYU_0050954','NYU_0050955']


    run_ciftify_recon_all_tests(subjects[0], src_data_dir, new_outputs)
    run_cifti_vis_maps_tests(subjects,
            os.path.join(new_outputs, 'cfy_FS_no'),
            src_data_dir)

    logger.info(ciftify.utils.section_header('Done'))


if __name__ == '__main__':
    main()
