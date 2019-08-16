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
import pandas as pd
import numpy as np

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

custom_dlabel_meants = os.path.join(get_test_data_path(),
                             'rois',
                             'sub-50005_task-rest_Atlas_s0_rois_for_tests_meants.csv')




# ciftify_meants (weighted)
# ciftify_meants (with a label)
# ciftify_meants (with multiple entries) - dlabel (no labels)
# ciftify_meants (with multiple entries) - dlabel (w labels)
# ciftify_meants (with multiple entries) - dscalar (no labels)
# ciftify_meants (with multiple entries) - dscalar (w labels)
# ciftify_meants (with mask)

# known correlations with the seed
# 0  0.087475
# 1  0.488206
# 2  0.049888
# 3  0.187913
# 4  0.078139

@pytest.fixture(scope = "function")
def output_dir():
    with ciftify.utils.TempDir() as outputdir:
        yield outputdir

@pytest.fixture(scope = "module")
def left_hemisphere_dir():
    '''build a cleaned and smoothed dtseries file that multiple tests use as input'''
    with ciftify.utils.TempDir() as mask_dir:
        left_mask_gii = os.path.join(mask_dir, 'mask.L.shape.gii')
        left_mask_dscalar = os.path.join(mask_dir, 'mask_L.dscalar.nii')
        left_roi_dscalar = os.path.join(mask_dir, 'roi_L.dscalar.nii')
        left_roi_gii = os.path.join(mask_dir, 'roi.L.shape.gii')
        left_func = os.path.join(mask_dir, 'func.L.func.gii')
        run(['wb_command', '-cifti-label-to-roi',
            custom_dlabel, left_roi_dscalar,
            '-key 1 -map 1'])
        run(['wb_command', '-cifti-separate',
            left_roi_dscalar, 'COLUMN',
            '-metric', 'CORTEX_LEFT', left_roi_gii,
            '-roi', left_mask_gii])
        run(['wb_command', '-cifti-separate',
            test_dtseries, 'COLUMN',
            '-metric', 'CORTEX_LEFT', left_func])
        run(['wb_command', '-cifti-create-dense-from-template',
             test_dtseries, left_mask_dscalar,
             '-metric', 'CORTEX_LEFT', left_mask_gii])
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

def read_meants_and_transpose(meants_csv):
    return pd.read_csv(meants_csv, header = None).transpose()

def get_the_5_rois_meants_outputs(input_file, tmpdir, seed_dscalar):
    meants_csv = os.path.join(tmpdir, 'mts.csv')
    meants_labels = os.path.join(tmpdir, 'labels.csv')
    run(['ciftify_meants',
         '--outputcsv', meants_csv,
         '--outputlabels', meants_labels,
         input_file, seed_dscalar])
    meants_pd = pd.read_csv(meants_csv, header = None)
    labels_pd = pd.read_csv(meants_labels)
    return meants_pd, labels_pd

@pytest.fixture(scope = "module")
def custom_dlabel_timeseries():
    meants_pd = read_meants_and_transpose(custom_dlabel_meants)
    yield meants_pd

# ciftify_meants <cifti_func> <cifti_seed> (cifti_seed - cortical)
# ciftify_meants <cifti_func> <gifti_seed>
# ciftify_meants <gifti_func> <gifti_seed>
  # results of a, b, and c should match

def test_ciftify_meants_cifti_func_custom_dlabel_left_gii(output_dir, custom_dlabel_timeseries, left_hemisphere_dir):
    meants_out = os.path.join(output_dir, 'meants.csv')
    run(['ciftify_meants',
         '--hemi L',
         '--outputcsv', meants_out,
         test_dtseries,
         os.path.join(left_hemisphere_dir, 'roi.L.shape.gii')])
    assert os.path.isfile(meants_out)
    meants_pd_out = read_meants_and_transpose(meants_out).loc[:,0]
    expected_pd = custom_dlabel_timeseries.loc[:,0]
    assert np.allclose(meants_pd_out.values, expected_pd.values, atol = 0.01)

def test_ciftify_meants_gii_func_custom_dlabel_left_gii(output_dir, custom_dlabel_timeseries, left_hemisphere_dir):
    meants_out = os.path.join(output_dir, 'meants.csv')
    run(['ciftify_meants', '--debug',
         '--outputcsv', meants_out,
         '--hemi L',
         os.path.join(left_hemisphere_dir, 'func.L.func.gii'),
         os.path.join(left_hemisphere_dir, 'roi.L.shape.gii')])
    assert os.path.isfile(meants_out)
    meants_pd_out = read_meants_and_transpose(meants_out).loc[:,0]
    expected_pd = custom_dlabel_timeseries.loc[:,0]
    assert np.allclose(meants_pd_out.values, expected_pd.values, atol = 0.01)

# ciftify_meants <nifti_func> <nifti_seed>
# ciftify_meants <cifti_func> <cifti_seed> (cifti_seed - subcortical)
  # results of a and b should match (as long as the nifti came from them cifti)

