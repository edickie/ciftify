#!/usr/bin/env python3
"""
Takes a atlas or cluster map ('dlabel.nii') and output a nifti image in a particular participants space

Usage:
    ciftify_dlabel_to_vol [options] --input-dlabel <input.dlabel.nii> --output-nifti --let

Arguments:
    --input-dlabel <input.dlabel.nii>       Input atlas or cluster map.
    --left-pial-surface <input.L.surf.gii>  Left surface file (note the other 3 needed surfaces are inferred from this)
    --volume-template <input.nii.gz>        Volume that defines the output space and resolution
    --output-nifti <output.nii.gz>          Output nifti atlas


Options:
    --map-number INT    The map number [default: 1] within the dlabel file to report on.

    --debug                Debug logging
    -n,--dry-run           Dry run
    -h, --help             Prints this message

DETAILS:

Useful for building regions of interest in volume space for diffusion analysis, or as an intermediate for checking volume-to-surface mapping.

"""
from docopt import docopt
import os, sys
import ciftify.utils

config_path = os.path.join(os.path.dirname(ciftify.config.find_ciftify_global()), 'bin', "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

class UserSettings(object):
    def __init__(self, arguments):
        self.dlabel_in = NibInput(arguments['<input.dlabel.nii>'])
        self.nifti_out = self.__get_output(arguments['<output.nii.gz'])
        self.volume_in = self.__get_output(arguments['<output.nii.gz'])
        self.surfs = self.__get_surfs['<']

def run_ciftify_dlabel_to_vol(arguments, tmpdir):

    settings = UserSetting(arguments)

    ## split the files into two label.gii files then map them to the volume
    ciftify.utils.run(['wb_command', '-cifti-separate',
        settings.dlabel_in.path,
        '-label', 'CORTEX_LEFT', os.path.join(tmpdir, 'atlas.L.label.gii'),
        '-label', 'CORTEX_RIGHT', os.path.join(tmpdir, 'atlas.R.label.gii')])

    for hemi in ['L', 'R']:
        surfs = settings.surfs[hemi]
        ciftify.utils.run(['wb_command', '-label-to-volume-mapping',
            os.path.join(tmpdir, 'atlas.{}.label.gii'.format(hemi)),
            surfs.midthickness,
            settings.volume_in.path,
            os.path.join(tmpdir, '{}.nii.gz'.format(hemi)),
            '-ribbon-constained', surfs.white, surfs.pial])

    # if there is a volume component - then separate that out to nii files
    if not setting.dlabel_in.has_volume:
        ciftify.utils.run(['wb_command', '-volume-math',
            '(Lsurf + Rsurf)',
            settings.output_nifti
            '-var Lsurf',os.path.join(tmpdir, 'L.nii.gz'),
            '-var Rsurf', os.path.join(tmpdir, 'R.nii.gz')])
    else:

        ciftify.utils.run(['wb_command', '-cifti-separate',
            settings.dlabel_in.path, 'COLUMN',
            '-volume-all', os.path.join(tmpdir, 'subcort.nii.gz')])

        ## add bit here that checks if the two match in voxel resolution
        ## if not then resample

        ## then add all three together
        ciftify.utils.run(['wb_command', '-volume-math',
            '(Lsurf + Rsurf + subcort)',
            settings.output_nifti
            '-var Lsurf',os.path.join(tmpdir, 'L.nii.gz'),
            '-var Rsurf', os.path.join(tmpdir, 'R.nii.gz'),
            '-var subcort', os.path.join(tmpdir, 'subcort.nii.gz')])


def main():
    arguments = docopt(__doc__)

    logger.setLevel(logging.WARNING)

    if arguments['--debug']:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ## set up the top of the log
    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
        ciftify.utils.section_header('Starting ciftify_dlabel_to_vol')))

    ciftify.utils.log_arguments(arguments)

    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = run_ciftify_dlabel_to_vol(arguments, tmpdir)

if __name__ == '__main__':
    main()
