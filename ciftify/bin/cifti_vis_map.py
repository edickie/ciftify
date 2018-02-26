#!/usr/bin/env python
"""
Creates pngs of standard surface and subcortical views from a nifti or cifti
input map.

Usage:
    cifti_vis_map cifti-snaps [options] <map.dscalar.nii> <subject> <map-name>
    cifti_vis_map cifti-subject [options] <map.dscalar.nii> <subject> <map-name>
    cifti_vis_map nifti-snaps [options] <map.nii> <subject> <map-name>
    cifti_vis_map nifti-subject [options] <map.nii> <subject> <map-name>
    cifti_vis_map index [options]

Arguments:
    <map.dscalar.nii>        A 2D cifti dscalar file to view
    <map.nii>                A 3D nifti file to view to view
    <subject>                Subject ID for HCP surfaces
    <map-name>               Name of dscalar map as it will appear in qc page
                             filenames

Options:
  --qcdir PATH             Full path to location of QC directory.
  --ciftify-work-dir PATH  The directory for HCP subjects (overrides
                           CIFTIFY_WORKDIR/ HCP_DATA enivironment variables)
  --hcp-data-dir PATH      The directory for HCP subjects (overrides
                           CIFTIFY_WORKDIR/ HCP_DATA enivironment variables) DEPRECATED
  --subjects-filter STR    A string that can be used to filter out subject
                           directories when creating index
  --colour-palette STR     Specify the colour palette for the seed correlation
                           maps
  --resample-nifti         The nifti file needs to be resampled to the voxel
                           space of the hcp subject first
  --v,--verbose            Verbose logging
  --debug                  Debug logging
  --help                   Print help

DETAILS
This makes pretty pictures of your hcp views using connectome workbenches
"show scene" commands. It pastes the pretty pictures together into some .html
QC pages. Requires connectome workbench (i.e. wb_command and imagemagick)

By default, all folder in the qc directory will be included in the index.

You can change the color palette for all pics using the --colour-palette flag.
The default colour palette is videen_style. Some people like 'PSYCH-NO-NONE'
better. For more info on palettes see wb_command help.

Written by Erin W Dickie
"""
import os
import sys
import logging
import logging.config

from docopt import docopt

import ciftify
from ciftify.utils import VisSettings
from ciftify.qc_config import replace_all_references, replace_path_references

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
        self.snap = self.get_cifti(arguments)
        self.surf_mesh = self.get_surf_mesh()
        self.surf_dir = self.get_surf_dir()
        self.surf_subject = self.get_surf_subject()
        self.T1w = self.get_T1w()
        self.subject_filter = arguments['--subjects-filter']

    def get_cifti(self, arguments):
        nifti = arguments['<map.nii>']
        palette = arguments['--colour-palette']
        if nifti is None:
            cifti_path = arguments['<map.dscalar.nii>']
            cifti = self.__change_palette(cifti_path, palette, copy=True)
            return cifti
        new_cifti = self.__convert_nifti(nifti)
        cifti = self.__change_palette(new_cifti, palette)
        return cifti

    def get_surf_dir(self):
        if not self.subject:
            return None
        if self.subject == 'HCP_S1200_GroupAvg':
            surf_dir = ciftify.config.find_HCP_S1200_GroupAvg()
        else:
            surf_dir = os.path.join(
                self.hcp_dir, self.subject, 'MNINonLinear', 'fsaverage_LR32k')
        return surf_dir

    def get_surf_subject(self):
        if self.subject == 'HCP_S1200_GroupAvg':
            surf_subject = 'S1200'
        else:
            surf_subject = self.subject
        return surf_subject

    def get_T1w(self):
        if not self.subject:
            return None
        if self.subject == 'HCP_S1200_GroupAvg':
            T1w_nii = os.path.join(ciftify.config.find_fsl(),
                'data','standard','MNI152_T1_1mm.nii.gz')
        else:
            T1w_nii = os.path.join(
                self.hcp_dir, self.subject, 'MNINonLinear', 'T1w.nii.gz')
        return T1w_nii

    def get_surf_mesh(self):
        if not self.subject:
            return None
        if self.subject == 'HCP_S1200_GroupAvg':
            surf_mesh = '_MSMAll.32k_fs_LR'
        else:
            surf_mesh = '.32k_fs_LR'
        return surf_mesh

    def __change_palette(self, cifti, palette, copy=False):
        if palette is None or cifti is None:
            return cifti
        if copy:
            # Copy the original cifti to the temp dir
            original = cifti
            cifti = os.path.join(self.temp, os.path.basename(original))
            ciftify.utils.run(['cp', original, cifti])
        # Change to the given palette
        cmd = ['wb_command', '-cifti-palette', cifti, 'MODE_AUTO_SCALE', cifti,
                '-palette-name', palette]
        ciftify.utils.run(cmd)
        return cifti

    def __convert_nifti(self, nifti):
        cifti_name = '{}.dscalar.nii'.format(self.map_name)
        output = os.path.join(self.temp, cifti_name)
        cmd = ['ciftify_vol_result', self.subject, nifti, output]
        if not self.subject == 'HCP_S1200_GroupAvg':
            cmd.insert(1, '--ciftify-work-dir')
            cmd.insert(2, self.hcp_dir)
        if self.resample:
            cmd.insert(1,'--resample-nifti')
        if self.debug_mode:
            cmd.insert(1, '--debug')
        ciftify.utils.run(cmd)
        return output

