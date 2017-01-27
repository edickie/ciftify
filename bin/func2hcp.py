#!/usr/bin/env python
"""
Projects a fMRI timeseries to and HCP dtseries file and does smoothing

Usage:
  func2hcp.py [options] <func.nii.gz> <Subject> <NameOffMRI> <SmoothingFWHM>

Arguments:
    <func.nii.gz>           Nifty 4D volume to project to cifti space
    <Subject>               The Subject ID in the HCP data folder
    <NameOffMRI>            The outputname for the cifti result folder
    <SmoothingFWHM>         The Full-Width-at-Half-Max for smoothing steps

Options:
  --hcp-data-dir PATH         Path to the HCP_DATA directory (overides the HCP_DATA environment variable)
  --no-MNItransform           Do not register and transform the input to MNI space BEFORE aligning
  --FLIRT-dof DOF             Degrees of freedom [default: 12] for FLIRT registration (use with '--MNItransform-fMRI')
  --FLIRT-cost COST           Cost function [default: corratio] for FLIRT registration (use with '--MNItransform-fMRI')
  --OutputSurfDiagnostics     Output some extra files for QCing the surface mapping.
  --DilateBelowPct PCT        Add a step to dilate places where signal intensity is below this percentage.
  --FinalfMRIResolution mm    Resolution [default: 2] of the proprocessed fMRI data
  --NeighborhoodSmoothing mm  Smoothing factor [default: 5] added while calculating outlier voxels
  --CI NUM                    Confidence factor [default: 0.5] for calculating outlier voxels
  --Dilate-MM MM              Distance in mm [default: 10] to dilate when filling holes in mesh
  -v,--verbose                Verbose logging
  --debug                     Debug logging in Erin's very verbose style
  -n,--dry-run                Dry run
  -h,--help                   Print help

DETAILS
Adapted from the fMRISurface module of the HCP Pipeline

We assume that the data is already registered and transformed to the MNI template,
and that the voxel resolution is 2x2x2mm. If this is not the case, you can use the
(--MNItransform-fMRI) option to do before all other steps.
FSL's flirt is used to register the fMRI to the T1w image,
this is concatenated to the non-linear transform to MNIspace in the xfms folder.
Options for FSL's flirt can be changed using the "--FLIRT-dof" and "--FLIRT-cost".

Written by Erin W Dickie, Jan 12, 2017
"""
from docopt import docopt
import os
import sys
import math
import datetime
import tempfile
import shutil
import subprocess
import logging
import ciftify

#logging.logging.setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
            sys.exit(p)
        if supress_stdout:
            logger.debug(out)
        else:
            logger.info(out)
        if len(err) > 0 : logger.warning(err)
        return p.returncode

def getstdout(cmdlist):
   ''' run the command given from the cmd list and report the stdout result'''
   logger.info('Evaluating: {}'.format(' '.join(cmdlist)))
   stdout = subprocess.check_output(cmdlist)
   return stdout

def first_word(text):
    '''return only the first word in a string'''
    FirstWord = text.split(' ', 1)[0]
    return(text)

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
    logger.info("Username: {}".format(getstdout(['whoami'])))
    logger.info(ciftify.config.system_info())
    logger.info(ciftify.config.ciftify_version(os.path.basename(__file__)))
    logger.info(ciftify.config.wb_command_version())
    logger.info(ciftify.config.freesurfer_version())
    logger.info(ciftify.config.fsl_version())

def FWHM2Sigma(FWHM):
  ''' convert the FWHM to a Sigma value '''
  sigma = FWHM / (2 * math.sqrt(2*math.log(2)))
  return(sigma)

