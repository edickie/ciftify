#!/usr/bin/env python
"""
A collection of utilities for the epitome pipeline. Mostly for getting
subject numbers/names, checking paths, gathering information, etc.
"""

import os, sys, copy
import numpy as np
import nibabel as nib
import ciftify
import nibabel.gifti.giftiio



def get_subj(dir):
    """
    Gets all folder names (i.e., subjects) in a directory (of subjects).
    Removes hidden folders.
    """
    subjects = []
    for subj in os.walk(dir).next()[1]:
        if os.path.isdir(os.path.join(dir, subj)) == True:
            subjects.append(subj)
    subjects.sort()
    subjects = filter(lambda x: x.startswith('.') == False, subjects)
    return subjects

def has_permissions(directory):
    if os.access(directory, 7) == True:
        flag = True
    else:
        print('\nYou do not have write access to directory ' + str(directory))
        flag = False
    return flag

def check_os():
    """
    Ensures the user isn't Bill Gates.
    """
    import platform

    operating_system = platform.system()
    if operating_system == 'Windows':
        print("""
              Windows detected. epitome requires Unix-like operating systems!
              """)
        sys.exit()

def get_date_user():
    """
    Returns a eyeball-friendly timestamp, the current user's name,
    and a filename-friendly timestamp.
    """
    import time
    import getpass

    datetime = time.strftime("%Y/%m/%d -- %H:%M:%S")
    user = getpass.getuser()
    f_id = time.strftime("%y%m%d_%H%M%S")

    return datetime, user, f_id

def mangle_string(string):
    """
    Turns an arbitrary string into a decent foldername/filename
    (no underscores allowed)!
    """
    string = string.replace(' ', '-')
    string = string.strip(",./;'[]\|_=+<>?:{}!@#$%^&*()`~")
    string = string.strip('"')

    return string

def print_dirs(in_dir):
    """
    Prints the directories found within the input directory.
    """
    dir_list = [d for d in os.listdir(in_dir) if
                           os.path.isdir(os.path.join(in_dir, d)) == True]
    dir_list.sort()
    for d in dir_list:
        print('    + ' + d)
    if len(dir_list) == 0:
        print('None found.')

def determine_filetype(filename):
    '''
    reads in filename and determines the filetype from it's extention
    returns two values a string for the filetype, and the basename of the file
    without its extention
    '''
    MRbase = os.path.basename(filename)
    if MRbase.endswith(".nii"):
        if MRbase.endswith("dtseries.nii"):
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
         MRbase = MRbase.replace(".shape.gii","").replace(".func.gii","")

    return MR_type, MRbase

def loadnii(filename):
    """
    Usage:
        nifti, affine, header, dims = loadnii(filename)

    Loads a Nifti file (3 or 4 dimensions).

    Returns:
        a 2D matrix of voxels x timepoints,
        the input file affine transform,
        the input file header,
        and input file dimensions.
    """

    # load everything in
    nifti = nib.load(filename)
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

def loadcifti(filename):
    """
    Usage:
        nifti, affine, header, dims = loadnii(filename)

    Loads a Nifti file (3 or 4 dimensions).

    Returns:
        a 2D matrix of voxels x timepoints,
        the input file affine transform,
        the input file header,
        and input file dimensions.
    """

    # load everything in
    cifti = nib.load(filename)
    affine = cifti.get_affine()
    header = cifti.get_header()
    dims = list(cifti.shape)

    # if smaller than 3D
    if len(dims) < 6:
        raise Exception("""
                        Your data is has less than 6 dims
                        """)

    # if smaller than 4D
    if len(dims) > 6:
        raise Exception("""
                        Your data has over 6 dims
                        """)

    # load in nifti and reshape to 2D
    cifti = cifti.get_data()
    cifti = cifti.reshape(dims[0]*dims[1]*dims[2]*dims[3]*dims[4], dims[5])
    cifti = np.transpose(cifti)

    return cifti, affine, header, dims

def load_gii_data(filename, intent='NIFTI_INTENT_NORMAL'):
    """
    Usage:
        data = load_gii_data(filename)

    Loads a gifti surface file (".shape.gii" or ".func.gii").

    Returns:
        a 2D matrix of vertices x timepoints,
    """
    ## use nibabel to load surface image
    surf_dist_nib = nibabel.gifti.giftiio.read(filename)

    ## gets number of arrays (i.e. TRs)
    numDA = surf_dist_nib.numDA

    ## read all arrays and concatenate in numpy
    data = surf_dist_nib.getArraysFromIntent(intent)[0].data
    if numDA >= 1:
        for DA in range(1,numDA):
            data = np.vstack((data, surf_dist_nib.getArraysFromIntent(intent)[DA].data))

    ## transpose the data so that it is vertices by TR
    data = np.transpose(data)

    ## if the output is one dimensional, make it 2D
    if len(data.shape) == 1:
        data = data.reshape(data.shape[0],1)

    return data

def check_dims(data, mask):
    """
    Ensures the input data and mask are on the same grid.
    """
    if np.shape(data)[0] != np.shape(mask)[0]:
        print('data = ' + str(data) + ', mask = ' + str(mask))
        raise Exception("""
                        Your data and mask are not in from the same space!
                        """)

