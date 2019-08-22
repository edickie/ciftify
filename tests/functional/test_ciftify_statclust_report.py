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
import json

def get_test_data_path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

test_dtseries = os.path.join(get_test_data_path(),
        'sub-50005_task-rest_Atlas_s0.dtseries.nii')
test_nifti = os.path.join(get_test_data_path(),
        'sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz')
left_sub_surface = os.path.join(get_test_data_path(),
        'sub-50005.L.midthickness.32k_fs_LR.surf.gii')
right_sub_surface = os.path.join(get_test_data_path(),
        'sub-50005.R.midthickness.32k_fs_LR.surf.gii')
left_3k_surface = os.path.join(get_test_data_path(),
        'tpl-fsaverage_hemi-L_den-3k_pial.surf.gii')
right_3k_surface = os.path.join(get_test_data_path(),
        'tpl-fsaverage_hemi-R_den-3k_pial.surf.gii')
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
    custom_config = {
        "DKT": {
            "folder": "CIFTIFY_GLOBAL_HCPS1200",
            "filename": "cvs_avg35_inMNI152.aparc.32k_fs_LR.dlabel.nii",
            "order" : 2,
            "name": "DKT",
            "map_number": 1
        },
        "Yeo17": {
            "folder": ciftify.config.find_HCP_S1200_GroupAvg(),
            "filename": "RSN-networks.32k_fs_LR.dlabel.nii",
            "order" : 1,
            "name" : "Yeo17",
            "map_number": 2
        }
    }
    custom_config_json = os.path.join(output_dir, 'custom_config.json')
    with open(custom_config_json, 'w') as json_file:
        json.dump(custom_config, json_file)
    output_result = os.path.join(output_dir, 'weighted_statclust_report')
    run(['ciftify_statclust_report',
    '--max-threshold 0',
    '--atlas-config', custom_config_json,
    '--outputbase', output_result,
     weighted_dscalar]
    )
    assert os.path.isfile('{}_statclust_report.csv'.format(output_result))
    assert os.path.isfile('{}_clust.dlabel.nii'.format(output_result))
    # assert False

def test_regress_report_from_smoothed_custom_dlabel(output_dir):
    '''cifti smooth the dlabel file to make it have more bits'''
    dscalar_file = os.path.join(output_dir, 'custom5.dscalar.nii')
    dscalar_file_sm = os.path.join(output_dir, 'custom5_sm.dscalar.nii')
    dscalar_file_sm_neg = os.path.join(output_dir, 'custom5_smneg.dscalar.nii')
    run(['wb_command', '-cifti-change-mapping',
         custom_dlabel, 'ROW', dscalar_file, '-scalar'])
    run(['wb_command', '-cifti-smoothing', dscalar_file,
         '4', '4','COLUMN', dscalar_file_sm,
         '-left-surface', left_sub_surface,
         '-right-surface', right_sub_surface])
    run(['wb_command', '-cifti-math "(x*-1)"', dscalar_file_sm_neg,
        '-var x', dscalar_file_sm])
    run(['ciftify_statclust_report',
         '--max-threshold 0', '--min-threshold 0',
        dscalar_file_sm])
    run(['ciftify_statclust_report',
         '--max-threshold 0', '--min-threshold 0',
         '--no-cluster-dlabel',
        dscalar_file_sm_neg])
    assert os.path.isfile(os.path.join(output_dir, 'custom5_sm_statclust_report.csv'))
    assert os.path.isfile(os.path.join(output_dir, 'custom5_sm_clust.dlabel.nii'))
    assert os.path.isfile(os.path.join(output_dir, 'custom5_smneg_statclust_report.csv'))
    assert not os.path.isfile(os.path.join(output_dir, 'custom5_smneg_clust.dlabel.nii'))
    # assert False

def test_report_with_different_surfaces(output_dir):
    '''make two rois with ciftify_surface_rois then send them to the other version'''
    vertices1_csv = os.path.join(output_dir, 'vertices1.csv')
    surface_gaussian = os.path.join(output_dir, 'vertices1.dscalar.nii')
    with open(vertices1_csv, "w") as text_file:
        text_file.write('''hemi,vertex
    L,290,
    R,1434,
    ''')
    run(['ciftify_surface_rois', '--debug',
        '--gaussian', vertices1_csv, '8',
        left_3k_surface, right_3k_surface, surface_gaussian])
    run(['ciftify_statclust_report',
         '--max-threshold 0', '--min-threshold 0',
         '--left-surface', left_3k_surface,
         '--right-surface', right_3k_surface,
        surface_gaussian])
    assert os.path.isfile(os.path.join(output_dir, 'vertices1_statclust_report.csv'))
    # assert False

def test_atlas_report_with_5rois(output_dir):
    ''' get basic regression output from atlas results on 5 rois '''
    output_csv = os.path.join(output_dir, 'custom5_label_report.csv')
    run(['ciftify_atlas_report', '--outputcsv', output_csv, custom_dlabel])
    assert os.path.isfile(output_csv)
