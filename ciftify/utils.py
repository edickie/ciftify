#!/usr/bin/env python
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
  if int(FWHM) == 0:
      sigma = 0
  else:
      sigma = float(FWHM) / (2 * math.sqrt(2*math.log(2)))
  return(sigma)


def make_dir(dir_name, dry_run=False):
    # Wait till logging is needed to get logger, so logging configuration
    # set in main module is respected
    logger = logging.getLogger(__name__)
    if dry_run:
        logger.debug("Dry-run, skipping creation of directory "\
                "{}".format(dir_name))
        return

    try:
        os.makedirs(dir_name)
    except OSError:
        logger.debug("{} already exists.".format(dir_name))

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

class HCPSettings(object):
    def __init__(self, arguments):
        logger = logging.getLogger(__name__)
        try:
            temp_hcp = arguments['--ciftify-work-dir']
        except KeyError:
            try:
                temp_hcp = arguments['--hcp-data-dir']
                logger.warning("Argument --hcp-data-dir has been deprecated. \
                Please instead use --ciftify-work-dir in the future.")
            except KeyError:
                temp_hcp = None
        try:
            temp_subject = arguments['<subject>']
        except KeyError:
            temp_subject = None
        self.hcp_dir = self.__set_hcp_dir(temp_hcp, temp_subject)

    def __set_hcp_dir(self, user_dir, subject):
        # Wait till logging is needed to get logger, so logging configuration
        # set in main module is respected
        logger = logging.getLogger(__name__)
        if user_dir:
            return os.path.realpath(user_dir)
        if subject == 'HCP_S1200_GroupAvg':
            return None
        found_dir = ciftify.config.find_hcp_data()
        if found_dir is None:
            logger.error("Cannot find HCP data directory, exiting.")
            sys.exit(1)
        return os.path.realpath(found_dir)

class VisSettings(HCPSettings):
    """
    A convenience class. Provides an hcp_dir and qc_dir attribute and a
    function to set each based on the user's input and the environment.
    This is intended to be inherited from in each script, so that user
    settings can be passed together and easily kept track of.

    Arguments:      A docopt parsed dictionary of the user's input arguments.
    qc_mode:        The qc_mode to operate in and the string to include
                    in the qc output folder name.

    Will raise SystemExit if the user hasn't set the hcp-data-dir and the
    environment variable isn't set.
    """
    def __init__(self, arguments, qc_mode):
        HCPSettings.__init__(self, arguments)
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
        qc_dir = os.path.join(self.hcp_dir, 'qc_{}'.format(self.qc_mode))
        return qc_dir

def run(cmd, dryrun=False,
        suppress_stdout=False,
        suppress_echo = False,
        suppress_stderr = False):
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

    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
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
