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
