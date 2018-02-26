#!/usr/bin/env python
"""
Makes pictures for quality assurance of fmri data and pastes them
together into a html pages.

Usage:
    cifti_vis_fmri snaps [options] <NameOffMRI> <subject>
    cifti_vis_fmri subject [options] <NameOffMRI> <subject>
    cifti_vis_fmri index [options]

Arguments:
  <NameOffMRI>         NameOffMRI argument given during ciftify_subject_fmri
  <subject>            Subject ID to process

Options:
  --qcdir PATH             Full path to location of QC directory
  --ciftify-work-dir PATH  The directory for HCP subjects (overrides
                           CIFTIFY_WORKDIR/ HCP_DATA enivironment variables)
  --hcp-data-dir PATH      The directory for HCP subjects (overrides
                           CIFTIFY_WORKDIR/ HCP_DATA enivironment variables) DEPRECATED
  --SmoothingFWHM FWHM     SmoothingFWHM argument given during ciftify_subject_fmri
  --smooth-conn FWHM       Add smoothing with this FWHM [default: 4] to connectivity images
                           if no smoothing was during ciftify_subject_fmri
  -v, --verbose            Verbose logging
  --debug                  Debug logging
  --help                   Print help

DETAILS
Produces visualizations for quality assurance of volume to cortex mapping step
- as well as subcortical resampling. It also produces some

This produces:
 ++ views of the functional data that has been projected to the "cifti space"
 ++ overlays of the functional volume and the pial surface
 ++ seed connectivity from 3 seeds
 ++ this option requires that 2 more arguments are specified
    ++ --NameOffMRI and --SmoothingFWHM -
    ++ these should match what was input in the ciftify_subject_fmri command

The functional to surface QC plots are shown in unsmoothed space.
(i.e. referencing the <NameOffMRI>_Atlas_s0.dtseries.nii file)

Gross patterns of connetivity as more visible with some surface smoothing.
So connectivity are shown either on the smoothed dtseries files indicated by the
"--SmoothingFWHM" option, or they using temporary files smoothed with the kernel
indicated by the ('--smoothed-conn') option (default value 8mm).

Written by Erin W Dickie, Feb 2016
"""

import os
import sys
import logging
import logging.config
import nibabel
import numpy as np

from docopt import docopt

import ciftify
from ciftify.utils import VisSettings, run, get_stdout
from ciftify.qc_config import replace_path_references, replace_all_references

