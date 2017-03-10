#!/usr/bin/env python
import os
import unittest
import logging

import ciftify.config

class SetUpMixin(object):
    def setUp(self):
        # Clear the shell environment, so it doesn't interfere with tests
        shell_dir = os.getenv(self.env_var)
        if shell_dir is not None:
            del os.environ[self.env_var]

class TestFindSceneTemplates(SetUpMixin, unittest.TestCase):

    env_var = 'HCP_SCENE_TEMPLATES'

    def test_returns_default_templates_folder_if_shell_var_unset(self):
        scene_dir = ciftify.config.find_scene_templates()
        ciftify_default = os.path.abspath(os.path.join(os.path.dirname(__file__),
                '../data/scene_templates'))

        assert scene_dir is not None
        assert scene_dir == ciftify_default

    def test_returns_user_shell_variable_when_set(self):
        template_path = '/some/path/templates'
        # Add a shell variable
        os.environ[self.env_var] = template_path

        scene_dir = ciftify.config.find_scene_templates()

        assert scene_dir == template_path

class TestFindCiftifyGlobal(SetUpMixin, unittest.TestCase):

    env_var = 'CIFTIFY_DATA'

    def test_returns_default_data_folder_if_shell_var_unset(self):
        data_folder = ciftify.config.find_ciftify_global()
        ciftify_default = os.path.abspath(os.path.join(os.path.dirname(__file__),
                '../data'))

        assert data_folder is not None
        assert data_folder == ciftify_default

    def test_returns_user_shell_variable_when_set(self):
        user_path = '/some/path/data'
        os.environ[self.env_var] = user_path

        data_path = ciftify.config.find_ciftify_global()

        assert data_path == user_path

class TestFindHCPS900GroupAvg(SetUpMixin, unittest.TestCase):

    env_var = 'CIFTIFY_DATA'
    hcp_folder = 'HCP_S900_GroupAvg_v1'

    def test_returns_path_relative_to_ciftify_global_dir(self):
        ciftify_path = '/some/users/path/ciftify/data'
        os.environ[self.env_var] = ciftify_path

        actual_path = ciftify.config.find_HCP_S900_GroupAvg()
        expected_path = os.path.join(ciftify_path, self.hcp_folder)

        assert actual_path == expected_path
