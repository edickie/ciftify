#!/usr/bin/env python3
import os
import unittest
import logging
import shutil
import tempfile
import pandas as pd
import ciftify.config
from ciftify.utils import run, TempDir

import pytest
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
confounds_tsv = os.path.join(get_test_data_path(),
        'sub-50005_task-rest_bold_confounds.tsv')
cleaning_config = os.path.join(ciftify.config.find_ciftify_global(),
        'cleaning_configs','24MP_8acompcor_4GSR.json')
pint_summary = os.path.join(get_test_data_path(),
        'PINT','pint_clean_sm8_summary.csv')

@pytest.fixture(scope = "module")
def clean_sm8_dtseries():
    '''build a cleaned and smoothed dtseries file that multiple tests use as input'''
    with ciftify.utils.TempDir() as clean_dir:
        clean_nii_sm8 = os.path.join(clean_dir, 'output_clean_s8.dtseries.nii')
        run(['ciftify_clean_img', '--debug', '--drop-dummy=3',
             '--clean-config={}'.format(cleaning_config),
             '--confounds-tsv={}'.format(confounds_tsv),
             '--output-file={}'.format(clean_nii_sm8),
             '--smooth-fwhm=8',
             '--left-surface={}'.format(left_surface),
             '--right-surface={}'.format(right_surface),
             test_dtseries])
        yield clean_nii_sm8

def read_meants_csv(meants_path):
    '''use pandas with no header and no index'''
    meants = pd.read_csv(meants_path, header = None)
    return meants

@pytest.fixture(scope = "function")
def output_dir():
    with ciftify.utils.TempDir() as outputdir:
        yield outputdir

@pytest.fixture(scope = "function")
def fake_ciftify_work_dir():
    '''link in files to mode a ciftify work dir so that qc pages can be generated'''
    with ciftify.utils.TempDir() as ciftify_wd:
        # create a temp outputdir
        subject = "sub-50005"
        surfs_dir = os.path.join(ciftify_wd, subject, 'MNINonLinear', 'fsaverage_LR32k')
        run(['mkdir', '-p', surfs_dir])
        os.symlink(left_surface, os.path.join(surfs_dir, 'sub-50005.L.midthickness.32k_fs_LR.surf.gii'))
        os.symlink(right_surface, os.path.join(surfs_dir, 'sub-50005.R.midthickness.32k_fs_LR.surf.gii'))
        for hemi in ['L', 'R']:
            old_path = os.path.join(ciftify.config.find_ciftify_global(),
                'HCP_S1200_GroupAvg_v1',
                'S1200.{}.very_inflated_MSMAll.32k_fs_LR.surf.gii'.format(hemi))
            new_path = os.path.join(surfs_dir,
            'sub-50005.{}.very_inflated.32k_fs_LR.surf.gii'.format(hemi))
            os.symlink(old_path, new_path)
        yield ciftify_wd


def test_clean_sm_plus_PINT(output_dir, clean_sm8_dtseries):

    ## run PINT on smoothed file without smoothing
    run(['ciftify_PINT_vertices', '--pcorr',
         clean_sm8_dtseries,
         left_surface,
         right_surface,
         os.path.join(ciftify.config.find_ciftify_global(), 'PINT', 'Yeo7_2011_80verts.csv'),
         os.path.join(output_dir, 'testsub_clean_sm8')])

    assert os.path.exists(os.path.join(output_dir, 'testsub_clean_sm8_tvertex_meants.csv'))
    fixture_meants_t = read_meants_csv(os.path.join(get_test_data_path(),
            'PINT','pint_clean_sm8_tvertex_meants.csv'))
    new_meants_t = read_meants_csv(os.path.join(output_dir, 'testsub_clean_sm8_tvertex_meants.csv'))
    assert (fixture_meants_t == new_meants_t).all().all()

    assert os.path.isfile(os.path.join(output_dir, 'testsub_clean_sm8_summary.csv'))
    fixture_summary = pd.read_csv(pint_summary)
    new_summary = pd.read_csv(os.path.join(output_dir, 'testsub_clean_sm8_summary.csv'))
    assert (fixture_summary == new_summary).all().all()

    assert os.path.isfile(os.path.join(output_dir, 'testsub_clean_sm8_pvertex_meants.csv'))
    fixture_meants_p = read_meants_csv(os.path.join(get_test_data_path(),
            'PINT','pint_clean_sm8_pvertex_meants.csv'))
    new_meants_p = read_meants_csv(os.path.join(output_dir, 'testsub_clean_sm8_pvertex_meants.csv'))
    assert (fixture_meants_p == new_meants_p).all().all()


