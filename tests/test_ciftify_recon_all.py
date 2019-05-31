#!/usr/bin/env python3
import unittest
import logging
import importlib
import copy
import os
from docopt import docopt

from unittest.mock import patch
import pytest
import ciftify.utils

logging.disable(logging.CRITICAL)

ciftify_recon_all = importlib.import_module('ciftify.bin.ciftify_recon_all')

class ConvertFreesurferSurface(unittest.TestCase):
    meshes = ciftify_recon_all.define_meshes('/somewhere/hcp/subject_1',
            "164", ["32"], '/tmp/temp_dir', False)

    @patch('ciftify.bin.ciftify_recon_all.run')
    def test_secondary_type_option_adds_to_set_structure_command(self, mock_run):
        secondary_type = 'GRAY_WHITE'
        ciftify_recon_all.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
                '/somewhere/freesurfer/subject_1', self.meshes['T1wNative'],
                surface_secondary_type=secondary_type)

        assert mock_run.call_count >= 1
        arg_list = mock_run.call_args_list

        set_structure_present = False
        for item in arg_list:
            args = item[0][0]
            if '-set-structure' in args:
                set_structure_present = True
                assert '-surface-secondary-type' in args
                assert secondary_type in args
        # If this fails the wb_command -set-structure call is not being made
        # at all. Is expected at least once regardless of secondary-type option
        assert set_structure_present

    @patch('ciftify.bin.ciftify_recon_all.run')
    def test_secondary_type_not_set_if_option_not_used(self, mock_run):
        ciftify_recon_all.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
                '/somewhere/freesurfer/subject_1', self.meshes['T1wNative'])

        assert mock_run.call_count >= 1
        arg_list = mock_run.call_args_list

        set_structure_present = False
        for item in arg_list:
            args = item[0][0]
            if '-set-structure' in args:
                set_structure_present = True
                assert '-surface-secondary-type' not in args
        # If this fails the wb_command -set-structure call is not being made
        # at all. Is expected at least once regardless of secondary-type option
        assert set_structure_present

    @patch('ciftify.bin.ciftify_recon_all.run')
    def test_wbcommand_surface_apply_affine_called_when_cras_option_set(self,
            mock_run):
        cras_file = '/somewhere/cras.mat'
        ciftify_recon_all.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
                '/somewhere/freesurfer/subject_1', self.meshes['T1wNative'],
                cras_mat=cras_file)

        assert mock_run.call_count >= 1
        arg_list = mock_run.call_args_list

        surface_apply_calls = 0
        for item in arg_list:
            args = item[0][0]
            if '-surface-apply-affine' in args and cras_file in args:
                surface_apply_calls += 1
        # The wb_command -surface-apply-affine command should be run once for
        # each hemisphere
        assert surface_apply_calls == 2

    @patch('ciftify.bin.ciftify_recon_all.run')
    def test_no_wbcommand_added_when_cras_option_not_set(self, mock_run):
        ciftify_recon_all.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
                '/somewhere/freesurfer/subject_1', self.meshes['T1wNative'])

        assert mock_run.call_count >= 1
        arg_list = mock_run.call_args_list

        surface_apply_calls = 0
        for item in arg_list:
            args = item[0][0]
            if '-surface-apply-affine' in args:
                surface_apply_calls += 1

        assert surface_apply_calls == 0

    @patch('ciftify.bin.ciftify_recon_all.run')
    def test_add_to_spec_option_adds_wbcommand_call(self, mock_run):
        ciftify_recon_all.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
                '/somewhere/freesurfer/subject_1', self.meshes['T1wNative'],
                add_to_spec=True)

        assert mock_run.call_count >= 1
        arg_list = mock_run.call_args_list

        spec_added_calls = 0
        for item in arg_list:
            args = item[0][0]
            if '-add-to-spec-file' in args:
                spec_added_calls += 1
        # Should add one call for each hemisphere
        assert spec_added_calls == 2

    @patch('ciftify.bin.ciftify_recon_all.run')
    def test_add_to_spec_option_not_present_when_option_not_set(self, mock_run):
        ciftify_recon_all.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
                '/somewhere/freesurfer/subject_1', self.meshes['T1wNative'],
                add_to_spec=False)

        assert mock_run.call_count >= 1
        arg_list = mock_run.call_args_list

        spec_added_calls = 0
        for item in arg_list:
            args = item[0][0]
            if '-add-to-spec-file' in args:
                spec_added_calls += 1
        assert spec_added_calls == 0

