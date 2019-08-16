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

@pytest.fixture(scope = "function")
def output_dir():
    with ciftify.utils.TempDir() as outputdir:
        yield outputdir

left_surface = os.path.join(get_test_data_path(),
        'sub-50005.L.midthickness.32k_fs_LR.surf.gii')
right_surface = os.path.join(get_test_data_path(),
        'sub-50005.R.midthickness.32k_fs_LR.surf.gii')


def test_ciftify_surface_rois_gaussian(output_dir):

    vertices1_csv = os.path.join(output_dir, 'vertices1.csv')

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
    ''')

    output_dscalar = os.path.join(output_dir, 'gaussian.dscalar.nii')
    run(['ciftify_surface_rois', vertices1_csv, '10', '--gaussian',
         left_surface,
         right_surface,
         output_dscalar])
    assert os.path.isfile(output_dscalar)


def test_ciftify_surface_rois_probmap(output_dir):

    vertices2_csv = os.path.join(output_dir, 'vertices1.csv')
    with open(vertices2_csv, "w") as text_file:
        text_file.write('''hemi,vertex
    R,2379
    R,2423
    R,2423
    R,2629
    R,29290
    R,29290
    ''')

    output_dscalar = os.path.join(output_dir, 'probmap.dscalar.nii')
    run(['ciftify_surface_rois', vertices2_csv, '10', '--probmap',
         left_surface,
         right_surface,
         output_dscalar])
    assert os.path.isfile(output_dscalar)

def test_ciftify_surface_rois_with_labels(output_dir):

    output_dscalar = os.path.join(output_dir, 'pint_template.dscalar.nii')
    run(['ciftify_surface_rois',
          os.path.join(ciftify.config.find_ciftify_global(), 'PINT', 'Yeo7_2011_80verts.csv'),
          '6',
          '--vertex-col', 'tvertex',
          '--labels-col', 'NETWORK',
          '--overlap-logic', 'EXCLUDE',
          os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                    'S1200.L.midthickness_MSMAll.32k_fs_LR.surf.gii'),
          os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                    'S1200.R.midthickness_MSMAll.32k_fs_LR.surf.gii'),
          output_dscalar])
    assert os.path.isfile(output_dscalar)
