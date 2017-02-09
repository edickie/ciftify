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

def spec_file(mesh_settings):
    '''return the formated spec_filename for this mesh'''
    global Subject
    specfile = os.path.join(mesh_settings['Folder'],
        "{}.{}.wb.spec".format(Subject, mesh_settings['meshname']))
    return(specfile)

def metric_file(mapname, Hemisphere, mesh_settings):
    '''return the formated file path for a metric (surface data) file for this mesh'''
    global Subject
    metric_gii = os.path.join(mesh_settings['tmpdir'],
        "{}.{}.{}.{}.shape.gii".format(Subject, Hemisphere, mapname, mesh_settings['meshname']))
    return(metric_gii)

def roi_file(Hemisphere, mesh_settings):
    '''
    medial wall ROIs are the only shape.gii files that aren't temp files,
    and their name is given in the mesh_settings, so they get there own function
    '''
    global Subject
    roi_gii = os.path.join(mesh_settings['Folder'],
        "{}.{}.{}.{}.shape.gii".format(Subject, Hemisphere, mesh_settings['ROI'], mesh_settings['meshname']))
    return(roi_gii)

def surf_file(surface, Hemisphere, mesh_settings):
    '''return the formated file path to a surface file '''
    global Subject
    surface_gii = os.path.join(mesh_settings['Folder'],
        '{}.{}.{}.{}.surf.gii'.format(Subject, Hemisphere, surface, mesh_settings['meshname']))
    return(surface_gii)

def label_file(labelname, Hemisphere, mesh_settings):
    '''return the formated file path to a label (surface data) file for this mesh'''
    global Subject
    label_gii = os.path.join(mesh_settings['tmpdir'],
        '{}.{}.{}.{}.label.gii'.format(Subject, Hemisphere, labelname, mesh_settings['meshname']))
    return(label_gii)

def define_dscalarsDict(RegName):
    dscalarsDict = {
        'sulc': {
            'mapname': 'sulc',
            'fsname': 'sulc',
            'map_postfix': '_Sulc',
            'palette_mode': 'MODE_AUTO_SCALE_PERCENTAGE',
            'palette_options': '-pos-percent 2 98 -palette-name Gray_Interp -disp-pos true -disp-neg true -disp-zero true',
            'mask_medialwall': False
                 },
        'curvature': {
            'mapname': 'curvature',
            'fsname': 'curv',
            'map_postfix': '_Curvature',
            'palette_mode': 'MODE_AUTO_SCALE_PERCENTAGE',
            'palette_options': '-pos-percent 2 98 -palette-name Gray_Interp -disp-pos true -disp-neg true -disp-zero true',
            'mask_medialwall': True
        },
        'thickness': {
            'mapname': 'thickness',
            'fsname': 'thickness',
            'map_postfix':'_Thickness',
            'palette_mode': 'MODE_AUTO_SCALE_PERCENTAGE',
            'palette_options': '-pos-percent 4 96 -interpolate true -palette-name videen_style -disp-pos true -disp-neg false -disp-zero false',
            'mask_medialwall': True
        },
        'ArealDistortion_FS': {
            'mapname' : 'ArealDistortion_FS',
            'map_postfix':'_ArealDistortion_FS',
            'palette_mode': 'MODE_USER_SCALE',
            'palette_options': '-pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false',
            'mask_medialwall': False
        }
    }

    if  RegName == "MSMSulc":
        dscalarDict['ArealDistortion_MSMSulc'] = {
            'mapname': 'ArealDisortion_MSMSulc',
            'map_postfix':'_ArealDistortion_MSMSulc',
            'palette_mode': 'MODE_USER_SCALE',
            'palette_options': '-pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false',
            'mask_medialwall': False
        }
    return(dscalarsDict)

def define_SpacesDict(HCP_DATA, Subject, HighResMesh, LowResMeshes,
    tmpdir, MakeLowReshNative):
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
            'Folder' : os.path.join(HCP_DATA, Subject, 'MNINonLinear'),
            'ROI': 'atlasroi',
            'meshname': '{}k_fs_LR'.format(HighResMesh),
            'tmpdir': os.path.join(tmpdir, '{}k_fs_LR'.format(HighResMesh)),
            'T1wImage': os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'T1w.nii.gz')}
    }
    for LowResMesh in LowResMeshes:
        SpacesDict['{}k_fs_LR'.format(LowResMesh)] = {
            'Folder': os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'fsaverage_LR{}k'.format(LowResMesh)),
            'ROI' : 'atlasroi',
            'meshname': '{}k_fs_LR'.format(LowResMesh),
            'tmpdir': os.path.join(tmpdir, '{}k_fs_LR'.format(LowResMesh)),
            'T1wImage': os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'T1w.nii.gz')}
        if MakeLowReshNative:
             SpacesDict['Native{}k_fs_LR'.format(LowResMesh)] = {
                 'Folder': os.path.join(HCP_DATA, Subject, 'T1w', 'fsaverage_LR{}k'.format(LowResMesh)),
                 'ROI' : 'atlasroi',
                 'meshname': '{}k_fs_LR'.format(LowResMesh),
                 'tmpdir': os.path.join(tmpdir, '{}k_fs_LR'.format(LowResMesh)),
                 'T1wImage': os.path.join(HCP_DATA, Subject, 'T1w', 'T1w.nii.gz'),
                 'DenseMapsFolder': os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'fsaverage_LR{}'.format(LowResMesh))}
    return(SpacesDict)

def define_VolRegSettings(Subject, HCP_DATA, method = 'FSL_fnirt', StandardRes = '2mm'):
    '''set up a dictionary of settings relevant to the registration to MNI space'''
    VolRegSettings = {
        'src_mesh': 'T1wNative',
        'dest_mesh': 'AtlasSpaceNative',
        'src_dir': os.path.join(HCP_DATA, Subject, 'T1w'),
        'dest_dir': os.path.join(HCP_DATA, Subject, 'MNINonLinear'),
        'xfms_dir' : os.path.join(HCP_DATA, Subject, 'MNINonLinear', 'xfms'),
        'T1wImage' : 'T1w.nii.gz',
        'T1wBrain' : 'T1w_brain.nii.gz',
        'BrainMask' : 'brainmask_fs.nii.gz',
        'AtlasTransform_Linear' : 'T1w2StandardLinear.mat',
        'AtlasTransform_NonLinear' : 'T1w2Standard_warp_noaffine.nii.gz',
        'InverseAtlasTransform_NonLinear' : 'Standard2T1w_warp_noaffine.nii.gz'
    }
    if method == 'FSL_fnirt' and StandardRes == '2mm':
        fsldir = os.path.dirname(ciftify.config.find_fsl())
        VolRegSettings['FNIRTConfig'] = os.path.join(fsldir,'etc','flirtsch','T1_2_MNI152_2mm.cnf') #FNIRT 2mm T1w Config
        VolRegSettings['standard_T1wImage'] = os.path.join(fsldir,'data', 'standard','MNI152_T1_2mm.nii.gz') #Lowres T1w MNI template
        VolRegSettings['standard_BrainMask'] = os.path.join(fsldir,'data', 'standard', 'MNI152_T1_2mm_brain_mask_dil.nii.gz') #Lowres MNI brain mask template
        VolRegSettings['standard_T1wBrain'] = os.path.join(fsldir,'data', 'standard', 'MNI152_T1_2mm_brain.nii.gz') #Hires brain extracted MNI template
    return(VolRegSettings)

