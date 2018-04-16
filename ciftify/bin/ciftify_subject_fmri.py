#!/usr/bin/env python
"""
Projects a fMRI timeseries to and HCP dtseries file and does smoothing

Usage:
  ciftify_subject_fmri [options] <func.nii.gz> <subject> <task_label>

Arguments:
    <func.nii.gz>           Nifty 4D volume to project to cifti space
    <subject>               The Subject ID in the HCP data folder
    <task_label>            The outputname for the cifti result folder

Options:
  --SmoothingFWHM MM          The Full-Width-at-Half-Max for smoothing steps
  --ciftify-work-dir PATH     The ciftify working directory (overrides
                              CIFTIFY_WORKDIR enivironment variable)

  --surf-reg REGNAME          Registration sphere prefix [default: FS]
  --FLIRT-to-T1w              Will register to T1w space (not recommended, see DETAILS)
  --func-ref ref              Type/or path of image to use [default: "first_vol"]
                              as reference for when realigning or resampling images. See DETAILS.
  --already-in-MNI            Functional volume has already been registered to MNI
                              space using the same transform in as the ciftified anatomical data
  --OutputSurfDiagnostics     Output some extra files for QCing the surface
                              mapping.
  --DilateBelowPct PCT        Add a step to dilate places where signal intensity
                              is below this percentage. (DEPRECATED)
  --hcp-data-dir PATH         DEPRECATED, use --ciftify-work-dir instead
  -v,--verbose                Verbose logging
  --debug                     Debug logging in Erin's very verbose style
  -n,--dry-run                Dry run
  -h,--help                   Print help

DETAILS

The default surface registration is now FS (freesurfer), althought MSMSulc is highly recommended.
If MSMSulc registration has been done specifiy this with "--surf-reg MSMSulc".

The default behaviour assumes that the functional data has already been distortion
corrected and realigned to the T1w anatomical image.  If this is not the case, the
"--FLIRT-to-T1w" flag can be used to run a simple linear tranform (using FSL's FLIRT)
between the functional and the anatomical data. Note, that is linear transform is
not ideal as it is other packages (i.e. fmriprep) do offer much better registation results.

The "--func-ref" flag allows the user to specify how a reference image for the
functional data should be calcualted (by using the "first_vol" or "median" options)
or to provide the path to an additional file to use as a registation intermediate.
Acceptable options are "first_vol" (to use the first volume), "median"
to use the median. The default is to use the first volume.

To skip the transform to MNI space, and resampling to 2x2x2mm (if this has been
done already), use the --already-in-MNI option.

Adapted from the fMRISurface module of the Human Connectome
Project's minimal proprocessing pipeline. Please cite:

Glasser MF, Sotiropoulos SN, Wilson JA, Coalson TS, Fischl B, Andersson JL, Xu J,
Jbabdi S, Webster M, Polimeni JR, Van Essen DC, Jenkinson M, WU-Minn HCP Consortium.
The minimal preprocessing pipelines for the Human Connectome Project. Neuroimage. 2013 Oct 15;80:105-24.
PubMed PMID: 23668970; PubMed Central PMCID: PMC3720813.

Written by Erin W Dickie, Jan 12, 2017
"""
from __future__ import division

import os
import sys
import datetime
import tempfile
import shutil
import subprocess
import logging
import nibabel
import numpy as np
from docopt import docopt

import ciftify
from ciftify.utils import get_stdout, section_header, FWHM2Sigma

logger = logging.getLogger('ciftify')
logger.setLevel(logging.DEBUG)

DRYRUN = False

