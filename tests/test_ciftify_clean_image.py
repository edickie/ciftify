#!/usr/bin/env python
import os
import unittest
import copy
import logging
import shutil
import random
import importlib
import pandas as pd

from nose.tools import raises
from mock import patch

import ciftify.bin.ciftify_clean_img as ciftify_clean_img

logging.disable(logging.CRITICAL)

class TestUserSettings(unittest.TestCase):

    docopt_args = {
      '<func_input>': '/path/to/func/file',
      '--output_file': None,
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
      '--t_r': None,
      '--smooth_fwhm': None,
      '--left-surface': None,
      '--right-surface': None }
    json_config = '''
    {
      "--detrend": true,
      "--standardize": true,
      "--cf-cols": "X,Y,Z,RotX,RotY,RotZ,CSF,WhiteMatter,GlobalSignal",
      "--cf-sq-cols": "X,Y,Z,RotX,RotY,RotZ,CSF,WhiteMatter,GlobalSignal",
      "--cf-td-cols": "X,Y,Z,RotX,RotY,RotZ,CSF,WhiteMatter,GlobalSignal",
      "--cf-sqtd-cols": "X,Y,Z,RotX,RotY,RotZ,CSF,WhiteMatter,GlobalSignal",
      "--low-pass": 0.1,
      "--high-pass": 0.01
     }
'''
    @patch('os.path.exists')
    def test_that_updated_arg_is_present(self, mock_exists):

        mock_exists.return_value = True

        arguments = copy.deepcopy(self.docopt_args)
        arguments['--clean-config'] = self.json_config

        settings = ciftify_clean_img.UserSettings(arguments)

        assert settings.high_pass == 0.01, "high_pass not set to config val"
        assert settings.detrent == True, "detrend not set to config val"

    @raises(SysExit)
    @patch('os.path.exists')
    def test_exist_gracefully_if_json_not_readable(self, mock_exists):

        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/func.nii.gz'
        missing_json = '/wrong/path/missing.json'
        arguments['--clean-config'] = missing_json

        mock_exists.side_effect = False if path == missing_json else True

        settings = ciftify_clean_img.UserSettings(arguments)

        assert False

    @raises(SysExit)
    @patch('os.path.exists')
    def test_exists_gracefully_if_input_is_gifti(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/func.L.func.gii'
        settings = ciftify_clean_img.UserSettings(arguments)

        assert False


    @raises(SysExit)
    @patch('os.path.exists')
    def test_exists_gracefully_if_input_is_dscalar(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/thickness.dscalar.nii'
        settings = ciftify_clean_img.UserSettings(arguments)

        assert False

    @raises(SysExit)
    @patch('os.path.exists')
    def test_exists_gracefully_if_input_is_dlabel(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/atlas.dlabel.nii'
        settings = ciftify_clean_img.UserSettings(arguments)

        assert False

    @patch('os.path.exists')
    def test_dtseries_input_returned(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.dtseries.nii'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.func.type == "cifti"
        assert settings.func.path == '/path/to/input/myfunc.dtseries.nii'


    @patch('os.path.exists')
    def test_nifti_input_returned_correctly(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.nii.gz'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.func.type == "nifti"
        assert settings.func.path == '/path/to/input/myfunc.nii.gz'

    @raises(SysExit)
    @patch('os.path.exists')
    def test_exists_gracefully_if_output_not_writable(self, mock_exists):

        wrong_func = '/wrong/path/to/input/myfunc.nii.gz'
        mock_exists.side_effect = False if path == wrong_func else True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = wrong_func
        settings = ciftify_clean_img.UserSettings(arguments)
        assert False

    @patch('os.path.exists')
    def test_proper_output_returned_for_nifti(self):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.nii.gz'
        arguments['--smooth_fwhm'] = 8
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.output_func == '/path/to/input/myfunc_clean_s8.nii.gz'

    @patch('os.path.exists')
    def test_proper_output_returned_for_cifti(self):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.dtseries.nii'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.output_func == '/path/to/input/myfunc_clean_s0.dtseries.nii'


    @patch('os.path.exists')
    def test_list_arg_returns_list_for_multi(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['--cf-cols'] = 'one,two,three'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.cf_cols == ['one','two','three']

    @patch('os.path.exists')
    def test_list_arg_returns_list_for_one_item(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['--cf-cols'] = 'one'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.cf_cols == ['one']

    @patch('os.path.exists')
    def test_list_arg_returns_empty_list_for_none(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.cf_cols == []

    @patch('os.path.exists')
    def test_bandpass_filter_returns_none_if_none(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.high_pass == None

    @patch('os.path.exists')
    def test_bandpass_filter_returns_float_if_float(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['--high_pass'] = '3.14'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert settings.high_pass == 3.14

    @raises(SysExit)
    @patch('os.path.exists')
    def test_exists_gracefully_if_filter_not_float(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['--high_pass'] = 'three'
        settings = ciftify_clean_img.UserSettings(arguments)
        assert False

    @raises(SysExit)
    @patch('os.path.exists')
    def test_exists_gracefully_if_surfaces_not_present(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.dtseries.nii'
        arguments['--smooth_fwhm'] = 8
        arguments['--left-surface'] = None

        settings = ciftify_clean_img.UserSettings(arguments)
        assert False


    @patch('os.path.exists')
    def test_fwhm_is_0_if_not_smoothing(self, mock_exists):

        mock_exists.return_value = True
        arguments = copy.deepcopy(self.docopt_args)
        arguments['<func_input>'] = '/path/to/input/myfunc.nii.gz'
        arguments['--smooth_fwhm'] = None

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
        assert confound_signals['y'].equals(pd.Series([1,2,4])), \
            "{} not equal to [1,2,4]".format(confound_signals['y'].values)

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
        assert confound_signals['y_lag'].equals(pd.Series([0,1,3])), \
            "{} not equal to [0,1,3]".format(confound_signals['y_lag'].values)

    def test_sq_is_returned(self):

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = ['y'],
                                     cf_sqtd_cols = [])

        confound_signals = ciftify_clean_img.mangle_confounds(settings)
        assert confound_signals['y_sq'].equals(pd.Series([1,4,9])), \
            "{} not equal to [1,4,9]".format(confound_signals['y_sq'].values)

    def test_sqtd_col_is_returned(self):

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = ['y'],
                                     cf_sqtd_cols = ['y'])

        confound_signals = ciftify_clean_img.mangle_confounds(settings)
        assert confound_signals['y_sqlag'].equals(pd.Series([0,1,9])), \
            "{} not equal to [0,1,9]".format(confound_signals['y_sqlag'].values)

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

    img_1to5 = nilean.image_concat([img1, img2, img3, img4, img5])

    img_trim = ciftify_clean_img.image_drop_dummy_trs(img_1to5, 2)

    assert img_trim.get_data()[1,1,1,:] == [3 4 5]
