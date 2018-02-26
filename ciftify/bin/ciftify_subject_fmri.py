#!/usr/bin/env python
"""
Projects a fMRI timeseries to and HCP dtseries file and does smoothing

Usage:
  ciftify_subject_fmri [options] <func.nii.gz> <Subject> <NameOffMRI>

Arguments:
    <func.nii.gz>           Nifty 4D volume to project to cifti space
    <Subject>               The Subject ID in the HCP data folder
    <NameOffMRI>            The outputname for the cifti result folder

Options:
  --SmoothingFWHM MM          The Full-Width-at-Half-Max for smoothing steps
  --ciftify-work-dir PATH     The directory for HCP subjects (overrides
                              CIFTIFY_WORKDIR/ HCP_DATA enivironment variables)
  --hcp-data-dir PATH         The directory for HCP subjects (overrides
                              CIFTIFY_WORKDIR/ HCP_DATA enivironment variables) DEPRECATED
  --already-in-MNI            Functional volume has already been registered to MNI
                              space using the same transform in as the hcp anatoical data
  --FLIRT-template NII        Optional 3D image (generated from the func.nii.gz)
                              to use calculating the FLIRT registration
  --FLIRT-dof DOF             Degrees of freedom [default: 12] for FLIRT
                              registration (Not used with --already-in-MNI)
  --FLIRT-cost COST           Cost function [default: corratio] for FLIRT
                              registration (Not used with '--already-in-MNI')
  --OutputSurfDiagnostics     Output some extra files for QCing the surface
                              mapping.
  --DilateBelowPct PCT        Add a step to dilate places where signal intensity
                              is below this percentage.
  --Dilate-MM MM              Distance in mm [default: 10] to dilate when
                              filling holes
  -v,--verbose                Verbose logging
  --debug                     Debug logging in Erin's very verbose style
  -n,--dry-run                Dry run
  -h,--help                   Print help

DETAILS

FSL's flirt is used to register the native fMRI ('--FLIRT-template')
to the native T1w image. This is concatenated to the non-linear transform to
MNIspace in the xfms folder. Options for FSL's flirt can be changed using the
"--FLIRT-dof" and "--FLIRT-cost". If a "--FLIRT-template" image is not given,
it will be calcuated using as the temporal mean of the func.nii.gz input image.

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

def run_ciftify_subject_fmri(arguments, tmpdir):
    input_fMRI = arguments["<func.nii.gz>"]
    if arguments['--ciftify-work-dir']:
        HCPData = arguments['--ciftify-work-dir']
    else:
        HCPData = arguments["--hcp-data-dir"]
    Subject = arguments["<Subject>"]
    NameOffMRI = arguments["<NameOffMRI>"]
    SmoothingFWHM = arguments["--SmoothingFWHM"]
    DilateBelowPct = arguments["--DilateBelowPct"]
    OutputSurfDiagnostics = arguments['--OutputSurfDiagnostics']
    noMNItransform = arguments['--already-in-MNI']
    RegTemplate = arguments['--FLIRT-template']
    FLIRT_dof = arguments['--FLIRT-dof']
    FLIRT_cost = arguments['--FLIRT-cost']


    if HCPData == None: HCPData = ciftify.config.find_hcp_data()

    ## write a bunch of info about the environment to the logs
    log_build_environment()

    logger.info('Arguments:')
    logger.info("\tinput_fMRI: {}".format(input_fMRI))
    if not os.path.isfile(input_fMRI):
      logger.error("input_fMRI does not exist :(..Exiting")
      sys.exit(1)
    logger.info("\tHCP_DATA: {}".format(HCPData))
    logger.info("\thcpSubject: {}".format(Subject))
    logger.info("\tNameOffMRI: {}".format(NameOffMRI))
    if SmoothingFWHM:
        logger.info("\tSmoothingFWHM: {}".format(SmoothingFWHM))
    if DilateBelowPct:
        logger.info("\tWill fill holes defined as data with intensity below {} percentile".format(DilateBelowPct))

    # Setup PATHS
    GrayordinatesResolution = "2"
    LowResMesh = "32"
    RegName = "FS"
    DilateFactor = "10"

    #Templates and settings
    AtlasSpaceFolder = os.path.join(HCPData, Subject, "MNINonLinear")
    DownSampleFolder = os.path.join(AtlasSpaceFolder, "fsaverage_LR32k")
    ResultsFolder = os.path.join(AtlasSpaceFolder, "Results", NameOffMRI)
    AtlasSpaceNativeFolder = os.path.join(AtlasSpaceFolder, "Native")

    logger.info("The following settings are set by default:")
    logger.info("\nGrayordinatesResolution: {}".format(GrayordinatesResolution))
    logger.info('\nLowResMesh: {}k'.format(LowResMesh))
    logger.info('Native space surfaces are in: {}'.format(AtlasSpaceNativeFolder))
    logger.info('The resampled surfaces (those matching the final result are in: {})'.format(DownSampleFolder))

    # PipelineScripts=${HCPPIPEDIR_fMRISurf}
    input_fMRI_4D=os.path.join(ResultsFolder,'{}.nii.gz'.format(NameOffMRI))
    input_fMRI_3D=os.path.join(tmpdir,'{}_Mean.nii.gz'.format(NameOffMRI))

    # output files
    if OutputSurfDiagnostics:
        DiagnosticsFolder = os.path.join(ResultsFolder, 'RibbonVolumeToSurfaceMapping')
        logger.info("Diagnostic Files will be written to: {}".format(DiagnosticsFolder))
        run(['mkdir','-p',DiagnosticsFolder])
    else:
        DiagnosticsFolder = tmpdir



    ###### from end of volume mapping pipeline

    ## copy inputs into the ResultsFolder
    run(['mkdir','-p',ResultsFolder])

    ## read the number of TR's and the TR from the header
    TR_num = first_word(get_stdout(['fslval', input_fMRI, 'dim4']))
    logger.info('Number of TRs: {}'.format(TR_num))
    MiddleTR = int(TR_num)//2
    logger.info('Middle TR: {}'.format(MiddleTR))
    TR_vol = first_word(get_stdout(['fslval', input_fMRI, 'pixdim4']))
    logger.info('TR(ms): {}'.format(TR_vol))

    ## either transform or copy the input_fMRI
    if noMNItransform:
      run(['cp', input_fMRI, input_fMRI_4D])
    else:
      logger.info(section_header('MNI Transform'))
      logger.info('Running transform to MNIspace with costfunction {} and dof {}'.format(FLIRT_cost, FLIRT_dof))
      transform_to_MNI(input_fMRI, input_fMRI_4D, FLIRT_cost, FLIRT_dof,
                        HCPData, Subject, RegTemplate, tmpdir)


    #Make fMRI Ribbon
    #Noisy Voxel Outlier Exclusion
    #Ribbon-based Volume to Surface mapping and resampling to standard surface
    logger.info(section_header('Making fMRI Ribbon'))

    run(['fslmaths', input_fMRI_4D, '-Tmean', input_fMRI_3D])

    RegName="reg.reg_LR"

    ribbon_vol=os.path.join(DiagnosticsFolder,'ribbon_only.nii.gz')
    make_cortical_ribbon(Subject, AtlasSpaceNativeFolder, input_fMRI_3D, ribbon_vol)

    goodvoxels_vol = os.path.join(DiagnosticsFolder, 'goodvoxels.nii.gz')
    tmean_vol, cov_vol = define_good_voxels(
        input_fMRI_4D, ribbon_vol, goodvoxels_vol, tmpdir)

    logger.info(section_header('Mapping fMRI to 32k Surface'))

    for Hemisphere in ["L", "R"]:

        ## the input surfaces for this section in the AtlasSpaceNativeFolder
        mid_surf_native = os.path.join(AtlasSpaceNativeFolder,
          '{}.{}.midthickness.native.surf.gii'.format(Subject, Hemisphere))
        pial_surf = os.path.join(AtlasSpaceNativeFolder,
          '{}.{}.pial.native.surf.gii'.format(Subject, Hemisphere))
        white_surf = os.path.join(AtlasSpaceNativeFolder,
          '{}.{}.white.native.surf.gii'.format(Subject, Hemisphere))
        roi_native_gii = os.path.join(AtlasSpaceNativeFolder,
          '{}.{}.roi.native.shape.gii'.format(Subject, Hemisphere))
        sphere_reg_native = os.path.join(AtlasSpaceNativeFolder,
          '{}.{}.sphere.{}.native.surf.gii'.format(Subject, Hemisphere, RegName))

        ## the inputs for this section from the DownSampleFolder
        mid_surf_32k = os.path.join(DownSampleFolder,
          '{}.{}.midthickness.{}k_fs_LR.surf.gii'.format(Subject, Hemisphere, LowResMesh))
        roi_32k_gii = os.path.join(DownSampleFolder,
          '{}.{}.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, Hemisphere, LowResMesh))
        sphere_reg_32k = os.path.join(DownSampleFolder,
          '{}.{}.sphere.{}k_fs_LR.surf.gii'.format(Subject, Hemisphere, LowResMesh))


        ## now finally, actually project the fMRI input
        input_func_native = os.path.join(tmpdir, '{}.{}.native.func.gii'.format(NameOffMRI, Hemisphere))
        run(['wb_command', '-volume-to-surface-mapping',
         input_fMRI_4D, mid_surf_native, input_func_native,
         '-ribbon-constrained', white_surf, pial_surf,
         '-volume-roi', goodvoxels_vol])

        ## dilate to get rid of wholes caused by the goodvoxels_vol mask
        run(['wb_command', '-metric-dilate',
          input_func_native, mid_surf_native, DilateFactor,
          input_func_native, '-nearest'])

        ## Erin's new addition - find what is below a certain percentile and dilate..
        ## Erin's new addition - find what is below a certain percentile and dilate..
        if DilateBelowPct:
            DilThres = get_stdout(['wb_command', '-metric-stats', input_func_native,
              '-percentile', str(DilateBelowPct),
              '-column', str(MiddleTR),
              '-roi', roi_native_gii])
            lowvoxels_gii = os.path.join(tmpdir,'{}.lowvoxels.native.func.gii'.format(Hemisphere))
            run(['wb_command', '-metric-math',
             '"(x < {})"'.format(DilThres),
             lowvoxels_gii, '-var', 'x', input_func_native, '-column', str(MiddleTR)])
            run(['wb_command', '-metric-dilate', input_func_native,
              mid_surf_native, str(DilateFactor), input_func_native,
              '-bad-vertex-roi', lowvoxels_gii, '-nearest'])
    ## back to the HCP program - do the mask and resample

        ## mask resample than mask combo
        input_func_32k = os.path.join(tmpdir,
          '{}.{}.atlasroi.{}k_fs_LR.func.gii'.format(NameOffMRI, Hemisphere,LowResMesh))
        mask_and_resample(input_func_native, input_func_32k,
                  roi_native_gii, roi_32k_gii,
                  mid_surf_native, mid_surf_32k,
                  sphere_reg_native, sphere_reg_32k)

        if OutputSurfDiagnostics:
            logger.info(section_header('Writing Surface Mapping Diagnotic Files'))

            for mapname in ["mean", "cov"]:

                if mapname == "mean": map_vol = tmean_vol
                if mapname == "cov": map_vol = cov_vol

                ## the output directories for this section
                map_native_gii = os.path.join(tmpdir, '{}.{}.native.func.gii'.format(mapname, Hemisphere))
                map_32k_gii = os.path.join(tmpdir,"{}.{}.{}k_fs_LR.func.gii".format(Hemisphere, mapname, LowResMesh))
                run(['wb_command', '-volume-to-surface-mapping',
                  map_vol, mid_surf_native, map_native_gii,
                  '-ribbon-constrained', white_surf, pial_surf,
                  '-volume-roi', goodvoxels_vol])
                run(['wb_command', '-metric-dilate',
                  map_native_gii, mid_surf_native, DilateFactor, map_native_gii,
                  '-nearest'])
                mask_and_resample(map_native_gii, map_32k_gii,
                    roi_native_gii, roi_32k_gii,
                    mid_surf_native, mid_surf_32k,
                    sphere_reg_native, sphere_reg_32k)

                mapall_native_gii = os.path.join(tmpdir, '{}_all.{}.native.func.gii'.format(mapname, Hemisphere))
                mapall_32k_gii = os.path.join(tmpdir,"{}.{}_all.{}k_fs_LR.func.gii".format(Hemisphere, mapname, LowResMesh))
                run(['wb_command', '-volume-to-surface-mapping',
                  map_vol, mid_surf_native, mapall_native_gii,
                 '-ribbon-constrained', white_surf, pial_surf])
                mask_and_resample(mapall_native_gii, mapall_32k_gii,
                    roi_native_gii, roi_32k_gii,
                    mid_surf_native, mid_surf_32k,
                    sphere_reg_native, sphere_reg_32k)

            ## now project the goodvoxels to the surface
            goodvoxels_native_gii = os.path.join(tmpdir,'{}.goodvoxels.native.func.gii'.format(Hemisphere))
            goodvoxels_32k_gii = os.path.join(tmpdir,'{}.goodvoxels.{}k_fs_LR.func.gii'.format(Hemisphere, LowResMesh))
            run(['wb_command', '-volume-to-surface-mapping', goodvoxels_vol,
             mid_surf_native,
             goodvoxels_native_gii,
             '-ribbon-constrained', white_surf, pial_surf])
            mask_and_resample(goodvoxels_native_gii, goodvoxels_32k_gii,
             roi_native_gii, roi_32k_gii,
             mid_surf_native, mid_surf_32k,
             sphere_reg_native, sphere_reg_32k)

            ## Also ouput the resampled low voxels
            if DilateBelowPct:
              lowvoxels_32k_gii = os.path.join(tmpdir,'{}.lowvoxels.{}k_fs_LR.func.gii'.format(Hemisphere, LowResMesh))
              mask_and_resample(lowvoxels_gii, lowvoxels_32k_gii,
                 roi_native_gii, roi_32k_gii,
                 mid_surf_native, mid_surf_32k,
                 sphere_reg_native, sphere_reg_32k)

    if OutputSurfDiagnostics:
      Maps = ['goodvoxels', 'mean', 'mean_all', 'cov', 'cov_all']
      if DilateBelowPct: Maps.append('lowvoxels')
    #   import pbd; pdb.set_trace()
      for Map in Maps:
          run(['wb_command', '-cifti-create-dense-scalar',
            os.path.join(DiagnosticsFolder, '{}.atlasroi.{}k_fs_LR.dscalar.nii'.format(Map, LowResMesh)),
            '-left-metric', os.path.join(tmpdir,'L.{}.{}k_fs_LR.func.gii'.format(Map, LowResMesh)),
            '-roi-left', os.path.join(DownSampleFolder,
              '{}.L.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, LowResMesh)),
            '-right-metric', os.path.join(tmpdir,'R.{}.{}k_fs_LR.func.gii'.format(Map, LowResMesh)),
            '-roi-right', os.path.join(DownSampleFolder, '{}.R.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, LowResMesh))])



    ############ The subcortical resampling step...
    logger.info(section_header("Subcortical Processing"))
    logger.info("VolumefMRI: {}".format(input_fMRI_4D))

    Atlas_Subcortical = os.path.join(tmpdir, '{}_AtlasSubcortical_s0.nii.gz'.format(NameOffMRI))
    AtlasROIvols = os.path.join(AtlasSpaceFolder, "ROIs",'Atlas_ROIs.{}.nii.gz'.format(GrayordinatesResolution))

    atlas_roi_vol = subcortical_atlas(input_fMRI_4D, AtlasSpaceFolder, ResultsFolder,
                                    GrayordinatesResolution, tmpdir)
    resample_subcortical(input_fMRI_4D, atlas_roi_vol, AtlasROIvols,
                            Atlas_Subcortical,tmpdir)

    #Generation of Dense Timeseries
    logger.info(section_header("Generation of Dense Timeseries"))
    cifti_output_s0 = os.path.join(ResultsFolder,
        '{}_Atlas_s0.dtseries.nii'.format(NameOffMRI))
    run(['wb_command', '-cifti-create-dense-timeseries', cifti_output_s0,
        '-volume', Atlas_Subcortical, AtlasROIvols,
        '-left-metric', os.path.join(tmpdir,
          '{}.L.atlasroi.{}k_fs_LR.func.gii'.format(NameOffMRI, LowResMesh)),
        '-roi-left', os.path.join(DownSampleFolder,
          '{}.L.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, LowResMesh)),
        '-right-metric', os.path.join(tmpdir,
          '{}.R.atlasroi.{}k_fs_LR.func.gii'.format(NameOffMRI,LowResMesh)),
        '-roi-right', os.path.join(DownSampleFolder,
          '{}.R.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, LowResMesh)),
        '-timestep', TR_vol])

    #########cifti smoothing ################
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

def transform_to_MNI(input_fMRI, MNIspacefMRI, cost_function,
                        degrees_of_freedom, HCPData, Subject, RegTemplate, tmpdir):
    '''
    transform the fMRI image to MNI space 2x2x2mm using FSL
    RegTemplate  An optional 3D MRI Image from the functional to use for registration
    '''
    ### these inputs should already be in the subject HCP folder
    T1wImage = os.path.join(HCPData,Subject,'T1w','T1w_brain.nii.gz')
    T1w2MNI_mat = os.path.join(HCPData,Subject,'MNINonLinear','xfms','T1w2StandardLinear.mat')
    T1w2MNI_warp = os.path.join(HCPData,Subject,'MNINonLinear','xfms','T1w2Standard_warp_noaffine.nii.gz')
    MNITemplate2mm = os.path.join(os.environ['FSLDIR'],'data','standard', 'MNI152_T1_2mm_brain.nii.gz')
    ResultsFolder = os.path.dirname(MNIspacefMRI)
    ## make the directory to hold the transforms if it doesn't exit
    run(['mkdir','-p',os.path.join(ResultsFolder,'native')])
    ### calculate the linear transform to the T1w

    logger.info('Calculating EPI to T1w transform')
    func2T1w_mat =  os.path.join(ResultsFolder,'native','mat_EPI_to_T1.mat')
    ## make a target registration file if it doesn't exist
    if RegTemplate:
        func3D = RegTemplate
    else :
        func3D = os.path.join(tmpdir,"func3D.nii.gz")
        run(['fslmaths', input_fMRI, '-Tmean', func3D])
    ## calculate the fMRI to native T1w transform
    run(['flirt',
        '-in', func3D,
        '-ref', T1wImage,
        '-omat', func2T1w_mat,
        '-dof', str(degrees_of_freedom),
        '-cost', cost_function, '-searchcost', cost_function,
        '-searchrx', '-180', '180',
        '-searchry', '-180', '180',
        '-searchrz', '-180', '180'])

    ## concatenate the transforms
    func2MNI_mat = os.path.join(ResultsFolder,'native','mat_EPI_to_TAL.mat')
    run(['convert_xfm','-omat', func2MNI_mat, '-concat', T1w2MNI_mat, func2T1w_mat])

    ## now apply the warp!!
    logger.info("Transforming to MNI space and resampling to 2x2x2mm")
    run(['applywarp',
        '--ref={}'.format(MNITemplate2mm),
        '--in={}'.format(input_fMRI),
        '--warp={}'.format(T1w2MNI_warp),
        '--premat={}'.format(func2MNI_mat),
        '--interp=spline',
        '--out={}'.format(MNIspacefMRI)])

def make_cortical_ribbon(Subject, AtlasSpaceNativeFolder, ref_vol, ribbon_vol):
    ''' make left and right cortical ribbons and combine '''

    with ciftify.utils.TempDir() as ribbon_tmp:
        for Hemisphere in ['L', 'R']:
            hemisphere_cortical_ribbon(Subject, Hemisphere, AtlasSpaceNativeFolder, ref_vol,
                        os.path.join(ribbon_tmp,'{}.{}.ribbon.nii.gz'.format(Subject, Hemisphere)),
                        ribbon_tmp)
        # combine the left and right ribbons into one mask
        run(['fslmaths', os.path.join(ribbon_tmp,'{}.L.ribbon.nii.gz'.format(Subject)),
            '-add', os.path.join(ribbon_tmp,'{}.R.ribbon.nii.gz'.format(Subject)),
             ribbon_vol])

def hemisphere_cortical_ribbon(Subject, Hemisphere, AtlasSpaceNativeFolder, ref_vol, ribbon_out,
                    ribbon_tmp, GreyRibbonValue = 1):
    '''builds a cortical ribbon mask for that hemisphere, returns the path to that ribbon '''

    ## the inputs are..
    white_surf = os.path.join(AtlasSpaceNativeFolder, '{}.{}.white.native.surf.gii'.format(Subject,Hemisphere))
    pial_surf = os.path.join(AtlasSpaceNativeFolder, '{}.{}.pial.native.surf.gii'.format(Subject,Hemisphere))

    ## create a volume of distances from the surface
    tmp_white_vol = os.path.join(ribbon_tmp,'{}.{}.white.native.nii.gz'.format(Subject, Hemisphere))
    tmp_pial_vol = os.path.join(ribbon_tmp,'{}.{}.pial.native.nii.gz'.format(Subject, Hemisphere))
    run(['wb_command', '-create-signed-distance-volume',
      white_surf, ref_vol, tmp_white_vol])
    run(['wb_command', '-create-signed-distance-volume',
      pial_surf, ref_vol, tmp_pial_vol])

    ## threshold and binarise these distance files
    tmp_whtie_vol_thr = os.path.join(ribbon_tmp,'{}.{}.white_thr0.native.nii.gz'.format(Subject, Hemisphere))
    tmp_pial_vol_thr = os.path.join(ribbon_tmp,'{}.{}.pial_uthr0.native.nii.gz'.format(Subject, Hemisphere))
    run(['fslmaths', tmp_white_vol, '-thr', '0', '-bin', '-mul', '255',
            tmp_whtie_vol_thr])
    run(['fslmaths', tmp_whtie_vol_thr, '-bin', tmp_whtie_vol_thr])
    run(['fslmaths', tmp_pial_vol, '-uthr', '0', '-abs', '-bin', '-mul', '255',
            tmp_pial_vol_thr])
    run(['fslmaths', tmp_pial_vol_thr, '-bin', tmp_pial_vol_thr])

    ## combine the pial and white to get the ribbon
    run(['fslmaths', tmp_pial_vol_thr,
      '-mas', tmp_whtie_vol_thr,
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

def mask_and_resample(input_native, output_lowres,
        roi_native, roi_lowres,
        mid_surf_native, mid_surf_lowres,
        sphere_reg_native, sphere_reg_lowres):
    '''
    Does three steps that happen often after surface projection to native space.
    1. mask in natve space (to remove the middle/subcortical bit)
    2. resample to the low-res-mesh (32k mesh)
    3. mask again in the low (32k space)
    '''
    run(['wb_command', '-metric-mask', input_native, roi_native, input_native])
    run(['wb_command', '-metric-resample',
      input_native, sphere_reg_native, sphere_reg_lowres, 'ADAP_BARY_AREA',
      output_lowres,
      '-area-surfs', mid_surf_native, mid_surf_lowres,
      '-current-roi', roi_native])
    run(['wb_command', '-metric-mask', output_lowres, roi_lowres, output_lowres])

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

def resample_subcortical(input_fMRI, atlas_roi_vol, Atlas_ROIs_vol,
                         output_subcortical,tmpdir):

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

    tmp_atlas_cifti = os.path.join(tmpdir, 'temp_atlas.dtseries.nii')
    Sigma = 0  ## turning the pre-resampling smoothing behaviour off
    if Sigma > 0 :
        logger.info("Smoothing")
        #this is the whole timeseries, so don't overwrite, in order to allow on-disk writing, then delete temporary
        tmp_smoothed = os.path.join(tmpdir, 'temp_subject_smooth.dtseries.nii')
        run(['wb_command', '-cifti-smoothing', tmp_dilate_cifti,
            '0',  str(Sigma), 'COLUMN', tmp_smoothed, -fix-zeros-volume])
        #resample, delete temporary
        resample_input_cifti = tmp_smoothed
    else :
        resample_input_cifti = tmp_dilate_cifti
    logger.info("Resampling")
    run(['wb_command', '-cifti-resample',
        resample_input_cifti, 'COLUMN', tmp_roi_dlabel,
        'COLUMN', 'ADAP_BARY_AREA', 'CUBIC', tmp_atlas_cifti,
        '-volume-predilate', '10'])

    #write output volume, delete temporary
    #NOTE: $VolumefMRI contains a path in it, it is not a file in the current directory
    run(['wb_command', '-cifti-separate', tmp_atlas_cifti,
        'COLUMN', '-volume-all', output_subcortical])




def main():
    arguments  = docopt(__doc__)
    verbose      = arguments['--verbose']
    debug        = arguments['--debug']
    DRYRUN       = arguments['--dry-run']
    if arguments['--ciftify-work-dir']:
        HCPData = arguments['--ciftify-work-dir']
    else:
        HCPData = arguments["--hcp-data-dir"]
    Subject = arguments["<Subject>"]
    NameOffMRI = arguments["<NameOffMRI>"]

    if HCPData == None: HCPData = ciftify.config.find_hcp_data()

    if not os.path.exists(os.path.join(HCPData,Subject,'MNINonLinear')):
        sys.exit("Subject HCPfolder does not exit")

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
    local_logpath = os.path.join(HCPData,Subject,'MNINonLinear','Results', NameOffMRI)
    logfile = os.path.join(local_logpath, 'ciftify_subject_fmri.log')
    if os.path.exists(logfile):
        logger.error('Subject output already exits.\n To force rerun, delete or rename the logfile:\n\t{}'.format(logfile))
        sys.exit(1)
    if not os.path.exists(local_logpath): os.mkdir(local_logpath)
    fh = logging.FileHandler(logfile)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
                section_header("Starting ciftify_subject_fmri")))
    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = run_ciftify_subject_fmri(arguments, tmpdir)
    logger.info(section_header("Done"))
    sys.exit(ret)

if __name__=='__main__':
    main()
