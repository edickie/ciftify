#!/usr/bin/env python3
"""
A collection of functions used by ciftifies report generation functions
i.e. ciftify_peaktable and ciftify_dlabel_report
"""

import os
from ciftify.utils import run
import ciftify.config
import numpy as np
import pandas as pd
import logging
import logging.config


def define_atlas_settings():
    atlas_settings = {
        'DKT': {
            'path' : os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                                  'cvs_avg35_inMNI152.aparc.32k_fs_LR.dlabel.nii'),
            'order' : 1,
            'name': 'DKT',
            'map_number': 1
        },
        'MMP': {
            'path': os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                                 'Q1-Q6_RelatedValidation210.CorticalAreas_dil_Final_Final_Areas_Group_Colors.32k_fs_LR.dlabel.nii'),
            'order' : 3,
            'name' : 'MMP',
            'map_number': 1
        },
        'Yeo7': {
            'path' : os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
                                  'RSN-networks.32k_fs_LR.dlabel.nii'),
            'order' : 2,
            'name' : 'Yeo7',
            'map_number': 1
        }
    }
    return(atlas_settings)

class HemiSurfaceSettings(object):
    '''class that holds the setting for one hemisphere'''
    def __init__(self, hemi, arguments):
        assert hemi in ['L','R']
        self.hemi = hemi
        self.wb_structure = self._get_wb_structure()
        self.surface = self._get_surf_arg(arguments)
        self.vertex_areas = self._get_vertex_areas_arg(arguments)

    def _get_wb_structure(self):
        ''' sets the structure according to the hemisphere'''
        if self.hemi == 'L': return 'CORTEX_LEFT'
        if self.hemi == 'R': return 'CORTEX_RIGHT'
        raise

    def _get_surf_arg(self, arguments):
        ''' sets the surface filename according to user arguments'''
        if self.hemi == 'L': return arguments['--left-surface']
        if self.hemi == 'R': return arguments['--right-surface']
        raise

    def _get_vertex_areas_arg(self, arguments):
        ''' sets the vertex areas according to the user arguments'''
        if self.hemi == 'L': return arguments['--left-surf-area']
        if self.hemi == 'R': return arguments['--right-surf-area']
        raise

    def set_surface_to_global(self):
        ''' sets the surface to the S1200 midthickness'''
        self.surface = os.path.join(
                            ciftify.config.find_HCP_S1200_GroupAvg(),
                            'S1200.{}.midthickness_MSMAll.32k_fs_LR.surf.gii'
                            ''.format(self.hemi))
        return(self)

    def set_vertex_areas_to_global(self):
        ''' sets the vertex areas to the S1200 average'''
        self.vertex_areas = os.path.join(
                        ciftify.config.find_HCP_S1200_GroupAvg(),
                        'S1200.{}.midthickness_MSMAll_va.32k_fs_LR.shape.gii'
                        ''.format(self.hemi))
        return(self)

    def calc_vertex_areas_from_surface(self, tmpdir):
        ''' use wb_command to calculate the vertex areas from the given surface'''
        self.vertex_areas = os.path.join(tmpdir,
                        'surf{}_va.shape.gii'.format(self.hemi))

        run(['wb_command', '-surface-vertex-areas',
                self.surface, self.vertex_areas])
        return(self)

class CombinedSurfaceSettings(object):
    ''' hold the setttings for both hemispheres'''
    def __init__(self, arguments, tmpdir):

        logger = logging.getLogger(__name__)

        for hemi in ['L','R']:
            self.__dict__[hemi] = HemiSurfaceSettings(hemi, arguments)

        ## check if surfaces or settings have been specified
        surfaces_not_set = (self.L.surface == None, self.R.surface == None)
        va_not_set = (self.L.vertex_areas == None, self.R.vertex_areas == None)

        if sum(surfaces_not_set) == 1:
            logger.error("Need both left and right surfaces - only one surface given")
            sys.exit(1)

        if sum(va_not_set) == 1:
            logger.error("Need both left and right surface area arguments - only one given")
            sys.exit(1)

        if all(va_not_set):
            if all(surfaces_not_set):
                # if neither have been specified, we use the HCP S1200 averages
                for hemi in ['L','R']:
                    self.__dict__[hemi].set_vertex_areas_to_global()
                    self.__dict__[hemi].set_surface_to_global()
            else:
                # if only surfaces have been given, we use the surface to calculate the vertex areas
                for hemi in ['L','R']:
                    self.__dict__[hemi].calc_vertex_areas_from_surface(tmpdir)

