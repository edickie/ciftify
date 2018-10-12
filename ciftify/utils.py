#!/usr/bin/env python3
"""
A collection of utilities for the epitome pipeline. Mostly for getting
subject numbers/names, checking paths, gathering information, etc.
"""

import os
import sys
import copy
import datetime
import subprocess
import tempfile
import shutil
import logging
import math
import yaml

import ciftify
logger = logging.getLogger(__name__)

def get_subj(path, user_filter=None):
    """
    Gets all folder names (i.e., subjects) in a directory (of subjects).
    Removes hidden folders.

    user_filter option can be used to return only the subjects that contain
    the given string.

    Warning: Returns a list in python2 and a generator in python3 so always
    wrap the returned value in list() if you require a list.
    """
    subjects = []

    if not os.path.exists(path):
        # return empty list if given bad path
        return subjects

    for subj in next(os.walk(path))[1]:
        subjects.append(subj)
    subjects.sort()
    subjects = filter(lambda x: x.startswith('.') == False, subjects)

    if user_filter:
        subjects = filter(lambda x: user_filter in x, subjects)

    return subjects

def FWHM2Sigma(FWHM):
  ''' convert the FWHM to a Sigma value '''
  if float(FWHM) == 0:
      sigma = 0
  else:
      sigma = float(FWHM) / (2 * math.sqrt(2*math.log(2)))
  return(sigma)


def make_dir(dir_name, dry_run=False, suppress_exists_error = False):
    # Wait till logging is needed to get logger, so logging configuration
    # set in main module is respected
    logger = logging.getLogger(__name__)
    if dry_run:
        logger.debug("Dry-run, skipping creation of directory "\
                "{}".format(dir_name))
        return

    try:
        os.makedirs(dir_name)
    except PermissionError:
        logger.error("You do not have permission to write to {}".format(dir_name))
    except FileExistsError:
        if not suppress_exists_error:
            logger.warning("{} already exists".format(dir_name))
    except OSError:
        logger.error('Could not create directory {}'.format(dir_name))

def check_output_writable(output_file, exit_on_error = True):
    ''' will test if the directory for an output_file exists and can be written too '''
    logger = logging.getLogger(__name__)
    dirname = os.path.dirname(output_file)
    dirname = '.' if dirname == '' else dirname
    result = os.access(dirname, os.W_OK)
    if result == False:
        if exit_on_error:
            logger.error('Directory for output {} does not exist, '
                'or you do not have permission to write there'.format(output_file))
            sys.exit(1)
    return(result)

def check_input_readable(path, exit_on_error = True):
    '''check that path exists and is readable, exits upon failure by default'''
    logger = logging.getLogger(__name__)
    if not os.access(path, os.R_OK):
        logger.error('Input {}, does not exist, or you do not have permission to read it.'
            ''.format(path))
        if exit_on_error:
            sys.exit(1)
    return(path)

def log_arguments(arguments):
    '''send a formatted version of the arguments to the logger'''
    logger = logging.getLogger(__name__)
    input_args = yaml.dump(arguments, default_flow_style=False)
    sep = '{}    '.format(os.linesep)
    input_args2 = input_args.replace(os.linesep,sep)
    input_args3 = input_args2.replace('!!python/object/new:docopt.Dict\ndictitems:','')
    logger.info('Arguments:{0}{1}'.format(sep, input_args3))

def section_header(title):
    '''returns a outlined bit to stick in a log file as a section header'''
    header = '''
-------------------------------------------------------------
{} : {}
-------------------------------------------------------------
'''.format(datetime.datetime.now(),title)
    return(header)

def ciftify_logo():
    ''' this logo is ascii art with fender font'''
    logo = '''

            .|';   ||          .|';
       ''   ||     ||     ''   ||
.|'',  ||  '||'  ''||''   ||  '||'  '||  ||`
||     ||   ||     ||     ||   ||    `|..||
`|..' .||. .||.    `|..' .||. .||.       ||
                                      ,  |'
                                       ''   '''
    return(logo)