# Read logging.conf
config_path = os.path.join(os.path.dirname(__file__), "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

class UserSettings(VisSettings):
    def __init__(self, arguments):

        VisSettings.__init__(self, arguments, qc_mode='fmri')
        self.fmri_name = arguments['<NameOffMRI>']
        self.subject = arguments['<subject>']
        self.snaps = arguments['subject'] or arguments['snaps']
        self.dtseries_s0 = self.get_dtseries_s0()
        self.fwhm = self.get_fwhm(arguments)
        self.surf_mesh = '.32k_fs_LR'

    def get_dtseries_s0(self):
        dtseries_s0 = ''
        if self.snaps:
            dtseries_s0 = os.path.join(self.hcp_dir, self.subject,
                    'MNINonLinear', 'Results', self.fmri_name,
                    '{}_Atlas_s0.dtseries.nii'.format(self.fmri_name))
            if not os.path.exists(dtseries_s0):
                logger.error("Expected fmri file {} not found."
                             "".format(dtseries_s0))
                sys.exit(1)
        return dtseries_s0

    def get_fwhm(self, arguments):
        if arguments['--SmoothingFWHM']:
            fwhm = arguments['--SmoothingFWHM']
            dtseries_sm = os.path.join(self.hcp_dir, self.subject,
                    'MNINonLinear', 'Results', self.fmri_name,
                    '{}_Atlas_s{}.dtseries.nii'.format(self.fmri_name,fwhm))
            if not os.path.exists(dtseries_sm):
                logger.error("Expected smoothed fmri file {} not found."
                    "To generate temporary smoothed file for visulizations "
                    "use the --smooth-con flag instead".format(dtseries_sm))
                sys.exit(1)
        else:
            fwhm = arguments['--smooth-conn']
        return(fwhm)


def main():
    arguments       = docopt(__doc__)
    snaps_only      = arguments['subject'] or arguments['snaps']
    verbose         = arguments['--verbose']
    debug           = arguments['--debug']

    if arguments['snaps']:
        logger.warning("The 'snaps' argument has be deprecated. Please use 'subject' in the future.")

    if verbose:
        logger.setLevel(logging.INFO)
        logging.getLogger('ciftify').setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ciftify.utils.log_arguments(arguments)

    user_settings = UserSettings(arguments)
    config = ciftify.qc_config.Config(user_settings.qc_mode)
    title_formatter = {'fwhm': user_settings.fwhm}

    if snaps_only:
        logger.info("Making snaps for subject {}".format(user_settings.subject))
        write_single_qc_page(user_settings, config, title_formatter)
        return

    logger.info("Writing index pages to {}".format(user_settings.qc_dir))
    # Double nested braces allows two stage formatting and get filled in after
    # single braces (i.e. qc mode gets inserted into the second set of braces)
    ciftify.html.write_index_pages(user_settings.qc_dir, config,
            user_settings.qc_mode, title="cifti_vis_fmri Index", title_formatter=title_formatter)

def write_single_qc_page(user_settings, config, title_formatter):
    """
    Generates a QC page for the subject specified by the user.
    """
    qc_dir = os.path.join(user_settings.qc_dir,
            '{}_{}'.format(user_settings.subject, user_settings.fmri_name))
    qc_html = os.path.join(qc_dir, 'qc.html')

    with ciftify.utils.TempDir() as temp_dir:
        generate_qc_page(user_settings, config, qc_dir, temp_dir, qc_html,
                temp_dir, title_formatter)

def generate_qc_page(user_settings, config, qc_dir, scene_dir, qc_html,
                    temp_dir, title_formatter):

    sbref_nii = change_sbref_palette(user_settings, temp_dir)
    dtseries_sm = get_smoothed_dtseries_file(user_settings, temp_dir)

    contents = config.get_template_contents()
    scene_file = personalize_template(contents, scene_dir, user_settings,
                                        sbref_nii, dtseries_sm)

    ciftify.utils.make_dir(qc_dir)
    with open(qc_html, 'w') as qc_page:
        ciftify.html.add_page_header(qc_page, config, user_settings.qc_mode,
                subject=user_settings.subject, path='..')
        wb_logging = 'INFO' if user_settings.debug_mode else 'WARNING'
        ciftify.html.add_images(qc_page, qc_dir, config.images,
            scene_file, wb_logging = wb_logging, add_titles = True,
            title_formatter = title_formatter)

def personalize_template(template_contents, output_dir, user_settings, sbref_nii, dtseries_sm):
    """
    Modify a copy of the given template to match the user specified values.
    """
    scene_file = os.path.join(output_dir,
            'qc{}_{}.scene'.format(user_settings.qc_mode,
            user_settings.subject))

    with open(scene_file,'w') as scene_stream:
        new_text = modify_template_contents(template_contents, user_settings,
                                            scene_file, sbref_nii, dtseries_sm)
        scene_stream.write(new_text)

    return scene_file

def modify_template_contents(template_contents, user_settings, scene_file,
        sbref_nii, dtseries_sm):
    """
    Customizes a template file to a specific hcp data directory, by
    replacing all relative path references and place holder paths
    with references to specific files.
    """

    surfs_dir = os.path.join(user_settings.hcp_dir, user_settings.subject,
      'MNINonLinear', 'fsaverage_LR32k')
    T1w_nii = os.path.join(user_settings.hcp_dir, user_settings.subject,
          'MNINonLinear', 'T1w.nii.gz')
    dtseries_sm_base = os.path.basename(dtseries_sm)
    dtseries_sm_base_noext = dtseries_sm_base.replace('.dtseries.nii','')

    txt = template_contents.replace('SURFS_SUBJECT', user_settings.subject)
    txt = txt.replace('SURFS_MESHNAME', user_settings.surf_mesh)
    txt = replace_path_references(txt, 'SURFSDIR', surfs_dir, scene_file)
    txt = replace_all_references(txt, 'T1W', T1w_nii, scene_file)
    txt = replace_all_references(txt, 'SBREF', sbref_nii, scene_file)
    txt = replace_all_references(txt, 'S0DTSERIES', user_settings.dtseries_s0, scene_file)
    txt = replace_path_references(txt, 'SMDTSERIES', os.path.dirname(dtseries_sm), scene_file)
    txt = txt.replace('SMDTSERIES_BASENOEXT', dtseries_sm_base_noext)

    return txt

def change_sbref_palette(user_settings, temp_dir):
    ''' create a temporary sbref file and returns it's path'''

    sbref_nii = os.path.join(temp_dir,
            '{}_SBRef.nii.gz'.format(user_settings.fmri_name))

    func4D_nii = os.path.join(user_settings.hcp_dir, user_settings.subject,
            'MNINonLinear', 'Results', user_settings.fmri_name,
            '{}.nii.gz'.format(user_settings.fmri_name))

    run(['wb_command', '-volume-reduce',
        func4D_nii, 'MEAN', sbref_nii])

    run(['wb_command', '-volume-palette',
        sbref_nii,
        'MODE_AUTO_SCALE_PERCENTAGE',
        '-disp-neg', 'false',
        '-disp-zero', 'false',
        '-pos-percent', '5', '99',
        '-palette-name','fidl'])

    return sbref_nii

def get_smoothed_dtseries_file(user_settings, temp_dir):
    '''
    create smoothed file if it does not exist,
    returns path to smoothed file
    '''
    pre_dtseries_sm = os.path.join(user_settings.hcp_dir, user_settings.subject,
                            'MNINonLinear', 'Results', user_settings.fmri_name,
                            '{}_Atlas_s{}.dtseries.nii'.format(user_settings.fmri_name,
                                                               user_settings.fwhm))
    if os.path.exists(pre_dtseries_sm):
        return pre_dtseries_sm

    else:
        dtseries_sm = os.path.join(temp_dir,
                                    '{}_Atlas_s{}.dtseries.nii'.format(user_settings.fmri_name,
                                                                       user_settings.fwhm))
        Sigma = ciftify.utils.FWHM2Sigma(user_settings.fwhm)
        surfs_dir = os.path.join(user_settings.hcp_dir, user_settings.subject,
          'MNINonLinear', 'fsaverage_LR32k')
        run(['wb_command', '-cifti-smoothing',
            user_settings.dtseries_s0,
            str(Sigma), str(Sigma), 'COLUMN',
            dtseries_sm,
            '-left-surface', os.path.join(surfs_dir,
              '{}.L.midthickness{}.surf.gii'.format(user_settings.subject,
                                                     user_settings.surf_mesh)),
            '-right-surface', os.path.join(surfs_dir,
              '{}.R.midthickness{}.surf.gii'.format(user_settings.subject,
                                                     user_settings.surf_mesh))])
        return dtseries_sm


if __name__ == '__main__':
    main()
