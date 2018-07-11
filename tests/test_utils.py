#!/usr/bin/env python
import os
import unittest
import logging
import shutil
import random
import copy

from nose.tools import raises
from mock import patch

import ciftify.utils as utilities

logging.disable(logging.CRITICAL)

class TestGetSubj(unittest.TestCase):
    path = '/some/path/somewhere'

    @patch('os.path.exists')
    @patch('os.walk')
    def test_all_subjects_returned(self, mock_walk, mock_exists):
        # Set up list of subjects with different site tags
        all_subjects = ['STUDY_CMH_0000_01', 'STUDY_CMH_9999_01',
                    'STUDY_CMH_1234_01', 'STUDY_MRP_1234_01',
                    'STUDY_MRP_0001_01']
        random.shuffle(all_subjects)

        # Set up mocks
        mock_exists.return_value = True
        walk = (self.path, all_subjects, [])
        mock_walk.return_value.__next__.return_value = walk

        subjects = list(utilities.get_subj(self.path))

        # Subjects must be wrapped in list call because py3 returns a generator
        assert sorted(list(subjects)) == sorted(all_subjects)

    def test_returns_empty_list_if_path_doesnt_exist(self):
        assert not os.path.exists(self.path)

        subjects = utilities.get_subj(self.path)
        assert subjects == []

    @patch('os.path.exists')
    @patch('os.walk')
    def test_doesnt_crash_when_no_subjects_found(self, mock_walk, mock_exists):
        # Pretend the path exists, but is empty dir
        mock_exists.return_value = True
        walk = (self.path, [], [])
        mock_walk.return_value.__next__.return_value = walk

        subjects = list(utilities.get_subj(self.path))

        assert subjects == []

    @patch('os.path.exists')
    @patch('os.walk')
    def test_hidden_folders_removed_from_subject_list(self, mock_walk,
            mock_exists):
        mock_exists.return_value = True
        walk = (self.path, ['subject1', '.git', 'subject2', '.hidden2'], [])
        mock_walk.return_value.__next__.return_value = walk

        subjects = utilities.get_subj(self.path)

        assert sorted(list(subjects)) == sorted(['subject1', 'subject2'])

    @patch('os.path.exists')
    @patch('os.walk')
    def test_user_filter_removes_tagged_subjects(self, mock_walk, mock_exists):
        # Set up list of tagged and untagged subjects
        tagged_subjects = ['STUDY_CMH_0000_01', 'STUDY_CMH_9999_01',
                    'STUDY_CMH_1234_01']
        all_subjects = ['STUDY_MRP_1234_01', 'STUDY_MRP_0001_01']
        all_subjects.extend(tagged_subjects)
        random.shuffle(all_subjects)

        # Set up mocks
        mock_exists.return_value = True
        walk = (self.path, all_subjects, [])
        mock_walk.return_value.__next__.return_value = walk

        subjects = list(utilities.get_subj(self.path, user_filter='CMH'))

        assert len(subjects) == len(tagged_subjects)
        for item in tagged_subjects:
            assert item in subjects

class TestMakeDir(unittest.TestCase):
    path = '/some/path/somewhere'

    @patch('os.makedirs')
    def test_dry_run_prevents_dir_from_being_made(self, mock_makedirs):
        utilities.make_dir(self.path, dry_run=True)

        assert mock_makedirs.call_count == 0

    @patch('os.makedirs')
    def test_doesnt_crash_if_directory_exists(self, mock_makedirs):
        mock_makedirs.side_effect = OSError(17, "File exists")

        utilities.make_dir(self.path)

        assert mock_makedirs.call_count == 1

class TestTempDir(unittest.TestCase):

    def tearDown(self):
        # In case the test fails and leaves behind a temp dir
        if os.path.exists(self.path):
            shutil.rmtree(self.path)

    def test_temp_dir_removed_when_exception_occurs(self):
        try:
            with utilities.TempDir() as temp:
                self.path = temp
                assert os.path.exists(self.path)
                raise Exception()
        except:
            pass
        assert not os.path.exists(self.path)

class TestWorkDirSettings(unittest.TestCase):

    def setUp(self):
        hcp_dir = os.getenv('HCP_DATA')
        if hcp_dir is not None:
            del os.environ['HCP_DATA']

    @raises(SystemExit)
    def test_exits_gracefully_if_no_hcp_dir_can_be_found(self):
        args = {}
        settings = utilities.WorkDirSettings(args)

class TestRun(unittest.TestCase):

    @patch('subprocess.Popen')
    def test_dry_run_prevents_command_from_running(self, mock_popen):
        mock_popen.return_value.communicate.return_value = (b'', b'')
        mock_popen.return_value.returncode = 0

        utilities.run('touch ./test_file.txt', dryrun=True)

        assert mock_popen.call_count == 0

    @patch('subprocess.Popen')
    def test_handles_string_commands(self, mock_popen):
        mock_popen.return_value.communicate.return_value = (b'', b'')
        mock_popen.return_value.returncode = 0
        cmd = 'touch ./test_file.txt'

        utilities.run(cmd)

        assert mock_popen.call_count == 1
        # First item in list, first argument in tuple format,
        # first item of this tuple
        assert mock_popen.call_args_list[0][0][0] == cmd

    @patch('subprocess.Popen')
    def test_handles_list_commands(self, mock_popen):
        mock_popen.return_value.communicate.return_value = (b'', b'')
        mock_popen.return_value.returncode = 0
        cmd = ['touch', './test_file.txt']

        utilities.run(cmd)

        assert mock_popen.call_count == 1
        assert mock_popen.call_args_list[0][0][0] == " ".join(cmd)

