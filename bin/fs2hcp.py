#!/usr/bin/env python
"""
Converts a freesurfer recon-all output to a HCP data directory

Usage:
  func2hcp.py [options] <Subject>

Arguments:
    <Subject>               The Subject ID in the HCP data folder

Options:
  --hcp-data-dir PATH         Path to the HCP_DATA directory (overides the
                              HCP_DATA environment variable)
  --fs-subjects-dir PATH      Path to the freesurfer SUBJECTS_DIR directory
                              (overides the SUBJECTS_DIR environment variable)
  --resample-LowRestoNative   Resample the 32k Meshes to Native Space (creates
                              additional output files)
  --settings-yaml PATH        Path to a yaml configuration file. Overrides
                              the default settings in
                              ciftify/data/fs2hcp_settings.yaml
  -v,--verbose                Verbose logging
  --debug                     Debug logging in Erin's very verbose style
  -n,--dry-run                Dry run
  -h,--help                   Print help

DETAILS
Adapted from the PostFreeSurferPipeline module of the HCP Pipeline

Written by Erin W Dickie, Jan 19, 2017
"""
import os
import sys
import math
import datetime
import tempfile
import shutil
import subprocess
import logging
import yaml

from docopt import docopt

import ciftify
from ciftify.utilities import HCPSettings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class Settings(HCPSettings):
    def __init__(self, arguments):
        HCPSettings.__init__(self, arguments)
        # reg_name hard coded for now, option later? (MSMSulc)
        self.reg_name = "FS"
        self.resample = arguments["--resample-LowRestoNative"]
        self.fs_root_dir = self.__set_fs_subjects_dir(arguments)
        self.subject = self.__get_subject(arguments)
        self.FSL_dir = self.__set_FSL_dir()
        self.ciftify_data_dir = self.__get_ciftify_data()

        # Read settings from yaml
        self.__config = self.__read_settings(arguments['--settings-yaml'])
        self.high_res = self.__get_config_entry('high_res')
        self.low_res = self.__get_config_entry('low_res')
        self.grayord_res = self.__get_config_entry('grayord_res')
        self.dscalars = self.__define_dscalars()
        self.registration = self.__define_registration_settings()

    def __set_fs_subjects_dir(self, arguments):
        fs_root_dir = arguments['--fs-subjects-dir']
        if fs_root_dir:
            return fs_root_dir
        fs_root_dir = ciftify.config.find_freesurfer_data()
        if fs_root_dir is None:
            logger.error("Cannot find freesurfer subjects dir, exiting.")
            sys.exit(1)
        return fs_root_dir

    def __get_subject(self, arguments):
        subject_id = arguments['<Subject>']
        return Subject(self.hcp_dir, self.fs_root_dir, subject_id)

    def __set_FSL_dir(self):
        fsl_dir = ciftify.config.find_fsl()
        if fsl_dir is None:
            logger.error("Cannot find FSL dir, exiting.")
            sys.exit(1)
        return os.path.dirname(fsl_dir)

    def __get_ciftify_data(self):
        ciftify_data = ciftify.config.find_ciftify_global()
        if ciftify_data is None:
            logger.error("CIFTIFY_TEMPLATES shell variable not defined, exiting")
            sys.exit(1)
        if not os.path.exists(ciftify_data):
            logger.error("CIFTIFY_TEMPLATES dir {} does not exist, exiting."
                "".format(ciftify_data))
            sys.exit(1)
        return ciftify_data

    def __read_settings(self, yaml_file):
        if yaml_file is None:
            yaml_file = os.path.join(os.path.dirname(__file__),
                    '../data/fs2hcp_settings.yaml')
        if not os.path.exists(yaml_file):
            logger.critical("fs2hcp settings yaml file {} does not exist"
                "".format(yaml_file))
            sys.exit(1)

        try:
            with open(yaml_file, 'r') as yaml_stream:
                config = yaml.load(yaml_stream)
        except:
            logger.critical("Cannot read yaml config file {}, check formatting."
                    "".format(yaml_file))
            sys.exit(1)

        return config

    def __get_config_entry(self, key):
        try:
            config_entry = self.__config[key]
        except KeyError:
            logger.critical("{} not defined in fs2hcp settings".format(key))
            sys.exit(1)
        return config_entry

    def __define_dscalars(self):
        dscalars_config = self.__get_config_entry('dscalars')
        if self.reg_name != 'MSMSulc':
            try:
                del dscalars_config['ArealDistortion_MSMSulc']
            except KeyError:
                # do nothing, MSMSulc options not defined anyway
                return dscalars_config
        return dscalars_config

    def __define_registration_settings(self, method='FSL_fnirt',
            standard_res='2mm'):
        registration_config = self.__get_config_entry('registration')
        for key in ['src_dir', 'dest_dir', 'xfms_dir']:
            try:
                subfolders = registration_config[key]
            except KeyError:
                logger.critical("registration config does not contain expected"
                        "key {}".format(key))
                sys.exit(1)
            registration_config[key] = os.path.join(self.subject.path, subfolders)
        resolution_config = self.__get_resolution_config(method, standard_res)
        registration_config.update(resolution_config)
        return registration_config

    def __get_resolution_config(self, method, standard_res):
        """
        Reads the method and resolution settings.
        """
        method_config = self.__get_config_entry(method)
        try:
            resolution_config = method_config[standard_res]
        except KeyError:
            logger.error("Registration resolution {} not defined for method "
                    "{}".format(standard_res, method))
            sys.exit(1)

        for key in resolution_config.keys():
            ## The base dir (FSL_dir currently) may need to change when new
            ## resolutions/methods are added
            reg_item = os.path.join(self.FSL_dir, resolution_config[key])
            if not os.path.exists(reg_item):
                logger.error("Item required for registration does not exist: "
                        "{}".format(reg_item))
                sys.exit(1)
            resolution_config[key] = reg_item
        return resolution_config

class Subject(object):
    def __init__(self, hcp_dir, fs_root_dir, subject_id):
        self.id = subject_id
        self.path = self.__set_path(hcp_dir)
        self.fs_folder = self.__set_fs_folder(fs_root_dir)
        self.T1w_dir = os.path.join(self.path, 'T1w')
        self.atlas_space_dir = os.path.join(self.path, 'MNINonLinear')
        self.log = os.path.join(self.path, 'fs2hcp.log')

    def __set_path(self, hcp_dir):
        path = os.path.join(hcp_dir, self.id)
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                logger.error("Cannot make subject path {}, exiting"
                            "".format(path))
                sys.exit(1)
        return path

    def __set_fs_folder(self, fs_root_dir):
        fs_path = os.path.join(fs_root_dir, self.id)
        if not os.path.exists(fs_path):
            logger.error("{} freesurfer folder does not exist, exiting."
                    "".format(self.id))
            sys.exit(1)
        return fs_path

    def get_subject_log_handler(self, formatter):
        fh = logging.FileHandler(self.log)
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        return fh

def spec_file(subject_id, mesh_settings):
    '''return the formated spec_filename for this mesh'''
    specfile = os.path.join(mesh_settings['Folder'],
        "{}.{}.wb.spec".format(subject_id, mesh_settings['meshname']))
    return specfile

def metric_file(subject_id, map_name, hemisphere, mesh_settings):
    '''return the formatted file path for a metric (surface data) file for this
    mesh'''
    metric_gii = os.path.join(mesh_settings['tmpdir'],
        "{}.{}.{}.{}.shape.gii".format(subject_id, hemisphere, map_name,
        mesh_settings['meshname']))
    return metric_gii

def medial_wall_roi_file(subject_id, hemisphere, mesh_settings):
    '''
    Medial wall ROIs are the only shape.gii files that aren't temp files,
    and their name is given in the mesh_settings, so they get their own function
    '''
    roi_gii = os.path.join(mesh_settings['Folder'],
        "{}.{}.{}.{}.shape.gii".format(subject_id, hemisphere,
        mesh_settings['ROI'], mesh_settings['meshname']))
    return roi_gii

def surf_file(subject_id, surface, hemisphere, mesh_settings):
    '''return the formatted file path to a surface file '''
    surface_gii = os.path.join(mesh_settings['Folder'],
            '{}.{}.{}.{}.surf.gii'.format(subject_id, hemisphere, surface,
            mesh_settings['meshname']))
    return surface_gii