def main():
    global DRYRUN
    arguments = docopt(__doc__)
    debug = arguments['--debug']
    verbose = arguments['--verbose']

    if arguments['cifti-snaps'] or arguments['nifti-snaps']:
        logger.warning("The 'snaps' argument has be deprecated. Please use 'subject' in the future.")

    if verbose:
        logger.setLevel(logging.INFO)
        logging.getLogger('ciftify').setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ciftify.utils.log_arguments(arguments)

    with ciftify.utils.TempDir() as temp_dir:
        logger.debug('Creating temp dir:{} on host:{}'.format(temp_dir,
                os.uname()[1]))

        settings = UserSettings(arguments, temp_dir)
        qc_config = ciftify.qc_config.Config(settings.qc_mode)

        ## make pics and qcpage for each subject
        if settings.snap:
            logger.info("Making snaps for subject {}, " \
                "Map: {}".format(settings.subject, settings.map_name))
            make_snaps(settings, qc_config, temp_dir)
            return 0

        logger.info("Writing Index pages to {}".format(settings.qc_dir))
        # Nested braces allow two stage formatting
        title = "{} View"
        ciftify.html.write_index_pages(settings.qc_dir, qc_config,
                '', title=title, user_filter=settings.subject_filter)
        return 0

def make_snaps(settings, qc_config, temp_dir):
    '''
    Does all the file manipulation and takes that pics for one subject
    '''
    qc_subdir = os.path.join(settings.qc_dir, '{}_{}'.format(settings.subject,
            settings.map_name))

    generate_qc_page(settings, qc_config, temp_dir, qc_subdir)

def generate_qc_page(settings, qc_config, scene_dir, qc_subdir):
    contents = qc_config.get_template_contents()
    scene_file = personalize_template(contents, scene_dir, settings)

    ciftify.utils.make_dir(qc_subdir, DRYRUN)
    qc_html = os.path.join(qc_subdir, 'qc.html')
    with open(qc_html, 'w') as qc_page:
        ciftify.html.add_page_header(qc_page, qc_config, settings.map_name,
                subject=settings.subject, path='..')
        wb_logging = 'INFO' if settings.debug_mode else 'WARNING'
        ciftify.html.add_images(qc_page, qc_subdir, qc_config.images,
                scene_file, wb_logging = wb_logging)

def personalize_template(template_contents, scene_dir, settings):
    scene_file = os.path.join(scene_dir,'{}_{}.scene'.format(settings.subject,
            settings.map_name))

    with open(scene_file, 'w') as scene_stream:
        new_text = modify_template_contents(template_contents, scene_file,
                settings)
        scene_stream.write(new_text)

    return scene_file

def modify_template_contents(template_contents, scene_file, settings):
    """
    Customizes a template file to a specific hcp data directory, by
    replacing all relative path references and place holder paths
    with references to specific files.
    """
    sulc_map = os.path.join(settings.surf_dir,
                            '{}.sulc{}.dscalar.nii'.format(settings.surf_subject,
                                                           settings.surf_mesh))

    txt = template_contents.replace('SURFS_SUBJECT', settings.surf_subject)
    txt = txt.replace('SURFS_MESHNAME', settings.surf_mesh)
    txt = replace_path_references(txt, 'SURFSDIR', settings.surf_dir, scene_file)
    txt = replace_all_references(txt, 'T1W', settings.T1w, scene_file)
    txt = replace_all_references(txt, 'TOPSCALAR', settings.snap, scene_file)
    txt = replace_all_references(txt, 'MIDSCALAR', sulc_map, scene_file)

    return txt


if __name__=='__main__':
    main()