def sum_idx_area(clust_idx, surf_va):
    '''
    calculates the surface area for a given set of indices
    '''
    area = sum(surf_va[clust_idx])
    return(area)

def get_cluster_indices(cluster_id, clust_altas):
    '''
    gets the indices for a cluster given the label
    '''
    clust_idx = np.where(clust_altas == cluster_id)[0]
    return(clust_idx)

def get_overlaping_idx(clust_id1, clust_atlas1, clust_id2, clust_atlas2):
    '''
    find the indices that overlap for two labels across two maps
    '''
    label1_idx = get_cluster_indices(int(clust_id1), clust_atlas1)
    label2_idx = get_cluster_indices(int(clust_id2), clust_atlas2)
    overlap_idx = np.intersect1d(label1_idx,label2_idx)
    return(overlap_idx)

def calc_cluster_area(cluster_id, atlas_array, surf_va_array):
    '''
    calculate the area of a cluster
    '''
    clust_idx = get_cluster_indices(int(cluster_id), atlas_array)
    area = sum_idx_area(clust_idx, surf_va_array)
    return(area)

def calc_overlapping_area(clust_id1, clust_atlas1, clust_id2, clust_atlas2, surf_va_array):
    '''
    calculates the area of overlap between two clusters
    '''
    overlap_idx = get_overlaping_idx(clust_id1, clust_atlas1, clust_id2, clust_atlas2)

    if len(overlap_idx) > 0:
        overlap_area = sum_idx_area(overlap_idx, surf_va_array)
    else:
        overlap_area = 0

    return(overlap_area)

def calc_label_to_atlas_overlap(clust_id1, clust_atlas1_data,
                                clust_atlas2_dict, clust_atlas2, surf_va_array):
    '''create a df of overlap of and atlas with one label'''
    ## create a data frame to hold the overlap
    o_df = pd.DataFrame.from_dict(clust_atlas2_dict, orient = "index")
    o_df = o_df.rename(index=str, columns={0: "clusterID"})

    for idx_label2 in o_df.index.get_values():
        o_df.loc[idx_label2, 'overlap_area'] = calc_overlapping_area(clust_id1, clust_atlas1_data,
                                                        idx_label2, clust_atlas2, surf_va_array)
    return(o_df)

def overlap_summary_string(overlap_df, min_percent_overlap):
    '''summarise the overlap as a sting'''
    rdf = overlap_df[overlap_df.overlap_percent > min_percent_overlap]
    rdf = rdf.sort_values(by='overlap_percent', ascending=False)
    result_string = ""
    for o_label in rdf.index.get_values():
        result_string += '{} ({:2.1f}%); '.format(rdf.loc[o_label, 'clusterID'],
                                                  rdf.loc[o_label, 'overlap_percent'])
    return(result_string)


def get_label_overlap_summary(clust_id1, clust_atlas1_data, clust_atlas2_data, clust_atlas2_dict,
                              surf_va_array, min_percent_overlap = 5):
    '''returns of sting listing all clusters in label2 that overlap with label1_idx in label1'''

    label1_area = calc_cluster_area(clust_id1, clust_atlas1_data, surf_va_array)
    if label1_area == 0:
        return("")

    ## get a pd dataframe of labels names and overlap
    overlap_df = calc_label_to_atlas_overlap(clust_id1, clust_atlas1_data,
                                             clust_atlas2_dict, clust_atlas2_data, surf_va_array)

    if overlap_df.overlap_area.sum() == 0:
        return("")

    ## convert overlap to percent
    overlap_df.loc[:, 'overlap_percent'] = overlap_df.loc[:, 'overlap_area']/label1_area*100

    ## convert the df to a string report
    result_string = overlap_summary_string(overlap_df, min_percent_overlap)

    return(result_string)
