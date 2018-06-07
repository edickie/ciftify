#!/usr/bin/env python
"""
Runs all posible ciftify functions on some test data

Usage:
    run_CNP_recon_all [options] <testing_dir>

Arguments:
    <testing_dir>    The directory to run the tests inside

Options:
    --outputs-dir PATH     The directory to write the gerated outputs into
    --resample-to-T1w32k   Wether to run resampling to T1w
    --surf-reg REGNAME     Which surface registration to runs
    --no-symlinks          Wether not run symlinks
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

def download_CNP_freesurfer(subid, src_data_dir):

    freesurfer_webtgz = 'https://s3.amazonaws.com/openneuro/ds000030/ds000030_R1.0.4/compressed/ds000030_R1.0.4_derivatives_freesurfer_sub50004-50008.zip'
    func_webtgz = 'https://s3.amazonaws.com/openneuro/ds000030/ds000030_R1.0.4/compressed/ds000030_R1.0.4_derivatives_sub50004-50008.zip'

    fs_subjects_dir = os.path.join(src_data_dir, 'ds000030_R1.0.4',
                                   'derivatives','freesurfer')
    if not os.path.exists(os.path.join(fs_subjects_dir, subid)):
        if not os.path.exists(os.path.join(src_data_dir,
                                           os.path.basename(freesurfer_webtgz))):
            run(['wget', '-P', src_data_dir, freesurfer_webtgz])

        run(['unzip',
             os.path.join(src_data_dir,
                          os.path.basename(freesurfer_webtgz)),
             os.path.join(sub_fs_path,'*'),
             '-d', src_data_dir])
    return fs_subject_dir

# In[5]:

## functions I wrote to help test that folder contents exist, still working on it
def get_recon_all_outputs(hcp_data_dir, subid):
    recon_all_out = folder_contents_list(os.path.join(hcp_data_dir, subid))
    recon_all_out = [x.replace(subid, 'subid') for x in recon_all_out]
    return(recon_all_out)

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
    t1w32k = arguments['--resample-to-T1w32k']
    surf_reg = arguments['--surf-reg']
    no_symlinks = arguments['--no-symlinks']


    src_data_dir= os.path.join(working_dir,'src_data')

    if work_from:
        new_outputs = work_from
    else:
        new_outputs= os.path.join(working_dir,'run_{}'.format(datetime.date.today()))

    t1w32k_lab = 't1' if t1w32k else 'no'
    sym_lab = 'no' is no_symlinks else 'sy'

    run_label = '{}_{}_{}'.format(surf_reg, t1w32k_lab, sym_lab)

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
    fh = logging.FileHandler(os.path.join(new_outputs, 'ciftify_CNP_recon_all_{}.log'.format(run_label)))
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


    logger.info(ciftify.utils.section_header('Starting CNP tests'))
    subjects=['sub-50005']

    fs_dir = download_CNP_freesurfer(subject, src_data_dir)
    ciftify_work_dir = os.path.join(new_outputs, 'cfy_{}'.format(run_label))
    run_ciftify_recon_all_test(subid, fs_dir, ciftify_work_dir, surf_reg,
                resample_to_T1w32k, no_symlinks)

    logger.info(ciftify.utils.section_header('Done'))


if __name__ == '__main__':
    main()
