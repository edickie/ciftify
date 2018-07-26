#!/usr/bin/env python3
"""
Takes a cifti map ('dscalar.nii') and outputs a csv of results

Usage:
    ciftify_peaktable [options] <func.dscalar.nii>

Arguments:
    <func.dscalar.nii>    Input map.

Options:
    --min-threshold MIN    the largest value [default: -2.85] to consider for being a minimum
    --max-threshold MAX    the smallest value [default: 2.85] to consider for being a maximum
    --area-threshold MIN   threshold [default: 20] for surface cluster area, in mm^2
    --surface-distance MM  minimum distance in mm [default: 20] between extrema of the same type.
    --volume-distance MM   minimum distance in mm [default: 20] between extrema of the same type.

    --outputbase prefix    Output prefix (with path) to output documents
    --no-cluster-dlabel    Do not output a dlabel map of the clusters

    --left-surface GII     Left surface file (default is HCP S1200 Group Average)
    --right-surface GII    Right surface file (default is HCP S1200 Group Average)
    --left-surf-area GII   Left surface vertex areas file (default is HCP S1200 Group Average)
    --right-surf-area GII  Right surface vertex areas file (default is HCP S1200 Group Average)

    --debug                Debug logging
    -n,--dry-run           Dry run
    -h, --help             Prints this message

DETAILS
Note: at the moment generates separate outputs for surface.
Uses -cifti-separate in combination with FSL's clusterize to get information from
the subcortical space.

Ouptputs a results csv with several headings:
  + clusterID: Integer for the cluster this peak is from (corresponds to dlabel.nii)
  + hemisphere: Hemisphere the peak is in (L or R)
  + vertex: The vertex id
  + x,y,z: The nearest x,y,z coordinates to the vertex
  + value: The intensity (value) at that vertex in the func.dscalar.nii
  + area: The surface area of the cluster (i.e. clusterID)
  + DKT: The label from the freesurfer anatomical atlas (aparc) at the vertex
  + DKT_overlap: The proportion of the cluster (clusterID) that overlaps with the DKT atlas label
  + Yeo7: The label from the Yeo et al 2011 7 network atlas at this peak vertex
  + Yeo7_overlap: The proportion of the cluster (clusterID) that overlaps with this Yeo7 network label
  + MMP: The label from the Glasser et al (2016) Multi-Modal Parcellation
  + MMP_overlap: The proportion of the cluster (clusterID) that overlaps with the MMP atlas label

If no surfaces of surface area files are given. The midthickness surfaces from
the HCP S1200 Group Mean will be used, as well as it's vertex-wise
surface area infomation.

Default name for the output csv taken from the input file.
i.e. func.dscalar.nii --> func_peaks.csv

Unless the '--no-cluster-dlabel' flag is given, a map of the clusters with be
be written to the same folder as the outputcsv to aid in visualication of the results.
This dlable map with have a name ending in '_clust.dlabel.nii'.
(i.e. func_peaks.csv & func_clust.dlabel.nii)

Atlas References:
Yeo, BT. et al. 2011. 'The Organization of the Human Cerebral Cortex
Estimated by Intrinsic Functional Connectivity.' Journal of Neurophysiology
106 (3): 1125-65.

Desikan, RS.et al. 2006. 'An Automated Labeling System for Subdividing the
Human Cerebral Cortex on MRI Scans into Gyral Based Regions of Interest.'
NeuroImage 31 (3): 968-80.

Glasser, MF. et al. 2016. 'A Multi-Modal Parcellation of Human Cerebral Cortex.'
Nature 536 (7615): 171-78.

Written by Erin W Dickie, Last updated August 27, 2017
"""

from __future__ import division

import os
import sys
import numpy as np
import scipy as sp
import nibabel as nib
import nibabel.gifti.giftiio
import pandas as pd
import ciftify
import logging
import logging.config
from docopt import docopt

import ciftify
from ciftify.utils import run
from ciftify.niio import load_hemisphere_data