def transform_to_MNI(InputfMRI, MNIspacefMRI, cost_function, degrees_of_freedom, HCPData, Subject):
    ''' transform the fMRI image to MNI space 2x2x2mm using FSL'''
    ### these inputs should already be in the subject HCP folder
    T1wImage = os.path.join(HCPData,Subject,'T1w','T1w_brain.nii.gz')
    T1w2MNI_mat = os.path.join(HCPData,Subject,'MNINonLinear','xfms','T1w2StandardLinear.mat')
    T1w2MNI_warp = os.path.join(HCPData,Subject,'MNINonLinear','xfms','T1w2Standard_warp_noaffine.nii.gz')
    MNITemplate2mm = os.path.join(os.environ['FSLDIR'],'data','standard', 'MNI152_T1_2mm_brain.nii.gz')
    ResultsFolder = os.path.dirname(MNIspacefMRI)
    ## make the directory to hold the transforms if it doesn't exit
    run(['mkdir','-p',os.path.join(ResultsFolder,'native')])
    ### calculate the linear transform to the T1w
    func2T1w_mat =  os.path.join(ResultsFolder,'native','mat_EPI_to_T1.mat')
    run(['flirt',
        '-in', InputfMRI,
        '-ref', T1wImage,
        '-omat', func2T1w_mat,
        '-dof', str(degrees_of_freedom),
        '-cost', cost_function, '-searchcost', cost_function,
        '-searchrx', '-180', '180', '-searchry', '-180', '180', '-searchrz', '-180', '180'])
    ## concatenate the transforms
    func2MNI_mat = os.path.join(ResultsFolder,'native','mat_EPI_to_TAL.mat')
    run(['convert_xfm','-omat', func2MNI_mat, '-concat', T1w2MNI_mat, func2T1w_mat])
    ## now apply the warp!!
    run(['applywarp',
        '--ref={}'.format(MNITemplate2mm),
        '--in={}'.format(InputfMRI),
        '--warp={}'.format(T1w2MNI_warp),
        '--premat={}'.format(os.path.join(ResultsFolder,'native','mat_EPI_to_TAL.mat')),
        '--interp=spline',
        '--out={}'.format(MNIspacefMRI)])

