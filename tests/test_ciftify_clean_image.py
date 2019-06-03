#!/usr/bin/env python3
import os
import unittest
import copy
import logging
import shutil
import random
import importlib
import pandas as pd
import json

from nose.tools import raises
from mock import patch

from nibabel import Nifti1Image
import numpy as np
import nilearn.image

import ciftify.bin.ciftify_clean_img as ciftify_clean_img

logging.disable(logging.CRITICAL)

def _check_input_readble_side_effect(path):
    '''just returns the path'''
    return(path)

def _pandas_read_side_effect(path):
    '''return and empty data frame'''
    return(pd.DataFrame())

class TestUserSettings(unittest.TestCase):

    docopt_args = {
      '<func_input>': '/path/to/func/file.nii.gz',
      '--output-file': None,
      '--clean-config': None,
      '--drop-dummy-TRs': None,
      '--no-cleaning': False,
      '--detrend': False,
      '--standardize': False,
      '--confounds-tsv': None,
      '--cf-cols': None,
      '--cf-sq-cols': None,
      '--cf-td-cols': None,
      '--cf-sqtd-cols': None,
      '--low-pass': None,
      '--high-pass': None,
      '--tr': '2.0',
      '--smooth-fwhm': None,
      '--left-surface': None,
      '--right-surface': None }
    json_config = '''
    {
      "--detrend": true,
      "--standardize": true,
      "--low-pass": 0.1,
      "--high-pass": 0.01
     }
'''


    @patch('ciftify.bin.ciftify_clean_img.load_json_file', side_effect = json.loads)
    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_that_updated_arg_is_present(self, mock_readable, mock_writable, mock_json):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['--clean-config'] = self.json_config
        settings = ciftify_clean_img.UserSettings(arguments)

        assert settings.high_pass == 0.01, "high_pass not set to config val"
        assert settings.detrend == True, "detrend not set to config val"


    @raises(SystemExit)
    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_exist_gracefully_if_json_not_readable(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/func.nii.gz'
        missing_json = '/wrong/path/missing.json'
        arguments['--clean-config'] = missing_json


        settings = ciftify_clean_img.UserSettings(arguments)

        assert False


    @raises(SystemExit)
    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_exists_gracefully_if_input_is_gifti(self, mock_readable, mock_writable):


        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/func.L.func.gii'
        settings = ciftify_clean_img.UserSettings(arguments)

        assert False


    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_dtseries_input_returned(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.dtseries.nii'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.func.type == "cifti"
        assert settings.func.path == '/path/to/input/myfunc.dtseries.nii'


    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_nifti_input_returned_correctly(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.nii.gz'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.func.type == "nifti"
        assert settings.func.path == '/path/to/input/myfunc.nii.gz'


    @raises(SystemExit)
    def test_exists_gracefully_if_output_not_writable(self):

        wrong_func = '/wrong/path/to/input/myfunc.nii.gz'
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = wrong_func
        settings = ciftify_clean_img.UserSettings(arguments)
        assert False


    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_proper_output_returned_for_nifti(self, mock_readable, mock_writable):


        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.nii.gz'
        arguments['--smooth-fwhm'] = 8
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.output_func == '/path/to/input/myfunc_clean_s8.nii.gz'

    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_proper_output_returned_for_cifti(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.dtseries.nii'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.output_func == '/path/to/input/myfunc_clean_s0.dtseries.nii'

    @raises(SystemExit)
    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_exits_when_confounds_tsv_not_given(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['--cf-cols'] = 'one,two,three'
        arguments['--confounds-tsv'] = None
        settings = ciftify_clean_img.UserSettings(arguments)
        assert False

    @patch('pandas.read_csv', return_value = pd.DataFrame(columns = ['one', 'two', 'three']))
    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_list_arg_returns_list_for_multi(self, mock_readable, mock_writable, mock_pdread):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['--cf-cols'] = 'one,two,three'
        arguments['--confounds-tsv'] = '/path/to/confounds.tsv'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.cf_cols == ['one','two','three']

    @patch('pandas.read_csv', return_value = pd.DataFrame(columns = ['one', 'two', 'three']))
    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_list_arg_returns_list_for_one_item(self, mock_readable, mock_writable, mock_pdread):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['--cf-cols'] = 'one'
        arguments['--confounds-tsv'] = '/path/to/confounds.tsv'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.cf_cols == ['one']

    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_list_arg_returns_empty_list_for_none(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.cf_cols == []


    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_bandpass_filter_returns_none_if_none(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.high_pass == None


    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_bandpass_filter_returns_float_if_float(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['--high-pass'] = '3.14'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.high_pass == 3.14


    @raises(SystemExit)
    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_exists_gracefully_if_filter_not_float(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['--high-pass'] = 'three'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert False


    @raises(SystemExit)
    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_exists_gracefully_if_surfaces_not_present(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.dtseries.nii'
        arguments['--smooth-fwhm'] = 8
        arguments['--left-surface'] = None

        settings = ciftify_clean_img.UserSettings(arguments)
        assert False


    @patch('ciftify.utils.check_input_readable', side_effect = _check_input_readble_side_effect)
    @patch('ciftify.utils.check_output_writable', return_value = True)
    def test_fwhm_is_0_if_not_smoothing(self, mock_readable, mock_writable):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.nii.gz'
        arguments['--smooth-fwhm'] = None

        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.smooth.fwhm == 0

class TestMangleConfounds(unittest.TestCase):

    input_signals = pd.DataFrame(data = {'x': [1,2,3,4,5],
                                         'y': [0,0,1,2,4],
                                         'z': [8,8,8,8,8]})

    class SettingsStub(object):
        def __init__(self, start_from, confounds,
            cf_cols, cf_sq_cols, cf_td_cols, cf_sqtd_cols):
            self.start_from_tr = start_from
            self.confounds = confounds
            self.cf_cols = cf_cols
            self.cf_sq_cols = cf_sq_cols
            self.cf_td_cols = cf_td_cols
            self.cf_sqtd_cols = cf_sqtd_cols

    def test_starts_from_correct_row(self):

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = [],
                                     cf_sqtd_cols = [])

        confound_signals = ciftify_clean_img.mangle_confounds(settings)
        test_output = confound_signals['y'].values
        expected_output = np.array([1,2,4])
        assert np.allclose(test_output, expected_output, equal_nan  = True), \
            "{} not equal to {}".format(test_output, expected_output)

    def test_that_omitted_cols_not_output(self):

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = [],
                                     cf_sqtd_cols = [])

        confound_signals = ciftify_clean_img.mangle_confounds(settings)
        assert 'z' not in list(confound_signals.columns.values)

    def test_td_col_is_returned(self):

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = ['y'],
                                     cf_sqtd_cols = [])

        confound_signals = ciftify_clean_img.mangle_confounds(settings)
        test_output = confound_signals['y_lag'].values
        expected_output = np.array([0,1,2])
        assert np.allclose(test_output, expected_output, equal_nan  = True), \
            "{} not equal to {}".format(test_output, expected_output)


    def test_sq_is_returned(self):

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = ['y'],
                                     cf_sqtd_cols = [])

        confound_signals = ciftify_clean_img.mangle_confounds(settings)
        test_output = confound_signals['y_sq'].values
        expected_output = np.array([1,4,16])
        assert np.allclose(test_output, expected_output, equal_nan  = True), \
            "{} not equal to {}".format(test_output, expected_output)


    def test_sqtd_col_is_returned(self):

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = ['y'],
                                     cf_sqtd_cols = ['y'])

        confound_signals = ciftify_clean_img.mangle_confounds(settings)

        test_output = confound_signals['y_sqlag'].values
        expected_output = np.array([0,1,4])
        assert np.allclose(test_output, expected_output, equal_nan  = True), \
            "{} not equal to {}".format(test_output, expected_output)


    def test_all_cols_named_as_expected(self):

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = ['y'],
                                     cf_sqtd_cols = ['y'])

        confound_signals = ciftify_clean_img.mangle_confounds(settings)
        for coln in ['x', 'y', 'y_sq', 'y_lag', 'y_sqlag']:
            assert coln in list(confound_signals.columns.values)

@patch('nilearn.image.clean_img')
class TestCleanImage(unittest.TestCase):
    # note this one need to patch nilean.clean_img just to check it is only called when asked for
    def test_nilearn_not_called_not_indicated(self, nilearn_clean):

        class SettingsStub(object):
            def __init__(self):
                self.detrend = False
                self.standardize = False
                self.high_pass = None
                self.low_pass = None

        input_img = 'fake_img.nii.gz'
        confound_signals = None
        settings = SettingsStub()

        output_img = ciftify_clean_img.clean_image_with_nilearn(
            input_img, confound_signals, settings)

        nilearn_clean.assert_not_called()

def test_drop_image():
    img1 = Nifti1Image(np.ones((2, 2, 2, 1)), affine=np.eye(4))
    img2 = Nifti1Image(np.ones((2, 2, 2, 1)) + 1, affine=np.eye(4))
    img3 = Nifti1Image(np.ones((2, 2, 2, 1)) + 2, affine=np.eye(4))
    img4 = Nifti1Image(np.ones((2, 2, 2, 1)) + 3, affine=np.eye(4))
    img5 = Nifti1Image(np.ones((2, 2, 2, 1)) + 4, affine=np.eye(4))

    img_1to5 = nilearn.image.concat_imgs([img1, img2, img3, img4, img5])

    img_trim = ciftify_clean_img.image_drop_dummy_trs(img_1to5, 2)

    assert np.allclose(img_trim.get_data()[1,1,1,:], np.array([3, 4, 5]))
    assert img_trim.header.get_data_shape() == (2,2,2,3)
