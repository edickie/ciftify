#!/usr/bin/env python
import os
import unittest
import logging
import shutil
import random

from nose.tools import raises
from mock import patch


test_dtseries = '../data/sub-50005_task-rest_Atlas_s0.dtseries.nii'
test_nifti = '../data/sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz'
left_surface = '../data/sub-50005.L.midthickness.32k_fs_LR.surf.gii'
right_surface = '../data/sub-50005.R.midthickness.32k_fs_LR.surf.gii'
confounds_tsv = '../data/sub-50005_task-rest_bold_confounds.tsv'
cleaning_config = '../ciftify/data/cleaning_configs/24MP_8acompcor_4GSR.json'

class TestCitifyClean():
    def SetUp():
        outputdir =
        # create a temp outputdir

    def tearDown():
        ## remove the whole outputdir

    def test_ciftify_clean_img_dtseries():

        run(['ciftify_clean_img', '--debug', '--drop-dummy=3',
             '--clean-config={}'.format(cleaning_config),
             '--confounds-tsv={}'.format(confounds_tsv),
             '--smooth_fwhm=8',
             '--left-surface={}'.format(left_surface),
             '--right-surface={}'.format(right_surface),
             test_dtseries])
        assert output1exists
        assert json exists


    def test_ciftify_clean_img_dtseries():

        run(['ciftify_clean_img', '--debug', '--drop-dummy=3',
             '--clean-config={}'.format(cleaning_config),
             '--confounds-tsv={}'.format(confounds_tsv),
             '--smooth_fwhm=8',
             test_nifti])
        assert output1exists
        assert json exists

# # run one dtseries with all options..
#     ## at least exists without errors..
#     def test_can_read_tr_from_cifti():
#
#
# # run one nifti series..
#     ## at least exits without errors..
#
#     def test_can_read_tr_from_nifti():
