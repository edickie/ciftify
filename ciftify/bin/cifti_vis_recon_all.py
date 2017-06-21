#!/usr/bin/env python
"""
Makes pictures of standard views from the hcp files and pastes them
together into a qcpage.

Usage:
    cifti_vis_recon_all snaps <QCmode> [options] <subject>
    cifti_vis_recon_all index <QCmode> [options]

Arguments:
  <QCmode>                 Type of QC to do ("MNIfsaverage32k","native")
  <subject>                The subject to make snaps for.

Options:
  --qcdir PATH             Full path to location of QC directory
  --hcp-data-dir PATH      The directory for HCP subjects (overrides HCP_DATA
                           enviroment variable)
  --debug                  Debug logging in Erin's very verbose style
  --verbose                More log messages, less than debug though
  -n,--dry-run             Dry run
  --help                   Print help

DETAILS
This makes pretty pictures of your hcp views using connectome workbenches
"show scene" commands. It pastes the pretty pictures together into some .html
QC pages

There are two "modes" for the spaces that are visualized:
  + native
     ++ views of subject brains in "native" space i.e. the "raw" converted
     ++ freesurfer outputs. Same information as the freesurfer QC tools
  + MNIfsaverage32k
     ++ views for the MNI transformed brains and fsaverage_LR surfaces
     ++ (32k meshes) this is the "space" where fMRI analysis is done

Also this function works by writing a temporary file into the HCP_DATA directory,
therefore, write permission in the HCP_DATA directory is required.

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
        qc_mode = self.get_qc_mode(arguments)
        VisSettings.__init__(self, arguments, qc_mode=qc_mode)
        self.subject = arguments['<subject>']

    def get_qc_mode(self, arguments):
        user_mode = arguments['<QCmode>']
        if user_mode != 'MNIfsaverage32k' and user_mode != 'native':
            logger.error("Given qc mode {} is not defined for this script."
                    "".format(user_mode))
            sys.exit(1)
        return user_mode

def main():
    arguments       = docopt(__doc__)
    snaps_only      = arguments['snaps']
    index_only      = arguments['index']
    debug           = arguments['--debug']
    verbose         = arguments['--verbose']
    DRYRUN          = arguments['--dry-run']

    if verbose:
        logger.setLevel(logging.INFO)
        logging.getLogger('ciftify').setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    logger.debug(arguments)

    settings = UserSettings(arguments)
    qc_config = ciftify.qc_config.Config(settings.qc_mode)

    ## make pics and qc page for each subject
    if snaps_only:
        logger.info("Making snaps for subject {}".format(settings.subject))
        write_single_qc_page(settings, qc_config)
        return

    logger.info("Writing index pages to {}".format(settings.qc_dir))
    # Double nested braces allows two stage formatting and get filled in after
    # single braces (i.e. qc mode gets inserted into the second set of braces)
    title = "{{}} View Index ({} space)".format(settings.qc_mode)
    ciftify.html.write_index_pages(settings.qc_dir, qc_config, settings.qc_mode,
            title=title)

def write_single_qc_page(settings, qc_config):
    qc_subdir = os.path.join(settings.qc_dir, settings.subject)
    qc_html = os.path.join(qc_subdir, 'qc.html')

    if os.path.exists(qc_html):
        logger.debug("QC page {} already exists.".format(qc_html))
        return

    with ciftify.utilities.TempSceneDir(settings.hcp_dir) as scene_dir:
        generate_qc_page(settings, qc_config, qc_subdir, scene_dir, qc_html)

def generate_qc_page(settings, qc_config, qc_dir, scene_dir, qc_html):
    contents = qc_config.get_template_contents()
    scene_file = personalize_template(contents, scene_dir, settings)

    if DRYRUN:
        return

    ciftify.utilities.make_dir(qc_dir)
    with open(qc_html, 'w') as qc_page:
        ciftify.html.add_page_header(qc_page, qc_config, settings.qc_mode,
                subject=settings.subject, path='..')
        ciftify.html.add_images(qc_page, qc_dir, qc_config.images,
                scene_file)

def personalize_template(template_contents, output_dir, settings):
    scene_file = os.path.join(output_dir,
            'qc{}_{}.scene'.format(settings.qc_mode, settings.subject))

    with open(scene_file, 'w') as scene_stream:
        new_text = modify_template_contents(template_contents, settings)
        scene_stream.write(new_text)

    return scene_file

def modify_template_contents(template_contents, settings):
    modified_text = template_contents.replace('HCP_DATA_PATH', settings.hcp_dir)
    modified_text = modified_text.replace('SUBJID', settings.subject)
    return modified_text

if __name__ == "__main__":
    main()