def test_clean_plus_PINT_smooth(output_dir):

    ## clean without smoothing
    clean_nii_sm0 = os.path.join(output_dir, 'output_clean_s0.dtseries.nii')
    run(['ciftify_clean_img', '--debug', '--drop-dummy=3',
         '--clean-config={}'.format(cleaning_config),
         '--confounds-tsv={}'.format(confounds_tsv),
         '--output-file={}'.format(clean_nii_sm0),
         test_dtseries])

    ## run PINT on unsmoothed file with smoothing
    run(['ciftify_PINT_vertices', '--pcorr',
         '--pre-smooth', '8',
         clean_nii_sm0,
         left_surface,
         right_surface,
         os.path.join(ciftify.config.find_ciftify_global(), 'PINT', 'Yeo7_2011_80verts.csv'),
         os.path.join(output_dir, 'testsub_clean_sm0_sm8')])

    assert os.path.exists(os.path.join(output_dir, 'testsub_clean_sm0_sm8_tvertex_meants.csv'))
    fixture_meants_t = read_meants_csv(os.path.join(get_test_data_path(),
            'PINT','pint_clean_sm0_sm8_tvertex_meants.csv'))
    new_meants_t = read_meants_csv(os.path.join(output_dir, 'testsub_clean_sm0_sm8_tvertex_meants.csv'))
    assert (fixture_meants_t == new_meants_t).all().all()

    assert os.path.isfile(os.path.join(output_dir, 'testsub_clean_sm0_sm8_summary.csv'))
    fixture_summary = pd.read_csv(pint_summary)
    new_summary = pd.read_csv(os.path.join(output_dir, 'testsub_clean_sm0_sm8_summary.csv'))
    assert (fixture_summary == new_summary).all().all()

    assert os.path.isfile(os.path.join(output_dir, 'testsub_clean_sm0_sm8_pvertex_meants.csv'))
    fixture_meants_p = read_meants_csv(os.path.join(get_test_data_path(),
            'PINT','pint_clean_sm0_sm8_pvertex_meants.csv'))
    new_meants_p = read_meants_csv(os.path.join(output_dir, 'testsub_clean_sm0_sm8_pvertex_meants.csv'))
    assert (fixture_meants_p == new_meants_p).all().all()


def test_that_PINT_vis_finishes_without_error(fake_ciftify_work_dir, clean_sm8_dtseries):

    run(['cifti_vis_PINT', 'subject',
        '--ciftify-work-dir', fake_ciftify_work_dir,
         clean_sm8_dtseries, 'sub-50005', pint_summary])

    run(['cifti_vis_PINT', 'index', '--ciftify-work-dir', fake_ciftify_work_dir])

    assert os.path.isfile(os.path.join(fake_ciftify_work_dir, 'qc_PINT', 'index.html'))
    ## assert that the subject output exists
    assert os.path.isfile(os.path.join(fake_ciftify_work_dir, 'qc_PINT', 'sub-50005', 'pvertexDM_LM.png'))
    assert os.path.isfile(os.path.join(fake_ciftify_work_dir, 'qc_PINT', 'sub-50005', 'qc_sub.html'))
