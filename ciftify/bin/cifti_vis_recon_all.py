#!/usr/bin/env python
"""
Makes pictures of standard views from ciftify_recon_all outputs and pastes them
together into a html page for quality assurance.

Usage:
    cifti_vis_recon_all snaps [options] <subject>
    cifti_vis_recon_all subject [options] <subject>
    cifti_vis_recon_all index [options]

Arguments:
  <subject>                The subject to make snaps for.

Options:
  --qcdir PATH             Full path to location of QC directory
  --ciftify-work-dir PATH  The directory for HCP subjects (overrides
                           CIFTIFY_WORKDIR/ HCP_DATA enivironment variables)
  --hcp-data-dir PATH      The directory for HCP subjects (overrides
                           CIFTIFY_WORKDIR/ HCP_DATA enivironment variables) DEPRECATED
  --temp-dir PATH          The directory for temporary files
  --debug                  Debug logging in Erin's very verbose style
  --verbose                More log messages, less than debug though
  --help                   Print help

DETAILS
Produces picture of surface outlines on slices as well as the recontruced surfaces.
Other views include the freesurfer automatic segmentation.

Two "spaces" are visualized ("native" and "MNI"). "Native" space are the "raw"
converted freesurfer outputs. The MNI transformed brains and fsaverage_LR surfaces
(32k meshes) is the "space" where fMRI analysis is done

Requires connectome workbench (i.e. wb_command and imagemagick)

Written by Erin W Dickie
"""

import os
import sys
import logging
import logging.config

from docopt import docopt

import ciftify
from ciftify.utils import VisSettings

DRYRUN = False

# Read logging.conf
config_path = os.path.join(os.path.dirname(__file__), "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

class UserSettings(VisSettings):
    def __init__(self, arguments):
        VisSettings.__init__(self, arguments, qc_mode='recon_all')
        self.subject = arguments['<subject>']
        self.tempdir = arguments['--temp-dir']

def main():
    arguments       = docopt(__doc__)
    snaps_only      = arguments['subject'] or arguments['snaps']
    index_only      = arguments['index']
    debug           = arguments['--debug']
    verbose         = arguments['--verbose']

    if arguments['snaps']:
        logger.warning("The 'snaps' argument has be deprecated. Please use 'subject' in the future.")

    if verbose:
        logger.setLevel(logging.INFO)
        logging.getLogger('ciftify').setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ciftify.utils.log_arguments(arguments)

    settings = UserSettings(arguments)
    qc_config = ciftify.qc_config.Config(settings.qc_mode)

    ## make pics and qc page for each subject
    if snaps_only:
        logger.info("Making snaps for subject {}".format(settings.subject))
        write_single_qc_page(settings, qc_config)
        return

    logger.info("Writing index pages to {}".format(settings.qc_dir))

    # For title: Double nested braces allows two stage formatting and get filled in after
    # single braces (i.e. qc mode gets inserted into the second set of braces)
    ciftify.html.write_index_pages(settings.qc_dir, qc_config, settings.qc_mode,
            title="{} Index")

def write_single_qc_page(settings, qc_config):
    qc_subdir = os.path.join(settings.qc_dir, settings.subject)
    qc_html = os.path.join(qc_subdir, 'qc.html')

    if settings.tempdir:
        scene_dir = settings.tempdir
        ciftify.utils.make_dir(scene_dir)
        generate_qc_page(settings, qc_config, qc_subdir, scene_dir, qc_html)
    else:
        with ciftify.utils.TempDir() as scene_dir:
            logger.info('temp files will be written to: {}'.format(scene_dir))
            generate_qc_page(settings, qc_config, qc_subdir, scene_dir, qc_html)

def generate_qc_page(settings, qc_config, qc_dir, scene_dir, qc_html):
    contents = qc_config.get_template_contents()
    scene_file = personalize_template(contents, scene_dir, settings)

    ciftify.utils.make_dir(qc_dir)
    with open(qc_html, 'w') as qc_page:
        ciftify.html.add_page_header(qc_page, qc_config, settings.qc_mode,
                subject=settings.subject, path='..')
        wb_logging = 'INFO' if settings.debug_mode else 'WARNING'
        ciftify.html.add_images(qc_page, qc_dir, qc_config.images,
                scene_file, wb_logging = wb_logging, add_titles = True)

def personalize_template(template_contents, output_dir, settings):
    scene_file = os.path.join(output_dir,
            'qc{}_{}.scene'.format(settings.qc_mode, settings.subject))

    with open(scene_file, 'w') as scene_stream:
        new_text = modify_template_contents(template_contents, settings, scene_file)
        scene_stream.write(new_text)

    return scene_file

def modify_template_contents(template_contents, settings, scene_file):
    modified_text = ciftify.qc_config.replace_path_references(template_contents,
                    'HCPDATA', settings.hcp_dir, scene_file)
    modified_text = modified_text.replace('SUBJID', settings.subject)
    return modified_text

if __name__ == "__main__":
    main()