def run_FSL_fnirt_registration(VolRegSettings, tmpdir):
    '''
    Run the registration from T1w to MNINonLinear space using FSL's fnirt
    registration settings and file paths are read from the VolRegSettings dictionary
    '''
    for key, val in VolRegSettings.iteritems():  # unpack the keys from the dictionary to individual variables
        exec (key + '=val')
    ##### Linear then non-linear registration to MNI
    T1w2StandardLinearImage = os.path.join(tmpdir, 'T1w2StandardLinearImage.nii.gz')
    run(['flirt', '-interp', 'spline', '-dof', '12',
      '-in', os.path.join(src_dir, T1wBrain), '-ref', standard_T1wBrain,
      '-omat', os.path.join(xfms_dir, AtlasTransform_Linear),
      '-o', T1w2StandardLinearImage])
    ### calculate the just the warp for the surface transform - need it because sometimes the brain is outside the bounding box of warfield
    run(['fnirt','--in={}'.format(T1w2StandardLinearImage),
       '--ref={}'.format(standard_T1wImage),'--refmask={}'.format(standard_BrainMask),
       '--fout={}'.format(os.path.join(xfms_dir,AtlasTransform_NonLinear)),
       '--logout={}'.format(os.path.join(xfms_dir, 'NonlinearReg_fromlinear.log')),
       '--config={}'.format(FNIRTConfig)])
    ## also inverse the non-prelinear warp - we will need it for the surface transforms
    run(['invwarp', '-w', os.path.join(xfms_dir,AtlasTransform_NonLinear),
      '-o', os.path.join(xfms_dir,InverseAtlasTransform_NonLinear), '-r', standard_T1wImage])
    ##T1w set of warped outputs (brain/whole-head + restored/orig)
    run(['applywarp', '--rel', '--interp=trilinear',
      '-i', os.path.join(src_dir, T1wImage),
      '-r', standard_T1wImage, '-w', os.path.join(xfms_dir,AtlasTransform_NonLinear),
      '--premat={}'.format(os.path.join(xfms_dir,AtlasTransform_Linear)),
      '-o', os.path.join(dest_dir, T1wImage)])

def apply_nonLinear_warp_to_nifti_rois(Image, VolRegSettings, import_labels = True):
    '''
    apply a non-linear warp to nifti Image of ROI labels
    Reads regratrion settings from the VolRegSettings dictionary
    '''
    Image_src = os.path.join(VolRegSettings['src_dir'],'{}.nii.gz'.format(Image))
    FreeSurferLabels = os.path.join(ciftify.config.find_ciftify_global(),'hcp_config','FreeSurferAllLut.txt')
    if os.path.isfile(Image_src):
        Image_dest = os.path.join(VolRegSettings['dest_dir'],'{}.nii.gz'.format(Image))
        run(['applywarp', '--rel', '--interp=nn',
        '-i', Image_src,
        '-r', os.path.join(VolRegSettings['dest_dir'], VolRegSettings['T1wImage']),
        '-w', os.path.join(VolRegSettings['xfms_dir'], VolRegSettings['AtlasTransform_NonLinear']),
        '--premat={}'.format(os.path.join(VolRegSettings['xfms_dir'], VolRegSettings['AtlasTransform_Linear'])),
        '-o', Image_dest])
        run(['wb_command', '-volume-label-import', '-logging', 'SEVERE',
          Image_dest, FreeSurferLabels, Image_dest, '-drop-unused-labels'])

def apply_nonLinear_warp_to_surface(Surface, VolRegSettings, MeshesDict):
    '''
    applys the linear and non-linear warps to a surfaces file and add
    the warped surfaces outputs to their spec file
    Arguments
        Surface          The surface to transform (i.e. 'white', 'pial')
        volregSettings   A dictionary of settings (i.e. paths, filenames) related to the warp.
        MeshesDict       A dictionary of settings (i.e. naming conventions) related to surfaces
    '''
    src_mesh_settings = MeshesDict[VolRegSettings['src_mesh']]
    dest_mesh_settings = MeshesDict[VolRegSettings['dest_mesh']]
    xfms_dir = VolRegSettings['xfms_dir']
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
      #native Mesh Processing
      #Convert and volumetrically register white and pial surfaces makign linear and nonlinear copies, add each to the appropriate spec file
        surf_src = surf_file(Surface, Hemisphere, src_mesh_settings)
        surf_dest = surf_file(Surface, Hemisphere, dest_mesh_settings)
        ## MNI transform the surfaces into the MNINonLinear/Native Folder
        run(['wb_command', '-surface-apply-affine', surf_src,
            os.path.join(xfms_dir, VolRegSettings['AtlasTransform_Linear']), surf_dest,
          '-flirt', src_mesh_settings['T1wImage'], VolRegSettings['standard_T1wImage']])
        run(['wb_command', '-surface-apply-warpfield', surf_dest,
            os.path.join(xfms_dir, VolRegSettings['InverseAtlasTransform_NonLinear']),
            surf_dest,
            '-fnirt', os.path.join(xfms_dir, VolRegSettings['AtlasTransform_NonLinear'])])
        run(['wb_command', '-add-to-spec-file', spec_file(dest_mesh_settings),
            Structure, surf_dest ])

def create_dscalar(mesh_settings, dscalarDict):
    '''
    create the dense scalars that combine the two surfaces
    set the meta-data and add them to the spec_file
    They read the important options from two dictionaries
        mesh_settings   Contains settings for this Mesh
        dscalarDict  Contains settings for this type of dscalar (i.e. palette settings)
    '''
    global Subject
    dscalar_file = os.path.join(mesh_settings['Folder'],
        '{}.{}.{}.dscalar.nii'.format(Subject,dscalarDict['mapname'], mesh_settings['meshname']))
    left_metric = metric_file(dscalarDict['mapname'],'L',mesh_settings)
    right_metric = metric_file(dscalarDict['mapname'], 'R', mesh_settings)
    ## combine left and right metrics into a dscalar file
    if dscalarDict['mask_medialwall']:
        run(['wb_command', '-cifti-create-dense-scalar', dscalar_file,
            '-left-metric', left_metric,'-roi-left', roi_file('L', mesh_settings),
            '-right-metric', right_metric,'-roi-right', roi_file('R', mesh_settings)])
    else :
        run(['wb_command', '-cifti-create-dense-scalar', dscalar_file,
                '-left-metric', left_metric, '-right-metric', right_metric])
    ## set the dscalar file metadata
    run(['wb_command', '-set-map-names', dscalar_file,
        '-map', '1', "{}{}".format(Subject, dscalarDict['map_postfix'])])
    run(['wb_command', '-cifti-palette', dscalar_file,
        dscalarDict['palette_mode'], dscalar_file, dscalarDict['palette_options']])

