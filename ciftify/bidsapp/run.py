#!/usr/bin/env python3
"""
Runs a combination of fmriprep and ciftify pipelines from BIDS specification

Usage:
  run.py <bids_dir> <output_dir> <analysis_level> [options]

Arguments:
    <bids_dir>               The directory with the input dataset formatted
                             according to the BIDS standard.
    <output_dir>             The directory where the output files should be stored.
                             If you are running ciftify on a partially run analyses see below.
    <analysis_level>         Analysis level to run (participant or group)

Options:
  --participant_label=<subjects>  String or Comma separated list of participants to process. Defaults to all.
  --task_label=<tasks>            String or Comma separated list of fmri tasks to process. Defaults to all.
  --session_label=<sessions>      String or Comma separated list of sessions to process. Defaults to all.
  --anat_only                     Only run the anatomical pipeline.
  --fmriprep-workdir PATH         Path to working directory for fmriprep
  --fs-license FILE               The freesurfer license file
  --ignore-fieldmaps              Will ignore available fieldmaps and use syn-sdc for fmriprep
  --no-SDC                        Will do  fmriprep distortion correction at all (NOT recommended)
  --fmriprep-args="args"          Additional user arguments that may be added to fmriprep stages
  --resample-to-T1w32k            Resample the Meshes to 32k Native (T1w) Space
  --surf-reg REGNAME              Registration sphere prefix [default: MSMSulc]
  --no-symlinks                   Will not create symbolic links to the zz_templates folder
  --SmoothingFWHM FWHM            Full Width at Half MAX for optional fmri cifti smoothing
  --MSM-config PATH               EXPERT OPTION. The path to the configuration file to use for
                                  MSMSulc mode. By default, the configuration file
                                  is ciftify/data/hcp_config/MSMSulcStrainFinalconf
                                  This setting is ignored when not running MSMSulc mode.
  --ciftify-conf YAML             EXPERT OPTION. Path to a yaml configuration file. Overrides
                                  the default settings in
                                  ciftify/data/ciftify_workflow_settings.yaml
  --n_cpus INT                    Number of cpu's available. Defaults to the value
                                  of the OMP_NUM_THREADS environment variable
  -v,--verbose                    Verbose logging
  --debug                         Debug logging in Erin's very verbose style
  -n,--dry-run                    Dry run
  -h,--help                       Print help

DETAILS

Adapted from modules of the Human Connectome
Project's minimal proprocessing pipeline. Please cite:

Glasser MF, Sotiropoulos SN, Wilson JA, Coalson TS, Fischl B, Andersson JL, Xu J,
Jbabdi S, Webster M, Polimeni JR, Van Essen DC, Jenkinson M, WU-Minn HCP Consortium.
The minimal preprocessing pipelines for the Human Connectome Project. Neuroimage. 2013 Oct 15;80:105-24.
PubMed PMID: 23668970; PubMed Central PMCID: PMC3720813.

The default outputs are condensed to include in 4 mesh "spaces" in the following directories:
  + T1w/Native: The freesurfer "native" output meshes
  + MNINonLinear/Native: The T1w/Native mesh warped to MNINonLinear
  + MNINonLinear/fsaverage_LR32k
     + the surface registered space used for fMRI and multi-modal analysis
     + This 32k mesh has approx 2mm vertex spacing
  + MNINonLinear_164k_fs_LR (in the MNINonLinear folder):
     + the surface registered space used for HCP's anatomical analysis
     + This 164k mesh has approx 0.9mm vertex spacing

In addition, the optional flag '--resample-to-T1w32k' can be used to output an
additional T1w/fsaverage_LR32k folder that occur in the HCP Consortium Projects.

By default, some to the template files needed for resampling surfaces and viewing
flatmaps will be symbolic links from a folder ($CIFTIFY_WORKDIR/zz_templates) to the
subject's output folder. If the --no-symlinks flag is indicated, these files will be
copied into the subject folder insteadself.

Written by Erin W Dickie
"""

import os.path
import sys
from bids.grabbids import BIDSLayout
import ciftify.utils
from ciftify.utils import run, get_number_cpus, section_header
import logging
from docopt import docopt

DRYRUN = False

# Read logging.conf
logger = logging.getLogger('ciftify')
logger.setLevel(logging.DEBUG)