class TestCheckOutput(unittest.TestCase):

    def test_returns_unicode_string_not_bytes(self):
        """This test is to ensure python 3 compatibility (i.e. check_output
        returns bytes unless decoded) """

        output = utilities.check_output("echo")

        # decode('utf-8') == str in py3 and == unicode in py2
        assert type(output) == str or type(output) == unicode

class TestWorkFlowSettings(unittest.TestCase):
    arguments = {'--hcp-data-dir' : '/somepath/pipelines/hcp',
                 '<subject>' : 'STUDY_SITE_ID_01',
                 '--ciftify-conf' : None,
                 '--surf-reg': 'MSMSulc',
                 '--ciftify-work-dir': None,
                 '--n_cpus': None}

    yaml_config = {'high_res' : "164",
            'low_res' : ["32"],
            'grayord_res' : [2],
            'dscalars' : {},
            'registration' : {'src_dir' : 'T1w',
                              'dest_dir' : 'MNINonLinear',
                              'xfms_dir' : 'MNINonLinear/xfms'},
            'FSL_fnirt' : {'2mm' : {'FNIRTConfig' : 'etc/flirtsch/T1_2_MNI152_2mm.cnf'}}}

    @raises(SystemExit)
    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_exits_gracefully_when_fsl_dir_cannot_be_found(self, mock_ciftify,
            mock_fsl, mock_exists):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        # This is to avoid sys.exit calls due to the mock directories not
        # existing.
        mock_exists.return_value = True

        mock_fsl.return_value = None
        settings = ciftify_recon_all.Settings(self.arguments)
        # Should never reach this line
        assert False

    @raises(SystemExit)
    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_exits_gracefully_when_ciftify_data_dir_not_found(self, mock_ciftify,
            mock_fsl, mock_exists):
        # This is to avoid test failure if shell environment changes
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to the mock directories not
        # existing.
        mock_exists.return_value = True

        mock_ciftify.return_value = None
        settings = ciftify_recon_all.Settings(self.arguments)
        assert False

    @raises(SystemExit)
    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_exits_gracefully_when_ciftify_data_dir_doesnt_exist(self,
            mock_ciftify, mock_fsl, mock_exists):

        ciftify_data = '/somepath/ciftify/data'
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = ciftify_data
        mock_fsl.return_value = '/somepath/FSL'

        mock_exists.side_effect = lambda path : False if path == ciftify_data else True
        settings = ciftify_recon_all.Settings(self.arguments)
        assert False

    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    def test_default_config_read_when_no_config_yaml_given(self,
            mock_fsl, mock_exists):
        # This is to avoid test failure if shell environment changes
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to mock directories not
        # existing.
        mock_exists.side_effect = False if path == self.subworkdir else True

        settings = ciftify_recon_all.Settings(self.arguments)
        config = settings._Settings__config

        assert config is not None

    @raises(SystemExit)
    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_exits_gracefully_when_yaml_config_file_doesnt_exist(self,
            mock_ciftify, mock_fsl, mock_exists):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'

        yaml_file = '/somepath/fake_config.yaml'
        mock_exists.side_effect = lambda path: False if path == yaml_file else True
        # work with a deep copy of arguments to avoid modifications having any
        # effect on later tests
        args_copy = copy.deepcopy(self.arguments)
        args_copy['--ciftify-conf'] = yaml_file

        settings = ciftify_recon_all.Settings(args_copy)
        assert False

    @raises(SystemExit)
    @patch('ciftify.utils.WorkFlowSettings.__read_settings')
    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_exits_gracefully_when_expected_registration_path_missing(self,
            mock_ciftify, mock_fsl, mock_exists, mock_yaml_settings):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to mock directories not
        # existing.
        mock_exists.return_value = True

        # Use copy to avoid side effects in other tests
        yaml_copy = copy.deepcopy(self.yaml_config)
        del yaml_copy['registration']['src_dir']
        mock_yaml_settings.return_value = yaml_copy

        settings = ciftify_recon_all.Settings(self.arguments)
        assert False

    @raises(SystemExit)
    @patch('ciftify.utils.WorkFlowSettings.__read_settings')
    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_exits_gracefully_when_resolution_not_defined_for_given_method(self,
            mock_ciftify, mock_fsl, mock_exists, mock_yaml_settings):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to mock directories not
        # existing.
        mock_exists.return_value = True

        # Use copy to avoid side effects in other tests
        yaml_copy = copy.deepcopy(self.yaml_config)
        del yaml_copy['FSL_fnirt']['2mm']
        mock_yaml_settings.return_value = yaml_copy

        settings = ciftify_recon_all.Settings(self.arguments)
        assert False

    @raises(SystemExit)
    @patch('ciftify.utils.WorkFlowSettings.__read_settings')
    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_exits_gracefully_when_registration_resolution_file_doesnt_exist(self,
            mock_ciftify, mock_fsl, mock_exists, mock_yaml_settings):
        fsl_dir = '/somepath/FSL'
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = fsl_dir

        mock_yaml_settings.return_value = self.yaml_config
        required_file = os.path.join(os.path.dirname(fsl_dir),
                self.yaml_config['FSL_fnirt']['2mm']['FNIRTConfig'])
        mock_exists.side_effect = lambda x: False if x == required_file else True

        settings = ciftify_recon_all.Settings(self.arguments)
        assert False
