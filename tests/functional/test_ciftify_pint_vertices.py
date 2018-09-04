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

class TestCitifyPINT(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp()
        # create a temp outputdir

    def tearDown(self):
        shutil.rmtree(self.path)


    def test_ciftify_pint_vertices(self):

        run(['ciftify_PINT_vertices', '--pcorr',
             test_dtseries,
             left_surface,
             right_surface,
             os.path.join(ciftify.config.find_ciftify_global(), 'PINT', 'Yeo7_2011_80verts.csv'),
             os.path.join(self.path, 'testsub')])

        assert os.path.exists(os.path.join(self.path, 'testsub_pvertex_meants.csv'))
        assert os.path.exists(os.path.join(self.path, 'testsub_tvertex_meants.csv'))
        assert os.path.exists(os.path.join(self.path, 'testsub_summary.csv'))

    def test_clean_sm_plus_PINT(self):

        ## clean with smoothing
        clean_nii_sm8 = os.path.join(self.path, 'output_clean_s8.dtseries.nii')
        run(['ciftify_clean_img', '--debug', '--drop-dummy=3',
             '--clean-config={}'.format(cleaning_config),
             '--confounds-tsv={}'.format(confounds_tsv),
             '--output-file={}'.format(clean_nii_sm8),
             '--smooth-fwhm=8',
             '--left-surface={}'.format(left_surface),
             '--right-surface={}'.format(right_surface),
             test_dtseries])

        ## run PINT on smoothed file without smoothing
        run(['ciftify_PINT_vertices', '--pcorr',
             clean_nii_sm8,
             left_surface,
             right_surface,
             os.path.join(ciftify.config.find_ciftify_global(), 'PINT', 'Yeo7_2011_80verts.csv'),
             os.path.join(self.path, 'testsub_clean_sm8')])

        assert os.path.isfile(os.path.join(self.path, 'testsub_clean_sm8_summary.csv'))


    def test_clean_plus_PINT_smooth(self):

        ## clean without smoothing
        clean_nii_sm0 = os.path.join(self.path, 'output_clean_s0.dtseries.nii')
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
             os.path.join(self.path, 'testsub_clean_sm0_sm8')])

        assert os.path.isfile(os.path.join(self.path, 'testsub_clean_sm0_sm8_summary.csv'))

class TestCitifyVisPINT(unittest.TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp()
        # create a temp outputdir
        self.subject = "sub-50005"
        surfs_dir = os.path.join(self.path, self.subject, 'MNINonLinear', 'fsaverage_LR32k')
        run(['mkdir', '-p', surfs_dir])
        os.symlink(left_surface, os.path.join(surfs_dir, 'sub-50005.L.midthickness.32k_fs_LR.surf.gii'))
        os.symlink(right_surface, os.path.join(surfs_dir, 'sub-50005.R.midthickness.32k_fs_LR.surf.gii'))
        for hemi in ['L', 'R']:
            old_path = os.path.join(ciftify.config.find_ciftify_global(),
                'HCP_S1200_GroupAvg_v1',
                'S1200.{}.very_inflated_MSMAll.32k_fs_LR.surf.gii'.format(hemi))
            new_path = os.path.join(surfs_dir,
            'sub-50005.{}.very_inflated.32k_fs_LR.surf.gii'.format(hemi))

    def tearDown(self):
        shutil.rmtree(self.path)

    def test_that_PINT_vis_finishes_without_error(self):

        ## clean with smoothing
        clean_nii_sm8 = os.path.join(self.path, 'output_clean_s8.dtseries.nii')
        run(['ciftify_clean_img', '--debug', '--drop-dummy=3',
             '--clean-config={}'.format(cleaning_config),
             '--confounds-tsv={}'.format(confounds_tsv),
             '--output-file={}'.format(clean_nii_sm8),
             '--smooth-fwhm=8',
             '--left-surface={}'.format(left_surface),
             '--right-surface={}'.format(right_surface),
             test_dtseries])

        run(cifti_vis_PINT subject --debug --ciftify-work-dir /scratch/edickie/test2018_ciftify/fake_wd/ output_clean_s8.dtseries.nii sub-50005 pint_clean_sm8_summary.csv
         cifti_vis_PINT index --debug --ciftify-work-dir /scratch/edickie/test2018_ciftify/fake_wd/
        assert os.path.isfile(os.path.join(self.path, 'testsub_clean_sm8_summary.csv'))