def create_dlabel(mesh_settings, labelname):
    '''
    create the dense labels that combine the two surfaces
    set the meta-data and add them to the spec_file
    They read the important options for the mesh from the mesh_settings
        mesh_settings   Contains settings for this Mesh
        labelname  Contains the name of the label to combine
    '''
    global Subject
    dlabel_file = os.path.join(mesh_settings['Folder'],
        '{}.{}.{}.dlabel.nii'.format(Subject,labelname, mesh_settings['meshname']))
    left_label = label_file(labelname,'L',mesh_settings)
    right_label = label_file(labelname, 'R', mesh_settings)
    ## combine left and right metrics into a dscalar file
    run(['wb_command', '-cifti-create-label', dlabel_file,
        '-left-label', left_label,'-roi-left', roi_file('L', mesh_settings),
        '-right-label', right_label,'-roi-right', roi_file('R', mesh_settings)])
    ## set the dscalar file metadata
    run(['wb_command', '-set-map-names', dlabel_file,
        '-map', '1', "{}_{}".format(Subject, labelname)])

def add_denseMaps_to_specfile(mesh_settings, dscalarsDict):
    '''add all the dlabels and the dscalars to the spec file'''
    if 'DenseMapsFolder' in mesh_settings.keys():
        mapsFolder = mesh_settings['DenseMapsFolder']
    else:
        mapsFolder = mesh_settings['Folder']
    for dscalar in dscalarsDict.keys():
        run(['wb_command', '-add-to-spec-file', os.path.realpath(spec_file(mesh_settings)), 'INVALID',
            os.path.realpath(os.path.join(mapsFolder,
                '{}.{}.{}.dscalar.nii'.format(Subject,dscalar, mesh_settings['meshname'])))])
    for labelname in ['aparc', 'aparc.a2009s', 'BA']:
        run(['wb_command', '-add-to-spec-file', os.path.realpath(spec_file(mesh_settings)), 'INVALID',
            os.path.realpath(os.path.join(mapsFolder,
                '{}.{}.{}.dlabel.nii'.format(Subject,labelname, mesh_settings['meshname'])))])

def add_T1wImages_to_spec_files(MeshesDict):
    '''add all the T1wImages to their associated spec_files'''
    for k, mDict in MeshesDict.items():
         run(['wb_command', '-add-to-spec-file', os.path.realpath(spec_file(mDict)),
            'INVALID', os.path.realpath(mDict['T1wImage'])])


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

def make_brainmask_from_wmparc(wmparc_nii, brainmask_nii):
    '''
    will create a brainmask_nii image out of the wmparc ROIs nifti converted from freesurfer
    '''
    ## Create FreeSurfer Brain Mask skipping 1mm version...
    run(['fslmaths', wmparc_nii,
        '-bin', '-dilD', '-dilD', '-dilD', '-ero', '-ero',
        brainmask_nii])
    run(['wb_command', '-volume-fill-holes', brainmask_nii, brainmask_nii])
    run(['fslmaths', brainmask_nii, '-bin', brainmask_nii])

def mask_T1wImage(T1wImage, BrainMask, T1wBrain):
    '''mask the T1w Image with the BrainMask to create the T1wBrain Image'''
    run(['fslmaths', T1wImage, '-mul', BrainMask, T1wBrain])

def calc_ArealDistortion_gii(sphere_pre, sphere_reg, AD_gii_out, map_prefix, map_postfix):
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
        '"(ln(spherereg / sphere) / ln(2))"',
        AD_gii_out,
        '-var', 'sphere', sphere_pre_va,
        '-var', 'spherereg', sphere_reg_va])
    ## set meta-data for the ArealDistotion files
    run(['wb_command', '-set-map-names', AD_gii_out,
        '-map', '1', '{}_Areal_Distortion_{}'.format(map_prefix, map_postfix)])
    run(['wb_command', '-metric-palette', AD_gii_out, 'MODE_AUTO_SCALE',
        '-palette-name', 'ROY-BIG-BL',
        '-thresholding', 'THRESHOLD_TYPE_NORMAL', 'THRESHOLD_TEST_SHOW_OUTSIDE', '-1', '1'])
    shutil.rmtree(va_tmpdir)

def resample_surfs_and_add_to_spec(surface, currentmesh_settings, dest_mesh_settings,
        current_sphere = 'sphere', dest_sphere = 'sphere'):
    '''
    resample surface files and add them to the resampled spaces spec file
    uses wb_command -surface-resample with BARYCENTRIC method
    Arguments:
        surface              Name of surface to resample (i.e 'pial', 'white')
        currentmesh_settings  Dictionary of Settings for current mesh
        dest_mesh_settings     Dictionary of Settings for destination (output) mesh
    '''
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        surf_in = surf_file(surface, Hemisphere, currentmesh_settings)
        surf_out = surf_file(surface, Hemisphere, dest_mesh_settings)
        current_sphere_surf = surf_file(current_sphere, Hemisphere, currentmesh_settings)
        dest_sphere_surf = surf_file(dest_sphere, Hemisphere, dest_mesh_settings)
        run(['wb_command', '-surface-resample', surf_in,
            current_sphere_surf, dest_sphere_surf, 'BARYCENTRIC', surf_out])
        run(['wb_command', '-add-to-spec-file',
            spec_file(dest_mesh_settings), Structure, surf_out])

def  make_midthickness_surfaces(mesh_settings):
     '''
     use the white and pial surfaces from the same mesh to create a midthickness file
     set the midthickness surface metadata and add it to the spec_file
     '''
     for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        #Create midthickness by averaging white and pial surfaces
        mid_surf = surf_file('midthickness', Hemisphere, mesh_settings)
        run(['wb_command', '-surface-average', mid_surf,
          '-surf', surf_file('white', Hemisphere, mesh_settings),
          '-surf', surf_file('pial', Hemisphere, mesh_settings)])
        run(['wb_command', '-set-structure', mid_surf, Structure,
          '-surface-type', 'ANATOMICAL', '-surface-secondary-type', 'MIDTHICKNESS'])
        run(['wb_command', '-add-to-spec-file', spec_file(mesh_settings), Structure, mid_surf])