def main(arguments, tmpdir):

  InputfMRI = arguments["<func.nii.gz>"]
  HCPData = arguments["--hcp-data-dir"]
  Subject = arguments["<Subject>"]
  NameOffMRI = arguments["<NameOffMRI>"]
  SmoothingFWHM = arguments["<SmoothingFWHM>"]
  DilateBelowPct = arguments["--DilateBelowPct"]
  OutputSurfDiagnostics = arguments['--OutputSurfDiagnostics']
  FinalfMRIResolution = arguments['--FinalfMRIResolution']
  noMNItransform = arguments['--no-MNItransform']
  FLIRT_dof = arguments['--FLIRT-dof']
  FLIRT_cost = arguments['--FLIRT-cost']
  NeighborhoodSmoothing = arguments['--NeighborhoodSmoothing']
  DilateFactor = arguments['--Dilate-MM']
  CI_limit = arguments['--CI']
  VERBOSE         = arguments['--verbose']
  DEBUG           = arguments['--debug']
  DRYRUN          = arguments['--dry-run']

  if HCPData == None: HCPData = ciftify.config.find_hcp_data()

  ## write a bunch of info about the environment to the logs
  log_build_environment()

  logger.info('Arguments:')
  logger.info("\tInputfMRI: {}".format(InputfMRI))
  if not os.path.isfile(InputfMRI):
      logger.error("InputfMRI does not exist :(..Exiting")
      sys.exit(1)
  logger.info("\tHCP_DATA: {}".format(HCPData))
  logger.info("\thcpSubject: {}".format(Subject))
  logger.info("\tNameOffMRI: {}".format(NameOffMRI))
  logger.info("\tSmoothingFWHM: {}".format(SmoothingFWHM))
  if DilateBelowPct:
    logger.info("\tWill fill holes defined as data with intensity below {} percentile".format(DilateBelowPct))

  # Setup PATHS
  GrayordinatesResolution = "2"
  LowResMesh = "32"
  RegName = "FS"

  #Templates and settings
  AtlasSpaceFolder = os.path.join(HCPData, Subject, "MNINonLinear")
  DownSampleFolder = os.path.join(AtlasSpaceFolder, "fsaverage_LR32k")
  ResultsFolder = os.path.join(AtlasSpaceFolder, "Results", NameOffMRI)
  ROIFolder = os.path.join(AtlasSpaceFolder, "ROIs")
  AtlasSpaceNativeFolder = os.path.join(AtlasSpaceFolder, "Native")

  logger.info("The following settings are set by default:")
  logger.info("\nGrayordinatesResolution: {}".format(GrayordinatesResolution))
  logger.info('\nLowResMesh: {}k'.format(LowResMesh))
  logger.info('Native space surfaces are in are in: {}'.format(AtlasSpaceNativeFolder))
  logger.info('The resampled surfaces (those matching the final result are in: {}'.format(DownSampleFolder))

  # PipelineScripts=${HCPPIPEDIR_fMRISurf}

  HCPPIPEDIR_Config = os.path.join(ciftify.config.find_ciftify_global(),'hcp_config')

  inputfMRI4D=os.path.join(ResultsFolder,'{}.nii.gz'.format(NameOffMRI))
  inputfMRI3D=os.path.join(ResultsFolder,'{}_SBRef.nii.gz'.format(NameOffMRI))

  # output files
  if OutputSurfDiagnostics:
    DiagnosticsFolder = os.path.join(ResultsFolder, 'RibbonVolumeToSurfaceMapping')
    logger.info("Diagnostic Files will be written to: {}".format(DiagnosticsFolder))
    run(['mkdir','-p',DiagnosticsFolder])
  else:
    DiagnosticsFolder = tmpdir
  outputRibbon=os.path.join(DiagnosticsFolder,'ribbon_only.nii.gz')
  goodvoxels = os.path.join(DiagnosticsFolder, 'goodvoxels.nii.gz')

  ###### from end of volume mapping pipeline

  ## copy inputs into the ResultsFolder
  run(['mkdir','-p',ResultsFolder])

  ## either transform or copy the InputfMRI
  if noMNItransform:
      run(['cp', InputfMRI, inputfMRI4D])
  else:
      logger.info(section_header('MNI Transform'))
      logger.info('Running transform to MNIspace with costfunction {} and dof {}'.format(FLIRT_cost, FLIRT_dof))
      transform_to_MNI(InputfMRI, inputfMRI4D, FLIRT_cost, FLIRT_dof, HCPData, Subject)

  run(['fslmaths', inputfMRI4D, '-Tmean', inputfMRI3D])

  ## read the number of TR's and the TR from the header
  TR_num = first_word(getstdout(['fslval', inputfMRI4D, 'dim4']))
  logger.info('Number of TRs: {}'.format(TR_num))
  MiddleTR = int(TR_num)/2
  logger.info('Middle TR: {}'.format(MiddleTR))
  TR_vol = first_word(getstdout(['fslval', inputfMRI4D, 'pixdim4']))
  logger.info('TR(ms): {}'.format(TR_vol))

  #Make fMRI Ribbon
  #Noisy Voxel Outlier Exclusion
  #Ribbon-based Volume to Surface mapping and resampling to standard surface
  logger.info(section_header('Making fMRI Ribbon'))

  RegName="reg.reg_LR"

  LeftGreyRibbonValue = "1"
  RightGreyRibbonValue = "1"

  for Hemisphere in ['L', 'R']:
    if Hemisphere == "L":
      GreyRibbonValue = LeftGreyRibbonValue
    elif Hemisphere == "R":
      GreyRibbonValue = RightGreyRibbonValue

    ## the inputs are..
    white_surf = os.path.join(AtlasSpaceNativeFolder, '{}.{}.white.native.surf.gii'.format(Subject,Hemisphere))
    pial_surf = os.path.join(AtlasSpaceNativeFolder, '{}.{}.pial.native.surf.gii'.format(Subject,Hemisphere))

    ## create a volume of distances from the surface
    tmp_white_vol = os.path.join(tmpdir,'{}.{}.white.native.nii.gz'.format(Subject, Hemisphere))
    tmp_pial_vol = os.path.join(tmpdir,'{}.{}.pial.native.nii.gz'.format(Subject, Hemisphere))
    run(['wb_command', '-create-signed-distance-volume',
      white_surf, inputfMRI3D, tmp_white_vol])
    run(['wb_command', '-create-signed-distance-volume',
      pial_surf, inputfMRI3D, tmp_pial_vol])

    ## threshold and binarise these distance files
    tmp_whtie_vol_thr = os.path.join(tmpdir,'{}.{}.white_thr0.native.nii.gz'.format(Subject, Hemisphere))
    tmp_pial_vol_thr = os.path.join(tmpdir,'{}.{}.pial_uthr0.native.nii.gz'.format(Subject, Hemisphere))
    run(['fslmaths', tmp_white_vol, '-thr', '0', '-bin', '-mul', '255', tmp_whtie_vol_thr])
    run(['fslmaths', tmp_whtie_vol_thr, '-bin', tmp_whtie_vol_thr])
    run(['fslmaths', tmp_pial_vol, '-uthr', '0', '-abs', '-bin', '-mul', '255', tmp_pial_vol_thr])
    run(['fslmaths', tmp_pial_vol_thr, '-bin', tmp_pial_vol_thr])

    ## combine the pial and white to get the ribbon
    tmp_ribbon = os.path.join(tmpdir,'{}.{}.ribbon.nii.gz'.format(Subject,Hemisphere))
    run(['fslmaths', tmp_pial_vol_thr,
      '-mas', tmp_whtie_vol_thr,
      '-mul', '255',
      tmp_ribbon])
    run(['fslmaths', tmp_ribbon, '-bin', '-mul', GreyRibbonValue,
       os.path.join(tmpdir,'{}.{}.ribbon.nii.gz'.format(Subject,Hemisphere))])

  # combine the left and right ribbons into one mask
  run(['fslmaths',
  os.path.join(tmpdir,'{}.L.ribbon.nii.gz'.format(Subject)),
  '-add',
  os.path.join(tmpdir,'{}.R.ribbon.nii.gz'.format(Subject)),
  outputRibbon])

  ## calculate Coefficient of Variation (cov) of the fMRI
  TMeanVol = os.path.join(tmpdir, 'Mean.nii.gz')
  TstdVol = os.path.join(tmpdir, 'SD.nii.gz')
  covVol = os.path.join(tmpdir, 'cov.nii.gz')
  run(['fslmaths', inputfMRI4D, '-Tmean', TMeanVol, '-odt', 'float'])
  run(['fslmaths', inputfMRI4D, '-Tstd', TstdVol, '-odt', 'float'])
  run(['fslmaths', TstdVol, '-div', TMeanVol, covVol])

  ## calculate a cov ribbon - modulated by the NeighborhoodSmoothing factor
  cov_ribbon = os.path.join(tmpdir, 'cov_ribbon.nii.gz')
  cov_ribbon_norm = os.path.join(tmpdir, 'cov_ribbon_norm.nii.gz')
  SmoothNorm = os.path.join(tmpdir, 'SmoothNorm.nii.gz')
  cov_ribbon_norm_smooth = os.path.join(tmpdir, 'cov_ribbon_norm_smooth.nii.gz')
  cov_norm_modulate = os.path.join(tmpdir, 'cov_norm_modulate.nii.gz')
  cov_norm_modulate_ribbon = os.path.join(tmpdir, 'cov_norm_modulate_ribbon.nii.gz')
  run(['fslmaths', covVol,'-mas', outputRibbon, cov_ribbon])
  cov_ribbonMean = first_word(getstdout(['fslstats', cov_ribbon, '-M']))
  cov_ribbonMean = cov_ribbonMean.rstrip(os.linesep) ## remove return
  run(['fslmaths', cov_ribbon, '-div', cov_ribbonMean, cov_ribbon_norm])
  run(['fslmaths', cov_ribbon_norm, '-bin', '-s', NeighborhoodSmoothing, SmoothNorm])
  run(['fslmaths', cov_ribbon_norm, '-s', NeighborhoodSmoothing,
   '-div', SmoothNorm, '-dilD', cov_ribbon_norm_smooth])
  run(['fslmaths', covVol, '-div', cov_ribbonMean,
  '-div', cov_ribbon_norm_smooth, cov_norm_modulate])
  run(['fslmaths', cov_norm_modulate,
  '-mas', outputRibbon, cov_norm_modulate_ribbon])

  ## get stats from the modulated cov ribbon file and log them
  ribbonMean = first_word(getstdout(['fslstats', cov_norm_modulate_ribbon, '-M']))
  logger.info('Ribbon Mean: {}'.format(ribbonMean))
  ribbonSTD = first_word(getstdout(['fslstats', cov_norm_modulate_ribbon, '-S']))
  logger.info('Ribbon STD: {}'.format(ribbonSTD))
  ribbonLower = float(ribbonMean) - (float(ribbonSTD)*float(CI_limit))
  logger.info('Ribbon Lower: {}'.format(ribbonLower))
  ribbonUpper = float(ribbonMean) + (float(ribbonSTD)*float(CI_limit))
  logger.info('Ribbon Upper: {}'.format(ribbonUpper))

  ## get a basic brain mask from the mean img
  bmaskVol = os.path.join(tmpdir, 'mask.nii.gz')
  run(['fslmaths', TMeanVol, '-bin', bmaskVol])

  ## make a goodvoxels mask img
  run(['fslmaths', cov_norm_modulate,
  '-thr', str(ribbonUpper), '-bin', '-sub', bmaskVol, '-mul', '-1',
  goodvoxels])

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
     inputfMRI4D, mid_surf_native, input_func_native,
     '-ribbon-constrained', white_surf, pial_surf,
     '-volume-roi', goodvoxels])

    ## dilate to get rid of wholes caused by the goodvoxels mask
    run(['wb_command', '-metric-dilate',
      input_func_native, mid_surf_native, DilateFactor,
      input_func_native, '-nearest'])

    ## Erin's new addition - find what is below a certain percentile and dilate..
    ## Erin's new addition - find what is below a certain percentile and dilate..
    if DilateBelowPct:
        DilThres = getstdout(['wb_command', '-metric-stats', input_func_native,
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

    #Surface Smoothing
    Sigma = FWHM2Sigma(float(SmoothingFWHM))
    logger.info(section_header("Surface Smoothing"))
    logger.info("FWHM: {}".format(SmoothingFWHM))
    logger.info("Sigma: {}".format(Sigma))

    run(['wb_command', '-metric-smoothing',
      mid_surf_32k,
      input_func_32k,
      '{}'.format(Sigma),
      os.path.join(tmpdir,
        '{}_s{}.atlasroi.{}.{}k_fs_LR.func.gii'.format(NameOffMRI,SmoothingFWHM,Hemisphere, LowResMesh)),
      '-roi', roi_32k_gii])

    if OutputSurfDiagnostics:
        logger.info(section_header('Writing Surface Mapping Diagnotic Files'))

        for mapname in ["mean", "cov"]:

            if mapname == "mean": map_vol = TMeanVol
            if mapname == "cov": map_vol = covVol

            ## the output directories for this section
            map_native_gii = os.path.join(tmpdir, '{}.{}.native.func.gii'.format(mapname, Hemisphere))
            map_32k_gii = os.path.join(tmpdir,"{}.{}.{}k_fs_LR.func.gii".format(Hemisphere, mapname, LowResMesh))
            run(['wb_command', '-volume-to-surface-mapping',
              map_vol, mid_surf_native, map_native_gii,
              '-ribbon-constrained', white_surf, pial_surf,
              '-volume-roi', goodvoxels])
            run(['wb_command', '-metric-dilate',
              map_native_gii, mid_surf_native, DilateFactor, map_native_gii, '-nearest'])
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
        run(['wb_command', '-volume-to-surface-mapping', goodvoxels,
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
  logger.info("VolumefMRI: {}".format(inputfMRI4D))

  Sigma = FWHM2Sigma(float(SmoothingFWHM))
  logger.info("Sigma: {}".format(Sigma))

  Atlas_Subcortical = os.path.join(tmpdir, '{}_AtlasSubcortical_s{}.nii.gz'.format(NameOffMRI,SmoothingFWHM))
  ##unset POSIXLY_CORRECT

  if GrayordinatesResolution == FinalfMRIResolution :
    logger.info("Doing volume parcel resampling without first applying warp")

    ## inputs for this section
    ROIvols = os.path.join(ROIFolder, 'ROIs.{}.nii.gz'.format(GrayordinatesResolution))
    AtlasROIvols = os.path.join(ROIFolder,'Atlas_ROIs.{}.nii.gz'.format(GrayordinatesResolution))

    run(['wb_command', '-volume-parcel-resampling',
      inputfMRI4D,
      ROIvols, AtlasROIvols,
      '{}'.format(Sigma),
      Atlas_Subcortical,
      '-fix-zeros'])
  else:
    logger.info("Doing applywarp and volume label import")

    ## inputs for this version
    wmparc = os.path.join(AtlasSpaceFolder, 'wmparc.nii.gz')
    AtlasROIvols = os.path.join(ROIFolder,'Atlas_ROIs.{}.nii.gz'.format(GrayordinatesResolution))

    ## resample the wmparc masks to inputfMRI4D
    wmparc_res = os.path.join(tmpdir, 'wmparc.{}.nii.gz'.format(FinalfMRIResolution))
    run(['applywarp', '--interp=nn',
      '-i', wmparc,
      '-r', inputfMRI4D,
      '-o', wmparc_res])

    ## import the labels into the wparc file
    rois_res = os.path.join(ResultsFolder, 'ROIs.{}.nii.gz'.format(FinalfMRIResolution))
    run(['wb_command',
      '-volume-label-import', wmparc_res,
      os.path.join(HCPPIPEDIR_Config,'FreeSurferSubcorticalLabelTableLut.txt'),
      rois_res, '-discard-others'])

    logger.info("Doing volume parcel resampling after applying warp and doing a volume label import")
    run(['wb_command', '-volume-parcel-resampling-generic',
      inputfMRI4D,
      roi_res, AtlasROIvols,
      '{}'.format(Sigma),
      Atlas_Subcortical,
      '-fix-zeros'])

  #Generation of Dense Timeseries
  logger.info(section_header("Generation of Dense Timeseries"))
  run(['wb_command', '-cifti-create-dense-timeseries',
    os.path.join(ResultsFolder, '{}_Atlas_s{}.dtseries.nii'.format(NameOffMRI, SmoothingFWHM)),
    '-volume', Atlas_Subcortical,
    AtlasROIvols,
    '-left-metric', os.path.join(tmpdir,
      '{}_s{}.atlasroi.L.{}k_fs_LR.func.gii'.format(NameOffMRI,SmoothingFWHM,LowResMesh)),
    '-roi-left', os.path.join(DownSampleFolder,
      '{}.L.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, LowResMesh)),
    '-right-metric', os.path.join(tmpdir,
      '{}_s{}.atlasroi.L.{}k_fs_LR.func.gii'.format(NameOffMRI,SmoothingFWHM,LowResMesh)),
    '-roi-right', os.path.join(DownSampleFolder,
      '{}.L.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, LowResMesh)),
    '-timestep', TR_vol])

  logger.info(section_header("Done"))

if __name__=='__main__':

    arguments  = docopt(__doc__)

    global DRYRUN

    VERBOSE      = arguments['--verbose']
    DEBUG        = arguments['--debug']
    DRYRUN       = arguments['--dry-run']
    HCPData = arguments["--hcp-data-dir"]
    Subject = arguments["<Subject>"]
    NameOffMRI = arguments["<NameOffMRI>"]

    if HCPData == None: HCPData = ciftify.config.find_hcp_data()
    # create a local tmpdir
    tmpdir = tempfile.mkdtemp()

    if not os.path.exists(os.path.join(HCPData,Subject,'MNINonLinear')):
        sys.exit("Subject HCPfolder does not exit")

    local_logpath = os.path.join(HCPData,Subject,'MNINonLinear','Results', NameOffMRI)

    if not os.path.exists(local_logpath): os.mkdir(local_logpath)

    fh = logging.FileHandler(os.path.join(local_logpath, 'func2hcp.log'))
    ch = logging.StreamHandler()
    fh.setLevel(logging.INFO)
    ch.setLevel(logging.WARNING)

    if VERBOSE:
        ch.setLevel(logging.INFO)

    if DEBUG:
        ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(message)s')

    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(section_header("Starting func2hcp"))
    logger.info('Creating tempdir:{} on host:{}'.format(tmpdir, os.uname()[1]))
    ret = main(arguments, tmpdir)
    shutil.rmtree(tmpdir)
    sys.exit(ret)
