#!/usr/bin/env python
import unittest
import logging
import importlib
import random

import ciftify.qc_config
func2hcp = importlib.import_module('ciftify.bin.cifti_vis_func2hcp')

# Necessary to silence all logging during tests.
logging.disable(logging.CRITICAL)

class TestModifyTemplateContents(unittest.TestCase):

    #This test is to prevent regression. The variable list should always
    # be replaced within this template (func2cifti)
    variable_list = ['HCP_DATA_PATH', 'SUBJID', 'RSLTDIR', 'DTSERIESFILE',
            'SBREFFILE', 'SBREFDIR', 'SBREFRELDIR']

    def test_replaced_variables_all_removed_from_template(self):
        template_contents = get_template_contents(self.variable_list)
        user_settings = self.get_settings()
        temp_dir = '/some/tmp/dir'
        scene_file = 'qcsomemode_subid.scene'

        new_text = func2hcp.modify_template_contents(template_contents,
                user_settings, scene_file, temp_dir)

        for variable in self.variable_list:
            assert variable not in new_text

    def get_settings(self):
        class UserSettings(object):
            def __init__(self):
                self.subject = "subject_id"
                self.fmri_name = "rest"
                self.fwhm = "8"
                self.hcp_dir = "/some/path"
        return UserSettings()

def get_template_contents(keys):
    # Not a stroke, just randomly generated text
    mock_contents = ['Behind sooner dining so window excuse he summer.',
            ' Breakfast met certainty and fulfilled propriety led. ',
            ' Waited get either are wooded little her. Contrasted ',
            'unreserved as mr particular collecting it everything as ',
            'indulgence. Seems ask meant merry could put. Age old begin ',
            'had boy noisy table front whole given.']
    mock_contents.extend(keys)
    random.shuffle(mock_contents)
    template_contents = ' '.join(mock_contents)
    return template_contents
