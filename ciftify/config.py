#!/usr/bin/env python
"""
These functions search the environment for software depenencies and configuration.
"""

import os
from ciftify.utilities import get_date_user
import subprocess
import multiprocessing as mp

def find_afni():

    """
    Returns the path of the afni bin/ folder, or None if unavailable.
    """
    try:
        dir_afni = subprocess.check_output('which afni', shell=True)
        dir_afni = os.path.dirname(dir_afni)
    except:
        dir_afni = None

    return dir_afni

def find_clone():
    """
    Returns path of the epitome clone directory, which defaults to ~/epitome.
    """
    dir_clone = os.getenv('EPITOME_CLONE')
    if dir_clone == None:
        datetime, user, f_id = get_date_user()
        dir_clone = '/home/{}/epitome'.format(user)

    return dir_clone

def find_epitome():
    """
    Returns path of the epitome bin/ folder, or None if unavailable.
    """
    try:
        dir_epitome = subprocess.check_output('which epitome', shell=True)
        dir_epitome = '/'.join(dir_epitome.split('/')[:-2])
    except:
        dir_epitome = None

    return dir_epitome

def find_workbench():
    """
    Returns path of the workbench bin/ folder, or None if unavailable.
    """
    try:
        workbench = subprocess.check_output('which wb_command', shell=True)
    except:
        workbench = None

    return workbench

def find_matlab():
    """
    Returns the path of the matlab folder, or None if unavailable.
    """
    try:
        dir_matlab = subprocess.check_output('which matlab', shell=True)
        dir_matlab = '/'.join(dir_matlab.split('/')[:-2])

    except:
        dir_matlab = None

    return dir_matlab

def find_fsl():
    """
    Returns the path of the fsl bin/ folder, or None if unavailable.
    """
    try:
        dir_fsl = subprocess.check_output('which fsl', shell=True)
        dir_fsl = '/'.join(dir_fsl.split('/')[:-1])
    except:
        dir_fsl = None

    return dir_fsl

def find_fix():
    """
    Returns the path of the fix bin/ folder, or None if unavailable.
    """
    try:
        dir_fix = subprocess.check_output('which fix', shell=True)
        dir_fix = '/'.join(dir_fix.split('/')[:-1])
    except:
        dir_fix = None

    return dir_fix

def find_freesurfer():
    """
    Returns the path of the freesurfer bin/ folder, or None if unavailable.
    """
    try:
        dir_freesurfer = subprocess.check_output('which recon-all', shell=True)
        dir_freesurfer = '/'.join(dir_freesurfer.split('/')[:-1])
    except:
        dir_freesurfer = None

    return dir_freesurfer

def find_hcp_tools():
    """
    Returns the hcp pipeline tools path defined in the environment.
    """
    try:
        dir_hcp_tools = os.getenv('HCPPIPEDIR')
    except:
        dir_hcp_tools = None

    return dir_hcp_tools

def find_scene_templates():
        """
        Returns the hcp scene templates path defined in the environment.
        """
        try:
            dir_hcp_templates = os.getenv('HCP_SCENE_TEMPLATES')
        except:
            dir_hcp_templates = None

        return dir_hcp_templates

def find_ciftify_global():
        """
        Returns the hcp scene templates path defined in the environment.
        """
        try:
            dir_templates = os.getenv('CIFTIFY_TEMPLATES')
        except:
            dir_templates = None

        return dir_templates

def find_HCP_S900_GroupAvg():
    """return path to HCP_S900_GroupAvg which should be in ciftify"""
    s900 = os.path.join(find_ciftify_global(), 'HCP_S900_GroupAvg_v1')
    return(s900)

def find_data():
    """
    Returns the epitome data path defined in the environment.
    """
    try:
        dir_data = os.getenv('EPITOME_DATA')
    except:
        dir_data = None

    return dir_data

def find_freesurfer_data():
    """
    Returns the freesurfer data path defined in the environment.
    """
    try:
        dir_freesurfer_data = os.getenv('SUBJECTS_DIR')
    except:
        dir_freesurfer_data = None

    return dir_freesurfer_data

def find_hcp_data():
    """
    Returns the freesurfer data path defined in the environment.
    """
    try:
        dir_hcp_data = os.getenv('HCP_DATA')
    except:
        dir_hcp_data = None

    return dir_hcp_data

def wb_command_version():
    '''
    Returns version info about wb_command
    '''
    wb_path = find_workbench()
    wb_help = subprocess.check_output('wb_command', shell=True)
    wb_version = wb_help.split(os.linesep)[0:3]
    wb_v = os.linesep.join(wb_version)
    all_info = 'wb_command Path: {}{}{}'.format(wb_path, os.linesep,wb_v)
    return(all_info)
