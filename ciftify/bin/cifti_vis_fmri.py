#!/usr/bin/env python
"""
Makes pictures of standard views from the hcp files and pastes them
together into a qcpage.

Usage:
    cifti_vis_fmri snaps [options] <OutputBasename> <SmoothingFWHM> <subject>
    cifti_vis_fmri index [options]

Arguments:
  <OutputBasename>         OutputBasename argument given during ciftify_subject_fmri
  <SmoothingFWHM>          SmoothingFWHM argument given during ciftify_subject_fmri
  <subject>                Subject ID to process

Options:
  --qcdir PATH             Full path to location of QC directory
  --hcp-data-dir PATH      The directory for HCP subjects (overrides HCP_DATA
                           environment variable)
  -v, --verbose
  --debug                  Debug logging in Erin's very verbose style
  -n,--dry-run             Dry run
  --help                   Print help

DETAILS
This makes pretty pictures of your hcp views using connectome workbenches "show
scene" commands. It pastes the pretty pictures together into some .html QC pages

This produces:
 ++ views of the functional data that has been projected to the "cifti space"
 ++ used to QC the volume to cortex mapping step - as well as subcortical
 ++ resampling this option requires that 2 more arguments are specified
    ++ --NameOffMRI and --SmoothingFWHM -
    ++ these should match what was input in the func2hcp command

Also this function works by writing a temporary file into the HCP_DATA
directory, therefore, write permission in the HCP_DATA directory is required.

Requires connectome workbench (i.e. wb_command and imagemagick)

Written by Erin W Dickie, Feb 2016
"""

import os
import sys
import logging
import logging.config

from docopt import docopt

import ciftify
from ciftify.utilities import VisSettings

DRYRUN = False

# Read logging.conf
config_path = os.path.join(os.path.dirname(__file__), "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

class UserSettings(VisSettings):
    def __init__(self, arguments):
        VisSettings.__init__(self, arguments, qc_mode='func2cifti')
        self.fmri_name = arguments['<OutputBasename>']
        self.fwhm = arguments['<SmoothingFWHM>']
        self.subject = arguments['<subject>']

def main():
    global DRYRUN
    arguments       = docopt(__doc__)
    snaps_only      = arguments['snaps']
    verbose         = arguments['--verbose']
    debug           = arguments['--debug']
    DRYRUN          = arguments['--dry-run']

    if verbose:
        logger.setLevel(logging.INFO)
        logging.getLogger('ciftify').setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    logger.debug(arguments)

    user_settings = UserSettings(arguments)
    config = ciftify.qc_config.Config(user_settings.qc_mode)

    if snaps_only:
        logger.info("Making snaps for subject {}".format(user_settings.subject))
        write_single_qc_page(user_settings, config)
        return

    logger.info("Writing index pages to {}".format(user_settings.qc_dir))
    # Double nested braces allows two stage formatting and get filled in after
    # single braces (i.e. qc mode gets inserted into the second set of braces)
    title = "{{}} View Index ({} space)".format(user_settings.qc_mode)
    ciftify.html.write_index_pages(user_settings.qc_dir, config,
            user_settings.qc_mode, title=title)

def write_single_qc_page(user_settings, config):
    """
    Generates a QC page for the subject specified by the user.
    """
    qc_dir = os.path.join(user_settings.qc_dir,
            '{}_{}_sm{}'.format(user_settings.subject, user_settings.fmri_name,
            user_settings.fwhm))
    qc_html = os.path.join(qc_dir, 'qc.html')

    if os.path.isfile(qc_html):
        logger.debug("QC page {} already exists.".format(qc_html))
        return

    with ciftify.utilities.TempSceneDir(user_settings.hcp_dir) as scene_dir:
        with ciftify.utilities.TempDir() as temp_dir:
            generate_qc_page(user_settings, config, qc_dir, scene_dir, qc_html,
                    temp_dir)

def generate_qc_page(user_settings, config, qc_dir, scene_dir, qc_html, temp_dir):
    contents = config.get_template_contents()
    scene_file = personalize_template(contents, scene_dir, user_settings, temp_dir)
    change_sbref_palette(user_settings, temp_dir)

    if DRYRUN:
        return

    ciftify.utilities.make_dir(qc_dir)
    with open(qc_html, 'w') as qc_page:
        ciftify.html.add_page_header(qc_page, config, user_settings.qc_mode,
                subject=user_settings.subject, path='..')
        ciftify.html.add_images(qc_page, qc_dir, config.images, scene_file)

def personalize_template(template_contents, output_dir, user_settings, temp_dir):
    """
    Modify a copy of the given template to match the user specified values.
    """
    scene_file = os.path.join(output_dir,
            'qc{}_{}.scene'.format(user_settings.qc_mode,
            user_settings.subject))

    with open(scene_file,'w') as scene_stream:
        new_text = modify_template_contents(template_contents, user_settings,
                                            scene_file, temp_dir)
        scene_stream.write(new_text)

    return scene_file

def modify_template_contents(template_contents, user_settings, scene_file,
        temp_dir):
    """
    Customizes a template file to a specific hcp data directory, by
    replacing all relative path references and place holder paths
    with references to specific files.
    """
    modified_text = template_contents.replace('HCP_DATA_PATH',
            user_settings.hcp_dir)
    modified_text = modified_text.replace('SUBJID', user_settings.subject)
    modified_text = modified_text.replace('RSLTDIR', user_settings.fmri_name)
    modified_text = modified_text.replace('DTSERIESFILE',
            '{}_Atlas_s{}.dtseries.nii'.format(user_settings.fmri_name,
            user_settings.fwhm))
    modified_text = modified_text.replace('SBREFFILE',
            '{}_SBRef.nii.gz'.format(user_settings.fmri_name))
    modified_text = modified_text.replace('SBREFDIR', os.path.realpath(temp_dir))
    modified_text = modified_text.replace('SBREFRELDIR', os.path.relpath(
            os.path.realpath(temp_dir),os.path.dirname(scene_file)))
    return modified_text

def change_sbref_palette(user_settings, temp_dir):
    sbref_nii = os.path.join(temp_dir,
            '{}_SBRef.nii.gz'.format(user_settings.fmri_name))
    brainmask_fs = os.path.join(user_settings.hcp_dir,
            user_settings.subject,'MNINonLinear', 'brainmask_fs.nii.gz')

    func4D_nii = os.path.join(user_settings.hcp_dir, user_settings.subject,
            'MNINonLinear', 'Results', user_settings.fmri_name,
            '{}.nii.gz'.format(user_settings.fmri_name))

    ciftify.utilities.docmd(['wb_command', '-volume-reduce',
        func4D_nii, 'MEAN', sbref_nii], DRYRUN)

    sbref_1percent = ciftify.utilities.get_stdout(['wb_command', '-volume-stats',
            sbref_nii, '-percentile', '1', '-roi', brainmask_fs])

    sbref_1percent = sbref_1percent.replace(os.linesep,'')

    ciftify.utilities.docmd(['wb_command', '-volume-palette',
        sbref_nii,
        'MODE_AUTO_SCALE_PERCENTAGE',
        '-disp-neg', 'false',
        '-disp-zero', 'false',
        '-pos-percent', '25','98',
        '-thresholding', 'THRESHOLD_TYPE_NORMAL',
        'THRESHOLD_TEST_SHOW_OUTSIDE', '-100', sbref_1percent,
        '-palette-name','fidl'], DRYRUN)

if __name__ == '__main__':
    main()
