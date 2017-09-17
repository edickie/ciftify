#!/usr/bin/env python
"""
Produces a csv file mean voxel/vertex time series from a functional file <func>
within a seed mask <seed>.

Usage:
    ciftify_meants [options] <func> <seed>

Arguments:
    <func>          functional data can be (nifti or cifti)
    <seed>          seed mask (nifti, cifti or gifti)

Options:
    --outputcsv PATH     Specify the output filename
    --outputlabels PATH  Specity a file to print the ROI row ids to.
    --mask FILE          brainmask (file format should match seed)
    --roi-label INT      Specify the numeric label of the ROI you want a seedmap for
    --weighted           Compute weighted average timeseries from the seed map
    --hemi HEMI          If the seed is a gifti file, specify the hemisphere (R or L) here
    --debug              Debug logging
    -h, --help           Prints this message

DETAILS:
The default output filename is <func>_<seed>_meants.csv inside the same directory
as the <func> file. This can be changed by specifying the full path after
the '--outputcsv' option. The integer labels for the seeds extracted can be printed
to text using the '--outputlabels' option.

If the seed file contains multiple interger values (i.e. an altas). One row will
be written for each integer value. If you only want a timeseries from one roi in
an atlas, you can specify the integer with the --roi-label option.

A weighted avereage can be calculated from a continuous seed if the --weighted
flag is given.

If a mask is given, the intersection of this mask and the seed mask will be taken.

If a nifti seed if given for a cifti functional file, wb_command -cifti separate will
try extract the subcortical cifti data and try to work with that.

Written by Erin W Dickie, March 17, 2016
"""

import sys
import subprocess
import os
import tempfile
import shutil
import logging
import logging.config

import numpy as np
import scipy as sp
import nibabel as nib
from docopt import docopt

import ciftify

