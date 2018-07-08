#!/usr/bin/env python
import os
import unittest
import logging
import shutil
import random

from nose.tools import raises
from mock import patch

import ciftify.niio as niio

logging.disable(logging.CRITICAL)

class TestUserSettings(unittest.TestCase):

    docopt_args = {}
    json_config = {}

    def test_that_updated_arg_is_present():

    def test_exist_gracefully_if_json_not_readable():

    def test_exists_gracefully_if_input_is_gifti():

    def test_exists_gracefully_if_input_is_dscalar():

    def test_exists_gracefully_if_input_is_dlabel():

    def test_dtseries_input_returned():

    def test_nifti_input_returned_correctly():

    def test_exists_gracefully_if_not_writable():

    def test_proper_output_returned_for_nifti():

    def test_proper_output_returned_for_cifti():

    def test_list_arg_always_returns_list():

    def test_bandpass_filter_returns_none_if_none():

    def test_bandpass_filter_returns_float_if_float():

    def test_exists_gracefully_if_filter_not_float():

    def test_exists_gracefully_if_surfaces_not_present():

    def test_fwhm_is_0_if_not_smoothing():


class TestMangleConfounds(unittest.TestCase):

    input_signals = pd.DataFrame('x')

    class SettingsStub(object):
        def __init__(self, confounddf,
            cf_cols, cf_sq_cols, cf_td_cols, cf_sqtd_cols):
            self.confounds = confounddf
            self.cf_cols = cf_cols
            self.cf_sq_cols = cf_sq_cols
            self.cf_td_cols = cf_td_cols
            self.cf_sqtd_cols = cf_sqtd_cols

    def test_that_omitted_cols_not_output:

    def test_td_col_is_returned:

    def test_sq_is_returned:

    def test_sqtd_col_is_returned:
