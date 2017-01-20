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
  --MNItransform-fMRI         Register and transform the input to MNI space BEFORE aligning
  --FLIRT-dof  DOF            Degrees of freedom [default: 12] for FLIRT registration (use with '--MNItransform-fMRI')
  --FLIRT-cost COST           Cost function [default: corratio] for FLIRT registration (use with '--MNItransform-fMRI')
  --OutputSurfDiagnostics     Output some extra files for QCing the surface mapping.
  --DilateBelowPct PCT        Add a step to dilate places where signal intensity is below this percentage.
  --FinalfMRIResolution mm    Resolution [default: 2] of the proprocessed fMRI data
  --NeighborhoodSmoothing mm  Smoothing factor [default: 5] added while calculating outlier voxels
  --Factor NUM                Confidence factor [default: 0.5] for calculating outlier voxels
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
import math
import tempfile
import shutil
import subprocess
import logging


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
        if supress_stdout:
            logger.debug(out)
        else:
            logger.info(out)
        if len(err) > 0 : logger.warning(err)
        return p.returncode

def getstdout(cmdlist):
   ''' run the command given from the cmd list and report the stdout result'''
   p = subprocess.Popen(cmdlist, stdout=PIPE, stderr=PIPE)
   stdout, stderr = p.communicate()
   if p.returncode:
       logger.error('cmd: {} \n Failed with error: {}'.format(cmdlist, stderr))
   return stdout

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

def FWHM2Sigma(FWHM):
  ''' convert the FWHM to a Sigma value '''
  sigma = FWHM / (2 * math.sqrt(2*math.log(2)))
  return(sigma)