def label_file(subject_id, label_name, hemisphere, mesh_settings):
    '''return the formated file path to a label (surface data) file for this mesh'''
    label_gii = os.path.join(mesh_settings['tmpdir'],
        '{}.{}.{}.{}.label.gii'.format(subject_id, hemisphere, label_name,
        mesh_settings['meshname']))
    return label_gii

def define_meshes(subject_hcp, high_res_mesh, low_res_meshes, temp_dir,
        make_low_res):
    '''sets up a dictionary of expected paths for each mesh'''
    meshes = {
        'T1wNative':{
            'Folder' : os.path.join(subject_hcp, 'T1w', 'Native'),
            'ROI': 'roi',
            'meshname': 'native',
            'tmpdir': os.path.join(temp_dir, 'native'),
            'T1wImage': os.path.join(subject_hcp, 'T1w', 'T1w.nii.gz'),
            'DenseMapsFolder': os.path.join(subject_hcp, 'MNINonLinear', 'Native')},
        'AtlasSpaceNative':{
            'Folder' : os.path.join(subject_hcp, 'MNINonLinear', 'Native'),
            'ROI': 'roi',
            'meshname': 'native',
            'tmpdir': os.path.join(temp_dir, 'native'),
            'T1wImage': os.path.join(subject_hcp, 'MNINonLinear', 'T1w.nii.gz')},
        'HighResMesh':{
            'Folder' : os.path.join(subject_hcp, 'MNINonLinear'),
            'ROI': 'atlasroi',
            'meshname': '{}k_fs_LR'.format(high_res_mesh),
            'tmpdir': os.path.join(temp_dir, '{}k_fs_LR'.format(high_res_mesh)),
            'T1wImage': os.path.join(subject_hcp, 'MNINonLinear', 'T1w.nii.gz')}
    }
    for low_res_mesh in low_res_meshes:
        meshes['{}k_fs_LR'.format(low_res_mesh)] = {
            'Folder': os.path.join(subject_hcp, 'MNINonLinear',
                    'fsaverage_LR{}k'.format(low_res_mesh)),
            'ROI' : 'atlasroi',
            'meshname': '{}k_fs_LR'.format(low_res_mesh),
            'tmpdir': os.path.join(temp_dir, '{}k_fs_LR'.format(low_res_mesh)),
            'T1wImage': os.path.join(subject_hcp, 'MNINonLinear', 'T1w.nii.gz')}
        if make_low_res:
             meshes['Native{}k_fs_LR'.format(low_res_mesh)] = {
                 'Folder': os.path.join(subject_hcp, 'T1w',
                        'fsaverage_LR{}k'.format(low_res_mesh)),
                 'ROI' : 'atlasroi',
                 'meshname': '{}k_fs_LR'.format(low_res_mesh),
                 'tmpdir': os.path.join(temp_dir,
                        '{}k_fs_LR'.format(low_res_mesh)),
                 'T1wImage': os.path.join(subject_hcp, 'T1w', 'T1w.nii.gz'),
                 'DenseMapsFolder': os.path.join(subject_hcp, 'MNINonLinear',
                        'fsaverage_LR{}k'.format(low_res_mesh))}
    return meshes

def run_T1_FNIRT_registration(reg_settings, temp_dir):
    '''
    Run the registration from T1w to MNINonLinear space using FSL's fnirt
    registration settings and file paths are read from reg_settings
    '''
    # unpack the keys from the dictionary to individual variables
    for key, val in reg_settings.iteritems():
        exec (key + '=val')

    ## Linear then non-linear registration to MNI
    T1w2_standard_linear = os.path.join(temp_dir,
            'T1w2StandardLinearImage.nii.gz')
    run(['flirt', '-interp', 'spline', '-dof', '12',
        '-in', os.path.join(src_dir, T1wBrain), '-ref', standard_T1wBrain,
        '-omat', os.path.join(xfms_dir, AtlasTransform_Linear),
        '-o', T1w2_standard_linear])
    ## calculate the just the warp for the surface transform - need it because
    ## sometimes the brain is outside the bounding box of warfield
    run(['fnirt','--in={}'.format(T1w2_standard_linear),
         '--ref={}'.format(standard_T1wImage),
         '--refmask={}'.format(standard_BrainMask),
         '--fout={}'.format(os.path.join(xfms_dir, AtlasTransform_NonLinear)),
         '--logout={}'.format(os.path.join(xfms_dir, 'NonlinearReg_fromlinear.log')),
         '--config={}'.format(FNIRTConfig)])
    ## also inverse the non-prelinear warp - we will need it for the surface
    ## transforms
    run(['invwarp', '-w', os.path.join(xfms_dir, AtlasTransform_NonLinear),
         '-o', os.path.join(xfms_dir,InverseAtlasTransform_NonLinear),
         '-r', standard_T1wImage])
    ##T1w set of warped outputs (brain/whole-head + restored/orig)
    run(['applywarp', '--rel', '--interp=trilinear',
         '-i', os.path.join(src_dir, T1wImage),
         '-r', standard_T1wImage, '-w', os.path.join(xfms_dir, AtlasTransform_NonLinear),
         '--premat={}'.format(os.path.join(xfms_dir,AtlasTransform_Linear)),
         '-o', os.path.join(dest_dir, T1wImage)])

def apply_nonlinear_warp_to_nifti_rois(image, reg_settings, hcp_templates,
                                       import_labels=True):
    '''
    Apply a non-linear warp to nifti image of ROI labels. Reads registration
    settings from reg_settings
    '''
    image_src = os.path.join(reg_settings['src_dir'], '{}.nii.gz'.format(image))
    fs_labels = os.path.join(hcp_templates, 'hcp_config',
            'FreeSurferAllLut.txt')
    if os.path.isfile(image_src):
        image_dest = os.path.join(reg_settings['dest_dir'],
                '{}.nii.gz'.format(image))
        run(['applywarp', '--rel', '--interp=nn',
             '-i', image_src,
             '-r', os.path.join(reg_settings['dest_dir'],
                    reg_settings['T1wImage']),
             '-w', os.path.join(reg_settings['xfms_dir'],
                    reg_settings['AtlasTransform_NonLinear']),
             '--premat={}'.format(os.path.join(reg_settings['xfms_dir'],
                    reg_settings['AtlasTransform_Linear'])),
             '-o', image_dest])
        if import_labels:
            run(['wb_command', '-volume-label-import', '-logging', 'SEVERE',
                    image_dest, fs_labels, image_dest, '-drop-unused-labels'])

def apply_nonlinear_warp_to_surface(subject_id, surface, reg_settings, meshes):
    '''
    Apply the linear and non-linear warps to a surfaces file and add
    the warped surfaces outputs to their spec file

    Arguments
        subject_id          The id of the subject being worked on
        surface             The surface to transform (i.e. 'white', 'pial')
        reg_settings        A dictionary of settings (i.e. paths, filenames)
                            related to the warp.
        meshes              A dictionary of settings (i.e. naming conventions)
                            related to surfaces
    '''
    src_mesh_settings = meshes[reg_settings['src_mesh']]
    dest_mesh_settings = meshes[reg_settings['dest_mesh']]
    xfms_dir = reg_settings['xfms_dir']
    for hemisphere, structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        # Native mesh processing
        # Convert and volumetrically register white and pial surfaces making
        # linear and nonlinear copies, add each to the appropriate spec file
        surf_src = surf_file(subject_id, surface, hemisphere, src_mesh_settings)
        surf_dest = surf_file(subject_id, surface, hemisphere, dest_mesh_settings)

        ## MNI transform the surfaces into the MNINonLinear/Native Folder
        run(['wb_command', '-surface-apply-affine', surf_src,
            os.path.join(xfms_dir, reg_settings['AtlasTransform_Linear']),
            surf_dest, '-flirt', src_mesh_settings['T1wImage'],
            reg_settings['standard_T1wImage']])
        run(['wb_command', '-surface-apply-warpfield', surf_dest,
            os.path.join(xfms_dir, reg_settings['InverseAtlasTransform_NonLinear']),
            surf_dest, '-fnirt', os.path.join(xfms_dir,
            reg_settings['AtlasTransform_NonLinear'])])
        run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
            dest_mesh_settings), structure, surf_dest])

