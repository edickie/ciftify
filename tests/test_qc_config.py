#!/usr/bin/env python
import os
import unittest
import logging
import yaml

from nose.tools import raises

import ciftify.qc_config

# Silence logging output for tests
logging.disable(logging.CRITICAL)

# A default qc mode defined in ciftify/data/qc_modes.yaml, tests should
# pass even if changed.
QC_MODE = 'func2cifti'

class TestConfig(unittest.TestCase):

    def setUp(self):
        # Clear environment to ensure ciftify default qc settings used
        ciftify_data = os.getenv('CIFTIFY_DATA')
        if ciftify_data is not None:
            del os.environ['CIFTIFY_DATA']
        hcp_templates = os.getenv('HCP_SCENE_TEMPLATES')
        if hcp_templates is not None:
            del os.environ['HCP_SCENE_TEMPLATES']

    def __get_settings(self):
        default_config = os.path.join(ciftify.config.find_ciftify_global(),
                'qc_modes.yaml')
        with open(default_config, 'r') as qc_stream:
            settings = yaml.load(qc_stream)
        return settings

    @raises(SystemExit)
    def test_exits_gracefully_when_qc_settings_file_unreadable(self):
        # Set the shell variable CIFTIFY_DATA to get qc_config.config
        # to try to read a nonexistent yaml
        fake_data_path = '/some/path/ciftify/data'
        os.environ['CIFTIFY_DATA'] = fake_data_path

        qc_config = ciftify.qc_config.Config(QC_MODE)

        # Should never reach this line
        assert False

    @raises(SystemExit)
    def test_exits_gracefully_when_given_undefined_qc_mode(self):
        qc_config = ciftify.qc_config.Config('banana')
        assert False

    @raises(SystemExit)
    def test_exits_gracefully_if_users_scene_templates_dont_exist(self):
        # If the user overrides the default with HCP_SCENE_TEMPLATES shell var
        # but the path doesn't exist, config should exit.
        fake_template_path = '/some/user/path/scene_templates'
        os.environ['HCP_SCENE_TEMPLATES'] = fake_template_path

        qc_config = ciftify.qc_config.Config(QC_MODE)
        assert False

    def test_sets_template_name_and_template_to_expected_value(self):
        all_modes = self.__get_settings()

        for qc_mode in all_modes.keys():
            qc_settings = all_modes[qc_mode]
            qc_config = ciftify.qc_config.Config(qc_mode)

            assert qc_config.template_name == qc_settings['TemplateFile']
            assert os.path.basename(qc_config.template) == qc_settings[
                    'TemplateFile']

    def test_get_navigation_list_adjusts_paths_of_list_items(self):
        path = '/some/path/somewhere'

        qc_config = ciftify.qc_config.Config(QC_MODE)

        nav_list = qc_config.get_navigation_list(path=path)

        for entry in nav_list:
            if not entry['href']:
                # Skip entries with no defined html page
                continue
            assert os.path.dirname(entry['href']) == path
