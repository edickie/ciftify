#!/usr/bin/env python
import os
import unittest
import logging
import shutil
import tempfile
import ciftify.config

from nose.tools import raises
from mock import patch

def get_test_data_path():
    return os.path.join(os.path.dirname(__file__), 'data')

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


    def test_ciftify_pint_vertices(self):

        run(['ciftify_PINT_vertices', '--pcorr',
             test_dtseries,
             left_surface,
             right_surface,
             os.path.join(ciftify.config.find_ciftify_global(), 'PINT', 'Yeo7_2011_80verts.csv'),
             os.path.join(self.path, 'PINT')])

        assert os.path.exists(os.path.join(self.path, 'PINT_pvertex_meants.csv'))
        assert os.path.exists(os.path.join(self.path, 'PINT_tvertex_meants.csv'))
        assert os.path.exists(os.path.join(self.path, 'PINT_summary.csv'))