def run_ciftify_subject_fmri(settings, tmpdir):

    ## write a bunch of info about the environment to the logs
    log_build_environment()
    ## print the settings to the logs
    if not settings.diagnostics.path:
        settings.diagnostics.path = tmpdir
    settings.log_settings()

    # define some mesh paths as a dictionary
    meshes = define_meshes(subject.path, tmpdir,
        low_res_meshes = settings.low_res)

    ## either transform or copy the input_fMRI
    define_func_3D(settings, tmpdir)

    atlas_fMRI_4D = os.path.join(settings.results_dir,
                                '{}.nii.gz'.format(settings.fmri_label))
    if settings.already_atlas_transformed:
      run(['cp', settings.input_fMRI.path, atlas_fMRI_4D])
    else:
      logger.info(section_header('MNI Transform'))
      if not settings.run_flirt
          func2T1w_mat = calc_sform_differences(settings, tmpdir)
      else:
          func2T1w_mat = run_flirt_to_T1w(settings, tmpdir)
      transform_to_MNI(func2T1w_mat, atlas_fMRI_4D, settings)


    #Make fMRI Ribbon
    #Noisy Voxel Outlier Exclusion
    #Ribbon-based Volume to Surface mapping and resampling to standard surface
    logger.info(section_header('Making fMRI Ribbon'))
    ribbon_vol=os.path.join(settings.diagnotics.path,'ribbon_only.nii.gz')
    make_cortical_ribbon(ref_vol = os.path.join(settings.vol_reg['src_dir'],
                                                settings.vol_reg['T1wImage']),
                        ribbon_vol = ribbon_vol,
                        settings = settings,
                        mesh_settings = meshes['AtlasSpaceNative'])

    logger.info(section_header('Determining Noisy fMRI voxels'))
    goodvoxels_vol = os.path.join(settings.diagnotics.path, 'goodvoxels.nii.gz')
    tmean_vol, cov_vol = define_good_voxels(
        atlas_fMRI_4D, ribbon_vol, goodvoxels_vol, tmpdir)

    logger.info(section_header('Mapping fMRI to 32k Surface'))

    for Hemisphere in ["L", "R"]:

        ## now finally, actually project the fMRI input
        map_volume_to_surface(vol_input = atlas_fMRI_4D,
                              map_name = settings.fmri_label,
                              subject = settings.subject.id,
                              hemisphere = Hemisphere,
                              mesh_settings = meshes['AtlasSpaceNative'],
                              dilate_factor = settings.dilate_factor,
                              volume_roi = goodvoxels_vol)


        ## Erin's new addition - find what is below a certain percentile and dilate..
        if settings.dilate_percent_below:
            dilate_out_low_intensity_voxels(settings, hemisphere, mesh_settings)

    ## back to the HCP program - do the mask and resample
        for low_res_mesh in settings.vol_reg.low_res:
            mask_and_resample(map_name = settings.fmri_label,
                            subject = settings.subject.id,
                            hemisphere = Hemisphere,
                            src_mesh = meshes['AtlasSpaceNative'],
                            dest_mesh = meshes['{}k_fs_LR'.format(low_res_mesh)'],
                            surf_reg = settings.surf_reg)

    if settings.diagnotics.run_all:
        build_diagnositic_cifti_file(settings, mesh_settings)



    ############ The subcortical resampling step...
    logger.info(section_header("Subcortical Processing"))
    logger.info("VolumefMRI: {}".format(atlas_fMRI_4D))


    AtlasROIvols = os.path.join(settings.subject.atlas_space_dir, "ROIs",'Atlas_ROIs.{}.nii.gz'.format(settings.greyord_res))

    atlas_roi_vol = subcortical_atlas(atlas_fMRI_4D,
                            settings.subject.atlas_space_dir,
                            settings.results_dir,
                            settings.greyord_res,
                            tmpdir)

    tmp_dilate_cifti, tmp_roi_dlabel, =resample_subcortical_part1(
                                                atlas_fMRI_4D,
                                                atlas_roi_vol,
                                                AtlasROIvols,
                                                tmpdir)
    subcortical_data_s0 = resample_subcortical_part2(
                                tmp_dilate_cifti,
                                tmp_roi_dlabel,
                                0, setting.fmri_label, tmpdir)

    #Generation of Dense Timeseries
    logger.info(section_header("Generation of Dense Timeseries"))
    for low_res_mesh in settings.vol_reg.low_res:
        create_dense_timeseries(smoothing = 0,
                    settings = settings,
                    subcortical_data = subcortical_data_s0,
                    subcortical_labels = Atlas_ROIs_vol,
                    mesh_settings = meshes['{}k_fs_LR'.format(low_res_mesh)'])


    #########cifti smoothing ################
    if settings.smoothing:
        logger.info(section_header("Smoothing Output"))
        Sigma = FWHM2Sigma(settings.smoothing)
        logger.info("FWHM: {}".format(settings.smoothing))
        logger.info("Sigma: {}".format(Sigma))

    subcortical_data_sm = resample_subcortical_part2(
                                tmp_dilate_cifti,
                                tmp_roi_dlabel,
                                settings.smoothing,
                                setting.fmri_label, tmpdir)

    for Hemisphere in ['L', 'R']:
        run(['wb_command', '-metric-smoothing',
             surf_file(settings.subject.id, "midthickness", Hemisphere)"$DownSampleFolder"/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii "$NameOffMRI"."$Hemisphere".atlasroi."$LowResMesh"k_fs_LR.func.gii "$Sigma" "$NameOffMRI"_s"$SmoothingFWHM".atlasroi."$Hemisphere"."$LowResMesh"k_fs_LR.func.gii -roi "$DownSampleFolder"/"$Subject"."$Hemisphere".atlasroi."$LowResMesh"k_fs_LR.shape.gii'])

for Hemisphere in L R ; do
  ${CARET7DIR}/wb_command -metric-smoothing "$DownSampleFolder"/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii "$NameOffMRI"."$Hemisphere".atlasroi."$LowResMesh"k_fs_LR.func.gii "$Sigma" "$NameOffMRI"_s"$SmoothingFWHM".atlasroi."$Hemisphere"."$LowResMesh"k_fs_LR.func.gii -roi "$DownSampleFolder"/"$Subject"."$Hemisphere".atlasroi."$LowResMesh"k_fs_LR.shape.gii

    if SmoothingFWHM:
        logger.info(section_header("Smoothing Output"))
        Sigma = FWHM2Sigma(SmoothingFWHM)
        logger.info("FWHM: {}".format(SmoothingFWHM))
        logger.info("Sigma: {}".format(Sigma))

        run(['wb_command', '-cifti-smoothing',
            cifti_output_s0,
            str(Sigma), str(Sigma), 'COLUMN',
            os.path.join(ResultsFolder,
                '{}_Atlas_s{}.dtseries.nii'.format(NameOffMRI, SmoothingFWHM)),
            '-left-surface', os.path.join(DownSampleFolder,
              '{}.L.midthickness.{}k_fs_LR.surf.gii'.format(Subject, LowResMesh)),
            '-right-surface', os.path.join(DownSampleFolder,
              '{}.R.midthickness.{}k_fs_LR.surf.gii'.format(Subject, LowResMesh))])

#### Settings parser

class Settings(WorkFlowSettings):
    def __init__(self, arguments):
        WorkFlowSettings.__init__(self, arguments)
        self.subject = self.__get_subject(arguments)
        self.fmri_label = arguments["<task_label>"]
        self = self.__set_results_dir()
        self = self.__set_func_4D(self, arguments["<func.nii.gz>"])
        self.func_ref = self.__get_func_3D(self, argments['--func-ref'])
        self.smoothing = self.__set_smoothing(self, arguments["--SmoothingFWHM"])
        self.dilate_percent_below = arguments["--DilateBelowPct"]
        self.diagnostics = self.__set_surf_diagnostics(self,arguments['--OutputSurfDiagnostics'])
        self.already_atlas_transformed = arguments['--already-in-MNI']
        self.run_flirt = arguments["--FLIRT-to-T1w"]
        self.vol_reg = self.__define_volume_registration(self, arguments)
        self.low_res = '32' #forcing only the 32k mesh for now
        self.surf_reg = self.__define_surface_registration(self, arguments)

    def __get_subject(self, arguments):
        subject_id = arguments['<subject>']
        return Subject(self.work_dir, subject_id)

    def __set_results_dir(self):
        '''
        check that the result does not already exist and make it
        sets self.result_dir and self.log
        '''
        self.result_dir = os.path.join(self.subject.atlas_space_dir, "Results",
         self.fmri_label)
        self.log = os.path.join(self.result_dir, "ciftify_subject_fmri.log")
        if os.path.exists(self.log):
            logger.error('Subject output already exits.\n '
            'To force rerun, delete or rename the logfile:\n\t{}'.format(self.log))
            sys.exit(1)
        if not os.path.exists(self.result_dir):
            ciftify.utils.make_dir(self.result_dir)
        return self

    def __set_func_4D(self, func_4D):
        '''
        parse the input func file and test it's validity
        '''
        if not os.path.isfile(func_4D):
          logger.error("input_fMRI does not exist :(..Exiting")
          sys.exit(1)
            ## read the number of TR's and the TR from the header
        self.func_4D = func_4D
        self.num_TR = first_word(get_stdout(['fslval', func_4D, 'dim4']))
        self.middle_TR = int(self.num_TR)//2
        self.TR_in_ms = first_word(get_stdout(['fslval', func_4D, 'pixdim4']))
        return(self)

    def __define_atlas_registration(self, arguments, method='FSL_fnirt',
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
        resolution_config = WorkflowSettings.set_resolution_config(method, standard_res)
        registration_config.update(resolution_config)
        return registration_config

    def __define_surface_registration(self, arguments):
        """
        Checks that option is either MSMSulc or FS
        Note: should check that sphere for registration do exist
        """
        surf_mode =  WorkflowSettings.get_registration_mode(arguments)
        if surf_mode == "MSMSulc":
            RegName = "MSMSulc"
        elif surf_mode == "FS":
            RegName = "reg.reg_LR"
        else:
            logger.critical('--reg-name argument must be "FS" or "MSMSulc"')
            sys.exit(1)
        ## this is where I should add more checks
        L_sphere = os.path.join(self.subject.atlas_native_dir,
          '{}.L.sphere.{}.native.surf.gii'.format(self.subject.id, RegName))
        if not os.path.exists(L_sphere):
            logger.critical("Registration Sphere {} not found".format(L_sphere))
            sys.exit(1)
        return RegName

    def __set_func_4D(self, func_4D):
        '''
        parse the input func file and test it's validity
        '''
        if not os.path.isfile(func_4D):
          logger.error("input_fMRI does not exist :(..Exiting")
          sys.exit(1)
            ## read the number of TR's and the TR from the header
        self.func_4D = func_4D
        self.num_TR = first_word(get_stdout(['fslval', func_4D, 'dim4']))
        self.middle_TR = int(self.num_TR)//2
        self.TR_in_ms = first_word(get_stdout(['fslval', func_4D, 'pixdim4']))
        return(self)

    def __get_func_3D(self, func_ref):
        '''
        parse the arguments to determine the registration template from the T1w image
        returns the path to the 3D file
        '''
        return ReferenceVolume(func_ref)

    def __set_surf_diagnostics(self, OutputSurfDiagnostics):
        '''
        sets a surfs diagnostics folder to a path inside the resutls dir or None
        '''
        return DiagnosticSettings.__init__(self.results_dir, OutputSurfDiagnostics)

    def get_log_handler(self, formatter):
        fh = logging.FileHandler(self.log)
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        return fh

    def print_settings(self):
        logger.info('Arguments:')
        logger.info("\tInput_fMRI: {}".format(self.func_4D))
        logger.info("\tCIFTIFY_WORKDIR: {}".format(self.WorkDir))
        logger.info("\tSubject: {}".format(self.subject.id))
        logger.info("\tTask Label: {}".format(self.fmri_label))
        logger.info("\tSurface Registration Sphere: {}".format(self.surf_reg))
        if self.smoothing:
            logger.info("\tSmoothingFWHM: {}".format(self.smoothing))
        if self.dilate_percent_below:
            logger.info("\tWill fill holes defined as data with intensity below {} percentile".format(self.dilate_percent_below))
        logger.info("The following settings are set by default:")
        logger.info("\nGrayordinatesResolution: {}".format(self.greyord_res))
        logger.info('\nLowResMesh: {}k'.format(self.low_res))
        logger.info('Native space surfaces are in: {}'.format(self.atlas_native_dir))
        logger.info('The resampled surfaces (those matching the final result are in: {})'.format(self.altas_LR32k_dir))
        ## read the number of TR's and the TR from the header
        if self.surf_diagnostics
            logger.info("Diagnostic Files will be written to: {}".format(self.surf_diagnostics))
        logger.info('Number of TRs: {}'.format(self.num_TR)
        logger.info('Middle TR: {}'.format(self.middle_TR))
        logger.info('TR(ms): {}'.format(self.TR_in_ms))


class Subject(object):
    def __init__(self, work_dir, subject_id):
        self.id = subject_id
        self.path = self.__set_path(work_dir)
        self.T1w_dir = os.path.join(self.path, 'T1w')
        self.atlas_space_dir = os.path.join(self.path, 'MNINonLinear')
        self.altas_LR32k_dir = os.path.join(self.atlas_space_dir, "fsaverage_LR32k")
        self.altas_native_dir = os.path.join(self.atlas_space_dir, "native")

    def __set_path(self, work_dir):
        path = os.path.join(work_dir, self.id)
        if not os.path.exists(path):
            logger.error("The subject's working directory not found. "
             "Note that ciftify_recon_all needs to be run before ciftify_subject_fmri")
            sys.exit(1)
        return path

class ReferenceVolume(object):
    def __init__(self, func_ref_arg):
        self.mode = None
        self.path = os.path.join(tmpdir, 'bold_ref.nii.gz')
        if func_ref_arg == "first_vol":
            self.mode = "first_vol"
        if func_ref_arg == "median":
            self.mode = "median"
        if os.path.isfile(func_ref_arg):
            self.mode = "path"
            self.path = func_ref_arg
        logger.error('--func-ref argument must be "first_vol", "median" or a valid filepath'
          '"{}" given'.format(func_ref))
        sys.exit(1)

class DiagnosticSettings(object):
    '''
    a class holding two values to record if diagnostics should be calcualated and
    where to write to
    '''
    def __init__(self, results_dir, diagnotics_arg, tmpdir):
        self.requested = diagnotics_arg
        if self.requested:
            self.path = os.path.join(results_dir, 'RibbonVolumeToSurfaceMapping')
            ciftify.utils.make_dir(self.path)
        else:
            self.path = None
        return self

def run(cmd, suppress_stdout = False):
    ''' calls the run function with specific settings'''
    returncode = ciftify.utils.run(cmd, suppress_stdout = suppress_stdout)
    if returncode :
        sys.exit(1)
    return(returncode)

def log_build_environment():
    '''print the running environment info to the logs (info)'''
    logger.info("{}---### Environment Settings ###---".format(os.linesep))
    logger.info("Username: {}".format(get_stdout(['whoami'], echo = False).replace(os.linesep,'')))
    logger.info(ciftify.config.system_info())
    logger.info(ciftify.config.ciftify_version(os.path.basename(__file__)))
    logger.info(ciftify.config.wb_command_version())
    logger.info(ciftify.config.freesurfer_version())
    logger.info(ciftify.config.fsl_version())
    logger.info("---### End of Environment Settings ###---{}".format(os.linesep))

def first_word(text):
    '''return only the first word in a string'''
    FirstWord = text.split(' ', 1)[0]
    return(text)

def define_func_3D(settings, tmpdir):
    """
    create the func_3D file as per subject instrutions
    """
    logger.info(section_header("Getting fMRI reference volume")

    if settings.ref_vol.mode == "first_vol":
        '''take the fist image (default)'''
        run(['wb_command', '-volume-math "(x)"', setting.ref_vol.path,
                        '-var','x', settins.input_fMRI, '-select', '1'])

    elif settings.ref_vol.mode == "median":
        '''take the median over time, if indicated'''
        run(['wb_command', '-volume-reduce',
            settings.input_fMRI, 'MEDIAN', settings.ref_vol.path])

    elif settings.ref_vol.mode == "path":
        '''use the file indicated by the user..after checking the dimension'''
        cifify.meants.verify_nifti_dimensions_match(settings.ref_vol.path,
                                                    settings.input_fMRI)
    else:
        sys.exit('Failed to define the ref volume')

def calc_sform_differences(settings, tmpdir):
    """
    adjust for any differences between the func sform and the T1w image
    using nilearn resample to find and intermidiate
    """
    logger.info('---Adjusting for differences between underlying sform---')
    resampled_ref = os.path.join(tmpdir, 'vol_ref_rT1w.nii.gz')
    logger.info("Using nilearn to create resampled image {}".format(resampled_ref))
    resampled_ref_vol = nilearn.image.resample_to_img(
        source_img = settings.ref_vol.path
        target_img = os.path.join(
                        settings.vol_reg['src_dir'],
                        settings.vol_reg['T1wImage'])
    resampled_ref_vol.to_filename(resampled_ref)

    logger.info("Calculating linear transform between resampled reference and reference vols")
    func2T1w_mat = os.path.join(settings.results_dir, 'native','mat_EPI_to_T1.mat')
    run(['mkdir','-p',os.path.join(settings.results_dir,'native')])
    run(['flirt',
        '-in', settings.ref_vol.path,
        '-ref', resampled_ref,
        '-omat', func2T1w_mat,
        '-dof', "6",
        '-cost', "corratio", '-searchcost', "corratio"])
    return func2T1w_mat

def run_flirt_to_T1w(settings, cost_function = "corratio", degrees_of_freedom = "12"):
    """
    Use FSL's FLIRT to calc a transform to the T1w Image.. not ideal transform
    """
    logger.info('Running FLIRT transform to T1w with costfunction {} and dof {}'.format(FLIRT_cost, FLIRT_dof))
    func2T1w_mat = os.path.join(settings.results_dir, 'native','mat_EPI_to_T1.mat')
    ## calculate the fMRI to native T1w transform
    run(['mkdir','-p',os.path.join(settings.results_dir,'native')])
    run(['flirt',
        '-in', settings.ref_vol.path,
        '-ref', os.path.join(
            settings.vol_reg['src_dir'],
            settings.vol_reg['T1wBrain']),
        '-omat', func2T1w_mat,
        '-dof', str(degrees_of_freedom),
        '-cost', cost_function, '-searchcost', cost_function,
        '-searchrx', '-180', '180',
        '-searchry', '-180', '180',
        '-searchrz', '-180', '180'])
    return func2T1w_mat

def transform_to_MNI(func2T1w_mat, atlas_fMRI_4D, settings):
    '''
    transform the fMRI image to MNI space 2x2x2mm using FSL
    RegTemplate  An optional 3D MRI Image from the functional to use for registration
    '''
    ## make the directory to hold the transforms if it doesn't exit
    run(['mkdir','-p',os.path.join(settings.results_dir,'native')])

    ## concatenate the transforms
    func2MNI_mat = os.path.join(settings.results_dir,'native','mat_EPI_to_TAL.mat')
    run(['convert_xfm','-omat', func2MNI_mat, '-concat',
        os.path.join(
            settings.vol_reg['xfms_dir'],
            settings.vol_reg['AtlasTransform_Linear']),
        func2T1w_mat])

    ## now apply the warp!!
    logger.info("Transforming to MNI space and resampling to 2x2x2mm")
    run(['applywarp',
        '--ref={}'.format(os.path.join(
            settings.vol_reg['dest_dir'],
            settings.vol_reg['T1wBrain']),
        '--in={}'.format(settings.input_fMRI)
        '--warp={}'.format(os.path.join(
            settings.vol_reg['xfms_dir'],
            settings.vol_reg['AtlasTransform_NonLinear'])),
        '--premat={}'.format(func2MNI_mat),
        '--interp=spline',
        '--out={}'.format(altas_fMRI_4D)])

def make_cortical_ribbon(ref_vol, ribbon_vol, settings, mesh_settings):
    ''' make left and right cortical ribbons and combine '''
    logger.info(section_header('Making fMRI Ribbon'))
    with ciftify.utils.TempDir() as ribbon_tmp:
        for Hemisphere in ['L', 'R']:
            hemisphere_cortical_ribbon(Hemisphere, settings.subject.id,
                        ref_vol, mesh_settings,
                        os.path.join(ribbon_tmp,'{}.ribbon.nii.gz'.format(Hemisphere)),
                        ribbon_tmp)
        # combine the left and right ribbons into one mask
        run(['fslmaths', os.path.join(ribbon_tmp,'L.ribbon.nii.gz'),
            '-add', os.path.join(ribbon_tmp,'R.ribbon.nii.gz'),
             ribbon_vol])

def hemisphere_cortical_ribbon(hemisphere, subject, ref_vol, mesh_settings,
             ribbon_out, ribbon_tmp, GreyRibbonValue = 1):
    '''
    builds a cortical ribbon mask for that hemisphere
    '''
    ## create a volume of distances from the surface
    tmp_white_vol = os.path.join(ribbon_tmp,'{}.white.native.nii.gz'.format(hemisphere))
    tmp_pial_vol = os.path.join(ribbon_tmp,'{}.pial.native.nii.gz'.format(hemisphere))
    run(['wb_command', '-create-signed-distance-volume',
      surf_file(subject, 'white', hemisphere, mesh_settings),
      ref_vol, tmp_white_vol])
    run(['wb_command', '-create-signed-distance-volume',
      surf_file(subject, 'pial', hemisphere, mesh_settings),
      ref_vol, tmp_pial_vol])

    ## threshold and binarise these distance files
    tmp_white_vol_thr = os.path.join(ribbon_tmp,'{}.white_thr0.native.nii.gz'.format(Hemisphere))
    tmp_pial_vol_thr = os.path.join(ribbon_tmp,'{}.pial_uthr0.native.nii.gz'.format(Hemisphere))
    run(['fslmaths', tmp_white_vol, '-thr', '0', '-bin', '-mul', '255',
            tmp_white_vol_thr])
    run(['fslmaths', tmp_white_vol_thr, '-bin', tmp_white_vol_thr])
    run(['fslmaths', tmp_pial_vol, '-uthr', '0', '-abs', '-bin', '-mul', '255',
            tmp_pial_vol_thr])
    run(['fslmaths', tmp_pial_vol_thr, '-bin', tmp_pial_vol_thr])

    ## combine the pial and white to get the ribbon
    run(['fslmaths', tmp_pial_vol_thr,
      '-mas', tmp_white_vol_thr,
      '-mul', '255',
      ribbon_out])
    run(['fslmaths', ribbon_out, '-bin', '-mul', str(GreyRibbonValue), ribbon_out])

def define_good_voxels(input_fMRI_4D, ribbon_vol, goodvoxels_vol, tmpdir,
          NeighborhoodSmoothing = "5", CI_limit = "0.5"):
    '''
    does diagnostics on input_fMRI_4D volume, within the ribbon_out mask,
    produces a goodvoxels_vol volume mask
    '''

    ## calculate Coefficient of Variation (cov) of the fMRI
    tmean_vol = os.path.join(tmpdir, 'Mean.nii.gz')
    TstdVol = os.path.join(tmpdir, 'SD.nii.gz')
    cov_vol = os.path.join(tmpdir, 'cov.nii.gz')
    run(['fslmaths', input_fMRI_4D, '-Tmean', tmean_vol, '-odt', 'float'])
    run(['fslmaths', input_fMRI_4D, '-Tstd', TstdVol, '-odt', 'float'])
    run(['fslmaths', TstdVol, '-div', tmean_vol, cov_vol])

    ## calculate a cov ribbon - modulated by the NeighborhoodSmoothing factor
    cov_ribbon = os.path.join(tmpdir, 'cov_ribbon.nii.gz')
    cov_ribbon_norm = os.path.join(tmpdir, 'cov_ribbon_norm.nii.gz')
    SmoothNorm = os.path.join(tmpdir, 'SmoothNorm.nii.gz')
    cov_ribbon_norm_smooth = os.path.join(tmpdir, 'cov_ribbon_norm_smooth.nii.gz')
    cov_norm_modulate = os.path.join(tmpdir, 'cov_norm_modulate.nii.gz')
    cov_norm_modulate_ribbon = os.path.join(tmpdir, 'cov_norm_modulate_ribbon.nii.gz')
    run(['fslmaths', cov_vol,'-mas', ribbon_vol, cov_ribbon])
    cov_ribbonMean = first_word(get_stdout(['fslstats', cov_ribbon, '-M']))
    cov_ribbonMean = cov_ribbonMean.rstrip(os.linesep) ## remove return
    run(['fslmaths', cov_ribbon, '-div', cov_ribbonMean, cov_ribbon_norm])
    run(['fslmaths', cov_ribbon_norm, '-bin', '-s', NeighborhoodSmoothing,
        SmoothNorm])
    run(['fslmaths', cov_ribbon_norm, '-s', NeighborhoodSmoothing,
    '-div', SmoothNorm, '-dilD', cov_ribbon_norm_smooth])
    run(['fslmaths', cov_vol, '-div', cov_ribbonMean,
    '-div', cov_ribbon_norm_smooth, cov_norm_modulate])
    run(['fslmaths', cov_norm_modulate,
    '-mas', ribbon_vol, cov_norm_modulate_ribbon])

    ## get stats from the modulated cov ribbon file and log them
    ribbonMean = first_word(get_stdout(['fslstats', cov_norm_modulate_ribbon, '-M']))
    logger.info('Ribbon Mean: {}'.format(ribbonMean))
    ribbonSTD = first_word(get_stdout(['fslstats', cov_norm_modulate_ribbon, '-S']))
    logger.info('Ribbon STD: {}'.format(ribbonSTD))
    ribbonLower = float(ribbonMean) - (float(ribbonSTD)*float(CI_limit))
    logger.info('Ribbon Lower: {}'.format(ribbonLower))
    ribbonUpper = float(ribbonMean) + (float(ribbonSTD)*float(CI_limit))
    logger.info('Ribbon Upper: {}'.format(ribbonUpper))

    ## get a basic brain mask from the mean img
    bmaskVol = os.path.join(tmpdir, 'mask.nii.gz')
    run(['fslmaths', tmean_vol, '-bin', bmaskVol])

    ## make a goodvoxels_vol mask img
    run(['fslmaths', cov_norm_modulate,
    '-thr', str(ribbonUpper), '-bin', '-sub', bmaskVol, '-mul', '-1',
    goodvoxels_vol])

    return(tmean_vol, cov_vol)

def map_volume_to_surface(vol_input, map_name, subject, hemisphere,
        mesh_settings, dilate_factor = None, volume_roi = None):
    """
    Does wb_command -volume-to-surface mapping ribbon constrained
    than does optional dilate step
    """
    output_func = func_gii_file(subject, map_name,
        hemisphere, mesh_settings)
    cmd = ['wb_command', '-volume-to-surface-mapping', vol_input,
     surf_file(subject, 'midthickness', hemisphere, mesh_settings),
     output_func,'-ribbon-constrained',
     surf_file(subject, 'white', hemisphere, mesh_settings),
     surf_file(subject, 'pial', hemisphere, mesh_settings)]
    if volume_roi:
        cmd.extend(['-volume-roi', volume_roi])
    run(cmd)

    if dilate:
    ## dilate to get rid of wholes caused by the goodvoxels_vol mask
        run(['wb_command', '-metric-dilate', output_func,
          surf_file(settings.subject.id, 'midthickness', hemisphere, mesh_settings)
          dilate_factor, output_func, '-nearest'])

def dilate_out_low_intensity_voxels(settings, hemisphere, mesh_settings):
    '''
    looks for voxels of low intensity and marks dilates to try to correct for them
    Hopefully this is an unnessary step with volume to surface mapping is done well
    '''
    intput_func_gii = func_gii_file(settings.subject.id, settings.fmri_label,
                            hemisphere, mesh_settings)
    lowvoxels_gii =  func_gii_file(settings.subject.id, 'lowvoxels',
                            hemisphere, mesh_settings)
    low_intensity_thres = get_stdout(['wb_command', '-metric-stats',
      input_func_gii,
      '-percentile', str(settings.dilate_percent_below),
      '-column', str(settings.middle_TR),
      '-roi', medial_wall_roi_file(settings.subject.id, hemisphere, mesh_settings)])
    run(['wb_command', '-metric-math',
     '"(x < {})"'.format(low_intensity_thres),
     lowvoxels_gii, '-var', 'x', input_func_gii, '-column', str(settings.middle_TR)])
    run(['wb_command', '-metric-dilate', input_func_gii
      medial_wall_roi_file(settings.subject.id, hemisphere, mesh_settings),
      str(settings.dilate_factor), input_func_gii,
      '-bad-vertex-roi', lowvoxels_gii, '-nearest'])

def mask_and_resample(map_name, subject, hemisphere, src_mesh, dest_mesh, surf_reg):
    '''
    Does three steps that happen often after surface projection to native space.
    1. mask in natve space (to remove the middle/subcortical bit)
    2. resample to the low-res-mesh (32k mesh)
    3. mask again in the low (32k space)
    '''
    ## define the sphere name for this operation
    if surf_reg == "FS":
        reg_sphere_name = 'sphere.reg.reg_LR'
    elif surf_reg == "MSMSulc":
        reg_sphere_name = 'sphere.MSMSulc'
    else:
        logger.error('surf_reg argmument to can only be'
            ''"FS" or "MSMSulc" {} given'.format(surf_reg))

    input_gii = func_gii_file(subject, map_name, hemisphere, src_mesh)
    output_gii = func_gii_file(subject, map_name, hemisphere, dest_mesh)
    roi_src = medial_wall_roi_file(subject, hemisphere, src_mesh)
    roi_dest = medial_wall_roi_file(subject, hemisphere, dest_mesh)
    run(['wb_command', '-metric-mask', input_gii, roi_src, input_gii])
    run(['wb_command', '-metric-resample', input_gii,
      surf_file(subject, reg_sphere_name, hemisphere, src_mesh),
      surf_file(subject, 'sphere', hemisphere, dest_mesh),
      'ADAP_BARY_AREA', output_gii,
      '-area-surfs',
      surf_file(settings.subject.id, 'midthickness', hemisphere, src_mesh),
      surf_file(settings.subject.id, 'midthickness', hemisphere, dest_mesh),
      '-current-roi', roi_src])
    run(['wb_command', '-metric-mask', output_gii, roi_dest, output_gii])

def volume_to_surface_plus_resampling(vol_input, map_name, subject, hemiphere,
        settings, meshes, volume_roi = None, dilate_factor = None):
    '''
    combines calls to dilate_out_low_intensity_voxels() and mask_and_resample()
    '''
    map_volume_to_surface(vol_input = vol_intput,
                          map_name = map_name,
                          subject = settings.subject.id,
                          hemisphere = hemisphere,
                          mesh_settings = meshes['AtlasSpaceNative'],
                          dilate_factor = dilate_factor,
                          volume_roi = volume_roi)
    for low_res_mesh in settings.vol_reg.low_res:
        mask_and_resample(map_name = map_name,
                        subject = settings.subject.id,
                        hemisphere = hemisphere,
                        src_mesh = meshes['AtlasSpaceNative'],
                        dest_mesh = meshes['{}k_fs_LR'.format(low_res_mesh)'],
                        surf_reg = settings.surf_reg)


def build_diagnositic_cifti_file(settings, mesh_settings):
    '''
    projects a bunch of diagnostic volumes to the surface and resamples them
    to the low res meshes. Than it build dscalar.nii outputs
    '''
    logger.info(section_header('Writing Surface Mapping Diagnotic Files'))
    for Hemisphere in ['L','R']:
        for mapname in ["mean", "cov"]:

            if mapname == "mean": map_vol = tmean_vol
            if mapname == "cov": map_vol = cov_vol

            ## project the maps of mean and cov signal with bad voxels removed
            volume_to_surface_plus_resampling(
                    vol_input = map_vol,
                    map_name = map_name,
                    hemiphere = Hemisphere,
                    settings = settings, meshes = meshes,
                    volume_roi = goodvoxels_vol,
                    dilate_factor = settings.dilate_factor)

            ## project the maps of mean and cov signal with bad voxels left in
            volume_to_surface_plus_resampling(
                    vol_input = map_vol,
                    map_name = "{}_all".format(map_name),
                    hemiphere = Hemisphere,
                    settings = settings, meshes = meshes,
                    volume_roi = None,
                    dilate_factor = None)

        ## project the maps of mean and cov signal with bad voxels left in
        volume_to_surface_plus_resampling(
                vol_input = goodvoxels_vol,
                map_name = "goodvoxels",
                hemiphere = Hemisphere,
                settings = settings, meshes = meshes,
                volume_roi = None,
                dilate_factor = None)

        ## Also ouput the resampled low voxels
        if settings.dilate_percent_below:
            for low_res_mesh in settings.low_res:
                  mask_and_resample(map_name = "lowvoxels",
                                  subject = settings.subject.id,
                                  hemisphere = Hemisphere,
                                  src_mesh = meshes['AtlasSpaceNative'],
                                  dest_mesh = meshes['{}k_fs_LR'.format(low_res_mesh)'],
                                  surf_reg = settings.surf_reg)


      map_names = ['goodvoxels', 'mean', 'mean_all', 'cov', 'cov_all']
      if settings.dilate_percent_below: map_names.append('lowvoxels')
    #   import pbd; pdb.set_trace()
      for map_name in map_names:
          for low_res_mesh in settings.low_res:
              mesh_settings = meshes['{}k_fs_LR'.format(low_res_mesh)']
              run(['wb_command', '-cifti-create-dense-scalar',
                os.path.join(settings.diagnotics.path,
                    '{}.atlasroi.{}.dscalar.nii'.format(map_name, mesh_settings['meshname'])),
                '-left-metric', func_gii_file(settings.subject_id, map_name, 'L', mesh_settings),
                '-roi-left', medial_wall_roi_file(settings.subject.id, 'L', mesh_settings),
                '-right-metric', func_gii_file(settings.subject_id, map_name, 'R', mesh_settings),
                '-roi-right', medial_wall_roi_file(settings.subject.id, 'R', mesh_settings))])


def subcortical_atlas(input_fMRI, AtlasSpaceFolder, ResultsFolder,
                      GrayordinatesResolution, tmpdir):

    ROIFolder = os.path.join(AtlasSpaceFolder, "ROIs")
    ROIvols = os.path.join(ROIFolder, 'ROIs.{}.nii.gz'.format(GrayordinatesResolution))
    #generate subject-roi space fMRI cifti for subcortical
    func_vx_size = ciftify.io.voxel_spacing(input_fMRI)
    expected_resolution = (float(GrayordinatesResolution),
                           float(GrayordinatesResolution),
                           float(GrayordinatesResolution))
    if func_vx_size == expected_resolution :
        logger.info("Creating subject-roi subcortical cifti at same resolution as output")
        vol_rois = ROIvols
    else :
        logger.info("Creating subject-roi subcortical cifti at differing fMRI resolution")
        tmp_ROIs = os.path.join(tmpdir, 'ROIs.nii.gz')
        run(['wb_command', '-volume-affine-resample', ROIvols,
            os.path.join(ciftify.config.find_fsl(),'etc', 'flirtsch/ident.mat'),
            input_fMRI, 'ENCLOSING_VOXEL', tmp_ROIs])
        vol_rois = tmp_ROIs
    return(vol_rois)

def resample_subcortical_part1(input_fMRI, atlas_roi_vol, Atlas_ROIs_vol,
                         output_subcortical,tmpdir):
    '''
    does the first step of the resampling, returns the two filepaths needed for next steps
    '''
    tmp_fmri_cifti = os.path.join(tmpdir,'temp_subject.dtseries.nii')
    run(['wb_command', '-cifti-create-dense-timeseries',
        tmp_fmri_cifti, '-volume', input_fMRI, atlas_roi_vol])

    logger.info("Dilating out zeros")
    #dilate out any exact zeros in the input data, for instance if the brain mask is wrong
    tmp_dilate_cifti = os.path.join(tmpdir, 'temp_subject_dilate.dtseries.nii')
    run(['wb_command', '-cifti-dilate', tmp_fmri_cifti,
        'COLUMN', '0', '10', tmp_dilate_cifti])

    logger.info('Generate atlas subcortical template cifti')
    tmp_roi_dlabel = os.path.join(tmpdir, 'temp_template.dlabel.nii')
    run(['wb_command', '-cifti-create-label', tmp_roi_dlabel,
        '-volume', Atlas_ROIs_vol, Atlas_ROIs_vol])
    return tmp_dilate_cifti, tmp_roi_dlabel

def resample_subcortical_part2(tmp_dilate_cifti, tmp_roi_dlabel,
        smoothing, fmri_label, tmpdir):
    '''
    step two does smoothing (if sigma > 0) and the do some extra resampling
    '''
    Atlas_Subcortical = os.path.join(tmpdir,
        '{}_AtlasSubcortical_s{}.nii.gz'.format(fmri_label, smoothing))
    Sigma = FWHM2Sigma(smoothing)
    if Sigma > 0 :
        logger.info("Smoothing subcortical with FWHM {}, Sigma {}".format(smoothing, sigma))
        #this is the whole timeseries, so don't overwrite, in order to allow on-disk writing, then delete temporary
        tmp_smoothed = os.path.join(tmpdir, 'temp_subject_smooth.dtseries.nii')
        run(['wb_command', '-cifti-smoothing', tmp_dilate_cifti,
            '0',  str(Sigma), 'COLUMN', tmp_smoothed, -fix-zeros-volume])
        #resample, delete temporary
        resample_input_cifti = tmp_smoothed
    else :
        resample_input_cifti = tmp_dilate_cifti

    logger.info("Resampling")
    tmp_atlas_cifti = os.path.join(tmpdir, 'temp_atlas.dtseries.nii')
    run(['wb_command', '-cifti-resample',
        resample_input_cifti, 'COLUMN', tmp_roi_dlabel,
        'COLUMN', 'ADAP_BARY_AREA', 'CUBIC', tmp_atlas_cifti,
        '-volume-predilate', '10'])

    #write output volume, delete temporary
    ##NOTE: $VolumefMRI contains a path in it, it is not a file in the current directory
    run(['wb_command', '-cifti-separate', tmp_atlas_cifti,
        'COLUMN', '-volume-all', output_subcortical])
    return output_subcortical

def create_dense_timeseries(map_name, smoothing, settings,
            subcortical_data, subcortical_labels, mesh_settings):
    '''
    put the surface mapped data and subcortical data together into the final dtseries file
    '''
    if mesh_settings['mesh_name'] == "32k_fs_LR":
        cifti_output = os.path.join(settings.results_dir,
            '{}_Atlas_s{}.dtseries.nii'.format(settings.fmri_label
                    smoothing))
    else:
        cifti_output = os.path.join(settings.results_dir,
            '{}_Atlas_s{}.{}.dtseries.nii'.format(settings.fmri_label,
                smoothing, mesh_settings['mesh_name'])

    if smoothing > 0:
        map_name = "{}_s{}".format(settings.fmri_label, smoothing)
    else:
        map_name = settings.fmri_label

    run(['wb_command', '-cifti-create-dense-timeseries', cifti_output,
        '-volume', subcortical_data, subcortical_labels,
        '-left-metric', func_gii_file(settings.subject.id, map_name,'L', mesh_settings),
        '-roi-left', medial_wall_roi_file(settings.subject.id, 'L', mesh_settings),
        '-right-metric',func_gii_file(settings.subject.id, map_name,'R', mesh_settings),
        '-roi-right', medial_wall_roi_file(settings.subject.id, 'R', mesh_settings)),
        '-timestep', settings.TR_in_ms])

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

    # Get settings, and add an extra handler for the current log
    settings = Settings(arguments)
    fh = settings.get_log_handler(formatter)
    logger.addHandler(fh)

    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
                section_header("Starting ciftify_subject_fmri")))
    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = run_ciftify_subject_fmri(settings, tmpdir)
    logger.info(section_header("Done"))
    sys.exit(ret)

if __name__=='__main__':
    main()
