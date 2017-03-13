#!/usr/bin/env python
import os
import unittest
import logging
import shutil

from nose.tools import raises
from mock import patch

import ciftify.utilities as utilities

logging.disable(logging.CRITICAL)

class TestGetSubj(unittest.TestCase):
    path = '/some/path/somewhere'

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
        mock_walk.return_value.next.return_value = walk

        subjects = utilities.get_subj(self.path)

        assert subjects == []

    @patch('os.path.exists')
    @patch('os.walk')
    def test_hidden_folders_removed_from_subject_list(self, mock_walk,
            mock_exists):
        mock_exists.return_value = True
        walk = (self.path, ['subject1', '.git', 'subject2', '.hidden2'], [])
        mock_walk.return_value.next.return_value = walk

        subjects = utilities.get_subj(self.path)

        assert sorted(subjects) == sorted(['subject1', 'subject2'])

class TestDetermineFiletype(unittest.TestCase):

    def test_recognizes_dtseries(self):
        file_name = "subject1_data.dtseries.nii"

        mr_type, mr_base = utilities.determine_filetype(file_name)

        assert mr_type == 'cifti'
        assert mr_base == 'subject1_data'

    def test_recognizes_dscalar(self):
        file_name = "subject1_data.dscalar.nii"

        mr_type, mr_base = utilities.determine_filetype(file_name)

        assert mr_type == 'cifti'
        assert mr_base == 'subject1_data'

    def test_recognizes_dlabel(self):
        file_name = "subject1_data.dlabel.nii"

        mr_type, mr_base = utilities.determine_filetype(file_name)

        assert mr_type == 'cifti'
        assert mr_base == 'subject1_data'

    def test_recognizes_nifti(self):
        file1 = "subject1_data.nii"
        file2 = "subject1_data.nii.gz"

        mr_type1, mr_base1 = utilities.determine_filetype(file1)
        mr_type2, mr_base2 = utilities.determine_filetype(file2)

        assert mr_type1 == 'nifti'
        assert mr_type2 == 'nifti'
        assert mr_base1 == mr_base2

    def test_recognizes_gifti_files(self):
        gifti1 = 'subject1_data.shape.gii'
        gifti2 = 'subject1_data.func.gii'
        gifti3 = 'subject1_data.surf.gii'
        gifti4 = 'subject1_data.label.gii'
        gifti5 = 'subject1_data.gii'

        giftis = [gifti1, gifti2, gifti3, gifti4, gifti5]

        for gifti_type in giftis:
            mr_type, mr_base = utilities.determine_filetype(gifti_type)
            assert mr_type == 'gifti'
            assert mr_base == 'subject1_data'

    def test_doesnt_mangle_dot_delimited_file_names(self):
        dot_name1 = 'subject.aparc.dlabel.nii'
        dot_name2 = 'subject.R.pial.gii'

        mr_type1, mr_base1 = utilities.determine_filetype(dot_name1)
        mr_type2, mr_base2 = utilities.determine_filetype(dot_name2)

        assert mr_type1 == 'cifti'
        assert mr_base1 == 'subject.aparc'
        assert mr_type2 == 'gifti'
        assert mr_base2 == 'subject.R.pial'

    def test_returns_basename_even_when_full_path_given(self):
        file_name = '/some/path/subject1_data.dlabel.nii'

        mr_type, mr_base = utilities.determine_filetype(file_name)

        assert mr_type == 'cifti'
        assert mr_base == 'subject1_data'

    @raises(TypeError)
    def test_raises_exception_with_unrecognized_filetype(self):
        file_name = 'subject1_data.txt'

        mr_type, mr_base = utilities.determine_filetype(file_name)

class TestLoadNii(unittest.TestCase):

    @raises(SystemExit)
    def test_exits_gracefully_if_nifti_cannot_be_read(self):
        path = '/some/path/fake_nifti.nii.gz'

        utilities.loadnii(path)

        # Should never reach here
        assert False

class TestLoadCifti(unittest.TestCase):

    @raises(SystemExit)
    def test_exits_gracefully_if_cifti_cannot_be_read(self):
        path = '/some/path/subject.data.dscalar.nii'

        utilities.loadcifti(path)
        assert False

class TestLoadGiiData(unittest.TestCase):

    @raises(SystemExit)
    def test_exits_gracefully_if_gifti_cannot_be_read(self):
        path = '/some/path/subject.data.shape.gii'

        utilities.load_gii_data(path)
        assert False

class TestDoCmd(unittest.TestCase):

    @patch('subprocess.call')
    def test_dry_run_prevents_command_from_executing(self, mock_call):
        cmd = ['touch ./test_empty_file.txt']
        utilities.docmd(cmd, dry_run=True)

        assert mock_call.call_count == 0

    @patch('subprocess.call')
    def test_handles_nonstring_arguments_in_command_list(self, mock_call):
        cmd = ['chmod', 775, './fake_file.txt']
        utilities.docmd(cmd)

        assert mock_call.call_count == 1

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

class TestTempSceneDir(unittest.TestCase):

    test_path = os.path.dirname(os.path.abspath(__file__))
    subject = 'subject_1'
    expected_path = os.path.join(test_path, "scene{}".format(subject))

    def tearDown(self):
        if os.path.exists(self.expected_path):
            shutil.rmtree(self.expected_path)

    def test_temp_dir_made_at_expected_location(self):
        with utilities.TempSceneDir(self.test_path, self.subject) as temp:
            assert temp == self.expected_path
            assert os.path.exists(temp)

    def test_temp_scene_dir_removed_when_assertion_occurs(self):
        try:
            with utilities.TempSceneDir(self.test_path, self.subject) as temp:
                assert os.path.exists(self.expected_path)
                raise Exception()
        except:
            pass
        assert not os.path.exists(self.expected_path)

class TestHCPSettings(unittest.TestCase):

    def setUp(self):
        hcp_dir = os.getenv('HCP_DATA')
        if hcp_dir is not None:
            del os.environ['HCP_DATA']

    @raises(SystemExit)
    def test_exits_gracefully_if_no_hcp_dir_can_be_found(self):
        args = {}
        settings = utilities.HCPSettings(args)

class TestRun(unittest.TestCase):

    @patch('subprocess.Popen')
    def test_dry_run_prevents_command_from_running(self, mock_popen):
        mock_popen.return_value.communicate.return_value = ('', '')
        mock_popen.return_value.returncode = 0

        utilities.run('touch ./test_file.txt', dryrun=True)

        assert mock_popen.call_count == 0

    @patch('subprocess.Popen')
    def test_handles_string_commands(self, mock_popen):
        mock_popen.return_value.communicate.return_value = ('', '')
        mock_popen.return_value.returncode = 0
        cmd = 'touch ./test_file.txt'

        utilities.run(cmd)

        assert mock_popen.call_count == 1
        # First item in list, first argument in tuple format,
        # first item of this tuple
        assert mock_popen.call_args_list[0][0][0] == cmd

    @patch('subprocess.Popen')
    def test_handles_list_commands(self, mock_popen):
        mock_popen.return_value.communicate.return_value = ('', '')
        mock_popen.return_value.returncode = 0
        cmd = ['touch', './test_file.txt']

        utilities.run(cmd)

        assert mock_popen.call_count == 1
        assert mock_popen.call_args_list[0][0][0] == " ".join(cmd)
