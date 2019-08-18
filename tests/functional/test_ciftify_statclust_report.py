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


@pytest.fixture(scope = "function")
def output_dir():
    with ciftify.utils.TempDir() as outputdir:
        yield outputdir

def test_regress_report_from_weighted(output_dir):
    ''' just get the report from the weigthed roi '''
    output_result = os.path.join(output_dir, 'weighted_statclust_report')
    run(['ciftify_statclust_report',
    '--max-threshold 0',
    '--outputbase', output_result,
     weighted_dscalar]
    )
    assert os.path.isfile('{}_statclust_report.csv'.format(output_result))
    assert os.path.isfile('{}_clust.dlabel.nii'.format(output_result))

def test_runs_with_custom_atlas_in_config(output_dir):
    '''will add Yeo17 or Gordon to the config and make sure results some out'''
    
    assert False

def test_regress_report_from_smoothed_custom_dlabel(output_dir):
    '''cifti smooth the dlabel file to make it have more bits'''
    dscalar_file = os.path.join(output_dir, 'custom5.dscalar.nii')
    dscalar_file_sm = os.path.join(output_dir, 'custom5_sm.dscalar.nii')
    dscalar_file_sm_neg = os.path.join(output_dir, 'custom5_smneg.dscalar.nii')
    run(['wb_command', '-cifti-change-mapping',
         custom_dlabel, 'ROW', dscalar_file, '-scalar'])
    run(['wb_command', '-cifti-smoothing', dscalar_file, 
         '4', '4','COLUMN', dscalar_file_sm, 
         '-left-surface', left_surface, 
         '-right-surface', right_surface])
    run(['wb_command', '-cifti-math "(x*-1)"', dscalar_file_sm_neg,
        '-var x', dscalar_file_sm])
    run(['ciftify_statclust_report', 
         '--max-threshold 0', '--min-threshold 0', 
        dscalar_file_sm])
    run(['ciftify_statclust_report', 
         '--max-threshold 0', '--min-threshold 0', 
        dscalar_file_smneg])
    assert False

def test_report_with_different_surfaces(output_dir): 
    assert False
