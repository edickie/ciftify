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

class TestFindWorkbench(unittest.TestCase):

    @patch('ciftify.utilities.check_output')
    def test_workbench_path_new_line_is_removed(self, mock_out):
        # When 'which wb_command' is run it returns the path ending in a new line
        mock_out.return_value = "/some/path/somewhere{}".format(os.linesep)

        workbench = ciftify.config.find_workbench()

        assert not workbench.endswith(os.linesep)

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

class TestFindFsl(unittest.TestCase):

    def setUp(self):
        # Clear the FSLDIR shell var in case the test runner has it defined.
        fsl_dir = os.getenv('FSLDIR')
        if fsl_dir is not None:
            del os.environ['FSLDIR']

    @patch('os.getenv')
    @patch('os.path.exists')
    def test_uses_fsldir_environment_variable_to_find_fsl_if_set_and_bin_exists(
            self, mock_exists, mock_env):
        # Mock the existence of fsl/bin folder
        fsl_bin = "/some/path/fsl/bin"
        mock_exists.side_effect = lambda x: x == fsl_bin
        mock_env.return_value = os.path.dirname(fsl_bin)

        found_path = ciftify.config.find_fsl()

        print(found_path)

        assert found_path == fsl_bin

    @patch('ciftify.utilities.check_output')
    def test_uses_which_to_find_fsl_if_fsldir_var_not_set(self, mock_which):
        fsl_path = '/some/install/path/fsl/bin/fsl'
        mock_which.return_value = fsl_path

        found_path = ciftify.config.find_fsl()

        assert not os.getenv('FSLDIR')
        assert found_path == os.path.dirname(fsl_path)

    @patch('ciftify.utilities.check_output')
    def test_returns_none_if_fsldir_unset_and_which_fails(self, mock_which):
        mock_which.return_value = ''

        found_path = ciftify.config.find_fsl()

        assert not os.getenv('FSLDIR')
        assert not found_path

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

    # without a file given, will check for git repo in package dir
    ciftify_path = os.path.normpath(os.path.join(os.path.dirname(__file__),
            '../ciftify'))

    @patch('pkg_resources.get_distribution')
    @patch('ciftify.utilities.check_output')
    def test_returns_installed_version_if_installed(self, mock_out, mock_dist):
        version = '9.9.9'
        mock_dist.return_value.version = version

        ciftify_version = ciftify.config.ciftify_version()
        assert mock_out.call_count == 0
        assert version in ciftify_version

        ciftify_version = ciftify.config.ciftify_version(__file__)
        assert mock_out.call_count == 0
        assert version in ciftify_version

    def test_returns_default_info_when_given_bad_file_name(self):
        info = ciftify.config.ciftify_version('some-file-that-doesnt-exist')

        assert info
        assert self.ciftify_path in info
        assert 'Commit:' in info
        assert 'Last commit for' not in info

    def test_returns_default_info_when_no_file_provided(self):
        info = ciftify.config.ciftify_version()

        assert info
        assert self.ciftify_path in info
        assert 'Commit:' in info
        assert 'Last commit for' not in info

    @patch('ciftify.config.get_git_log')
    def test_returns_path_only_when_git_log_cant_be_found(self, mock_log):
        mock_log.return_value = ''

        info = ciftify.config.ciftify_version()

        assert info
        assert self.ciftify_path in info
        assert "Commit:" not in info

    def test_adds_last_commit_of_file_when_given_file_name(self):
        info = ciftify.config.ciftify_version('fs2hcp.py')

        assert info
        assert 'Last commit for' in info

class TestGetGitLog(unittest.TestCase):

    path = os.path.dirname(__file__)

    @patch('subprocess.check_output')
    def test_doesnt_crash_when_git_command_fails(self, mock_proc):
        """ This test ensures that if the git user interface is unexpectedly
        different (old version, future versions etc.) or path is not a git repo
        the failed git command will not cause an exception. """
        mock_proc.side_effect = CalledProcessError(999, "Non-zero return value")

        log = ciftify.config.get_git_log(self.path)

        assert not log

    @patch('subprocess.check_output')
    def test_adds_file_name_when_given(self, mock_proc):
        fname = 'some-file-name'
        log = ciftify.config.get_git_log(self.path, fname)

        assert mock_proc.call_count == 1
        git_cmd = mock_proc.call_args_list[0][0][0]
        assert '--follow {}'.format(fname) in git_cmd
