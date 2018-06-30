#!/usr/bin/env python
"""
Converts a freesurfer recon-all output to a working directory

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

from bids.grabbids import BIDSLayout
from ciftify.utils import run, get_number_cpus

class Settings(object):
    def __init__(self, arguments):
        self.bids_dir = arguments['<bids_dir']
        self.bids_layout = self.__get_bids_layout()
        self.fs_dir, self.fmriprep_dir, self.ciftify_work_dir = __set_derivatives_dirs(self, arguments['<output_dir>'])
        self.analysis_level = self._get_analysis_level(arguments['<analysis_level>'])
        self.participant_labels = self._get_participants(arguments['--participant_label'])
        self.sessions = self._get_sessions(arguments['--session_label'])
        self.tasks = self._get_tasks(arguments['--task_label'])
        self.reg_name = self.__set_registration_mode(arguments)
        self.resample = arguments['--resample-to-T1w32k']
        self.no_symlinks = arguments['--no-symlinks']
        self.n_cpus = ciftify.utils.get_number_cpus(arguments['--n_cpus'])
        self.fs_license = arguments['--fs-license']
        self.fmriprep_work = arguments['--fmriprep_work']
        self.fmri_smooth_fwhm = arguments['--SmoothingFWHM']

    def __get_bids_layout(self):
        '''run the BIDS validator and produce the bids_layout'''
        run("bids-validator {}".format(self.bids_dir)
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
        if ana_user_arg == "group"
            return "group"
        logger.critical('<analysis_level> must be "participant" or "group", {} given'.format(ana_user_arg))

    def parse_comma_sep_arg(list_argument):
        ''' parse a comma separated list arg to return list'''
        retrun list_argument.split(“,”)

    def __get_participants(self, participant_user_arg):
        '''get the subjects, check that they are in bids_dir'''
        all_subjects = self.layout.get_subjects()
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
        all_sessions = self.layout.get_sessions()
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
        all_tasks = self.layout.get_tasks()
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
            verify_msm_available()
            user_config = arguments['--MSM-config']
            if not user_config:
                self.msm_config = os.path.join(self.__get_ciftify_data(),
                        'hcp_config', 'MSMSulcStrainFinalconf')
            elif user_config and not os.path.exists(user_config):
                logger.error("MSM config file {} does not exist".format(user_config))
                sys.exit(1)
            else:
                self.msm_config = user_config

def run_group_workflow(settings):
    ''' run the QC tools index mode '''
    run('cifti_vis_recon_all index --ciftify-work-dir {ciftify_work_dir}'.format(
        ciftify_work_dir = settings.ciftify_work_dir))
    run('cifti_vis_fmri index --ciftify-work-dir {ciftify_work_dir}'.format(
        ciftify_work_dir = settings.ciftify_work_dir))

def run_participant_workflow(settings):
    '''run all participants through participant workflow'''
    for participant_label in settings.participant_labels:
        run_one_participant(settings, participant_label)

def run_one_participant(settings, user_args, participant_label):
    ''' the main workflow'''

    # anat bit
    find_or_build_fs_dir(settings, participant_label)

    # run ciftify_recon_all
    run_ciftify_recon_all(subid = 'sub-{}'.format(participant_label),
                          fs_dir = setting.fs_dir,
                          ciftify_work_dir = settings.ciftify_work_dir,
                          n_cpus = settings.n_cpus,
                          surf_reg = settings.surf_reg,
                          resample_to_T1w32k = user_args['--resample-to-T1w32k'],
                          no_symlinks=user_args['--no-symlinks'])

    if settings.anat_only:
        return

    # find the bold_preproc abouts in the func derivates
    bolds = [f.filename for f in layout.get(subject = participant_label,
                                            type="bold",
                                            session = sessions
                                            task = tasks,
                                            extensions=["nii.gz", "nii"])]

    for bold_input in bolds:

        bold_preproc, fmriname = find_bold_preproc(bold_input, settings)
        if not os.path.isfile(bold_preproc):
            #to-add run_fmriprep for this subject (make sure --space)
            run_fmriprep_func(fmriname, settings)

        run_ciftify_subject_fmri(bold_preproc, fmriname, settings)
    return

def find_or_build_fs_dir(settings, participant_label):
    '''either finds a freesurfer output folder in the outputs
    if the freesurfer output are not run..it runs the fmriprep anat pipeline'''
    fs_sub_dir = os.path.join(settings.fs_dir,
                             'sub-{}'.format(participant_label))
    ## check for a wmparc file to insure that freesurfer probably finished
    if os.file.exists(os.path.join(fs_sub_dir, 'mri', 'wmparc.mgz')):
        logger.info("Found freesurder outputs for sub-{}".format(participant_label))
        return
    else:
        run(['fmriprep', settings.bids_dir, settings.derivatives_dir,
            'participant', '--participant_label', participant_label,
            '--anat-only', '--output-space T1w template',
            '--nthreads', settings.n_cpus,
            '--omp-nthreads', settings.n_cpus,
            '--work-dir', settings.fmriprep_work, \
            '--fs-license-file', settings.fs_license])

def run_ciftify_recon_all(settings, participant_label):
    run_cmd = ['ciftify_recon_all',
            '--ciftify-work-dir', settings.ciftify_work_dir,
            '--fs-subjects-dir', settings.fs_dir,
            '--surf-reg', settings.surf_reg,
            'sub-{}'.format(participant_label)]
    if settings.resample_to_T1w32k:
        run_cmd.insert(1,'--resample-to-T1w32k')
    if settings.no_symlinks:
        run_cmd.insert(1,'--no-symlinks')
    run(run_cmd)
    run(['cifti_vis_recon_all', 'subject',
        '--ciftify-work-dir',settings.ciftify_work_dir,
        'sub-()'.format(participant_label)])

def find_bold_preproc(bold_input, settings):
    ''' find the T1w preproc file for specified BIDS dir bold input
    return the func input filename and task_label input for ciftify_subject_fmri'''
    ## stuff goes here
    fmriname = "_".join(bold_input.split("sub-")[-1].split("_")[1:]).split(".")[0]
    assert fmriname
    return bold_preproc, fmriname

def run_ciftify_subject_fmri(participant_label, bold_preproc, fmriname, settings):
    '''run ciftify_subject_fmri for the bold file plus the vis function'''
    cmd = ['ciftify_subject_fmri',
        '--n_cpus', settings.n_cpus,
        '--ciftify-work-dir', settings.ciftify_work_dir,
        '--surf-reg', settings.surf_reg,
        bold_preproc,
        'sub-{}'.format(participant_label),
        fmriname]
    if settings.fmri_smooth_fwhm:
        cmd.insert(3, '--SmoothingFWHM {}'.format(settings.fmri_smooth_fwhm))
    run(cmd)

    vis_cmd = ['cifti_vis_fmri', 'subject',
    '--ciftify-work-dir', settings.ciftify_work_dir,
    fmriname, 'sub-{}'.format(participant_label)]
    if settings.fmri_smooth_fwhm:
        vis_cmd.insert(2, '--SmoothingFWHM {}'.format(settings.fmri_smooth_fwhm))
    run(vis_cmd)

def main():
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
    fh = settings.get_log_handler(formatter)
    logger.addHandler(fh)

    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
                section_header("Starting ciftify_subject_fmri")))
    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = run_ciftify_workflow(settings, tmpdir)
    logger.info(section_header("Done"))
    sys.exit(ret)

if __name__=='__main__':
    main()
