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
  --rerun-if-incomplete           Will delete and rerun ciftify workflows if incomplete outputs are found.

  --read-from-derivatives PATH    Indicates pre-ciftify will be read from
                                  the indicated derivatives path and freesurfer/fmriprep will not be run
  --func-preproc-dirname STR      Name derivatives folder where func derivatives are found [default: fmriprep]
  --func-preproc-desc TAG         The bids desc tag [default: preproc] assigned to the preprocessed file
  --older-fmriprep                Read from fmriprep derivatives that are version 1.1.8 or older

  --fmriprep-workdir PATH         Path to working directory for fmriprep
  --fs-license FILE               The freesurfer license file
  --n_cpus INT                    Number of cpu's available. Defaults to the value
                                  of the OMP_NUM_THREADS environment variable
  --ignore-fieldmaps              Will ignore available fieldmaps and use syn-sdc for fmriprep
  --no-SDC                        Will not do fmriprep distortion correction at all (NOT recommended)
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
These outputs can be critical for those building masks for DWI tract tracing.

By default, some to the template files needed for resampling surfaces and viewing
flatmaps will be symbolic links from a folder ($CIFTIFY_WORKDIR/zz_templates) to the
subject's output folder. If the --no-symlinks flag is indicated, these files will be
copied into the subject folder insteadself.

