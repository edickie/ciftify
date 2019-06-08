#!/usr/bin/env python3
"""
Takes a cifti map ('dscalar.nii') and outputs a csv of results

Usage:
    ciftify_statclust_report [options] <func.dscalar.nii>

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
    --output-peaks         Also output an additional output of peak locations

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

Outputs a cluster report csv with the following headings:
  + clusterID: Integer for the cluster this peak is from (corresponds to dlabel.nii)
  + cluster_name: the cluster label
    + by default this will be "LABEL_<clusterID>" but this be changed
      in the .dlabel.nii file using connectome-workbench
  + mean_value: the average value for this cluster within the input dscalar.nii map
  + area: the surface area of the cluster (on the specified surface)
  + DKT_overlap: a list of DKT freesurfer anatomical atlas (aparc) atlas labels
     that overlap with this cluster and the percent overlap of each label
  + Yeo7_overlap: a list of the Yeo et al 2011 7 network labels that overlap
     with this cluster and the percent overlap of each label
  + MMP_overlap: The labels from the Glasser et al (2016) Multi-Modal Parcellation
     that overlap with this cluster and the percent overlap of each label

If the '--output-peaks' flag is indicated, an addtional table will be output
with several headings:
  + clusterID: Integer for the cluster this peak is from (corresponds to dlabel.nii)
  + hemisphere: Hemisphere the peak is in (L or R)
  + vertex: The vertex id
  + x,y,z: The nearest x,y,z coordinates to the vertex
  + value: The intensity (value) at that vertex in the func.dscalar.nii
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
from docopt import docopt
import os, sys
import numpy as np
import pandas as pd
import logging
import logging.config
import ciftify.niio
import ciftify.report
import ciftify.utils
from ciftify.meants import NibInput

config_path = os.path.join(os.path.dirname(ciftify.config.find_ciftify_global()), 'bin', "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

def load_LR_vertex_areas(surf_settings):
    ''' loads the vertex areas and stacks the dataframes'''
    surf_va_L = ciftify.niio.load_gii_data(surf_settings.L.vertex_areas)
    surf_va_R = ciftify.niio.load_gii_data(surf_settings.R.vertex_areas)
    surf_va_LR = np.vstack((surf_va_L, surf_va_R))
    return(surf_va_LR)


def report_atlas_overlap(df, label_data, atlas, surf_va_LR, min_percent_overlap = 5):
    # read the atlas
    atlas_data, atlas_dict = ciftify.niio.load_LR_label(atlas['path'],
                                                    int(atlas['map_number']))
    # write an overlap report to the outputfile
    o_col = '{}_overlap'.format(atlas['name'])
    df[o_col] = ""
    for pd_idx in df.index.get_values():
        df.loc[pd_idx, o_col] = ciftify.report.get_label_overlap_summary(
                        pd_idx, label_data, atlas_data, atlas_dict, surf_va_LR,
                        min_percent_overlap = min_percent_overlap)
    return(df)


def run_ciftify_dlabel_report(arguments, tmpdir):

    dscalar_in = NibInput(arguments['<func.dscalar.nii>'])
    surf_distance = arguments['--surface-distance']

    outputbase = arguments['--outputbase']
    dont_output_clusters = arguments['--no-cluster-dlabel']
    output_peaktable = arguments['--output-peaks']

    surf_settings = ciftify.report.CombinedSurfaceSettings(arguments, tmpdir)
    atlas_settings = ciftify.report.define_atlas_settings()

    ## if not outputname is given, create it from the input dscalar map
    if not outputbase:
        outputbase = os.path.join(os.path.dirname(dscalar_in.path), dscalar_in.base)
        ciftify.utils.check_output_writable(outputbase, exit_on_error = True)

    clusters_dscalar = clusterise_dscalar_input(dscalar_in.path,
            arguments,
            surf_settings,
            tmpdir)

    if dont_output_clusters:
        cluster_dlabel = os.path.join(tmpdir, 'clust.dlabel.nii')
    else:
        cluster_dlabel = '{}_clust.dlabel.nii'.format(outputbase)
    empty_labels = os.path.join(tmpdir, 'empty_labels.txt')
    ciftify.utils.run('touch {}'.format(empty_labels))
    ciftify.utils.run(['wb_command', '-cifti-label-import',
        clusters_dscalar, empty_labels, cluster_dlabel])

    ## load the data
    label_data, label_dict = ciftify.niio.load_LR_label(cluster_dlabel, map_number = 1)

    ## define the outputcsv
    outputcsv = '{}_statclust_report.csv'.format(outputbase)
    logger.info('Output table: {}'.format(outputcsv))

    ## load the vertex areas
    surf_va_LR = load_LR_vertex_areas(surf_settings)

    ## assert that the dimensions match
    if not (label_data.shape[0] == surf_va_LR.shape[0]):
        logger.error('label file vertices {} not equal to vertex areas {}'
                     ''.format(label_data.shape[0], surf_va_LR.shape[0]))
        sys.exit(1)

    ## use the label dict to start the report dataframe
    df = pd.DataFrame.from_dict(label_dict, orient = "index")
    df['label_idx'] = df.index
    df = df.rename(index=str, columns={0: "label_name"})


    # calculate a column of the surface area for row ROIs
    df['area'] = -999
    for pd_idx in df.index.get_values():
        df.loc[pd_idx, 'area']  = ciftify.report.calc_cluster_area(pd_idx,
                                                        label_data, surf_va_LR)

    for atlas in atlas_settings.values():
        df = report_atlas_overlap(df, label_data, atlas,
                                  surf_va_LR, min_percent_overlap = 5)

    df.to_csv(outputcsv)

    if output_peaktable:
        write_statclust_peaktable(dscalar_in.path, clusters_dscalar, outputbase,
                arguments, surf_settings, atlas_settings)

class ThresholdArgs(object):
    '''little class that holds the user aguments about thresholds'''
    def __init__(self, arguments):
        self.max = arguments([])
        area_threshold = arguments['--area-threshold']
        self.volume_distance = arguments['--volume-distance']
        min_threshold = arguments['--min-threshold']
        max_threshold = arguments['--max-threshold']
        area_threshold = arguments['--area-thratlas_settingseshold']

def clusterise_dscalar_input(data_file, arguments, surf_settings, tmpdir):
    '''runs wb_command -cifti-find-clusters twice
    returns the path to the output
    '''
    ## also run clusterize with the same settings to get clusters
    pcluster_dscalar = os.path.join(tmpdir,'pclusters.dscalar.nii')

    wb_cifti_clusters(data_file, pcluster_dscalar, surf_settings,
                      arguments['--max-threshold'],
                      arguments['--area-threshold'],
                      less_than = False, starting_label=1)

    ## load both cluster files to determine the max value
    pos_clust_data = ciftify.niio.load_concat_cifti_surfaces(pcluster_dscalar)
    max_pos = int(np.max(pos_clust_data))

    ## now get the negative clusters
    ncluster_dscalar = os.path.join(tmpdir,'nclusters.dscalar.nii')
    wb_cifti_clusters(data_file, ncluster_dscalar, surf_settings,
                      arguments['--min-threshold'],
                      arguments['--area-threshold'],
                      less_than = True, starting_label=max_pos + 1)

    ## add the positive and negative together to make one cluster map
    clusters_out = os.path.join(tmpdir,'clusters.dscalar.nii')
    ciftify.utils.run(['wb_command', '-cifti-math "(x+y)"',
        clusters_out,
        '-var','x',pcluster_dscalar, '-var','y',ncluster_dscalar])
    return clusters_out

def wb_cifti_clusters(input_cifti, output_cifti, surf_settings,
                      value_threshold, minimun_size,less_than, starting_label=1):
    '''runs wb_command -cifti-find-clusters'''
    wb_arglist = ['wb_command', '-cifti-find-clusters',
            input_cifti,
            str(value_threshold), str(minimun_size),
            str(value_threshold), str(minimun_size),
            'COLUMN',
            output_cifti,
            '-left-surface', surf_settings.L.surface,
            '-corrected-areas', surf_settings.L.vertex_areas,
            '-right-surface', surf_settings.R.surface,
            '-corrected-areas', surf_settings.R.vertex_areas,
            '-start', str(starting_label)]
    if less_than : wb_arglist.append('-less-than')
    cinfo = ciftify.niio.cifti_info(input_cifti)
    if cinfo['maps_to_volume']: wb_arglist.append('-merged-volume')
    ciftify.utils.run(wb_arglist)

def write_statclust_peaktable(data_file, clusters_dscalar, outputbase,
        arguments, surf_settings, atlas_settings):
    '''runs the old peak table functionality

    Parameters
    ----------
    data_file : filepath
      path to the dscalar map input
    clusters_dscalar : filepath
      path to the cluster file created with same settings
    outputbase :
       the prefix for the outputfile
    arguments : dict
      the user args dictionary to pull the thresholds from
    surf_settings : dict
      the dictionary of paths to the surface files,
      created by ciftify.report.CombinedSurfaceSettings
    altas_settings : dict
      dictionary of paths and settings related to the atlases to use for overlaps
      comparison. Created by ciftify.report.define_atlas_settings()

    Outputs
    -------
    writes a csv to <outputbase>_cortex_peaks.csv
    '''
    with ciftify.utils.TempDir() as ex_tmpdir:
        ## run FSL's cluster on the subcortical bits
        ## now to run FSL's cluster on the subcortical bits
        cinfo = ciftify.niio.cifti_info(data_file)
        if cinfo['maps_to_volume']:
            subcortical_vol = os.path.join(ex_tmpdir, 'subcortical.nii.gz')
            ciftify.utils.run(['wb_command', '-cifti-separate', data_file, 'COLUMN', '-volume-all', subcortical_vol])
            fslcluster_cmd = ['cluster',
                '--in={}'.format(subcortical_vol),
                '--thresh={}'.format(arguments['--max-threshold']),
                '--peakdist={}'.format(arguments['--volume-distance'])]
            peak_table = ciftify.utils.get_stdout(fslcluster_cmd)
            with open("{}_subcortical_peaks.csv".format(outputbase), "w") as text_file:
                text_file.write(peak_table.replace('/t',','))
        else:
            logger.info('No subcortical volume data in {}'.format(data_file))

        ## run wb_command -cifti-extrema to find the peak locations
        extrema_dscalar = os.path.join(ex_tmpdir,'extrema.dscalar.nii')
        ciftify.utils.run(['wb_command','-cifti-extrema',
               data_file,
               str(arguments['--surface-distance']),
               str(arguments['--volume-distance']),
               'COLUMN',
               extrema_dscalar,
               '-left-surface', surf_settings.L.surface,
               '-right-surface', surf_settings.R.surface,
               '-threshold',
               str(arguments['--min-threshold']),
               str(arguments['--max-threshold'])])

        ## multiply the cluster labels by the extrema to get the labeled exteama
        lab_extrema_dscalar = os.path.join(ex_tmpdir,'lab_extrema.dscalar.nii')
        ciftify.utils.run(['wb_command', '-cifti-math "(abs(x*y))"',
            lab_extrema_dscalar,
            '-var','x',clusters_dscalar, '-var','y',extrema_dscalar])

        ## run left and right dfs... then concatenate them
        dfL = build_hemi_results_df(surf_settings.L, atlas_settings,
                                  data_file, lab_extrema_dscalar, clusters_dscalar)
        dfR = build_hemi_results_df(surf_settings.R, atlas_settings,
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
    df.to_csv("{}_cortex_peaks.csv".format(outputbase),
          columns = output_columns,index=False)



def build_hemi_results_df(surf_settings, atlas_settings,
                          input_dscalar, extreama_dscalar, clusters_dscalar):

    ## read in the extrema file from above
    extrema_array = ciftify.niio.load_hemisphere_data(extreama_dscalar, surf_settings.wb_structure)
    vertices = np.nonzero(extrema_array)[0]  # indices - vertex id for peaks in hemisphere

    ## read in the original data for the value column
    input_data_array = ciftify.niio.load_hemisphere_data(input_dscalar, surf_settings.wb_structure)

    ## load both cluster indices
    clust_array = ciftify.niio.load_hemisphere_data(clusters_dscalar, surf_settings.wb_structure)

    ## load the coordinates
    coords = ciftify.niio.load_surf_coords(surf_settings.surface)
    surf_va = ciftify.niio.load_gii_data(surf_settings.vertex_areas)

    ## put all this info together into one pandas dataframe
    df = pd.DataFrame({"clusterID": np.reshape(extrema_array[vertices],(len(vertices),)),
                    "hemisphere": surf_settings.hemi,
                    "vertex": vertices,
                    'peak_value': [round(x,3) for x in np.reshape(input_data_array[vertices],(len(vertices),))]})

    ## look at atlas overlap
    for atlas in atlas_settings.keys():
        df = calc_atlas_overlap(df, surf_settings.wb_structure, clust_array, surf_va, atlas_settings[atlas])

    return(df)

def calc_atlas_overlap(df, wb_structure, clust_label_array, surf_va, atlas_settings):
    '''
    calculates the surface area column of the peaks table
    needs hemisphere specific inputs
    '''

    ## load atlas
    atlas_label_array, atlas_dict = ciftify.niio.load_hemisphere_labels(atlas_settings['path'],
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
        df.loc[pd_idx, atlas_prefix] = atlas_dict[atlas_label]

        overlap_area = ciftify.report.calc_overlapping_area(
            df.loc[pd_idx, 'clusterID'], clust_label_array,
            atlas_label, atlas_label_array,
            surf_va)

        ## overlap area is the area of the overlaping region over the total cluster area
        clust_area = ciftify.report.calc_cluster_area(
            df.loc[pd_idx, 'clusterID'],
            clust_label_array,
            surf_va)

        df.loc[pd_idx, overlap_col] = overlap_area/clust_area

    return(df)

def main():
    arguments = docopt(__doc__)

    logger.setLevel(logging.WARNING)

    if arguments['--debug']:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ## set up the top of the log
    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
        ciftify.utils.section_header('Starting ciftify_statclust_report')))

    ciftify.utils.log_arguments(arguments)

    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = run_ciftify_dlabel_report(arguments, tmpdir)

if __name__ == '__main__':
    main()