def make_inflated_surfaces(mesh_settings, iterations_scale = 2.5):
    '''
    make inflated and very_inflated surfaces from the mid surface of the specified mesh
    adds the surfaces to the spec_file
    '''
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        infl_surf = surf_file('inflated', Hemisphere, mesh_settings)
        vinfl_surf = surf_file('very_inflated', Hemisphere, mesh_settings)
        run(['wb_command', '-surface-generate-inflated',
          surf_file('midthickness', Hemisphere, mesh_settings),
          infl_surf, vinfl_surf, '-iterations-scale', str(iterations_scale)])
        run(['wb_command', '-add-to-spec-file', spec_file(mesh_settings), Structure, infl_surf])
        run(['wb_command', '-add-to-spec-file', spec_file(mesh_settings), Structure, vinfl_surf])

def resample_and_mask_metric(dscalarDict, Hemisphere, currentmesh_settings, dest_mesh_settings,
        current_sphere = 'sphere', dest_sphere = 'sphere'):
    '''
    rasample the metric files to a different mesh than mask out the medial wall
    uses wb_command -metric-resample with 'ADAP_BARY_AREA' method
    To remove masking steps the roi can be set to None
    Arguments:
        MapName              Name of metric to resample (i.e 'sulc', 'thickness')
        currentmesh_settings  Dictionary of Settings for current mesh
        dest_mesh_settings     Dictionary of Settings for destination (output) mesh
    '''
    MapName = dscalarDict['mapname']
    metric_in = metric_file(MapName, Hemisphere, currentmesh_settings)
    metric_out = metric_file(MapName, Hemisphere, dest_mesh_settings)

    current_midthickness = surf_file('midthickness', Hemisphere, currentmesh_settings)
    new_midthickness = surf_file('midthickness', Hemisphere, dest_mesh_settings)

    current_sphere_surf = surf_file(current_sphere, Hemisphere, currentmesh_settings)
    dest_sphere_surf = surf_file(dest_sphere, Hemisphere, dest_mesh_settings)

    if dscalarDict['mask_medialwall']:
        run(['wb_command', '-metric-resample', metric_in,
            current_sphere_surf, dest_sphere_surf, 'ADAP_BARY_AREA', metric_out,
            '-area-surfs', current_midthickness, new_midthickness,
            '-current-roi', roi_file(Hemisphere, currentmesh_settings)])
        run(['wb_command', '-metric-mask', metric_out,
            roi_file('L', dest_mesh_settings), metric_out])
    else:
        run(['wb_command', '-metric-resample',
            metric_in, current_sphere_surf, dest_sphere_surf, 'ADAP_BARY_AREA', metric_out,
            '-area-surfs', current_midthickness, new_midthickness])

def convert_freesurfer_annot(labelname, FreeSurferFolder, dest_mesh_settings):
    ''' convert a freesurfer annot to a gifti label and set metadata'''
    global Subject
    for Hemisphere, hemisphere, Structure in [('L','l','CORTEX_LEFT'), ('R','r', 'CORTEX_RIGHT')]:
        fs_annot = os.path.join(FreeSurferFolder,
            'label','{}h.{}.annot'.format(hemisphere, labelname))
        if os.path.exists(fs_annot):
          label_gii = label_file(labelname, Hemisphere, dest_mesh_settings)
          run(['mris_convert', '--annot', fs_annot,
            os.path.join(FreeSurferFolder,'surf','{}h.white'.format(hemisphere)),
            label_gii])
          run(['wb_command', '-set-structure', label_gii, Structure])
          run(['wb_command', '-set-map-names', label_gii,
            '-map', '1', '{}_{}_{}'.format(Subject,Hemisphere,labelname)])
          run(['wb_command', '-gifti-label-add-prefix',
            label_gii, '{}_'.format(Hemisphere), label_gii])

def resample_label(labelname, Hemisphere, currentmesh_settings, dest_mesh_settings,
        current_sphere = 'sphere', dest_sphere = 'sphere'):
    '''
    resample label files if they exist
    uses wb_command -label-resample with BARYCENTRIC method
    Arguments:
        labelname            Name of label to resample (i.e 'aparc')
        Hemisphere           Hemisphere of label to resample ('L' or 'R')
        currentmesh_settings  Dictionary of Settings for current mesh
        dest_mesh_settings     Dictionary of Settings for destination (output) mesh
        current_sphere       The name (default 'sphere') of the current registration surface
        new_sphere           The name (default 'sphere') of the dest registration surface
    '''
    label_in = label_file(labelname, Hemisphere, currentmesh_settings)
    if  os.path.exists(label_in):
      run(['wb_command', '-label-resample', label_in,
        surf_file(current_sphere, Hemisphere, currentmesh_settings),
        surf_file(dest_sphere, Hemisphere, dest_mesh_settings), 'BARYCENTRIC',
        label_file(labelname, Hemisphere, dest_mesh_settings), '-largest'])

def convert_freesurfer_T1(FreeSurferFolder, T1w_nii):
    ''' convert T1w from freesurfer(mgz) to nifti format, and run fslreorient2std
        Arguments:
            T1w_nii     Path to T1wImage to with desired output orientation
            FreeSurferFolder  Path the to subjects freesurfer output
    '''
    run(['mri_convert', os.path.join(FreeSurferFolder,'mri','T1.mgz'), T1w_nii])
    run(['fslreorient2std', T1w_nii, T1w_nii])

def convert_freesurfer_mgz(ImageName,  T1w_nii, FreeSurferFolder, OutDir):
    ''' convert image from freesurfer(mgz) to nifti format, and
        realigned to the specified T1wImage, and imports labels
        Arguments:
            ImageName    Name of Image to Convert
            T1w_nii     Path to T1wImage to with desired output orientation
            FreeSurferFolder  Path the to subjects freesurfer output
            OutDir       Output Directory for converted Image
    '''
    freesurfer_mgz = os.path.join(FreeSurferFolder,'mri','{}.mgz'.format(ImageName))
    if os.path.isfile(freesurfer_mgz):
        Image_nii = os.path.join(OutDir,'{}.nii.gz'.format(ImageName))
        run(['mri_convert', '-rt', 'nearest',
          '-rl', T1w_nii, freesurfer_mgz, Image_nii])
        run(['wb_command', '-logging', 'SEVERE','-volume-label-import', Image_nii,
          os.path.join(ciftify.config.find_ciftify_global(),'hcp_config','FreeSurferAllLut.txt'),
          Image_nii, '-drop-unused-labels'])