Written by Erin W Dickie
"""

import os.path
import sys
import shutil
from bids.layout import BIDSLayout
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
        self.ciftify_work_dir = os.path.join(arguments['<output_dir>'], 'ciftify')
        self.run_fmriprep, self.fs_dir, self.func_derivs_dir = self.__set_derivs_dirs(
                                arguments['<output_dir>'],
                                arguments['--read-from-derivatives'],
                                arguments['--func-preproc-dirname'])
        self.bids_layout = self.__get_bids_layout()
        self.analysis_level = self.__get_analysis_level(arguments['<analysis_level>'])
        self.participant_labels = self.__get_from_bids_layout(arguments['--participant_label'], 'subject')
        self.sessions = self.__get_from_bids_layout(arguments['--session_label'], 'session')
        self.tasks = self.__get_from_bids_layout(arguments['--task_label'], 'task')
        self.surf_reg = self.__set_registration_mode(arguments)
        self.resample_to_T1w32k = arguments['--resample-to-T1w32k']
        self.no_symlinks = arguments['--no-symlinks']
        self.n_cpus = ciftify.utils.get_number_cpus(arguments['--n_cpus'])
        self.fmriprep_vargs = self.__set_fmriprep_arg(arguments, '--fmriprep-args')
        self.fs_license = self.__get_freesurfer_license(arguments['--fs-license'])
        self.fmriprep_work = self.__get_fmriprep_work(arguments,'--fmriprep-workdir')
        self.fmri_smooth_fwhm = arguments['--SmoothingFWHM']
        self.ignore_fieldmaps = self.__set_fmriprep_arg(arguments, '--ignore-fieldmaps')
        self.no_sdc = self.__set_fmriprep_arg(arguments, '--no-SDC')
        self.anat_only = arguments['--anat_only']
        self.rerun = arguments['--rerun-if-incomplete']
        self.old_fmriprep_derivs = arguments['--older-fmriprep']
        self.preproc_desc = arguments['--func-preproc-desc']

    def __set_derivs_dirs(self, output_dir_arg, derivs_dir_arg, func_derivs):
        '''define the location of freesurfer and functional derivatives from user inputs
        if no optional paths are set, freesurfer and fmriprep outputs will be generated in the <output_path>
        '''
        if derivs_dir_arg:
            run_fmriprep = False
            derivs_base = derivs_dir_arg
        else:
            run_fmriprep = True
            derivs_base = output_dir_arg
        fs_dir = os.path.join(derivs_base, 'freesurfer')
        func_derivs_dir = os.path.join(derivs_base, func_derivs)
        return run_fmriprep, fs_dir, func_derivs_dir

    def __set_fmriprep_arg(self, arguments, option_to_check):
        '''sets an user option for fmriprep workflow only if run_fmriprep is set'''
        if not arguments[option_to_check]:
            return arguments[option_to_check]
        if not self.run_fmriprep:
            logger.error('Sorry the argument {} cannot be combined with --read-from-derivatives because fmriprep will not be run'.format(
            option_to_check))
            sys.exit()
        return arguments[option_to_check]

    def __get_bids_layout(self):
        '''run the BIDS validator and produce the bids_layout'''
        run("bids-validator {}".format(self.bids_dir),  dryrun = DRYRUN)
        try:
            layout = BIDSLayout(self.bids_dir, exclude=['derivatives'])
        except:
            logger.critical('Could not parse <bids_dir> {}'.format(self.bids_dir))
            sys.exit(1)
        return layout

    def __get_analysis_level(self, ana_user_arg):
        if ana_user_arg == "participant":
            return "participant"
        if ana_user_arg == "group":
            return "group"
        logger.critical('<analysis_level> must be "participant" or "group", {} given'.format(ana_user_arg))
        sys.exit(1)

    def __get_from_bids_layout(self, user_arg, entity):
        '''for a given BIDSLayout entity, check the layout against the user arguments'''
        all_ids = self.bids_layout.get(return_type = "id", target = entity)
        if user_arg:
            ids_to_analyze = user_arg.split(",")
            for label in ids_to_analyze:
                if label not in all_ids:
                    logger.critical("{} {} not in bids_dir".format(entity, label))
                    sys.exit(1)
        # for all subjects
        else:
            ids_to_analyze = all_ids
        return ids_to_analyze

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

    def __get_fmriprep_work(self, arguments, work_arg):
        '''check fmriprep's work dir, if specified, is writable'''
        workdir = self.__set_fmriprep_arg(arguments, work_arg)
        if workdir:
            # note: check output writeble tests the directory above a path...giving it a fake file
            ciftify.utils.check_output_writable(os.path.join(workdir, 'testworkstuff.txt'))
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

        if settings.run_fmriprep:
            # run fmriprep if its allowed

            bold_preproc = find_bold_preprocs(bold_input, settings)
            if len(bold_preproc) < 1:
                logger.info('Preprocessed derivative for bold {} not found, running fmriprep'.format(bold_input))
                #to-add run_fmriprep for this subject (make sure --space)
                run_fmriprep_func(bold_input, settings)

        # now read in as many preproc outputs as you can find...
        # note that find_bold_preproc always outputs a list
        bold_preprocs = find_bold_preprocs(bold_input, settings)

        # print error and exit if we can't find and output at this point
        if len(bold_preprocs) < 1:
            logger.error('No preprocessed derivative for bold {} not found. Skipping ciftify_subject_fmri. Please check preprocessing pipeline for errors'.format(bold_input))
        
        else :
            # if we do find preproc files...then we can run ciftify_subject_fmri now
            for bold_preproc in bold_preprocs:
                run_ciftify_subject_fmri(participant_label, bold_preproc, settings)
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
        cmd = ['fmriprep', settings.bids_dir, os.path.dirname(settings.func_derivs_dir),
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
    if can_skip_ciftify_recon_all(settings, participant_label):
        logger.info("Skipping ciftify_recon_all for sub-{}".format(participant_label))
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

def can_skip_ciftify_recon_all(settings, participant_label):
    '''determine if ciftify_recon_all has already completed or should be clobbered'''
    is_done = ciftify.utils.has_ciftify_recon_all_run(
        settings.ciftify_work_dir, 'sub-{}'.format(participant_label))
    if is_done == True:
        if settings.resample_to_T1w32k:
            T1w32k_path = os.path.join(settings.ciftify_work_dir,
                'sub-{}'.format(participant_label),
                'T1w', 'fsaverage_LR32k')
            if os.path.exists(T1w32k_path):
                logger.info("ciftify outputs including T1w/fsaverage_LR32k surfaces exists - skipping ciftify anat")
                return True
            else:
                logger.info("Running extra resampling to T1w/fsaverage_LR32k")
                return False

        logger.info("Found ciftify anat outputs for sub-{}".format(participant_label))
        return True

    ciftify_subject_dir = os.path.join(settings.ciftify_work_dir,
        'sub-{}'.format(participant_label))

    if os.path.exists(ciftify_subject_dir):
        if settings.rerun:
            logger.info('Deleting ciftify outputs for participant {} and restarting ciftify_recon_all'.format(participant_label))
            shutil.rmtree(ciftify_subject_dir)
            return False
        # check if we are clobbereing - if so, delete and return True, else warning and False
        logger.warning("ciftify anat outputs for sub-{} are not complete, consider deleting ciftify outputs and rerunning.".format(participant_label))
        return True
    return False

def find_participant_bold_inputs(participant_label, settings):
    '''find all the bold files in the bids layout'''

    bolds = settings.bids_layout.get(subject = participant_label,
                                       suffix="bold",
                                       session = settings.sessions if len(settings.sessions) > 0 else None,
                                       task = settings.tasks,
                                       extensions=["nii.gz", "nii"])

    return bolds


def get_derivatives_layout(derivs_dir):
    '''run pybids and produce the derivs_layout'''
    try:
        derivs_layout = BIDSLayout(derivs_dir,
             validate = False, config = ['bids', 'derivatives'])
    except:
        logger.warning('Could not parse BIDS derivatives from {}'.format(derivs_dir))
    return derivs_layout

def find_bold_preprocs(bold_input, settings):
    ''' find the T1w preproc file for specified BIDS dir bold input
    return the func input filename and task_label input for ciftify_subject_fmri'''
    # if the func derivatives directory doesn't even exist, return the empty string
    if not os.path.exists(settings.func_derivs_dir):
        return []
    derivs_layout = get_derivatives_layout(settings.func_derivs_dir)
    bents = bold_input.entities
    if settings.old_fmriprep_derivs:
        bold_preprocs = derivs_layout.get(
                subject = bents['subject'],
                session = bents['session'] if 'session' in bents.keys() else None,
                task = bents['task'],
                run = bents['run'] if 'run' in bents.keys() else None,
                space = "T1w",
                suffix = 'preproc',
                datatype = 'func',
                extensions = ['.nii.gz', ".nii"])
        return bold_preprocs

    #use bids derivatives layout to find the proproc files
    # Note: this section may need to be expanded in the future with acceptable space-related metadata keys
    # for example: ReferenceMap  = "/path/to/sub-{subject}_desc-preproc_T1w.nii.gz"
    bold_preprocs = derivs_layout.get(
               subject = bents['subject'],
               session = bents['session'] if 'session' in bents.keys() else None,
               task = bents['task'],
               run = bents['run'] if 'run' in bents.keys() else None,
               desc = settings.preproc_desc,
               suffix = "bold",
               space = "T1w",
               extensions=["nii.gz", "nii"])
    return bold_preprocs

        ## now need to verify that there is only one...

def find_fmriname(settings, bold_preproc):
    '''build the NameoffMRI folder name using build path'''
    derivs_layout = get_derivatives_layout(settings.func_derivs_dir)
    fmriname = derivs_layout.build_path(bold_preproc.entities,
        "[ses-{session}_]task-{task}[_acq-{acquisition}][_rec-{reconstruction}][_run-{run}][_desc-{desc}]")
    if '_run-0' in bold_preproc.path:
        fmriname = fmriname.replace('_run-', '_run-0')
    return fmriname

def run_fmriprep_func(bold_input, settings):
    '''runs fmriprep with combo of user args and required args for ciftify'''
    # if feildmaps are available use default settings
    fieldmap_list = settings.bids_layout.get_fieldmap(bold_input.path, return_list = True)
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
    fcmd = ['fmriprep', settings.bids_dir, os.path.dirname(settings.func_derivs_dir),
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


def run_ciftify_subject_fmri(participant_label, bold_preproc, settings):
    '''run ciftify_subject_fmri for the bold file plus the vis function'''
    fmriname = find_fmriname(settings, bold_preproc)
    if can_skip_ciftify_fmri(participant_label, fmriname, settings):
        return
    cmd = ['ciftify_subject_fmri',
        '--n_cpus', str(settings.n_cpus),
        '--ciftify-work-dir', settings.ciftify_work_dir,
        '--surf-reg', settings.surf_reg,
        bold_preproc.path,
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

def can_skip_ciftify_fmri(participant_label, fmriname, settings):
    '''determine if ciftify_fmri has already been run successfully
    if previous run exited with errors, and rerun flag was used will delete old output
    '''
    is_done = ciftify.utils.has_ciftify_fmri_run(
        'sub-{}'.format(participant_label), fmriname, settings.ciftify_work_dir)
    if is_done:
        logger.info('ciftify_subject_fmri has already been run for sub-{}_{}'.format(participant_label, fmriname))
        return True
    results_dir = os.path.join(
        settings.ciftify_work_dir,
        'sub-{}'.format(participant_label),
        'MNINonLinear', 'Results', fmriname)
    print(results_dir)
    if os.path.exists(results_dir):
        if settings.rerun:
            logger.info('Deleting incomplete ciftify outputs for sub-{}_{} and re-running ciftify_subject_fmri'.format(participant_label, fmriname))
            shutil.rmtree(results_dir)
            return False
        else:
            logger.warning('Incomplete ciftify_subject_fmri output found for sub-{}_{}' \
            'Consider using the --rerun-if-incomplete flag to delete and rerun ciftify_subject_fmri'.format(participant_label, fmriname))
            return True
    return False

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