def pint_logo():
    ''' logo from ascii text with font fender'''
    logo = """
'||'''|, |''||''| '||\   ||` |''||''|
 ||   ||    ||     ||\\  ||     ||
 ||...|'    ||     || \\ ||     ||
 ||         ||     ||  \\||     ||
.||      |..||..| .||   \||.   .||.
"""
    return(logo)

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass. - Taken from six
    to ensure python 2 and 3 class compatibility"""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

class TempDir(object):
    def __init__(self):
        self.path = None
        return

    def __enter__(self):
        self.path = tempfile.mkdtemp()
        return self.path

    def __exit__(self, type, value, traceback):
        if self.path is not None:
            shutil.rmtree(self.path)

class TempSceneDir(object):
    """
    A context manager for the temporary scene dir.

    A temp dir in the same directory as the hcp data is used for the scene
    file due to the fact that scene files contain a large number of relative
    paths and the images will come out broken if it is put anywhere else.
    """
    def __init__(self, hcp_dir):
        self.base = os.path.join(hcp_dir, 'scene')

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix=self.base)
        return self.dir

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.dir)

class WorkDirSettings(object):
    def __init__(self, arguments):
        logger = logging.getLogger(__name__)
        try:
            temp_dir = arguments['--ciftify-work-dir']
        except KeyError:
            temp_dir = None
        if not temp_dir:
            try:
                temp_dir = arguments['--hcp-data-dir']
                if temp_dir:
                    logger.warning("Argument --hcp-data-dir has been deprecated. "
                    "Please instead use --ciftify-work-dir in the future.")
            except KeyError:
                temp_dir = None
        try:
            temp_subject = arguments['<subject>']
        except KeyError:
            temp_subject = None
        self.work_dir = self.__set_work_dir(temp_dir, temp_subject)

    def __set_work_dir(self, user_dir, subject):
        # Wait till logging is needed to get logger, so logging configuration
        # set in main module is respected
        logger = logging.getLogger(__name__)
        if user_dir:
            return os.path.realpath(user_dir)
        if subject == 'HCP_S1200_GroupAvg':
            return None
        found_dir = ciftify.config.find_work_dir()
        if found_dir is None:
            logger.error("Cannot find working directory, exiting.")
            sys.exit(1)
        return os.path.realpath(found_dir)

def get_registration_mode(arguments):
    """
    Insures that the --surf-reg argument is either FS or MSMSulc
    """
    if arguments['--surf-reg'] == "MSMSulc":
        return 'MSMSulc'
    if arguments['--surf-reg'] == "FS":
        return 'FS'
    else:
        logger.error('--surf-reg must be either "MSMSulc" or "FS"')
        sys.exit(1)

class WorkFlowSettings(WorkDirSettings):
    '''
    A convenience class for parsing settings that are shared
    by ciftify_recon_all and ciftify_subject_fmri
    '''
    def __init__(self, arguments):
        WorkDirSettings.__init__(self, arguments)
        self.FSL_dir = self.__set_FSL_dir()

        # Read settings from yaml
        self.__config = self.__read_settings(arguments['--ciftify-conf'])
        self.high_res = self.get_config_entry('high_res')
        self.low_res = self.get_config_entry('low_res')
        self.grayord_res = self.get_config_entry('grayord_res')
        self.n_cpus = get_number_cpus(arguments['--n_cpus'])

    def __set_FSL_dir(self):
        fsl_dir = ciftify.config.find_fsl()
        if fsl_dir is None:
            logger.error("Cannot find FSL dir, exiting.")
            sys.exit(1)
        fsl_data = os.path.normpath(os.path.join(fsl_dir, 'data'))
        if not os.path.exists(fsl_data):
            logger.warn("Found {} for FSL path but {} does not exist. May "
                    "prevent registration files from being found.".format(
                    fsl_dir, fsl_data))
        return fsl_dir

    def __read_settings(self, yaml_file):
        if yaml_file is None:
            yaml_file = os.path.join(ciftify.config.find_ciftify_global(),
                    'ciftify_workflow_settings.yaml')
        if not os.path.exists(yaml_file):
            logger.critical("Settings yaml file {} does not exist"
                "".format(yaml_file))
            sys.exit(1)

        try:
            with open(yaml_file, 'r') as yaml_stream:
                config = yaml.load(yaml_stream)
        except:
            logger.critical("Cannot read yaml config file {}, check formatting."
                    "".format(yaml_file))
            sys.exit(1)

        return config

    def get_config_entry(self, key):
        try:
            config_entry = self.__config[key]
        except KeyError:
            logger.critical("{} not defined in cifti recon settings".format(key))
            sys.exit(1)
        return config_entry

    def get_resolution_config(self, method, standard_res):
        """
        Reads the method and resolution settings.
        """
        method_config = self.get_config_entry(method)
        try:
            resolution_config = method_config[standard_res]
        except KeyError:
            logger.error("Registration resolution {} not defined for method "
                    "{}".format(standard_res, method))
            sys.exit(1)

        for key in resolution_config.keys():
            ## The base dir (FSL_dir currently) may need to change when new
            ## resolutions/methods are added
            reg_item = os.path.join(self.FSL_dir, resolution_config[key])
            if not os.path.exists(reg_item):
                logger.error("Item required for registration does not exist: "
                        "{}".format(reg_item))
                sys.exit(1)
            resolution_config[key] = reg_item
        return resolution_config

def get_number_cpus(user_n_cpus = None):
    ''' reads the number of CPUS available for multithreaded processes
    either from a user argument, or from the enviroment'''
    if user_n_cpus:
        try:
            n_cpus = int(user_n_cpus)
        except:
            logger.critical('Could note read --n_cpus entry {} as integer'.format(user_n_cpus))
            sys.exit(1)
    else:
        n_cpus = os.getenv('OMP_NUM_THREADS')
    # if all else fails..set n_cpus to 1
    if not n_cpus:
        n_cpus = 1
    return n_cpus

class VisSettings(WorkDirSettings):
    """
    A convenience class. Provides a work_dir and qc_dir attribute and a
    function to set each based on the user's input and the environment.
    This is intended to be inherited from in each script, so that user
    settings can be passed together and easily kept track of.

    Arguments:      A docopt parsed dictionary of the user's input arguments.
    qc_mode:        The qc_mode to operate in and the string to include
                    in the qc output folder name.

    Will raise SystemExit if the user hasn't set the ciftify-work-dir/hcp-data-dir
    and the environment variable isn't set.
    """
    def __init__(self, arguments, qc_mode):
        WorkDirSettings.__init__(self, arguments)
        try:
            temp_qc = arguments['--qcdir']
        except KeyError:
            temp_qc = None
        try:
            self.debug_mode = arguments['--debug']
        except KeyError:
            self.debug_mode = False
        self.qc_mode = qc_mode
        self.qc_dir = self.__set_qc_dir(temp_qc)

    def __set_qc_dir(self, user_qc_dir):
        if user_qc_dir:
            return user_qc_dir
        qc_dir = os.path.join(self.work_dir, 'qc_{}'.format(self.qc_mode))
        return qc_dir

def run(cmd, dryrun=False,
        suppress_stdout=False,
        suppress_echo = False,
        suppress_stderr = False,
        env = None):
    """
    Runs command in default shell, returning the return code and logging the
    output. It can take a cmd argument as a string or a list.
    If a list is given, it is joined into a string. There are some arguments
    for changing the way the cmd is run:
       dryrun:          Do not actually run the command (for testing) (default:
                        False)
       suppress_echo:    echo's command to debug steam (default is info)
       suppress_stdout:  Any standard output from the function is printed to
                        the log at "debug" level but not "info"
       suppress_stderr: Send error message to stdout...for situations when
                        program logs info to stderr stream..urg
       env: a dict of environment variables to add to the subshell
            (this can be a useful may to restrict CPU usage of the subprocess)
    """
    # Wait till logging is needed to get logger, so logging configuration
    # set in main module is respected
    logger = logging.getLogger(__name__)

    if type(cmd) is list:
        cmd = ' '.join(cmd)

    if suppress_echo:
        logger.debug("Running: {}".format(cmd))
    else:
        logger.info("Running: {}".format(cmd))

    if dryrun:
        logger.info('Doing a dryrun')
        return 0

    merged_env = os.environ
    if env:
        merged_env.update(env)

    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=merged_env)
    out, err = p.communicate()
    # py3 compability :(
    out = out.decode('utf-8')
    err = err.decode('utf-8')

    if p.returncode:
        logger.error('cmd: {} \n Failed with returncode {}'.format(cmd,
                p.returncode))
    if len(out) > 0:
        if suppress_stdout:
            logger.debug(out)
        else:
            logger.info(out)
    if len(err) > 0:
        if suppress_stderr:
            logger.info(err)
        else:
            logger.warning(err)

    return p.returncode

class cd(object):
    """
    A context manager for changing directory. Since best practices dictate
    returning to the original directory, saves the original directory and
    returns to it after the block has exited.

    May raise OSError if the given path doesn't exist (or the current directory
    is deleted before switching back)
    """

    def __init__(self, path):
        user_path = os.path.expanduser(path)
        self.new_path = os.path.expandvars(user_path)

    def __enter__(self):
        self.old_path = os.getcwd()
        os.chdir(self.new_path)

    def __exit__(self, e, value, traceback):
        os.chdir(self.old_path)

def get_stdout(cmd_list, echo=True):
   ''' run the command given from the cmd list and report the stdout result

   Input: A command list'''
   logger = logging.getLogger(__name__)
   if echo: logger.info('Evaluating: {}'.format(' '.join(cmd_list)))
   stdout = subprocess.check_output(cmd_list)
   return stdout.decode('utf-8')

def check_output(command, stderr=None, shell = True):
    """ Ensures python 3 compatibility by always decoding the return value of
    subprocess.check_output

    Input: A command string"""
    output = subprocess.check_output(command, shell=shell, stderr=stderr)
    return output.decode('utf-8')

def ciftify_log_endswith_done(ciftify_log):
    '''return true with the ciftify log file exists and ends with the word Done'''
    if not os.path.isfile(ciftify_log):
        return False
    with open(ciftify_log, 'r') as f:
        lines = f.read().splitlines()
        last_line = lines[-3]
        is_done = True if 'Done' in last_line else False
    return is_done

def has_ciftify_recon_all_run(ciftify_work_dir, subject):
    '''determine if ciftify_recon_all has already completed'''
    ciftify_log = os.path.join(ciftify_work_dir,
                        subject,
                        'cifti_recon_all.log')
    return ciftify_log_endswith_done(ciftify_log)

def has_ciftify_fmri_run(subject, fmriname, ciftify_work_dir):
    '''determine if ciftify_recon_all has already completed'''
    ciftify_log = os.path.join(ciftify_work_dir,
                        subject,
                        'MNINonLinear', 'Results', fmriname,
                        'ciftify_subject_fmri.log')
    # print('ciftify_subject_fmri done {}'.format(ciftify_log_endswith_done(ciftify_log)))
    return ciftify_log_endswith_done(ciftify_log)