def create_dscalar(subject_id, mesh_settings, dscalar_entry):
    '''
    Create the dense scalars that combine the two surfaces, set the meta-data
    and add them to the spec_file. Important options are read from two
    dictionaries.
        mesh_settings   Contains settings for this Mesh
        dscalar_entry   Contains settings for this type of dscalar
                        (i.e. palette settings)
    '''
    dscalar_file = os.path.join(mesh_settings['Folder'],
            '{}.{}.{}.dscalar.nii'.format(subject_id, dscalar_entry['mapname'],
            mesh_settings['meshname']))

    left_metric = metric_file(subject_id, dscalar_entry['mapname'], 'L',
            mesh_settings)
    right_metric = metric_file(subject_id, dscalar_entry['mapname'], 'R',
            mesh_settings)

    ## combine left and right metrics into a dscalar file
    if dscalar_entry['mask_medialwall']:
        run(['wb_command', '-cifti-create-dense-scalar', dscalar_file,
            '-left-metric', left_metric,'-roi-left',
            medial_wall_roi_file(subject_id, 'L', mesh_settings),
            '-right-metric', right_metric,'-roi-right',
            medial_wall_roi_file(subject_id, 'R', mesh_settings)])
    else :
        run(['wb_command', '-cifti-create-dense-scalar', dscalar_file,
                '-left-metric', left_metric, '-right-metric', right_metric])

    ## set the dscalar file metadata
    run(['wb_command', '-set-map-names', dscalar_file,
        '-map', '1', "{}{}".format(subject_id, dscalar_entry['map_postfix'])])
    run(['wb_command', '-cifti-palette', dscalar_file,
        dscalar_entry['palette_mode'], dscalar_file,
        dscalar_entry['palette_options']])

def create_dlabel(subject_id, mesh_settings, label_name):
    '''
    Create the dense labels that combine the two surfaces, set the meta-data and
    add them to the spec_file. They read the important options for the mesh
    from the mesh_settings
        mesh_settings   Contains settings for this Mesh
        label_name      Contains the name of the label to combine
    '''
    dlabel_file = os.path.join(mesh_settings['Folder'],
            '{}.{}.{}.dlabel.nii'.format(subject_id, label_name,
            mesh_settings['meshname']))
    left_label = label_file(subject_id, label_name, 'L', mesh_settings)
    right_label = label_file(subject_id, label_name, 'R', mesh_settings)
    if not os.path.exists(left_label):
        logger.error("label file {} does not exist. Skipping dlabel creation."
                "".format(left_label))
        return
    ## combine left and right metrics into a dscalar file
    run(['wb_command', '-cifti-create-label', dlabel_file,
        '-left-label', left_label,'-roi-left',
        medial_wall_roi_file(subject_id, 'L', mesh_settings),
        '-right-label', right_label,'-roi-right',
        medial_wall_roi_file(subject_id, 'R', mesh_settings)])
    ## set the dscalar file metadata
    run(['wb_command', '-set-map-names', dlabel_file, '-map', '1',
        "{}_{}".format(subject_id, label_name)])

def add_dense_maps_to_spec_file(subject_id, mesh_settings, dscalar_types):
    '''add all the dlabels and the dscalars to the spec file'''
    if 'DenseMapsFolder' in mesh_settings.keys():
        maps_folder = mesh_settings['DenseMapsFolder']
    else:
        maps_folder = mesh_settings['Folder']

    for dscalar in dscalar_types:
        run(['wb_command', '-add-to-spec-file',
            os.path.realpath(spec_file(subject_id, mesh_settings)), 'INVALID',
            os.path.realpath(os.path.join(maps_folder,
                    '{}.{}.{}.dscalar.nii'.format(subject_id, dscalar,
                    mesh_settings['meshname'])))])

    for label_name in ['aparc', 'aparc.a2009s', 'BA', 'aparc.DKTatlas',
            'BA_exvivo']:
        file_name = "{}.{}.{}.dlabel.nii".format(subject_id, label_name,
                mesh_settings['meshname'])
        dlabel_file = os.path.realpath(os.path.join(maps_folder, file_name))
        if not os.path.exists(dlabel_file):
            logger.debug("dlabel file {} does not exist, skipping".format(
                    dlabel_file))
            continue
        run(['wb_command', '-add-to-spec-file', os.path.realpath(spec_file(
                subject_id, mesh_settings)), 'INVALID', dlabel_file)

def add_T1w_images_to_spec_files(meshes, subject_id):
    '''add all the T1wImages to their associated spec_files'''
    for mesh in meshes.values():
         run(['wb_command', '-add-to-spec-file',
              os.path.realpath(spec_file(subject_id, mesh)),
              'INVALID', os.path.realpath(mesh['T1wImage'])])

def write_cras_file(freesurfer_folder, cras_mat):
    '''read info about the surface affine matrix from freesurfer output and
    write it to a tmpfile'''
    mri_info = get_stdout(['mri_info', os.path.join(freesurfer_folder, 'mri',
            'brain.finalsurfs.mgz')])

    for line in mri_info.split(os.linesep):
        if 'c_r' in line:
            bitscr = line.split('=')[4]
            matrix_x = bitscr.replace(' ','')
        elif 'c_a' in line:
            bitsca = line.split('=')[4]
            matrix_y = bitsca.replace(' ','')
        elif 'c_s' in line:
            bitscs = line.split('=')[4]
            matrix_z = bitscs.replace(' ','')

    with open(cras_mat, 'w') as cfile:
        cfile.write('1 0 0 {}\n'.format(matrix_x))
        cfile.write('0 1 0 {}\n'.format(matrix_y))
        cfile.write('0 0 1 {}\n'.format(matrix_z))
        cfile.write('0 0 0 1{}\n')

def make_brain_mask_from_wmparc(wmparc_nii, brain_mask):
    '''
    Will create a brainmask_nii image out of the wmparc ROIs nifti converted
    from freesurfer
    '''
    ## Create FreeSurfer Brain Mask skipping 1mm version...
    run(['fslmaths', wmparc_nii,
        '-bin', '-dilD', '-dilD', '-dilD', '-ero', '-ero',
        brain_mask])
    run(['wb_command', '-volume-fill-holes', brain_mask, brain_mask])
    run(['fslmaths', brain_mask, '-bin', brain_mask])

def mask_T1w_image(T1w_image, brain_mask, T1w_brain):
    '''mask the T1w Image with the brain_mask to create the T1w_brain image'''
    run(['fslmaths', T1w_image, '-mul', brain_mask, T1w_brain])

def calc_areal_distortion_gii(sphere_pre, sphere_reg, AD_gii_out, map_prefix,
                              map_postfix):
    ''' calculate Areal Distortion Map (gifti) after registration
        Arguments:
            sphere_pre    Path to the pre registration sphere (gifti)
            sphere_reg    Path to the post registration sphere (gifti)
            AD_gii_out    Path to the Area Distortion gifti output
            map_prefix    Prefix added to the map-name meta-data
            map_postfix   Posfix added to the map-name meta-data
    '''
    with ciftify.utilities.TempDir() as va_tmpdir:
        pre_va = os.path.join(va_tmpdir, 'sphere_pre_va.shape.gii')
        reg_va = os.path.join(va_tmpdir, 'sphere_reg_va.shape.gii')
        ## calculate surface vertex areas from pre and post files
        run(['wb_command', '-surface-vertex-areas', sphere_pre, pre_va])
        run(['wb_command', '-surface-vertex-areas', sphere_reg, reg_va])
        ## caluculate Areal Distortion using the vertex areas
        run(['wb_command', '-metric-math', '"(ln(spherereg / sphere) / ln(2))"',
            AD_gii_out, '-var', 'sphere', pre_va, '-var', 'spherereg', reg_va])
        ## set meta-data for the ArealDistotion files
        run(['wb_command', '-set-map-names', AD_gii_out,
            '-map', '1', '{}_Areal_Distortion_{}'.format(map_prefix,
            map_postfix)])
        run(['wb_command', '-metric-palette', AD_gii_out, 'MODE_AUTO_SCALE',
            '-palette-name', 'ROY-BIG-BL', '-thresholding',
            'THRESHOLD_TYPE_NORMAL', 'THRESHOLD_TEST_SHOW_OUTSIDE', '-1', '1'])

def resample_surfs_and_add_to_spec(subject_id, source_mesh, dest_mesh,
        current_sphere='sphere', dest_sphere='sphere'):
    '''
    Resample surface files and add them to the resampled spaces spec file
    uses wb_command -surface-resample with BARYCENTRIC method
    Arguments:
        source_mesh      Dictionary of Settings for current mesh
        dest_mesh        Dictionary of Settings for destination (output) mesh
    '''
    for surface in ['white', 'midthickness', 'pial']:
        for hemisphere, structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
            surf_in = surf_file(subject_id, surface, hemisphere, source_mesh)
            surf_out = surf_file(subject_id, surface, hemisphere, dest_mesh)
            current_sphere_surf = surf_file(subject_id, current_sphere,
                    hemisphere, source_mesh)
            dest_sphere_surf = surf_file(subject_id, dest_sphere, hemisphere,
                    dest_mesh)
            run(['wb_command', '-surface-resample', surf_in,
                current_sphere_surf, dest_sphere_surf, 'BARYCENTRIC', surf_out])
            run(['wb_command', '-add-to-spec-file',
                spec_file(subject_id, dest_mesh), structure, surf_out])

def make_midthickness_surfaces(subject_id, mesh_settings):
     '''
     Use the white and pial surfaces from the same mesh to create a midthickness
     file. Set the midthickness surface metadata and add it to the spec_file
     '''
     for hemisphere, structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        #Create midthickness by averaging white and pial surfaces
        mid_surf = surf_file(subject_id, 'midthickness', hemisphere,
                mesh_settings)
        run(['wb_command', '-surface-average', mid_surf,
            '-surf', surf_file(subject_id, 'white', hemisphere, mesh_settings),
            '-surf', surf_file(subject_id, 'pial', hemisphere, mesh_settings)])
        run(['wb_command', '-set-structure', mid_surf, structure,
            '-surface-type', 'ANATOMICAL', '-surface-secondary-type', 'MIDTHICKNESS'])
        run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
            mesh_settings), structure, mid_surf])

