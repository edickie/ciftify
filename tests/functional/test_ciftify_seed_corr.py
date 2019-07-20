#!/usr/bin/env python3
import os
import unittest
import logging
import shutil
import tempfile
import ciftify.config
from ciftify.utils import run
import pytest
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
                            
                          
@pytest.fixture(scope = "function")
def output_dir():
    with ciftify.utils.TempDir() as outputdir:
        yield outputdir
                          
@pytest.fixture(scope = "module")
def left_hemisphere_dir():
    '''build a cleaned and smoothed dtseries file that multiple tests use as input'''
    with ciftify.utils.TempDir() as mask_dir:
        left_mask = os.path.join(mask_dir, 'mask.L.shape.gii')
        left_mask_dscalar = os.path.join(mask_dir, 'mask_L.dscalar.nii')
        left_rois = os.path.join(mask_dir, 'rois.L.label.gii')
        left_func = os.path.join(mask_dir, 'func.L.func.gii')
        run(['wb_command', '-cifti-separate',
            custom_dlabel, 'COLUMN',
            '-label', 'CORTEX_LEFT', left_rois,
            '-roi', left_mask])
        run(['wb_command', '-cifti-separate',
            test_dtseries, 'COLUMN',
            '-metric', 'CORTEX_LEFT', left_func])
        run(['wb_command', '-cifti-create-dense-from-template', 
             test_dtseries, left_mask_dscalar, 
             '-metric', 'CORTEX_LEFT', left_mask])
        yield mask_dir
        
@pytest.fixture(scope = "module")
def subcort_images_dir():
    '''create the '''
    with ciftify.utils.TempDir() as subcort_images_dir:
        subcort_mask = os.path.join(subcort_images_dir, 'mask.nii.gz')
        subcort_rois = os.path.join(subcort_images_dir, 'rois.nii.gz')
        subcort_func = os.path.join(subcort_images_dir, 'func.nii.gz')
        run(['wb_command', '-cifti-separate',
            custom_dlabel, 'COLUMN',
            '-volume-all', subcort_rois,
            '-roi', subcort_mask])
        run(['wb_command', '-cifti-separate',
            test_dtseries, 'COLUMN',
            '-volume-all', subcort_func])
        yield subcort_images_dir 
        
def get_the_5_rois_meants_outputs(input_file):
    run(['ciftify_meants'])
    
def test_ciftify_seedcorr_with_cifti_output_no_mask(output_dir, left_hemisphere_dir):
    new_test_dtseries = os.path.join(output_dir, 'sub-xx_test.dtseries.nii')
    run(['cp', test_dtseries, new_test_dtseries])
    seedcorr_output = os.path.join(output_dir,
                                  'sub-xx_test_weighted_test_roi.dscalar.nii')
    run(['ciftify_seed_corr', '--debug',
         '--weighted',
         '--mask', os.path.join(left_hemisphere_dir, 'mask_L.dscalar.nii'),
         new_test_dtseries, 
         weighted_dscalar])
    
    assert os.path.isfile(seedcorr_output)
    
def test_ciftify_seedcorr_cifti_output_with_mask(output_dir, left_hemisphere_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.dscalar.nii')
    run(['ciftify_seed_corr', '--debug',
         '--outputname', seedcorr_output,
         '--weighted', 
         '--mask', os.path.join(left_hemisphere_dir, 'mask_L.dscalar.nii'),
         test_dtseries, 
         weighted_dscalar])
    assert os.path.isfile(seedcorr_output)
    
def test_ciftify_seedcorr_nifti_output_no_mask(output_dir, subcort_images_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.nii.gz')
    run(['ciftify_seed_corr', 
         '--roi-label 4', 
         '--outputname', seedcorr_output,
         os.path.join(subcort_images_dir, 'func.nii.gz'), 
         os.path.join(subcort_images_dir, 'rois.nii.gz')])
    assert os.path.isfile(seedcorr_output)
    
def test_ciftify_seedcorr_nifti_output_with_mask(output_dir, subcort_images_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.nii.gz')
    run(['ciftify_seed_corr', 
         '--roi-label 4',
         '--outputname', seedcorr_output,
         '--mask', os.path.join(subcort_images_dir, 'mask.nii.gz'),
         os.path.join(subcort_images_dir, 'func.nii.gz'), 
         os.path.join(subcort_images_dir, 'rois.nii.gz')])
    assert os.path.isfile(seedcorr_output)
    
def test_ciftify_seedcorr_cifti_output_with_fisherz(output_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.dscalar.nii')
    meants_output = os.path.join(output_dir,
                                  'seedcorr_meants.csv')
    run(['ciftify_seed_corr', '--debug',
         '--weighted', '--fisher-z',
         '--outputname', seedcorr_output,
         '--output-ts',
         test_dtseries, 
         weighted_dscalar])
    assert os.path.isfile(seedcorr_output)
    assert os.path.isfile(meants_output)
    
def test_ciftify_seedcorr_cifti_output_with_TRfile(output_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.dscalar.nii')
    TR_file = os.path.join(output_dir, 'TR_file.txt')
    with open(TR_file, "w") as text_file:
        text_file.write('''1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30''') 
    run(['ciftify_seed_corr', 
         '--outputname', seedcorr_output,
         '--use-TRs', TR_file,
         '--weighted',
         test_dtseries, 
         weighted_dscalar])
    assert os.path.isfile(seedcorr_output)
    