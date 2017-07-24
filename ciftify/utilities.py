#!/usr/bin/env python
"""
A collection of utilities for the epitome pipeline. Mostly for getting
subject numbers/names, checking paths, gathering information, etc.
"""

import os
import sys
import copy
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
    the given string.

    Warning: Returns a list in python2 and a generator in python3 so always
    wrap the returned value in list() if you require a list.
    """
    subjects = []

    if not os.path.exists(path):
        # return empty list if given bad path
        return subjects

    for subj in next(os.walk(path))[1]:
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
        voldata, _,_,_ = loadnii(vol_data_nii)

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

def load_surfaces(filename, tempdir):
    '''
    separate a cifti file into surfaces,
    then loads the surface data
    '''
    ## separate the cifti file into left and right surfaces
    L_data_surf=os.path.join(tempdir, 'Ldata.func.gii')
    R_data_surf=os.path.join(tempdir, 'Rdata.func.gii')
    run(['wb_command','-cifti-separate', filename, 'COLUMN',
        '-metric', 'CORTEX_LEFT', L_data_surf,
        '-metric', 'CORTEX_RIGHT', R_data_surf])

    ## load both surfaces and concatenate them together
    Ldata = load_gii_data(L_data_surf)
    Rdata = load_gii_data(R_data_surf)

    return Ldata, Rdata

def load_surfaceonly(filename):
    '''
    separate a cifti file into surfaces,
    then loads and concatenates the surface data
    '''
    with TempDir() as tempdir:
        Ldata, Rdata = load_surfaces(filename, tempdir)
        data = np.vstack((Ldata, Rdata))

    ## return the 2D concatenated surface data
    return data

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
        logger.debug("{} already exists.".format(dir_name))

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass. - Taken from six
    to ensure python 2 and 3 class compatibility"""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

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

def run(cmd, dryrun=False, echo=True, supress_stdout=False):
    """
    Runs command in default shell, returning the return code and logging the
    output. It can take a cmd argument as a string or a list.
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
    # py3 compability :(
    out = out.decode('utf-8')
    err = err.decode('utf-8')

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

class cd(object):
    """
    A context manager for changing directory. Since best practices dictate
    returning to the original directory, saves the original directory and
    returns to it after the block has exited.

    May raise OSError if the given path doesn't exist (or the current directory
    is deleted before switching back)
    """

    def __init__(self, path):
        user_path = os.path.expanduser(path)
        self.new_path = os.path.expandvars(user_path)

    def __enter__(self):
        self.old_path = os.getcwd()
        os.chdir(self.new_path)

    def __exit__(self, e, value, traceback):
        os.chdir(self.old_path)

def get_stdout(cmd_list, echo=True):
   ''' run the command given from the cmd list and report the stdout result

   Input: A command list'''
   logger = logging.getLogger(__name__)
   if echo: logger.info('Evaluating: {}'.format(' '.join(cmd_list)))
   stdout = subprocess.check_output(cmd_list)
   return stdout.decode('utf-8')

def check_output(command, stderr=None):
    """ Ensures python 3 compatibility by always decoding the return value of
    subprocess.check_output

    Input: A command string"""
    output = subprocess.check_output(command, shell=True, stderr=stderr)
    return output.decode('utf-8')