def make_inflated_surfaces(subject_id, mesh_settings, iterations_scale=2.5):
    '''
    Make inflated and very_inflated surfaces from the mid surface of the
    specified mesh. Adds the surfaces to the spec_file
    '''
    for hemisphere, structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        infl_surf = surf_file(subject_id, 'inflated', hemisphere, mesh_settings)
        vinfl_surf = surf_file(subject_id, 'very_inflated', hemisphere,
                mesh_settings)
        run(['wb_command', '-surface-generate-inflated',
            surf_file(subject_id, 'midthickness', hemisphere, mesh_settings),
            infl_surf, vinfl_surf, '-iterations-scale', str(iterations_scale)])
        run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
            mesh_settings), structure, infl_surf])
        run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
            mesh_settings), structure, vinfl_surf])

def resample_and_mask_metric(subject_id, dscalar, hemisphere, source_mesh,
        dest_mesh, current_sphere='sphere', dest_sphere='sphere'):
    '''
    Resample the metric files to a different mesh and then mask out the medial
    wall. Uses wb_command -metric-resample with 'ADAP_BARY_AREA' method.
    To remove masking steps the roi can be set to None

    Arguments:
        dscalar                 Dscalar specific settings (e.g. 'sulc',
                                'thickness', etc.)
        current_mesh            Settings for current mesh
        dest_mesh               Settings for destination (output) mesh
    '''
    map_name = dscalar['mapname']
    metric_in = metric_file(subject_id, map_name, hemisphere, source_mesh)
    metric_out = metric_file(subject_id, map_name, hemisphere, dest_mesh)

    current_midthickness = surf_file(subject_id, 'midthickness', hemisphere,
            source_mesh)
    new_midthickness = surf_file(subject_id, 'midthickness', hemisphere,
            dest_mesh)

    current_sphere_surf = surf_file(subject_id, current_sphere, hemisphere,
            source_mesh)
    dest_sphere_surf = surf_file(subject_id, dest_sphere, hemisphere,
            dest_mesh)

    if dscalar['mask_medialwall']:
        run(['wb_command', '-metric-resample', metric_in, current_sphere_surf,
            dest_sphere_surf, 'ADAP_BARY_AREA', metric_out,
            '-area-surfs', current_midthickness, new_midthickness,
            '-current-roi', medial_wall_roi_file(subject_id, hemisphere,
            source_mesh)])
        run(['wb_command', '-metric-mask', metric_out,
            medial_wall_roi_file(subject_id, hemisphere, dest_mesh), metric_out])
    else:
        run(['wb_command', '-metric-resample', metric_in, current_sphere_surf,
            dest_sphere_surf, 'ADAP_BARY_AREA', metric_out,
            '-area-surfs', current_midthickness, new_midthickness])

def convert_freesurfer_annot(subject_id, label_name, fs_folder,
                             dest_mesh_settings):
    ''' convert a freesurfer annot to a gifti label and set metadata'''
    for hemisphere, structure in [('L', 'CORTEX_LEFT'), ('R', 'CORTEX_RIGHT')]:
        fs_annot = os.path.join(fs_folder, 'label',
                '{}h.{}.annot'.format(hemisphere.lower(), label_name))
        if os.path.exists(fs_annot):
            label_gii = label_file(subject_id, label_name, hemisphere,
                    dest_mesh_settings)
            run(['mris_convert', '--annot', fs_annot,
                os.path.join(fs_folder, 'surf',
                        '{}h.white'.format(hemisphere.lower())),
                label_gii])
            run(['wb_command', '-set-structure', label_gii, structure])
            run(['wb_command', '-set-map-names', label_gii,
                '-map', '1', '{}_{}_{}'.format(subject_id, hemisphere,
                label_name)])
            run(['wb_command', '-gifti-label-add-prefix',
                label_gii, '{}_'.format(hemisphere), label_gii])

def resample_label(subject_id, label_name, hemisphere, source_mesh, dest_mesh,
        current_sphere='sphere', dest_sphere='sphere'):
    '''
    Resample label files if they exist. Uses wb_command -label-resample with
    BARYCENTRIC method

    Arguments:
        label_name            Name of label to resample (i.e 'aparc')
        hemisphere            hemisphere of label to resample ('L' or 'R')
        source_mesh           Settings for current mesh
        dest_mesh             Settings for destination (output) mesh
        current_sphere        The name (default 'sphere') of the current
                              registration surface
        new_sphere            The name (default 'sphere') of the dest
                              registration surface
    '''
    label_in = label_file(subject_id, label_name, hemisphere, source_mesh)
    if os.path.exists(label_in):
        run(['wb_command', '-label-resample', label_in,
            surf_file(subject_id, current_sphere, hemisphere, source_mesh),
            surf_file(subject_id, dest_sphere, hemisphere, dest_mesh),
            'BARYCENTRIC',
            label_file(subject_id, label_name, hemisphere, dest_mesh),
            '-largest'])

def convert_freesurfer_T1(fs_folder, T1w_nii):
    '''
    Convert T1w from freesurfer(mgz) to nifti format and run fslreorient2std
    Arguments:
            fs_folder   Path to the subject's freesurfer output
            T1w_nii     Path to T1wImage to with desired output orientation
    '''
    fs_T1 = os.path.join(fs_folder, 'mri', 'T1.mgz')
    if not os.path.exists(fs_T1):
        logger.error("Cannot find freesurfer T1 {}, exiting".format(fs_T1))
        sys.exit(1)
    run(['mri_convert', fs_T1, T1w_nii])
    run(['fslreorient2std', T1w_nii, T1w_nii])

def convert_freesurfer_mgz(image_name,  T1w_nii, hcp_templates,
                           freesurfer_folder, out_dir):
    ''' convert image from freesurfer(mgz) to nifti format, and
        realigned to the specified T1wImage, and imports labels
        Arguments:
            image_name          Name of Image to Convert
            T1w_nii             Path to T1wImage to with desired output
                                orientation
            hcp_templates       The path to the hcp templates, as defined by
                                the shell variable CIFTIFY_TEMPLATES
            freesurfer_folder   Path the to subjects freesurfer output
            out_dir             Output Directory for converted Image
    '''
    freesurfer_mgz = os.path.join(freesurfer_folder, 'mri',
            '{}.mgz'.format(image_name))
    if not os.path.isfile(freesurfer_mgz):
        logger.error("{} not found, exiting.".format(freesurfer_mgz))
        sys.exit(1)
    image_nii = os.path.join(out_dir, '{}.nii.gz'.format(image_name))
    run(['mri_convert', '-rt', 'nearest', '-rl', T1w_nii, freesurfer_mgz,
            image_nii])
    run(['wb_command', '-logging', 'SEVERE','-volume-label-import', image_nii,
            os.path.join(hcp_templates, 'hcp_config', 'FreeSurferAllLut.txt'),
            image_nii, '-drop-unused-labels'])

