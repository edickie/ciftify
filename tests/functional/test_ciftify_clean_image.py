#!/usr/bin/env python3
import os
import unittest
import logging
import shutil
import tempfile
import ciftify.config
from ciftify.utils import run

from nose.tools import raises
from mock import patch

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

class TestCitifyClean(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp()
        # create a temp outputdir

    def tearDown(self):
        shutil.rmtree(self.path)


    def test_ciftify_clean_img_dtseries(self):

        output_nii = os.path.join(self.path, 'output_clean_s8.dtseries.nii')
        output_json = os.path.join(self.path, 'output_clean_s8.json')
        run(['ciftify_clean_img', '--debug', '--drop-dummy=3',
             '--clean-config={}'.format(cleaning_config),
             '--confounds-tsv={}'.format(confounds_tsv),
             '--output-file={}'.format(output_nii),
             '--smooth-fwhm=8',
             '--left-surface={}'.format(left_surface),
             '--right-surface={}'.format(right_surface),
             test_dtseries])
        assert os.path.isfile(output_nii)
        assert os.path.isfile(output_json)


    def test_ciftify_clean_img_nifti(self):

        output_nii = os.path.join(self.path, 'output_clean_s8.nii.gz')
        output_json = os.path.join(self.path, 'output_clean_s8.json')
        run(['ciftify_clean_img', '--debug', '--drop-dummy=3',
             '--clean-config={}'.format(cleaning_config),
             '--confounds-tsv={}'.format(confounds_tsv),
             '--output-file={}'.format(output_nii),
             '--smooth-fwhm=8',
             test_nifti])
        assert os.path.isfile(output_nii)
        assert os.path.isfile(output_json)