config_path = os.path.join(os.path.dirname(ciftify.config.find_ciftify_global()), 'bin', "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

def run_ciftify_peak_table(tmpdir):
    global DRYRUN

    arguments = docopt(__doc__)
    data_file = arguments['<func.dscalar.nii>']
    surf_distance = arguments['--surface-distance']
    volume_distance = arguments['--volume-distance']
    min_threshold = arguments['--min-threshold']
    max_threshold = arguments['--max-threshold']
    area_threshold = arguments['--area-threshold']
    outputbase = arguments['--outputbase']
    dont_output_clusters = arguments['--no-cluster-dlabel']
    debug = arguments['--debug']
    DRYRUN = arguments['--dry-run']

    logger.setLevel(logging.WARNING)

    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ## set up the top of the log
    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
        ciftify.utils.section_header('Starting ciftify_peaktable')))
    ciftify.utils.log_arguments(arguments)

    if not os.path.exists(data_file):
        logger.critical('Input map {} not found.\n'\
            'File does not exist, or folder permissions prevent seeing it'.format(data_file))
        sys.exit(1)

    atlas_settings = define_atlas_settings()
    ## if not outputname is given, create it from the input dscalar map
    if not outputbase:
        outputbase = data_file.replace('.dscalar.nii','')

    outputcsv_cortex = '{}_cortex.csv'.format(outputbase)
    outputcsv_sub = '{}_subcortical.csv'.format(outputbase)

    ## grab surface files from the HCP group average if they are not specified
    surf_settings = define_surface_settings(arguments, tmpdir)

    ## run wb_command -cifti-extrema to find the peak locations
    extrema_dscalar = os.path.join(tmpdir,'extrema.dscalar.nii')
    run(['wb_command','-cifti-extrema',
           data_file,
           str(surf_distance), str(volume_distance),'COLUMN',
           extrema_dscalar,
           '-left-surface', surf_settings['L']['surface'],
           '-right-surface', surf_settings['R']['surface'],
           '-threshold', str(min_threshold), str(max_threshold)])

    ## also run clusterize with the same settings to get clusters
    pcluster_dscalar = os.path.join(tmpdir,'pclusters.dscalar.nii')

    wb_cifti_clusters(data_file, pcluster_dscalar, surf_settings,
                      max_threshold, area_threshold,
                      less_than = False, starting_label=1)

    ## load both cluster files to determine the max value
    pos_clust_data = ciftify.niio.load_concat_cifti_surfaces(pcluster_dscalar)
    max_pos = int(np.max(pos_clust_data))

    ## now get the negative clusters
    ncluster_dscalar = os.path.join(tmpdir,'nclusters.dscalar.nii')
    wb_cifti_clusters(data_file, ncluster_dscalar, surf_settings,
                      min_threshold, area_threshold,
                      less_than = True, starting_label=max_pos + 1)

    ## add the positive and negative together to make one cluster map
    clusters_dscalar = os.path.join(tmpdir,'clusters.dscalar.nii')
    run(['wb_command', '-cifti-math "(x+y)"',
        clusters_dscalar,
        '-var','x',pcluster_dscalar, '-var','y',ncluster_dscalar])

    ## multiply the cluster labels by the extrema to get the labeled exteama
    lab_extrema_dscalar = os.path.join(tmpdir,'lab_extrema.dscalar.nii')
    run(['wb_command', '-cifti-math "(abs(x*y))"',
        lab_extrema_dscalar,
        '-var','x',clusters_dscalar, '-var','y',extrema_dscalar])

    ## run left and right dfs... then concatenate them
    dfL = build_hemi_results_df(surf_settings['L'], atlas_settings,
                              data_file, lab_extrema_dscalar, clusters_dscalar)
    dfR = build_hemi_results_df(surf_settings['R'], atlas_settings,
                              data_file, lab_extrema_dscalar, clusters_dscalar)
    df = dfL.append(dfR, ignore_index = True)

    ## write the table out to the outputcsv
    output_columns = ['clusterID','hemisphere','vertex', 'peak_value', 'area']
    decimals_out = {"clusterID":0, 'peak_value':3, 'area':0}
    for atlas in atlas_settings.keys():
        atlas_name = atlas_settings[atlas]['name']
        output_columns.append(atlas_name)
        output_columns.append('{}_overlap'.format(atlas_name))
        decimals_out['{}_overlap'.format(atlas_name)] = 3

    df = df.round(decimals_out)
    df.to_csv(outputcsv_cortex,
          columns = output_columns,index=False)

    if not dont_output_clusters:
        cluster_dlabel = '{}_clust.dlabel.nii'.format(outputbase)
        empty_labels = os.path.join(tmpdir, 'empty_labels.txt')
        run('touch {}'.format(empty_labels))
        run(['wb_command', '-cifti-label-import',
            clusters_dscalar, empty_labels, cluster_dlabel])

    ## run FSL's cluster on the subcortical bits
    ## now to run FSL's cluster on the subcortical bits
    cinfo = ciftify.niio.cifti_info(data_file)
    if cinfo['maps_to_volume']:
        subcortical_vol = os.path.join(tmpdir, 'subcortical.nii.gz')
        run(['wb_command', '-cifti-separate', data_file, 'COLUMN', '-volume-all', subcortical_vol])
        fslcluster_cmd = ['cluster',
            '--in={}'.format(subcortical_vol),
            '--thresh={}'.format(max_threshold),
            '--peakdist={}'.format(volume_distance)]
        peak_table = ciftify.utils.get_stdout(fslcluster_cmd)
        with open(outputcsv_sub, "w") as text_file:
            text_file.write(peak_table.replace('/t',','))
    else:
        logger.info('No subcortical volume data in {}'.format(data_file))

    logger.info(ciftify.utils.section_header('Done ciftify_peaktable'))