class CreateRegSphere(unittest.TestCase):
    @patch('ciftify.bin.ciftify_recon_all.run_MSMSulc_registration')
    @patch('ciftify.bin.ciftify_recon_all.run_fs_reg_LR')
    def test_reg_sphere_is_not_set_to_none_for_any_mode(self, mock_fs_reg,
            mock_msm_reg):
        """
        Should fail if MSMSulc registration is implemented without supplying a
        value for reg_sphere
        """
        # settings stub, to allow tests to be written.
        class Settings(object):
            def __init__(self, name):
                self.high_res = 999
                self.reg_name = name
                self.ciftify_data_dir = '/somedir/'
                self.msm_config = None

        # Test reg_sphere set when in FS mode
        settings = Settings('FS')
        meshes = {'AtlasSpaceNative' : ''}
        subject_id = 'some_id'

        reg_sphere = ciftify_recon_all.create_reg_sphere(settings, subject_id, meshes)
        assert reg_sphere is not None

        # Test reg_sphere set when in MSMSulc mode
        settings = Settings('MSMSulc')
        reg_sphere = ciftify_recon_all.create_reg_sphere(settings, subject_id, meshes)
        assert reg_sphere is not None

class CopyAtlasRoiFromTemplate(unittest.TestCase):

    @patch('ciftify.bin.ciftify_recon_all.link_to_template_file')
    def test_does_nothing_when_roi_src_does_not_exist(self, mock_link):
        class Settings(object):
            def __init__(self):
                self.subject = self.Subject()
                self.ciftify_data_dir = '/someotherpath/ciftify/data'
                self.work_dir = '/somepath/hcp'

            class Subject(object):
                def __init__(self):
                    id = 'some_id'

        settings = Settings()
        mesh_settings = {'meshname' : 'some_mesh'}

        ciftify_recon_all.copy_atlas_roi_from_template(settings, mesh_settings)

        assert mock_link.call_count == 0

class DilateAndMaskMetric(unittest.TestCase):
    @patch('ciftify.bin.ciftify_recon_all.run')
    def test_does_nothing_when_dscalars_map_doesnt_mask_medial_wall(self,
            mock_run):
        # Stubs to allow testing
        dscalars = {'some_map' : {'mask_medialwall' : False}}
        mesh = {'tmpdir' : '/tmp/temp_dir',
                'meshname' : 'some_mesh'}
        ciftify_recon_all.dilate_and_mask_metric('some_id', mesh, dscalars)

        assert mock_run.call_count == 0

