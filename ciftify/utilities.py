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

def get_subj(path):
    """
    Gets all folder names (i.e., subjects) in a directory (of subjects).
    Removes hidden folders.
    """
    subjects = []
    for subj in os.walk(path).next()[1]:
        if os.path.isdir(os.path.join(path, subj)) == True:
            subjects.append(subj)
    subjects.sort()
    subjects = filter(lambda x: x.startswith('.') == False, subjects)
    return subjects

def has_permissions(directory):
    logger = logging.getLogger(__name__)
    if os.access(directory, 7) == True:
        flag = True
    else:
        logger.info('\nYou do not have write access to directory ' +
                str(directory))
        flag = False
    return flag

def check_os():
    """
    Ensures the user isn't Bill Gates.
    """
    import platform
    logger = logging.getLogger(__name__)

    operating_system = platform.system()
    if operating_system == 'Windows':
        logger.error("""
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
    logger = logging.getLogger(__name__)
    if np.shape(data)[0] != np.shape(mask)[0]:
        logger.error('data = ' + str(data) + ', mask = ' + str(mask))
        raise Exception("""
                        Your data and mask are not in from the same space!
                        """)

def check_mask(mask):
    """
    Ensures mask is 2D.
    """
    logger = logging.getLogger(__name__)
    if np.shape(mask)[1] > 1:
        logger.error('mask contains ' + str(np.shape(mask)[1]) +
                'values per voxel,')
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
    logger = logging.getLogger(__name__)

    check_dims(data, mask)
    check_mask(mask)

    # make sure the rule chosen is kosher
    if any(rule == item for item in ['=', '>', '<']) == False:
        logger.error('threshold rule is ' + str(rule))
        raise Exception("""
                        Your threshold rule must be '=', '>', or '<'!
                        """)

    # make sure the threshold are numeric and non-numpy
    if type(threshold) != list:
        logger.error('threshold datatype is ' + str(type(threshold)))
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
    def __init__(self, hcp_dir, subject):
        temp_scene_dir = "scene{}".format(subject)
        self.dir = os.path.join(hcp_dir, temp_scene_dir)

    def __enter__(self):
        make_dir(self.dir)
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
    Runscommand in default shell, returning the return code. And logging the output.
    It can take a the cmd argument as a string or a list.
    If a list is given, it is joined into a string.
    There are some arguments for changing the way the cmd is run:
       dryrun:     do not actually run the command (for testing) (default: False)
       echo:       Print the command to the log (info (level))
       supress_stdout:  Any standard output from the function is printed to the log at "debug" level but not "info"
    """
    # Wait till logging is needed to get logger, so logging configuration
    # set in main module is respected
    logger = logging.getLogger(__name__)

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
        if len(out) > 0:
            if supress_stdout:
                logger.debug(out)
            else:
                logger.info(out)
        if len(err) > 0 : logger.warning(err)
        return p.returncode

def add_page_header(html_page, qc_config, page_subject, subject=None, active_link=None,
        path='', title=None):
    """
    Adds a QC page header for a 'snap' or index page in the cifti_vis_* scripts.
    """

    if title is None:
        title = page_subject

    first_line = '<!DOCTYPE html>\n<HTML><TITLE>'
    if subject is not None:
        first_line = first_line + " QC {}".format(subject)
    first_line = first_line + " {} </TITLE>\n".format(title)

    html_page.write(first_line)
    ciftify.html.write_header(html_page)

    html_page.write('<body>\n')
    nav_list = get_navigation_list(qc_config, path)
    ciftify.html.write_navbar(html_page, page_subject, nav_list, active_link)

    if subject is not None:
        html_page.write('\n<h1>QC {} {}</h1>\n'.format(subject, page_subject))

def get_navigation_list(qc_config, path=''):
    nav_list = [{'href': '', 'label':'View:'}]

    for image in qc_config.images:
        if image.make_index:
            image_path = os.path.join(path, '{}.html'.format(image.name))
            nav_list.append({ 'href': image_path,
                              'label': image.name})

    index_path = os.path.join(path, 'index.html')
    nav_list.append({'href': index_path, 'label':'Index'})

    return nav_list

def add_images(qc_page, qc_dir, image_list, scene_file):
    """
    Takes a list of scenes and montages, generates them, and adds them to
    qc_page.
    """
    for image in image_list:
        pic_name = "{}.png".format(image.name)
        ciftify.html.add_image(qc_page, 12, pic_name, pic_name, "")
        output_path = os.path.join(qc_dir, pic_name)
        image.make_image(output_path, scene_file)

def add_image_and_subject_index(index_page, config, subjects, page_subject):
    index_page.write('<h1>{} Index</h1>\n'.format(page_subject))
    index_page.write('<h2>All subjects together</h2>\n')
    index_page.write('<ul>\n  ')
    for image in config.images:
        if not image.make_index:
            continue
        index_page.write('<li><a href="{}.html">{} View</a>' \
                '</li>\n'.format(image.name, image.name))
    index_page.write('</ul>\n')
    index_page.write('<h2>Subject Pages</h2>\n')
    index_page.write('<ul>\n  ')
    for subject in subjects:
        index_page.write('<li><a href="{}/qc.html">{}</a>' \
                '</li>\n'.format(subject, subject))
    index_page.write('</ul>\n')
    index_page.write('</body>')

def write_image_index(qc_dir, subjects, qc_config, page_subject, image_name,
        title=None, colwidth=12):
    '''
    Writes html file with all subjects for one pic shown together
    '''
    pic_name = "{}.png".format(image_name)
    html_name = "{}.html".format(image_name)
    # open the file
    html_index = os.path.join(qc_dir, html_name)
    with open(html_index, 'w') as image_page:
        add_page_header(image_page, qc_config, page_subject, title=title,
                active_link=html_name)
        ## add the main title
        if title is not None:
            image_page.write('<h1>{}</h1>\n'.format(title))
        for subject in subjects:
            add_image_and_subject_page_link(image_page, subject, pic_name,
                    colwidth)
        ## close the html page
        image_page.write('</body>\n')

def add_image_and_subject_page_link(image_page, subject, pic_name, colwidth):
    image_page.write('<div class="container" style="width: 100%;">')
    subject_page = os.path.join('{}'.format(subject), 'qc.html')
    pic = os.path.join('{}'.format(subject), pic_name)
    ciftify.html.add_image(image_page, colwidth, subject_page, pic, subject)
    image_page.write('</div>\n</br>')
