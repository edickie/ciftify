#!/usr/bin/env python
"""
Runs all posible ciftify functions on some test data

Usage:
    ciftify_intergration_tests [options] <testing_dir>

Arguments:
    <testing_dir> PATH    The directory to run the tests inside

Options:
    --outputs-dir PATH     The directory to write the gerated outputs into
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
fh = logging.FileHandler(os.path.join(new_outputs, 'ciftify_tests.log'))
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
logger.addHandler(fh)


logger.info(ciftify.utils.section_header('Starting'))
## getting the data

freesurfer_webtgz = 'https://s3.amazonaws.com/openneuro/ds000030/ds000030_R1.0.4/compressed/ds000030_R1.0.4_derivatives_freesurfer_sub50004-50008.zip'
func_webtgz = 'https://s3.amazonaws.com/openneuro/ds000030/ds000030_R1.0.4/compressed/ds000030_R1.0.4_derivatives_sub50004-50008.zip'

subids = ['sub-50005','sub-50007']
#subids = ['sub-50005','sub-50006']


fs_subjects_dir = os.path.join(src_data_dir, 'ds000030_R1.0.4',
                               'derivatives','freesurfer')
hcp_data_dir = os.path.join(new_outputs, 'hcp')

if not os.path.exists(hcp_data_dir):
    run(['mkdir','-p',hcp_data_dir])


# In[4]:


def download_file(web_address, local_filename):
    '''download file if it does not exist'''
    if not os.path.isfile(local_filename):
        run(['wget', web_address, '-O', local_filename])
    if not os.path.getsize(local_filename) > 0:
        os.remove(local_filename)


# In[5]:


def get_recon_all_outputs(hcp_data_dir, subid):
    recon_all_out = folder_contents_list(os.path.join(hcp_data_dir, subid))
    recon_all_out = [x.replace(subid, 'subid') for x in recon_all_out]
    return(recon_all_out)


# In[6]:


def folder_contents_list(path):
    '''returns a list of folder contents'''
    folder_contents = glob.glob(os.path.join(path, '**'), recursive = True)
    folder_contents = [x.replace('{}/'.format(path),'') for x in folder_contents ]
    folder_contents = folder_contents[1:] ## the first element is the path name
    return(folder_contents)


# In[7]:


def seed_corr_default_out(func, seed):
    functype, funcbase = ciftify.io.determine_filetype(func)
    _, seedbase = ciftify.io.determine_filetype(seed)
    outputdir = os.path.dirname(func)
    outbase = '{}_{}'.format(funcbase, seedbase)
    outputname = os.path.join(outputdir, outbase)
    if functype == "nifti": outputname = '{}.nii.gz'.format(outputname)
    if functype == "cifti": outputname = '{}.dscalar.nii'.format(outputname)
    return(outputname)

def run_vis_map(result_map, result_prefix, result_type):
    run(['cifti_vis_map', '{}-snaps'.format(result_type), '--hcp-data-dir', hcp_data_dir,
     result_map, subid, result_prefix])

def run_seedcorr_peaktable(result_map):
    run(['ciftify_peaktable',
         '--min-threshold', '-0.5',
         '--max-threshold', '0.5',
         '--no-cluster-dlabel',
         result_map])

def run_seed_corr_fmri_test(func_cifti, hcp_data_dir, roi_dir):
    ''' runs one of the seed corrs and then peak table to get a csv to test for each dtseries'''
    subid = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(func_cifti)))))
    atlas_vol =  os.path.join(hcp_data_dir, subid, 'MNINonLinear', 'wmparc.nii.gz')
    struct = 'RIGHT-PUTAMEN'
    putamen_vol_seed_mask = os.path.join(roi_dir, '{}_{}_vol.nii.gz'.format(subid, struct))
    if not os.path.exists(putamen_vol_seed_mask):
        run(['wb_command', '-volume-label-to-roi', atlas_vol, putamen_vol_seed_mask, '-name', struct])
    run(['ciftify_seed_corr', func_cifti, putamen_vol_seed_mask])
    run_seedcorr_peaktable(seed_corr_default_out(func_cifti, putamen_vol_seed_mask))


logger.info(ciftify.utils.section_header('Getting ABIDE and running recon-all'))
# # Getting ABIDE and running recon-all

# In[8]:


abide_amazon_addy = 'https://s3.amazonaws.com/fcp-indi/data/Projects/ABIDE_Initiative/Outputs/freesurfer/5.1'

subid = 'NYU_0050954'
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


# In[ ]:


run(['ciftify_recon_all', '--hcp-data-dir', hcp_data_dir,
        '--fs-subjects-dir', abide_freesurfer,
        'NYU_0050954'])


# In[ ]:



run(['cifti_vis_recon_all', 'snaps', '--hcp-data-dir',hcp_data_dir, 'NYU_0050954'])
run(['cifti_vis_recon_all', 'index', '--hcp-data-dir', hcp_data_dir])

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


logger.info(ciftify.utils.section_header('ciftify_vol_result with HCP data..if data in src'))

# # Testing ciftify_vol_result with HCP data..if data in src

# In[15]:


HCP_subid = '100307'
HCP_src_dir = os.path.join(src_data_dir, 'HCP')
label_vol = os.path.join(HCP_src_dir, HCP_subid, 'MNINonLinear', 'aparc+aseg.nii.gz')
scalar_vol = os.path.join(HCP_src_dir, HCP_subid, 'MNINonLinear', 'T2w_restore.nii.gz')

run_HCP_tests = True if os.path.exists(HCP_src_dir) else False

if run_HCP_tests:
    HCP_out_dir = os.path.join(new_outputs, 'HCP')
    run(['mkdir', '-p', HCP_out_dir])
    run(['ciftify_vol_result', '--HCP-Pipelines', '--resample-nifti',
         '--hcp-data-dir', HCP_src_dir,
        '--integer-labels', HCP_subid, label_vol,
         os.path.join(HCP_out_dir, '{}.aparc+aseg.32k_fs_LR.dscalar.nii'.format(HCP_subid))])


# In[16]:


if run_HCP_tests:
    run(['ciftify_vol_result','--HCP-Pipelines', '--HCP-MSMAll','--resample-nifti',
         '--hcp-data-dir', HCP_src_dir,
        '--integer-labels', HCP_subid, label_vol,
         os.path.join(HCP_out_dir, '{}.aparc+aseg_MSMAll.32k_fs_LR.dscalar.nii'.format(HCP_subid))])


# In[17]:


if run_HCP_tests:
    run(['ciftify_vol_result','--HCP-Pipelines', '--resample-nifti',
         '--hcp-data-dir', HCP_src_dir, HCP_subid,
         os.path.join(HCP_src_dir, HCP_subid, 'MNINonLinear', 'T2w_restore.nii.gz'),
         os.path.join(HCP_out_dir, '{}.T2w_restore.32k_fs_LR.dscalar.nii'.format(HCP_subid))])


# In[18]:


if run_HCP_tests:
    run(['ciftify_vol_result','--HCP-Pipelines', '--HCP-MSMAll',
         '--hcp-data-dir', HCP_src_dir, HCP_subid,
         os.path.join(HCP_src_dir, HCP_subid, 'MNINonLinear', 'T2w_restore.2.nii.gz'),
         os.path.join(HCP_out_dir, '{}.T2w_restore_MSMAll.32k_fs_LR.dscalar.nii'.format(HCP_subid))])

logger.info(ciftify.utils.section_header('Download the main dataset'))

# # Download the main dataset

# In[19]:


subids = ['sub-50005','sub-50007']

if not os.path.exists(src_data_dir):
    run(['mkdir','-p',src_data_dir])

for subid in subids:
    sub_fs_path = os.path.join('ds000030_R1.0.4','derivatives','freesurfer', subid)
if not os.path.exists(os.path.join(src_data_dir, sub_fs_path)):
    if not os.path.exists(os.path.join(src_data_dir,
                                       os.path.basename(freesurfer_webtgz))):
        run(['wget', '-P', src_data_dir, freesurfer_webtgz])

    run(['unzip',
         os.path.join(src_data_dir,
                      os.path.basename(freesurfer_webtgz)),
         os.path.join(sub_fs_path,'*'),
         '-d', src_data_dir])

for subid in subids:
    sub_file = os.path.join('ds000030_R1.0.4','derivatives',
                            'fmriprep', subid,'func',
                            '{}_task-rest_bold_space-T1w_preproc.nii.gz'.format(subid))
    if not os.path.exists(os.path.join(src_data_dir,sub_file)):
        if not os.path.exists(os.path.join(src_data_dir,
                                           os.path.basename(func_webtgz))):
            run(['wget', '-P', src_data_dir, func_webtgz])

        run(['unzip',
             os.path.join(src_data_dir,
                          os.path.basename(func_webtgz)),
             sub_file,
             '-d', src_data_dir])

for subid in subids:
    sub_file = os.path.join('ds000030_R1.0.4','derivatives',
                            'fmriprep', subid,'func',
                            '{}_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz'.format(subid))
    if not os.path.exists(os.path.join(src_data_dir,sub_file)):
        if not os.path.exists(os.path.join(src_data_dir,
                                           os.path.basename(func_webtgz))):
            run(['wget', '-P', src_data_dir, func_webtgz])

        run(['unzip',
             os.path.join(src_data_dir,
                          os.path.basename(func_webtgz)),
             sub_file,
             '-d', src_data_dir])


# In[ ]:


run(['ciftify_recon_all', '--resample-to-T1w32k', '--hcp-data-dir', hcp_data_dir,
    '--fs-subjects-dir', fs_subjects_dir,
    subids[0]])


# In[ ]:


run(['ciftify_recon_all', '--hcp-data-dir', hcp_data_dir,
    '--fs-subjects-dir', fs_subjects_dir,
    subids[1]])


# In[ ]:


for subid in subids:
    run(['cifti_vis_recon_all', 'snaps', '--hcp-data-dir',hcp_data_dir, subid])
run(['cifti_vis_recon_all', 'index', '--hcp-data-dir', hcp_data_dir])


# In[ ]:


# for subid in ['sub-50004','sub-50006', 'sub-50008']:
#     run(['ciftify_recon_all', '--hcp-data-dir', hcp_data_dir,
#         '--fs-subjects-dir', fs_subjects_dir,
#         subid])


# In[ ]:


# for subid in ['sub-50004','sub-50006', 'sub-50008']:
#     run(['cifti_vis_recon_all', 'snaps', '--hcp-data-dir',hcp_data_dir, subid])
# run(['cifti_vis_recon_all', 'index', '--hcp-data-dir', hcp_data_dir])

logger.info(ciftify.utils.section_header('Running ciftify_subject_fmri'))
# # Running ciftify_subject_fmri

# In[ ]:


subid=subids[0]
native_func = os.path.join(src_data_dir,'ds000030_R1.0.4','derivatives',
                 'fmriprep', subid,'func',
                 '{}_task-rest_bold_space-native_preproc.nii.gz'.format(subid))
mat_file = os.path.join(src_data_dir, 'ds000030_R1.0.4','derivatives',
                            'fmriprep', subid,'func',
                            '{}_task-rest_bold_T1_to_EPI.mat'.format(subid))

with open(mat_file, "w") as text_file:
    text_file.write('''1.03  -0.015  0.0025  -15.0
0.014  1.01  -0.005  -11.9
-0.007 0.01  0.99  2
0  0  0  1
''')

t1_func = os.path.join(src_data_dir,'ds000030_R1.0.4','derivatives',
                 'fmriprep', subid,'func',
                 '{}_task-rest_bold_space-T1w_preproc.nii.gz'.format(subid))
if not os.path.exists(native_func):
    run(['flirt', '-in', t1_func, '-ref', t1_func,
         '-out', native_func, '-init', mat_file, '-applyxfm'])

run(['ciftify_subject_fmri', '--SmoothingFWHM', '12',
    '--hcp-data-dir', hcp_data_dir,
    native_func, subid, 'rest_test1'])


# In[ ]:


subid=subids[0]
run(['cifti_vis_fmri', 'snaps', '--SmoothingFWHM', '12', '--hcp-data-dir',hcp_data_dir, 'rest_test1', subid])


# In[ ]:


subid=subids[0]
native_func_mean = os.path.join(src_data_dir,'ds000030_R1.0.4','derivatives',
                 'fmriprep', subid,'func',
                 '{}_task-rest_bold_space-native_mean.nii.gz'.format(subid))

run(['fslmaths', native_func, '-Tmean', native_func_mean])

run(['ciftify_subject_fmri', '--hcp-data-dir', hcp_data_dir,
    '--FLIRT-template', native_func_mean, native_func, subid, 'rest_test2'])


# In[ ]:


subid=subids[0]
run(['cifti_vis_fmri', 'snaps', '--smooth-conn', '12', '--hcp-data-dir',hcp_data_dir, 'rest_test2', subid])


# In[ ]:


subid = subids[1]
run(['ciftify_subject_fmri', '--SmoothingFWHM', '8', '--FLIRT-dof', '30',
    '--hcp-data-dir', hcp_data_dir,
     '--OutputSurfDiagnostics',
    os.path.join(src_data_dir,'ds000030_R1.0.4','derivatives',
                 'fmriprep', subid,'func',
                 '{}_task-rest_bold_space-T1w_preproc.nii.gz'.format(subid)),
    subid, 'rest_test_dof30'])


# In[ ]:


subid = subids[1]
run(['cifti_vis_fmri', 'snaps', '--hcp-data-dir',hcp_data_dir, 'rest_test_dof30', subid])


# In[ ]:


subid = subids[1]
run(['ciftify_subject_fmri', '--already-in-MNI', '--SmoothingFWHM', '8',
    '--hcp-data-dir', hcp_data_dir,
    os.path.join(src_data_dir,'ds000030_R1.0.4','derivatives',
                 'fmriprep', subid,'func',
                 '{}_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz'.format(subid)),
    subid, 'rest_bad_transform'])


# In[ ]:


subid = subids[1]
run(['cifti_vis_fmri', 'snaps', '--hcp-data-dir',hcp_data_dir, 'rest_bad_transform', subid])


# In[ ]:


run(['cifti_vis_fmri', 'index', '--hcp-data-dir', hcp_data_dir])


# In[21]:


from glob import glob
dtseries_files = glob(os.path.join(hcp_data_dir,'*',
                                       'MNINonLinear', 'Results',
                                       '*', '*Atlas_s*.dtseries.nii'))
run(['cifti_vis_RSN', 'cifti-snaps',
         '--hcp-data-dir',hcp_data_dir,
         '--colour-palette', 'PSYCH-NO-NONE',
         dtseries_files[0],
         os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(dtseries_files[0])))))])

for dtseries in dtseries_files[1:]:
    run(['cifti_vis_RSN', 'cifti-snaps',
         '--hcp-data-dir',hcp_data_dir, dtseries,
         os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(dtseries)))))])
run(['cifti_vis_RSN', 'index',
     '--hcp-data-dir', hcp_data_dir])


# In[22]:


run(['cifti_vis_RSN', 'index', '--hcp-data-dir', hcp_data_dir])


# In[117]:


roi_dir = os.path.join(new_outputs, 'rois')
if not os.path.exists(roi_dir):
    run(['mkdir', roi_dir])
for dtseries in dtseries_files:
    run_seed_corr_fmri_test(dtseries, hcp_data_dir, roi_dir)


# In[24]:


run(['cifti_vis_RSN', 'nifti-snaps',
         '--hcp-data-dir',hcp_data_dir,
         '--qcdir', os.path.join(hcp_data_dir, 'RSN_from_nii'),
         '--colour-palette', 'PSYCH-NO-NONE',

        os.path.join(src_data_dir,'ds000030_R1.0.4','derivatives',
                 'fmriprep', subids[0],'func',
                 '{}_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz'.format(subids[0])),
        subids[0]])

run(['cifti_vis_RSN', 'nifti-snaps',
         '--hcp-data-dir',hcp_data_dir,
         '--qcdir', os.path.join(hcp_data_dir, 'RSN_from_nii'),
        os.path.join(src_data_dir,'ds000030_R1.0.4','derivatives',
                 'fmriprep', subids[1],'func',
                 '{}_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz'.format(subids[1])),
        subids[1]])

run(['cifti_vis_RSN', 'index',
     '--qcdir', os.path.join(hcp_data_dir, 'RSN_from_nii'),
     '--hcp-data-dir', hcp_data_dir])


# In[116]:


groupmask_cmd = ['ciftify_groupmask', os.path.join(hcp_data_dir, 'groupmask.dscalar.nii')]
groupmask_cmd.extend(dtseries_files)

run(groupmask_cmd)

logger.info(ciftify.utils.section_header('Running PINT and related functions'))
# # Running PINT and related functions

# In[26]:


subid = subids[0]
run(['mkdir', '-p', os.path.join(new_outputs, 'PINT', subid)])

run(['ciftify_PINT_vertices', '--pcorr',
     os.path.join(hcp_data_dir, subid,'MNINonLinear', 'Results',
                  'rest_test1', 'rest_test1_Atlas_s12.dtseries.nii'),
     os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.L.midthickness.32k_fs_LR.surf.gii'.format(subid)),
     os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.R.midthickness.32k_fs_LR.surf.gii'.format(subid)),
     os.path.join(ciftify.config.find_ciftify_global(), 'PINT', 'Yeo7_2011_80verts.csv'),
     os.path.join(new_outputs, 'PINT', subid, subid)])


# In[27]:


subid = subids[0]
run(['cifti_vis_PINT', 'snaps', '--hcp-data-dir',  hcp_data_dir,
     os.path.join(hcp_data_dir, subid,'MNINonLinear', 'Results',
                  'rest_test1', 'rest_test1_Atlas_s12.dtseries.nii'),
     subid,
     os.path.join(new_outputs, 'PINT', subid, '{}_summary.csv'.format(subid))])


# In[28]:


subid = subids[1]
run(['mkdir', '-p', os.path.join(new_outputs, 'PINT', subid)])

run(['ciftify_PINT_vertices',
     os.path.join(hcp_data_dir, subid,'MNINonLinear', 'Results',
                  'rest_test_dof30', 'rest_test_dof30_Atlas_s8.dtseries.nii'),
     os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.L.midthickness.32k_fs_LR.surf.gii'.format(subid)),
     os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.R.midthickness.32k_fs_LR.surf.gii'.format(subid)),
     os.path.join(ciftify.config.find_ciftify_global(), 'PINT', 'Yeo7_2011_80verts.csv'),
     os.path.join(new_outputs, 'PINT', subid, subid)])


# In[29]:


run(['cifti_vis_PINT', 'snaps', '--hcp-data-dir',  hcp_data_dir,
     os.path.join(hcp_data_dir, subid,'MNINonLinear', 'Results',
                  'rest_test_dof30', 'rest_test_dof30_Atlas_s8.dtseries.nii'),
     subid,
     os.path.join(new_outputs, 'PINT', subid, '{}_summary.csv'.format(subid))])


# In[120]:


subid = subids[1]
run(['mkdir', '-p', os.path.join(new_outputs, 'PINT', subid)])

run(['ciftify_PINT_vertices', '--outputall',
     os.path.join(hcp_data_dir, subid,'MNINonLinear', 'Results',
                  'rest_test_dof30', 'rest_test_dof30_Atlas_s8.dtseries.nii'),
     os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.L.midthickness.32k_fs_LR.surf.gii'.format(subid)),
     os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.R.midthickness.32k_fs_LR.surf.gii'.format(subid)),
     os.path.join(ciftify.config.find_ciftify_global(), 'PINT', 'Yeo7_2011_80verts.csv'),
     os.path.join(new_outputs, 'PINT', subid, '{}_all'.format(subid))])


# In[121]:


run(['cifti_vis_PINT', 'snaps', '--hcp-data-dir',  hcp_data_dir,
     os.path.join(hcp_data_dir, subid,'MNINonLinear', 'Results',
                  'rest_test_dof30', 'rest_test_dof30_Atlas_s8.dtseries.nii'),
     subid,
     os.path.join(new_outputs, 'PINT', subid, '{}_all_summary.csv'.format(subid))])


# In[122]:


run(['cifti_vis_PINT', 'index', '--hcp-data-dir',  hcp_data_dir])


# In[123]:


summary_files = glob(os.path.join(new_outputs, 'PINT', '*','*_summary.csv'))
concat_cmd = ['ciftify_postPINT1_concat',
           os.path.join(new_outputs, 'PINT', 'concatenated.csv')]
concat_cmd.extend(summary_files)
run(concat_cmd)


# In[124]:


run(['ciftify_postPINT2_sub2sub', os.path.join(new_outputs, 'PINT', 'concatenated.csv'),
     os.path.join(new_outputs, 'PINT', 'ivertex_distances.csv')])


# In[125]:


run(['ciftify_postPINT2_sub2sub', '--roiidx', '14',
     os.path.join(new_outputs, 'PINT', 'concatenated.csv'),
     os.path.join(new_outputs, 'PINT', 'ivertex_distances_roiidx14.csv')])

logger.info(ciftify.utils.section_header('Running ciftify_surface_rois'))
# # Running ciftify_surface_rois

# In[126]:


vertices1_csv = os.path.join(src_data_dir, 'vertices1.csv')

with open(vertices1_csv, "w") as text_file:
    text_file.write('''hemi,vertex
L,11801
L,26245
L,26235
L,26257
L,13356
L,289
L,13336
L,13337
L,26269
L,13323
L,26204
L,26214
L,13326
L,13085
L,13310
L,13281
L,13394
L,13395
L,26263
L,26265
L,13343
L,77
L,13273
L,13342
L,26271
L,11804
L,13322
L,13369
L,13353
L,26268
L,26201
L,26269
L,68
L,13391
''')

subid = subids[0]
run(['mkdir', '-p', os.path.join(new_outputs, 'rois')])
run(['ciftify_surface_rois', vertices1_csv, '10', '--gaussian',
     os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.L.midthickness.32k_fs_LR.surf.gii'.format(subid)),
     os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.R.midthickness.32k_fs_LR.surf.gii'.format(subid)),
     os.path.join(new_outputs, 'rois', 'gaussian_roi.dscalar.nii')])


# In[37]:


subid = subids[0]
run(['cifti_vis_map', 'cifti-snaps', '--hcp-data-dir',
     hcp_data_dir,
     os.path.join(new_outputs, 'rois', 'gaussian_roi.dscalar.nii'),
     subid,
     'gaussian_roi'])


# In[38]:


run(['ciftify_peaktable', '--max-threshold', '0.05',
    '--left-surface', os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.L.midthickness.32k_fs_LR.surf.gii'.format(subid)),
    '--right-surface', os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.R.midthickness.32k_fs_LR.surf.gii'.format(subid)),
    os.path.join(new_outputs, 'rois', 'gaussian_roi.dscalar.nii')])


# In[39]:


vertices2_csv = os.path.join(src_data_dir, 'vertices1.csv')

with open(vertices2_csv, "w") as text_file:
    text_file.write('''hemi,vertex
R,2379
R,2423
R,2423
R,2629
R,29290
R,29290
R,1794
R,29199
R,1788
R,2380
R,2288
R,29320
R,29274
R,29272
R,29331
R,29356
R,2510
R,29345
R,2506
R,2506
R,1790
R,29305
R,2630
R,2551
R,2334
R,2334
R,29306
R,2551
R,2422
R,29256
R,2468
R,29332
R,2425
R,29356
''')

run(['mkdir', '-p', os.path.join(new_outputs, 'rois')])
run(['ciftify_surface_rois', vertices1_csv, '6', '--probmap',
     os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.L.midthickness.32k_fs_LR.surf.gii'.format(subid)),
     os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.R.midthickness.32k_fs_LR.surf.gii'.format(subid)),
     os.path.join(new_outputs, 'rois', 'probmap_roi.dscalar.nii')])


# In[40]:


subid = subids[0]
run(['cifti_vis_map', 'cifti-snaps', '--hcp-data-dir',
     hcp_data_dir,
     os.path.join(new_outputs, 'rois', 'probmap_roi.dscalar.nii'),
     subid,
     'probmap_roi'])


# In[41]:


run(['ciftify_peaktable', '--max-threshold', '0.05',
    '--left-surface', os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.L.midthickness.32k_fs_LR.surf.gii'.format(subid)),
    '--right-surface', os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.R.midthickness.32k_fs_LR.surf.gii'.format(subid)),
   os.path.join(new_outputs, 'rois', 'probmap_roi.dscalar.nii')])


# In[42]:


for hemi in ['L','R']:
    run(['wb_command', '-surface-vertex-areas',
         os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.{}.midthickness.32k_fs_LR.surf.gii'.format(subid, hemi)),
         os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.{}.midthickness_va.32k_fs_LR.shape.gii'.format(subid, hemi))])

run(['ciftify_peaktable',
    '--outputbase', os.path.join(new_outputs, 'rois', 'probmap_roi_withva'),
    '--max-threshold', '0.05',
    '--left-surface', os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.L.midthickness.32k_fs_LR.surf.gii'.format(subid)),
    '--right-surface', os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.R.midthickness.32k_fs_LR.surf.gii'.format(subid)),
    '--left-surf-area', os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.L.midthickness_va.32k_fs_LR.shape.gii'.format(subid)),
    '--right-surf-area', os.path.join(hcp_data_dir, subid,'MNINonLinear','fsaverage_LR32k',
                  '{}.R.midthickness_va.32k_fs_LR.shape.gii'.format(subid)),
   os.path.join(new_outputs, 'rois', 'probmap_roi.dscalar.nii')])


# In[43]:


run(['ciftify_surface_rois',
      os.path.join(ciftify.config.find_ciftify_global(), 'PINT', 'Yeo7_2011_80verts.csv'),
      '6', '--vertex-col', 'tvertex', '--labels-col', 'NETWORK', '--overlap-logic', 'EXCLUDE',
      os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                'S1200.L.midthickness_MSMAll.32k_fs_LR.surf.gii'),
      os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                'S1200.R.midthickness_MSMAll.32k_fs_LR.surf.gii'),
      os.path.join(new_outputs, 'rois', 'tvertex.dscalar.nii')])


# In[44]:


subid = subids[0]
run(['cifti_vis_map', 'cifti-snaps', '--hcp-data-dir',
     hcp_data_dir,
     os.path.join(new_outputs, 'rois', 'tvertex.dscalar.nii'),
     subid,
     'tvertex'])

logger.info(ciftify.utils.section_header('Running ciftify_seed_corr'))
# # Running ciftify_seed_corr

# In[77]:


subid = subids[0]
smoothing = 12
func_vol = os.path.join(hcp_data_dir, subid, 'MNINonLinear', 'Results', 'rest_test1', 'rest_test1.nii.gz')
func_cifti_sm0 = os.path.join(hcp_data_dir, subid, 'MNINonLinear', 'Results', 'rest_test1', 'rest_test1_Atlas_s0.dtseries.nii')
func_cifti_smoothed = os.path.join(hcp_data_dir, subid, 'MNINonLinear', 'Results', 'rest_test1', 'rest_test1_Atlas_s{}.dtseries.nii'.format(smoothing))
atlas_vol =  os.path.join(hcp_data_dir, subid, 'MNINonLinear', 'wmparc.nii.gz')

seed_corr_dir = os.path.join(new_outputs, 'ciftify_seed_corr')
if not os.path.exists(seed_corr_dir):
    run(['mkdir', '-p', seed_corr_dir])
struct = 'RIGHT-PUTAMEN'
putamen_vol_seed_mask = os.path.join(seed_corr_dir, '{}_{}_vol.nii.gz'.format(subid, struct))
run(['wb_command', '-volume-label-to-roi', atlas_vol, putamen_vol_seed_mask, '-name', struct])



# In[76]:


### All results
# ciftify_peaktable - with va input
# cifti_vis_map
run(['extract_nuisance_regressors',
     os.path.join(hcp_data_dir, subid, 'MNINonLinear'),
     func_vol])


# In[79]:


run(['ciftify_seed_corr', func_vol, putamen_vol_seed_mask])
run(['cifti_vis_map', 'nifti-snaps', '--hcp-data-dir',
     hcp_data_dir,
     seed_corr_default_out(func_vol, putamen_vol_seed_mask),
     subid,
     '{}_{}_niftitonifti_unmasked'.format(subid, struct)])

# In[78]:


run(['ciftify_seed_corr', '--fisher-z', func_vol, putamen_vol_seed_mask])
run(['cifti_vis_map', 'nifti-snaps', '--hcp-data-dir',
     hcp_data_dir,
     seed_corr_default_out(func_vol, putamen_vol_seed_mask),
     subid,
     '{}_{}_niftitoniftiZ_unmasked'.format(subid, struct)])


# In[80]:


run(['ciftify_seed_corr',
     '--outputname', os.path.join(seed_corr_dir, '{}_{}_niftitonifti_masked.nii.gz'.format(subid, struct)),
     '--mask', os.path.join(hcp_data_dir, subid, 'MNINonLinear', 'brainmask_fs.nii.gz'),
     func_vol, putamen_vol_seed_mask])

run(['cifti_vis_map', 'nifti-snaps', '--hcp-data-dir',
     hcp_data_dir,
     os.path.join(seed_corr_dir, '{}_{}_niftitonifti_masked.nii.gz'.format(subid, struct)),
     subid,
     '{}_{}_niftitonifti_masked'.format(subid, struct)])


# In[81]:


run(['ciftify_seed_corr', '--fisher-z',
     '--outputname', os.path.join(seed_corr_dir, '{}_{}_niftitoniftiZ_masked.nii.gz'.format(subid, struct)),
     '--mask', os.path.join(hcp_data_dir, subid, 'MNINonLinear', 'brainmask_fs.nii.gz'),
     func_vol, putamen_vol_seed_mask])

run(['cifti_vis_map', 'nifti-snaps', '--hcp-data-dir',
     hcp_data_dir,
     os.path.join(seed_corr_dir, '{}_{}_niftitoniftiZ_masked.nii.gz'.format(subid, struct)),
     subid,
     '{}_{}_niftitoniftiZ_masked'.format(subid, struct)])


# In[82]:


run(['ciftify_seed_corr', func_cifti_smoothed, putamen_vol_seed_mask])

run(['cifti_vis_map', 'cifti-snaps', '--hcp-data-dir',
     hcp_data_dir,
     seed_corr_default_out(func_cifti_smoothed, putamen_vol_seed_mask),
     subid,
     '{}_{}_niftitocifti_unmasked'.format(subid, struct)])


# In[82]:


run(['ciftify_seed_corr', '--fisher-z', func_cifti_smoothed, putamen_vol_seed_mask])

run(['cifti_vis_map', 'cifti-snaps', '--hcp-data-dir',
     hcp_data_dir,
     seed_corr_default_out(func_cifti_smoothed, putamen_vol_seed_mask),
     subid,
     '{}_{}_niftitociftiZ_unmasked'.format(subid, struct)])

run_seedcorr_peaktable(seed_corr_default_out(func_cifti_smoothed, putamen_vol_seed_mask))


# In[83]:


cifti_mask = os.path.join(seed_corr_dir, '{}_func_mask.dscalar.nii'.format(subid))
run(['wb_command', '-cifti-math', "'(x > 0)'", cifti_mask,
    '-var', 'x', func_cifti_sm0, '-select', '1', '1'])
run(['ciftify_seed_corr',
     '--outputname', os.path.join(seed_corr_dir, '{}_{}_niftitocifti_masked.dscalar.nii'.format(subid, struct)),
     '--mask', cifti_mask,
     func_cifti_smoothed, putamen_vol_seed_mask])

subid = subids[0]
run(['cifti_vis_map', 'cifti-snaps', '--hcp-data-dir', hcp_data_dir,
     os.path.join(seed_corr_dir, '{}_{}_niftitocifti_masked.dscalar.nii'.format(subid, struct)),
     subid,
     '{}_{}_niftitocifti_masked'.format(subid, struct)])
run_seedcorr_peaktable(os.path.join(seed_corr_dir, '{}_{}_niftitocifti_masked.dscalar.nii'.format(subid, struct)))


# In[84]:


run(['ciftify_seed_corr', '--fisher-z',
     '--outputname', os.path.join(seed_corr_dir, '{}_{}_niftitociftiZ_masked.dscalar.nii'.format(subid, struct)),
     '--mask', cifti_mask,
     func_cifti_smoothed, putamen_vol_seed_mask])

subid = subids[0]
run(['cifti_vis_map', 'cifti-snaps', '--hcp-data-dir', hcp_data_dir,
     os.path.join(seed_corr_dir, '{}_{}_niftitociftiZ_masked.dscalar.nii'.format(subid, struct)),
     subid,
     '{}_{}_niftitociftiZ_masked'.format(subid, struct)])
run_seedcorr_peaktable(os.path.join(seed_corr_dir, '{}_{}_niftitociftiZ_masked.dscalar.nii'.format(subid, struct)))


# In[85]:


func = func_cifti_smoothed
seed = os.path.join(seed_corr_dir, '{}_{}_cifti.dscalar.nii'.format(subid, struct))
result_map = seed_corr_default_out(func, seed)
result_type = 'cifti'
result_prefix = '{}_{}_ciftitocifti_unmasked'.format(subid, struct)
run(['wb_command', '-cifti-create-dense-from-template',
     func_cifti_sm0, seed,
     '-volume-all', putamen_vol_seed_mask])

run(['ciftify_seed_corr', func, seed])


# In[86]:


run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[87]:


result_map = os.path.join(seed_corr_dir, '{}_{}_ciftitocifti_30TRs.dscalar.nii'.format(subid, struct))
result_type = 'cifti'
result_prefix = '{}_{}_ciftitocifti_30TRs'.format(subid, struct)

TR_file = os.path.join(new_outputs, 'rois','TR_file.txt')
with open(TR_file, "w") as text_file:
    text_file.write('''1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30''')

run(['ciftify_seed_corr',
     '--outputname', result_map,
     '--use-TRs', TR_file,
     func_cifti_smoothed, putamen_vol_seed_mask])
run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[88]:


result_map = os.path.join(seed_corr_dir, '{}_{}_ciftitocifti_masked.dscalar.nii'.format(subid, struct))
result_type = 'cifti'
result_prefix = '{}_{}_ciftitocifti_masked'.format(subid, struct)

run(['ciftify_seed_corr',
     '--outputname', result_map,
     '--mask', cifti_mask,
     func_cifti_smoothed,
    os.path.join(seed_corr_dir, '{}_{}_cifti.dscalar.nii'.format(subid, struct))])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[89]:


result_map = seed_corr_default_out(func_cifti_smoothed, os.path.join(new_outputs, 'rois', 'gaussian_roi.dscalar.nii'))
result_type = 'cifti'
result_prefix = '{}_gaussian_ciftitocifti_unmasked'.format(subid)


run(['ciftify_seed_corr', '--weighted', func_cifti_smoothed,
     os.path.join(new_outputs, 'rois', 'gaussian_roi.dscalar.nii')])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[90]:


result_map = os.path.join(seed_corr_dir, '{}_gaussian_ciftitocifti_masked.dscalar.nii'.format(subid))
result_type = 'cifti'
result_prefix = '{}_gaussian_ciftitocifti_masked'.format(subid)

run(['ciftify_seed_corr', '--weighted',
     '--outputname', result_map,
     '--mask', cifti_mask,
     func_cifti_smoothed,
     os.path.join(new_outputs, 'rois', 'gaussian_roi.dscalar.nii')])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[91]:


L_gaussian_roi = os.path.join(new_outputs, 'rois', 'gaussian_L_roi.shape.gii')

result_map = seed_corr_default_out(func_cifti_smoothed, L_gaussian_roi)
result_type = 'cifti'
result_prefix = '{}_gaussian_giftitocifti_unmasked'.format(subid)


run(['wb_command', '-cifti-separate',
     os.path.join(new_outputs, 'rois', 'gaussian_roi.dscalar.nii'),
     'COLUMN','-metric', 'CORTEX_LEFT', L_gaussian_roi])
run(['ciftify_seed_corr', '--weighted', '--hemi', 'L',
     func_cifti_smoothed,
     L_gaussian_roi])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[92]:


result_map = os.path.join(seed_corr_dir, '{}_gaussian_giftitocifti_masked.dscalar.nii'.format(subid))
result_type = 'cifti'
result_prefix = '{}_gaussian_giftitocifti_masked'.format(subid)

run(['ciftify_seed_corr', '--weighted', '--hemi', 'L',
     '--outputname', result_map,
     '--mask', cifti_mask,
     func_cifti_smoothed,
     L_gaussian_roi])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[93]:


result_map = seed_corr_default_out(func_cifti_smoothed, os.path.join(new_outputs, 'rois', 'probmap_roi.dscalar.nii'))
result_type = 'cifti'
result_prefix = '{}_promap_ciftitocifti_unmasked.dscalar.nii'.format(subid)

run(['ciftify_seed_corr', '--weighted', func_cifti_smoothed,
     os.path.join(new_outputs, 'rois', 'probmap_roi.dscalar.nii')])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[94]:


result_map = os.path.join(seed_corr_dir, '{}_probmap_ciftitocifti_masked.dscalar.nii'.format(subid))
result_type = 'cifti'
result_prefix = '{}_probmap_ciftitocifti_masked'.format(subid)

run(['ciftify_seed_corr', '--weighted',
     '--outputname', result_map,
     '--mask', cifti_mask,
     func_cifti_smoothed,
     os.path.join(new_outputs, 'rois', 'probmap_roi.dscalar.nii')])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[95]:


R_probmap_roi = os.path.join(new_outputs, 'rois', 'probmap_R_roi.shape.gii')
result_map = seed_corr_default_out(func_cifti_smoothed, R_probmap_roi)
result_type = 'cifti'
result_prefix = '{}_promap_giftitocifti_unmasked.dscalar.nii'.format(subid)

run(['wb_command', '-cifti-separate',
     os.path.join(new_outputs, 'rois', 'probmap_roi.dscalar.nii'),
     'COLUMN','-metric', 'CORTEX_RIGHT', R_probmap_roi])
run(['ciftify_seed_corr', '--weighted', '--hemi', 'R', func_cifti_smoothed,
     R_probmap_roi])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[96]:


result_map = os.path.join(seed_corr_dir, '{}_probmap_giftitocifti_masked.dscalar.nii'.format(subid))
result_type = 'cifti'
result_prefix = '{}_probmap_giftitocifti_masked'.format(subid)

run(['ciftify_seed_corr', '--weighted', '--hemi', 'R',
     '--outputname', result_map,
     '--mask', cifti_mask,
     func_cifti_smoothed,
     R_probmap_roi])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[97]:


result_map = seed_corr_default_out(func_cifti_smoothed, os.path.join(new_outputs, 'rois', 'tvertex.dscalar.nii'))
result_type = 'cifti'
result_prefix = '{}_tvertex7_ciftitocifti_unmasked'.format(subid)

run(['ciftify_seed_corr', '--roi-label', '7', func_cifti_smoothed,
     os.path.join(new_outputs, 'rois', 'tvertex.dscalar.nii')])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[98]:


result_map = os.path.join(seed_corr_dir, '{}_tvertex7_ciftitocifti_masked.dscalar.nii'.format(subid))
result_type = 'cifti'
result_prefix = '{}_tvertex7_ciftitocifti_masked'.format(subid)

run(['ciftify_seed_corr', '--roi-label', '7',
     '--outputname', result_map,
     '--mask', cifti_mask,
     func_cifti_smoothed,
     os.path.join(new_outputs, 'rois', 'tvertex.dscalar.nii')])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[99]:


R_tvertex_roi = os.path.join(new_outputs, 'rois', 'tvertex_R_roi.shape.gii')
result_map = seed_corr_default_out(func_cifti_smoothed, R_tvertex_roi)
result_type = 'cifti'
result_prefix = '{}_tvertex7_giftitocifti_umasked'.format(subid)


run(['wb_command', '-cifti-separate',
     os.path.join(new_outputs, 'rois', 'tvertex.dscalar.nii'),
     'COLUMN','-metric', 'CORTEX_RIGHT', R_tvertex_roi])
run(['ciftify_seed_corr', '--roi-label', '7', '--hemi', 'R',
     func_cifti_smoothed, R_tvertex_roi])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[100]:


result_map = os.path.join(seed_corr_dir, '{}_tvertex7_giftitocifti_masked.dscalar.nii'.format(subid))
result_type = 'cifti'
result_prefix = '{}_tvertex7_giftitocifti_masked'.format(subid)

run(['ciftify_seed_corr', '--roi-label', '7', '--hemi', 'R',
     '--outputname', result_map,
     '--mask', cifti_mask,
     func_cifti_smoothed, R_tvertex_roi])

run_vis_map(result_map, result_prefix, result_type)
run_seedcorr_peaktable(result_map)


# In[101]:


run(['cifti_vis_map', 'index', '--hcp-data-dir', hcp_data_dir])

logger.info(ciftify.utils.section_header('ciftify_meants (atlas examples)'))
# # ciftify_meants (atlas examples)

# In[102]:


subject_aparc = os.path.join(hcp_data_dir, subid,
                            'MNINonLinear', 'fsaverage_LR32k',
                            '{}.aparc.32k_fs_LR.dlabel.nii'.format(subid))
subject_thickness = os.path.join(hcp_data_dir, subid,
                            'MNINonLinear', 'fsaverage_LR32k',
                            '{}.thickness.32k_fs_LR.dscalar.nii'.format(subid))
run(['ciftify_meants', func_cifti_sm0, subject_aparc])


# In[112]:


run(['ciftify_meants',
     '--outputcsv', os.path.join(seed_corr_dir,
                                 '{}_aparc_thickness_ciftitocifti_unmasked_meants.csv'.format(subid)),
     '--outputlabels', os.path.join(seed_corr_dir,
                                    '{}_aparc_ciftitocifti_unmasked_labels.csv'.format(subid)),
         subject_thickness, subject_aparc])


# In[104]:


run(['ciftify_meants', func_cifti_sm0,
     os.path.join(new_outputs, 'rois', 'tvertex.dscalar.nii')])


# In[105]:


run(['ciftify_meants',
     '--mask', cifti_mask,
     '--outputcsv', os.path.join(seed_corr_dir,
                                 '{}_tvertex_func_ciftitocifti_unmasked_meants.csv'.format(subid)),
     func_cifti_sm0,
     os.path.join(new_outputs, 'rois', 'tvertex.dscalar.nii')])


# In[106]:


## project wmparc to subject
wmparc_dscalar_d0 = os.path.join(seed_corr_dir, '{}_wmparc_MNI_d0.dscalar.nii'.format(subid))
run(['ciftify_vol_result', '--hcp-data-dir', hcp_data_dir,
    '--integer-labels', subid, atlas_vol, wmparc_dscalar_d0])


# In[107]:


## project wmparc to subject
wmparc_dscalar = os.path.join(seed_corr_dir, '{}_wmparc_MNI_d10.dscalar.nii'.format(subid))
run(['ciftify_vol_result',
     '--hcp-data-dir', hcp_data_dir,
     '--dilate', '10',
    '--integer-labels', subid, atlas_vol, wmparc_dscalar])


# In[115]:


run(['ciftify_meants',
     '--mask', os.path.join(hcp_data_dir, subid, 'MNINonLinear', 'brainmask_fs.nii.gz'),
     '--outputcsv', os.path.join(seed_corr_dir,
                                 '{}_wmparc_func_niftitonifti_masked_meants.csv'.format(subid)),
     '--outputlabels', os.path.join(seed_corr_dir,
                                 '{}_wmparc_func_niftitonifti_masked_labels.csv'.format(subid)),
     func_vol, atlas_vol])


# In[114]:


run(['ciftify_meants',
     '--mask', cifti_mask,
     '--outputcsv', os.path.join(seed_corr_dir,
                                 '{}_wmparc_func_ciftitocifti_masked_meants.csv'.format(subid)),
     '--outputlabels', os.path.join(seed_corr_dir,
                                 '{}_wmparc_func_ciftitocifti_masked_labels.csv'.format(subid)),
     func_cifti_sm0, wmparc_dscalar])


# In[113]:


wmparc_dlabel = os.path.join(seed_corr_dir, '{}_wmparc_MNI.dlabel.nii'.format(subid))
run(['wb_command', '-cifti-label-import', '-logging', 'SEVERE',
     wmparc_dscalar,
     os.path.join(ciftify.config.find_ciftify_global(), 'hcp_config', 'FreeSurferAllLut.txt'),
    wmparc_dlabel])
run(['ciftify_meants',
     '--outputcsv', os.path.join(seed_corr_dir,
                                 '{}_wmparc_func_ciftiltocifti_dlabel_meants.csv'.format(subid)),
     '--outputlabels', os.path.join(seed_corr_dir,
                                 '{}_wmparc_func_ciftiltocifti_dlabel_labels.csv'.format(subid)),
     func_cifti_sm0, wmparc_dlabel])


# In[128]:

logger.info(ciftify.utils.section_header('Testing csv outputs'))


fixtures_dir = os.path.join(os.path.dirname(os.path.dirname(ciftify.config.find_ciftify_global())),
                                  'tests','integration','fixtures')
csv_df = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(ciftify.config.find_ciftify_global())),
                                  'tests','integration','expected_csvs.csv'))
csv_df['num_rows'] = ''
csv_df['num_cols'] = ''
csv_df['exists'] = ''
csv_df['matches'] = ''


# In[129]:


for row in csv_df.index:
    expected_csv = os.path.join(new_outputs, csv_df.loc[row, 'expected_output'])
    if os.path.isfile(expected_csv):
        compare_csv = os.path.join(fixtures_dir, csv_df.loc[row, 'compare_to'])
        header_col = 0
        if expected_csv.endswith('_meants.csv'): header_col = None
        if expected_csv.endswith('_labels.csv'): header_col = None
        if expected_csv.endswith('_CSF.csv'): header_col = None
        if expected_csv.endswith('_WM.csv'): header_col = None
        if expected_csv.endswith('_GM.csv'): header_col = None
        testdf = pd.read_csv(expected_csv, header = header_col)
        csv_df.loc[row, 'exists'] = True
        csv_df.loc[row, 'num_rows'] = testdf.shape[0]
        csv_df.loc[row, 'num_cols'] = testdf.shape[1]
        comparedf = pd.read_csv(compare_csv, header = header_col)
        try:
            csv_df.loc[row, 'matches'] = (comparedf == testdf).all().all()
        except:
            csv_df.loc[row, 'matches'] = False
    else:
        csv_df.loc[row, 'exists'] = False


# In[131]:


csv_df.to_csv(os.path.join(new_outputs, 'csv_compare_results.csv'))


# In[134]:


if csv_df.exists.all():
    logger.info('All expected csv were generated')
else:
    logger.error('Some expected csv outputs were not generated')


# In[135]:


if csv_df.matches.all():
    logger.info('All expected csv outputs match expected')
else:
    logger.info('Some csv outputs do not match..see csv_compare_results.csv of more details')


# In[136]:


logger.info(ciftify.utils.section_header('Done'))


# In[ ]:
