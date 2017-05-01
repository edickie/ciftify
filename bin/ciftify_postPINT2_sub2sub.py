#!/usr/bin/env python
"""
Will measure the distance from one subjects rois to all other subjects in mm on specified surfaces.

Usage:
  ciftify_postPINT2_sub2sub.py [options] <subid> <concatenated-pint> <outputdir>

Arguments:
    <subid>                The subject id of the subject to compare to all other subjects
    <concatenated-pint>    The concatenated PINT outputs (csv file)
    <outputdir>            The base folder for the outputs

Options:
  --surfL SURFACE            The left surface on to measure distances on (see details)
  --surfR SURFACE            The right surface to to measure distances on (see details)
  --outputcsv FILE           The path to the output
  --debug                    Debug logging in Erin's very verbose style
  -n,--dry-run               Dry run
  --help                     Print help

DETAILS
Requires that all PINT summary files have already been comdined into one "concatenated" input.

If surfL and surfR are not given, measurements will be done on the HCP s900 Average mid-surface.

Writes the outputs back into the outputdir/<subid>_ivertex2subs_mm.csv

Written by Erin W Dickie, April 28, 2017
"""
import ciftify
import numpy as np
import nibabel as nib
import random
import os
import sys
import tempfile
import shutil
import subprocess
import pandas as pd
import nibabel.gifti.giftiio
from cifity.docopt import docopt

## function for doing stuffs in the shell
def docmd(cmdlist):
    "sends a command (inputed as a list) to the shell"
    if DEBUG: print ' '.join(cmdlist)
    if not DRYRUN: subprocess.call(cmdlist)

## measuring distance
def get_surf_distances(surf, orig_vertex, radius_search):
    '''
    uses wb_command -surface-geodesic-distance command to measure
    distance between two vertices on the surface
    '''
    with ciftify.utilities.TempDir() as tmpdir:
        surf_distance = os.path.join(tmpdir, "distancecalc.shape.gii")
        docmd(['wb_command', '-surface-geodesic-distance',
                surf, str(orig_vertex), surf_distance,
                '-limit', str(radius_search)])
        distances = ciftify.utilities.load_gii_data(surf_distance)
    return(distances)

def main():
    global DEBUG
    global DRYRUN

    arguments = docopt(__doc__)
    subid = arguments['<subid>']
    allvertices_csv = arguments['<concatenated-pint>']
    outputdir = arguments['<outputdir>']
    surfL = arguments['<surfL>']
    surfR = arguments['<surfR>']
    DEBUG = arguments['--debug']
    DRYRUN = arguments['--dry-run']

    if DEBUG: print(arguments)

    ## make the tempdir
    tmpdir = tempfile.mkdtemp()

    ## read in the thing
    vertices_df = pd.read_csv(allvertices_csv)

    ## get the ivertex columns
    ivertex_columns = [x for x in vertices_df.columns if "ivertex" in x]
    radius_search = 100

    ## set up my fancy long table
    ivertex_thissub = [x for x in ivertex_columns if subid in x]
    ivertex_othersubs = list(set(ivertex_columns)-set(ivertex_thissub))
    ivertex_othersubs.sort()
    result = pd.DataFrame({"subid1": ivertex_thissub*(len(ivertex_othersubs)), "subid2": ivertex_othersubs})
    cols_to_write=['subid1','subid2']

    ## loop over all vertices
    for vidx in vertices_df.index.tolist():
        ## determine the roiidx and the hemisphere (surface)
        roiidx = vertices_df.loc[vidx,'roiidx']

        if vertices_df.loc[vidx,'hemi'] is 'L': surf = surfL
        if vertices_df.loc[vidx,'hemi'] is 'R': surf = surfR

        result.loc[:,'roiidx' + str(roiidx)] = -999
        cols_to_write.append('roiidx' + str(roiidx))
        ## loop over all pairs of PINT result outputs
        for idx in result.index:

            ## read the vertex numbers
            ivertexcol_x = result.loc[idx,'subid1']
            ivertexcol_y = result.loc[idx,'subid2']
            vertex_x = int(vertices_df.loc[vertices_df['roiidx']==roiidx,ivertexcol_x])
            vertex_y= int(vertices_df.loc[vertices_df['roiidx']==roiidx,ivertexcol_y])

            ## if this is the first one - or if vertex_x has changed - load the distances
            if idx == 0:
                distances = get_surf_distances(surf, vertex_x, radius_search, tmpdir)
            elif ivertexcol_x != result.loc[idx - 1,'subid1']:
                distances = get_surf_distances(surf, vertex_x, radius_search, tmpdir)

            ## if vertex_x is equal to vertex_y set to 0
            ## otherwise read the distance from the vertex column
            if vertex_x == vertex_y:
                result.loc[idx,'roiidx' + str(roiidx)] = 0
            else:
                result.loc[idx,'roiidx' + str(roiidx)] = distances[vertex_y,0]

    ### write out the resutls to a csv
    docmd(['mkdir','-p', os.path.join(outputdir,subid)])
    result.to_csv(os.path.join(outputdir,subid,"{}_ivertex2subs_mm.csv".format(subid)),
                  columns = cols_to_write, index = False)

    #get rid of the tmpdir
    shutil.rmtree(tmpdir)

if __name__ == "__main__":
    main()