def load_hemisphere_labels(filename, wb_structure, map_number = 1):
    '''separates dlabel file into left and right and loads label data'''

    with ciftify.utils.TempDir() as little_tempdir:
        ## separate the cifti file into left and right surfaces
        labels_gii = os.path.join(little_tempdir, 'data.label.gii')
        run(['wb_command','-cifti-separate', filename, 'COLUMN',
            '-label', wb_structure, labels_gii])

        # loads label table as dict and data as numpy array
        gifti_img = nibabel.gifti.giftiio.read(labels_gii)
        atlas_data = gifti_img.getArraysFromIntent('NIFTI_INTENT_LABEL')[map_number - 1].data

        atlas_dict = gifti_img.get_labeltable().get_labels_as_dict()
        atlas_df = pd.DataFrame.from_dict(atlas_dict, orient = "index")

    return atlas_data, atlas_df


def wb_cifti_clusters(input_cifti, output_cifti, surf_settings,
                      value_threshold, minimun_size,less_than, starting_label=1):
    '''runs wb_command -cifti-find-clusters'''
    wb_arglist = ['wb_command', '-cifti-find-clusters',
            input_cifti,
            str(value_threshold), str(minimun_size),
            str(value_threshold), str(minimun_size),
            'COLUMN',
            output_cifti,
            '-left-surface', surf_settings['L']['surface'],
            '-corrected-areas', surf_settings['L']['vertex_areas'],
            '-right-surface', surf_settings['R']['surface'],
            '-corrected-areas', surf_settings['R']['vertex_areas'],
            '-start', str(starting_label)]
    if less_than : wb_arglist.append('-less-than')
    cinfo = ciftify.niio.cifti_info(input_cifti)
    if cinfo['maps_to_volume']: wb_arglist.append('-merged-volume')
    run(wb_arglist)

def calc_cluster_areas(df, clust_labs, surf_va):
    '''
    calculates the surface area column of the peaks table
    needs hemisphere specific inputs
    '''
    for cID in df.clusterID.unique():
        idx = np.where(clust_labs == cID)[0]
        area = sum(surf_va[idx])
        df.loc[df.loc[:,'clusterID']==cID,'area'] = area
    return(df)

def calc_atlas_overlap(df, wb_structure, clust_label_array, surf_va, atlas_settings):
    '''
    calculates the surface area column of the peaks table
    needs hemisphere specific inputs
    '''

    ## load atlas
    atlas_label_array, atlas_df = load_hemisphere_labels(atlas_settings['path'],
                                                       wb_structure,
                                                       map_number = atlas_settings['map_number'])
    atlas_prefix = atlas_settings['name']

    ## create new cols to hold the data
    df[atlas_prefix] = pd.Series('not_calculated', index = df.index)
    overlap_col = '{}_overlap'.format(atlas_prefix)
    df[overlap_col] = pd.Series(-99.0, index = df.index)

    for pd_idx in df.index.tolist():
        ## atlas interger label is the integer at the vertex
        atlas_label = atlas_label_array[df.loc[pd_idx, 'vertex']]

        ## the atlas column holds the labelname for this label
        df.loc[pd_idx, atlas_prefix] = atlas_df.iloc[atlas_label, 0]

        ## overlap indices are the intersection of the cluster and the atlas integer masks
        clust_mask = np.where(clust_label_array == df.loc[pd_idx, 'clusterID'])[0]
        atlas_mask = np.where(atlas_label_array == atlas_label)[0]
        overlap_mask = np.intersect1d(clust_mask,atlas_mask)

        ## overlap area is the area of the overlaping region over the total cluster area
        clust_area = df.loc[pd_idx, 'area']
        overlap_area = sum(surf_va[overlap_mask])
        df.loc[pd_idx, overlap_col] = overlap_area/clust_area

    return(df)


