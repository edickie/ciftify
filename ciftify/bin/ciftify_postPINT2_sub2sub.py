#!/usr/bin/env python3
"""
Will measure the distance from one subjects rois to all other subjects in mm on specified surfaces.

Usage:
  ciftify_postPINT2_sub2sub [options] <concatenated-pint> <output_sub2sub.csv>

Arguments:
    <concatenated-pint>    The concatenated PINT outputs (csv file)
    <output_sub2sub.csv>   The outputfile name

Options:
  --surfL SURFACE        The left surface on to measure distances on (see details)
  --surfR SURFACE        The right surface to to measure distances on (see details)
  --roiidx INT           Measure distances for only this roi (default will loop over all ROIs)
  --pvertex-col COLNAME  The column [default: pvertex] to read the personlized vertices
  --debug                Debug logging in Erin's very verbose style
  -n,--dry-run           Dry run
  --help                 Print help

DETAILS
Requires that all PINT summary files have already been comdined into one
"concatenated" input. by ciftify_postPINT1_concat.py

If surfL and surfR are not given, measurements will be done on the
HCP S1200 Average mid-surface.

Will output a csv with four columns. 'subid1', 'subid2', 'roiidx', 'distance'

Written by Erin W Dickie, May 5, 2017
"""
import random
import os
import sys
import logging
import logging.config

import pandas as pd
import numpy as np
import nibabel as nib
from docopt import docopt

import ciftify

config_path = os.path.join(os.path.dirname(__file__), "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

def main():
    global DEBUG
    global DRYRUN

    arguments = docopt(__doc__)
    allvertices_csv = arguments['<concatenated-pint>']
    output_sub2sub = arguments['<output_sub2sub.csv>']
    surfL = arguments['--surfL']
    surfR = arguments['--surfR']
    roiidx = arguments['--roiidx']
    pvertex_colname = arguments['--pvertex-col']
    DEBUG = arguments['--debug']
    DRYRUN = arguments['--dry-run']

    if DEBUG:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ciftify.utils.log_arguments(arguments)

    if not surfL:
        surfL = os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
            'S1200.L.midthickness_MSMAll.32k_fs_LR.surf.gii')
        surfR = os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
            'S1200.R.midthickness_MSMAll.32k_fs_LR.surf.gii')

    ## read in the concatenated results
    vertices_df = pd.read_csv(allvertices_csv)
    vertices_df = vertices_df.loc[:,['subid','hemi','roiidx',pvertex_colname]]

    if roiidx:
        roiidx = int(roiidx)
        if roiidx in vertices_df.loc[:,'roiidx']:
            result = calc_allroiidx_distances(vertices_df, roiidx, surfL, surfR, pvertex_colname)
        else:
            logger.critical("roiidx argument given is not in the concatenated df")
            sys.exit(1)
    else:
        all_rois = vertices_df.roiidx.unique()
        all_sub2sub = (calc_allroiidx_distances(vertices_df, roi, surfL, surfR, pvertex_colname) for roi in all_rois)
        result = pd.concat(all_sub2sub, ignore_index=True)

    ### write out the resutls to a csv
    result.to_csv(output_sub2sub,
                  columns = ['subid1','subid2','roiidx','distance'],
                  index = False)

def calc_subdistances_distances(roidf, surf, subid, pvertex_colname):
    '''
    calculates all distances from one subject to the rest for one roi
    returns a dataframe with columns: subid1, subid2, roiidx, distances'
    '''
    ## read the subids vertex from the roidf
    pvertex1 = int(roidf.loc[roidf.loc[:,'subid']==subid, pvertex_colname])

    ## set up a new df
    thisdf = roidf.rename(columns={'subid': 'subid2', pvertex_colname: 'pvertex2'})
    thisdf['subid1'] = subid
    thisdf['pvertex1'] = pvertex1

    ## calculate the distances
    distances = ciftify.niio.get_surf_distances(surf, pvertex1)
    thisdf.loc[:,'distance'] =  distances[thisdf.loc[:,'pvertex2'],0]
    ## set cases were ivertices are the same to distance 0
    thisdf.loc[thisdf.loc[:,'pvertex2'] == thisdf.loc[:,'pvertex1'],'distance'] = 0

    ## trim and return the result
    result = thisdf.loc[:,['subid1','subid2','roiidx','distance']]
    return(result)

def calc_allroiidx_distances(vertices_df, roi, surfL, surfR, pvertex_colname):
    '''
    loop over all subjects calculating distances for one roi
    '''
    ## determine the surface for measurment
    hemi = vertices_df.loc[vertices_df.roiidx==roi,'hemi'].values[0]
    if hemi == "L": surf = surfL
    if hemi == "R": surf = surfR

    ## subset the dataframe
    roidf = vertices_df.loc[vertices_df.roiidx==roi,:]

    ## run all the subjects and return into a tupley thing of results
    all_dfs = (calc_subdistances_distances(roidf, surf, subid, pvertex_colname) for subid in vertices_df.subid.unique())
    ## concatenate all the results
    roi_sub2sub = pd.concat(all_dfs, ignore_index=True)
    return(roi_sub2sub)


if __name__ == "__main__":
    main()
