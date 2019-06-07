#!/usr/bin/env python3
"""
Will concatenate PINT output summaries into one concatenated file.
Also, calculates all distances from template vertex on standard surface

Usage:
  ciftify_postPINT1_concat [options] <concatenated-pint> <PINT_summary.csv>...

Arguments:
    <concatenated-pint>    The concatenated PINT output to write
    <PINT_summary.csv>     The PINT summary files (repeatable)

Options:
  --surfL SURFACE            The left surface on to measure distances on (see details)
  --surfR SURFACE            The right surface to to measure distances on (see details)
  --no-distance-calc         Will not calculate the distance from the template vertex
  --pvertex-col COLNAME      The column [default: pvertex] to read the personlized vertices
  --debug                    Debug logging in Erin's very verbose style
  -n,--dry-run               Dry run
  --help                     Print help

DETAILS
If surfL and surfR are not given, measurements will be done on the
HCP S1200 Average mid-surface.

In old versions of PINT (2017 and earlier) the pvertex colname was "ivertex".
Use the option '--pvertex-col ivertex' to process these files.

Written by Erin W Dickie, April 28, 2017
"""
import os
import sys
import logging
import logging.config

import pandas as pd
from docopt import docopt

import ciftify

# Read logging.conf
config_path = os.path.join(os.path.dirname(ciftify.config.find_ciftify_global()), 'bin', "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

def main():
    global DEBUG
    global DRYRUN

    arguments = docopt(__doc__)
    allvertices_csv = arguments['<concatenated-pint>']
    summary_csvs = arguments['<PINT_summary.csv>']
    surfL = arguments['--surfL']
    surfR = arguments['--surfR']
    NO_TVERTEX_MM = arguments['--no-distance-calc']
    pvertex_colname = arguments['--pvertex-col']
    DEBUG = arguments['--debug']
    DRYRUN = arguments['--dry-run']

    if DEBUG:
        logger.setLevel(logging.INFO)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.WARNING)

    logger.info('{}{}'.format(ciftify.utils.pint_logo(),
                ciftify.utils.section_header("Starting ciftify_postPINT1_concat")))
    ciftify.utils.log_arguments(arguments)

    ## read all the dfs into a tupley thing
    all_dfs = (read_process_PINT_summary(f, pvertex_colname) for f in summary_csvs)
    ## concatenate all the summarycvs
    concatenated_df = pd.concat(all_dfs, ignore_index=True)
    concat_df_columns = ['subid', 'hemi','NETWORK', 'roiidx','tvertex',pvertex_colname,
                            'dist_49','vertex_48']

    if NO_TVERTEX_MM:
        ## if done, write to file
        concatenated_df.to_csv(allvertices_csv, index = False, columns = concat_df_columns)
    else:
        ## define the surface fo measuring..
        distance_col = 'std_distance'
        if not surfL:
            surfL = os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                'S1200.L.midthickness_MSMAll.32k_fs_LR.surf.gii')
            surfR = os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                'S1200.R.midthickness_MSMAll.32k_fs_LR.surf.gii')

        ## for each roi, calculated the distance from the tvertex to the ivertex
        concatenated_df[distance_col] = -99.0
        for roi in concatenated_df.roiidx.unique():
            hemi = concatenated_df.hemi[concatenated_df.roiidx==roi].unique()[0]
            orig_vertex = concatenated_df.tvertex[concatenated_df.roiidx==roi].unique()[0]
            if hemi == "L": surf = surfL
            if hemi == "R": surf = surfR
            roi_distances =  ciftify.niio.get_surf_distances(surf, orig_vertex)
            roi_idx = concatenated_df.loc[concatenated_df.roiidx==roi].index
            concatenated_df.loc[roi_idx,distance_col] = roi_distances[concatenated_df.loc[roi_idx,pvertex_colname].values]

        ## replace any values where ivertex == tvertex with a 0 (tends to be -1)
        concatenated_df.loc[concatenated_df.loc[:, pvertex_colname] == concatenated_df.tvertex,distance_col] = 0

        ## write to file
        concat_df_columns.append(distance_col)
        concatenated_df.to_csv(allvertices_csv, index = False, columns = concat_df_columns)

    logger.info(ciftify.utils.section_header('Done ciftify_postPINT1_concat'))

def read_process_PINT_summary(inputcsv, pvertex_colname):
    '''
    reads in one PINT summary csv and does a little cleaning of the result..
    add an extra column that is only the PINT output prefix
    '''
    thisdf = pd.read_csv(inputcsv)
    this_subid = os.path.basename(inputcsv)
    this_subid = this_subid.replace('_summary.csv','')
    thisdf['subid'] = this_subid
    if 'dist_49' not in thisdf.columns:
        thisdf['dist_49'] = 0
        thisdf['vertex_48'] = thisdf.loc[:,pvertex_colname]
    output_df = thisdf.loc[:,('subid', 'hemi','NETWORK', 'roiidx','tvertex',pvertex_colname,'dist_49','vertex_48')]
    return(output_df)



if __name__ == '__main__':
    main()