def convert_freesurfer_surface(Surface, SurfaceType, FreeSurferFolder,dest_mesh_settings,
        SurfaceSecondaryType = None, cras_mat = None, add_to_spec = True):
    '''
    Convert freesurfer surface to gifti surface files
    Arguments:
        Surface           Surface Name
        SurfaceType       Surface type to add to the metadata
        SecondaryType     Type that will be added to gifti metadata
        FreeSurferFolder  The subject freesurfer output folder
        dest_mesh_settings  Dictionary of settings with naming conventions for the gifti files
        cras_mat          Path to the freesurfer affine matrix
        add_to_spec       Wether to add the gifti file the spec file (default True)
    '''
    global Subject
    for Hemisphere, hemisphere, Structure in [('L','l','CORTEX_LEFT'), ('R','r', 'CORTEX_RIGHT')]:
        surf_fs = os.path.join(FreeSurferFolder,'surf','{}h.{}'.format(hemisphere, Surface))
        surf_native = surf_file(Surface, Hemisphere, dest_mesh_settings)
        ## convert the surface into the T1w/Native Folder
        run(['mris_convert',surf_fs, surf_native])
        if SurfaceSecondaryType:
            run(['wb_command', '-set-structure', surf_native, Structure,
                '-surface-type', SurfaceType, '-surface-secondary-type', SurfaceSecondaryType])
        else:
            run(['wb_command', '-set-structure', surf_native, Structure,
                '-surface-type', SurfaceType])
        if cras_mat:
            run(['wb_command', '-surface-apply-affine', surf_native,
                    cras_mat, surf_native])
        run(['wb_command', '-add-to-spec-file',spec_file(dest_mesh_settings),Structure, surf_native])

def convert_freesurfer_maps(MapDict, FreeSurferFolder, dest_mesh_settings):
    ''' convert a freesurfer data (thickness, curv, sulc) to a gifti metric and set metadata'''
    global Subject
    for Hemisphere, hemisphere, Structure in [('L','l','CORTEX_LEFT'), ('R','r', 'CORTEX_RIGHT')]:
        map_gii = metric_file(MapDict['mapname'], Hemisphere, dest_mesh_settings)
        ## convert the freesurfer files to gifti
        run(['mris_convert', '-c',
            os.path.join(FreeSurferFolder,'surf','{}h.{}'.format(hemisphere, MapDict['fsname'])),
            os.path.join(FreeSurferFolder,'surf', '{}h.white'.format(hemisphere)),
            map_gii])
        ## set a bunch of meta-data and multiply by -1
        run(['wb_command', '-set-structure',map_gii, Structure])
        run(['wb_command', '-metric-math', '"(var * -1)"',
            map_gii, '-var', 'var', map_gii])
        run(['wb_command', '-set-map-names', map_gii,
            '-map', '1', '{}_{}{}'.format(Subject, Hemisphere, MapDict['map_postfix'])])
        if MapDict['mapname'] == 'thickness':
            ## I don't know why but there are thickness specific extra steps'''
            # Thickness set thickness at absolute value than set palette metadata
            run(['wb_command', '-metric-math', '"(abs(thickness))"',
                map_gii, '-var', 'thickness', map_gii])
        run(['wb_command', '-metric-palette', map_gii, MapDict['palette_mode'],
            MapDict['palette_options']])

def medialwall_rois_from_thickness_maps(mesh_settings):
    '''create and roi file by thresholding the thickness surfaces'''
    global Subject
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
      ## create the native ROI file using the thickness file
      native_roi =  roi_file(Hemisphere, mesh_settings)
      midthickness_gii = surf_file('midthickness',Hemisphere, mesh_settings)
      run(['wb_command', '-metric-math', '"(thickness > 0)"', native_roi,
        '-var', 'thickness', metric_file('thickness', Hemisphere, mesh_settings)])
      run(['wb_command', '-metric-fill-holes',
        midthickness_gii, native_roi, native_roi])
      run(['wb_command', '-metric-remove-islands',
        midthickness_gii, native_roi, native_roi])
      run(['wb_command', '-set-map-names', native_roi,
        '-map', '1', '{}_{}_ROI'.format(Subject, Hemisphere)])

def merge_subject_medialwall_with_altastemplate(HighResMesh, MeshesDict, RegSphere, tmpdir):
    '''resample the atlas medial wall roi into subjects native space then merge with native roi'''
    SurfaceAtlasDIR = os.path.join(ciftify.config.find_ciftify_global(),'standard_mesh_atlases')
    native_mesh_settings = MeshesDict['AtlasSpaceNative']
    highresmesh_settings = MeshesDict['HighResMesh']
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        #Ensure no zeros in atlas medial wall ROI
        atlasroi_native_gii = metric_file('atlasroi', Hemisphere, native_mesh_settings) ## note this roi is a temp file so I'm not using the roi_file function
        native_roi = roi_file(Hemisphere, native_mesh_settings)
        run(['wb_command', '-metric-resample',
            roi_file(Hemisphere, highresmesh_settings),
            surf_file('sphere', Hemisphere, highresmesh_settings),
            surf_file(RegSphere, Hemisphere, native_mesh_settings),
            'BARYCENTRIC', atlasroi_native_gii,'-largest'])
        run(['wb_command', '-metric-math', '"(atlas + individual) > 0"', native_roi,
            '-var', 'atlas', atlasroi_native_gii, '-var', 'individual', native_roi])

def run_fs_reg_LR(HighResMesh, RegSphereOut, native_mesh_settings):
    ''' Copy all the template files and do the FS left to right registration'''
    global Subject
    SurfaceAtlasDIR = os.path.join(ciftify.config.find_ciftify_global(),'standard_mesh_atlases')
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
      #Concatinate FS registration to FS --> FS_LR registration
      FSRegSphere = surf_file('sphere.reg.reg_LR', Hemisphere, native_mesh_settings)
      run(['wb_command', '-surface-sphere-project-unproject',
        surf_file('sphere.reg', Hemisphere, native_mesh_settings),
        os.path.join(SurfaceAtlasDIR, 'fs_{}'.format(Hemisphere),
            'fsaverage.{0}.sphere.{1}k_fs_{0}.surf.gii'.format(Hemisphere, HighResMesh)),
        os.path.join(SurfaceAtlasDIR, 'fs_{}'.format(Hemisphere),
            'fs_{0}-to-fs_LR_fsaverage.{0}_LR.spherical_std.{1}k_fs_{0}.surf.gii'.format(Hemisphere, HighResMesh)),
        FSRegSphere])
      #Make FreeSurfer Registration Areal Distortion Maps
      calc_ArealDistortion_gii(
        surf_file('sphere', Hemisphere, native_mesh_settings),
        FSRegSphere,
        metric_file('ArealDistortion_FS', Hemisphere, native_mesh_settings),
        '{}_{}'.format(Subject, Hemisphere), 'FS')

def dilate_and_mask_metric(mesh_settings, dscalarsDict):
    ''' dilate and mask gifti metric data..done after refinining the medial roi mask'''
    ## remask the thickness and curvature data with the redefined medial wall roi
    for mapname in dscalarsDict.keys():
        for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
            if dscalarsDict[mapname]['mask_medialwall']:
              ## dilate the thickness and curvature file by 10mm
              metric_map = metric_file(mapname,Hemisphere,mesh_settings)
              run(['wb_command', '-metric-dilate', metric_map,
                surf_file('midthickness',Hemisphere, mesh_settings),
                '10', metric_map,'-nearest'])
              ## apply the medial wall roi to the thickness and curvature files
              run(['wb_command', '-metric-mask', metric_map,
                roi_file(Hemisphere, mesh_settings), metric_map])

