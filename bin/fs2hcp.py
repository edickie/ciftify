#!/usr/bin/env python
"""
Converts a freesurfer recon-all output to a HCP data directory

Usage:
  func2hcp.py [options] <Subject>

Arguments:
    <Subject>               The Subject ID in the HCP data folder

Options:
  --hcp-data-dir PATH         Path to the HCP_DATA directory (overides the HCP_DATA environment variable)
  --fs-subjects-dir PATH      Path to the freesurfer SUBJECTS_DIR directory (overides the SUBJECTS_DIR environment variable)
  --resample-LowRestoNative   Resample the 32k Meshes to Native Space (creates additional output files)
  -v,--verbose                Verbose logging
  --debug                     Debug logging in Erin's very verbose style
  -n,--dry-run                Dry run
  -h,--help                   Print help

DETAILS
Adapted from the PostFreeSurferPipeline module of the HCP Pipeline

Written by Erin W Dickie, Jan 19, 2017
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

def define_dscalarsDict(RegName):
    dscalarsDict = {
        'sulc': {
            'mapname': 'sulc',
            'fsname': 'sulc',
            'map_posfix': '_Sulc',
            'palette_mode': 'MODE_AUTO_SCALE_PERCENTAGE',
            'palette_options': '-pos-percent 2 98 -palette-name Gray_Interp -disp-pos true -disp-neg true -disp-zero true',
            'mask_medialwall': False
                 },
        'curvature': {
            'mapname': 'curvature',
            'fsname': 'curv',
            'map_posfix': '_Curvature',
            'palette_mode': 'MODE_AUTO_SCALE_PERCENTAGE',
            'palette_options': '-pos-percent 2 98 -palette-name Gray_Interp -disp-pos true -disp-neg true -disp-zero true',
            'mask_medialwall': True
        },
        'thickness': {
            'mapname': 'thickness',
            'fsname': 'thickness',
            'map_posfix':'_Thickness',
            'palette_mode': 'MODE_AUTO_SCALE_PERCENTAGE',
            'palette_options': '-pos-percent 4 96 -interpolate true -palette-name videen_style -disp-pos true -disp-neg false, -disp-zero false',
            'mask_medialwall': True
        },
        'ArealDistortion_FS': {
            'mapname' : 'ArealDistortion_FS'
            'map_posfix':'_ArealDistortion_FS',
            'palette_mode': 'MODE_USER_SCALE',
            'palette_options': '-pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false',
            'mask_medialwall': False
        }
    }

    if  RegName == "MSMSulc":
        dscalarDict['ArealDistortion_MSMSulc'] = {
            'mapname': 'ArealDisortion_MSMSulc',
            'map_posfix':'_ArealDistortion_MSMSulc',
            'palette_mode': 'MODE_USER_SCALE',
            'palette_options': '-pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false',
            'mask_medialwall': False
        }
    return(dscalarsDict)


def define_SpacesDict(HCP_DATA, Subject, HighResMesh, LowResMeshes,
    tmpdir, MakeLowReshNative = False):
    '''sets up a dictionary of expected paths for each mesh'''
    SpacesDict = {
        'T1wNative':{
            'Folder' : os.path.join(HCP_DATA, Subject, 'T1w', 'Native'),
            'ROI': 'roi',
            'meshname': 'native',
            'tmpdir': os.path.join(tmpdir, 'native'),
            'T1wImage': os.path.join(HCP_DATA, Subject, 'T1w', 'T1w.nii.gz'),
            'DenseMapsFolder': os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'Native')},
        'AtlasSpaceNative':{
            'Folder' : os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'Native'),
            'ROI': 'roi',
            'meshname': 'native',
            'tmpdir': os.path.join(tmpdir, 'native'),
            'T1wImage': os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'T1w.nii.gz')},
        'HighResMesh':{
            'Folder' : os.path.join(HCP_DATA, Subject, 'MNINonLinear')
            'ROI': 'atlasroi',
            'meshname': '{}k_fs_LR'.format(HighResMesh)},
            'tmpdir': os.path.join(tmpdir, '{}k_fs_LR'.format(HighResMesh),
            'T1wImage': os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'T1w.nii.gz'))
    }
    for LowResMesh in LowResMeshes:
        SpacesDict['{}k_fs_LR'.format(LowResMesh)] = {
            'Folder': os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'fsaverage_LR{}'.format(LowResMesh)),
            'ROI' : 'atlasroi',
            'meshname': 'fsaverage_LR{}'.format(LowResMesh)),
            'tmpdir': os.path.join(tmpdir, '{}k_fs_LR'.format(LowResMesh)),
            'T1wImage': os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'T1w.nii.gz')}
        if MakeLowReshNative:
             SpacesDict['Native{}k_fs_LR'.format(LowResMesh)] = {
                 'Folder': os.path.join(HCP_DATA, Subject, 'T1w', 'fsaverage_LR{}'.format(LowResMesh)),
                 'ROI' : 'atlasroi',
                 'meshname': 'fsaverage_LR{}'.format(LowResMesh)),
                 'tmpdir': os.path.join(tmpdir, '{}k_fs_LR'.format(LowResMesh)),
                 'T1wImage': os.path.join(HCP_DATA, Subject, 'T1w', 'T1w.nii.gz'),
                 'DenseMapsFolder': os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'fsaverage_LR{}'.format(LowResMesh))}
    return(SpacesDict)

def spec_file(meshDict):
    '''return the formated spec_filename for this mesh'''
    global Subject
    specfile = os.path.join(meshDict['Folder']),
        "{}.{}.wb.spec".format(Subject, meshDict['meshname'])
    return(specfile)

def metric_file(mapname, Hemisphere, meshDict):
    '''return the formated file path for a metric (surface data) file for this mesh'''
    global Subject
    metric_file = os.path.join(meshDict['tmpdir']),
        "{}.{}.{}.{}.shape.gii".format(Subject, Hemisphere, mapname, meshDict['meshname'])

def surf_file(surface, Hemisphere, meshDict):
    '''return the formated file path to a surface file '''
    global Subject
    surface_file = os.path.join(meshDict['Folder']),
        '{}.{}.{}.{}.surf.gii'.format(Subject, Hemisphere, surface, meshDict['meshname'])

def label_file(labelname, Hemisphere, meshDict):
    '''return the formated file path to a label (surface data) file for this mesh'''
    global Subject
    label_file = os.path.join(meshDick['tmpdir']),
        '{}.{}.{}.{}.label.gii'.format(Subject, Hemisphere, labelname, meshDict['meshname'])

def create_dscalar(meshDict, dscalarDict):
    '''
    create the dense scalars that combine the two surfaces
    set the meta-data and add them to the spec_file
    They read the important options from two dictionaries
        meshDict   Contains settings for this Mesh
        dscalarDict  Contains settings for this type of dscalar (i.e. palette settings)
    '''
    global Subject
    dscalar_file = os.path.join(meshDict['Folder'],
        '{}.{}.{}.dscalar.nii'.format(Subject,dscalarDict['mapname'], meshDict['meshname']))
    left_metric = metric_file(dscalarDict['mapname'],'L',meshDict)
    right_metric = metric_file(dscalarDict['mapname'], 'R', meshDict)
    ## combine left and right metrics into a dscalar file
    if dscalarDict['mask_medialwall']:
        run(['wb_command', '-cifti-create-dense-scalar', dscalar_file,
            '-left-metric', left_metric,
            '-roi-left', metric_file(meshDict['ROI'], 'L', meshDict),
            '-right-metric', right_metric,
            '-roi-right', metric_file(meshDict['ROI'], 'R', meshDict)])
    else
        run(['wb_command', '-cifti-create-dense-scalar', dscalar_file,
                '-left-metric', left_metric, '-right-metric', right_metric])
    ## set the dscalar file metadata
    run(['wb_command', '-set-map-names', dscalar_file,
        '-map', '1', "{}{}".format(Subject, dscalarDict['map_posfix'])])
    run(['wb_command', '-cifti-palette', dscalar_file,
        dscalarDict['palette_mode'], dscalar_file, dscalarDict['palette_options'])

def create_dlabel(meshDict, labelname):
    '''
    create the dense labels that combine the two surfaces
    set the meta-data and add them to the spec_file
    They read the important options for the mesh from the meshDict
        meshDict   Contains settings for this Mesh
        labelname  Contains the name of the label to combine
    '''
    global Subject
    dlabel_file = os.path.join(meshDict['Folder'],
        '{}.{}.{}.dlabel.nii'.format(Subject,labelname, meshDict['meshname']))
    left_label = label_file(labelname,'L',meshDict)
    right_label = label_file(labelname, 'R', meshDict)
    ## combine left and right metrics into a dscalar file
    run(['wb_command', '-cifti-create-label', dlabel_file,
        '-left-label', left_label,
        '-roi-left', metric_file(meshDict['ROI'], 'L', meshDict),
        '-right-label', right_label,
        '-roi-right', metric_file(meshDict['ROI'], 'R', meshDict)])
    ## set the dscalar file metadata
    run(['wb_command', '-set-map-names', dlabel_file,
        '-map', '1', "{}_{}".format(Subject, labelname)])

def add_denseMaps_to_specfile(meshDict, dscalarsDict = dscalarsDict):
    '''add all the dlabels and the dscalars to the spec file'''
    if 'DenseMapsFolder' in meshDict.keys():
        mapsFolder = meshDict['DenseMapsFolder']
    else:
        mapsFolder = meshDickt['Folder']
    for dscalar in dscalarsDict.keys():
        run(['wb_command', '-add-to-spec-file', spec_file(meshDict), 'INVALID',
            os.path.join(mapsFolder,
                '{}.{}.{}.dscalar.nii'.format(Subject,dscalar, meshDict['meshname']))])
    for labelname in ['aparc', 'aparc.a2009s', 'BA']:
        run(['wb_command', '-add-to-spec-file', spec_file(meshDict), 'INVALID',
            os.path.join(mapsFolder,
                '{}.{}.{}.dlabel.nii'.format(Subject,labelname, meshDict['meshname']))])


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


def write_cras_file(FreeSurferFolder, cras_mat):
    '''read info about the surface affine matrix from freesurfer output and write it to a tmpfile'''
    mri_info = getstdout(['mri_info',os.path.join(FreeSurferFolder, 'mri','brain.finalsurfs.mgz')])
    for line in mri_info.split(os.linesep):
        if 'c_r' in line:
            bitscr = line.split('=')[4]
            MatrixX = bitscr.replace(' ','')
        elif 'c_a' in line:
            bitsca = line.split('=')[4]
            MatrixY = bitsca.replace(' ','')
        elif 'c_s' in line:
            bitscs = line.split('=')[4]
            MatrixZ = bitscs.replace(' ','')
    with open(cras_mat, 'w') as cfile:
        cfile.write('1 0 0 {}{}'.format(MatrixX, os.linesep))
        cfile.write('0 1 0 {}{}'.format(MatrixY, os.linesep))
        cfile.write('0 0 1 {}{}'.format(MatrixZ, os.linesep))
        cfile.write('0 0 0 1{}'.format(os.linesep))


def calc_ArealDistortion_gii(sphere_pre, sphere_reg, AD_gii_out, map_prefix, map_posfix):
    ''' calculate Areal Distortion Map (gifti) after registraion
        Arguments:
            sphere_pre    Path to the pre registration sphere (gifti)
            sphere_reg    Path to the post registration sphere (gifti)
            AD_gii_out    Path to the Area Distortion gifti output
            map_prefix    Prefix added to the map-name meta-data
            map_postfix   Posfix added to the map-name meta-data
    '''
    ## set temp file paths
    va_tmpdir = tempfile.mkdtemp()
    sphere_pre_va = os.path.join(va_tmpdir, 'sphere_pre_va.shape.gii')
    sphere_reg_va = os.path.join(va_tmpdir, 'sphere_reg_va.shape.gii')
    ## calculate surface vertex areas from pre and post files
    run(['wb_command', '-surface-vertex-areas', sphere_pre, sphere_pre_va])
    run(['wb_command', '-surface-vertex-areas', sphere_reg, sphere_reg_va])
    ## caluculate Areal Distortion using the vertex areas
    run(['wb_command', '-metric-math',
        '(ln(spherereg / sphere) / ln(2))',
        AD_gii_out,
        '-var', 'sphere', sphere_pre_va,
        '-var', 'spherereg', sphere_reg_va])
    ## set meta-data for the ArealDistotion files
    run(['wb_command', '-set-map-names', AD_gii_out,
        '-map', '1', '{}_Areal_Distortion_{}'.format(map_prefix. map_postfix)])
    run(['wb_command', '-metric-palette', AD_gii_out, 'MODE_AUTO_SCALE',
        '-palette-name', 'ROY-BIG-BL',
        '-thresholding', 'THRESHOLD_TYPE_NORMAL', 'THRESHOLD_TEST_SHOW_OUTSIDE', '-1', '1'])
    shutil.rmtree(va_tmpdir)

def resample_surfs_and_add_to_spec(surface, currentMeshSettings, destMeshSettings,
        current_sphere = 'sphere', dest_sphere = 'sphere'):
    '''
    resample surface files and add them to the resampled spaces spec file
    uses wb_command -surface-resample with BARYCENTRIC method
    Arguments:
        surface              Name of surface to resample (i.e 'pial', 'white')
        currentMeshSettings  Dictionary of Settings for current mesh
        destMeshSettings     Dictionary of Settings for destination (output) mesh
    '''
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        surf_in = surf_file(surface, Hemisphere, currentMeshSettings)
        surf_out = surf_file(surface, Hemisphere, currentMeshSettings)
        current_sphere_surf = surf_file(current_sphere, Hemisphere, currentMeshSettings)
        dest_sphere_surf = surf_file(dest_sphere, Hemisphere, currentMeshSettings)
        run(['wb_command', '-surface-resample', surf_in,
            current_sphere_surf, dest_sphere_surf, 'BARYCENTRIC', surf_out])
        run(['wb_command', '-add-to-spec-file',
            spec_file(destMeshSettings), Structure, surf_out])

def  make_midthickness_surfaces(meshDict):
     '''
     use the white and pial surfaces from the same mesh to create a midthickness file
     set the midthickness surface metadata and add it to the spec_file
     '''
     for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        #Create midthickness by averaging white and pial surfaces
        mid_surf = surf_file('midthickness', Hemisphere, meshDict)
        run(['wb_command', '-surface-average', mid_surf,
          '-surf', surf_file('white', Hemisphere, meshDict),
          '-surf', surf_file('pial', Hemisphere, meshDict)])
        run(['wb_command', '-set-structure', mid_surf, Structure,
          '-surface-type', 'ANATOMICAL', '-surface-secondary-type', 'MIDTHICKNESS'])
        run(['wb_command', '-add-to-spec-file', spec_file(meshDict), Structure, mid_surf])

def make_inflated_surfaces(meshDict, iterations_scale = 2.5):
    '''
    make inflated and very_inflated surfaces from the mid surface of the specified mesh
    adds the surfaces to the spec_file
    '''
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        infl_surf = surf_file('inflated', Hemisphere, meshDict)
        vinfl_surf = surf_file('very_inflated', Hemisphere, meshDict)
        run(['wb_command', '-surface-generate-inflated',
          surf_file('midthickness', Hemisphere, meshDict)
          infl_surf, vinfl_surf, '-iterations-scale', str(iterations_scale)])
        run(['wb_command', '-add-to-spec-file', spec_file(meshDict), Structure, infl_surf])
        run(['wb_command', '-add-to-spec-file', spec_file(meshDict), Structure, vinfl_surf])

def resample_and_mask_metric(MapName, Hemisphere, currentMeshSettings, destMeshSettings,
        current_sphere = 'sphere', dest_sphere = 'sphere', dscalarsDict = dscalarsDict):
    '''
    rasample the metric files to a different mesh than mask out the medial wall
    uses wb_command -metric-resample with 'ADAP_BARY_AREA' method
    To remove masking steps the roi can be set to None
    Arguments:
        MapName              Name of metric to resample (i.e 'sulc', 'thickness')
        currentMeshSettings  Dictionary of Settings for current mesh
        destMeshSettings     Dictionary of Settings for destination (output) mesh
    '''
    metric_in = metric_file(MapName, Hemisphere, currentMeshSettings)
    metric_out = metric_file(MapName, Hemisphere, destMeshSettings)

    current_midthickness = surf_file('midthickness', Hemisphere, currentMeshSettings)
    new_midthickness = surf_file('midthickness', Hemisphere, destMeshSettings)

    current_sphere_surf = surf_file(current_sphere, Hemisphere, currentMeshSettings)
    dest_spherereg_surf = surf_file(dest_sphere, Hemisphere, currentMeshSettings)

    if descalarsDict[MapName]['mask_medialwall']:
        run(['wb_command', '-metric-resample', metric_in,
            current_sphere_surf, dest_sphere_surf, 'ADAP_BARY_AREA', metric_out,
            '-area-surfs', current_midthickness, new_midthickness,
            '-current-roi', metric_file(currentMeshSettings['ROI'], 'L', currentMeshSettings)])
        run(['wb_command', '-metric-mask', metric_out,
            metric_file(destMeshSettings['ROI'], 'L', destMeshSettings), metric_out])
    else:
        run(['wb_command', '-metric-resample',
            metric_in, current_sphere_surf, dest_sphere_surf, 'ADAP_BARY_AREA', metric_out,
            '-area-surfs', current_midthickness, new_midthickness])

def convert_annot(labelname, FreesurferFolder, destMeshSettings):
    ''' convert a freesurfer annot to a gifti label and set metadata'''
    global Subject
    for Hemisphere, hemisphere, Structure in [('L','l','CORTEX_LEFT'), ('R','r', 'CORTEX_RIGHT')]:
        fs_annot = os.path.join(FreeSurferFolder,
            'label','{}h.{}.annot'.format(hemisphere))
        if os.file.exists(fs_annot):
          label_gii = label_file(labelname, Hemisphere, destMeshSettings)
          run(['mris_convert', '--annot', fs_annot,
            os.path.join(FreeSurferFolder,'surf','{}h.white'.format(hemisphere)),
            label_gii])
          run(['wb_command', '-set-structure', label_gii, 'Structure'])
          run(['wb_command', '-set-map-names', label_gii,
            '-map', '1', '{}_{}_{}'.format(Subject,Hemisphere,labelname)])
          run(['wb_command', '-gifti-label-add-prefix',
            label_gii, '{}_'.format(Hemisphere), label_gii])

def resample_label(labelname, Hemisphere, currentMeshSettings, destMeshSettings,
        current_sphere = 'sphere', dest_sphere = 'sphere'):
    '''
    resample label files if they exist
    uses wb_command -label-resample with BARYCENTRIC method
    Arguments:
        labelname            Name of label to resample (i.e 'aparc')
        Hemisphere           Hemisphere of label to resample ('L' or 'R')
        currentMeshSettings  Dictionary of Settings for current mesh
        destMeshSettings     Dictionary of Settings for destination (output) mesh
        current_sphere       The name (default 'sphere') of the current registration surface
        new_sphere           The name (default 'sphere') of the dest registration surface
    '''
  label_in = label_file(labelname, Hemisphere, currentMeshSettings)
  if  os.file.exists(label_in):
      run(['wb_command', '-label-resample', label_in,
        surf_file(current_sphere, Hemisphere, currentMeshSettings),
        surf_file(dest_sphere, Hemisphere, destMeshSettings), 'BARYCENTRIC',
        label_file(labelname, Hemisphere, destMeshSettings), '-largest'])

def convert_freesurfer_mgz(ImageName,  T1w_nii, FreesurferFolder, OutDir):
    ''' convert image from freesurfer(mgz) to nifti format, and
        realigned to the specified T1wImage, and imports labels
        Arguments:
            ImageName    Name of Image to Convert
            T1w_nii     Path to T1wImage to with desired output orientation
            FreesurferFolder  Path the to subjects freesurfer output
            OutDir       Output Directory for converted Image
    '''
    freesurfer_mgz = os.path.join(FreeSurferFolder,'mri','{}.mgz'.format(ImageName))
      if os.path.isfile(freesurfer_mgz):
        Image_nii = os.path.join(OutDir,'{}.nii.gz'.format(ImageName))
        run(['mri_convert', '-rt', 'nearest',
          '-rl', T1w_nii, freesurfer_mgz, Image_nii])
        run(['wb_command', '-volume-label-import', Image_nii,
          os.path.join(find_ciftify_templates(),'hcp_config','FreeSurferAllLut.txt')
          Image_nii, '-drop-unused-labels'])

def convert_freesurfer_surface(Surface, SurfaceType, FreesurferFolder,deshMeshSettings,
        SurfaceSecondaryType = None, cras_mat = None, add_to_spec = True):
    '''
    Convert freesurfer surface to gifti surface files
    Arguments:
        Surface           Surface Name
        SurfaceType       Surface type to add to the metadata
        SecondaryType     Type that will be added to gifti metadata
        FreesurferFolder  The subject freesurfer output folder
        deshMeshSettings  Dictionary of settings with naming conventions for the gifti files
        cras_mat          Path to the freesurfer affine matrix
        add_to_spec       Wether to add the gifti file the spec file (default True)
    '''
    global Subject
    for Hemisphere, hemisphere, Structure in [('L','l','CORTEX_LEFT'), ('R','r', 'CORTEX_RIGHT')]:
        surf_fs = os.path.join(FreeSurferFolder,'surf','{}h.{}'.format(hemisphere, Surface))
        surf_native = surf_file(Structure, Hemisphere, deshMeshSettings)
        ## convert the surface into the T1w/Native Folder
        run(['mris_convert',surf_fs, surf_native])
        if SurfaceSecondaryType:
            run(['wb_command', '-set-structure', surf_native, Structure,
                '-surface-type', SurfaceType, SecondaryType)
        else:
            run(['wb_command', '-set-structure', surf_native, Structure,
                '-surface-type', SurfaceType)]
        if cras_mat:
            run(['wb_command', '-surface-apply-affine', surf_native,
                    cras_mat, surf_native])]
        run(['wb_command', '-add-to-spec-file',spec_file(deshMeshSettings),Structure, surf_native])

def convert_freesurfer_maps(MapDict, FreesurferFolder, destMeshSettings):
    ''' convert a freesurfer data (thickness, curv, sulc) to a gifti metric and set metadata'''
    global Subject
    for Hemisphere, hemisphere, Structure in [('L','l','CORTEX_LEFT'), ('R','r', 'CORTEX_RIGHT')]:
        map_gii = metric_file(MapDict['mapname'], Hemisphere, destMeshSettings)
        ## convert the freesurfer files to gifti
        run(['mris_convert', '-c',
            os.path.join(FreeSurferFolder,'surf','{}h.{}'.format(hemisphere, MapDict['fsname'])),
            os.path.join(FreeSurferFolder,'surf', '{}h.white'.format(hemisphere)),
            map_native_gii])
        ## set a bunch of meta-data and multiply by -1
        run(['wb_command', '-set-structure',map_gii, Structure])
        run(['wb_command', '-metric-math', '(var * -1)',
            map_native_gii, '-var', 'var', map_gii])
        run(['wb_command', '-set-map-names', map_gii,
            '-map', '1', '{}_{}{}'.format(Subject, Hemisphere, MapDict['map_postfix'])])
        if MapDict[mapname] == 'thickness':
            '''I don't know why but there are thickness specific extra steps'''
              #Thickness set thickness at absolute value than set palette metadata
              run(['wb_command', '-metric-math', '(abs(thickness))',
                map_gii, '-var', 'thickness', map_gii])
        run(['wb_command', '-metric-palette', map_gii, MapDict['palette_mode'],
            MapDict['palette_options'])

def medialwall_rois_from_thickness_maps(meshDict):
    '''create and roi file by thresholding the thickness surfaces'''
    global Subject
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
      ## create the native ROI file using the thickness file
      native_roi =  metric_file(meshDict['ROI',Hemisphere, meshDict)
      midthickness_gii = surf_file('midthickness',Hemisphere, meshDict)
      run(['wb_command', '-metric-math', "(thickness > 0)", native_roi,
        '-var', 'thickness', metric_file('thickness', Hemisphere, meshDict)])
      run(['wb_command', '-metric-fill-holes',
        midthickness_gii, native_roi, native_roi])
      run(['wb_command', '-metric-remove-islands',
        midthickness_gii, native_roi, native_roi])
      run(['wb_command', '-set-map-names', native_roi,
        '-map', '1', '{}_{}_ROI'.format(Subject, Hemisphere)])

def run_fs_reg_LR(HighResMesh, RegSphereOut):
    ''' Copy all the template files and do the FS left to right registration'''
    global Subject
    SurfaceAtlasDIR = os.path.join(find_ciftify_templates(),'standard_mesh_atlases')
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
      #Concatinate FS registration to FS --> FS_LR registration
      FSRegSphere = surf_file('sphere.reg.reg_LR', Hemisphere, MeshesDict['AtlasSpaceNative'])
      run(['wb_command', '-surface-sphere-project-unproject',
        surf_file('sphere', Hemisphere, MeshesDict['AtlasSpaceNative'])
        os.path.join(SurfaceAtlasDIR, 'fs_{}'.format(Hemisphere),
            'fsaverage.{0}.sphere.{1}k_fs_{0}.surf.gii'.format(Hemisphere, HighResMesh)),
        os.path.join(SurfaceAtlasDIR, 'fs_{}'.format(Hemisphere),
            'fs_{0}-to-fs_LR_fsaverage.{0}_LR.spherical_std.{1}k_fs_{0}.surf.gii'.format(Hemisphere, HighResMesh)),
        FSRegSphere])
      #Make FreeSurfer Registration Areal Distortion Maps
      calc_ArealDistortion_gii(
        surf_file('sphere', Hemisphere, MeshesDict['AtlasSpaceNative']),
        FSRegSphere,
        metric_file('ArealDistortion_FS', Hemisphere, MeshesDict['AtlasSpaceFolder'])
        '{}_{}'.format(Subject, Hemisphere), 'FS')

def copy_colin_flat_and_add_to_spec(meshSettings):
    ''' copy the colin flat atlas out of the templates folder and add it to the spec file'''
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        colin_src = os.path.join(find_ciftify_templates(),
            'standard_mesh_atlases',
            'colin.cerebral.{}.flat.{}.surf.gii'.format(Hemisphere, meshSettings['meshname']))
        if os.file.exists(colin_src):
            colin_dest = surf_file(flat, Hemisphere, meshSettings)
            run(['cp', colin_src colin_dest])
            run(['wb_command', '-add-to-spec-file', meshSettings, Structure, colin_dest])

def copy_sphere_mesh_from_template(meshSettings):
    '''Copy the sphere of specific mesh settings out of the template and into subjects folder'''
    meshname = meshSettings['meshname']
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        if meshname == '164k_fs_LR':
            sphere_src = os.path.join(find_ciftify_templates(),
                'standard_mesh_atlases',
                'fsaverage.{}_LR.spherical_std.{}.surf.gii'.format(Hemisphere, meshname))
        else :
            sphere_src = os.path.join(find_ciftify_templates(),
                'standard_mesh_atlases','{}.sphere.{}.surf.gii'.format(Hemisphere, meshname))
        sphere_dest = surf_file('sphere', Hemisphere, meshSettings)
        run(['cp', sphere_src, sphere_dest])
        run(['wb_command', '-add-to-spec-file', spec_file(meshSettings), Structure, sphere_dest])

def copy_atlasroi_from_template(meshSettings):
    '''Copy the atlasroi (roi of medialwall) for a specific mesh out of templates'''
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        roi_src = os.path.join(find_ciftify_templates(),
            'standard_mesh_atlases',
            '{}.atlasroi.{}.shape.gii'.format(Hemisphere, meshSettings['meshname']))
        if os.file.exists(sphere_src):
        ## Copying sphere surface from templates file to subject folder
        roi_dest = metric_file('atlasroi', Hemisphere, meshSettings)
        run(['cp', roi_src, roi_dest])

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

def main(arguments, tmpdir):

    Subject = arguments["<Subject>"]
    SUBJECTS_DIR = arguments["--fs-subjects-dir"]
    HCP_DATA = arguments["--hcp-data-dir"]
    MakeLowReshNative = arguments["--resample-LowRestoNative"]
    VERBOSE         = arguments['--verbose']
    DEBUG           = arguments['--debug']
    DRYRUN          = arguments['--dry-run']

    if HCP_DATA == None: HCPData = ciftify.config.find_hcp_data()
    if SUBJECTS_DIR == None: SUBJECTS_DIR = ciftify.config.find_freesurfer_data()

    ## write a bunch of info about the environment to the logs
    log_build_environment()

    logger.info('Arguments:')

    logger.info("Platform Information Follows: ")
    #add my config info
    log_build_environment()

    logger.info("Aruguments")
    logger.info('freesurfer SUBJECTS_DIR: {}'.format(SUBJECTS_DIR))
    logger.info('HCP_DATA directory: {}'.format(HCP_DATA))
    logger.info('Subject: {}'.format(Subject))

    logger.debug("Defining Settings")
    HighResMesh = "164"
    LowResMeshes = ["32"]
    NativeFolder = "Native"
    RegName = "FS"

    ## the Meshes Dict contrain file paths and naming conventions specitic to all ouput meshes
    MeshesDict = define_SpacesDict(HCP_DATA, Subject, HighResMesh, LowResMeshes,
        tmpdir, MakeLowReshNative = False)

    ## the dscalarsDict contrains naming conventions and setting specfic to each map output
    dscalarsDict = define_dscalarsDict(RegName)

    logger.info("START: FS2CaretConvertRegisterNonlinear")

    FreeSurferLabels = os.path.join(find_ciftify_templates(),'hcp_config','FreeSurferAllLut.txt')
    GrayordinatesSpaceDIR = os.path.join(find_ciftify_templates(),'91282_Greyordinates')
    SubcorticalGrayLabels = os.path.join(find_ciftify_templates(),'FreeSurferSubcorticalLabelTableLut.txt')
    SurfaceAtlasDIR = os.path.join(find_ciftify_templates(),'standard_mesh_atlases')



    FreeSurferFolder= os.path.join(SUBJECTS_DIR,Subject)
    GrayordinatesResolutions = "2"
    HighResMesh = "164"
    LowResMeshes = ["32"]
    NativeFolder = "Native"
    RegName = "FS"

    T1wImageBrainMask="brainmask_fs"
    T1wImage="T1w" #if not running
    T1wImageBrain="${T1wImage}_brain"

    #Make some folders for this and later scripts
    ### Naming conventions
    T1wFolder = os.path.join(HCP_DATA, Subject, 'T1w')
    AtlasSpaceFolder = os.path.join(HCP_DATA, Subject, 'MNINonLinear')
    for k, mDict in MeshesDict.items():
        run(['mkdir','p', mDict['Folder']])
        run(['mkdir','p', mDict['tmpdir']])
    run(['mkdir','p',os.path.join(AtlasSpaceFolder,'xfms')])
    run(['mkdir','p',os.path.join(AtlasSpaceFolder,'ROIs')])
    run(['mkdir','p',os.path.join(AtlasSpaceFolder,'Results')])
    run(['mkdir','p',os.path.join(T1wFolder,'fsaverage')])
    run(['mkdir','p',os.path.join(AtlasSpaceFolder,'fsaverage')])

    ## the ouput files
    ###Templates and settings
    BrainSize = "150" #BrainSize in mm, 150 for humans
    FNIRTConfig = os.path.join(ciftify.config.find_fsl(),'etc','flirtsch','T1_2_MNI152_2mm.cnf') #FNIRT 2mm T1w Config
    T1wTemplate2mmBrain = os.path.join(ciftify.config.find_fsl(),'data', 'standard', 'MNI152_T1_2mm_brain.nii.gz') #Hires brain extracted MNI template
    T1wTemplate2mm = os.path.join(ciftify.config.find_fsl(),'data', 'standard','MNI152_T1_2mm.nii.gz') #Lowres T1w MNI template
    T1wTemplate2mmMask = os.path.join(ciftify.config.find_fsl(),'data', 'standard', 'MNI152_T1_2mm_brain_mask_dil.nii.gz') #Lowres MNI brain mask template

    T1w_nii = os.path.join(T1wFolder,'{}.nii.gz'.format(T1wImage))
    T1wImageBrainMask = os.path.join(T1wFolder,"brainmask_fs.nii.gz")
    T1wBrain_nii = os.path.join(T1wFolder,'{}_brain.nii.gz'.format(T1wImage))
    AtlasTransform_Linear = os.path.join(AtlasSpaceFolder,'xfms','T1w2StandardLinear.mat')
    AtlasTransform_NonLinear = os.path.join(AtlasSpaceFolder,'T1w2Standard_warp_noaffine.nii.gz')
    InverseAtlasTransform_NonLinear = os.path.join(AtlasSpaceFolder,'xfms', 'Standard2T1w_warp_noaffine.nii.gz')
    T1wImage_MNI = os.path.join(AtlasSpaceFolder,'{}.nii.gz'.format(T1wImage))

    ###### convert the mgz T1w and put in T1w folder
    run(['mri_convert', os.path.join(FreeSurferFolder,'mri','T1.mgz'), T1w_nii])
    run(['fslreorient2std', T1w_nii, T1w_nii])

    #Convert FreeSurfer Volumes and import the label metadata
    for Image in ['wmparc', 'aparc.a2009s+aseg', 'aparc+aseg']:
      convert_freesurfer_mgz(Image,  T1w_nii, FreesurferFolder, T1wFolder)

    ## Create FreeSurfer Brain Mask skipping 1mm version...
    run(['fslmaths',
      os.path.join(T1wFolder,'wmparc.nii.gz'),
      '-bin', '-dilD', '-dilD', '-dilD', '-ero', '-ero',
      T1wImageBrainMask])
    run(['wb_command', '-volume-fill-holes', T1wImageBrainMask, T1wImageBrainMask])
    run(['fslmaths', T1wImageBrainMask, '-bin', T1wImageBrainMask])
    ## apply brain mask to the T1wImage
    run(['fslmaths', T1w_nii, '-mul', T1wImageBrainMask, T1wBrain_nii])

    ##### Linear then non-linear registration to MNI
    T1w2StandardLinearImage = os.path.join(tmpdir, 'T1w2StandardLinearImage.nii.gz')
    run(['flirt', '-interp', 'spline', '-dof', '12',
      '-in', T1wBrain_nii,
      '-ref', T1wTemplate2mmBrain,
      '-omat', AtlasTransform_Linear,
      '-o', T1w2StandardLinearImage])

    ### calculate the just the warp for the surface transform - need it because sometimes the brain is outside the bounding box of warfield
    run(['fnirt',
       '--in={}'.format(T1w2StandardLinearImage),
       '--ref={}'.format(T1wTemplate2mm),
       '--refmask={}'.format(T1wTemplate2mmMask),
       '--fout={}'.format(AtlasTransform_NonLinear),
       '--logout={}'.format(os.path.join(AtlasSpaceFolder,'xfms', 'NonlinearReg_fromlinear.txt')),
       '--config={}'.format(FNIRTConfig)])

    ## also inverse the non-prelinear warp - we will need it for the surface transforms
    run(['invwarp',
      '-w', AtlasTransform_NonLinear,
      '-o', InverseAtlasTransform_NonLinear,
      '-r', T1wTemplate2mm])

    ##T1w set of warped outputs (brain/whole-head + restored/orig)
    run(['applywarp', '--rel', '--interp=trilinear',
      '-i', T1wImage_nii,
      '-r', T1wTemplate2mm,
      '-w', AtlasTransform_NonLinear,
      '--premat={}'.format(AtlasTransform_Linear),
      '-o', T1wImage_MNI])

    #Convert FreeSurfer Segmentations to MNI space
    for Image in ['wmparc', 'aparc.a2009s+aseg', 'aparc+aseg', 'brainmask_fs']:
      if os.path.isfile(os.path.join(T1wFolder,'{}.nii.gz'.format(Image))):
        Image_MNI = os.path.join(AtlasSpaceFolder,'{}.nii.gz'.format(Image))
        run(['applywarp', '--rel', '--interp=nn',
        '-i', os.path.join(T1wFolder,'{}.nii.gz'.format(Image)),
        '-r', T1wImage_MNI, '-w', AtlasTransform_NonLinear,
        '--premat={}'.format(AtlasTransform_Linear),
        '-o', Image_MNI])
        run(['wb_command', '-volume-label-import',
          Image_MNI, FreeSurferLabels, Image_MNI, '-drop-unused-labels'])

    #Create Spec Files with the T1w files including
    for k, mDict in MeshesDict.items():
         run(['wb_command', '-add-to-spec-file', spec_file(mDict), 'INVALID', mDict['T1wImage']])

    # Import Subcortical ROIs and resample to the Grayordinate Resolution
    for GrayordinatesResolution in GrayordinatesResolutions:
      ## The outputs of this sections
      Atlas_ROIs = os.path.join(AtlasSpaceFolder,'ROIs', 'Atlas_ROIs.{}.nii.gz'.format(GrayordinatesResolution))
      wmparc_ROIs = os.path.join(tmpdir, 'wmparc.{}.nii.gz'.format(GrayordinatesResolution))
      wmparcAtlas_ROIs = os.path.join(tmpdir, 'Atlas_wmparc.{}.nii.gz'.format(GrayordinatesResolution))
      ROIs_nii = os.path.join(AtlasSpaceFolder, 'ROIs', 'ROIs.{}.nii.gz'.format(GrayordinatesResolution))
      T1wImage_res = os.path.join(AtlasSpaceFolder, 'T1w.{}.nii.gz'.format(GrayordinatesResolution))
      ## the analysis steps
      run(['cp',
        os.path.join(GrayordinatesSpaceDIR, 'Atlas_ROIs.{}.nii.gz'.format(GrayordinatesResolution)),
        Atlas_ROIs])
      run(['applywarp', '--interp=nn',
        '-i', os.path.join(AtlasSpaceFolder, 'wmparc.nii.gz'),
        '-r', Atlas_ROIs, '-o', wmparc_ROIs])
      run(['wb_command', '-volume-label-import',
        wmparc_ROIs, FreeSurferLabels, wmparc_ROIs, '-drop-unused-labels'])
      run(['applywarp', '--interp=nn',
        '-i', os.path.join(SurfaceAtlasDIR, 'Avgwmparc.nii.gz'),
        '-r', Atlas_ROIs, '-o', wmparcAtlas_ROIs])
      run(['wb_command', '-volume-label-import',
        wmparcAtlas_ROIs, FreeSurferLabels,  wmparcAtlas_ROIs, '-drop-unused-labels'])
      run(['wb_command', '-volume-label-import',
        wmparc_ROIs, SubcorticalGrayLabels, ROIs_nii,'-discard-others'])
      run(['applywarp', '--interp=spline',
        '-i', T1wImage_MNI, '-r', Atlas_ROIs,
        '-o', T1wImage_res])

    #Find c_ras offset between FreeSurfer surface and volume and generate matrix to transform surfaces
    write_cras_file(FreeSurferFolder, cras_mat)

    for Surface, SecondaryType in [('white','GRAY_WHITE'), ('pial', 'PIAL')]:
        convert_freesurfer_surface(Surface, 'ANATOMICAL', FreesurferFolder,
            MeshesDict['T1wNative'], SurfaceSecondaryType = SecondaryType,
            cras_mat = cras_mat, add_to_spec = True)

    for Hemisphere, hemisphere, Structure in [('L','l','CORTEX_LEFT'), ('R','r', 'CORTEX_RIGHT')]:
      #native Mesh Processing
      #Convert and volumetrically register white and pial surfaces makign linear and nonlinear copies, add each to the appropriate spec file
      for Surface in ['white', 'pial'] :
        surf_native = surf_file(Surface, Hemisphere, MeshesDict['T1wNative'])
        surf_mni = surf_file(Surface, Hemisphere, MeshesDict['AtlasSpaceNative'])
        ## MNI transform the surfaces into the MNINonLinear/Native Folder
        run(['wb_command', '-surface-apply-affine',
          surf_native, AtlasTransform_Linear, surf_mni,
          '-flirt', T1w_nii, T1wTemplate2mm])
        run(['wb_command', '-surface-apply-warpfield',
          surf_mni, InverseAtlasTransform_NonLinear, surf_mni,
          '-fnirt', AtlasTransform_NonLinear ])
        run(['wb_command', '-add-to-spec-file', spec_file(MeshesDict['AtlasSpaceNative']), Structure, surf_mni ])

    #Convert original and registered spherical surfaces and add them to the nonlinear spec file
    convert_freesurfer_surface(Surface = 'sphere', SurfaceType = 'SPHERICAL',
          FreesurferFolder = FreesurferFolder, deshMeshSettings = MeshesDict['AtlasSpaceNative'],
          SurfaceSecondaryType = None, cras_mat = None, add_to_spec = True)
    convert_freesurfer_surface(Surface = 'sphere.reg', SurfaceType = 'SPHERICAL',
        FreesurferFolder = FreesurferFolder, deshMeshSettings = MeshesDict['AtlasSpaceNative'],
        SurfaceSecondaryType = None, cras_mat = None, add_to_spec = False)

    for mesh in ['T1wNative', 'AtlasSpaceNative']:
        ## build midthickness out the white and pial
        make_midthickness_surfaces(MeshesDict[mesh])
        # make inflated surfaces from midthickness
        make_inflated_surfaces(MeshesDict[mesh])

    # Convert freesurfer annotation to gift labels and set meta-data
    for Map in ['aparc', 'aparc.a2009s', 'BA']:
      convert_annot(Map, FreesurferFolder, MeshesDict['AtlasSpaceNative'])

    #Add more files to the spec file and convert other FreeSurfer surface data to metric/GIFTI including sulc, curv, and thickness.
    for Map, MapDict in dscalarsDict.iteritems():
        if 'fsname' in MapDict[Map].keys():
            convert_freesurfer_maps(MapDict, FreesurferFolder, MeshesDict['AtlasSpaceNative'])

    medialwall_rois_from_thickness_maps(MeshesDict['AtlasSpaceNative'])
      #End main native mesh processing

    ## use data from the template files along with the freesurfer sphere to create RegSphere
    FSRegSphere = 'sphere.reg.reg_LR'
    run_fs_reg_LR(HighResMesh, FSRegSphere)

    if RegName == 'MSMSulc':
        run_MSMSulc_registration()

    else :
     RegSphere = FSRegSphere

    copy_atlasroi_from_template(MeshesDict['HighResMesh'])
    copy_sphere_mesh_from_template(MeshesDict['HighResMesh'])
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
          #Ensure no zeros in atlas medial wall ROI
          atlasroi_native_gii = metric_file('atlasroi', Hemisphere, MeshesDict['AtlasSpaceNative'])
          native_roi = metric_file('roi', Hemisphere, MeshesDict['AtlasSpaceFolder'])
          run(['wb_command', '-metric-resample',
            os.path.join(SurfaceAtlasDIR,
                '{}.atlasroi.{}k_fs_LR.shape.gii'.format(Hemisphere, HighResMesh)),
            surf_file('sphere', Hemisphere, MeshesDict['HighResMesh']),
            surf_file(RegSphere, Hemisphere, MeshesDict['AtlasSpaceFolder'])
            'BARYCENTRIC', atlasroi_native_gii,'-largest'])
          run(['wb_command', '-metric-math', '(atlas + individual) > 0)',
            native_roi,
            '-var', 'atlas', atlasroi_native_gii,
            '-var', 'individual', native_roi)

    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        for mapname in ['thickness','curvature']:
          ## dilate the thickness and curvature file by 10mm
          metric_map = metric_file(mapname,Hemisphere, MeshesDict['AtlasSpaceNative'])
          run(['wb_command', '-metric-dilate', metric_map,
            surf_file('midthickness',Hemisphere, MeshesDict['AtlasSpaceNative']),
            '10', metric_map,'-nearest'])
          ## apply the medial wall roi to the thickness and curvature files
          run(['wb_command', '-metric-mask', metric_map,
            surf_file(MeshesDict['AtlasSpaceNative']['ROI'], Hemisphere, MeshesDict['AtlasSpaceNative']),
            metric_map])

    ## add all the dscalar and dlable files to the spec file
    add_denseMaps_to_specfile(MeshesDict['T1wNative'])
    add_denseMaps_to_specfile(MeshesDict['AtlasSpaceNative'])

    #Populate Highres fs_LR spec file.
    logger.info(section_header('Resampling data from Native to {}'.format(MeshesDict['HighResMesh']['meshname'])))


    copy_colin_flat_and_add_to_spec(MeshesDict['HighResMesh'])
    # Deform surfaces and other data according to native to folding-based registration selected above.
    for Surface in ['white', 'midthickness', 'pial']:
        resample_surfs_and_add_to_spec(Surface,
                MeshesDict['AtlasSpaceNative'], MeshesDict['HighResMesh'],
                current_sphere = RegSphere)
        ## create the inflated HighRes surfaces
        make_inflated_surfaces(MeshesDict['HighResMesh']))

    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
      ## resample the metric data to the new mesh
      for MapName in dscalarsDict.keys():
        resample_and_mask_metric(MapName, Hemisphere, MeshesDict['AtlasSpaceNative'],
            MeshesDict['HighResMesh'], current_sphere = RegSphere)
      ## resample all the label data to the new mesh
      for Map in ['aparc', 'aparc.a2009s', 'BA']:
          resample_label(Map, Hemisphere, MeshesDict['AtlasSpaceNative'],
            MeshesDict['HighResMesh'], current_sphere = RegSphere)
    ## combine L and R metrics into dscalar files
    for Map in ['aparc', 'aparc.a2009s', 'BA']:
        create_dlabel_add_to_spec(MeshesDict['HighResMesh'], Map)
    ## combine L and R labels into a dlabel file
    for MapName in dscalarsDict.keys():
        create_dscalar_add_to_spec(MeshesDict['HighResMesh'], dscalarsDict[MapName])
    add_denseMaps_to_specfile(MeshesDict['HighResMesh'])

    #Populate LowRes fs_LR spec file.
    for LowResMesh in LowResMeshes:
        logger.info(section_header('Resampling data from Native to {}k_fs_LR'.format(LowResMesh)))
        ## define the LowResMesh Settings
        destMeshSettings = MeshesDict['{}k_fs_LR'.format(LowResMesh)]
        # Set Paths for this section
        copy_atlasroi_from_template(destMeshSettings)
        copy_sphere_mesh_from_template(destMeshSettings)
        copy_colin_flat_and_add_to_spec(destMeshSettings)
        # Deform surfaces and other data according to native to folding-based registration selected above.
        for Surface in ['white', 'midthickness', 'pial']:
            resample_surfs_and_add_to_spec(Surface,
                    MeshesDict['AtlasSpaceNative'], destMeshSettings,
                    current_sphere = RegSphere)
        ## create the inflated HighRes surfaces
        make_inflated_surfaces(destMeshSettings, iterations_scale = 0.75)

        for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
          ## resample the metric data to the new mesh
          for MapName in dscalarsDict.keys():
            resample_and_mask_metric(MapName, Hemisphere, MeshesDict['AtlasSpaceNative'],
                destMeshSettings, current_sphere = RegSphere)
          ## resample all the label data to the new mesh
          for Map in ['aparc', 'aparc.a2009s', 'BA']:
              resample_label(Map, Hemisphere, MeshesDict['AtlasSpaceNative'],
                destMeshSettings, current_sphere = RegSphere)
        ## combine L and R metrics into dscalar files
        for Map in ['aparc', 'aparc.a2009s', 'BA']:
            create_dlabel_add_to_spec(destMeshSettings, Map)
        ## combine L and R labels into a dlabel file
        for MapName in dscalarsDict.keys():
            create_dscalar_add_to_spec(destMeshSettings, dscalarsDict[MapName])
        ## add all the dscalar and dlable files to the spec file
        add_denseMaps_to_specfile(destMeshSettings)

    if MakeLowReshNative:
        for LowResMesh in LowResMeshes:
            meshDict = MeshesDict['Native{}k_fs_LR'.format(LowResMesh)]
            for Surface in ['white', 'pial', 'midthickness']:
                resample_surfs_and_add_to_spec(Surface,
                        MeshesDict['AtlasSpaceNative'], meshDict,
                        current_sphere = RegSphere)
            make_inflated_surfaces(meshDict, iterations_scale = 0.75)
            ## add dsclars and dlabels from the AtlasSpaceFolder mesh
            add_denseMaps_to_specfile(meshDict)

if __name__=='__main__':

    arguments  = docopt(__doc__)

    global DRYRUN
    global Subject

    VERBOSE      = arguments['--verbose']
    DEBUG        = arguments['--debug']
    DRYRUN       = arguments['--dry-run']
    HCPData = arguments["--hcp-data-dir"]
    Subject = arguments["<Subject>"]

    if HCPData == None: HCPData = ciftify.config.find_hcp_data()
    # create a local tmpdir
    tmpdir = tempfile.mkdtemp()

    local_logpath = os.path.join(HCPData,Subject)

    if not os.path.exists(local_logpath): os.mkdir(local_logpath)

    fh = logging.FileHandler(os.path.join(local_logpath, 'fs2hcp.log'))
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

    logger.info(section_header("Starting fs2hcp"))
    logger.info('Creating tempdir:{} on host:{}'.format(tmpdir, os.uname()[1]))
    ret = main(arguments, tmpdir)
    shutil.rmtree(tmpdir)
    sys.exit(ret)
