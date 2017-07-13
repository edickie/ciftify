#!/usr/bin/env python
"""
Will measure the distance from one subjects rois to all other subjects in mm on specified surfaces.

Usage:
  ciftify_postPINT2_sub2sub.py [options] <concatenated-pint> <output_sub2sub.csv>

Arguments:
    <concatenated-pint>    The concatenated PINT outputs (csv file)
    <output_sub2sub.csv>   The outputfile name

Options:
  --surfL SURFACE     The left surface on to measure distances on (see details)
  --surfR SURFACE     The right surface to to measure distances on (see details)
  --roiidx INT        Measure distances for only this roi (default will loop over all ROIs)
  --debug             Debug logging in Erin's very verbose style
  -n,--dry-run        Dry run
  --help              Print help

DETAILS
Requires that all PINT summary files have already been comdined into one
"concatenated" input. by ciftify_postPINT1_concat.py

If surfL and surfR are not given, measurements will be done on the
HCP s900 Average mid-surface.

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

## measuring distance
def get_surf_distances(surf, orig_vertex, radius_search=100):
    '''
    uses wb_command -surface-geodesic-distance command to measure
    distance between two vertices on the surface
    '''
    global DEBUG
    global DRYRUN

    with ciftify.utilities.TempDir() as tmpdir:
        surf_distance = os.path.join(tmpdir, "distancecalc.shape.gii")
        ciftify.utilities.run(['wb_command', '-surface-geodesic-distance',
                surf, str(orig_vertex), surf_distance,
                '-limit', str(radius_search)], dryrun=DRYRUN, echo=DEBUG)
        distances = ciftify.utilities.load_gii_data(surf_distance)
    return(distances)

def calc_subdistances_distances(roidf, surf, subid):
    '''
    calculates all distances from one subject to the rest for one roi
    returns a dataframe with columns: subid1, subid2, roiidx, distances'
    '''
    ## read the subids vertex from the roidf
    ivertex1 = int(roidf.loc[roidf.loc[:,'subid']==subid,'ivertex'])

    ## set up a new df
    thisdf = roidf.rename(columns={'subid': 'subid2', 'ivertex': 'ivertex2'})
    thisdf['subid1'] = subid
    thisdf['ivertex1'] = ivertex1

    ## calculate the distances
    distances = get_surf_distances(surf, ivertex1)
    thisdf.loc[:,'distance'] =  distances[thisdf.loc[:,'ivertex2'],0]
    ## set cases were ivertices are the same to distance 0
    thisdf.loc[thisdf.loc[:,'ivertex2'] == thisdf.loc[:,'ivertex1'],'distance'] = 0

    ## trim and return the result
    result = thisdf.loc[:,['subid1','subid2','roiidx','distance']]
    return(result)

def calc_allroiidx_distances(vertices_df, roi, surfL, surfR):
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
    all_dfs = (calc_subdistances_distances(roidf, surf, subid) for subid in vertices_df.subid.unique())
    ## concatenate all the results
    roi_sub2sub = pd.concat(all_dfs, ignore_index=True)
    return(roi_sub2sub)

def main():
    global DEBUG
    global DRYRUN

    arguments = docopt(__doc__)
    allvertices_csv = arguments['<concatenated-pint>']
    output_sub2sub = arguments['<output_sub2sub.csv>']
    surfL = arguments['--surfL']
    surfR = arguments['--surfR']
    roiidx = arguments['--roiidx']
    DEBUG = arguments['--debug']
    DRYRUN = arguments['--dry-run']

    if DEBUG:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

        logger.info(arguments)

    if not surfL:
        surfL = os.path.join(ciftify.config.find_HCP_S900_GroupAvg(),
            'S900.L.midthickness_MSMAll.32k_fs_LR.surf.gii')
        surfR = os.path.join(ciftify.config.find_HCP_S900_GroupAvg(),
            'S900.R.midthickness_MSMAll.32k_fs_LR.surf.gii')

    ## read in the concatenated results
    vertices_df = pd.read_csv(allvertices_csv)
    vertices_df = vertices_df.loc[:,['subid','hemi','roiidx','ivertex']]

    if roiidx:
        if roiidx in vertices_df.loc[:,'roiidx']:
            result = calc_allroiidx_distances(vertices_df, roiidx, surfL, surfR)
        else:
            logger.critical("roiidx argument given is not in the concatenated df")
            sys.exit(1)
    else:
        all_rois = vertices_df.roiidx.unique()
        all_sub2sub = (calc_allroiidx_distances(vertices_df, roi, surfL, surfR) for roi in all_rois)
        result = pd.concat(all_sub2sub, ignore_index=True)

    ### write out the resutls to a csv
    result.to_csv(output_sub2sub,
                  columns = ['subid1','subid2','roiidx','distance'],
                  index = False)

if __name__ == "__main__":
    main()
