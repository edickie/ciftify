#!/usr/bin/env python3
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
    -v,--verbose         Verbose logging
    --debug              Debug logging
    -h, --help           Prints this message

DETAILS:
The default output filename is <func>_<seed>_meants.csv inside the same directory
as the <func> file. This can be changed by specifying the full path after
the '--outputcsv' option. The integer labels for the seeds extracted can be printed
to text using the '--outputlabels' option.

If the seed file contains multiple interger values (i.e. an altas). One row will
be written for each integer value. If you only want a timeseries from one roi in
an atlas, you can specify the integer with the '--roi-label' option.

A weighted avereage can be calculated from a continuous seed if the '--weighted'
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
from ciftify.meants import MeantsSettings

logger = logging.getLogger('ciftify')
logger.setLevel(logging.DEBUG)

def run_ciftify_meants(settings):
    '''run ciftify_meants workflow '''

    ## if seed is dlabel - convert to dscalar
    if ".dlabel.nii" in settings.seed.path:
        ## apolagise for all the cases where this approach doesn't work..
        if settings.weighted:
            logger.error('--weighted mean time-series cannot be calcualted with a .dlabel.nii seed. Exiting.')
            sys.exit(1)
        if settings.roi_label:
            logger.error("Sorry, --roi-label option doesn't work for .dlabel.nii seed inputs. Exiting.")
            sys.exit(1)
        if settings.mask:
            logger.error("Sorry, --mask option doesn't work for .dlabel.nii seed inputs. Exiting.")
            sys.exit(1)
        if not settings.func.type == 'cifti':
            logger.error("If <seed> is .dlabel.nii, the <func> needs to be a cifti file. Exiting.")
            sys.exit(1)

        ## parcellate and then right out the parcellations..
        cifti_parcellate_to_meants(settings)

    else:
        ## calculated the meants using numpy

        _ = ciftify.meants.calc_meants_with_numpy(settings, outputlabels = settings.outputlabels)


def cifti_parcellate_to_meants(settings):
    ''' use wb_command -cifti-parcellate to create meants..much faster '''
    with ciftify.utils.TempDir() as tempdir:
        ## parcellate and then right out the parcellations..
        if settings.func.path.endswith('dtseries.nii'):
            tmp_parcelated = os.path.join(tempdir, 'parcellated.ptseries.nii')
        if settings.func.path.endswith('dscalar.nii'):
            tmp_parcelated = os.path.join(tempdir, 'parcellated.pscalar.nii')
        ciftify.utils.run(['wb_command', '-cifti-parcellate',
            settings.func.path, settings.seed.path,
            'COLUMN', tmp_parcelated, '-include-empty'])
        ciftify.utils.run(['wb_command', '-cifti-convert', '-to-text',
            tmp_parcelated, settings.outputcsv,'-col-delim ","'])
        if settings.outputlabels:
            temp_wb_labels = os.path.join(tempdir, 'wb_labels.txt')
            ciftify.utils.run(['wb_command', '-cifti-label-export-table',
                settings.seed.path, '1',
                temp_wb_labels])
            ciftify.niio.wb_labels_to_csv(temp_wb_labels, csv_out= settings.outputlabels)


class UserSettings(MeantsSettings):
    def __init__(self, arguments):
        MeantsSettings.__init__(self, arguments)
        self.outputcsv = self.get_outputcsv(arguments['--outputcsv'])
        self.outputlabels = self.get_outputlabels(arguments['--outputlabels'])

    def check_output_path(self, path):
        ''' use ciftify function to ensure output is writable'''
        ciftify.utils.check_output_writable(path)
        return(path)

    def get_outputcsv(self, outputcsv):
        '''
        determine func and seed filetypes
        if outputcsv path doesn't exist, make one out of the func and seed names
        '''
        if not outputcsv:
            outputdir = os.path.dirname(self.func.path)
            outputcsv = os.path.join(outputdir,self.func.base + '_' + self.seed.base + '_meants.csv' )
        outputcsv = self.check_output_path(outputcsv)
        return(outputcsv)

    def get_outputlabels(self,outputlabels):
        '''if outputlabels where specified, check that they are writable '''
        if outputlabels:
            self.check_output_path(outputlabels)
        return(outputlabels)

def main():
    arguments = docopt(__doc__)
    debug = arguments['--debug']
    verbose = arguments['--verbose']

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    if verbose:
        ch.setLevel(logging.INFO)

    if debug:
        ch.setLevel(logging.DEBUG)

    logger.addHandler(ch)

    ## set up the top of the log
    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
        ciftify.utils.section_header('Starting ciftify_meants')))
    ciftify.utils.log_arguments(arguments)

    settings = UserSettings(arguments)

    ret = run_ciftify_meants(settings)

    logger.info(ciftify.utils.section_header('Done ciftify_meants'))
    sys.exit(ret)

if __name__ == '__main__':
    main()
