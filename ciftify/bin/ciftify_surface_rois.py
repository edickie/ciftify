#!/usr/bin/env python3
"""
Runs wb_command -surface-geodesic-rois to make rois on left and right surfaces then combines
them into one dscalar file.

Usage:
    ciftify_surface_rois [options] <inputcsv> <radius> <L.surf.gii> <R.surf.gii> <output.dscalar.nii>

Arguments:
    <inputcsv>            csv to read vertex list and hemisphere (and optional labels) from
    <radius>              radius for geodesic rois (mm)
    <L.surf.gii>          Corresponding Left surface
    <R.surf.gii>          Corresponding Right surface file
    <output.dscalar.nii>  output dscalar file

Options:
    --vertex-col COLNAME   Column name [default: vertex] for column with vertices
    --hemi-col COLNAME     Column name [default: hemi] where hemisphere is given as L or R
    --labels-col COLNAME   Values in this column will be multiplied by the roi
    --overlap-logic LOGIC  Overlap logic [default: ALLOW] for wb_command
    --gaussian             Build a gaussian instead of a circular ROI.
    --probmap              Divide the map by the number to inputs so that the sum is meaningful.
    --debug                Debug logging
    -v,--verbose           Verbose logging
    -h, --help             Prints this message

DETAILS
This reads the vertex ids, from which to center ROIs from a csv file (with a header)
with two required columns ("vertex", and "hemi").

Example:
  vertex, hemi,
  6839, L
  7980, R
  ...

The column (header) names can be indicated with the ('--vertex-col', and '--hemi-col')
arguments. Additionally, a third column can be given of interger labels to apply to
these ROIs, indicated by the '--labels-col' option.

The  argument to -overlap-logic must be one of ALLOW, CLOSEST, or EXCLUDE.
 ALLOW is the default, and means that ROIs are treated independently and may overlap.
 CLOSEST means that ROIs may not overlap, and that no ROI contains vertices that are closer to a different seed vertex.
 EXCLUDE means that ROIs may not overlap, and that any vertex within range of more than one ROI does not belong to any ROI.

Written by Erin W Dickie, June 3, 2016
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
import nibabel.gifti.giftiio
import pandas as pd
from docopt import docopt

import ciftify
from ciftify.utils import run

config_path = os.path.join(os.path.dirname(ciftify.config.find_ciftify_global()), 'bin', "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

def run_ciftify_surface_rois(arguments, tmpdir):
    inputcsv = arguments['<inputcsv>']
    surfL = arguments['<L.surf.gii>']
    surfR = arguments['<R.surf.gii>']
    radius = arguments['<radius>']
    output_dscalar = arguments['<output.dscalar.nii>']
    vertex_col = arguments['--vertex-col']
    hemi_col = arguments['--hemi-col']
    labels_col = arguments['--labels-col']
    gaussian = arguments['--gaussian']
    overlap_logic = arguments['--overlap-logic']
    probmap = arguments['--probmap']

    ## read in the inputcsv
    try:
        df = pd.read_csv(inputcsv)
    except:
        logger.critical("Could not load csv {}".format(inputcsv))
        sys.exit(1)

    ## check that vertex-col and hemi-col exist
    if vertex_col not in df.columns:
        logger.error("Vertex column '{}' not in csv".format(vertex_col))
        sys.exit(1)

    if hemi_col not in df.columns:
        logger.error("Hemisphere column '{}' not in csv".format(hemi_col))
        sys.exit(1)

    for hemisphere in ['L','R']:

        surf = surfL if hemisphere == 'L' else surfR

        ## from the temp text build - func masks and target masks
        rois_2D = os.path.join(tmpdir,'rois_{}_2D.func.gii'.format(hemisphere))
        rois_1D = os.path.join(tmpdir, 'rois_{}_1D.shape.gii'.format(hemisphere))

        ## right the L and R hemisphere vertices from the table out to temptxt
        vertex_list = os.path.join(tmpdir, 'vertex_list.txt')
        vertices = df.loc[df[hemi_col] == hemisphere, vertex_col]
        logger.info('{} vertices are: {}'.format(hemisphere, vertices))
        if len(vertices) > 0:
            vertices.to_csv(vertex_list,sep='\n',index=False, header = False)

            if gaussian:
                run(['wb_command', '-surface-geodesic-rois', surf,
                       str(radius), vertex_list, rois_2D, '-gaussian',
                       str(radius)])
            else:
                run(['wb_command', '-surface-geodesic-rois', surf,
                    str(radius),  vertex_list, rois_2D,
                    '-overlap-logic', overlap_logic])

            if labels_col:
                run(['wb_command -metric-math "x*0"', rois_1D,
                       '-var', 'x', rois_2D, '-column', '1'], suppress_stdout=True)

                for i, label in enumerate(df.loc[df[hemi_col] == hemisphere, labels_col]):
                    run(['wb_command -metric-math "((x*{}) + y)"'.format(label), rois_1D,
                           '-var', 'x', rois_2D, '-column', '{}'.format(i + 1),
                          '-var', 'y', rois_1D], suppress_stdout=True)
            else:
                run(['wb_command', '-metric-reduce',
                      rois_2D, 'SUM', rois_1D])

        else:
            pd.Series([1]).to_csv(vertex_list,sep='\n',index=False, header = False)
            run(['wb_command', '-surface-geodesic-rois', surf,
                str(radius),  vertex_list, rois_2D])
            run(['wb_command -metric-math "x*0"', rois_1D,
                   '-var', 'x', rois_2D, '-column', '1'], suppress_stdout=True)

    if probmap:
        mergedoutput = os.path.join(tmpdir,"mergedoutput.dscalar.nii")
    else:
        mergedoutput = output_dscalar
    # combine result surfaces into a cifti file
    run(['wb_command', '-cifti-create-dense-scalar', mergedoutput,
           '-left-metric', os.path.join(tmpdir,'rois_L_1D.shape.gii'),
           '-right-metric', os.path.join(tmpdir,'rois_R_1D.shape.gii')])

    if probmap:
        run(['wb_command -cifti-math "(x/{})"'.format(len(df)),
                output_dscalar,
                '-var', 'x', mergedoutput ], suppress_stdout=True)

def main():
    arguments  = docopt(__doc__)
    verbose      = arguments['--verbose']
    debug        = arguments['--debug']

    logger.setLevel(logging.WARNING)

    if verbose:
        logger.setLevel(logging.INFO)
        logging.getLogger('ciftify').setLevel(logging.INFO)

    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ## set up the top of the log
    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
        ciftify.utils.section_header('Starting ciftify_surface_rois')))
    ciftify.utils.log_arguments(arguments)

    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # logger.setFormatter(formatter)

    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir, os.uname()[1]))
        ret = run_ciftify_surface_rois(arguments, tmpdir)

    logger.info(ciftify.utils.section_header('Done ciftify_surface_rois'))
    sys.exit(ret)

if __name__=='__main__':
    main()