config_path = os.path.join(os.path.dirname(__file__), "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

def run_ciftify_meants(tempdir):
    global DRYRUN

    arguments = docopt(__doc__)
    debug = arguments['--debug']

    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ciftify.utils.log_arguments(arguments)

    settings = UserSettings(arguments)

    ## if seed is dlabel - convert to dscalar
    if ".dlabel.nii" in settings.seed_path:
        ## apolagise for all the cases where this approach doesn't work..
        if settings.weighted:
            logger.error('--weighted mean time-series cannot be calcualted with a .dlabel.nii seed. Exiting.')
            sys.exit(1)
        if settings.roi_label:
            logger.error("Sorry, --roi-label option doesn't work for .dlabel.nii seed inputs. Exiting.")
            sys.exit(1)
        if settings.mask_path:
            logger.error("Sorry, --mask option doesn't work for .dlabel.nii seed inputs. Exiting.")
            sys.exit(1)
        if not settings.func_type == 'cifti':
            logger.error("If <seed> is .dlabel.nii, the <func> needs to be a cifti file. Exiting.")
            sys.exit(1)

        ## parcellate and then right out the parcellations..
        cifti_parcellate_to_meants(settings, tempdir)

    else:
        ## calculated the meants using numpy
        func_data, seed_data, mask_data = load_data_as_numpy_arrays(settings, tempdir)
        calc_meants_with_numpy(func_data, seed_data, mask_data, settings)

def cifti_parcellate_to_meants(settings, tempdir):
    ''' use wb_command -cifti-parcellate to create meants..much faster '''
    ## parcellate and then right out the parcellations..
    if settings.func_path.endswith('dtseries.nii'):
        tmp_parcelated = os.path.join(tempdir, 'parcellated.ptseries.nii')
    if settings.func_path.endswith('dscalar.nii'):
        tmp_parcelated = os.path.join(tempdir, 'parcellated.pscalar.nii')
    ciftify.utils.run(['wb_command', '-cifti-parcellate',
        settings.func_path, settings.seed_path,
        'COLUMN', tmp_parcelated])
    ciftify.utils.run(['wb_command', '-cifti-convert', '-to-text',
        tmp_parcelated, settings.outputcsv,'-col-delim ","'])
    if settings.outputlabels:
        ciftify.utils.run(['wb_command', '-cifti-label-export-table',
            settings.seed_path, '1',
            settings.outputlabels])


def load_data_as_numpy_arrays(settings, tempdir):
    '''loads the data using ciftify.io tools according to their type'''

    if not settings.mask_path: mask_data = None

    if settings.seed_type == "cifti":
        seed_info = ciftify.io.cifti_info(settings.seed_path)
        func_info = ciftify.io.cifti_info(settings.func_path)
        if not all((seed_info['maps_to_volume'], func_info['maps_to_volume'])):
            seed_data = ciftify.io.load_concat_cifti_surfaces(settings.seed_path)
            if settings.func_type == "cifti":
                func_data = ciftify.io.load_concat_cifti_surfaces(settings.func_path)
            else:
                sys.exit('If <seed> is in cifti, func file needs to match.')
            if settings.mask_path:
                if settings.mask_type == "cifti":
                    mask_data = ciftify.io.load_concat_cifti_surfaces(settings.mask_path)
                else:
                    sys.exit('If <seed> is in cifti, func file needs to match.')
        else:
            seed_data = ciftify.io.load_cifti(settings.seed_path)
            if settings.func_type == "cifti":
                func_data = ciftify.io.load_cifti(settings.func_path)
            else:
                sys.exit('If <seed> is in cifti, func file needs to match.')
            if settings.mask_path:
                if settings.mask_type == "cifti":
                     mask_data = ciftify.io.load_cifti(settings.mask_path)
                else:
                  sys.exit('If <seed> is in cifti, mask file needs to match.')

    elif settings.seed_type == "gifti":
        seed_data = ciftify.io.load_gii_data(settings.seed_path)
        if settings.func_type == "gifti":
            func_data = ciftify.io.load_gii_data(settings.func_path)
            if settings.mask_path:
                if settings.mask_type == "gifti":
                    mask_data = ciftify.io.load_gii_data(settings.mask_path)
                else:
                    sys.exit('If <seed> is in gifti, mask file needs to match.')
        elif settings.func_type == "cifti":
            if settings.hemi == 'L':
                func_data = ciftify.io.load_hemisphere_data(settings.func_path, 'CORTEX_LEFT')
            elif settings.hemi == 'R':
                func_data = ciftify.io.load_hemisphere_data(settings.func_path, 'CORTEX_RIGHT')
            ## also need to apply this change to the mask if it matters
            if settings.mask_type == "cifti":
                 if settings.hemi == 'L':
                     mask_data = ciftify.io.load_hemisphere_data(settings.mask_path, 'CORTEX_LEFT')
                 elif settings.hemi == 'R':
                     mask_data = ciftify.io.load_hemisphere_data(settings.mask_path, 'CORTEX_RIGHT')
        else:
            sys.exit('If <seed> is in gifti, <func> must be gifti or cifti')

    elif settings.seed_type == "nifti":
        seed_data, _, _, _ = ciftify.io.load_nifti(settings.seed_path)
        if settings.func_type == "nifti":
            func_data, _, _, _ = ciftify.io.load_nifti(settings.func_path)
        elif settings.func_type == 'cifti':
            subcort_func = os.path.join(tempdir, 'subcort_func.nii.gz')
            ciftify.utils.run(['wb_command',
              '-cifti-separate', settings.func_path, 'COLUMN',
              '-volume-all', subcort_func])
            func_data, _, _, _ = ciftify.io.load_nifti(subcort_func)
        else:
            sys.exit('If <seed> is in nifti, func file needs to match.')
        if settings.mask_path:
            if settings.mask_type == "nifti":
                mask_data, _, _, _ = ciftify.io.load_nifti(settings.mask_path)
            elif settings.mask_type == 'cifti':
                subcort_mask = os.path.join(tempdir, 'subcort_mask.nii.gz')
                ciftify.utils.run(['wb_command',
                  '-cifti-separate', settings.mask_path, 'COLUMN',
                  '-volume-all', subcort_mask])
                mask_data, _, _, _ = ciftify.io.load_nifti(subcort_mask)
            else:
                sys.exit('If <seed> is in nifti, <mask> file needs to match.')

    ## check that dim 0 of both seed and func
    if func_data.shape[0] != seed_data.shape[0]:
        logger.error("<func> and <seed> images have different number of voxels")
        sys.exit(1)

    if seed_data.shape[1] != 1:
        logger.WARNING("your seed volume has more than one timepoint")

    return(func_data, seed_data, mask_data)

def calc_meants_with_numpy(func_data, seed_data, mask_data, settings):
    '''calculate the meants using numpy and write to file '''
    ## even if no mask given, mask out all zero elements..
    std_array = np.std(func_data, axis=1)
    m_array = np.mean(func_data, axis=1)
    std_nonzero = np.where(std_array > 0)[0]
    m_nonzero = np.where(m_array != 0)[0]
    mask_indices = np.intersect1d(std_nonzero, m_nonzero)

    if settings.mask_path:
        # attempt to mask out non-brain regions in ROIs
        n_seeds = len(np.unique(seed_data))
        if seed_data.shape[0] != mask_data.shape[0]:
            sys.exit('ERROR: at the mask and seed images have different number of voxels')
        mask_idx = np.where(mask_data > 0)[0]
        mask_indices = np.intersect1d(mask_indices, mask_idx)
        if len(np.unique(np.multiply(seed_data,mask_data))) != n_seeds:
            sys.exit('ERROR: At least 1 ROI completely outside mask for {}.'.format(outputcsv))

    if settings.weighted:
        out_data = np.average(func_data[mask_indices,:], axis=0,
                              weights=np.ravel(seed_data[mask_indices]))
    else:
        # init output vector
        if settings.roi_label:
            if float(settings.roi_label) not in np.unique(seed_data)[1:]:
               sys.exit('ROI {}, not in seed map labels: {}'.format(settings.roi_label, np.unique(seed)[1:]))
            else:
               rois = [float(settings.roi_label)]
        else:
            rois = np.unique(seed_data)[1:]
        out_data = np.zeros((len(rois), func_data.shape[1]))

        # get mean seed dataistic from each, append to output
        for i, roi in enumerate(rois):
            idx = np.where(seed_data == roi)[0]
            idxx = np.intersect1d(mask_indices, idx)
            out_data[i,:] = np.mean(func_data[idxx, :], axis=0)

    # write out csv
    np.savetxt(settings.outputcsv, out_data, delimiter=",")

    if settings.outputlabels: np.savetxt(settings.outputlabels, rois, delimiter=",")

class UserSettings():
    def __init__(self, arguments):
        self.func_path = self.check_input_path(arguments['<func>'])
        self.seed_path = self.check_input_path(arguments['<seed>'])
        self.mask_path, self.mask_type = self.get_mask(arguments['--mask'])
        self.outputcsv, self.func_type, self.seed_type = self.get_outputcsv(arguments['--outputcsv'])
        self.roi_label = arguments['--roi-label']
        self.outputlabels = self.get_outputlabels(arguments['--outputlabels'])
        self.hemi = self.get_hemi(arguments['--hemi'])
        self.weighted = arguments['--weighted']

    def check_input_path(self, path):
        '''check that path exists and is readable, exit upon failure'''
        if not os.access(path, os.R_OK):
            logger.error('Input {}, does not exist, or you do not have permission to read it.'
                ''.format(path))
            sys.exit(1)
        return(path)

    def check_output_path(self, path):
        ''' use ciftify function to ensure output is writable'''
        ciftify.utils.check_output_writable(path)
        return(path)

    def get_mask(self, mask):
        '''parse mask_type if mask exists'''
        if mask:
            mask = self.check_input_path(mask)
            mask_type, _ = ciftify.io.determine_filetype(mask)
        else:
            mask_type = None
        return(mask, mask_type)

    def get_outputcsv(self, outputcsv):
        '''
        determine func and seed filetypes
        if outputcsv path doesn't exist, make one out of the func and seed names
        '''
        func_type, funcbase = ciftify.io.determine_filetype(self.func_path)
        logger.debug("func_type is {}".format(func_type))
        seed_type, seedbase = ciftify.io.determine_filetype(self.seed_path)
        logger.debug("seed_type is {}".format(seed_type))
        if not outputcsv:
            outputdir = os.path.dirname(self.func_path)
            outputcsv = os.path.join(outputdir,funcbase + '_' + seedbase + '_meants.csv' )
        outputcsv = self.check_output_path(outputcsv)
        return(outputcsv, func_type, seed_type)

    def get_outputlabels(self,outputlabels):
        '''if outputlabels where specified, check that they are writable '''
        if outputlabels:
            self.check_output_path(outputlabels)
        return(outputlabels)

    def get_hemi(self, hemi):
        if hemi:
            if hemi == "L" or hemi == "R":
                return hemi
            else:
                logger.error("--hemi {} not valid option. Exiting.\n"
                    "Specify 'L' (for left) or 'R' (for right)".format(hemi))
                sys.exit(1)
        else:
            if self.seed_type == 'gifti':
                logger.error("If seed type is gifti, Hemisphere needs to be specified with --hemi")
                sys.exit(1)
        return(hemi)

def main():
    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = run_ciftify_meants(tmpdir)
    sys.exit(ret)

if __name__ == '__main__':
    main()
