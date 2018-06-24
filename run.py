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
  --participant_label sub    Space separated list of participants to process. Defaults to all.
  --task_label task          Space separated list of fmri tasks to process. Defaults to all.
  --session_labl sess        Space separated list of sessions to process. Defaults to all.
  --anat_only                Only run the anatomical pipeline.
  --resample-to-T1w32k        Resample the Meshes to 32k Native (T1w) Space
  --surf-reg REGNAME          Registration sphere prefix [default: MSMSulc]
  --no-symlinks               Will not create symbolic links to the zz_templates folder

  --MSM-config PATH           EXPERT OPTION. The path to the configuration file to use for
                              MSMSulc mode. By default, the configuration file
                              is ciftify/data/hcp_config/MSMSulcStrainFinalconf
                              This setting is ignored when not running MSMSulc mode.
  --ciftify-conf YAML         EXPERT OPTION. Path to a yaml configuration file. Overrides
                              the default settings in
                              ciftify/data/ciftify_workflow_settings.yaml
  --n_cpus INT                Number of cpu's available. Defaults to the value
                              of the OMP_NUM_THREADS environment variable
  -v,--verbose                Verbose logging
  --debug                     Debug logging in Erin's very verbose style
  -n,--dry-run                Dry run
  -h,--help                   Print help

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
from ciftify.utils import run


run("bids-validator " + args.bids_dir)

layout = BIDSLayout(args.bids_dir, exclude=['derivatives'])
subjects_to_analyze = []
# only for a subset of subjects
if args.participant_label:
    subjects_to_analyze = args.participant_label
# for all subjects
else:
    subject_dirs = glob(os.path.join(args.bids_dir, "sub-*"))
    subjects_to_analyze = [subject_dir.split("-")[-1] for subject_dir in subject_dirs]

def run_one_particpant(settings, user_args, participant_label):
    ''' the main workflow'''

    # anat bit
    fs_dir = find_or_build_fs_dir(settings, participant_label)

    # run ciftify_recon_all
    run_ciftify_recon_all(subid = 'sub-{}'.format(participant_label),
                          fs_dir = fs_dir,
                          ciftify_work_dir = settings.ciftify_work_dir,
                          n_cpus = settings.n_cpus,
                          surf_reg = settings.surf_reg,
                          resample_to_T1w32k = user_args['--resample-to-T1w32k'],
                          no_symlinks=user_args['--no-symlinks'])

    if settings.anat_only:
        return

    # find the bold_preproc abouts in the func derivates
    bolds = [f.filename for f in layout.get(subject=participant_label,
                                            type='bold',
                                            extensions=["nii.gz", "nii"])]

    for bold_input in bolds:

        bold_preproc, fmriname = find_bold_preproc(bold_input, settings)
        if not os.path.isfile(bold_preproc):
            #to-add run_fmriprep for this subject (make sure --space)
            run_fmriprep_func(fmriname, settings)

        run_ciftify_subject_fmri(bold_preproc, fmriname, settings, user_args)
    return

def find_or_build_fs_dir(settings):
    '''either finds a freesurfer output folder in the outputs
    if the freesurfer output are not run..it runs the fmriprep anat pipeline'''
    return

def run_ciftify_recon_all(subid, fs_dir, ciftify_work_dir, n_cpus, surf_reg,
            resample_to_T1w32k, no_symlinks=False):
    run(['mkdir','-p',ciftify_work_dir])
    run_cmd = ['ciftify_recon_all',
            '--ciftify-work-dir', ciftify_work_dir,
            '--fs-subjects-dir', fs_dir,
            '--surf-reg', surf_reg,
            subid]
    if resample_to_T1w32k:
        run_cmd.insert(1,'--resample-to-T1w32k')
    if no_symlinks:
        run_cmd.insert(1,'--no-symlinks')
    run(run_cmd)
    run(['cifti_vis_recon_all', 'subject', '--ciftify-work-dir',ciftify_work_dir, subid])

def find_bold_preproc(bold_input, settings):
    ''' find the T1w preproc file for specified BIDS dir bold input
    return the func input filename and task_label input for ciftify_subject_fmri'''
    ## stuff goes here
    fmriname = "_".join(bold_input.split("sub-")[-1].split("_")[1:]).split(".")[0]
    assert fmriname
    return bold_preproc, fmriname

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
