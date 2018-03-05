#!/usr/bin/env python
"""
Converts a freesurfer recon-all output to a HCP data directory

Usage:
  ciftify_recon_all [options] <Subject>

Arguments:
    <Subject>               The Subject ID in the HCP data folder

Options:
  --ciftify-work-dir PATH     The directory for HCP subjects (overrides
                              CIFTIFY_WORKDIR/ HCP_DATA enivironment variables)
  --hcp-data-dir PATH         The directory for HCP subjects (overrides
                              CIFTIFY_WORKDIR/ HCP_DATA enivironment variables) DEPRECATED
  --fs-subjects-dir PATH      Path to the freesurfer SUBJECTS_DIR directory
                              (overides the SUBJECTS_DIR environment variable)
  --resample-to-T1w32k        Resample the Meshes to 32k Native (T1w) Space
  --MSMSulc                   Run MSMSulc surface registration (instead of using FS)
  --MSM-config PATH           The path to the configuration file to use for
                              MSMSulc mode. By default, the configuration file
                              is ciftify/data/hcp_config/MSMSulcStrainFinalconf
                              This setting is ignored when not running MSMSulc mode.
  --T2                        Include T2 files from freesurfer outputs
  --settings-yaml PATH        Path to a yaml configuration file. Overrides
                              the default settings in
                              ciftify/data/cifti_recon_settings.yaml
  -v,--verbose                Verbose logging
  --debug                     Debug logging in Erin's very verbose style
  -n,--dry-run                Dry run
  -h,--help                   Print help

DETAILS
Adapted from the PostFreeSurferPipeline module of the Human Connectome
Project's minimal proprocessing pipeline. Please cite:

Glasser MF, Sotiropoulos SN, Wilson JA, Coalson TS, Fischl B, Andersson JL, Xu J,
Jbabdi S, Webster M, Polimeni JR, Van Essen DC, Jenkinson M, WU-Minn HCP Consortium.
The minimal preprocessing pipelines for the Human Connectome Project. Neuroimage. 2013 Oct 15;80:105-24.
PubMed PMID: 23668970; PubMed Central PMCID: PMC3720813.

The default outputs are condensed to include in 4 mesh "spaces" in the following directories:
  + T1w/Native: The freesurfer "native" output meshes
  + MNINonLinear/Native: The T1w/Native mesh warped to MNINonLinear
  + MNINonLinear/fsaverage_LR32k
     + the surface registered space used for fMRI and multi-modal analysis
     + This 32k mesh has approx 2mm vertex spacing
  + MNINonLinear_164k_fs_LR (in the MNINonLinear folder):
     + the surface registered space used for HCP's anatomical analysis
     + This 164k mesh has approx 0.9mm vertex spacing

In addition, the optional flag '--resample-to-T1w32k' can be used to output an
additional T1w/fsaverage_LR32k folder that occur in the HCP Consortium Projects.

Note: --MSMSulc and --MSM-config options are still experimental. While the --T2
option does allow you to extract T2 weighted outputs that were submitted to recon_all.
If T2 weighted data is available, we strongly recommend using the HCP pipelines
rather than this command..

Written by Erin W Dickie
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
from ciftify.utils import WorkDirSettings, get_stdout, cd, section_header
from ciftify.filenames import *

logger = logging.getLogger('ciftify')
logger.setLevel(logging.DEBUG)

DRYRUN = False

def run_ciftify_recon_all(temp_dir, settings):
    subject = settings.subject

    log_inputs(settings.fs_root_dir, settings.hcp_dir, subject.id,
            settings.msm_config)
    log_build_environment(settings)

    fs_version = pars_recon_all_logs(subject.fs_folder)

    logger.debug("Defining Settings")
    ## the Meshes Dict contains file paths and naming conventions specific to
    ## all ouput meshes
    meshes = define_meshes(subject.path, settings.high_res, settings.low_res,
            temp_dir, settings.resample)

    expected_labels = define_expected_labels(fs_version)

    #Make some folders for this and later scripts
    create_output_directories(meshes, settings.registration['xfms_dir'],
            os.path.join(subject.atlas_space_dir, 'ROIs'),
            os.path.join(subject.atlas_space_dir, 'Results'))

    T1w_nii = os.path.join(subject.T1w_dir, settings.registration['T1wImage'])
    wmparc = os.path.join(subject.T1w_dir, 'wmparc.nii.gz')
    convert_T1_and_freesurfer_inputs(T1w_nii, subject,
            settings.ciftify_data_dir, T2_raw=settings.use_T2)
    prepare_T1_image(wmparc, T1w_nii, settings.registration)

    convert_inputs_to_MNI_space(settings.registration, settings.ciftify_data_dir,
            temp_dir, use_T2=settings.use_T2)

    #Create Spec Files including the T1w files
    add_anat_images_to_spec_files(meshes, subject.id)
    if settings.use_T2:
        add_anat_images_to_spec_files(meshes, subject.id, img_type='T2wImage')

    # Import Subcortical ROIs and resample to the Grayordinate Resolution
    create_cifti_subcortical_ROIs(subject.atlas_space_dir, settings.hcp_dir,
            settings.grayord_res, settings.ciftify_data_dir, temp_dir)
    convert_FS_surfaces_to_gifti(subject.id, subject.fs_folder, meshes,
            settings.registration, temp_dir)
    process_native_meshes(subject, meshes, settings.dscalars, expected_labels)

    ## copy the HighResMesh medialwall roi and the sphere mesh from the
    ## templates
    copy_atlas_roi_from_template(settings.hcp_dir, settings.ciftify_data_dir,
            subject.id, meshes['HighResMesh'])
    copy_sphere_mesh_from_template(settings.hcp_dir, settings.ciftify_data_dir,
            subject.id, meshes['HighResMesh'])

    reg_sphere = create_reg_sphere(settings, subject.id, meshes)

    logger.info(section_header("Importing HighRes Template Sphere and Medial "
            "Wall ROI"))

    ## incorporate the atlasroi boundries into the native space roi
    merge_subject_medial_wall_with_atlas_template(subject.id, settings.high_res,
            meshes, reg_sphere, temp_dir)

    ## remask the thickness and curvature data with the redefined medial wall roi
    dilate_and_mask_metric(subject.id, meshes['AtlasSpaceNative'],
            settings.dscalars)

    logger.info(section_header("Creating Native Space Dense Maps"))
    make_dense_map(subject.id, meshes['AtlasSpaceNative'],
            settings.dscalars, expected_labels)
    add_dense_maps_to_spec_file(subject.id, meshes['T1wNative'],
            settings.dscalars.keys(), expected_labels)

    #Populate Highres fs_LR spec file.
    logger.info(section_header('Resampling data from Native to {}'
            ''.format(meshes['HighResMesh']['meshname'])))

    copy_colin_flat_and_add_to_spec(subject.id, settings.hcp_dir,
            settings.ciftify_data_dir, meshes['HighResMesh'])

    deform_to_native(meshes['AtlasSpaceNative'], meshes['HighResMesh'],
            settings.dscalars, expected_labels, subject.id, sphere=reg_sphere)

    # Populate LowRes fs_LR spec file.
    for res in settings.low_res:
        low_res_name = '{}k_fs_LR'.format(res)
        logger.info(section_header('Resampling data from Native to '
                '{}'.format(low_res_name)))
        populate_low_res_spec_file(meshes['AtlasSpaceNative'],
                meshes[low_res_name], subject, settings, reg_sphere, expected_labels)
        if not settings.resample:
            continue
        dest_mesh_name = 'Native{}k_fs_LR'.format(res)
        resample_to_native(meshes['AtlasSpaceNative'], meshes[dest_mesh_name],
                settings, subject.id, reg_sphere, expected_labels)
    # exit successfully
    logger.info(section_header('Done'))
    return 0

def run(cmd, dryrun = False, suppress_stdout = False, suppress_stderr = False):
    ''' calls the run function with specific settings'''
    global DRYRUN
    dryrun = DRYRUN or dryrun
    returncode = ciftify.utils.run(cmd,
                                       dryrun = dryrun,
                                       suppress_stdout = suppress_stdout,
                                       suppress_stderr = suppress_stderr)
    if returncode :
        sys.exit(1)
    return(returncode)

class Settings(WorkDirSettings):
    def __init__(self, arguments):
        WorkDirSettings.__init__(self, arguments)
        self.reg_name = self.__set_registration_mode(arguments)
        self.resample = arguments['--resample-to-T1w32k']
        self.fs_root_dir = self.__set_fs_subjects_dir(arguments)
        self.subject = self.__get_subject(arguments)
        self.FSL_dir = self.__set_FSL_dir()
        self.ciftify_data_dir = self.__get_ciftify_data()
        self.use_T2 = self.__get_T2(arguments, self.subject)

        # Read settings from yaml
        self.__config = self.__read_settings(arguments['--settings-yaml'])
        self.high_res = self.__get_config_entry('high_res')
        self.low_res = self.__get_config_entry('low_res')
        self.grayord_res = self.__get_config_entry('grayord_res')
        self.dscalars = self.__define_dscalars()
        self.registration = self.__define_registration_settings()

    def __set_registration_mode(self, arguments):
        """
        Must be set after ciftify_data_dir is set, since it requires this
        for MSMSulc config
        """
        if arguments['--MSMSulc']:
            verify_msm_available()
            user_config = arguments['--MSM-config']
            if not user_config:
                self.msm_config = os.path.join(self.__get_ciftify_data(),
                        'hcp_config', 'MSMSulcStrainFinalconf')
            elif user_config and not os.path.exists(user_config):
                logger.error("MSM config file {} does not exist".format(user_config))
                sys.exit(1)
            else:
                self.msm_config = user_config
            return 'MSMSulc'
        self.msm_config = None
        return 'FS'

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
        fsl_data = os.path.normpath(os.path.join(fsl_dir, 'data'))
        if not os.path.exists(fsl_data):
            logger.warn("Found {} for FSL path but {} does not exist. May "
                    "prevent registration files from being found.".format(
                    fsl_dir, fsl_data))
        return fsl_dir

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
                    '../data/cifti_recon_settings.yaml')
        if not os.path.exists(yaml_file):
            logger.critical("Settings yaml file {} does not exist"
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
            logger.critical("{} not defined in cifti recon settings".format(key))
            sys.exit(1)
        return config_entry

    def __define_dscalars(self):
        dscalars_config = self.__get_config_entry('dscalars')
        if self.reg_name != 'MSMSulc':
            try:
                del dscalars_config['ArealDistortion_MSMSulc']
                del dscalars_config['EdgeDistortion_MSMSulc']
            except KeyError:
                # do nothing, MSMSulc options not defined anyway
                pass
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

    def __get_T2(self, arguments, subject):
        if not arguments['--T2']:
            return None
        raw_T2 = os.path.join(subject.fs_folder, 'mri/orig/T2raw.mgz')
        if not os.path.exists(raw_T2):
            return None
        return raw_T2

class Subject(object):
    def __init__(self, hcp_dir, fs_root_dir, subject_id):
        self.id = subject_id
        self.fs_folder = self.__set_fs_folder(fs_root_dir)
        self.path = self.__set_path(hcp_dir)
        self.T1w_dir = os.path.join(self.path, 'T1w')
        self.atlas_space_dir = os.path.join(self.path, 'MNINonLinear')
        self.log = os.path.join(self.path, 'cifti_recon_all.log')

    def __set_fs_folder(self, fs_root_dir):
        fs_path = os.path.join(fs_root_dir, self.id)
        if not os.path.exists(fs_path):
            logger.error("{} freesurfer folder does not exist, exiting."
                    "".format(self.id))
            sys.exit(1)
        return fs_path

    def __set_path(self, hcp_dir):
        path = os.path.join(hcp_dir, self.id)
        if os.path.exists(path):
            logger.error('Subject output {} already exisits.'
                'If you wish to re-run, you must first delete old outputs.'
                ''.format(path))
            sys.exit(1)
        else:
            try:
                os.makedirs(path)
            except:
                logger.error("Cannot make subject path {}, exiting"
                            "".format(path))
                sys.exit(1)
        return path

    def get_subject_log_handler(self, formatter):
        fh = logging.FileHandler(self.log)
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        return fh


############ Step 0: Settings and Logging #############################
def log_inputs(fs_dir, hcp_dir, subject_id, msm_config=None):
    logger.info("Arguments: ")
    logger.info('    freesurfer SUBJECTS_DIR: {}'.format(fs_dir))
    logger.info('    HCP_DATA directory: {}'.format(hcp_dir))
    logger.info('    Subject: {}'.format(subject_id))
    if msm_config:
        logger.info('    MSM config file: {}'.format(msm_config))

def log_build_environment(settings):
    '''print the running environment info to the logs (info)'''
    logger.info("{}---### Environment Settings ###---".format(os.linesep))
    logger.info("Username: {}".format(get_stdout(['whoami'],
            echo=False).replace(os.linesep,'')))
    logger.info(ciftify.config.system_info())
    logger.info(ciftify.config.ciftify_version(os.path.basename(__file__)))
    logger.info(ciftify.config.wb_command_version())
    logger.info(ciftify.config.freesurfer_version())
    logger.info(ciftify.config.fsl_version())
    if settings.msm_config: logger.info(ciftify.config.msm_version())
    logger.info("---### End of Environment Settings ###---{}".format(os.linesep))

def verify_msm_available():
    msm = ciftify.config.find_msm()
    if not msm:
        logger.error("Cannot find \'msm\' binary. Please ensure FSL 5.0.10 is "
                "installed, or run without the --MSMSulc option")
        sys.exit(1)

def pars_recon_all_logs(fs_folder):
    '''prints recon_all run settings to the log '''
    fslog = ciftify.config.FSLog(fs_folder)
    sep = '{}    '.format(os.linesep)
    freesurfer_info = "recon_all was run {1} with settings:{0}Build Stamp: "\
                "{2}{0}Version parsed as: {3}{0}CMD args: {4}{0}".format(
                sep, fslog.start, fslog.build, fslog.version, fslog.cmdargs)
    logger.info(freesurfer_info)
    if len(fslog.status) > 0:
        logger.warning(fslog.status)
    return fslog.version

def define_expected_labels(fs_version):
    ''' figures out labels according to freesurfer version run '''
    expected_labels = ['aparc', 'aparc.a2009s', 'BA', 'aparc.DKTatlas',
            'BA_exvivo']
    if fs_version == 'v6.0.0':
        expected_labels.remove('BA')
    if 'v5.' in fs_version:
        expected_labels.remove('aparc.DKTatlas')
        expected_labels.remove('BA_exvivo')
    return expected_labels

def create_output_directories(meshes, xfms_dir, rois_dir, results_dir):
    for mesh in meshes.values():
        ciftify.utils.make_dir(mesh['Folder'], DRYRUN)
        ciftify.utils.make_dir(mesh['tmpdir'], DRYRUN)
    ciftify.utils.make_dir(xfms_dir, DRYRUN)
    ciftify.utils.make_dir(rois_dir, DRYRUN)
    ciftify.utils.make_dir(results_dir, DRYRUN)

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
        if not os.path.exists(via_folder):
                run(['mkdir','-p',via_folder], dryrun=DRYRUN)
        run(['cp', global_file, via_file], dryrun=DRYRUN)
    ## link the subject_file to via_file
    os.symlink(os.path.relpath(via_file, os.path.dirname(subject_file)),
               subject_file)

## Step 1: Conversion from Freesurfer Format ######################
## Step 1.0: Conversion of Freesurfer Volumes #####################
def convert_T1_and_freesurfer_inputs(T1w_nii, subject, hcp_templates,
        T2_raw=None):
    logger.info(section_header("Converting T1wImage and Segmentations from "
            "freesurfer"))
    ###### convert the mgz T1w and put in T1w folder
    convert_freesurfer_T1(subject.fs_folder, T1w_nii)
    #Convert FreeSurfer Volumes and import the label metadata
    for image in ['wmparc', 'aparc.a2009s+aseg', 'aparc+aseg']:
      convert_freesurfer_mgz(image, T1w_nii, hcp_templates, subject.fs_folder,
            subject.T1w_dir)
    if T2_raw:
        T2w_nii = os.path.join(subject.T1w_dir, 'T2w.nii.gz')
        resample_freesurfer_mgz(T1w_nii, T2_raw, T2w_nii)

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
    run(['mri_convert', fs_T1, T1w_nii], dryrun=DRYRUN)
    run(['fslreorient2std', T1w_nii, T1w_nii], dryrun=DRYRUN)

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
        if freesurfer_mgz == 'wmparc.mgz':
            logger.error("{} not found, exiting.".format(freesurfer_mgz))
            sys.exit(1)
        else:
            logger.warning("{} not found".format(freesurfer_mgz))
    else:
        image_nii = os.path.join(out_dir, '{}.nii.gz'.format(image_name))
        resample_freesurfer_mgz(T1w_nii, freesurfer_mgz, image_nii)
        run(['wb_command', '-logging', 'SEVERE','-volume-label-import', image_nii,
                os.path.join(hcp_templates, 'hcp_config', 'FreeSurferAllLut.txt'),
                image_nii, '-drop-unused-labels'], dryrun=DRYRUN)

def resample_freesurfer_mgz(T1w_nii, freesurfer_mgz, image_nii):
    run(['mri_convert', '-rt', 'nearest', '-rl', T1w_nii, freesurfer_mgz,
            image_nii], dryrun=DRYRUN)

## Step 1.1: Creating Brainmask from wmparc #######################
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

def make_brain_mask_from_wmparc(wmparc_nii, brain_mask):
    '''
    Will create a brainmask_nii image out of the wmparc ROIs nifti converted
    from freesurfer
    '''
    ## Create FreeSurfer Brain Mask skipping 1mm version...
    run(['fslmaths', wmparc_nii,
        '-bin', '-dilD', '-dilD', '-dilD', '-ero', '-ero',
        brain_mask], dryrun=DRYRUN)
    run(['wb_command', '-volume-fill-holes', brain_mask, brain_mask],
            dryrun=DRYRUN)
    run(['fslmaths', brain_mask, '-bin', brain_mask], dryrun=DRYRUN)

def mask_T1w_image(T1w_image, brain_mask, T1w_brain):
    '''mask the T1w Image with the brain_mask to create the T1w_brain image'''
    run(['fslmaths', T1w_image, '-mul', brain_mask, T1w_brain], dryrun=DRYRUN)

## Step 1.2: running FSL registration #############################

def convert_inputs_to_MNI_space(reg_settings, hcp_templates, temp_dir,
        use_T2=None):
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

    if use_T2:
        # Transform T2 to MNI space too
        apply_nonlinear_warp_to_nifti_rois('T2w', reg_settings, hcp_templates,
                import_labels=False)

def run_T1_FNIRT_registration(reg_settings, temp_dir):
    '''
    Run the registration from T1w to MNINonLinear space using FSL's fnirt
    registration settings and file paths are read from reg_settings
    '''
    src_dir = reg_settings['src_dir']
    T1wBrain = reg_settings['T1wBrain']
    standard_T1wBrain = reg_settings['standard_T1wBrain']
    xfms_dir = reg_settings['xfms_dir']
    AtlasTransform_Linear = reg_settings['AtlasTransform_Linear']
    standard_BrainMask = reg_settings['standard_BrainMask']
    AtlasTransform_NonLinear = reg_settings['AtlasTransform_NonLinear']
    FNIRTConfig = reg_settings['FNIRTConfig']
    InverseAtlasTransform_NonLinear = reg_settings['InverseAtlasTransform_NonLinear']
    standard_T1wImage = reg_settings['standard_T1wImage']
    T1wImage = reg_settings['T1wImage']
    dest_dir = reg_settings['dest_dir']

    ## Linear then non-linear registration to MNI
    T1w2_standard_linear = os.path.join(temp_dir,
            'T1w2StandardLinearImage.nii.gz')
    run(['flirt', '-interp', 'spline', '-dof', '12',
        '-in', os.path.join(src_dir, T1wBrain), '-ref', standard_T1wBrain,
        '-omat', os.path.join(xfms_dir, AtlasTransform_Linear),
        '-o', T1w2_standard_linear], dryrun=DRYRUN)
    ## calculate the just the warp for the surface transform - need it because
    ## sometimes the brain is outside the bounding box of warfield
    run(['fnirt','--in={}'.format(T1w2_standard_linear),
         '--ref={}'.format(standard_T1wImage),
         '--refmask={}'.format(standard_BrainMask),
         '--fout={}'.format(os.path.join(xfms_dir, AtlasTransform_NonLinear)),
         '--logout={}'.format(os.path.join(xfms_dir, 'NonlinearReg_fromlinear.log')),
         '--config={}'.format(FNIRTConfig)], dryrun=DRYRUN)
    ## also inverse the non-prelinear warp - we will need it for the surface
    ## transforms
    run(['invwarp', '-w', os.path.join(xfms_dir, AtlasTransform_NonLinear),
         '-o', os.path.join(xfms_dir,InverseAtlasTransform_NonLinear),
         '-r', standard_T1wImage], dryrun=DRYRUN)
    ##T1w set of warped outputs (brain/whole-head + restored/orig)
    run(['applywarp', '--rel', '--interp=trilinear',
         '-i', os.path.join(src_dir, T1wImage),
         '-r', standard_T1wImage, '-w', os.path.join(xfms_dir, AtlasTransform_NonLinear),
         '--premat={}'.format(os.path.join(xfms_dir,AtlasTransform_Linear)),
         '-o', os.path.join(dest_dir, T1wImage)], dryrun=DRYRUN)

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
             '-o', image_dest], dryrun=DRYRUN)
        if import_labels:
            run(['wb_command', '-volume-label-import', '-logging', 'SEVERE',
                    image_dest, fs_labels, image_dest, '-drop-unused-labels'],
                    dryrun=DRYRUN)

def add_anat_images_to_spec_files(meshes, subject_id, img_type='T1wImage'):
    '''add all the T1wImages to their associated spec_files'''
    for mesh in meshes.values():
         run(['wb_command', '-add-to-spec-file',
              os.path.realpath(spec_file(subject_id, mesh)),
              'INVALID', os.path.realpath(mesh[img_type])], dryrun=DRYRUN)

## Step 1.5 Create Subcortical ROIs  ###########################

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
            'wmparc.nii.gz'), '-r', atlas_ROIs, '-o', wmparc_ROIs], dryrun=DRYRUN)
        ## import the label metadata
        run(['wb_command', '-logging', 'SEVERE', '-volume-label-import', wmparc_ROIs,
            freesurfer_labels, wmparc_ROIs, '-drop-unused-labels'], dryrun=DRYRUN)
        ## These commands were used in the original fs2hcp script, Erin
        ## discovered they are probably not being used. Leaving these commands
        ## here, though, just in case
        #   run(['applywarp', '--interp=nn', '-i', Avgwmparc, '-r', Atlas_ROIs,
        #       '-o', wmparcAtlas_ROIs])
        #   run(['wb_command', '-volume-label-import',
        #     wmparcAtlas_ROIs, FreeSurferLabels,  wmparcAtlas_ROIs,
        #     '-drop-unused-labels'])
        run(['wb_command', '-logging', 'SEVERE', '-volume-label-import', wmparc_ROIs,
            subcortical_gray_labels, ROIs_nii,'-discard-others'], dryrun=DRYRUN)

## Step 1.4 Conversion of other formats ###########################

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
                label_gii], suppress_stderr = True, dryrun=DRYRUN)
            run(['wb_command', '-set-structure', label_gii, structure],
                    dryrun=DRYRUN)
            run(['wb_command', '-set-map-names', label_gii,
                '-map', '1', '{}_{}_{}'.format(subject_id, hemisphere,
                label_name)], dryrun=DRYRUN)
            run(['wb_command', '-gifti-label-add-prefix',
                label_gii, '{}_'.format(hemisphere), label_gii], dryrun=DRYRUN)

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
            reg_settings['standard_T1wImage']], dryrun=DRYRUN)
        run(['wb_command', '-surface-apply-warpfield', surf_dest,
            os.path.join(xfms_dir, reg_settings['InverseAtlasTransform_NonLinear']),
            surf_dest, '-fnirt', os.path.join(xfms_dir,
            reg_settings['AtlasTransform_NonLinear'])], dryrun=DRYRUN)
        run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
            dest_mesh_settings), structure, surf_dest], dryrun=DRYRUN)

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
        run(['mris_convert',surf_fs, surf_native], dryrun=DRYRUN)

        set_structure_command = ['wb_command', '-set-structure', surf_native,
                structure, '-surface-type', surface_type]
        if surface_secondary_type:
            set_structure_command.extend(['-surface-secondary-type',
                    surface_secondary_type])
        run(set_structure_command, dryrun=DRYRUN)

        if cras_mat:
            run(['wb_command', '-surface-apply-affine', surf_native,
                    cras_mat, surf_native], dryrun=DRYRUN)
        if add_to_spec:
            run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
                    dest_mesh_settings), structure, surf_native], dryrun=DRYRUN)

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
            map_gii], dryrun=DRYRUN)
        ## set a bunch of meta-data and multiply by -1
        run(['wb_command', '-set-structure', map_gii, structure], dryrun=DRYRUN)
        run(['wb_command', '-metric-math', '"(var * -1)"',
            map_gii, '-var', 'var', map_gii], dryrun=DRYRUN)
        run(['wb_command', '-set-map-names', map_gii,
            '-map', '1', '{}_{}{}'.format(subject_id, hemisphere,
            map_dict['map_postfix'])], dryrun=DRYRUN)
        if map_dict['mapname'] == 'thickness':
            ## I don't know why but there are thickness specific extra steps
            # Thickness set thickness at absolute value than set palette metadata
            run(['wb_command', '-metric-math', '"(abs(thickness))"',
                map_gii, '-var', 'thickness', map_gii], dryrun=DRYRUN)
        run(['wb_command', '-metric-palette', map_gii, map_dict['palette_mode'],
            map_dict['palette_options']], dryrun=DRYRUN)

## Step 2.0 Fucntions Called Multiple times ##############################

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
            '-surf', surf_file(subject_id, 'pial', hemisphere, mesh_settings)],
            dryrun=DRYRUN)
        run(['wb_command', '-set-structure', mid_surf, structure,
            '-surface-type', 'ANATOMICAL', '-surface-secondary-type',
            'MIDTHICKNESS'], dryrun=DRYRUN)
        run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
            mesh_settings), structure, mid_surf], dryrun=DRYRUN)

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
            infl_surf, vinfl_surf, '-iterations-scale', str(iterations_scale)],
            dryrun=DRYRUN)
        run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
            mesh_settings), structure, infl_surf], dryrun=DRYRUN)
        run(['wb_command', '-add-to-spec-file', spec_file(subject_id,
            mesh_settings), structure, vinfl_surf], dryrun=DRYRUN)

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
            medial_wall_roi_file(subject_id, 'R', mesh_settings)], dryrun=DRYRUN)
    else :
        run(['wb_command', '-cifti-create-dense-scalar', dscalar_file,
                '-left-metric', left_metric, '-right-metric', right_metric],
                dryrun=DRYRUN)

    ## set the dscalar file metadata
    run(['wb_command', '-set-map-names', dscalar_file,
        '-map', '1', "{}{}".format(subject_id, dscalar_entry['map_postfix'])],
        dryrun=DRYRUN)
    run(['wb_command', '-cifti-palette', dscalar_file,
        dscalar_entry['palette_mode'], dscalar_file,
        dscalar_entry['palette_options']], dryrun=DRYRUN)

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
        logger.warning("label file {} does not exist. Skipping dlabel creation."
                "".format(left_label))
        return
    ## combine left and right metrics into a dscalar file
    run(['wb_command', '-cifti-create-label', dlabel_file,
        '-left-label', left_label,'-roi-left',
        medial_wall_roi_file(subject_id, 'L', mesh_settings),
        '-right-label', right_label,'-roi-right',
        medial_wall_roi_file(subject_id, 'R', mesh_settings)], dryrun=DRYRUN)
    ## set the dscalar file metadata
    run(['wb_command', '-set-map-names', dlabel_file, '-map', '1',
        "{}_{}".format(subject_id, label_name)], dryrun=DRYRUN)

def add_dense_maps_to_spec_file(subject_id, mesh_settings,
                                dscalar_types, expected_labels):
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
                    mesh_settings['meshname'])))], dryrun=DRYRUN)

    for label_name in expected_labels:
        file_name = "{}.{}.{}.dlabel.nii".format(subject_id, label_name,
                mesh_settings['meshname'])
        dlabel_file = os.path.realpath(os.path.join(maps_folder, file_name))
        if not os.path.exists(dlabel_file):
            logger.debug("dlabel file {} does not exist, skipping".format(
                    dlabel_file))
            continue
        run(['wb_command', '-add-to-spec-file', os.path.realpath(spec_file(
                subject_id, mesh_settings)), 'INVALID', dlabel_file],
                dryrun=DRYRUN)

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
            mesh_settings), structure, colin_dest], dryrun=DRYRUN)

def make_dense_map(subject_id, mesh, dscalars, expected_labels):
    ## combine L and R metrics into dscalar files
    for map_type in expected_labels:
        create_dlabel(subject_id, mesh, map_type)

    ## combine L and R labels into a dlabel file
    for map_name in dscalars.keys():
        create_dscalar(subject_id, mesh, dscalars[map_name])

    ## add all the dscalar and dlabel files to the spec file
    add_dense_maps_to_spec_file(subject_id, mesh,
                                dscalars.keys(), expected_labels)

## Step 2.1 Working with Native Mesh  #################

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
            mesh_settings), structure, sphere_dest], dryrun=DRYRUN)

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

def process_native_meshes(subject, meshes, dscalars, expected_labels):
    logger.info(section_header("Creating midthickness, inflated and "
            "very_inflated surfaces"))
    for mesh_name in ['T1wNative', 'AtlasSpaceNative']:
        ## build midthickness out the white and pial
        make_midthickness_surfaces(subject.id, meshes[mesh_name])
        # make inflated surfaces from midthickness
        make_inflated_surfaces(subject.id, meshes[mesh_name])

    # Convert freesurfer annotation to gifti labels and set meta-data
    logger.info(section_header("Converting Freesurfer measures to gifti"))
    for label_name in expected_labels:
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
            mesh_settings)], dryrun=DRYRUN)
        run(['wb_command', '-metric-fill-holes', midthickness_gii, native_roi,
            native_roi], dryrun=DRYRUN)
        run(['wb_command', '-metric-remove-islands', midthickness_gii,
            native_roi, native_roi], dryrun=DRYRUN)
        run(['wb_command', '-set-map-names', native_roi, '-map', '1',
            '{}_{}_ROI'.format(subject_id, hemisphere)], dryrun=DRYRUN)

## Step 3.0 Surface Registration ##################################

def create_reg_sphere(settings, subject_id, meshes):
    logger.info(section_header("Concatenating Freesurfer Reg with template to "
            "get fs_LR reg"))

    FS_reg_sphere_name = 'sphere.reg.reg_LR'
    run_fs_reg_LR(subject_id, settings.ciftify_data_dir, settings.high_res,
            FS_reg_sphere_name, meshes['AtlasSpaceNative'])

    if settings.reg_name == 'MSMSulc':
        reg_sphere_name = 'sphere.MSMSulc'
        run_MSMSulc_registration(subject_id, settings.ciftify_data_dir,
                    meshes, reg_sphere_name, FS_reg_sphere_name, settings.msm_config)
    else :
        reg_sphere_name = FS_reg_sphere_name
    return reg_sphere_name

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
                    fs_reg_sphere], dryrun=DRYRUN)

        #Make FreeSurfer Registration Areal Distortion Maps
        calc_areal_distortion_gii(
                surf_file(subject_id, 'sphere', hemisphere,
                        native_mesh_settings),
                fs_reg_sphere,
                metric_file(subject_id, 'ArealDistortion_FS', hemisphere,
                        native_mesh_settings),
                '{}_{}'.format(subject_id, hemisphere), 'FS')

def run_MSMSulc_registration(subject, ciftify_data_dir, mesh_settings,
        reg_sphere_name, FS_reg_sphere, msm_config):
    native_settings = mesh_settings['AtlasSpaceNative']
    highres_settings = mesh_settings['HighResMesh']

    ## define and create a folder to hold MSMSulc reg related files.
    MSMSulc_dir = os.path.join(native_settings['Folder'], 'MSMSulc')
    ciftify.utils.make_dir(MSMSulc_dir, DRYRUN)

    for hemisphere, structure in [('L', 'CORTEX_LEFT'), ('R', 'CORTEX_RIGHT')]:
        ## prepare data for MSMSulc registration
        ## calculate and affine surface registration to FS mesh
        native_sphere = surf_file(subject, 'sphere', hemisphere, native_settings)
        fs_LR_sphere = surf_file(subject, FS_reg_sphere, hemisphere, native_settings)
        affine_mat = os.path.join(MSMSulc_dir, '{}.mat'.format(hemisphere))
        affine_rot_gii = os.path.join(MSMSulc_dir, '{}.sphere_rot.surf.gii'.format(hemisphere))
        run(['wb_command', '-surface-affine-regression',
                native_sphere, fs_LR_sphere, affine_mat])
        run(['wb_command', '-surface-apply-affine',
                native_sphere, affine_mat, affine_rot_gii])
        run(['wb_command', '-surface-modify-sphere',
                affine_rot_gii, "100", affine_rot_gii])

        ## run MSM with affine rotated surf at start point
        native_rot_sphere = surf_file(subject, 'sphere.rot', hemisphere, native_settings)
        refsulc_metric = os.path.join(ciftify_data_dir,
                                      'standard_mesh_atlases',
                                      '{}.refsulc.{}.shape.gii'.format(hemisphere,
                                            highres_settings['meshname']))

        run(['cp', affine_rot_gii, native_rot_sphere])

        with cd(MSMSulc_dir):
            run(['msm', '--conf={}'.format(msm_config),
                    '--inmesh={}'.format(native_rot_sphere),
                    '--refmesh={}'.format(surf_file(subject, 'sphere', hemisphere,
                            highres_settings)),
                    '--indata={}'.format(metric_file(subject, 'sulc', hemisphere,
                            native_settings)),
                    '--refdata={}'.format(refsulc_metric),
                    '--out={}'.format(os.path.join(MSMSulc_dir,
                            '{}.'.format(hemisphere))),
                    '--verbose'])

        conf_log = os.path.join(MSMSulc_dir, '{}.logdir'.format(hemisphere),'conf')
        run(['cp', msm_config, conf_log])

        #copy the MSMSulc outputs into Native folder and calculate Distortion
        MSMsulc_sphere = surf_file(subject, reg_sphere_name, hemisphere, native_settings)
        run(['cp', os.path.join(MSMSulc_dir, '{}.sphere.reg.surf.gii'.format(hemisphere)),
                MSMsulc_sphere])
        run(['wb_command', '-set-structure', MSMsulc_sphere, structure])

        #Make MSMSulc Registration Areal Distortion Maps
        calc_areal_distortion_gii(native_sphere, MSMsulc_sphere,
                metric_file(subject, 'ArealDistortion_MSMSulc', hemisphere, native_settings),
                '{}_{}_'.format(subject, hemisphere), '_MSMSulc')

        run(['wb_command', '-surface-distortion',
                native_sphere, MSMsulc_sphere,
                metric_file(subject, 'EdgeDistortion_MSMSulc',hemisphere, native_settings),
                '-edge-method'])

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
    with ciftify.utils.TempDir() as va_tmpdir:
        pre_va = os.path.join(va_tmpdir, 'sphere_pre_va.shape.gii')
        reg_va = os.path.join(va_tmpdir, 'sphere_reg_va.shape.gii')
        ## calculate surface vertex areas from pre and post files
        run(['wb_command', '-surface-vertex-areas', sphere_pre, pre_va],
                dryrun=DRYRUN)
        run(['wb_command', '-surface-vertex-areas', sphere_reg, reg_va],
                dryrun=DRYRUN)
        ## caluculate Areal Distortion using the vertex areas
        run(['wb_command', '-metric-math', '"(ln(spherereg / sphere) / ln(2))"',
            AD_gii_out, '-var', 'sphere', pre_va, '-var', 'spherereg', reg_va],
                dryrun=DRYRUN)
        ## set meta-data for the ArealDistotion files
        run(['wb_command', '-set-map-names', AD_gii_out,
            '-map', '1', '{}_Areal_Distortion_{}'.format(map_prefix,
            map_postfix)], dryrun=DRYRUN)
        run(['wb_command', '-metric-palette', AD_gii_out, 'MODE_AUTO_SCALE',
            '-palette-name', 'ROY-BIG-BL', '-thresholding',
            'THRESHOLD_TYPE_NORMAL', 'THRESHOLD_TEST_SHOW_OUTSIDE', '-1', '1'],
            dryrun=DRYRUN)

## Step 4.0 Post Registration Native Mesh #######################

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
            'BARYCENTRIC', atlas_roi_native_gii,'-largest'], dryrun=DRYRUN)
        run(['wb_command', '-metric-math', '"(atlas + individual) > 0"',
            native_roi, '-var', 'atlas', atlas_roi_native_gii, '-var',
            'individual', native_roi], dryrun=DRYRUN)

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
                '10', metric_map,'-nearest'], dryrun=DRYRUN)
            ## apply the medial wall roi to the thickness and curvature files
            run(['wb_command', '-metric-mask', metric_map,
                medial_wall_roi_file(subject_id, hemisphere,
                        native_mesh_settings),
                metric_map], dryrun=DRYRUN)

## Step 4.1 Resampling Mesh to other Spaces #######################

def populate_low_res_spec_file(source_mesh, dest_mesh, subject, settings,
        sphere, expected_labels):
    copy_atlas_roi_from_template(settings.hcp_dir, settings.ciftify_data_dir,
            subject.id, dest_mesh)
    copy_sphere_mesh_from_template(settings.hcp_dir, settings.ciftify_data_dir,
            subject.id, dest_mesh)
    copy_colin_flat_and_add_to_spec(subject.id, settings.hcp_dir,
            settings.ciftify_data_dir, dest_mesh)
    deform_to_native(source_mesh, dest_mesh, settings.dscalars, expected_labels,
            subject.id, sphere, scale=0.75)

def deform_to_native(native_mesh, dest_mesh, dscalars, expected_labels, subject_id,
        sphere='sphere', scale=2.5):
    resample_surfs_and_add_to_spec(subject_id, native_mesh, dest_mesh,
            current_sphere=sphere)
    make_inflated_surfaces(subject_id, dest_mesh, iterations_scale=scale)
    resample_metric_and_label(subject_id, dscalars, expected_labels, native_mesh, dest_mesh,
            sphere)
    make_dense_map(subject_id, dest_mesh, dscalars, expected_labels)

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
                current_sphere_surf, dest_sphere_surf, 'BARYCENTRIC', surf_out],
                dryrun=DRYRUN)
            run(['wb_command', '-add-to-spec-file',
                spec_file(subject_id, dest_mesh), structure, surf_out],
                dryrun=DRYRUN)

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
            source_mesh)], dryrun=DRYRUN)
        run(['wb_command', '-metric-mask', metric_out,
            medial_wall_roi_file(subject_id, hemisphere, dest_mesh), metric_out],
            dryrun=DRYRUN)
    else:
        run(['wb_command', '-metric-resample', metric_in, current_sphere_surf,
            dest_sphere_surf, 'ADAP_BARY_AREA', metric_out,
            '-area-surfs', current_midthickness, new_midthickness],
            dryrun=DRYRUN)

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
            '-largest'], dryrun=DRYRUN)

def resample_to_native(native_mesh, dest_mesh, settings, subject_id,
        sphere, expected_labels):
    copy_sphere_mesh_from_template(settings.hcp_dir, settings.ciftify_data_dir,
            subject_id, dest_mesh)
    resample_surfs_and_add_to_spec(subject_id, native_mesh, dest_mesh,
            current_sphere=sphere)
    make_inflated_surfaces(subject_id, dest_mesh, iterations_scale=0.75)
    add_dense_maps_to_spec_file(subject_id, dest_mesh,
            settings.dscalars.keys(), expected_labels)

def resample_metric_and_label(subject_id, dscalars, expected_labels,
        source_mesh, dest_mesh, current_sphere):
    for hemisphere in ['L', 'R']:
        ## resample the metric data to the new mesh
        for map_name in dscalars.keys():
            resample_and_mask_metric(subject_id, dscalars[map_name], hemisphere,
                    source_mesh, dest_mesh, current_sphere=current_sphere)
        ## resample all the label data to the new mesh
        for map_name in expected_labels:
            resample_label(subject_id, map_name, hemisphere, source_mesh,
                    dest_mesh, current_sphere=current_sphere)

## The main function ################################################


def main():
    arguments  = docopt(__doc__)
    verbose      = arguments['--verbose']
    debug        = arguments['--debug']
    DRYRUN       = arguments['--dry-run']

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    if verbose:
        ch.setLevel(logging.INFO)
    if debug:
        ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Get settings, and add an extra handler for the subject log
    settings = Settings(arguments)
    fh = settings.subject.get_subject_log_handler(formatter)
    logger.addHandler(fh)

    if arguments['--T2'] and not settings.use_T2:
        logger.error("Cannot locate T2 for {} in freesurfer "
                "outputs".format(settings.subject.id))

    logger.info(ciftify.utils.ciftify_logo())
    logger.info(section_header("Starting cifti_recon_all"))
    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        run_ciftify_recon_all(tmpdir, settings)

if __name__ == '__main__':
    main()