def check_mask(mask):
    """
    Ensures mask is 2D.
    """
    if np.shape(mask)[1] > 1:
        print('mask contains ' + str(np.shape(mask)[1]) + 'values per voxel,')
        raise Exception("""
                        Your mask can't contain multiple values per voxel!
                        """)

def maskdata(data, mask, rule='>', threshold=[0]):
    """
    Usage:
        data, idx = maskdata(data, mask, rule, threshold)

    Extracts voxels of interest from a 2D data matrix, using a threshold rule
    applied to the mask file, which is assumed to only contain one value per
    voxel.

    Valid thresholds:
        '<' = keep voxels less than threshold value.
        '>' = keep voxels greater than threshold value.
        '=' = keep voxels equal to threshold value.

    The threshold(s) should be a list of value(s).

    By default, this program finds all voxels that are greater than zero in the
    mask, which is handy for removing non-brain voxels (for example).

    Finally, this program *always* removes voxels with constant-zero values
    regardless of your mask, because they are both annoying and useless.
    If it finds voxels like this, it will tell you about them so you can
    investigate.

    Returns:
        voxels of interest in data as a collapsed 2D array
        and a set of indices relative to the size of the original array.
    """
    check_dims(data, mask)
    check_mask(mask)

    # make sure the rule chosen is kosher
    if any(rule == item for item in ['=', '>', '<']) == False:
        print('threshold rule is ' + str(rule))
        raise Exception("""
                        Your threshold rule must be '=', '>', or '<'!
                        """)

    # make sure the threshold are numeric and non-numpy
    if type(threshold) != list:
        print('threshold datatype is ' + str(type(threshold)))
        raise Exception("""
                        Your threshold(s) must be in a list.
                        """)

    # compute the index
    idx = np.array([])
    threshold = list(threshold)
    for t in threshold:
        # add any new voxels corresponding to a given threshold
        if rule == '=':
            idx = np.unique(np.append(idx, np.where(mask == t)[0]))
        elif rule == '>':
            idx = np.unique(np.append(idx, np.where(mask > t)[0]))
        elif rule == '<':
            idx = np.unique(np.append(idx, np.where(mask < t)[0]))

    # find voxels with constant zeros, remove those from the index
    idx_zeros = np.where(np.sum(data, axis=1) == 0)[0]
    idx = np.setdiff1d(idx, idx_zeros)

    # collapse data using the index
    idx = idx.tolist()
    data = data[idx, :]

    return data, idx

def get_mean_roi(data, mask, val):
    """
    Uses the submitted mask to get the mean value from all voxels with
    the submitted mask value. Outputs a single time series, or nans in
    the case of an error.
    """
    if type(val) == int:
        val = [val]

    data, idx = maskdata(data, mask, rule='=', threshold=[val])
    data = np.nanmean(data, axis=0)

    return data

def roi_graph(data, mask):
    """
    This generates a graph G from the correlations the mean timeseries
    taken from each non-zero value in the mask.
    """
    # generate list of ROIs
    rois = filter(lambda x: x > 0, np.unique(mask))
    rois = np.array(rois)
    # generate output array
    ts = np.zeros((len(rois), data.shape[1]))

    for i, roi in enumerate(rois):
        ts[i, :] = get_mean_roi(data, mask, roi)

    G = np.corrcoef(ts)

    return G

def write_graph(filename, G):
    """
    Writes a .csv file representing a graph in matrix form.
    """
    np.savetxt(filename, G)

def translate(data, factors=[]):
    """
    Usage:
        data = translate(data, factors)

    Scales each time series or data point by a factor or set of factors
    of length  equivalent to the number of input voxels. If no factors
    are provided, this will demean each input time series (and will do
    to data that wasn't originally 4D).

    Returns:
        translated versions of the input data.
    """

    # ensure factors is of the correct size
    if len(factors) > 1 and np.shape(data)[0] != len(factors):
        raise Exception("""
                        You submitted a set of factors of the wrong size for
                        the input data!
                        """)

    # if a constant was submitted, scale all time series by it
    if len(factors) == 1:
        data = data / factors

    # if nothing was submitted, scale all time series by it's mean
    elif len(factors) == 0:
        # None adds extra dimension to keep broadcasting in check
        data = data / np.mean(data, axis=1)[:, None]

    return data

def scale_timeseries(ts):
    minimum = np.min(ts)
    ts = ts - minimum

    maximum = np.max(ts)
    ts = ts / maximum

    return ts

def IOTA(junk):
    """
    Does stuff to junk and returns things.
    """
    print('do stuff!')
    things = 'things'

    return things

def init_shell(path, expt):
    """
    Gets all of the subjects and prints them as a BASH friendly variable.
    TO DEPRICATE.
    """
    subjects = epi.utilities.get_subj(os.path.join(path, expt))
    output = '"'

    for subj in subjects:
        output+=str(subj)
        output+=' '
    output+='"'

    os.system('echo ' + str(output))