def build_hemi_results_df(surf_settings, atlas_settings,
                          input_dscalar, extreama_dscalar, clusters_dscalar):

    ## read in the extrema file from above
    extrema_array = load_hemisphere_data(extreama_dscalar, surf_settings['wb_structure'])
    vertices = np.nonzero(extrema_array)[0]  # indices - vertex id for peaks in hemisphere

    ## read in the original data for the value column
    input_data_array = load_hemisphere_data(input_dscalar, surf_settings['wb_structure'])

    ## load both cluster indices
    clust_array = load_hemisphere_data(clusters_dscalar, surf_settings['wb_structure'])

    ## load the coordinates
    coords =  nibabel.gifti.giftiio.read(surf_settings['surface']).getArraysFromIntent('NIFTI_INTENT_POINTSET')[0].data
    surf_va = ciftify.niio.load_gii_data(surf_settings['vertex_areas'])

    ## put all this info together into one pandas dataframe
    df = pd.DataFrame({"clusterID": np.reshape(extrema_array[vertices],(len(vertices),)),
                    "hemisphere": surf_settings['hemi'],
                    "vertex": vertices,
                    'peak_value': [round(x,3) for x in np.reshape(input_data_array[vertices],(len(vertices),))],
                    'area': -99.0})

    ## calculate the area of the clusters
    df = calc_cluster_areas(df, clust_array, surf_va)

    ## look at atlas overlap
    for atlas in atlas_settings.keys():
        df = calc_atlas_overlap(df, surf_settings['wb_structure'], clust_array, surf_va, atlas_settings[atlas])

    return(df)

def define_atlas_settings():
    atlas_settings = {
        'DKT': {
            'path' : os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                                  'cvs_avg35_inMNI152.aparc.32k_fs_LR.dlabel.nii'),
            'order' : 1,
            'name': 'DKT',
            'map_number': 1
        },

        'Yeo7': {
            'path' : os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                                  'RSN-networks.32k_fs_LR.dlabel.nii'),
            'order' : 2,
            'name' : 'Yeo7',
            'map_number': 1
        },
        'MMP': {
            'path': os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                                 'Q1-Q6_RelatedValidation210.CorticalAreas_dil_Final_Final_Areas_Group_Colors.32k_fs_LR.dlabel.nii'),
            'order' : 3,
            'name' : 'MMP',
            'map_number': 1
        }
    }
    return(atlas_settings)


def define_surface_settings(arguments, tmpdir):
    ''' parse arguments to define surfaces '''

    surf_settings = {
        'L': {'surface' : arguments['--left-surface'],
              'vertex_areas' : arguments['--left-surf-area'],
              'wb_structure' : 'CORTEX_LEFT',
              'hemi' : 'L'
        },
        'R': {
            'surface' : arguments['--right-surface'],
            'vertex_areas' :  arguments['--right-surf-area'],
            'wb_structure' : 'CORTEX_RIGHT',
            'hemi' : 'R'
        },
    }

    if any((surf_settings['L']['surface'] == None, surf_settings['R']['surface'] == None)):
        if all((surf_settings['L']['surface'] == None, surf_settings['R']['surface'] == None)):
            for hemi in ['L','R']:
                surf_settings[hemi]['surface'] = os.path.join(
                            ciftify.config.find_HCP_S1200_GroupAvg(),
                            'S1200.{}.midthickness_MSMAll.32k_fs_LR.surf.gii'
                            ''.format(hemi))
                surf_settings[hemi]['vertex_areas'] = os.path.join(
                        ciftify.config.find_HCP_S1200_GroupAvg(),
                        'S1200.{}.midthickness_MSMAll_va.32k_fs_LR.shape.gii'
                        ''.format(hemi))
        else:
            logger.error("Need both left and right surfaces - only one surface given")
            sys.exit(1)

    if any((surf_settings['L']['vertex_areas'] == None,
           surf_settings['R']['vertex_areas'] == None)):
        if all((surf_settings['L']['vertex_areas'] == None,
               surf_settings['R']['vertex_areas'] == None)):
            for hemi in ['L','R']:
                surf_settings[hemi]['vertex_areas'] = os.path.join(tmpdir,
                        'surf{}_va.shape.gii'.format(hemi))
                run(['wb_command', '-surface-vertex-areas',
                        surf_settings[hemi]['surface'],
                        surf_settings[hemi]['vertex_areas']])
        else:
            logger.error("Need both left and right surface area arguments - only one given")
            sys.exit(1)

    return(surf_settings)

def main():
    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = run_ciftify_peak_table(tmpdir)

if __name__ == '__main__':
    main()