def convert_freesurfer_surface(subject_id, surface, surface_type, fs_subject_dir,
        dest_mesh_settings, surface_secondary_type=None, cras_mat=None,
        add_to_spec=True):
    '''
    Convert freesurfer surface to gifti surface files
    Arguments:
        surface                     Surface name
        surface_type                Surface type to add to the metadata
        surface_secondary_type      Type that will be added to gifti metadata
        fs_subject_dir              The subject freesurfer output folder
        dest_mesh_settings          Dictionary of settings with naming
                                    conventions for the gifti files
        cras_mat                    Path to the freesurfer affine matrix
        add_to_spec                 Whether to add the gifti file the spec file
    '''
    for hemisphere, structure in [('L', 'CORTEX_LEFT'), ('R', 'CORTEX_RIGHT')]:
        surf_fs = os.path.join(fs_subject_dir, 'surf',
                '{}h.{}'.format(hemisphere.lower(), surface))
        surf_native = surf_file(subject_id, surface, hemisphere,
                dest_mesh_settings)
        ## convert the surface into the T1w/Native Folder
        run(['mris_convert',surf_fs, surf_native])

        set_structure_command = ['wb_command', '-set-structure', surf_native,
                structure, '-surface-type', surface_type]
        if surface_secondary_type:
            set_structure_command.extend(['-surface-secondary-type',
                    surface_secondary_type])
        run(set_structure_command)

        if cras_mat:
            run(['wb_command', '-surface-apply-affine', surf_native,
                    cras_mat, surf_native])
        if add_to_spec:
            run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
                    dest_mesh_settings), structure, surf_native])

def convert_freesurfer_maps(subject_id, map_dict, fs_folder,
                            dest_mesh_settings):
    ''' Convert a freesurfer data (thickness, curv, sulc) to a gifti metric
    and set metadata'''
    for hemisphere, structure in [('L', 'CORTEX_LEFT'), ('R', 'CORTEX_RIGHT')]:
        map_gii = metric_file(subject_id, map_dict['mapname'], hemisphere,
                dest_mesh_settings)
        ## convert the freesurfer files to gifti
        run(['mris_convert', '-c',
            os.path.join(fs_folder, 'surf', '{}h.{}'.format(hemisphere.lower(),
                    map_dict['fsname'])),
            os.path.join(fs_folder, 'surf',
                    '{}h.white'.format(hemisphere.lower())),
            map_gii])
        ## set a bunch of meta-data and multiply by -1
        run(['wb_command', '-set-structure', map_gii, structure])
        run(['wb_command', '-metric-math', '"(var * -1)"',
            map_gii, '-var', 'var', map_gii])
        run(['wb_command', '-set-map-names', map_gii,
            '-map', '1', '{}_{}{}'.format(subject_id, hemisphere,
            map_dict['map_postfix'])])
        if map_dict['mapname'] == 'thickness':
            ## I don't know why but there are thickness specific extra steps
            # Thickness set thickness at absolute value than set palette metadata
            run(['wb_command', '-metric-math', '"(abs(thickness))"',
                map_gii, '-var', 'thickness', map_gii])
        run(['wb_command', '-metric-palette', map_gii, map_dict['palette_mode'],
            map_dict['palette_options']])

def medial_wall_rois_from_thickness_maps(subject_id, mesh_settings):
    '''create an roi file by thresholding the thickness surfaces'''
    for hemisphere, structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        ## create the native ROI file using the thickness file
        native_roi =  medial_wall_roi_file(subject_id, hemisphere,
                mesh_settings)
        midthickness_gii = surf_file(subject_id, 'midthickness', hemisphere,
                mesh_settings)
        run(['wb_command', '-metric-math', '"(thickness > 0)"', native_roi,
            '-var', 'thickness', metric_file(subject_id, 'thickness', hemisphere,
            mesh_settings)])
        run(['wb_command', '-metric-fill-holes', midthickness_gii, native_roi,
            native_roi])
        run(['wb_command', '-metric-remove-islands', midthickness_gii,
            native_roi, native_roi])
        run(['wb_command', '-set-map-names', native_roi, '-map', '1',
            '{}_{}_ROI'.format(subject_id, hemisphere)])

def merge_subject_medial_wall_with_atlas_template(subject_id, high_res_mesh,
        meshes, reg_sphere, temp_dir):
    '''resample the atlas medial wall roi into subjects native space then
    merge with native roi'''

    native_settings = meshes['AtlasSpaceNative']
    high_res_settings = meshes['HighResMesh']

    for hemisphere in ['L', 'R']:
        ## note this roi is a temp file so I'm not using the roi_file function
        atlas_roi_native_gii = metric_file(subject_id, 'atlasroi', hemisphere,
                native_settings)

        native_roi = medial_wall_roi_file(subject_id, hemisphere,
                native_settings)
        #Ensures no zeros in atlas medial wall ROI
        run(['wb_command', '-metric-resample',
            medial_wall_roi_file(subject_id, hemisphere, high_res_settings),
            surf_file(subject_id, 'sphere', hemisphere, high_res_settings),
            surf_file(subject_id, reg_sphere, hemisphere, native_settings),
            'BARYCENTRIC', atlas_roi_native_gii,'-largest'])
        run(['wb_command', '-metric-math', '"(atlas + individual) > 0"',
            native_roi, '-var', 'atlas', atlas_roi_native_gii, '-var',
            'individual', native_roi])

def run_fs_reg_LR(subject_id, ciftify_data_dir, high_res_mesh, reg_sphere,
                  native_mesh_settings):
    ''' Copy all the template files and do the FS left to right registration'''
    surface_atlas_dir = os.path.join(ciftify_data_dir, 'standard_mesh_atlases')
    for hemisphere in ['L', 'R']:

        #Concatenate FS registration to FS --> FS_LR registration
        fs_reg_sphere = surf_file(subject_id, reg_sphere, hemisphere,
                native_mesh_settings)
        run(['wb_command', '-surface-sphere-project-unproject',
            surf_file(subject_id, 'sphere.reg', hemisphere,
                    native_mesh_settings),
            os.path.join(surface_atlas_dir, 'fs_{}'.format(hemisphere),
                    'fsaverage.{0}.sphere.{1}k_fs_{0}.surf.gii'.format(
                    hemisphere, high_res_mesh)),
            os.path.join(surface_atlas_dir, 'fs_{}'.format(hemisphere),
                    'fs_{0}-to-fs_LR_fsaverage.{0}_LR.spherical_std.' \
                    '{1}k_fs_{0}.surf.gii'.format(hemisphere, high_res_mesh)),
                    fs_reg_sphere])

        #Make FreeSurfer Registration Areal Distortion Maps
        calc_areal_distortion_gii(
                surf_file(subject_id, 'sphere', hemisphere,
                        native_mesh_settings),
                fs_reg_sphere,
                metric_file(subject_id, 'ArealDistortion_FS', hemisphere,
                        native_mesh_settings),
                '{}_{}'.format(subject_id, hemisphere), 'FS')

def dilate_and_mask_metric(subject_id, native_mesh_settings, dscalars):
    ''' Dilate and mask gifti metric data... done after refinining the medial
    roi mask'''
    ## remask the thickness and curvature data with the redefined medial wall roi
    for map_name in dscalars.keys():
        if not dscalars[map_name]['mask_medialwall']:
            continue
        for hemisphere  in ['L', 'R']:
            ## dilate the thickness and curvature file by 10mm
            metric_map = metric_file(subject_id, map_name, hemisphere,
                    native_mesh_settings)
            run(['wb_command', '-metric-dilate', metric_map,
                surf_file(subject_id, 'midthickness',hemisphere,
                        native_mesh_settings),
                '10', metric_map,'-nearest'])
            ## apply the medial wall roi to the thickness and curvature files
            run(['wb_command', '-metric-mask', metric_map,
                medial_wall_roi_file(subject_id, hemisphere,
                        native_mesh_settings),
                metric_map])

