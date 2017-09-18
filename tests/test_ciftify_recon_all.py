#!/usr/bin/env python
import unittest
import logging
import importlib
import copy
import os

from mock import patch
from nose.tools import raises

logging.disable(logging.CRITICAL)

fs2hcp = importlib.import_module('ciftify.bin.fs2hcp')

class ConvertFreesurferSurface(unittest.TestCase):
    meshes = fs2hcp.define_meshes('/somewhere/hcp/subject_1',
            "164", ["32"], '/tmp/temp_dir', False)

    @patch('ciftify.bin.fs2hcp.run')
    def test_secondary_type_option_adds_to_set_structure_command(self, mock_run):
        secondary_type = 'GRAY_WHITE'
        fs2hcp.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
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

    @patch('ciftify.bin.fs2hcp.run')
    def test_secondary_type_not_set_if_option_not_used(self, mock_run):
        fs2hcp.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
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

    @patch('ciftify.bin.fs2hcp.run')
    def test_wbcommand_surface_apply_affine_called_when_cras_option_set(self,
            mock_run):
        cras_file = '/somewhere/cras.mat'
        fs2hcp.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
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

    @patch('ciftify.bin.fs2hcp.run')
    def test_no_wbcommand_added_when_cras_option_not_set(self, mock_run):
        fs2hcp.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
                '/somewhere/freesurfer/subject_1', self.meshes['T1wNative'])

        assert mock_run.call_count >= 1
        arg_list = mock_run.call_args_list

        surface_apply_calls = 0
        for item in arg_list:
            args = item[0][0]
            if '-surface-apply-affine' in args:
                surface_apply_calls += 1

        assert surface_apply_calls == 0

    @patch('ciftify.bin.fs2hcp.run')
    def test_add_to_spec_option_adds_wbcommand_call(self, mock_run):
        fs2hcp.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
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

    @patch('ciftify.bin.fs2hcp.run')
    def test_add_to_spec_option_not_present_when_option_not_set(self, mock_run):
        fs2hcp.convert_freesurfer_surface('subject_1', 'white', 'ANATOMICAL',
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
    @patch('ciftify.bin.fs2hcp.run_MSMSulc_registration')
    @patch('ciftify.bin.fs2hcp.run_fs_reg_LR')
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

        reg_sphere = fs2hcp.create_reg_sphere(settings, subject_id, meshes)
        assert reg_sphere is not None

        # Test reg_sphere set when in MSMSulc mode
        settings = Settings('MSMSulc')
        reg_sphere = fs2hcp.create_reg_sphere(settings, subject_id, meshes)
        assert reg_sphere is not None

class CopyAtlasRoiFromTemplate(unittest.TestCase):

    @patch('ciftify.bin.fs2hcp.link_to_template_file')
    def test_does_nothing_when_roi_src_does_not_exist(self, mock_link):
        hcp_dir = '/somepath/hcp'
        hcp_templates_dir = '/someotherpath/ciftify/data'
        mesh_settings = {'meshname' : 'some_mesh'}
        subject_id = 'some_id'

        fs2hcp.copy_atlas_roi_from_template(hcp_dir, hcp_templates_dir,
                subject_id, mesh_settings)

        assert mock_link.call_count == 0

class DilateAndMaskMetric(unittest.TestCase):
    @patch('ciftify.bin.fs2hcp.run')
    def test_does_nothing_when_dscalars_map_doesnt_mask_medial_wall(self,
            mock_run):
        # Stubs to allow testing
        dscalars = {'some_map' : {'mask_medialwall' : False}}
        mesh = {'tmpdir' : '/tmp/temp_dir',
                'meshname' : 'some_mesh'}
        fs2hcp.dilate_and_mask_metric('some_id', mesh, dscalars)

        assert mock_run.call_count == 0

class TestSettings(unittest.TestCase):
    arguments = {'--hcp-data-dir' : '/somepath/pipelines/hcp',
                 '--fs-subjects-dir' : '/somepath/pipelines/freesurfer',
                 '--resample-LowRestoNative' : False,
                 '<Subject>' : 'STUDY_SITE_ID_01',
                 '--settings-yaml' : None,
                 '--T2': False,
                 '--MSMSulc': False,
                 '--MSM-config': None}

    yaml_config = {'high_res' : "164",
            'low_res' : ["32"],
            'grayord_res' : [2],
            'dscalars' : {},
            'registration' : {'src_dir' : 'T1w',
                              'dest_dir' : 'MNINonLinear',
                              'xfms_dir' : 'MNINonLinear/xfms'},
            'FSL_fnirt' : {'2mm' : {'FNIRTConfig' : 'etc/flirtsch/T1_2_MNI152_2mm.cnf'}}}

    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_fs_root_dir_set_to_user_value_when_given(self, mock_ciftify,
            mock_fsl, mock_exists):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to the mock directories not
        # existing.
        mock_exists.return_value = True

        settings = fs2hcp.Settings(self.arguments)

        assert settings.fs_root_dir == self.arguments['--fs-subjects-dir']

    @raises(SystemExit)
    @patch('ciftify.config.find_freesurfer_data')
    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_exits_when_no_fs_dir_given_and_cannot_find_shell_value(self,
            mock_ciftify, mock_fsl, mock_exists, mock_fs):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to the mock directories not
        # existing.
        mock_exists.return_value = True

        # work with a deep copy of arguments to avoid modifications having any
        # effect on later tests
        args_copy = copy.deepcopy(self.arguments)
        args_copy['--fs-subjects-dir'] = None
        # Just in case the shell environment has the variable set...
        mock_fs.return_value = None

        settings = fs2hcp.Settings(args_copy)
        # Should never reach this line
        assert False

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
        settings = fs2hcp.Settings(self.arguments)
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
        settings = fs2hcp.Settings(self.arguments)
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
        settings = fs2hcp.Settings(self.arguments)
        assert False

    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_default_config_read_when_no_config_yaml_given(self,
            mock_ciftify, mock_fsl, mock_exists):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to mock directories not
        # existing.
        mock_exists.return_value = True

        settings = fs2hcp.Settings(self.arguments)
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
        args_copy['--settings-yaml'] = yaml_file

        settings = fs2hcp.Settings(args_copy)
        assert False

    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_dscalars_doesnt_contain_msmsulc_settings_when_reg_name_is_FS(
            self, mock_ciftify, mock_fsl, mock_exists):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to mock directories not
        # existing.
        mock_exists.return_value = True

        settings = fs2hcp.Settings(self.arguments)

        if settings.reg_name == 'FS':
            assert 'ArealDistortion_MSMSulc' not in settings.dscalars.keys()
        else:
            assert True

    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_msm_config_set_to_none_in_fs_mode(self, mock_ciftify, mock_fsl,
            mock_exists):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to mock directories not
        # existing.
        mock_exists.return_value = True

        settings = fs2hcp.Settings(self.arguments)

        assert settings.msm_config is None

    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_msm_config_set_to_default_when_user_config_not_given(self,
            mock_ciftify, mock_fsl, mock_exists):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'
        # This is to avoid sys.exit calls due to mock directories not
        # existing.
        mock_exists.return_value = True

        # Modify copy of arguments, so changes dont effect other tests
        args = copy.deepcopy(self.arguments)
        args['--MSMSulc'] = True
        args['--MSM-config'] = None
        settings = fs2hcp.Settings(args)

        assert settings.msm_config is not None

    @raises(SystemExit)
    @patch('os.path.exists')
    @patch('ciftify.config.find_fsl')
    @patch('ciftify.config.find_ciftify_global')
    def test_sys_exit_raised_when_user_msm_config_doesnt_exist(self, mock_ciftify,
            mock_fsl, mock_exists):
        # This is to avoid test failure if shell environment changes
        mock_ciftify.return_value = '/somepath/ciftify/data'
        mock_fsl.return_value = '/somepath/FSL'

        user_config = "/some/path/nonexistent_config"

        mock_exists.side_effect = lambda path: False if path == user_config else True

        args = copy.deepcopy(self.arguments)
        args['--MSMSulc'] = True
        args['--MSM-config'] = user_config

        settings = fs2hcp.Settings(args)
        # Test should never reach this line
        assert False

    @raises(SystemExit)
    @patch('ciftify.bin.fs2hcp.Settings._Settings__read_settings')
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

        settings = fs2hcp.Settings(self.arguments)
        assert False

    @raises(SystemExit)
    @patch('ciftify.bin.fs2hcp.Settings._Settings__read_settings')
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

        settings = fs2hcp.Settings(self.arguments)
        assert False

    @raises(SystemExit)
    @patch('ciftify.bin.fs2hcp.Settings._Settings__read_settings')
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

        settings = fs2hcp.Settings(self.arguments)
        assert False