def test_ciftify_meants_cifti_func_custom_dlabel(output_dir, custom_dlabel_timeseries):
    meants_out = os.path.join(output_dir, 'meants.csv')
    run(['ciftify_meants',
         '--outputcsv', meants_out,
         test_dtseries, custom_dlabel])
    assert os.path.isfile(meants_out)
    meants_pd_out = read_meants_and_transpose(meants_out)
    results_cormat = meants_pd_out.corr().values
    print(results_cormat)
    expected_cormat = custom_dlabel_timeseries.corr().values
    print(expected_cormat)
    assert np.allclose(results_cormat, expected_cormat, atol = 0.001)
    assert np.allclose(meants_pd_out, custom_dlabel_timeseries, atol = 0.001)
    
def test_ciftify_meants_cifti_func_custom_dlabel_some_missing(output_dir, custom_dlabel_timeseries, left_hemisphere_dir, subcort_images_dir):
    ''' set to make sure that the correct number of ROIs are extracted if the data is missing'''
    ## build a cifti file with only one hemisphere of data
    one_hemi_func = os.path.join(output_dir, 'func_L_hemi.dtseries.nii')
    run(['wb_command', '-cifti-create-dense-timeseries',
             one_hemi_func,
             '-left-metric', os.path.join(left_hemisphere_dir, 'func.L.func.gii'),
        '-volume',  
        os.path.join(subcort_images_dir, 'func.nii.gz'),
        os.path.join(ciftify.config.find_ciftify_global(),'standard_mesh_atlases','Atlas_ROIs.2.nii.gz')])
    meants_out = os.path.join(output_dir, 'meants.csv')
    labels_out = os.path.join(output_dir, 'labels.csv')
    run(['ciftify_meants',
         '--outputcsv', meants_out,
         '--outputlabels',labels_out,
         one_hemi_func, custom_dlabel])
    assert os.path.isfile(meants_out)
    assert os.path.isfile(labels_out)
    meants_pd_out = read_meants_and_transpose(meants_out)
    meants_labels = pd.read_csv(labels_out)
    assert meants_pd_out.shape[1] == meants_labels.shape[0]
    print(meants_pd_out)
    print(meants_labels)
    assert np.allclose(meants_pd_out.loc[:,0].values, custom_dlabel_timeseries.loc[:,0].values, atol = 0.001)
    assert np.allclose(meants_pd_out.loc[:,1:2].values, np.zeros((meants_pd_out.shape[0],2)), atol = 0.001)


def test_ciftify_meants_cifti_func_custom_dlabel_subcort(output_dir, custom_dlabel_timeseries, subcort_images_dir):
    meants_out = os.path.join(output_dir, 'meants.csv')
    run(['ciftify_meants',
         '--outputcsv', meants_out,
         test_dtseries,
         os.path.join(subcort_images_dir, 'rois.nii.gz')])
    assert os.path.isfile(meants_out)
    meants_pd_out = read_meants_and_transpose(meants_out)
    expected_pd = custom_dlabel_timeseries.loc[:,3:4]
    corr_test = meants_pd_out.corr().values
    corr_expected = expected_pd.corr().values
    assert np.allclose(corr_test[0,1], corr_expected[0,1], atol = 0.001)
    assert np.allclose(meants_pd_out.values, expected_pd.values, atol = 0.001)

def test_ciftify_meants_nifti_func_custom_dlabel_subcort(output_dir, custom_dlabel_timeseries, subcort_images_dir):
    meants_out = os.path.join(output_dir, 'meants.csv')
    run(['ciftify_meants',
         '--outputcsv', meants_out,
         os.path.join(subcort_images_dir, 'func.nii.gz'),
         os.path.join(subcort_images_dir, 'rois.nii.gz')])
    assert os.path.isfile(meants_out)
    meants_pd_out = read_meants_and_transpose(meants_out)
    expected_pd = custom_dlabel_timeseries.loc[:,3:4]
    corr_test = meants_pd_out.corr().values
    corr_expected = expected_pd.corr().values
    assert np.allclose(corr_test[0,1], corr_expected[0,1], atol = 0.001)
    assert np.allclose(meants_pd_out.values, expected_pd.values, atol = 0.001)

def test_ciftify_meants_nifti_func_custom_dlabel_subcort_one_label(output_dir, custom_dlabel_timeseries, subcort_images_dir):
    meants_out = os.path.join(output_dir, 'meants.csv')
    run(['ciftify_meants',
         '--outputcsv', meants_out,
         '--roi-label 4',
         os.path.join(subcort_images_dir, 'func.nii.gz'),
         os.path.join(subcort_images_dir, 'rois.nii.gz')])
    assert os.path.isfile(meants_out)
    meants_pd_out = read_meants_and_transpose(meants_out).loc[:,0]
    expected_pd = custom_dlabel_timeseries.loc[:,3]
    assert np.allclose(meants_pd_out.values, expected_pd.values, atol = 0.001)

