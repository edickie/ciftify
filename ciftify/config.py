#!/usr/bin/env python
"""
These functions search the environment for software dependencies and configuration.
"""
from __future__ import unicode_literals

import os
import subprocess
import logging
import pkg_resources

import ciftify.utilities as util

def find_workbench():
    """
    Returns path of the workbench bin/ folder, or None if unavailable.
    """
    try:
        workbench = util.check_output('which wb_command')
        workbench = workbench.strip()
    except:
        workbench = None

    return workbench

def find_fsl():
    """
    Returns the path of the fsl bin/ folder, or None if unavailable.
    """
    # Check the FSLDIR environment variable first
    shell_val = os.getenv('FSLDIR')
    dir_fsl = os.path.join(shell_val, 'bin') if shell_val else ''

    if os.path.exists(dir_fsl):
        return dir_fsl

    # If the env var method fails, fall back to using which. This method is
    # not used first because sometimes the executable is installed separately
    # from the rest of the fsl package, making it hard (or impossible) to locate
    # fsl data files based on the returned path
    try:
        dir_fsl = util.check_output('which fsl')
        dir_fsl = '/'.join(dir_fsl.split('/')[:-1])
    except:
        dir_fsl = None

    return dir_fsl

def find_freesurfer():
    """
    Returns the path of the freesurfer bin/ folder, or None if unavailable.
    """
    try:
        dir_freesurfer = util.check_output('which recon-all')
        dir_freesurfer = '/'.join(dir_freesurfer.split('/')[:-1])
    except:
        dir_freesurfer = None

    return dir_freesurfer

def find_msm():
    try:
        msm = util.check_output("which msm")
    except:
        msm = None
    return msm.replace(os.linesep, '')

def find_scene_templates():
    """
    Returns the hcp scene templates path. If the shell variable
    HCP_SCENE_TEMPLATES is set, uses that. Otherwise returns the defaults
    stored in the ciftify/data/scene_templates folder.
    """
    dir_hcp_templates = os.getenv('HCP_SCENE_TEMPLATES')

    if dir_hcp_templates is None:
        ciftify_path = os.path.dirname(__file__)
        dir_hcp_templates = os.path.abspath(os.path.join(find_ciftify_global(),
                'scene_templates'))
    return dir_hcp_templates

def find_ciftify_global():
    """
    Returns the path to ciftify required config and support files. If the
    shell variable CIFTIFY_DATA is set, uses that. Otherwise returns the
    defaults stored in the ciftify/data folder.
    """
    dir_templates = os.getenv('CIFTIFY_DATA')

    if dir_templates is None:
        ciftify_path = os.path.dirname(__file__)
        dir_templates = os.path.abspath(os.path.join(ciftify_path, 'data'))

    return dir_templates