def link_to_template_file(subject_file, global_file, via_file):
    '''
    The original hcp pipelines would copy atlas files into each subject's
    directory, which had the benefit of making the atlas files easier to find
    and copy across systems but created many redundant files.

    This function instead will copy the atlas files into a templates directory
    in the HCP_DATA Folder and then link from each subject's individual
    directory to this file
    '''
    ## copy from ciftify template to the HCP_DATA if via_file does not exist
    if not os.path.isfile(via_file):
        via_folder = os.path.dirname(via_file)
        if not os.path.exists(via_folder): run(['mkdir','-p',via_folder])
        run(['cp', global_file, via_file])
    ## link the subject_file to via_file
    os.symlink(os.path.relpath(via_file, os.path.dirname(subject_file)),
               subject_file)

def create_cifti_subcortical_ROIs(atlas_space_folder, hcp_data,
                                  grayordinate_resolutions, hcp_templates,
                                  temp_dir):
    '''
    defines the subcortical ROI labels for cifti files combines a template ROI
    masks with the participants freesurfer wmparc output to do so
    '''
    # The template files required for this section
    freesurfer_labels = os.path.join(hcp_templates, 'hcp_config',
            'FreeSurferAllLut.txt')
    grayord_space_dir = os.path.join(hcp_templates, '91282_Greyordinates')
    subcortical_gray_labels = os.path.join(hcp_templates, 'hcp_config',
            'FreeSurferSubcorticalLabelTableLut.txt')
    avg_wmparc = os.path.join(hcp_templates, 'standard_mesh_atlases',
            'Avgwmparc.nii.gz')

    ## right now we only have a template for the 2mm greyordinate space..
    for grayord_res in grayordinate_resolutions:
        ## The outputs of this sections
        atlas_ROIs = os.path.join(atlas_space_folder, 'ROIs',
                'Atlas_ROIs.{}.nii.gz'.format(grayord_res))
        wmparc_ROIs = os.path.join(temp_dir,
                'wmparc.{}.nii.gz'.format(grayord_res))
        wmparc_atlas_ROIs = os.path.join(temp_dir,
                'Atlas_wmparc.{}.nii.gz'.format(grayord_res))
        ROIs_nii = os.path.join(atlas_space_folder, 'ROIs',
                'ROIs.{}.nii.gz'.format(grayord_res))

        ## linking this file into the subjects folder because func2hcp needs it
        link_to_template_file(atlas_ROIs,
                os.path.join(grayord_space_dir,
                        'Atlas_ROIs.{}.nii.gz'.format(grayord_res)),
                os.path.join(hcp_data, 'zz_templates',
                        'Atlas_ROIs.{}.nii.gz'.format(grayord_res)))

        ## the analysis steps - resample the participants wmparc output the
        ## greyordinate resolution
        run(['applywarp', '--interp=nn', '-i', os.path.join(atlas_space_folder,
            'wmparc.nii.gz'), '-r', atlas_ROIs, '-o', wmparc_ROIs])
        ## import the label metadata
        run(['wb_command', '-volume-label-import', wmparc_ROIs,
            freesurfer_labels, wmparc_ROIs, '-drop-unused-labels'])
        ## These commands were used in the original fs2hcp script, Erin
        ## discovered they are probably not being used. Leaving these commands
        ## here, though, just in case
        #   run(['applywarp', '--interp=nn', '-i', Avgwmparc, '-r', Atlas_ROIs,
        #       '-o', wmparcAtlas_ROIs])
        #   run(['wb_command', '-volume-label-import',
        #     wmparcAtlas_ROIs, FreeSurferLabels,  wmparcAtlas_ROIs,
        #     '-drop-unused-labels'])
        run(['wb_command', '-volume-label-import', wmparc_ROIs,
            subcortical_gray_labels, ROIs_nii,'-discard-others'])

def copy_colin_flat_and_add_to_spec(subject_id, hcp_dir, ciftify_data_dir,
                                    mesh_settings):
    ''' Copy the colin flat atlas out of the templates folder and add it to
    the spec file. '''
    for hemisphere, structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        colin_src = os.path.join(ciftify_data_dir, 'standard_mesh_atlases',
            'colin.cerebral.{}.flat.{}.surf.gii'.format(hemisphere,
            mesh_settings['meshname']))
        if not os.path.exists(colin_src):
            continue
        colin_dest = surf_file(subject_id, 'flat', hemisphere, mesh_settings)
        link_to_template_file(colin_dest, colin_src,
            os.path.join(hcp_dir, 'zz_templates', os.path.basename(colin_src)))
        run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
            mesh_settings), structure, colin_dest])

def copy_sphere_mesh_from_template(hcp_dir, ciftify_data_dir, subject_id,
                                   mesh_settings):
    '''Copy the sphere of specific mesh settings out of the template and into
    subjects folder'''
    mesh_name = mesh_settings['meshname']
    for hemisphere, structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        if mesh_name == '164k_fs_LR':
            sphere_basename = 'fsaverage.{}_LR.spherical_std.{}.' \
                    'surf.gii'.format(hemisphere, mesh_name)
        else :
            sphere_basename = '{}.sphere.{}.surf.gii'.format(hemisphere,
                    mesh_name)
        sphere_src = os.path.join(ciftify_data_dir, 'standard_mesh_atlases',
                sphere_basename)
        sphere_dest = surf_file(subject_id, 'sphere', hemisphere, mesh_settings)
        link_to_template_file(sphere_dest, sphere_src,
            os.path.join(hcp_dir, 'zz_templates', sphere_basename))
        run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
            mesh_settings), structure, sphere_dest])

def copy_atlas_roi_from_template(hcp_dir, ciftify_data_dir, subject_id,
                                 mesh_settings):
    '''Copy the atlas roi (roi of medial wall) for a specific mesh out of
    templates'''
    for hemisphere in ['L', 'R']:
        roi_basename = '{}.atlasroi.{}.shape.gii'.format(hemisphere,
                mesh_settings['meshname'])
        roi_src = os.path.join(ciftify_data_dir, 'standard_mesh_atlases',
                roi_basename)
        if os.path.exists(roi_src):
            ## Copying sphere surface from templates file to subject folder
            roi_dest = medial_wall_roi_file(subject_id, hemisphere,
                    mesh_settings)
            link_to_template_file(roi_dest, roi_src,
                    os.path.join(hcp_dir, 'zz_templates', roi_basename))

def section_header(title):
    '''returns a outlined bit to stick in a log file as a section header'''
    header = '''
\n-------------------------------------------------------------
{} : {}
-------------------------------------------------------------
'''.format(datetime.datetime.now(),title)
    return(header)

def log_build_environment():
    '''print the running environment info to the logs (info)'''
    logger.info("{}---### Environment Settings ###---".format(os.linesep))
    logger.info("Username: {}".format(get_stdout(['whoami'],
            echo=False).replace(os.linesep,'')))
    logger.info(ciftify.config.system_info())
    logger.info(ciftify.config.ciftify_version(os.path.basename(__file__)))
    logger.info(ciftify.config.wb_command_version())
    logger.info(ciftify.config.freesurfer_version())
    logger.info(ciftify.config.fsl_version())
    logger.info("---### End of Environment Settings ###---{}".format(os.linesep))

