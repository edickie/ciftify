#!/usr/bin/env python3
"""
Produces a correlation map of the mean time series within the seed with
every voxel in the functional file.

Usage:
    ciftify_seed_corr [options] <func> <seed>

Arguments:
    <func>          functional data (nifti or cifti)
    <seed>          seed mask (nifti, cifti or gifti)

Options:
    --outputname STR   Specify the output filename
    --output-ts        Also output write the from the seed to text
    --roi-label INT    Specify the numeric label of the ROI you want a seedmap for
    --hemi HEMI        If the seed is a gifti file, specify the hemisphere (R or L) here
    --mask FILE        brainmask
    --fisher-z         Apply the fisher-z transform (arctanh) to the correlation map
    --weighted         compute weighted average timeseries from the seed map
    --use-TRs FILE     Only use the TRs listed in the file provided (TR's in file starts with 1)
    -v,--verbose       Verbose logging
    --debug            Debug logging
    -h, --help         Prints this message

DETAILS:
The default output filename is created from the <func> and <seed> filenames,
(i.e. func.dscalar.nii + seed.dscalar.nii --> func_seed.dscalar.nii)
and written to same folder as the <func> input. Use the '--outputname'
argument to specify a different outputname. The output datatype matches the <func>
input.

The mean timeseries is calculated using ciftify_meants, '--roi-label', '--hemi',
'--mask', and '--weighted' arguments are passed to it. See ciftify_meants '--help' for
more info on their usage. The timeseries output (*_meants.csv) of this step can be
saved to disk using the '--output-ts' option.

If a mask is provided with the ('--mask') option. (Such as a brainmask) it will be
applied to both the seed and functional file.

The '--use-TRs' argument allows you to calcuate the correlation maps from specific
timepoints (TRs) in the timeseries. This option can be used to exclude outlier
timepoints or to limit the calculation to a subsample of the timecourse
(i.e. only the beggining or end). It expects a text file containing the integer numbers
TRs to keep (where the first TR=1).

Written by Erin W Dickie
"""
import os
import sys
import subprocess
import tempfile
import shutil
import logging
import logging.config

import numpy as np
import scipy as sp
import nibabel as nib
from docopt import docopt

import ciftify
from ciftify.utils import run
from ciftify.meants import MeantsSettings

# Read logging.conf
logger = logging.getLogger('ciftify')
logger.setLevel(logging.DEBUG)

class UserSettings(MeantsSettings):
    def __init__(self, arguments):
        MeantsSettings.__init__(self, arguments)
        self.fisher_z = arguments['--fisher-z']
        self.output_prefix = self.get_output_prefix(arguments['--outputname'])
        self.outputcsv = self.get_outputcsv(arguments['--output-ts'])
        self.TR_file = self.get_TRfile(arguments['--use-TRs'])

    def get_output_prefix(self, outputname):
        '''
        output_prefix is outputname if it was specified
        if not, it is created from the func and seed input paths
        '''
        ## determine outbase if it has not been specified
        if outputname:
            output_prefix = outputname.replace('.nii.gz','').replace('.dscalar.nii','')
        else:
            outbase = '{}_{}'.format(self.func.base, self.seed.base)
            output_prefix = os.path.join(os.path.dirname(self.func.path), outbase)
        ## uses utils funciton to make sure the output is writable, will sys.exit with error if not the case
        ciftify.utils.check_output_writable(output_prefix)
        return(output_prefix)

    def get_outputcsv(self, output_ts):
        '''set outputcsv name if this is asked for'''
        if output_ts:
            outputcsv = '{}_meants.csv'.format(self.output_prefix)
        else:
            outputcsv = None
        return(outputcsv)

    def get_TRfile(self, TRfile):
        if TRfile:
            ciftify.utils.check_input_readable(TRfile)
        return(TRfile)


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
        ciftify.utils.section_header('Starting ciftify_seed_corr')))
    ciftify.utils.log_arguments(arguments)

    settings = UserSettings(arguments)

    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = run_ciftify_seed_corr(settings, tmpdir)

    logger.info(ciftify.utils.section_header('Done ciftify_seed_corr'))
    sys.exit(ret)

