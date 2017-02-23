import unittest
import logging
import importlib

from mock import patch

logging.disable(logging.CRITICAL)

fs2hcp = importlib.import_module('bin.fs2hcp')

class ConvertFreesurferSurface(unittest.TestCase):
    meshes = fs2hcp.define_meshes('/somewhere/hcp/subject_1',
            "164", ["32"], '/tmp/temp_dir', False)

    @patch('bin.fs2hcp.run')
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

    @patch('bin.fs2hcp.run')
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

    @patch('bin.fs2hcp.run')
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

    @patch('bin.fs2hcp.run')
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

    @patch('bin.fs2hcp.run')
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

    @patch('bin.fs2hcp.run')
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
    @patch('bin.fs2hcp.run_fs_reg_LR')
    def test_reg_sphere_is_not_none(self, mock_fs_reg):
        """
        This test is meant to start failing if the MSMSulc registration is
        implemented without supplying a value for reg_sphere
        """
        # settings stub, to allow tests to be written.
        class Settings(object):
            def __init__(self, name):
                self.high_res = 999
                self.reg_name = name
        settings = Settings('FS')
        meshes = {'AtlasSpaceNative' : ''}

        reg_sphere = fs2hcp.create_reg_sphere(settings, meshes)
        assert reg_sphere is not None

        settings = Settings('MSMSulc')
        try:
            reg_sphere = fs2hcp.create_reg_sphere(settings, meshes)
        except SystemExit:
            # MSMSulc has not been implemented, no value need be returned
            assert True
        assert reg_sphere is not None

class CopyAtlasRoiFromTemplate(unittest.TestCase):

    @patch('bin.fs2hcp.link_to_template_file')
    def test_does_nothing_when_roi_src_does_not_exist(self, mock_link):
        hcp_dir = '/somepath/hcp'
        hcp_templates_dir = '/someotherpath/ciftify/data'
        mesh_settings = {'meshname' : 'some_mesh'}
        subject_id = 'some_id'

        fs2hcp.copy_atlas_roi_from_template(hcp_dir, hcp_templates_dir,
                subject_id, mesh_settings)

        assert mock_link.call_count == 0

class DilateAndMaskMetric(unittest.TestCase):
    @patch('bin.fs2hcp.run')
    def test_does_nothing_when_dscalars_map_doesnt_mask_medial_wall(self,
            mock_run):
        # Stubs to allow testing
        dscalars = {'some_map' : {'mask_medialwall' : False}}
        mesh = {'tmpdir' : '/tmp/temp_dir',
                'meshname' : 'some_mesh'}
        fs2hcp.dilate_and_mask_metric('some_id', mesh, dscalars)

        assert mock_run.call_count == 0