def find_HCP_S900_GroupAvg():
    """return path to HCP_S900_GroupAvg which should be in ciftify"""
    s900 = os.path.join(find_ciftify_global(), 'HCP_S900_GroupAvg_v1')
    return s900

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
    Returns version info about wb_command.

    Will raise an error if wb_command is not found, since the scripts that use
    this depend heavily on wb_command and should crash anyway in such
    an unexpected situation.
    '''
    wb_path = find_workbench()
    if wb_path is None:
        raise EnvironmentError("wb_command not found. Please check that it is "
                "installed.")
    wb_help = util.check_output('wb_command')
    wb_version = wb_help.split(os.linesep)[0:3]
    sep = '{}    '.format(os.linesep)
    wb_v = sep.join(wb_version)
    all_info = 'wb_command: {}Path: {}    {}'.format(sep,wb_path,wb_v)
    return(all_info)

def freesurfer_version():
    '''
    Returns version info for freesurfer
    '''
    fs_path = find_freesurfer()
    if fs_path is None:
        raise EnvironmentError("Freesurfer cannot be found. Please check that "
            "it is installed.")
    try:
        fs_buildstamp = os.path.join(os.path.dirname(fs_path),
                'build-stamp.txt')
        with open(fs_buildstamp, "r") as text_file:
            bstamp = text_file.read()
    except:
        return "freesurfer build information not found."
    bstamp = bstamp.replace(os.linesep,'')
    info = "freesurfer:{0}Path: {1}{0}Build Stamp: {2}".format(
            '{}    '.format(os.linesep),fs_path, bstamp)
    return info

def fsl_version():
    '''
    Returns version info for FSL
    '''
    fsl_path = find_fsl()
    if fsl_path is None:
        raise EnvironmentError("FSL not found. Please check that it is "
                "installed")
    try:
        fsl_buildstamp = os.path.join(os.path.dirname(fsl_path), 'etc',
                'fslversion')
        with open(fsl_buildstamp, "r") as text_file:
            bstamp = text_file.read()
    except:
        return "FSL build information not found."
    bstamp = bstamp.replace(os.linesep,'')
    info = "FSL:{0}Path: {1}{0}Version: {2}".format('{}    '.format(os.linesep),
            fsl_path, bstamp)
    return info

def msm_version():
    '''
    Returns version info for msm
    '''
    msm_path = find_msm()
    if not msm_path:
        return "MSM not found."
    try:
        version = util.check_output('msm --version').replace(os.linesep, '')
    except:
        version = ''
    info = "MSM:{0}Path: {1}{0}Version: {2}".format('{}    '.format(os.linesep),
            msm_path, version)
    return info

def ciftify_version(file_name=None):
    '''
    Returns the path and the latest git commit number and date if working from
    a git repo, or the version number if working with an installed copy.
    '''
    logger = logging.getLogger(__name__)

    try:
        version = pkg_resources.get_distribution('ciftify').version
    except pkg_resources.DistributionNotFound:
        # Ciftify not installed, but a git repo, so return commit info
        pass
    else:
        return "Ciftify version {}".format(version)

    try:
        dir_ciftify = util.check_output('which {}'.format(file_name))
    except subprocess.CalledProcessError:
        file_name = None
        dir_ciftify = __file__

    ciftify_path = os.path.dirname(dir_ciftify)
    git_log = get_git_log(ciftify_path)

    if not git_log:
        logger.error("Something went wrong while retrieving git log. Returning "
                "ciftify path only.")
        return "Ciftify:{0}Path: {1}".format(os.linesep, ciftify_path)

    commit_num, commit_date = read_commit(git_log)
    info = "Ciftify:{0}Path: {1}{0}{2}{0}{3}".format('{}    '.format(os.linesep),
            ciftify_path, commit_num, commit_date)

    if not file_name:
        return info

    ## Try to return the file_name's git commit too, if a file was given
    file_log = get_git_log(ciftify_path, file_name)

    if not file_log:
        # File commit info not found
        return info

    commit_num, commit_date = read_commit(file_log)
    info = "{1}{5}Last commit for {2}:{0}{3}{0}{4}".format('{}    '.format(
            os.linesep), info, file_name, commit_num,
            commit_date, os.linesep)

    return info

def get_git_log(git_dir, file_name=None):
    git_cmd = ["cd {}; git log".format(git_dir)]
    if file_name:
        git_cmd.append("--follow {}".format(file_name))
    git_cmd.append("| head")
    git_cmd = " ".join(git_cmd)

    # Silence stderr
    try:
        with open(os.devnull, 'w') as DEVNULL:
            file_log = util.check_output(git_cmd, stderr=DEVNULL)
    except subprocess.CalledProcessError:
        # Fail safe in git command returns non-zero value
        logger = logging.getLogger(__name__)
        logger.error("Unrecognized command: {} "
                "\nReturning empty git log.".format(git_cmd))
        file_log = ""

    return file_log

def read_commit(git_log):
    commit_num = git_log.split(os.linesep)[0]
    commit_num = commit_num.replace('commit', 'Commit:')
    commit_date = git_log.split(os.linesep)[2]
    return commit_num, commit_date

def system_info():
    ''' return formatted version of the system info'''
    sys_info = os.uname()
    sep = '{}    '.format(os.linesep)
    info = "System Info:{0}OS: {1}{0}Hostname: {2}{0}Release: {3}{0}Version: " \
            "{4}{0}Machine: {5}".format(
            sep, sys_info[0], sys_info[1], sys_info[2], sys_info[3],
            sys_info[4])
    return info
