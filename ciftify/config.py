#!/usr/bin/env python
"""
These functions search the environment for software dependencies and configuration.
"""
from __future__ import unicode_literals

import os
import subprocess
import logging
import pkg_resources
import re
import glob

import ciftify.utils as util

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
    dir_fsl = os.path.abspath(shell_val) if shell_val else ''

    if os.path.exists(dir_fsl):
        return dir_fsl

    # If the env var method fails, fall back to using which. This method is
    # not used first because sometimes the executable is installed separately
    # from the rest of the fsl package, making it hard (or impossible) to locate
    # fsl data files based on the returned path
    try:
        dir_fsl = util.check_output('which fsl')
        dir_fsl = '/'.join(dir_fsl.split('/')[:-2])
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

def find_HCP_S1200_GroupAvg():
    """return path to HCP_S900_GroupAvg which should be in ciftify"""
    s1200 = os.path.join(find_ciftify_global(), 'HCP_S1200_GroupAvg_v1')
    return s1200

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
    Returns the ciftify working directory path defined in the environment.
    """
    logger = logging.getLogger(__name__)
    work_dir = os.getenv('CIFTIFY_WORKDIR')
    if work_dir is None:
        work_dir = os.getenv('HCP_DATA')
        if work_dir is not None:
            logger.working("Environment variable HCP_DATA has been deprecated. \
            Please instead use CIFTIFY_WORKDIR in the future.")
        else:
            work_dir = None
    return work_dir

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
    all_info = 'wb_command:{0}Path: {1}{0}{2}'.format(sep,wb_path,wb_v)
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
        fsl_buildstamp = os.path.join(fsl_path, 'etc',
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

    sep = '{}    '.format(os.linesep)
    try:
        version = pkg_resources.get_distribution('ciftify').version
    except pkg_resources.DistributionNotFound:
        # Ciftify not installed, but a git repo, so return commit info
        pass
    else:
        return "ciftify:{0}Version: {1}".format(sep, version)

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
        return "ciftify:{0}Path: {1}".format(sep, ciftify_path)

    commit_num, commit_date = read_commit(git_log)
    info = "ciftify:{0}Path: {1}{0}{2}{0}{3}".format('{}    '.format(sep),
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

class FSLog(object):
    _MAYBE_HALTED = "FS may not have finished running."
    _ERROR = "Exited with error."

    def __init__(self, freesurfer_folder):
        logger = logging.getLogger(__name__)
        self._path = freesurfer_folder
        fs_scripts = os.path.join(freesurfer_folder, 'scripts')
        self.status = self._get_status(fs_scripts)
        self.build = self._get_build(os.path.join(fs_scripts,
                'build-stamp.txt'))
        self.version = self.get_version(self.build)

        try:
            recon_contents = self.parse_recon_done(os.path.join(fs_scripts,
                    'recon-all.done'))
        except:
            logger.warning('Failed to parse the scripts/recon-all.done log')
            recon_contents = {}

        self.subject = self.get_subject(recon_contents.get('SUBJECT', ''))
        self.start = self.get_date(recon_contents.get('START_TIME', ''))
        self.end = self.get_date(recon_contents.get('END_TIME', ''))
        self.kernel = self.get_kernel(recon_contents.get('UNAME', ''))
        self.cmdargs = self.get_cmdargs(recon_contents.get('CMDARGS',''))
        self.args = self.get_args(recon_contents.get('CMDARGS', ''))
        self.nii_inputs = self.get_niftis(recon_contents.get('CMDARGS', ''))


    def read_log(self, path):
        try:
            with open(path, 'r') as log:
                contents = log.readlines()
        except IOError:
            return []
        return contents

    def _get_status(self, scripts):
        error_log = os.path.join(scripts, 'recon-all.error')
        regex = os.path.join(scripts, '*')
        run_logs = [item for item in glob.glob(regex) if 'IsRunning' in item]
        recon_log = os.path.join(scripts, 'recon-all.done')

        if run_logs:
            status = self._MAYBE_HALTED
        elif os.path.exists(error_log):
            status = self._ERROR
        elif os.path.exists(recon_log):
            status = ''
        else:
            raise Exception("No freesurfer log files found for "
                    "{}".format(scripts))

        return status

    def _get_build(self, build_stamp):
        contents = self.read_log(build_stamp)
        if not contents:
            return ''
        return contents[0].strip('\n')

    def get_version(self, build):
        if 'v6.0.0' in build:
            return 'v6.0.0'
        if 'v5.3.0' in build:
            return 'v5.3.0'
        if 'v5.1.0' in build:
            return 'v5.1.0'
        else:
            return 'unknown'

    def parse_recon_done(self, recon_done):
        recon_contents = self.read_log(recon_done)

        if len(recon_contents) < 2:
            # If length is less than two, log is malformed and will cause a
            # crash when the for loop is reached below
            return {}

        parsed_contents = {}
        # Skip first line, which is just a bunch of dashes
        for line in recon_contents[1:]:
            # line = line.decode('utf-8')
            fields = line.strip('\n').split(None, 1)
            parsed_contents[fields[0]] = fields[1]
        return parsed_contents

    def get_subject(self, subject_field):
        if subject_field:
            return subject_field
        subject = os.path.basename(self._path)
        return subject

    def get_date(self, date_str):
        if not date_str:
            return ''
#        return datetime.datetime.strptime(date_str, '%a %b %d %X %Z %Y')
        return date_str

    def get_kernel(self, log_uname):
        if not log_uname:
            return ''
        return log_uname.split()[2]

    def get_cmdargs(self, cmd_args):
        if not cmd_args:
            return ''
        return cmd_args

    @staticmethod
    def get_args(cmd_args):
        if not cmd_args:
            return ''
        cmd_pieces = re.split('^-|\s-', cmd_args)
        args = cmd_pieces
        for item in ['i ', 'T2 ', 'subjid ']:
            args = filter(lambda x: not x.startswith(item), args)
        str_args = ' -'.join(sorted(args))
        return str_args.strip()

    @staticmethod
    def get_niftis(cmd_args):
        if not cmd_args:
            return ''
        # Will break on paths containing white space
        nifti_inputs = re.findall('-i\s*\S*|-T2\s*\S*', cmd_args)
        niftis = [item.strip('-i').strip('-T2').strip() for item in nifti_inputs]
        return '; '.join(niftis)