def link_to_template_file(subject_file, global_file, via_file):
    '''
    So the orig hcp pipelines would copy atlas files into each subjects directory.
    This has the benefit of making the atlas files easier to find and copy across systems,
    but creates many redundant files.
    So instead I will copy the atlas files into a templates directory in the HCP_DATA Folder
    than link from each Subject individual directory to this file
    '''
    ## copy from cifitfy template to the HCP_DATA if via_file does not exist
    if not os.path.isfile(via_file):
        via_folder = os.path.dirname(via_file)
        if not os.path.exists(via_folder): run(['mkdir','-p',via_folder])
        run(['cp', global_file, via_file])
    ## link the subject_file to via_file
    os.symlink(os.path.relpath(via_file, os.path.dirname(subject_file)), subject_file)


def create_cifti_subcortical_ROIs(AtlasSpaceFolder, GrayordinatesResolutions, LinkTemplate = True):
    '''
    defines the subcortical ROI labels for cifti files
    combines a template ROI masks with the participants freesurfer wmparc output to do so
    '''
    global HCP_DATA
    # The template files required for this section
    FreeSurferLabels = os.path.join(ciftify.config.find_ciftify_global(),'hcp_config','FreeSurferAllLut.txt')
    GrayordinatesSpaceDIR = os.path.join(ciftify.config.find_ciftify_global(),'91282_Greyordinates')
    SubcorticalGrayLabels = os.path.join(ciftify.config.find_ciftify_global(),'hcp_config','FreeSurferSubcorticalLabelTableLut.txt')
    Avgwmparc = os.path.join(ciftify.config.find_ciftify_global(),'standard_mesh_atlases','Avgwmparc.nii.gz')
    ## right now we only have a templat for the 2mm greyordinate space..
    for GrayordinatesResolution in GrayordinatesResolutions:
      ## The outputs of this sections
      Atlas_ROIs = os.path.join(AtlasSpaceFolder,'ROIs', 'Atlas_ROIs.{}.nii.gz'.format(GrayordinatesResolution))
      wmparc_ROIs = os.path.join(tmpdir, 'wmparc.{}.nii.gz'.format(GrayordinatesResolution))
      wmparcAtlas_ROIs = os.path.join(tmpdir, 'Atlas_wmparc.{}.nii.gz'.format(GrayordinatesResolution))
      ROIs_nii = os.path.join(AtlasSpaceFolder, 'ROIs', 'ROIs.{}.nii.gz'.format(GrayordinatesResolution))
      ## linking this file into the subjects folder because func2hcp will need it
      link_to_template_file(Atlas_ROIs,
        os.path.join(GrayordinatesSpaceDIR, 'Atlas_ROIs.{}.nii.gz'.format(GrayordinatesResolution)),
        os.path.join(HCP_DATA, 'zz_templates', 'Atlas_ROIs.{}.nii.gz'.format(GrayordinatesResolution)))

      ## the analysis steps - resample the participants wmparc output the greyordinate resolution
      run(['applywarp', '--interp=nn', '-i', os.path.join(AtlasSpaceFolder, 'wmparc.nii.gz'),
        '-r', Atlas_ROIs, '-o', wmparc_ROIs])
      ## import the label metadata
      run(['wb_command', '-volume-label-import',
        wmparc_ROIs, FreeSurferLabels, wmparc_ROIs, '-drop-unused-labels'])
    #   run(['applywarp', '--interp=nn', '-i', Avgwmparc, '-r', Atlas_ROIs, '-o', wmparcAtlas_ROIs])
    #   run(['wb_command', '-volume-label-import',
    #     wmparcAtlas_ROIs, FreeSurferLabels,  wmparcAtlas_ROIs, '-drop-unused-labels'])
      run(['wb_command', '-volume-label-import',
        wmparc_ROIs, SubcorticalGrayLabels, ROIs_nii,'-discard-others'])

def copy_colin_flat_and_add_to_spec(mesh_settings):
    ''' copy the colin flat atlas out of the templates folder and add it to the spec file'''
    global HCP_DATA
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        colin_src = os.path.join(ciftify.config.find_ciftify_global(),
            'standard_mesh_atlases',
            'colin.cerebral.{}.flat.{}.surf.gii'.format(Hemisphere, mesh_settings['meshname']))
        if os.path.exists(colin_src):
            colin_dest = surf_file('flat', Hemisphere, mesh_settings)
            link_to_template_file(colin_dest, colin_src,
                os.path.join(HCP_DATA, 'zz_templates', os.path.basename(colin_src)))
            run(['wb_command', '-add-to-spec-file', spec_file(mesh_settings), Structure, colin_dest])

def copy_sphere_mesh_from_template(mesh_settings):
    '''Copy the sphere of specific mesh settings out of the template and into subjects folder'''
    global HCP_DATA
    meshname = mesh_settings['meshname']
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        if meshname == '164k_fs_LR':
            sphere_src = os.path.join(ciftify.config.find_ciftify_global(),
                'standard_mesh_atlases',
                'fsaverage.{}_LR.spherical_std.{}.surf.gii'.format(Hemisphere, meshname))
        else :
            sphere_src = os.path.join(ciftify.config.find_ciftify_global(),
                'standard_mesh_atlases','{}.sphere.{}.surf.gii'.format(Hemisphere, meshname))
        sphere_dest = surf_file('sphere', Hemisphere, mesh_settings)
        link_to_template_file(sphere_dest, sphere_src,
            os.path.join(HCP_DATA, 'zz_templates', os.path.basename(sphere_src)))
        run(['wb_command', '-add-to-spec-file', spec_file(mesh_settings), Structure, sphere_dest])

def copy_atlasroi_from_template(mesh_settings):
    '''Copy the atlasroi (roi of medialwall) for a specific mesh out of templates'''
    global HCP_DATA
    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
        roi_src = os.path.join(ciftify.config.find_ciftify_global(),
            'standard_mesh_atlases',
            '{}.atlasroi.{}.shape.gii'.format(Hemisphere, mesh_settings['meshname']))
        if os.path.exists(roi_src):
            ## Copying sphere surface from templates file to subject folder
            roi_dest = roi_file(Hemisphere, mesh_settings)
            link_to_template_file(roi_dest, roi_src,
                os.path.join(HCP_DATA, 'zz_templates', os.path.basename(roi_src)))

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
    logger.info("Username: {}".format(getstdout(['whoami'], echo = False).replace(os.linesep,'')))
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

def getstdout(cmdlist, echo = True):
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