class Settings(object):
    def __init__(self, arguments):
        self.bids_dir = arguments['<bids_dir>']
        self.bids_layout = self.__get_bids_layout()
        self.fs_dir, self.fmriprep_dir, self.ciftify_work_dir = self.__set_derivatives_dirs(arguments['<output_dir>'])
        self.analysis_level = self.__get_analysis_level(arguments['<analysis_level>'])
        self.participant_labels = self.__get_participants(arguments['--participant_label'])
        self.sessions = self.__get_sessions(arguments['--session_label'])
        self.tasks = self.__get_tasks(arguments['--task_label'])
        self.surf_reg = self.__set_registration_mode(arguments)
        self.resample_to_T1w32k = arguments['--resample-to-T1w32k']
        self.no_symlinks = arguments['--no-symlinks']
        self.n_cpus = ciftify.utils.get_number_cpus(arguments['--n_cpus'])
        self.fmriprep_vargs = arguments['--fmriprep-args']
        self.fs_license = self.__get_freesurfer_license(arguments['--fs-license'])
        self.fmriprep_work = self.__get_fmriprep_work(arguments['--fmriprep-workdir'])
        self.fmri_smooth_fwhm = arguments['--SmoothingFWHM']
        self.ignore_fieldmaps = arguments['--ignore-fieldmaps']
        self.no_sdc = arguments['--no-SDC']
        self.anat_only = arguments['--anat_only']

    def __get_bids_layout(self):
        '''run the BIDS validator and produce the bids_layout'''
        run("bids-validator {}".format(self.bids_dir),  dryrun = DRYRUN)
        try:
            layout = BIDSLayout(self.bids_dir, exclude=['derivatives'])
        except:
            logger.critical('Could not parse <bids_dir> {}'.format(self.bids_dir))
            sys.exit(1)
        return layout

    def __set_derivatives_dirs(self, output_dir_arg):
        '''define the three derivates directories from the output flag'''
        fs_dir = os.path.join(output_dir_arg, 'freesurfer')
        fmriprep_dir = os.path.join(output_dir_arg, 'fmriprep')
        ciftify_work_dir = os.path.join(output_dir_arg, 'ciftify')
        return fs_dir, fmriprep_dir, ciftify_work_dir

    def __get_analysis_level(self, ana_user_arg):
        if ana_user_arg == "participant":
            return "participant"
        if ana_user_arg == "group":
            return "group"
        logger.critical('<analysis_level> must be "participant" or "group", {} given'.format(ana_user_arg))

    def parse_comma_sep_arg(self, list_argument):
        ''' parse a comma separated list arg to return list'''
        list_argument = str(list_argument)
        return list_argument.split(',')

    def __get_participants(self, participant_user_arg):
        '''get the subjects, check that they are in bids_dir'''
        all_subjects = self.bids_layout.get_subjects()
        if participant_user_arg:
            subjects_to_analyze = participant_user_arg.split(",")
            for subject in subjects_to_analyze:
                if subject not in all_subjects:
                    logger.warning("sub-{} not in bids_dir".format(subject))
        # for all subjects
        else:
            subjects_to_analyze = all_subjects
        return subjects_to_analyze

    def __get_sessions(self, sessions_user_arg):
        '''get all sessions, check that they are in bids_layout'''
        all_sessions = self.bids_layout.get_sessions()
        if sessions_user_arg:
            sessions_to_analyze = sessions_user_arg.split(",")
            for session in sessions_to_analyze:
                if session not in all_sessions:
                    logger.warning("sess-{} not in bids_dir".format(session))
        # for all subjects
        else:
            sessions_to_analyze = all_sessions
        return sessions_to_analyze

    def __get_tasks(self, tasks_user_arg):
        '''get all sessions, check that they are in bids_layout'''
        all_tasks = self.bids_layout.get_tasks()
        if tasks_user_arg:
            tasks_to_analyze = tasks_user_arg.split(",")
            for task in tasks_to_analyze:
                if task not in all_tasks:
                    logger.warning("task-{} not in bids_dir".format(task))
        # for all subjects
        else:
            tasks_to_analyze = all_tasks
        return tasks_to_analyze

    def __set_registration_mode(self, arguments):
        """
        Must be set after ciftify_data_dir is set, since it requires this
        for MSMSulc config
        """
        surf_reg = ciftify.utils.get_registration_mode(arguments)
        if surf_reg == "MSMSulc":
            ciftify.config.verify_msm_available()
            user_config = arguments['--MSM-config']
            if not user_config:
                self.msm_config = os.path.join(ciftify.config.find_ciftify_global(),
                        'hcp_config', 'MSMSulcStrainFinalconf')
            elif user_config and not os.path.exists(user_config):
                logger.error("MSM config file {} does not exist".format(user_config))
                sys.exit(1)
            else:
                self.msm_config = user_config
        return surf_reg

    def __get_freesurfer_license(self, fs_license_arg):
        '''check that freesurfer license is readable'''
        fs_license_file = fs_license_arg
        if fs_license_file:
            ciftify.utils.check_input_readable(fs_license_file)
        return fs_license_file

    def __get_fmriprep_work(self, work_arg):
        '''check fmriprep's work dir, if specified, is writable'''
        workdir = work_arg
        if workdir:
            ciftify.utils.check_output_writable(workdir)
        return workdir

