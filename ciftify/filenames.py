#!/usr/bin/env python3
"""
A collection of function for the building file and directory names
within the ciftify/HCP pipelines naming convention
"""

import os
import logging

def spec_file(subject_id, mesh_settings):
    '''return the formated spec_filename for this mesh'''
    specfile = os.path.join(mesh_settings['Folder'],
        "{}.{}.wb.spec".format(subject_id, mesh_settings['meshname']))
    return specfile

def metric_file(subject_id, map_name, hemisphere, mesh_settings):
    '''return the formatted file path for a metric (surface data) file for this
    mesh'''
    metric_gii = os.path.join(mesh_settings['tmpdir'],
        "{}.{}.{}.{}.shape.gii".format(subject_id, hemisphere, map_name,
        mesh_settings['meshname']))
    return metric_gii

def func_gii_file(subject_id, map_name, hemisphere, mesh_settings):
    '''return the formatted file path for metric fmri (surface data) file for this
    mesh'''
    metric_gii = os.path.join(mesh_settings['tmpdir'],
        "{}.{}.{}.{}.func.gii".format(subject_id, hemisphere, map_name,
        mesh_settings['meshname']))
    return metric_gii

def medial_wall_roi_file(subject_id, hemisphere, mesh_settings):
    '''
    Medial wall ROIs are the only shape.gii files that aren't temp files,
    and their name is given in the mesh_settings, so they get their own function
    '''
    roi_gii = os.path.join(mesh_settings['Folder'],
        "{}.{}.{}.{}.shape.gii".format(subject_id, hemisphere,
        mesh_settings['ROI'], mesh_settings['meshname']))
    return roi_gii

def surf_file(subject_id, surface, hemisphere, mesh_settings):
    '''return the formatted file path to a surface file '''
    surface_gii = os.path.join(mesh_settings['Folder'],
            '{}.{}.{}.{}.surf.gii'.format(subject_id, hemisphere, surface,
            mesh_settings['meshname']))
    return surface_gii

def label_file(subject_id, label_name, hemisphere, mesh_settings):
    '''return the formated file path to a label (surface data) file for this mesh'''
    label_gii = os.path.join(mesh_settings['tmpdir'],
        '{}.{}.{}.{}.label.gii'.format(subject_id, hemisphere, label_name,
        mesh_settings['meshname']))
    return label_gii

def define_meshes(subject_workdir, temp_dir, high_res_mesh = "164",
        low_res_meshes = ["32"], make_low_res = False):
    '''sets up a dictionary of expected paths for each mesh'''

    meshes = {
        'T1wNative':{
            'Folder' : os.path.join(subject_workdir, 'T1w', 'Native'),
            'ROI': 'roi',
            'meshname': 'native',
            'tmpdir': os.path.join(temp_dir, 'T1w', 'native'),
            'T1wImage': os.path.join(subject_workdir, 'T1w', 'T1w.nii.gz'),
            'T2wImage': os.path.join(subject_workdir, 'T1w', 'T2w.nii.gz'),
            'DenseMapsFolder': os.path.join(subject_workdir, 'MNINonLinear', 'Native')},
        'AtlasSpaceNative':{
            'Folder' : os.path.join(subject_workdir, 'MNINonLinear', 'Native'),
            'ROI': 'roi',
            'meshname': 'native',
            'tmpdir': os.path.join(temp_dir, 'MNINonLinear', 'native'),
            'T1wImage': os.path.join(subject_workdir, 'MNINonLinear', 'T1w.nii.gz'),
            'T2wImage': os.path.join(subject_workdir, 'MNINonLinear', 'T2w.nii.gz')},
        'HighResMesh':{
            'Folder' : os.path.join(subject_workdir, 'MNINonLinear'),
            'ROI': 'atlasroi',
            'meshname': '{}k_fs_LR'.format(high_res_mesh),
            'tmpdir': os.path.join(temp_dir, '{}k_fs_LR'.format(high_res_mesh)),
            'T1wImage': os.path.join(subject_workdir, 'MNINonLinear', 'T1w.nii.gz'),
            'T2wImage': os.path.join(subject_workdir, 'MNINonLinear', 'T2w.nii.gz')}
    }
    for low_res_mesh in low_res_meshes:
        meshes['{}k_fs_LR'.format(low_res_mesh)] = {
            'Folder': os.path.join(subject_workdir, 'MNINonLinear',
                    'fsaverage_LR{}k'.format(low_res_mesh)),
            'ROI' : 'atlasroi',
            'meshname': '{}k_fs_LR'.format(low_res_mesh),
            'tmpdir': os.path.join(temp_dir, '{}k_fs_LR'.format(low_res_mesh)),
            'T1wImage': os.path.join(subject_workdir, 'MNINonLinear', 'T1w.nii.gz'),
            'T2wImage': os.path.join(subject_workdir, 'MNINonLinear', 'T2w.nii.gz')}
        if make_low_res:
             meshes['Native{}k_fs_LR'.format(low_res_mesh)] = {
                 'Folder': os.path.join(subject_workdir, 'T1w',
                        'fsaverage_LR{}k'.format(low_res_mesh)),
                 'ROI' : 'atlasroi',
                 'meshname': '{}k_fs_LR'.format(low_res_mesh),
                 'tmpdir': os.path.join(temp_dir,
                        '{}k_fs_LR'.format(low_res_mesh)),
                 'T1wImage': os.path.join(subject_workdir, 'T1w', 'T1w.nii.gz'),
                 'T2wImage': os.path.join(subject_workdir, 'T1w', 'T2w.nii.gz'),
                 'DenseMapsFolder': os.path.join(subject_workdir, 'MNINonLinear',
                        'fsaverage_LR{}k'.format(low_res_mesh))}
    return meshes