def run(cmd, dryrun=False, echo=True, supress_stdout = False):
    """
    Runscommand in default shell, returning the return code. And logging the output.
    It can take a the cmd argument as a string or a list.
    If a list is given, it is joined into a string.
    There are some arguments for changing the way the cmd is run:
       dryrun:     do not actually run the command (for testing) (default: False)
       echo:       Print the command to the log (info (level))
       supress_stdout:  Any standard output from the function is printed to the log at "debug" level but not "info"
    """

    global DRYRUN
    dryrun = DRYRUN

    if type(cmd) is list:
        thiscmd = ' '.join(cmd)
    else: thiscmd = cmd
    if echo:
        logger.info("Running: {}".format(thiscmd))
    if dryrun:
        logger.info('Doing a dryrun')
        return 0
    else:
        p = subprocess.Popen(thiscmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode:
            logger.error('cmd: {} \n Failed with returncode {}'.format(thiscmd, p.returncode))
            logger.error('Error message: {}'.format(err))
            sys.exit(p)
        if supress_stdout:
            logger.debug(out)
        else:
            logger.info(out)
        if len(err) > 0 : logger.warning(err)
        return p.returncode

def get_stdout(cmdlist, echo=True):
   ''' run the command given from the cmd list and report the stdout result'''
   if echo: logger.info('Evaluating: {}'.format(' '.join(cmdlist)))
   stdout = subprocess.check_output(cmdlist)
   return stdout

def run_MSMSulc_registration():
    sys.exit('Sorry, MSMSulc registration is not ready yet...Exiting')
#   #If desired, run MSMSulc folding-based registration to FS_LR initialized with FS affine
#   if [ ${RegName} = "MSMSulc" ] ; then
#     #Calculate Affine Transform and Apply
#     if [ ! -e "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc ] ; then
#       mkdir "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc
#     fi
#     ${CARET7DIR}/wb_command -surface-affine-regression "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.reg.reg_LR.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.mat
#     ${CARET7DIR}/wb_command -surface-apply-affine "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.mat "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.sphere_rot.surf.gii
#     ${CARET7DIR}/wb_command -surface-modify-sphere "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.sphere_rot.surf.gii 100 "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.sphere_rot.surf.gii
#     cp "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.sphere_rot.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.rot.native.surf.gii
#     DIR=`pwd`
#     cd "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc
#     #Register using FreeSurfer Sulc Folding Map Using MSM Algorithm Configured for Reduced Distortion
#     #${MSMBin}/msm --version
#     ${MSMBin}/msm --levels=4 --conf=${MSMBin}/allparameterssulcDRconf --inmesh="$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.rot.native.surf.gii --trans="$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.rot.native.surf.gii --refmesh="$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii --indata="$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sulc.native.shape.gii --refdata="$SurfaceAtlasDIR"/"$Hemisphere".refsulc."$HighResMesh"k_fs_LR.shape.gii --out="$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}. --verbose
#     cd $DIR
#     cp "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.HIGHRES_transformed.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.surf.gii
#     ${CARET7DIR}/wb_command -set-structure "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.surf.gii ${Structure}
#
#     #Make MSMSulc Registration Areal Distortion Maps
#     ${CARET7DIR}/wb_command -surface-vertex-areas "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.shape.gii
#     ${CARET7DIR}/wb_command -surface-vertex-areas "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.shape.gii
#     ${CARET7DIR}/wb_command -metric-math "ln(spherereg / sphere) / ln(2)" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_MSMSulc.native.shape.gii -var sphere "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.shape.gii -var spherereg "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.shape.gii
#     rm "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.shape.gii
#     ${CARET7DIR}/wb_command -set-map-names "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_MSMSulc.native.shape.gii -map 1 "$Subject"_"$Hemisphere"_Areal_Distortion_MSMSulc
#     ${CARET7DIR}/wb_command -metric-palette "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_MSMSulc.native.shape.gii MODE_AUTO_SCALE -palette-name ROY-BIG-BL -thresholding THRESHOLD_TYPE_NORMAL THRESHOLD_TEST_SHOW_OUTSIDE -1 1
#
#     RegSphere="${AtlasSpaceFolder}/${NativeFolder}/${Subject}.${Hemisphere}.sphere.MSMSulc.native.surf.gii"

def resample_to_native(native_mesh, dest_mesh, settings, subject_id,
        sphere):
    copy_sphere_mesh_from_template(settings.hcp_dir, settings.ciftify_data_dir,
            subject_id, dest_mesh)
    resample_surfs_and_add_to_spec(subject_id, native_mesh, dest_mesh,
            current_sphere=sphere)
    make_inflated_surfaces(subject_id, dest_mesh, iterations_scale=0.75)
    add_dense_maps_to_spec_file(subject_id, dest_mesh,
            settings.dscalars.keys())

def deform_to_native(native_mesh, dest_mesh, dscalars, subject_id,
        sphere='sphere', scale=2.5):
    resample_surfs_and_add_to_spec(subject_id, native_mesh, dest_mesh,
            current_sphere=sphere)
    make_inflated_surfaces(subject_id, dest_mesh, iterations_scale=scale)
    resample_metric_and_label(subject_id, dscalars, native_mesh, dest_mesh,
            sphere)
    make_dense_map(subject_id, dest_mesh, dscalars)

def populate_low_res_spec_file(source_mesh, dest_mesh, subject, settings,
        sphere):
    copy_atlas_roi_from_template(settings.hcp_dir, settings.ciftify_data_dir,
            subject.id, dest_mesh)
    copy_sphere_mesh_from_template(settings.hcp_dir, settings.ciftify_data_dir,
            subject.id, dest_mesh)
    copy_colin_flat_and_add_to_spec(subject.id, settings.hcp_dir,
            settings.ciftify_data_dir, dest_mesh)
    deform_to_native(source_mesh, dest_mesh, settings.dscalars, subject.id,
            sphere, scale=0.75)

def make_dense_map(subject_id, mesh, dscalars):
    ## combine L and R metrics into dscalar files
    for map_type in ['aparc', 'aparc.a2009s', 'BA', 'aparc.DKTatlas',
            'BA_exvivo']:
        create_dlabel(subject_id, mesh, map_type)

    ## combine L and R labels into a dlabel file
    for map_name in settings.dscalars.keys():
        create_dscalar(subject_id, mesh, dscalars[map_name])

    ## add all the dscalar and dlabel files to the spec file
    add_dense_maps_to_spec_file(subject_id, mesh, dscalars.keys())

def resample_metric_and_label(subject_id, dscalars, source_mesh, dest_mesh,
        current_sphere):
    for hemisphere in ['L', 'R']:
        ## resample the metric data to the new mesh
        for map_name in dscalars.keys():
            resample_and_mask_metric(subject_id, dscalars[map_name], hemisphere,
                    source_mesh, dest_mesh, current_sphere=current_sphere)
        ## resample all the label data to the new mesh
        for map_name in ['aparc', 'aparc.a2009s', 'BA' 'aparc.DKTatlas',
                'BA_exvivo']:
            resample_label(subject_id, map_name, hemisphere, source_mesh,
                    dest_mesh, current_sphere=current_sphere)

def create_reg_sphere(settings, subject_id, meshes):
    logger.info(section_header("Concatenating Freesurfer Reg with template to "
            "get fs_LR reg"))

    FS_reg_sphere = 'sphere.reg.reg_LR'
    run_fs_reg_LR(subject_id, settings.ciftify_data_dir, settings.high_res,
            FS_reg_sphere, meshes['AtlasSpaceNative'])

    if settings.reg_name == 'MSMSulc':
        reg_sphere = run_MSMSulc_registration()
    else :
        reg_sphere = FS_reg_sphere
    return reg_sphere

def process_native_meshes(subject, meshes, dscalars):
    logger.info(section_header("Creating midthickness, inflated and "
            "very_inflated surfaces"))
    for mesh_name in ['T1wNative', 'AtlasSpaceNative']:
        ## build midthickness out the white and pial
        make_midthickness_surfaces(subject.id, meshes[mesh_name])
        # make inflated surfaces from midthickness
        make_inflated_surfaces(subject.id, meshes[mesh_name])

    # Convert freesurfer annotation to gifti labels and set meta-data
    logger.info(section_header("Converting Freesurfer measures to gifti"))
    for label_name in ['aparc', 'aparc.a2009s', 'BA', 'aparc.DKTatlas',
            'BA_exvivo']:
        convert_freesurfer_annot(subject.id, label_name, subject.fs_folder,
                meshes['AtlasSpaceNative'])

    # Add more files to the spec file and convert other FreeSurfer surface data
    # to metric/GIFTI including sulc, curv, and thickness.
    for map_dict in dscalars.values():
        if 'fsname' not in map_dict.keys():
            continue
        convert_freesurfer_maps(subject.id, map_dict, subject.fs_folder,
                meshes['AtlasSpaceNative'])
    medial_wall_rois_from_thickness_maps(subject.id, meshes['AtlasSpaceNative'])

def convert_FS_surfaces_to_gifti(subject_id, freesurfer_subject_dir, meshes,
                                 reg_settings, temp_dir):
    logger.info(section_header("Converting freesurfer surfaces to gifti"))

    # Find c_ras offset between FreeSurfer surface and volume and generate
    # matrix to transform surfaces
    cras_mat = os.path.join(temp_dir, 'cras.mat')
    write_cras_file(freesurfer_subject_dir, cras_mat)

    for surface, secondary_type in [('white','GRAY_WHITE'), ('pial', 'PIAL')]:
        ## convert the surfaces from freesurfer into T1w Native Directory
        convert_freesurfer_surface(subject_id, surface, 'ANATOMICAL',
                freesurfer_subject_dir, meshes['T1wNative'],
                surface_secondary_type=secondary_type, cras_mat=cras_mat)

        ## MNI transform the surfaces into the MNINonLinear/Native Folder
        apply_nonlinear_warp_to_surface(subject_id, surface, reg_settings,
                meshes)

    # Convert original and registered spherical surfaces and add them to the
    # nonlinear spec file
    convert_freesurfer_surface(subject_id, 'sphere', 'SPHERICAL',
            freesurfer_subject_dir, meshes['AtlasSpaceNative'])
    convert_freesurfer_surface(subject_id, 'sphere.reg', 'SPHERICAL',
            freesurfer_subject_dir, meshes['AtlasSpaceNative'],
            add_to_spec=False)

def convert_inputs_to_MNI_space(reg_settings, hcp_templates, temp_dir):
    logger.info(section_header("Registering T1wImage to MNI template using FSL "
            "FNIRT"))
    run_T1_FNIRT_registration(reg_settings, temp_dir)

    # convert FreeSurfer Segmentations and brainmask to MNI space
    logger.info(section_header("Applying MNI transform to label files"))
    for image in ['wmparc', 'aparc.a2009s+aseg', 'aparc+aseg']:
        apply_nonlinear_warp_to_nifti_rois(image, reg_settings, hcp_templates)

    # also transform the brain mask to MNI space
    apply_nonlinear_warp_to_nifti_rois('brainmask_fs', reg_settings,
            hcp_templates, import_labels=False)

def prepare_T1_image(wmparc, T1w_nii, reg_settings):
    T1w_brain_mask = os.path.join(reg_settings['src_dir'],
            reg_settings['BrainMask'])
    T1w_brain_nii = os.path.join(reg_settings['src_dir'],
            reg_settings['T1wBrain'])

    logger.info(section_header('Creating brainmask from freesurfer wmparc '
            'segmentation'))
    make_brain_mask_from_wmparc(wmparc, T1w_brain_mask)
    ## apply brain mask to the T1wImage
    mask_T1w_image(T1w_nii, T1w_brain_mask, T1w_brain_nii)

def convert_T1_and_freesurfer_inputs(T1w_nii, subject, hcp_templates):
    logger.info(section_header("Converting T1wImage and Segmentations from "
            "freesurfer"))
    ###### convert the mgz T1w and put in T1w folder
    convert_freesurfer_T1(subject.fs_folder, T1w_nii)
    #Convert FreeSurfer Volumes and import the label metadata
    for image in ['wmparc', 'aparc.a2009s+aseg', 'aparc+aseg']:
      convert_freesurfer_mgz(image, T1w_nii, hcp_templates, subject.fs_folder,
            subject.T1w_dir)

def create_output_directories(meshes, xfms_dir, rois_dir, results_dir):
    for mesh in meshes.values():
        ciftify.utilities.make_dir(mesh['Folder'], DRYRUN)
        ciftify.utilities.make_dir(mesh['tmpdir'], DRYRUN)
    ciftify.utilities.make_dir(xfms_dir, DRYRUN)
    ciftify.utilities.make_dir(rois_dir, DRYRUN)
    ciftify.utilities.make_dir(results_dir, DRYRUN)

def log_inputs(fs_dir, hcp_dir, subject_id):
    logger.info("Arguments: ")
    logger.info('    freesurfer SUBJECTS_DIR: {}'.format(fs_dir))
    logger.info('    HCP_DATA directory: {}'.format(hcp_dir))
    logger.info('    Subject: {}'.format(subject_id))

def main(temp_dir, settings):
    subject = settings.subject

    log_inputs(settings.fs_root_dir, settings.hcp_dir, subject.id)
    log_build_environment()

    logger.debug("Defining Settings")
    ## the Meshes Dict contains file paths and naming conventions specific to
    ## all ouput meshes
    meshes = define_meshes(subject.path, settings.high_res, settings.low_res,
            temp_dir, settings.resample)

    logger.info("START: FS2CaretConvertRegisterNonlinear")
    #Make some folders for this and later scripts
    create_output_directories(meshes, settings.registration['xfms_dir'],
            os.path.join(subject.atlas_space_dir, 'ROIs'),
            os.path.join(subject.atlas_space_dir, 'Results'))

    T1w_nii = os.path.join(subject.T1w_dir, settings.registration['T1wImage'])
    wmparc = os.path.join(subject.T1w_dir, 'wmparc.nii.gz')
    convert_T1_and_freesurfer_inputs(T1w_nii, subject,
            settings.ciftify_data_dir)
    prepare_T1_image(wmparc, T1w_nii, settings.registration)

    convert_inputs_to_MNI_space(settings.registration, settings.ciftify_data_dir,
            temp_dir)

    #Create Spec Files including the T1w files
    add_T1w_images_to_spec_files(meshes, subject.id)

    # Import Subcortical ROIs and resample to the Grayordinate Resolution
    create_cifti_subcortical_ROIs(subject.atlas_space_dir, settings.hcp_dir,
            settings.grayord_res, settings.ciftify_data_dir, temp_dir)
    convert_FS_surfaces_to_gifti(subject.id, subject.fs_folder, meshes,
            settings.registration, temp_dir)
    process_native_meshes(subject, meshes, settings.dscalars)
    reg_sphere = create_reg_sphere(settings, subject.id, meshes)

    logger.info(section_header("Importing HighRes Template Sphere and Medial "
            "Wall ROI"))
    ## copy the HighResMesh medialwall roi and the sphere mesh from the
    ## templates
    copy_atlas_roi_from_template(settings.hcp_dir, settings.ciftify_data_dir,
            subject.id, meshes['HighResMesh'])
    copy_sphere_mesh_from_template(settings.hcp_dir, settings.ciftify_data_dir,
            subject.id, meshes['HighResMesh'])

    ## incorporate the atlasroi boundries into the native space roi
    merge_subject_medial_wall_with_atlas_template(subject.id, settings.high_res,
            meshes, reg_sphere, temp_dir)

    ## remask the thickness and curvature data with the redefined medial wall roi
    dilate_and_mask_metric(subject.id, meshes['AtlasSpaceNative'],
            settings.dscalars)

    logger.info(section_header("Creating Native Space Dense Maps"))
    make_dense_map(subject.id, meshes['AtlasSpaceNative'],
            settings.dscalars)
    add_dense_maps_to_spec_file(subject.id, meshes['T1wNative'],
            settings.dscalars.keys())

    #Populate Highres fs_LR spec file.
    logger.info(section_header('Resampling data from Native to {}'
            ''.format(meshes['HighResMesh']['meshname'])))

    copy_colin_flat_and_add_to_spec(subject.id, settings.hcp_dir,
            settings.ciftify_data_dir, meshes['HighResMesh'])

    deform_to_native(meshes['AtlasSpaceNative'], meshes['HighResMesh'],
            settings.dscalars, subject.id, sphere=reg_sphere)

    # Populate LowRes fs_LR spec file.
    for res in settings.low_res:
        low_res_name = '{}k_fs_LR'.format(res)
        logger.info(section_header('Resampling data from Native to '
                '{}'.format(low_res_name)))
        populate_low_res_spec_file(meshes['AtlasSpaceNative'],
                meshes[low_res_name], subject, settings, reg_sphere)
        if not settings.resample:
            continue
        dest_mesh_name = 'Native{}k_fs_LR'.format(res)
        resample_to_native(meshes['AtlasSpaceNative'], meshes[dest_mesh_name],
                settings, subject.id, reg_sphere)
    # exit successfully
    return 0

if __name__ == '__main__':
    arguments  = docopt(__doc__)
    VERBOSE      = arguments['--verbose']
    DEBUG        = arguments['--debug']
    DRYRUN       = arguments['--dry-run']

    settings = Settings(arguments)

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    if VERBOSE:
        ch.setLevel(logging.INFO)
    if DEBUG:
        ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    fh = settings.subject.get_subject_log_handler(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(section_header("Starting fs2hcp"))
    with ciftify.utilities.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = main(tmpdir, settings)
    sys.exit(ret)
