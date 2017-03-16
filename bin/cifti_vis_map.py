#!/usr/bin/env python
"""
Creates pngs of standard surface and subcortical views from a nifti of cifti
input map.

Usage:
    cifti_vis_map cifti-snaps [options] <map.dscalar.nii> <subject> <map-name>
    cifti_vis_map nifti-snaps [options] <map.nii> <subject> <map-name>
    cifti_vis_map index [options] <map-name>

Arguments:
    <map.dscalar.nii>        A 2D cifti dscalar file to view
    <map.nii>                A 3D nifti file to view to view
    <subject>                Subject ID for HCP surfaces
    <map-name>               Name of dscalar map as it will appear in qc page
                             filenames

Options:
  --qcdir PATH             Full path to location of QC directory.
  --roi-overlay FILE       A mask of seeds you may want to overlay on your seed
                           correlation maps
  --hcp-data-dir PATH      The directory for HCP subjects (overrides HCP_DATA
                           enviroment variable)
  --subjects-filter STR    A string that can be used to filter out subject
                           directories
  --colour-palette STR     Specify the colour palette for the seed correlation
                           maps
  --output-dscalar FILE    Specify the output filename, if you would like the
                           dscalar file saved (from nifti-snaps)
  --resample-nifti         The nifti file needs to be resampled to the voxel
                           space of the hcp subject first
  --v,--verbose            Verbose logging
  --debug                  Debug logging in Erin's very verbose style
  -n,--dry-run             Dry run
  --help                   Print help

DETAILS
Requires connectome workbench (i.e. wb_command and imagemagick)

This makes pretty pictures of your hcp views using connectome workbenches
"show scene" commands. It pastes the pretty pictures together into some .html
QC pages.

Also this function works by writing a temporary file into the HCP_DATA
directory, therefore, write permission in the HCP_DATA directory is required.

By default, all folder in the qc directory will be included in the index.

You can change the color palette for all pics using the --colour-palette flag.
The default colour palette is videen_style. Some people like 'PSYCH-NO-NONE'
better. For more info on palettes see wb_command help.

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

config_path = os.path.join(os.path.dirname(__file__), "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

class UserSettings(VisSettings):
    def __init__(self, arguments, temp_dir):
        self.temp = temp_dir
        VisSettings.__init__(self, arguments, qc_mode='mapvis')
        self.map_name = arguments['<map-name>']
        self.subject = arguments['<subject>']
        self.resample = arguments['--resample-nifti']
        self.snap = self.__get_cifti(arguments)
        self.overlay = arguments['--roi-overlay']
        self.subject_filter = arguments['--subjects-filter']
        self.save_dscalar = arguments['--output-dscalar']

    def __get_cifti(self, arguments):
        nifti = arguments['<map.nii>']
        palette = arguments['--colour-palette']
        if nifti is None:
            cifti_path = arguments['<map.dscalar.nii>']
            cifti = self.__change_palette(cifti_path, palette, copy=True)
            return cifti
        new_cifti = self.__convert_nifti(nifti)
        cifti = self.__change_palette(new_cifti, palette)
        return output

    def __change_palette(self, cifti, palette, copy=False):
        if palette is None or cifti is None:
            return cifti
        if copy:
            # Copy the original cifti to the temp dir
            original = cifti
            cifti = os.path.join(self.temp, os.path.basename(original))
            ciftify.utilities.docmd(['cp', original, cifti])
        # Change to the given palette
        cmd = ['wb_command', '-cifti-palette', cifti, 'MODE_AUTO_SCALE', cifti,
                '-palette-name', palette]
        ciftify.utilities.docmd(cmd)
        return cifti

    def __convert_nifti(self, nifti):
        cifti_name = '{}.dscalar.nii'.format(self.map_name)
        output = os.path.join(self.temp, cifti_name)
        subject_hcp_dir = os.path.join(self.hcp_dir, self.subject)
        cmd = ['ciftify-a-nifti', '--hcp-subjects-dir', subject_hcp_dir, nifti,
                output]
        if self.resample:
            cmd.append('--resample-voxels')
        ciftify.utilities.docmd(cmd, DRYRUN)
        return output

def main(temp_dir):
    global DEBUG, DRYRUN
    arguments = docopt(__doc__)
    DEBUG = arguments['--debug']
    DRYRUN = arguments['--dry-run']
    verbose = arguments['--verbose']

    if verbose:
        logger.setLevel(logging.INFO)

    logger.debug(arguments)

    settings = UserSettings(arguments, temp_dir)
    qc_config = ciftify.qc_config.Config(settings.qc_mode)

    ## make pics and qcpage for each subject
    if settings.snap:
        logger.info("Making snaps for subject {}, " \
            "Map: {}".format(settings.subject, settings.map_name))
        make_snaps(settings, qc_config)
        return 0

    logger.info("Writing Index pages to {}".format(settings.qc_dir))
    write_index_pages(settings, qc_config)
    return 0

def make_snaps(settings, qc_config):
    '''
    Does all the file manipulation and takes that pics for one subject
    '''
    qc_subdir = os.path.join(settings.qc_dir, '{}_{}'.format(settings.subject,
            settings.map_name))

    if os.path.exists(qc_subdir):
        logger.debug('Subject {}, Map {} already has qc files. " \
                "Exiting'.format(settings.subject, settings.map_name))
        return 0

    with ciftify.utilities.TempSceneDir(settings.hcp_dir,
            settings.subject) as scene_dir:
        generate_qc_page(settings, qc_config, scene_dir, qc_subdir)

def generate_qc_page(settings, qc_config, scene_dir, qc_subdir):
    scene_file = personalize_template(qc_config.template, scene_dir, settings)

    if DRYRUN:
        return

    ciftify.utilities.make_dir(qc_subdir, DRYRUN)
    qc_html = os.path.join(qc_subdir, 'qc.html')
    with open(qc_html, 'w') as qc_page:
        ciftify.html.add_page_header(qc_page, qc_config, settings.map_name,
                subject=settings.subject, path='..')
        ciftify.html.add_images(qc_page, qc_subdir, qc_config.images,
                scene_file)

def personalize_template(template, scene_dir, settings):
    with open(template, 'r') as template_txt:
        template_contents = template_txt.read()

    if not template_contents:
        logger.error("{} cannot be read or is empty".format(template))
        sys.exit(1)

    scene_file = os.path.join(scene_dir,'{}_{}.scene'.format(settings.subject,
            settings.map_name))

    with open(scene_file, 'w') as scene_stream:
        new_text = modify_template_contents(template_contents, scene_file,
                settings)
        scene_stream.write(new_text)

    return scene_file

def modify_template_contents(template_contents, scene_file, settings):
    modified_text = template_contents.replace('HCP_DATA_PATH', settings.hcp_dir)
    modified_text = modified_text.replace('HCP_DATA_RELPATH',
            os.path.relpath(settings.hcp_dir, os.path.dirname(scene_file)))
    modified_text = modified_text.replace('SUBJID', settings.subject)
    modified_text = modified_text.replace('SEEDCORRDIR', os.path.dirname(
            os.path.realpath(settings.snap)))
    modified_text = modified_text.replace('SEEDCORRRELDIR', os.path.relpath(
            os.path.dirname(os.path.realpath(settings.snap)),
            os.path.dirname(scene_file)))
    modified_text = modified_text.replace('SEEDCORRCIFTI', os.path.basename(
            os.path.realpath(settings.snap)))
    return modified_text

def write_index_pages(settings, qc_config):
    '''
    writes the main index pages and then calls write_index to write the rest
    '''
    subjects = ciftify.utilities.get_subj(settings.qc_dir)

    if settings.subject_filter:
        subjects = filter(lambda x: settings.subjects_filter in x, subjects)

    index_html = os.path.join(settings.qc_dir, 'index.html')
    with open(index_html, 'w') as main_index:
        ciftify.html.add_page_header(main_index, qc_config,
                settings.map_name, active_link='index.html')
        ciftify.html.add_image_and_subject_index(main_index, qc_config.images,
                subjects, settings.map_name)

    for image in qc_config.images:
        if not image.make_index:
            continue
        title = "{} {} View".format(settings.map_name, image.name)
        ciftify.html.write_image_index(settings.qc_dir, subjects,
                qc_config, settings.map_name, image.name, title=title)

if __name__=='__main__':
    with ciftify.utilities.TempDir() as temp_dir:
        logger.debug('Creating temp dir:{} on host:{}'.format(temp_dir,
                os.uname()[1]))
        ret = main(temp_dir)
    sys.exit(ret)
