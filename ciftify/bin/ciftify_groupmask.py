#!/usr/bin/env python3
"""
Makes a group mask (excluding low signal voxels) for statistical comparisons
from input cifti files.

Usage:
  ciftify_groupmask [options] <output.dscalar.nii> <input.dtseries.nii>...

Arguments:
    <output.dscalar.nii>  Output cifti mask
    <input.dtseries.nii>  Input cifti files

Options:
  --percent-thres <Percent>  Lower threshold [default: 5] applied to all files to make mask.
  --cifti-column <column>    Lower threshold [default: 1] applied to all files to make mask.
  --debug                    Debug logging in Erin's very verbose style
  --help                     Print help

DETAILS
Take the specified column from each input file and threshold and binarizes it get
a mask, for each subject, of valid voxels (i.e. voxels of signal above the percentile cut-off).

Then, for each voxel/vertex we take the minimum value across the population.
Therefore our mask contains 1 for each vertex that is valid for all participants and 0 otherwise.

Written by Erin W Dickie, April 15, 2016
"""
import sys
import subprocess
import os
import glob
import logging
import logging.config

from docopt import docopt

import ciftify

# Read logging.conf
config_path = os.path.join(os.path.dirname(__file__), "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))



## function for getting a percentile value from a cifti file
def get_cifti_percentile(ciftifile, percentile, column):
    pctl = ciftify.utils.get_stdout(['wb_command', '-cifti-stats',
                      ciftifile,
                      '-percentile', str(percentile),
                      '-column', str(column)])
    pctl = pctl.replace('\n','')
    return pctl

def main():

    arguments = docopt(__doc__)
    outputmask = arguments['<output.dscalar.nii>']
    filelist = arguments['<input.dtseries.nii>']
    column = arguments['--cifti-column']
    percentile = arguments['--percent-thres']
    debug = arguments['--debug']

    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
        ciftify.utils.section_header('Starting ciftify_groupmask')))
    ciftify.utils.log_arguments(arguments)

    with ciftify.utils.TempDir() as tempdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tempdir,
                    os.uname()[1]))

        ## start the merge command
        merge_cmd = ['wb_command', '-cifti-merge',
           os.path.join(tempdir, 'mergedfile.dscalar.nii')]

        for i in range(len(filelist)):
            '''
            for each file, threshold and binarize then add to the merge_cmd filelist
            '''
            ciftifile = filelist[i]
            pctl = get_cifti_percentile(ciftifile, percentile, column)
            ciftify.utils.run(['wb_command', '-cifti-math', 'x > {}'.format(pctl),
                   os.path.join(tempdir, 'tmp{}.dscalar.nii'.format(i)),
                   '-var','x',ciftifile, '-select', '1', str(column)])
            merge_cmd.append('-cifti')
            merge_cmd.append(os.path.join(tempdir, 'tmp{}.dscalar.nii'.format(i)))

        ## merge the files and take the minimum (i.e. 100 good voxels = mask)
        ciftify.utils.run(merge_cmd)
        ciftify.utils.run(['wb_command', '-cifti-reduce',
              os.path.join(tempdir, 'mergedfile.dscalar.nii'),
              'MIN', outputmask])

        logger.info(ciftify.utils.section_header('Done ciftify_groupmask'))

if __name__ == "__main__":
    main()
