#!/usr/bin/env python
import os
import unittest
import logging
import shutil
import random
import importlib
import pandas as pd

from nose.tools import raises
from mock import patch

ciftify_clean_img = importlib.import_module('ciftify.bin.ciftify_clean_img')

logging.disable(logging.CRITICAL)

# class TestUserSettings(unittest.TestCase):
#
#     docopt_args = {}
#     json_config = {}
#
#     def test_that_updated_arg_is_present():
#
#     def test_exist_gracefully_if_json_not_readable():
#
#     def test_exists_gracefully_if_input_is_gifti():
#
#     def test_exists_gracefully_if_input_is_dscalar():
#
#     def test_exists_gracefully_if_input_is_dlabel():
#
#     def test_dtseries_input_returned():
#
#     def test_nifti_input_returned_correctly():
#
#     def test_exists_gracefully_if_not_writable():
#
#     def test_proper_output_returned_for_nifti():
#
#     def test_proper_output_returned_for_cifti():
#
#     def test_list_arg_always_returns_list():
#
#     def test_bandpass_filter_returns_none_if_none():
#
#     def test_bandpass_filter_returns_float_if_float():
#
#     def test_exists_gracefully_if_filter_not_float():
#
#     def test_exists_gracefully_if_surfaces_not_present():
#
#     def test_fwhm_is_0_if_not_smoothing():


class TestMangleConfounds(unittest.TestCase):

    input_signals = pd.DataFrame(data = {'x': [1,2,3,4,5],
                                         'y': [0,0,1,2,4],
                                         'z': [8,8,8,8,8])

    class SettingsStub(object):
        def __init__(self, start_from, confounddf,
            cf_cols, cf_sq_cols, cf_td_cols, cf_sqtd_cols):
            self.start_from_tr = start_from
            self.confounds = confounddf
            self.cf_cols = cf_cols
            self.cf_sq_cols = cf_sq_cols
            self.cf_td_cols = cf_td_cols
            self.cf_sqtd_cols = cf_sqtd_cols

    def test_starts_from_correct_row():

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = [],
                                     cf_sqtd_cols = [])

        confound_signals = ciftify.bin.ciftify_clean_img.mangle_confounds(settings)
        assert confound_signals['y'] == [1,2,4]

    def test_that_omitted_cols_not_output():

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = [],
                                     cf_sqtd_cols = [])

        confound_signals = ciftify.bin.ciftify_clean_img.mangle_confounds(settings)
        assert 'z' not in confound_signals.columns

    def test_td_col_is_returned():

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = ['y'],
                                     cf_sqtd_cols = [])

        confound_signals = ciftify.bin.ciftify_clean_img.mangle_confounds(settings)
        assert confound_signals['y_lag'].values == [0,1,3]

    def test_sq_is_returned():

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = ['y'],
                                     cf_sqtd_cols = [])

        confound_signals = ciftify.bin.ciftify_clean_img.mangle_confounds(settings)
        assert confound_signals['y_sq'].values == [1,4,9]

    def test_sqtd_col_is_returned():

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = ['y'],
                                     cf_sqtd_cols = ['y'])

        confound_signals = ciftify.bin.ciftify_clean_img.mangle_confounds(settings)
        assert confound_signals['y_sqlag'].values == [0,1,9]

    def test_all_cols_named_as_expected():

        settings = self.SettingsStub(start_from = 2,
                                     confounds = self.input_signals,
                                     cf_cols = ['x', 'y'],
                                     cf_sq_cols = ['y'],
                                     cf_td_cols = ['y'],
                                     cf_sqtd_cols = ['y'])

        confound_signals = ciftify.bin.ciftify_clean_img.mangle_confounds(settings)
        for coln in ['x', 'y', 'y_sq', 'y_lag', 'y_sqlag']:
            assert coln in confound_signals.columns

# class TestCleanImage(unittest.TestCase):
#     # note this one need to patch nilean.clean_img just to check it is only called when asked for
#     def test_nilearn_not_called_not_indicated():