@patch('os.makedirs')
@patch('ciftify.config.find_fsl')
class TestSettings(unittest.TestCase):

    arguments = docopt(ciftify_recon_all.__doc__,
     '--hcp-data-dir /somepath/pipelines/hcp --fs-subjects-dir /somepath/pipelines/freesurfer --surf-reg FS STUDY_SITE_ID_01')

    subworkdir = '/somepath/pipelines/hcp/STUDY_SITE_ID_01'
    yaml_config = {'high_res' : "164",
            'low_res' : ["32"],
            'grayord_res' : [2],
            'dscalars' : {},
            'registration' : {'src_dir' : 'T1w',
                              'dest_dir' : 'MNINonLinear',
                              'xfms_dir' : 'MNINonLinear/xfms'},
            'FSL_fnirt' : {'2mm' : {'FNIRTConfig' : 'etc/flirtsch/T1_2_MNI152_2mm.cnf'}}}

    def set_mock_env(self, mock_ciftify, mock_fsl, mock_makedirs):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'

    @patch('ciftify.config.find_ciftify_global')
    @patch('ciftify.bin.ciftify_recon_all.WorkFlowSettings._WorkFlowSettings__read_settings')
    @patch('os.path.exists')
    def test_fs_root_dir_set_to_user_value_when_given(self, mock_exists,
            mock_settings, mock_ciftify, mock_fsl, mock_makedirs):
        self.set_mock_env(mock_ciftify, mock_fsl, mock_makedirs)
        mock_exists.side_effect = lambda path: False if path == self.subworkdir else True
        mock_settings.return_value = self.yaml_config

        settings = ciftify_recon_all.Settings(self.arguments)

        assert settings.fs_root_dir == self.arguments['--fs-subjects-dir']


    @patch('ciftify.config.find_ciftify_global')
    @patch('ciftify.config.find_freesurfer_data')
    @patch('os.path.exists')
    def test_exits_when_no_fs_dir_given_and_cannot_find_shell_value(self,
            mock_exists, mock_fs, mock_ciftify, mock_fsl, mock_makedirs):
        self.set_mock_env(mock_ciftify, mock_fsl, mock_makedirs)
        # This is to avoid sys.exit calls due to the mock directories not
        # existing.
        mock_exists.return_value = True

        # work with a deep copy of arguments to avoid modifications having any
        # effect on later tests
        args_copy = copy.deepcopy(self.arguments)
        args_copy['--fs-subjects-dir'] = None
        # Just in case the shell environment has the variable set...
        mock_fs.return_value = None
        with pytest.raises(SystemExit):
            settings = ciftify_recon_all.Settings(args_copy)


    @patch('ciftify.config.find_ciftify_global')
    @patch('ciftify.bin.ciftify_recon_all.WorkFlowSettings._WorkFlowSettings__read_settings')
    @patch('os.path.exists')
    def test_dscalars_doesnt_contain_msmsulc_settings_when_reg_name_is_FS(
            self, mock_exists, mock_yaml_settings, mock_ciftify, mock_fsl,
            mock_makedirs):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to mock directories not
        # existing.
        mock_exists.side_effect = lambda path: False if path == self.subworkdir else True
        mock_yaml_settings.return_value = self.yaml_config

        settings = ciftify_recon_all.Settings(self.arguments)

        if settings.reg_name == 'FS':
            assert 'ArealDistortion_MSMSulc' not in settings.dscalars.keys()
        else:
            assert True

    @patch('ciftify.config.find_ciftify_global')
    @patch('ciftify.bin.ciftify_recon_all.WorkFlowSettings._WorkFlowSettings__read_settings')
    @patch('os.path.exists')
    def test_msm_config_set_to_none_in_fs_mode(self, mock_exists,
            mock_yaml_settings, mock_ciftify, mock_fsl, mock_makedirs):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to mock directories not
        # existing.
        mock_exists.side_effect = lambda path: False if path == self.subworkdir else True
        mock_yaml_settings.return_value = self.yaml_config
        args_copy = copy.deepcopy(self.arguments)
        args_copy['--surf-reg'] = "FS"
        settings = ciftify_recon_all.Settings(self.arguments)

        assert settings.msm_config is None

    @patch('ciftify.config.find_ciftify_global')
    @patch('ciftify.config.verify_msm_available')
    @patch('ciftify.bin.ciftify_recon_all.Settings.check_msm_config', return_value = True)
    @patch('ciftify.bin.ciftify_recon_all.WorkFlowSettings._WorkFlowSettings__read_settings')
    @patch('os.path.exists')
    def test_msm_config_set_to_default_when_user_config_not_given(self,
            mock_exists, mock_yaml_settings, mock_msm_check, mock_msm_check1,
            mock_ciftify, mock_fsl, mock_makedirs):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to mock directories not
        # existing.
        mock_exists.side_effect = lambda path: False if path == self.subworkdir else True
        mock_yaml_settings.return_value = self.yaml_config

        # Modify copy of arguments, so changes dont effect other tests
        args = copy.deepcopy(self.arguments)
        args['--surf-reg'] = 'MSMSulc'
        args['--MSM-config'] = None
        settings = ciftify_recon_all.Settings(args)

        assert settings.msm_config is not None

    @patch('ciftify.config.find_ciftify_global')
    @patch('os.path.exists')
    def test_sys_exit_raised_when_user_msm_config_doesnt_exist(self, mock_exists,
            mock_ciftify, mock_fsl, mock_makedirs):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'

        user_config = "/some/path/nonexistent_config"

        mock_exists.side_effect = lambda path: False if path == user_config else True

        args = copy.deepcopy(self.arguments)
        args['--surf-reg'] = 'MSMSulc'
        args['--MSM-config'] = user_config

        with pytest.raises(SystemExit):
            settings = ciftify_recon_all.Settings(args)


    @patch('ciftify.config.find_ciftify_global')
    @patch('os.path.exists')
    def test_sys_exit_raised_when_nonlin_xfm_given_alone(self, mock_exists,
            mock_ciftify, mock_fsl, mock_makedirs):
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        mock_exists.side_effect = lambda path: False if path == self.subworkdir else True
        args = copy.deepcopy(self.arguments)
        args['--read-non-lin-xfm'] = '/some/file'
        with pytest.raises(SystemExit):
            settings = ciftify_recon_all.Settings(args)


    @patch('ciftify.config.find_ciftify_global')
    @patch('os.path.exists')
    def test_sys_exit_raised_when_lin_xfm_given_alone(self, mock_exists,
            mock_ciftify, mock_fsl, mock_makedirs):
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        mock_exists.side_effect = lambda path: False if path == self.subworkdir else True
        args = copy.deepcopy(self.arguments)
        args['--read-lin-premat'] = '/some/file'
        with pytest.raises(SystemExit):
            settings = ciftify_recon_all.Settings(args)


    @patch('ciftify.utils.check_input_readable')
    @patch('os.path.exists')
    def test_xfms_set_if_given(self, mock_exists, mock_inputreadble,
            mock_fsl, mock_makedirs):
        mock_fsl.return_value = '/somepath/FSL'
        mock_exists.side_effect = lambda path: False if path == self.subworkdir else True
        args = copy.deepcopy(self.arguments)
        args['--read-lin-premat'] = '/some/file1'
        args['--read-non-lin-xfm'] = '/some/file2'
        settings = ciftify_recon_all.Settings(args)
        # Test should never reach this line
        assert settings.registration['User_AtlasTransform_Linear'] == '/some/file1'
        assert settings.registration['User_AtlasTransform_NonLinear'] == '/some/file2'
