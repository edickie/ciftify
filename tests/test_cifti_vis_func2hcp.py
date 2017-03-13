#!/usr/bin/env python
import unittest
import logging
import importlib

import ciftify.qc_config
func2hcp = importlib.import_module('bin.cifti_vis_func2hcp')

# Necessary to silence all logging during tests.
logging.disable(logging.CRITICAL)

class TestModifyTemplateContents(unittest.TestCase):
    def test_replaced_variables_all_removed_from_template(self):
        #This test is to prevent regression. The variable list should always
        # be replaced within this template (func2cifti)
        variable_list = ['HCP_DATA_PATH', 'SUBJID', 'RSLTDIR', 'DTSERIESFILE',
                'SBREFFILE']

        # settings stub
        class UserSettings(object):
            def __init__(self):
                self.subject = "subject_id"
                self.fmri_name = "rest"
                self.fwhm = "8"
                self.hcp_dir = "/some/path"

        qc_config = ciftify.qc_config.Config('func2cifti')
        with open(qc_config.template, 'r') as template_text:
            template_contents = template_text.read()
        user_settings = UserSettings()

        new_text = func2hcp.modify_template_contents(template_contents,
                user_settings)

        for variable in variable_list:
            assert variable not in new_text
