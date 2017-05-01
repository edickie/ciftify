#!/usr/bin/env python
"""
A collection of utilities for the epitome pipeline. Mostly for getting
subject numbers/names, checking paths, gathering information, etc.
"""

import os, sys, copy
import subprocess
import tempfile
import shutil
import logging

import numpy as np
import nibabel as nib
import nibabel.gifti.giftiio

import ciftify

def get_subj(path, user_filter=None):
    """
    Gets all folder names (i.e., subjects) in a directory (of subjects).
    Removes hidden folders.

    user_filter option can be used to return only the subjects that contain
    the given string
    """
    subjects = []

    if not os.path.exists(path):
        # return empty list if given bad path
        return subjects

    for subj in os.walk(path).next()[1]:
        subjects.append(subj)
    subjects.sort()
    subjects = filter(lambda x: x.startswith('.') == False, subjects)

    if user_filter:
        subjects = filter(lambda x: user_filter in x, subjects)

    return subjects

def determine_filetype(filename):
    '''
    reads in filename and determines the filetype from its extension.
    Returns two values: a string for the filetype, and the basename of the file
    without its extension
    '''
    MRbase = os.path.basename(filename)
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
        raise TypeError("{} is not a nifti or gifti file type".format(filename))

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

def loadcifti(filename):
    """
    Usage:
        cifti, affine, header, dims = loadcifti(filename)

    Loads a Cifti file (6 dimensions).

    Returns:
        a 2D matrix of voxels x timepoints,
        the input file affine transform,
        the input file header,
        and input file dimensions.
    """
    logger = logging.getLogger(__name__)

    # load everything in
    try:
        cifti = nib.load(filename)
    except:
        logger.error("Cannot read {}".format(filename))
        sys.exit(1)

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

def docmd(command_list, dry_run=False):
    "sends a command (inputed as a list) to the shell"
    # Wait till logging is needed to get logger, so logging configuration
    # set in main module is respected
    logger = logging.getLogger(__name__)
    command_list = [str(cmd) for cmd in command_list]
    logger.debug(' '.join(command_list))
    if dry_run:
        return 0
    return subprocess.call(command_list)

def make_dir(dir_name, dry_run=False):
    # Wait till logging is needed to get logger, so logging configuration
    # set in main module is respected
    logger = logging.getLogger(__name__)
    if dry_run:
        logger.debug("Dry-run, skipping creation of directory "\
                "{}".format(dir_name))
        return

    try:
        os.makedirs(dir_name)
    except OSError:
        logger.debug("{} already exists.")

class TempDir(object):
    def __init__(self):
        self.path = None
        return

    def __enter__(self):
        self.path = tempfile.mkdtemp()
        return self.path

    def __exit__(self, type, value, traceback):
        if self.path is not None:
            shutil.rmtree(self.path)

class TempSceneDir(object):
    """
    A context manager for the temporary scene dir.

    A temp dir in the same directory as the hcp data is used for the scene
    file due to the fact that scene files contain a large number of relative
    paths and the images will come out broken if it is put anywhere else.
    """
    def __init__(self, hcp_dir):
        self.base = os.path.join(hcp_dir, 'scene')

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix=self.base)
        return self.dir

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.dir)

class HCPSettings(object):
    def __init__(self, arguments):
        try:
            temp_hcp = arguments['--hcp-data-dir']
        except KeyError:
            temp_hcp = None
        self.hcp_dir = self.__set_hcp_dir(temp_hcp)

    def __set_hcp_dir(self, user_dir):
        # Wait till logging is needed to get logger, so logging configuration
        # set in main module is respected
        logger = logging.getLogger(__name__)
        if user_dir:
            return os.path.realpath(user_dir)
        found_dir = ciftify.config.find_hcp_data()
        if found_dir is None:
            logger.error("Cannot find HCP data directory, exiting.")
            sys.exit(1)
        return os.path.realpath(found_dir)

class VisSettings(HCPSettings):
    """
    A convenience class. Provides an hcp_dir and qc_dir attribute and a
    function to set each based on the user's input and the environment.
    This is intended to be inherited from in each script, so that user
    settings can be passed together and easily kept track of.

    Arguments:      A docopt parsed dictionary of the user's input arguments.
    qc_mode:        The qc_mode to operate in and the string to include
                    in the qc output folder name.

    Will raise SystemExit if the user hasn't set the hcp-data-dir and the
    environment variable isn't set.
    """
    def __init__(self, arguments, qc_mode):
        HCPSettings.__init__(self, arguments)
        try:
            temp_qc = arguments['--qcdir']
        except KeyError:
            temp_qc = None
        self.qc_mode = qc_mode
        self.qc_dir = self.__set_qc_dir(temp_qc)

    def __set_qc_dir(self, user_qc_dir):
        if user_qc_dir:
            return user_qc_dir
        qc_dir = os.path.join(self.hcp_dir, 'qc_{}'.format(self.qc_mode))
        return qc_dir

def run(cmd, dryrun=False, echo=True, supress_stdout = False):
    """
    Runs command in default shell, returning the return code. And logging the
    output. It can take a the cmd argument as a string or a list.
    If a list is given, it is joined into a string. There are some arguments
    for changing the way the cmd is run:
       dryrun:          Do not actually run the command (for testing) (default:
                        False)
       echo:            Print the command to the log (info (level))
       supress_stdout:  Any standard output from the function is printed to
                        the log at "debug" level but not "info"
    """
    # Wait till logging is needed to get logger, so logging configuration
    # set in main module is respected
    logger = logging.getLogger(__name__)

    if type(cmd) is list:
        cmd = ' '.join(cmd)

    if echo:
        logger.info("Running: {}".format(cmd))

    if dryrun:
        logger.info('Doing a dryrun')
        return 0

    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    out, err = p.communicate()

    if p.returncode:
        logger.error('cmd: {} \n Failed with returncode {}'.format(cmd,
                p.returncode))
    if len(out) > 0:
        if supress_stdout:
            logger.debug(out)
        else:
            logger.info(out)
    if len(err) > 0:
        logger.warning(err)

    return p.returncode