def tranform_to_MNI(InputfMRI, MNIspacefMRI, cost_function, degrees_of_freedom):
    ''' transform the fMRI image to MNI space 2x2x2mm using FSL'''
    ### these inputs should already be in the subject HCP folder
    T1wImage = os.path.join(HCP_DATA,Subject,'T1w','T1w_brain.nii.gz')
    T1w2MNI_mat = os.path.join(HCP_DATA,Subject,'MNINonLinear','xfms','T1w2StandardLinear.mat')
    T1w2MNI_warp = os.path.join(HCP_DATA,Subject,'MNINonLinear','xfms','T1w2Standard_warp_noaffine.nii.gz')
    MNITemplate2mm = os.path.join(os.environ['FSLDIR'],'data','standard', 'MNI152_T1_2mm_brain.nii.gz')
    ## make the directory to hold the transforms if it doesn't exit
    run(['mkdir','-p',os.path.join(ResultsFolder,'native')])
    ### calculate the linear transform to the T1w
    func2T1w_mat =  os.path.join(ResultsFolder,'native','mat_EPI_to_T1.mat')
    run(['flirt'
        '-in', InputfMRI,
        '-ref', T1wImage,
        '-omat', func2T1w_mat,
        '-dof', degrees_of_freedom,
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
  HCP_DATA = arguments["--hcp-data-dir"]
  Subject = arguments["<Subject>"]
  NameOffMRI = arguments["<NameOffMRI>"]
  SmoothingFWHM = arguments["<SmoothingFWHM>"]
  DilateBelowPct = arguments["--DilateBelowPct"]
  OutputSurfDiagnostics = ['--OutputSurfDiagnostics']
  FinalfMRIResolution = ['--FinalfMRIResolution']
  runMNItransform = ['--MNItransform-fMRI']
  FLIRT_dof = ['--FLIRT-dof']
  FLIRT_cost = ['--FLIRT-cost']
  NeighborhoodSmoothing = ['--NeighborhoodSmoothing']
  Factor = ['--Factor']
  DilateFactor = ['--DilateFactor']
  VERBOSE         = arguments['--verbose']
  DEBUG           = arguments['--debug']
  DRYRUN          = arguments['--dry-run']

  if not HCP_DATA: HCP_DATA = os.environ(['HCP_DATA'])

  logger.info("InputfMRI: {}".format(InputfMRI))
  logger.info("HCP_DATA: {}".format(HCP_DATA))
  logger.info("hcpSubject: {}".format(Subject))
  logger.info("NameOffMRI: {}".format(NameOffMRI))
  logger.info("SmoothingFWHM: {}".format(SmoothingFWHM))
  if DilateBelowPct:
    logger.info("Will fill holes defined as data with intensity below {} percentile".format(DilateBelowPct))

  # Setup PATHS
  GrayordinatesResolution = "2"
  LowResMesh = "32"
  RegName = "FS"

  #Templates and settings
  AtlasSpaceFolder = os.path.join(HCP_DATA, Subject, "MNINonLinear")
  DownSampleFolder = os.path.join(AtlasSpaceFolder, "fsaverage_LR32k")
  ResultsFolder = os.path.join(AtlasSpaceFolder, "Results", NameOffMRI)
  ROIFolder = os.path.join(AtlasSpaceFolder, "ROIs")
  AtlasSpaceNativeFolder = os.path.join(AtlasSpaceFolder, "Native")

  logger.info("The following settings are set by default:")
  logger.info("GrayordinatesResolution: {}".format(GrayordinatesResolution))
  logger.info('LowResMesh: {}k'.format(LowResMesh))
  logger.info('Native space surfaces are in are in: {}'.format(AtlasSpaceNativeFolder))
  logger.info('The resampled surfaces (those matching the final result are in: {}'.format(DownSampleFolder))

  # PipelineScripts=${HCPPIPEDIR_fMRISurf}

  HCPPIPEDIR_Config = os.environ['HCP_ConfigDir']

  inputfMRI4D=os.path.join(ResultsFolder,'{}.nii.gz'.format(NameOffMRI))
  inputfMRI3D=os.path.join(ResultsFolder,'{}_SBRef.nii.gz'.format(NameOffMRI))

  # output files
  if OutputSurfDiagnostics:
    DiagnosticsFolder = os.path.join(ResultsFolder, 'RibbonVolumeToSurfaceMapping')
    logging.info("Diagnostic Files will be written to: {}".format(DiagnosticsFolder))
    run(['mkdir','-p',DiagnosticsFolder])
  else:
    DiagnosticsFolder = tmpdir
  outputRibbon=os.path.join(DiagnosticsFolder,'ribbon_only.nii.gz')
  goodvoxels = os.path.join(DiagnosticsFolder, 'goodvoxels.nii.gz')

  ###### from end of volume mapping pipeline

  ## copy inputs into the ResultsFolder
  run(['mkdir','-p',ResultsFolder])

  ## either transform or copy the InputfMRI
  if runMNItransform:
      logger.info('Running transform to MNIspace with costfunction {} and dof {}'.format(FLIRT_cost, FLIRT_dof))
      tranform_to_MNI(InputfMRI, inputfMRI4D, FLIRT_cost, FLIRT_dof)
  else:
      run(['cp', InputfMRI, inputfMRI4D])

  run(['fslmaths', inputfMRI4D, '-Tmean', inputfMRI3D])

  ## read the number of TR's and the TR from the header
  TR_num = getstdout(['fslval', inputfMRI3D, 'dim4 | cut -d " " -f 1'])
  MiddleTR = int(TR_num)//2
  TR_vol = getstdout(['fslval', inputfMRI3D, 'pixdim4 | cut -d " " -f 1'])

  #Make fMRI Ribbon
  #Noisy Voxel Outlier Exclusion
  #Ribbon-based Volume to Surface mapping and resampling to standard surface
  logger.info("Make fMRI Ribbon")

  RegName="reg.reg_LR"

  LeftGreyRibbonValue = "1"
  RightGreyRibbonValue = "1"

  for Hemisphere in ['L', 'R']:
    if Hemisphere == "L":
      GreyRibbonValue = "LeftGreyRibbonValue"
    elif Hemisphere == "R":
      GreyRibbonValue = "RightGreyRibbonValue"
    fi

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
  TsdtVol = os.path.join(tmpdir, 'SD.nii.gz')
  covVol = os.path.join(tmpdir, 'cov.nii.gz')
  run(['fslmaths', inputfMRI4D, '-Tmean', TmeanVol, '-odt', 'float'])
  run(['fslmaths', inputfMRI4D, '-Tstd', TsdtVol, '-odt', 'float'])
  run(['fslmaths', TstdVol, '-div', TmeanVol, covVol])

  ## calculate a cov ribbon - modulated by the NeighborhoodSmoothing factor
  cov_ribbon = os.path.join(tmpdir, 'cov_ribbon.nii.gz')
  cov_ribbonMean = getstout(['fslstats', cov_ribbon, '-M'])
  cov_ribbon_norm = os.path.join(tmpdir, 'cov_ribbon_norm.nii.gz')
  SmoothNorm = os.path.join(tmpdir, 'SmoothNorm.nii.gz')
  cov_ribbon_norm_smooth = os.path.join(tmpdir, 'cov_ribbon_norm_smooth.nii.gz')
  cov_norm_modulate = os.path.join(tmpdir, 'cov_norm_modulate.nii.gz')
  cov_norm_modulate_ribbon = os.path.join(tmpdir, 'cov_norm_modulate_ribbon.nii.gz')
  run(['fslmaths', covVol,'-mas', outputRibbon, cov_ribbon])
  cov_ribbonMean = getstout(['fslstats', cov_ribbon, '-M'])
  run(['fslmaths', cov_ribbon, '-div', cov_ribbonMean, cov_ribbon_norm])
  run(['fslmaths', cov_ribbon_norm, '-bin', '-s', NeighborhoodSmoothing, SmoothNorm])
  run(['fslmaths', cov_ribbon_norm, '-s', NeighborhoodSmoothing,
   '-div', SmoothNorm, '-dilD', cov_ribbon_norm_smooth])
  run(['fslmaths', covVol, '-div', cov_ribbonMean,
  '-div', cov_ribbon_norm_smooth, cov_norm_modulate])
  run(['fslmaths', cov_norm_modulate,
  '-mas', outputRibbon, cov_norm_modulate_ribbon])

  ## get stats from the modulated cov ribbon file and log them
  ribbonMEAN = getstdout(['fslstats', cov_norm_modulate_ribbon, '-M'])
  logger.info('Ribbon Mean: {}'.format(ribbonMean))
  ribbonSTD = getstdout(['fslstats', cov_norm_modulate_ribbon, '-S'])
  logger.info('Ribbon STD: {}'.format(ribbonSTD))
  ribbonLower = float(ribbonMean) - (float(ribbonSTD)*float(Factor))
  logger.info('Ribbon Lower: {}'.format(ribbonLower))
  ribbonUpper = float(ribbonMean) + (float(ribbonSTD)*float(Factor))
  logger.info('Ribbon Upper: {}'.format(ribbonUpper))

  ## get a basic brain mask from the mean img
  bmaskVol = os.path.join(tmpdir, 'mask.nii.gz')
  run(['fslmaths', TmeanVol, '-bin', bmaskVol])

  ## make a goodvoxels mask img
  run(['fslmaths', cov_norm_modulate,
  '-thr', ribbonUpper, '-bin', '-sub', bmaskVol, '-mul', '-1',
  goodvoxels])

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
    DilThres = getstdout(['wb_command', '-metric-stats', input_func_native,
      '-percentile', DilateBelowPct,
      '-column', MiddleTR,
      '-roi', roi_native_gii])
    lowvoxels_gii = os.path.join(tmpdir,'{}.lowvoxels.native.func.gii'.format(Hemisphere))
    run(['wb_command', '-metric-math',
     "x < {}".format(DilThres),
     lowvoxels_gii, '-var', 'x', input_func_native, '-column', MiddleTR])
    run(['wb_command', '-metric-dilate', input_func_native,
      mid_surf_native, DilateFactor, input_func_native,
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
    Sigma = FWHM2Sigma(SmoothingFWHM)
    logging.info("Surface Smoothing with Sigma {}".format(Sigma))

    run(['wb_command', '-metric-smoothing',
      mid_surf_32k,
      input_func_32k,
      Sigma,
      os.path.join(tmpdir,
        '{}_s{}.atlasroi.{}.{}k_fs_LR.func.gii'.format(NameOffMRI,SmoothingFWHM,Hemisphere, LowResMesh)),
      '-roi', roi_32k_gii])

    if OutputSurfDiagnostics:
      for mapname in ["mean", "cov"]:

        if mapname == "mean": map_vol = TmeanVol
        if mapname == "cov": map_vol = covVol

        ## the output directories for this section
        map_native_gii = os.path.join(tmpdir, '{}.{}.native.func.gii'.format(mapname, Hemisphere))
        map_32k_gii = os.path.join(tmpdir,"{}.{}.{}k_fs_LR.func.gii".format(Hemisphere, mapname, LowResMesh))
        run(['wb_command', '-volume-to-surface-mapping',
          map_vol, mid_surf_native, map_native_gii,
          '-ribbon-constrained', white_surf, pial_surf,
          '-volume-roi', goodvoxels])
        run(['wb_command', '-metric-dilate',
          map_native_gii, mid_surf_native, DilateFactor, mapall_natve_gii, '-nearest'])
        mask_and_resample(map_native_gii, mapall_32k_gii,
            roi_native_gii, roi_32k_gii,
            mid_surf_native, mid_surf_32k,
            sphere_reg_native, sphere_reg_32k)

        mapall_natve_gii = os.path.join(tmpdir, '{}_all.{}.native.func.gii'.format(mapname, Hemisphere))
        mapall_32k_gii = os.path.join(tmpdir,"{}.{}_all.{}k_fs_LR.func.gii".format(Hemisphere, mapname, LowResMesh))
        run(['wb_command', '-volume-to-surface-mapping',
          map_vol, mid_surf, mapall_natve_gii,
         '-ribbon-constrained', white_surf, pial_surf])
        mask_and_resample(mapall_natve_gii, mapall_32k_gii,
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
      lowvoxels_32k_gii = os.path.join(tmpdir,'{}.lowvoxels.{}k_fs_LR.func.gii'.format(Hemisphere, LowResMesh))
      mask_and_resample(lowvoxels_gii, lowvoxels_32k_gii,
         roi_native_gii, roi_32k_gii,
         mid_surf_native, mid_surf_32k,
         sphere_reg_native, sphere_reg_32k)

  if OutputSurfDiagnostics:
    for Map in ['goodvoxels', 'lowvoxels', 'mean', 'mean_all', 'cov', 'cov_all']:
      run(['wb_command', '-cifti-create-dense-scalar',
        os.path.join(DiagnosticsFolder, '{}.atlasroi.{}k_fs_LR.dscalar.nii'.format(Map, LowResMesh)),
        '-left-metric', os.path.join(tmpdir,'L.{}.{}k_fs_LR.func.gii'.format(Map, LowResMesh)),
        '-roi-left', os.path.join(DownSampleFolder,
          '{}.L.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, LowResMesh)),
        '-right-metric', os.path.join(tmpdir,'R.{}.{}k_fs_LR.func.gii'.format(Map, LowResMesh)),
        '-roi-right', os.path.join(DownSampleFolder, '{}.R.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, LowResMesh))])


  ############ The subcortical resampling step...
  logger.info("Subcortical Processing")
  logger.info("VolumefMRI: {}".format(inputfMRI4D))

  Sigma = FWHM2Sigma(SmoothingFWHM)
  logger.info("Sigma: {}".format(Sigma))

  Atlas_Subcortical = os.path.join(tmpdir, '{}_AtlasSubcortical_s{}.nii.gz'.format(NameOffMRI,SmoothingFWHM))
  ##unset POSIXLY_CORRECT

  if GrayordinatesResolution == FinalfMRIResolution :
    logging.info("Doing volume parcel resampling without first applying warp")

    ## inputs for this section
    ROIvols = os.path.join(ROIFolder, 'ROIs.{}.nii.gz'.format(GrayordinatesResolution))
    AtlasROIvols = os.path.join(ROIFolder,'Atlas_ROIs.{}.nii.gz'.format(GrayordinatesResolution))

    run(['wb_command', '-volume-parcel-resampling',
      inputfMRI4D,
      ROIvols, AtlasROIvols,
      Sigma,
      Atlas_Subcortical,
      '-fix-zeros'])
  else:
    logging.info("Doing applywarp and volume label import")

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

    logging.info("Doing volume parcel resampling after applying warp and doing a volume label import")
    run(['wb_command', '-volume-parcel-resampling-generic',
      inputfMRI4D,
      roi_res, AtlasROIvols,
      Sigma,
      Atlas_Subcortical,
      '-fix-zeros'])

  #Generation of Dense Timeseries
  logging.info("Generation of Dense Timeseries")
  run(['wb_command', '-cifti-create-dense-timeseries',
    os.path.join(ResultsFolder, '{}_Atlas_s{}.dtseries.nii'.format(NameOffMRI, SmoothingFWHM)),
    '-volume', Atlas_Subcortical,
    Atlas_Subcortical,
    '-left-metric', os.path.join(tmpdir,
      '{}_s{}.atlasroi.L.{}k_fs_LR.func.gii'.format(NameOffMRI,SmoothingFWHM,LowResMesh)),
    '-roi-left', os.path.join(DownSampleFolder,
      '{}.L.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, LowResMesh)),
    '-right-metric', os.path.join(tmpdir,
      '{}_s{}.atlasroi.L.{}k_fs_LR.func.gii'.format(NameOffMRI,SmoothingFWHM,LowResMesh)),
    '-roi-right', os.path.join(DownSampleFolder,
      '{}.L.atlasroi.{}k_fs_LR.shape.gii'.format(Subject, LowResMesh)),
    '-timestep', TR_vol])

  logger.info("Completed")

if __name__=='__main__':

    arguments  = docopt(__doc__)

    global DRYRUN

    VERBOSE      = arguments['--verbose']
    DEBUG        = arguments['--debug']
    DRYRUN       = arguments['--dry-run']

    # create a local tmpdir
    tmpdir = tempfile.mkdtemp()
    logger.setLevel(logging.WARNING)

    if VERBOSE:
        logger.setLevel(logging.INFO)

    if DEBUG:
        logger.setLevel(logging.DEBUG)

    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # logger.setFormatter(formatter)


    logger.info('Creating tempdir:{} on host:{}'.format(tmpdir, os.uname()[1]))
    ret = main(arguments, tmpdir)
    shutil.rmtree(tmpdir)
    sys.exit(ret)
