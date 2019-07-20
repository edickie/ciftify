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

rsn_dlabel = os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(), 
                          "RSN-networks.32k_fs_LR.dlabel.nii")
test_nifti = os.path.join(get_test_data_path(),
        'sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz')
hcp_Lmid = os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                        'S1200.L.midthickness_MSMAll.32k_fs_LR.surf.gii')
custom_dlabel = os.path.join(get_test_data_path(),
                             'rois', 'rois_for_tests.dlabel.nii')
sub_left_mid_surface = os.path.join(get_test_data_path(),
        'sub-50005.L.midthickness.32k_fs_LR.surf.gii')

@pytest.fixture(scope = "function")
def output_dir():
    with ciftify.utils.TempDir() as outputdir:
        yield outputdir
        

def test_ciftify_dlabel_to_vol_rsn_map1(output_dir):

    output_nii = os.path.join(output_dir, 'yeo_atlas.nii.gz')
    run(['ciftify_dlabel_to_vol',
         '--input-dlabel', rsn_dlabel,
         '--left-mid-surface', hcp_Lmid,
         '--volume-template', test_nifti,
         '--output-nifti', output_nii])
    assert os.path.isfile(output_nii)

def test_ciftify_dlabel_to_vol_rsn_map2(output_dir):

    output_nii = os.path.join(output_dir, 'yeo17_atlas.nii.gz')
    run(['ciftify_dlabel_to_vol',
         '--map-number', '2',
         '--input-dlabel', rsn_dlabel,
         '--left-mid-surface', hcp_Lmid,
         '--volume-template', test_nifti,
         '--output-nifti', output_nii])
    assert os.path.isfile(output_nii)

def test_ciftify_dlabel_to_vol_rsn_nearest(output_dir):

    output_nii = os.path.join(output_dir, 'yeo7_atlas.nii.gz')
    run(['ciftify_dlabel_to_vol',
         '--use-nearest-vertex', '1.2',
         '--input-dlabel', rsn_dlabel,
         '--left-mid-surface', sub_left_mid_surface,
         '--volume-template', test_nifti,
         '--output-nifti', output_nii])
    assert os.path.isfile(output_nii)

def test_ciftify_dlabel_to_vol_custom_map(output_dir):

    output_nii = os.path.join(output_dir, 'custom_atlas.nii.gz')
    run(['ciftify_dlabel_to_vol',
         '--input-dlabel', custom_dlabel,
         '--left-mid-surface', hcp_Lmid,
         '--volume-template', test_nifti,
         '--output-nifti', output_nii])
    assert os.path.isfile(output_nii)