def main(arguments, tmpdir):

    global Subject
    global HCP_DATA

    SUBJECTS_DIR = arguments["--fs-subjects-dir"]
    MakeLowReshNative = arguments["--resample-LowRestoNative"]

    if SUBJECTS_DIR == None: SUBJECTS_DIR = ciftify.config.find_freesurfer_data()

    logger.info("Arguments: ")
    logger.info('    freesurfer SUBJECTS_DIR: {}'.format(SUBJECTS_DIR))
    logger.info('    HCP_DATA directory: {}'.format(HCP_DATA))
    logger.info('    Subject: {}'.format(Subject))

    #add my config info
    log_build_environment()

    logger.debug("Defining Settings")
    HighResMesh = "164"
    LowResMeshes = ["32"]
    GrayordinatesResolutions = [2]
    RegName = "FS"

    ## the Meshes Dict contrain file paths and naming conventions specitic to all ouput meshes
    MeshesDict = define_SpacesDict(HCP_DATA, Subject, HighResMesh, LowResMeshes,
        tmpdir, MakeLowReshNative)

    ## the dscalarsDict contrains naming conventions and setting specfic to each map output
    dscalarsDict = define_dscalarsDict(RegName)

    logger.info("START: FS2CaretConvertRegisterNonlinear")

    FreeSurferFolder = os.path.join(SUBJECTS_DIR,Subject)

    VolRegSettings = define_VolRegSettings(Subject, HCP_DATA, method = 'FSL_fnirt', StandardRes = '2mm')
    #Make some folders for this and later scripts
    ### Naming conventions
    T1wFolder = os.path.join(HCP_DATA, Subject, 'T1w')
    AtlasSpaceFolder = os.path.join(HCP_DATA, Subject, 'MNINonLinear')
    for k, mDict in MeshesDict.items():
        run(['mkdir','-p', mDict['Folder']])
        run(['mkdir','-p', mDict['tmpdir']])
    run(['mkdir','-p',VolRegSettings['xfms_dir']])
    run(['mkdir','-p',os.path.join(AtlasSpaceFolder,'ROIs')])
    run(['mkdir','-p',os.path.join(AtlasSpaceFolder,'Results')])

    ## the ouput files
    ###Templates and settings
    T1w_nii = os.path.join(VolRegSettings['src_dir'], VolRegSettings['T1wImage'])
    T1wImageBrainMask = os.path.join(VolRegSettings['src_dir'], VolRegSettings['BrainMask'])
    T1wBrain_nii = os.path.join(VolRegSettings['src_dir'], VolRegSettings['T1wBrain'])
    T1wImage_MNI = os.path.join(VolRegSettings['dest_dir'],VolRegSettings['T1wImage'])

    ###### convert the mgz T1w and put in T1w folder
    logger.info(section_header("Converting T1wImage and Segmentations from freesurfer"))
    convert_freesurfer_T1(FreeSurferFolder, T1w_nii)

    #Convert FreeSurfer Volumes and import the label metadata
    for Image in ['wmparc', 'aparc.a2009s+aseg', 'aparc+aseg']:
      convert_freesurfer_mgz(Image,  T1w_nii, FreeSurferFolder, T1wFolder)

    ## Create FreeSurfer Brain Mask from the wmparc image
    logger.info(section_header('Creating brainmask from freesurfer wmparc segmentation'))
    make_brainmask_from_wmparc(os.path.join(T1wFolder, 'wmparc.nii.gz'), T1wImageBrainMask)
    ## apply brain mask to the T1wImage
    mask_T1wImage(T1w_nii, T1wImageBrainMask, T1wBrain_nii)

    ## register the T1wImage to MNIspace
    logger.info(section_header("Registering T1wImage to MNI template using FSL FNIRT"))
    run_FSL_fnirt_registration(VolRegSettings, tmpdir)

    #Convert FreeSurfer Segmentations and brainmask to MNI space
    logger.info(section_header("Applying MNI transform to label files"))
    for Image in ['wmparc', 'aparc.a2009s+aseg', 'aparc+aseg']:
        apply_nonLinear_warp_to_nifti_rois(Image, VolRegSettings, import_labels = True)
    ## also tranform the brain mask to MNI space
    apply_nonLinear_warp_to_nifti_rois('brainmask_fs', VolRegSettings, import_labels = False)

    #Create Spec Files including the T1w files
    add_T1wImages_to_spec_files(MeshesDict)

    # Import Subcortical ROIs and resample to the Grayordinate Resolution
    create_cifti_subcortical_ROIs(AtlasSpaceFolder, GrayordinatesResolutions)

    #Find c_ras offset between FreeSurfer surface and volume and generate matrix to transform surfaces
    logger.info(section_header("Converting freesurfer surfaces to gifti"))
    cras_mat = os.path.join(tmpdir, 'cras.mat')
    write_cras_file(FreeSurferFolder, cras_mat)

    for Surface, SecondaryType in [('white','GRAY_WHITE'), ('pial', 'PIAL')]:
        ## convert the surfaces from freesurfer into T1w Native Directory
        convert_freesurfer_surface(Surface, 'ANATOMICAL', FreeSurferFolder,
            MeshesDict['T1wNative'], SurfaceSecondaryType = SecondaryType,
            cras_mat = cras_mat, add_to_spec = True)
        ## MNI transform the surfaces into the MNINonLinear/Native Folder
        apply_nonLinear_warp_to_surface(Surface, VolRegSettings, MeshesDict)

    #Convert original and registered spherical surfaces and add them to the nonlinear spec file
    convert_freesurfer_surface(Surface = 'sphere', SurfaceType = 'SPHERICAL',
          FreeSurferFolder = FreeSurferFolder, dest_mesh_settings = MeshesDict['AtlasSpaceNative'],
          SurfaceSecondaryType = None, cras_mat = None, add_to_spec = True)
    convert_freesurfer_surface(Surface = 'sphere.reg', SurfaceType = 'SPHERICAL',
        FreeSurferFolder = FreeSurferFolder, dest_mesh_settings = MeshesDict['AtlasSpaceNative'],
        SurfaceSecondaryType = None, cras_mat = None, add_to_spec = False)

    logger.info(section_header("Creating midthickness, inflated and very_inflated surfaces"))
    for mesh in ['T1wNative', 'AtlasSpaceNative']:
        ## build midthickness out the white and pial
        make_midthickness_surfaces(MeshesDict[mesh])
        # make inflated surfaces from midthickness
        make_inflated_surfaces(MeshesDict[mesh])

    # Convert freesurfer annotation to gift labels and set meta-data
    logger.info(section_header("Convertng Freesufer measures to gifti"))
    for Map in ['aparc', 'aparc.a2009s', 'BA']:
      convert_freesurfer_annot(Map, FreeSurferFolder, MeshesDict['AtlasSpaceNative'])

    #Add more files to the spec file and convert other FreeSurfer surface data to metric/GIFTI including sulc, curv, and thickness.
    for Map, MapDict in dscalarsDict.iteritems():
        if 'fsname' in MapDict.keys():
            convert_freesurfer_maps(MapDict, FreeSurferFolder, MeshesDict['AtlasSpaceNative'])

    medialwall_rois_from_thickness_maps(MeshesDict['AtlasSpaceNative'])
      #End main native mesh processing

    ## use data from the template files along with the freesurfer sphere to create RegSphere
    logger.info(section_header("Concatenating Freesurfer Reg wiht template to get fs_LR reg"))
    FSRegSphere = 'sphere.reg.reg_LR'
    run_fs_reg_LR(HighResMesh, FSRegSphere, MeshesDict['AtlasSpaceNative'])

    if RegName == 'MSMSulc':
        run_MSMSulc_registration()
    else :
     RegSphere = FSRegSphere

    logger.info(section_header("Importing HighRes Template Sphere and Medial Wall ROI"))
    ## copy the HighResMesh medialwall roi and the sphere mesh from the templates
    copy_atlasroi_from_template(MeshesDict['HighResMesh'])
    copy_sphere_mesh_from_template(MeshesDict['HighResMesh'])

    ## incorporate the atlasroi boundries into the native space roi
    merge_subject_medialwall_with_altastemplate(HighResMesh, MeshesDict, RegSphere, tmpdir)

    ## remask the thickness and curvature data with the redefined medial wall roi
    dilate_and_mask_metric(MeshesDict['AtlasSpaceNative'], dscalarsDict)

    logger.info(section_header("Creating Native Space Dense Maps"))
    ## combine L and R metrics into dscalar files
    for Map in ['aparc', 'aparc.a2009s', 'BA']:
        create_dlabel(MeshesDict['AtlasSpaceNative'], Map)
    ## combine L and R labels into a dlabel file
    for MapName in dscalarsDict.keys():
        create_dscalar(MeshesDict['AtlasSpaceNative'], dscalarsDict[MapName])

    ## add all the dscalar and dlable files to the spec file
    add_denseMaps_to_specfile(MeshesDict['T1wNative'], dscalarsDict)
    add_denseMaps_to_specfile(MeshesDict['AtlasSpaceNative'], dscalarsDict)

    #Populate Highres fs_LR spec file.
    logger.info(section_header('Resampling data from Native to {}'.format(MeshesDict['HighResMesh']['meshname'])))

    copy_colin_flat_and_add_to_spec(MeshesDict['HighResMesh'])
    # Deform surfaces and other data according to native to folding-based registration selected above.
    for Surface in ['white', 'midthickness', 'pial']:
        resample_surfs_and_add_to_spec(Surface,
                MeshesDict['AtlasSpaceNative'], MeshesDict['HighResMesh'],
                current_sphere = RegSphere)
    ## create the inflated HighRes surfaces
    make_inflated_surfaces(MeshesDict['HighResMesh'])

    for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
      ## resample the metric data to the new mesh
      for MapName in dscalarsDict.keys():
        resample_and_mask_metric(dscalarsDict[MapName], Hemisphere, MeshesDict['AtlasSpaceNative'],
            MeshesDict['HighResMesh'], current_sphere = RegSphere)
      ## resample all the label data to the new mesh
      for Map in ['aparc', 'aparc.a2009s', 'BA']:
          resample_label(Map, Hemisphere, MeshesDict['AtlasSpaceNative'],
            MeshesDict['HighResMesh'], current_sphere = RegSphere)
    ## combine L and R metrics into dscalar files
    for Map in ['aparc', 'aparc.a2009s', 'BA']:
        create_dlabel(MeshesDict['HighResMesh'], Map)
    ## combine L and R labels into a dlabel file
    for MapName in dscalarsDict.keys():
        create_dscalar(MeshesDict['HighResMesh'], dscalarsDict[MapName])
    add_denseMaps_to_specfile(MeshesDict['HighResMesh'], dscalarsDict)

    #Populate LowRes fs_LR spec file.
    for LowResMesh in LowResMeshes:
        logger.info(section_header('Resampling data from Native to {}k_fs_LR'.format(LowResMesh)))
        ## define the LowResMesh Settings
        src_mesh_settings = MeshesDict['AtlasSpaceNative']
        dest_mesh_settings = MeshesDict['{}k_fs_LR'.format(LowResMesh)]
        # Set Paths for this section
        copy_atlasroi_from_template(dest_mesh_settings)
        copy_sphere_mesh_from_template(dest_mesh_settings)
        copy_colin_flat_and_add_to_spec(dest_mesh_settings)
        # Deform surfaces and other data according to native to folding-based registration selected above.
        for Surface in ['white', 'midthickness', 'pial']:
            resample_surfs_and_add_to_spec(Surface,
                    src_mesh_settings, dest_mesh_settings, current_sphere = RegSphere)
        ## create the inflated HighRes surfaces
        make_inflated_surfaces(dest_mesh_settings, iterations_scale = 0.75)

        for Hemisphere, Structure in [('L','CORTEX_LEFT'), ('R','CORTEX_RIGHT')]:
          ## resample the metric data to the new mesh
          for MapName in dscalarsDict.keys():
            resample_and_mask_metric(dscalarsDict[MapName], Hemisphere,
                src_mesh_settings, dest_mesh_settings, current_sphere = RegSphere)
          ## resample all the label data to the new mesh
          for Map in ['aparc', 'aparc.a2009s', 'BA']:
              resample_label(Map, Hemisphere, src_mesh_settings,
                dest_mesh_settings, current_sphere = RegSphere)
        ## combine L and R metrics into dscalar files
        for Map in ['aparc', 'aparc.a2009s', 'BA']:
            create_dlabel(dest_mesh_settings, Map)
        ## combine L and R labels into a dlabel file
        for MapName in dscalarsDict.keys():
            create_dscalar(dest_mesh_settings, dscalarsDict[MapName])
        ## add all the dscalar and dlable files to the spec file
        add_denseMaps_to_specfile(dest_mesh_settings, dscalarsDict)

    if MakeLowReshNative:
        for LowResMesh in LowResMeshes:
            mesh_settings = MeshesDict['Native{}k_fs_LR'.format(LowResMesh)]
            copy_sphere_mesh_from_template(mesh_settings)
            for Surface in ['white', 'pial', 'midthickness']:
                resample_surfs_and_add_to_spec(Surface,
                        MeshesDict['AtlasSpaceNative'], mesh_settings,
                        current_sphere = RegSphere)
            make_inflated_surfaces(mesh_settings, iterations_scale = 0.75)
            ## add dsclars and dlabels from the AtlasSpaceFolder mesh
            add_denseMaps_to_specfile(mesh_settings, dscalarsDict)

if __name__=='__main__':

    arguments  = docopt(__doc__)

    global DRYRUN
    global Subject
    global HCP_DATA

    VERBOSE      = arguments['--verbose']
    DEBUG        = arguments['--debug']
    DRYRUN       = arguments['--dry-run']
    HCP_DATA = arguments["--hcp-data-dir"]
    Subject = arguments["<Subject>"]

    if HCP_DATA == None: HCP_DATA = ciftify.config.find_hcp_data()
    # create a local tmpdir
    tmpdir = tempfile.mkdtemp()

    local_logpath = os.path.join(HCP_DATA,Subject)

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
