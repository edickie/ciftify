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

# coding: utf-8

# In[1]:


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
# In[75]:

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


logger.info(ciftify.utils.section_header('Starting'))
## getting the data




# In[4]:


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

    for filename in ['T1.mgz', 'aparc+aseg.mgz', 'aparc.a2009s+aseg.mgz', 'wmparc.mgz', 'brain.finalsurfs.mgz']:
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


logger.info(ciftify.utils.section_header('Getting ABIDE and running recon-all'))
# # Getting ABIDE and running recon-all

# In[8]:


abide_amazon_addy = 'https://s3.amazonaws.com/fcp-indi/data/Projects/ABIDE_Initiative/Outputs/freesurfer/5.1'
subid = 'NYU_0050954'

download_abide_freesurfer(subid, src_data_dir)

def run_cifti_vis_recon_all(subid, ciftify_work_dir):
    '''runs both subject and index stages of the cifti_vis_recon_all'''
    run(['cifti_vis_recon_all', 'subject', '--ciftify-work-dir',ciftify_work_dir, subid])
    run(['cifti_vis_recon_all', 'index', '--ciftify-work-dir', ciftify_work_dir])

def run_ciftify_recon_all_test(subid, fs_dir, ciftify_work_dir, surf_reg,
            resample_to_T1w32k, no_symlinks=False):
    run(['mkdir','-p',ciftify_work_dir])
    run_cmd['ciftify_recon_all',
            '--ciftify-work-dir', ciftify_work_dir,
            '--fs-subjects-dir', abide_freesurfer,
            '--surf-reg', surf_reg,
            '--resample-to-T1w32k',
            subid]
    if resample_to_T1w32k:
        run_cmd.insert(1,'--resample-to-T1w32k')
    if no_symlinks:
        run_cmd.insert(1,'--no-symlinks')
    run(run_cmd)
    run(['cifti_vis_recon_all', 'subject', '--ciftify-work-dir',ciftify_work_dir, subid])
    run(['cifti_vis_recon_all', 'index', '--ciftify-work-dir', ciftify_work_dir])

## loop over all the tests
for surf_reg in ['FS', 'MSMSulc']:
    for i,resample_to_T1w32k in [('t1', True), ('no',False)]:
        ciftify_work_dir = os.path.join(new_outputs, 'cfy_{}_{}'.format(surf_reg, i))
        run_ciftify_recon_all_w_T1w23k_FS(subid, fs_dir, ciftify_work_dir, surf_reg,
                    resample_to_T1w32k, no_symlinks=False)


logger.info(ciftify.utils.section_header('Download ABIDE PCP data for ciftify_vol_result tests'))
# ## Download ABIDE PCP data for ciftify_vol_result tests

# In[9]:


def download_vmhc(subid):
    amazon_addy = 'https://s3.amazonaws.com/fcp-indi/data/Projects/ABIDE_Initiative/Outputs/cpac/filt_global/vmhc/{}_vmhc.nii.gz'.format(subid)
    sub_vmhc = os.path.join(src_vmhc, '{}_vmhc.nii.gz'.format(subid))
    download_file(amazon_addy, sub_vmhc)

src_vmhc = os.path.join(src_data_dir, 'abide', 'vmhc')
if not os.path.exists(src_vmhc):
    run(['mkdir', src_vmhc])

subjects=['NYU_0050954','NYU_0050955']
for subid in subjects:
    download_vmhc(subid)


# In[10]:


subject = 'NYU_0050954'
run(['cifti_vis_map', 'nifti-snaps',
        '--hcp-data-dir', hcp_data_dir,
        '--qcdir', os.path.join(hcp_data_dir, 'abide_vmhc_vis'),
        '--resample-nifti', '--colour-palette', 'fidl',
        os.path.join(src_vmhc, '{}_vmhc.nii.gz'.format(subject)), subject, '{}_vmhc'.format(subject)])


# In[11]:


subject = 'NYU_0050954'
run(['cifti_vis_map', 'nifti-snaps',
        '--hcp-data-dir', hcp_data_dir,
        '--qcdir', os.path.join(hcp_data_dir, 'abide_vmhc_vis'),
        '--resample-nifti',
        os.path.join(src_vmhc, '{}_vmhc.nii.gz'.format(subject)), subject, '{}_vmhc_dcol'.format(subject)])


# In[12]:


subject = 'NYU_0050954'
run(['cifti_vis_map', 'nifti-snaps',
        '--qcdir', os.path.join(hcp_data_dir, 'abide_vmhc_vis'),
        '--resample-nifti', '--colour-palette', 'fidl',
        os.path.join(src_vmhc, '{}_vmhc.nii.gz'.format(subject)), 'HCP_S1200_GroupAvg', '{}_vmhc'.format(subject)])


# In[13]:


subject = 'NYU_0050955'
run(['cifti_vis_map', 'nifti-snaps',
        '--qcdir', os.path.join(hcp_data_dir, 'abide_vmhc_vis'),
        '--resample-nifti',
        os.path.join(src_vmhc, '{}_vmhc.nii.gz'.format(subject)), 'HCP_S1200_GroupAvg', '{}_vmhc'.format(subject)])


# In[14]:


run(['cifti_vis_map', 'index',
        '--hcp-data-dir', '/tmp',
        '--qcdir', os.path.join(hcp_data_dir, 'abide_vmhc_vis')])
