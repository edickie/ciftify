#!/usr/bin/env python3
"""
A collection of utilities for ciftify functions mostly for
loading data into numpy arrays
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
import nibabel as nib
import nibabel.gifti.giftiio

from ciftify.utils import run, get_stdout, TempDir

def cifti_info(filename):
    '''runs wb_command -file-information" to try to figure out what the file is made off'''
    c_info = get_stdout(['wb_command', '-file-information', filename, '-no-map-info'])
    cinfo = {}
    for line in c_info.split(os.linesep):
        if 'Structure' in line:
            cinfo['has_LSurf'] = True if 'CortexLeft' in line else False
            cinfo['has_RSurf'] = True if 'CortexRight' in line else False
        if 'Maps to Surface' in line:
            cinfo['maps_to_surf'] = True if "true" in line else False
        if 'Maps to Volume' in line:
            cinfo['maps_to_volume'] = True if "true" in line else False
    return cinfo

def wb_labels_to_csv(wb_labels_txt, csv_out = None):
    '''
    flatten the workbench labels table into a version easier to read as csv
    The wb format is plain txt like this

    <labelname>
    <value> <red> <green> <blue> <alpha>

    example:
    LEFT-CEREBRAL-EXTERIOR
    1    180.0  130.0  70.0   255.0

    The ouput csv:
    int_value,labelname,red,green,blue,alpha
    1,LEFT-CEREBRAL-EXTERIOR,180.0,130.0,70.0,255.0

    '''
    ## read in the label table as txt
    labels = pd.read_csv(wb_labels_txt,
                         header=None,
                         names = ['lab','R','G','B','alpha'],
                         delim_whitespace=True)
    ## use pandas pivot functions to reshape the data to one row per label
    labels['A_stack'] = ['one', 'two'] * (int(labels.shape[0]/2))
    labels['B_stack'] = pd.Series(range(int(labels.shape[0]/2))).repeat(2).values
    labels_p = labels.pivot(index = 'B_stack', columns = 'A_stack')
    label_df = pd.DataFrame({'labelname' : labels_p['lab']['one'],
                            'int_value' : labels_p['lab']['two'],
                            'red': labels_p['R']['two'],
                            'green': labels_p['G']['two'],
                            'blue': labels_p['B']['two'],
                            'alpha': labels_p['alpha']['two']})

    ## if file output specified, write to csv and return nothing
    if csv_out:
        label_df.to_csv(csv_out, index = False, columns = ['int_value','labelname', 'red','green','blue','alpha'])
        return(0)
    ## if file output not specified return the label table as a dataframe
    return(label_df)

def voxel_spacing(filename):
    '''use nibabel to return voxel spacing for a nifti file'''
    spacing = nib.load(filename).header.get_zooms()[0:3]
    return spacing

def load_nifti(filename):
    """
    Usage:
        nifti, affine, header, dims = load_nifti(filename)

    Loads a Nifti file (3 or 4 dimensions).

    Returns:
        a 2D matrix of voxels x timepoints,
        the input file affine transform,
        the input file header,
        and input file dimensions.
    """
    # Wait till logging is needed to get logger, so logging configuration
    # set in main module is respected
    logger = logging.getLogger(__name__)

    # load everything in
    try:
        nifti = nib.load(filename)
    except:
        logger.error("Cannot read {}".format(filename))
        sys.exit(1)

    affine = nifti.get_affine()
    header = nifti.get_header()
    dims = list(nifti.shape)

    # if smaller than 3D
    if len(dims) < 3:
        raise Exception("""
                        Your data has less than 3 dimensions!
                        """)

    # if smaller than 4D
    if len(dims) > 4:
        raise Exception("""
                        Your data is at least a penteract (over 4 dimensions!)
                        """)

    # load in nifti and reshape to 2D
    nifti = nifti.get_data()
    if len(dims) == 3:
        dims.append(1)
    nifti = nifti.reshape(dims[0]*dims[1]*dims[2], dims[3])

    return nifti, affine, header, dims

def load_cifti(filename):
    """
    Usage:
        cifti, affine, header, dims = load_cifti(filename)

    Loads a Cifti file (6 dimensions).

    Returns:
        a 2D matrix of voxels x timepoints,
    """
    logger = logging.getLogger(__name__)

    # load everything in
    try:
        cifti = nib.load(filename)
    except:
        logger.error("Cannot read {}".format(filename))
        sys.exit(1)

    ## separate the cifti file into left and right surfaces
    with TempDir() as tempdir:
        L_data_surf=os.path.join(tempdir, 'Ldata.func.gii')
        R_data_surf=os.path.join(tempdir, 'Rdata.func.gii')
        vol_data_nii=os.path.join(tempdir,'vol.nii.gz')
        run(['wb_command','-cifti-separate', filename, 'COLUMN',
            '-metric', 'CORTEX_LEFT', L_data_surf,
            '-metric', 'CORTEX_RIGHT', R_data_surf,
            '-volume-all', vol_data_nii])

        ## load both surfaces and concatenate them together
        Ldata = load_gii_data(L_data_surf)
        Rdata = load_gii_data(R_data_surf)
        voldata, _,_,_ = load_nifti(vol_data_nii)

        cifti_data = np.vstack((Ldata, Rdata, voldata))

    return cifti_data

def load_gii_data(filename, intent='NIFTI_INTENT_NORMAL'):
    """
    Usage:
        data = load_gii_data(filename)

    Loads a gifti surface file (".shape.gii" or ".func.gii").

    Returns:
        a 2D matrix of vertices x timepoints,
    """
    logger = logging.getLogger(__name__)

    ## use nibabel to load surface image
    try:
        surf_dist_nib = nibabel.gifti.giftiio.read(filename)
    except:
        logger.error("Cannot read {}".format(filename))
        sys.exit(1)

    ## gets number of arrays (i.e. TRs)
    numDA = surf_dist_nib.numDA

    ## read all arrays and concatenate in numpy
    try:
        array1 = surf_dist_nib.getArraysFromIntent(intent)[0]
    except IndexError:
        logger.error("Invalid intent: {}".format(intent))
        sys.exit(1)

    data = array1.data
    if numDA >= 1:
        for DA in range(1,numDA):
            data = np.vstack((data, surf_dist_nib.getArraysFromIntent(intent)[
                    DA].data))

    ## transpose the data so that it is vertices by TR
    data = np.transpose(data)

    ## if the output is one dimensional, make it 2D
    if len(data.shape) == 1:
        data = data.reshape(data.shape[0],1)

    return data

def load_surfaces(filename, suppress_echo = False):
    '''
    separate a cifti file into surfaces,
    then loads the surface data
    '''
    ## separate the cifti file into left and right surfaces
    with TempDir() as tempdir:
        L_data_surf=os.path.join(tempdir, 'Ldata.func.gii')
        R_data_surf=os.path.join(tempdir, 'Rdata.func.gii')
        run(['wb_command','-cifti-separate', filename, 'COLUMN',
            '-metric', 'CORTEX_LEFT', L_data_surf,
            '-metric', 'CORTEX_RIGHT', R_data_surf],
            suppress_echo = suppress_echo)

        ## load both surfaces and concatenate them together
        Ldata = load_gii_data(L_data_surf)
        Rdata = load_gii_data(R_data_surf)

    return Ldata, Rdata

def load_concat_cifti_surfaces(filename, suppress_echo = False):
    '''
    separate a cifti file into surfaces,
    then loads and concatenates the surface data
    '''

    Ldata, Rdata = load_surfaces(filename, suppress_echo)
    data = np.vstack((Ldata, Rdata))

    ## return the 2D concatenated surface data
    return data

def load_hemisphere_data(filename, wb_structure, suppress_echo = False):
    '''loads data from one hemisphere of dscalar,nii file'''

    with TempDir() as little_tempdir:
        ## separate the cifti file into left and right surfaces
        data_gii = os.path.join(little_tempdir, 'data.func.gii')
        run(['wb_command','-cifti-separate', filename, 'COLUMN',
            '-metric', wb_structure, data_gii], suppress_echo)

        # loads label table as dict and data as numpy array
        data = load_gii_data(data_gii)
    return data

## measuring distance
def get_surf_distances(surf, orig_vertex, radius_search=100,
                        dryrun = False, suppress_echo = False):
    '''
    uses wb_command -surface-geodesic-distance command to measure
    distance between two vertices on the surface
    '''

    with TempDir() as tmpdir:
        surf_distance = os.path.join(tmpdir, "distancecalc.shape.gii")
        run(['wb_command', '-surface-geodesic-distance',
                surf, str(orig_vertex), surf_distance,
                '-limit', str(radius_search)],
                dryrun=dryrun, suppress_echo = suppress_echo)
        distances = load_gii_data(surf_distance)
    return(distances)

def load_surf_coords(surf):
    '''load the coordinates from a surface file'''
    coords = nibabel.gifti.giftiio.read(surf).getArraysFromIntent('NIFTI_INTENT_POINTSET')[0].data
    return coords


def load_hemisphere_labels(filename, wb_structure, map_number = 1):
    '''separates dlabel file into left and right and loads label data'''

    with TempDir() as little_tempdir:
        ## separate the cifti file into left and right surfaces
        labels_gii = os.path.join(little_tempdir, 'data.label.gii')
        run(['wb_command','-cifti-separate', filename, 'COLUMN',
            '-label', wb_structure, labels_gii])

        # loads label table as dict and data as numpy array
        gifti_img = nibabel.gifti.giftiio.read(labels_gii)
        atlas_data = gifti_img.getArraysFromIntent('NIFTI_INTENT_LABEL')[map_number - 1].data

        atlas_dict = gifti_img.get_labeltable().get_labels_as_dict()

    return atlas_data, atlas_dict

def load_LR_label(filename, map_number):
    '''
    read left and right hemisphere label data and stacks them
    returns the stacked data and the label dictionary
    '''
    label_L, label_dict = load_hemisphere_labels(filename,'CORTEX_LEFT', map_number)
    label_R, _ = load_hemisphere_labels(filename, 'CORTEX_RIGHT', map_number)
    label_LR = np.hstack((label_L, label_R))
    return label_LR, label_dict

def determine_filetype(path):
    '''
    reads in filename and determines the filetype from its extension.
    Returns two values: a string for the filetype, and the basename of the file
    without its extension
    '''
    logger = logging.getLogger(__name__)
    MRbase = os.path.basename(path)
    if MRbase.endswith(".nii"):
        if MRbase.endswith(".dtseries.nii"):
            MR_type = "cifti"
            MRbase = MRbase.replace(".dtseries.nii","")
        elif MRbase.endswith(".dscalar.nii"):
            MR_type = "cifti"
            MRbase = MRbase.replace(".dscalar.nii","")
        elif MRbase.endswith(".dlabel.nii"):
            MR_type = "cifti"
            MRbase = MRbase.replace(".dlabel.nii","")
        else:
            MR_type = "nifti"
            MRbase = MRbase.replace(".nii","")
    elif MRbase.endswith("nii.gz"):
        MR_type = "nifti"
        MRbase = MRbase.replace(".nii.gz","")
    elif MRbase.endswith(".gii"):
        MR_type = "gifti"
        gifti_types = ['.shape.gii', '.func.gii', '.surf.gii', '.label.gii',
            '.gii']
        for ext_type in gifti_types:
            MRbase = MRbase.replace(ext_type, "")
    else:
        logger.error("{} is not a nifti or gifti file type".format(path))
        sys.exit(1)

    return(MR_type, MRbase)