def run_ciftify_seed_corr(settings, tempdir):


    logger.debug('func: type: {}, base: {}'.format(settings.func.type, settings.func.base))
    logger.debug('seed: type: {}, base: {}'.format(settings.seed.type, settings.seed.base))

    if ".dlabel.nii" in settings.seed.path:
        logger.error("Sorry this function can't handle .dlabel.nii seeds")
        sys.exit(1)

    seed_ts = ciftify.meants.calc_meants_with_numpy(settings)
    logger.debug('seed_ts shape before reshaping {}'.format(seed_ts.shape))
    if ((len(seed_ts.shape) != 2) or (seed_ts.shape[0] != 1 and seed_ts.shape[1] !=1)):
        logger.error("Incorrect shape dimensions. May have forgotten to indicate the '--weighted' or '-roi-label' file")
        sys.exit(1)
    seed_ts = seed_ts.reshape(seed_ts.shape[0]*seed_ts.shape[1])
    logger.debug('seed_ts shape after reshaping {}'.format(seed_ts.shape))
    logger.debug('Writing output with prefix: {}'.format(settings.output_prefix))
    logger.debug('Writing meants: {}'.format(settings.outputcsv))
    logger.info('Using numpy to calculate seed-correlation')

    ## convert to nifti
    if settings.func.type == "cifti":
        func_fnifti = os.path.join(tempdir,'func.nii.gz')
        run(['wb_command','-cifti-convert','-to-nifti',settings.func.path, func_fnifti])
        func_data, outA, header, dims = ciftify.niio.load_nifti(func_fnifti)

    # import template, store the output paramaters
    if settings.func.type == "nifti":
        func_data, outA, header, dims = ciftify.niio.load_nifti(settings.func.path)

    if settings.mask:
        if settings.mask.type == "cifti":
            mask_fnifti = os.path.join(tempdir,'mask.nii.gz')
            run(['wb_command','-cifti-convert','-to-nifti', settings.mask.path, mask_fnifti])
            mask_data, _, _, _ = ciftify.niio.load_nifti(mask_fnifti)

        if settings.mask.type == "nifti":
            mask_data, _, _, _ = ciftify.niio.load_nifti(settings.mask.path)

    # decide which TRs go into the correlation
    if settings.TR_file:
        TR_file = np.loadtxt(settings.TR_file, int)
        TRs = TR_file - 1 # shift TR-list to be zero-indexed
    else:
        TRs = np.arange(dims[3])

    # get mean seed timeseries
    ## even if no mask given, mask out all zero elements..
    std_array = np.std(func_data, axis=1)
    std_nonzero = np.where(std_array > 0)[0]
    idx_mask = std_nonzero
    if settings.mask:
        idx_of_mask = np.where(mask_data > 0)[0]
        idx_mask = np.intersect1d(idx_mask, idx_of_mask)

    # create output array
    out = np.zeros([dims[0]*dims[1]*dims[2], 1])

    # look through each time series, calculating r
    for i in np.arange(len(idx_mask)):
        out[idx_mask[i]] = np.corrcoef(seed_ts[TRs], func_data[idx_mask[i], TRs])[0][1]

    # create the 3D volume and export
    out = out.reshape([dims[0], dims[1], dims[2], 1])
    out = nib.nifti1.Nifti1Image(out, outA)

    ## determine nifti filenames for the next two steps
    if settings.func.type == "nifti":
        if settings.fisher_z:
            nifti_corr_output = os.path.join(tempdir, 'corr_out.nii.gz')
            nifti_Zcorr_output = '{}.nii.gz'.format(settings.output_prefix)
        else:
           nifti_corr_output = '{}.nii.gz'.format(settings.output_prefix)
    if settings.func.type == "cifti":
        nifti_corr_output = os.path.join(tempdir, 'corr_out.nii.gz')
        if settings.fisher_z:
            nifti_Zcorr_output = os.path.join(tempdir, 'corrZ_out.nii.gz')
        else:
            nifti_Zcorr_output = nifti_corr_output

    # write out nifti
    out.to_filename(nifti_corr_output)

    # do fisher-z transform on values
    if settings.fisher_z:
        run(['wb_command', "-volume-math 'atanh(x)'", nifti_Zcorr_output,
            '-var', 'x', nifti_corr_output])

    if settings.func.type == "cifti":
        ## convert back
        run(['wb_command','-cifti-convert','-from-nifti',
            nifti_Zcorr_output,
            settings.func.path,
            '{}.dscalar.nii'.format(settings.output_prefix),
            '-reset-scalars'])


if __name__ == '__main__':
    main()
