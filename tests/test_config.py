#!/usr/bin/env python
import os
import unittest
import logging
from subprocess import CalledProcessError

from mock import patch
from nose.tools import raises

import ciftify.config

logging.disable(logging.CRITICAL)

class SetUpMixin(object):
    def setUp(self):
        # Clear the shell environment, so it doesn't interfere with tests
        for shell_var in self.clear_vars:
            setting = os.getenv(shell_var)
            if setting is not None:
                del os.environ[shell_var]

class TestFindSceneTemplates(SetUpMixin, unittest.TestCase):

    env_var = 'HCP_SCENE_TEMPLATES'
    clear_vars = [env_var, 'CIFTIFY_DATA']

    def test_returns_default_templates_folder_if_shell_var_unset(self):
        scene_dir = ciftify.config.find_scene_templates()
        ciftify_default = os.path.abspath(os.path.join(os.path.dirname(__file__),
                '../ciftify/data/scene_templates'))

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
    clear_vars = list(env_var)

    def test_returns_default_data_folder_if_shell_var_unset(self):
        data_folder = ciftify.config.find_ciftify_global()
        ciftify_default = os.path.abspath(os.path.join(os.path.dirname(__file__),
                '../ciftify/data'))

        assert data_folder is not None
        assert data_folder == ciftify_default

    def test_returns_user_shell_variable_when_set(self):
        user_path = '/some/path/data'
        os.environ[self.env_var] = user_path

        data_path = ciftify.config.find_ciftify_global()

        assert data_path == user_path

class TestFindHCPS900GroupAvg(SetUpMixin, unittest.TestCase):

    env_var = 'CIFTIFY_DATA'
    clear_vars = list(env_var)
    hcp_folder = 'HCP_S900_GroupAvg_v1'

    def test_returns_path_relative_to_ciftify_global_dir(self):
        ciftify_path = '/some/users/path/ciftify/data'
        os.environ[self.env_var] = ciftify_path

        actual_path = ciftify.config.find_HCP_S900_GroupAvg()
        expected_path = os.path.join(ciftify_path, self.hcp_folder)

        assert actual_path == expected_path

class TestWBCommandVersion(unittest.TestCase):

    @raises(EnvironmentError)
    @patch('ciftify.config.find_workbench')
    def test_error_raised_if_not_found(self, mock_find):
        mock_find.return_value = None

        version = ciftify.config.wb_command_version()

class TestFreesurferVersion(unittest.TestCase):

    @raises(EnvironmentError)
    @patch('ciftify.config.find_freesurfer')
    def test_raises_error_when_not_found(self, mock_find):
        mock_find.return_value = None

        version = ciftify.config.freesurfer_version()

    @patch('ciftify.config.find_freesurfer')
    def test_doesnt_crash_if_build_stamp_txt_not_found(self, mock_find):
        mock_find.return_value = '/some/fake/path'

        version = ciftify.config.freesurfer_version()

        assert version

class TestFSLVersion(unittest.TestCase):

    @raises(EnvironmentError)
    @patch('ciftify.config.find_fsl')
    def test_raises_error_when_not_found(self, mock_find):
        mock_find.return_value = None

        version = ciftify.config.fsl_version()

    @patch('ciftify.config.find_fsl')
    def test_doesnt_crash_if_version_info_not_found(self, mock_find):
        mock_find.return_value = '/some/fake/path'

        version = ciftify.config.fsl_version()

        assert version

class TestCiftifyVersion(unittest.TestCase):

    ciftify_path = os.path.dirname(os.path.dirname(__file__))

    def test_returns_default_info_when_given_bad_file_name(self):
        info = ciftify.config.ciftify_version('some-file-that-doesnt-exist')

        assert info
        assert self.ciftify_path in info
        assert 'Commit:' in info

    def test_returns_default_info_when_no_file_provided(self):
        info = ciftify.config.ciftify_version()

        assert info
        assert self.ciftify_path in info
        assert 'Commit:' in info

    @patch('subprocess.check_output')
    def test_returns_path_only_when_git_log_cant_be_found(self, mock_check):
        mock_check.side_effect = CalledProcessError(999, "Some message")

        info = ciftify.config.ciftify_version()

        assert info
        assert self.ciftify_path in info
        assert "Commit:" not in info

    @patch('subprocess.check_output')
    def test_attempts_to_return_last_commit_when_file_name_given(self,
            mock_check):
        info = ciftify.config.ciftify_version('func2hcp.py')

        print('If this test starts failing, it may be because func2hcp has '
                'been renamed. Couldnt think of a more reliable way to write '
                'this test than to pick a random bin script, sorry.')
        assert mock_check.call_count == 3