def run_group_workflow(settings):
    ''' run the QC tools index mode '''
    run('cifti_vis_recon_all index --ciftify-work-dir {ciftify_work_dir}'.format(
        ciftify_work_dir = settings.ciftify_work_dir), dryrun = DRYRUN)
    run('cifti_vis_fmri index --ciftify-work-dir {ciftify_work_dir}'.format(
        ciftify_work_dir = settings.ciftify_work_dir), dryrun = DRYRUN)

def run_participant_workflow(settings):
    '''run all participants through participant workflow'''
    for participant_label in settings.participant_labels:
        run_one_participant(settings, participant_label)

def run_one_participant(settings, participant_label):
    ''' the main workflow'''

    # anat bit
    find_or_build_fs_dir(settings, participant_label)

    # run ciftify_recon_all
    run_ciftify_recon_all(settings, participant_label)

    if settings.anat_only:
        return

    bolds = find_participant_bold_inputs(participant_label, settings)

    for bold_input in bolds:
        bold_preproc, fmriname = find_bold_preproc(bold_input, settings)
        if not os.path.isfile(bold_preproc):
            logger.info('Preprocessed bold {} not found, running fmriprep'.format(bold_preproc))
            #to-add run_fmriprep for this subject (make sure --space)
            run_fmriprep_func(bold_input, settings)

        run_ciftify_subject_fmri(participant_label, bold_preproc, fmriname, settings)
    return

def find_or_build_fs_dir(settings, participant_label):
    '''either finds a freesurfer output folder in the outputs
    if the freesurfer output are not run..it runs the fmriprep anat pipeline'''
    fs_sub_dir = os.path.join(settings.fs_dir,
                             'sub-{}'.format(participant_label))
    ## check for a wmparc file to insure that freesurfer probably finished
    if os.path.isfile(os.path.join(fs_sub_dir, 'mri', 'wmparc.mgz')):
        logger.info("Found freesurfer outputs for sub-{}".format(participant_label))
        return
    else:
        cmd = ['fmriprep', settings.bids_dir, os.path.dirname(settings.fmriprep_dir),
            'participant', '--participant_label', participant_label,
            '--anat-only', '--output-space T1w template',
            '--nthreads', str(settings.n_cpus),
            '--omp-nthreads', str(settings.n_cpus)]
        if settings.fmriprep_work:
            cmd.extend(['--work-dir',settings.fmriprep_work])
        if settings.fs_license:
            cmd.extend(['--fs-license-file', settings.fs_license])
        if settings.fmriprep_vargs:
            cmd.append(settings.fmriprep_vargs)
        run(cmd, dryrun = DRYRUN)

def run_ciftify_recon_all(settings, participant_label):
    '''construct ciftify_recon_all command line call and run it'''
    if has_ciftify_recon_all_run(settings, participant_label):
        logger.info("Found ciftify anat outputs for sub-{}".format(participant_label))
        return
    run_cmd = ['ciftify_recon_all',
            '--n_cpus', str(settings.n_cpus),
            '--ciftify-work-dir', settings.ciftify_work_dir,
            '--fs-subjects-dir', settings.fs_dir,
            '--surf-reg', settings.surf_reg,
            'sub-{}'.format(participant_label)]
    if settings.resample_to_T1w32k:
        run_cmd.insert(1,'--resample-to-T1w32k')
    if settings.no_symlinks:
        run_cmd.insert(1,'--no-symlinks')
    run(run_cmd, dryrun = DRYRUN, env={'FS_LICENSE': settings.fs_license})
    run(['cifti_vis_recon_all', 'subject',
        '--ciftify-work-dir',settings.ciftify_work_dir,
        'sub-{}'.format(participant_label)], dryrun = DRYRUN,
        env={'FS_LICENSE': settings.fs_license})

def has_ciftify_recon_all_run(settings, participant_label):
    '''determine if ciftify_recon_all has already completed'''
    ciftify_log = os.path.join(settings.ciftify_work_dir,
                        'sub-{}'.format(participant_label),
                        'cifti_recon_all.log')
    if not os.path.isfile(ciftify_log):
        return False
    with open(ciftify_log, 'r') as f:
        lines = f.read().splitlines()
        last_line = lines[-3]
        is_done = True if 'Done' in last_line else False
    if is_done == True:
        logger.info("Found ciftify anat outputs for sub-{}".format(participant_label))
    else:
        logger.warning("ciftify anat outputs for sub-{} are not complete, consider deleting ciftify outputs and rerunning.".format(participant_label))
    return True