def test_ciftify_seedcorr_with_cifti_output_no_mask(output_dir, left_hemisphere_dir):
    new_test_dtseries = os.path.join(output_dir, 'sub-xx_test.dtseries.nii')
    run(['cp', test_dtseries, new_test_dtseries])
    seedcorr_output = os.path.join(output_dir,
                                  'sub-xx_test_weighted_test_roi.dscalar.nii')
    run(['ciftify_seed_corr', '--debug',
         '--weighted',
         new_test_dtseries,
         weighted_dscalar])
    meants5, labels5 = get_the_5_rois_meants_outputs(seedcorr_output, output_dir, custom_dlabel)
    assert os.path.isfile(seedcorr_output)
    assert pytest.approx(meants5.loc[0,0], 0.001) == 0.0875
    assert pytest.approx(meants5.loc[1,0], 0.001) == 0.488
    assert pytest.approx(meants5.loc[3,0], 0.001) == 0.1879

def test_ciftify_seedcorr_cifti_output_with_mask(output_dir, left_hemisphere_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.dscalar.nii')
    run(['ciftify_seed_corr', '--debug',
         '--outputname', seedcorr_output,
         '--weighted',
         '--mask', os.path.join(left_hemisphere_dir, 'mask_L.dscalar.nii'),
         test_dtseries,
         weighted_dscalar])
    meants5, labels5 = get_the_5_rois_meants_outputs(seedcorr_output, output_dir, custom_dlabel)
    assert os.path.isfile(seedcorr_output)
    print(meants5)
    print(labels5)
    assert pytest.approx(meants5.loc[0,0], 0.001) == 0.0875
    assert pytest.approx(meants5.loc[1,0], 0.001) == 0
    assert pytest.approx(meants5.loc[3,0], 0.001) == 0

def test_ciftify_seedcorr_cifti_output_nifti_seed(output_dir, subcort_images_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.dscalar.nii')
    run(['ciftify_seed_corr',
         '--debug',
         '--roi-label 4',
         '--outputname', seedcorr_output,
         test_dtseries,
         os.path.join(subcort_images_dir, 'rois.nii.gz')])
    meants5, labels5 = get_the_5_rois_meants_outputs(
        seedcorr_output, output_dir, custom_dlabel)
    print(meants5)
    print(labels5)
    assert os.path.isfile(seedcorr_output)
    assert pytest.approx(meants5.loc[0,0], 0.001) == 0.1256
    assert pytest.approx(meants5.loc[1,0], 0.001) == 0.3094
    assert pytest.approx(meants5.loc[3,0], 0.001) == 0.3237
    assert pytest.approx(meants5.loc[4,0], 0.001) == 0.1458

def test_ciftify_seedcorr_nifti_output_no_mask(output_dir, subcort_images_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.nii.gz')
    run(['ciftify_seed_corr',
         '--roi-label 4',
         '--outputname', seedcorr_output,
         os.path.join(subcort_images_dir, 'func.nii.gz'),
         os.path.join(subcort_images_dir, 'rois.nii.gz')])
    meants5, labels5 = get_the_5_rois_meants_outputs(seedcorr_output, output_dir, os.path.join(subcort_images_dir, 'rois.nii.gz'))
    print(meants5)
    print(labels5)
    assert os.path.isfile(seedcorr_output)
    assert pytest.approx(meants5.loc[0,0], 0.001) == 0.3237
    assert pytest.approx(meants5.loc[1,0], 0.001) == 0.1458

def test_ciftify_seedcorr_nifti_output_with_mask(output_dir, subcort_images_dir):
    seedcorr_output = os.path.join(output_dir,
                                  'seedcorr.nii.gz')
    run(['ciftify_seed_corr',
         '--roi-label 4',
         '--outputname', seedcorr_output,
         '--mask', os.path.join(subcort_images_dir, 'mask.nii.gz'),
         os.path.join(subcort_images_dir, 'func.nii.gz'),
         os.path.join(subcort_images_dir, 'rois.nii.gz')])
    meants5, labels5 = get_the_5_rois_meants_outputs(seedcorr_output, output_dir, os.path.join(subcort_images_dir, 'rois.nii.gz'))
    print(meants5)
    assert os.path.isfile(seedcorr_output)
    assert pytest.approx(meants5.loc[0,0], 0.001) == 0.3237
    assert pytest.approx(meants5.loc[1,0], 0.001) == 0.1458

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
    meants5, labels5 = get_the_5_rois_meants_outputs(
        seedcorr_output, output_dir, custom_dlabel)
    assert pytest.approx(meants5.loc[0,0], 0.001) == 0.0894
    assert pytest.approx(meants5.loc[1,0], 0.001) == 0.547
    assert pytest.approx(meants5.loc[3,0], 0.001) == 0.194

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
    meants5, labels5 = get_the_5_rois_meants_outputs(
        seedcorr_output, output_dir, custom_dlabel)
    assert pytest.approx(meants5.loc[0,0], 0.001) == 0.0929
    assert pytest.approx(meants5.loc[1,0], 0.001) == 0.482
    assert pytest.approx(meants5.loc[3,0], 0.001) == 0.220
