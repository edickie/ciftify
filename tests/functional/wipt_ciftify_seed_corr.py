#!/usr/bin/env python3
import os
import unittest
import logging
import shutil
import tempfile
import ciftify.config
from ciftify.utils import run

from pytest import raises
from unittest.mock import patch

def get_test_data_path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

test_dtseries = os.path.join(get_test_data_path(),
        'sub-50005_task-rest_Atlas_s0.dtseries.nii')
test_nifti = os.path.join(get_test_data_path(),
        'sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz')
left_surface = os.path.join(get_test_data_path(),
        'sub-50005.L.midthickness.32k_fs_LR.surf.gii')
right_surface = os.path.join(get_test_data_path(),
        'sub-50005.R.midthickness.32k_fs_LR.surf.gii')
custom_dlabel = os.path.join(get_test_data_path(),
                             'rois',
                             'rois_for_tests.dlabel.nii')

weighted_dscalar = os.path.join(get_test_data_path(),
                             'rois',
                        'weighted_test_roi.dscalar.nii')
                          
# ciftify_meants <nifti_func> <nifti_seed>
# ciftify_meants <cifti_func> <cifti_seed> (cifti_seed - subcortical)
  # results of a and b should match (as long as the nifti came from them cifti)
                            
# ciftify_meants <cifti_func> <cifti_seed> (cifti_seed - cortical)
# ciftify_meants <cifti_func> <gifti_seed> 
# ciftify_meants <gifti_func> <gifti_seed>
  # results of a, b, and c should match
                            
# ciftify_meants (weighted)
# ciftify_meants (with a label)
# ciftify_meants (with multiple entries) - dlabel (no labels)
# ciftify_meants (with multiple entries) - dlabel (w labels)
# ciftify_meants (with multiple entries) - dscalar (no labels)
# ciftify_meants (with multiple entries) - dscalar (w labels) 
# ciftify_meants (with mask)
                            
# ciftify_seedcorr with a TR drop                            
#   TR_file = os.path.join(new_outputs, 'rois','TR_file.txt')
# with open(TR_file, "w") as text_file:
#     text_file.write('''1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30''')                          
# ciftify_seedcorr with mask                            
# ciftify seedcorr with cifti_output
# ciftify_seedcorr with cifti out w mask
# ciftify_seedcorr with nifti_output
# ciftify_seedcorr with nifti_output w mask
# ciftify_seedcorr with with fisher-z
                          
@pytest.fixture(scope = "module")
def left_hemisphere_mask():
    '''build a cleaned and smoothed dtseries file that multiple tests use as input'''
    with ciftify.utils.TempDir() as mask_dir:
        left_mask = os.path.join(mask_dir, 'mask.L.shape.gii')
        run(['wb_command', '-cifti-separate',
            custom_dlabel, 'COLUMN',
            '-label', 'CORTEX_LEFT', os.path.join(mask_dir, 'tmp.L.label.gii'),
            '-roi', left_mask])
        yield left_mask
        
@pytest.fixture(scope = "module")
def subcort_mask():
    '''build a cleaned and smoothed dtseries file that multiple tests use as input'''
    with ciftify.utils.TempDir() as mask_dir:
        subcort_mask = os.path.join(mask_dir, 'subcort_mask.nii.gz')
        run(['wb_command', '-cifti-separate',
            custom_dlabel, 'COLUMN',
            '-volume-all', os.path.join(mask_dir, 'tmp.nii.gz'),
            '-roi', subcort_mask])
        yield left_mask
    
    
def test_ciftify_seedcorr_with_cifti_output_no_mask(output_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.dscalar.nii')
    run(['ciftify_seed_corr', 
         '--weighted', 
         test_dtseries, 
         weighted_dscalar])
    assert os.path.isfile(seedcorr_output)
    
def test_ciftify_seedcorr_cifti_output_with_mask(output_dir, left_hemisphere_mask):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.dscalar.nii')
    run(['ciftify_seed_corr', 
         '--weighted', 
         '--mask', left_hemisphere_mask,
         test_dtseries, 
         weighted_dscalar])
    assert os.path.isfile(seedcorr_output)
    
def test_ciftify_seedcorr_nifti_output_no_mask(output_dir):
    assert False
    
def test_ciftify_seedcorr_nifti_output_with_mask(output_dir):
    assert False
    
def test_ciftify_seedcorr_cifti_output_with_fisher-z(output_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.dscalar.nii')
    run(['ciftify_seed_corr', 
         '--weighted', '--fisher-z',
         test_dtseries, 
         weighted_dscalar])
    assert os.path.isfile(seedcorr_output)
    
def test_ciftify_seedcorr_cifti_output_with_TRfile(output_dir):
    TR_file = os.path.join(new_outputs, 'rois','TR_file.txt')
    with open(TR_file, "w") as text_file:
        text_file.write('''1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30''') 
    run(['ciftify_seed_corr', 
         '--use-TRs', TR_file,
         test_dtseries, 
         weighted_dscalar])
    assert os.path.isfile(seedcorr_output)
    