def find_participant_bold_inputs(participant_label, settings):
    '''find all the bold files in the bids layout'''
    bolds = []
    for task in settings.tasks:
        if len(settings.sessions) > 0:
            for session in settings.sessions:
                bolds.extend(settings.bids_layout.get(subject = participant_label,
                                                   type="bold",
                                                   session = session,
                                                   task = task,
                                                   extensions=["nii.gz", "nii"]))
        else:
            # find the bold_preproc abouts in the func derivates
            bolds.extend(settings.bids_layout.get(
                                        subject = participant_label,
                                        type="bold",
                                        task = task,
                                        extensions=["nii.gz", "nii"]))
    return bolds

def find_bold_preproc(bold_input, settings):
    ''' find the T1w preproc file for specified BIDS dir bold input
    return the func input filename and task_label input for ciftify_subject_fmri'''
    bold_inputfile = bold_input.filename
    fmriname = "_".join(bold_inputfile.split("sub-")[-1].split("_")[1:]).split(".")[0]
    assert fmriname
    try:
        session = bold_input.session
    except:
        session = None
    if session:
        preproc_dir = os.path.join(settings.fmriprep_dir,
                        'sub-{}'.format(bold_input.subject),
                        'ses-{}'.format(session),
                        'func')
    else:
        preproc_dir = os.path.join(settings.fmriprep_dir,
                        'sub-{}'.format(bold_input.subject),
                        'func')
    bold_preproc = os.path.join(preproc_dir,
                    'sub-{}_{}_space-T1w_preproc.nii.gz'.format(bold_input.subject,
                                                                fmriname))
    return bold_preproc, fmriname

def run_fmriprep_func(bold_input, settings):
    '''runs fmriprep with combo of user args and required args for ciftify'''
    # if feildmaps are available use default settings
    fieldmap_list = settings.bids_layout.get_fieldmap(bold_input.filename, return_list = True)
    if len(fieldmap_list) > 0 :
        if settings.no_sdc:
            fieldmap_arg = "--ignore fieldmaps"
        elif settings.ignore_fieldmaps:
            fieldmap_arg = "--ignore fieldmaps --use-syn-sdc"
        else:
            fieldmap_arg = ''
    else:
        fieldmap_arg = '--use-syn-sdc'
        if settings.no_sdc:
            fieldmap_arg = ""
    # if not, run with syn-dc
    fcmd = ['fmriprep', settings.bids_dir, os.path.dirname(settings.fmriprep_dir),
        'participant', '--participant_label', bold_input.subject,
        '-t', bold_input.task,
        '--output-space T1w template',
        fieldmap_arg,
        '--nthreads', str(settings.n_cpus),
        '--omp-nthreads', str(settings.n_cpus)]
    if settings.fmriprep_work:
        fcmd.extend(['--work-dir',settings.fmriprep_work])
    if settings.fs_license:
        fcmd.extend(['--fs-license-file', settings.fs_license])
    if settings.fmriprep_vargs:
        fcmd.append(settings.fmriprep_vargs)
    run(fcmd, dryrun = DRYRUN)


def run_ciftify_subject_fmri(participant_label, bold_preproc, fmriname, settings):
    '''run ciftify_subject_fmri for the bold file plus the vis function'''
    cmd = ['ciftify_subject_fmri',
        '--n_cpus', str(settings.n_cpus),
        '--ciftify-work-dir', settings.ciftify_work_dir,
        '--surf-reg', settings.surf_reg,
        bold_preproc,
        'sub-{}'.format(participant_label),
        fmriname]
    if settings.fmri_smooth_fwhm:
        cmd.insert(3, '--SmoothingFWHM {}'.format(settings.fmri_smooth_fwhm))
    run(cmd, dryrun = DRYRUN)

    vis_cmd = ['cifti_vis_fmri', 'subject',
    '--ciftify-work-dir', settings.ciftify_work_dir,
    fmriname, 'sub-{}'.format(participant_label)]
    if settings.fmri_smooth_fwhm:
        vis_cmd.insert(2, '--SmoothingFWHM {}'.format(settings.fmri_smooth_fwhm))
    run(vis_cmd, dryrun = DRYRUN)

def main():

    global DRYRUN

    arguments  = docopt(__doc__)
    verbose      = arguments['--verbose']
    debug        = arguments['--debug']
    DRYRUN       = arguments['--dry-run']

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    if verbose:
        ch.setLevel(logging.INFO)

    if debug:
        ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Get settings, and add an extra handler for the current log
    settings = Settings(arguments)

    logger.info('{}'.format(ciftify.utils.ciftify_logo()))

    if settings.analysis_level == "group":
        logger.info(section_header("Starting ciftify group"))
        ret = run_group_workflow(settings)

    if settings.analysis_level == "participant":
        logger.info(section_header("Starting ciftify participant"))
        ret = run_participant_workflow(settings)

    logger.info(section_header("Done"))
    sys.exit(ret)

if __name__=='__main__':
    main()
