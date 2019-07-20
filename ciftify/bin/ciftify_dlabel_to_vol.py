#!/usr/bin/env python3
"""
Takes a atlas or cluster map ('dlabel.nii') and output a nifti image in a particular participants space

Usage:
    ciftify_dlabel_to_vol [options] --input-dlabel <input.dlabel.nii> --left-mid-surface <input.L.surf.gii> --volume-template <voltemplate.nii.gz> --output-nifti <output.nii.gz>

Arguments:
    --input-dlabel <input.dlabel.nii>       Input atlas or cluster map.
    --left-mid-surface <input.L.surf.gii>   Left midthickness surface file (note the other 5 needed surfaces are inferred from this)
    --volume-template <voltemplate.nii.gz>  Volume that defines the output space and resolution
    --output-nifti <output.nii.gz>          Output nifti atlas

Options:
    --map-number INT         The map number [default: 1] within the dlabel file to report on.
    --use-nearest-vertex MM  Use wb_commands nearest vertex method (instead 
                             of ribbon contrained) where voxels nearest 
                             to the midthickness surface are labeled 
                             within the specified MM distance. 

    --debug                Debug logging
    -n,--dry-run           Dry run
    -h, --help             Prints this message

DETAILS:

Useful for building regions of interest in volume space for diffusion analysis, or as an intermediate for checking volume-to-surface mapping.

"""
from docopt import docopt
import os, sys
import ciftify.utils
from ciftify.meants import NibInput
import logging
from ciftify.niio import cifti_info, voxel_spacing
from nilearn.image import resample_to_img

config_path = os.path.join(os.path.dirname(ciftify.config.find_ciftify_global()), 'bin', "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

class UserSettings(object):
    def __init__(self, arguments):
        self.dlabel_in = NibInput(arguments['--input-dlabel'])
        self.output_nifti = self.__get_output_path(arguments['--output-nifti'])
        self.volume_in = NibInput(arguments['--volume-template'])
        self.use_nearest = self.__get_surf_method(arguments['--use-nearest-vertex'])
        self.surfs = self.__get_surfs(arguments['--left-mid-surface'])
        self.map_number = str(arguments['--map-number'])
        #returns a bool of wether or not there are volume space labels to deal with
        self.dlabel_in.has_volume = cifti_info(self.dlabel_in.path)['maps_to_volume']

    def __get_surfs(self, L_mid_path):

        surfs = {
            'L': {
                'pial': L_mid_path.replace('midthickness', 'pial'),
                'midthickness': L_mid_path,
                'white': L_mid_path.replace('midthickness', 'white'),
            },
            'R' : {
                'pial': L_mid_path.replace('midthickness', 'pial').replace('L.', 'R.').replace('hemi-L','hemi-R'),
                'midthickness': L_mid_path.replace('L.', 'R.').replace('hemi-L','hemi-R'),
                'white': L_mid_path.replace('midthickness', 'white').replace('L.', 'R.').replace('hemi-L','hemi-R'),
            }
        }
        return surfs

    def __get_output_path(self, output_arg):
        ciftify.utils.check_output_writable(output_arg)
        if not output_arg.endswith('.nii.gz'):
            logger.warning('Recommended output extension is ".nii.gz", path {} given'.format(output_arg))
        return output_arg
    
    def __get_surf_method(self, nearest_arg):
        if not nearest_arg:
            return None
        else:
            return str(nearest_arg)

def dlabel_number_maps(dlabel_file_path):
    '''make sure that we get the correct settings'''
    c_info = ciftify.utils.get_stdout(['wb_command', '-file-information',
                dlabel_file_path, '-no-map-info'])
    for line in c_info.split(os.linesep):
        if "Number of Columns:" in line:
            number_of_cols_str = line.replace("Number of Columns:",'')
            number_of_cols_int = int(number_of_cols_str)
    return number_of_cols_int

def run_ciftify_dlabel_to_vol(arguments, tmpdir):

    settings = UserSettings(arguments)

    if dlabel_number_maps(settings.dlabel_in.path) > 1:
        dlabel_file = os.path.join(tmpdir, 'split_in.dlabel.nii')
        ciftify.utils.run(['wb_command', '-cifti-merge',
            dlabel_file,
            '-cifti', settings.dlabel_in.path,
            '-column', settings.map_number])
    else:
        dlabel_file = settings.dlabel_in.path

    ## split the files into two label.gii files then map them to the volume
    ciftify.utils.run(['wb_command', '-cifti-separate',
        dlabel_file, 'COLUMN',
        '-label', 'CORTEX_LEFT', os.path.join(tmpdir, 'atlas.L.label.gii'),
        '-label', 'CORTEX_RIGHT', os.path.join(tmpdir, 'atlas.R.label.gii')])

    for hemi in ['L', 'R']:
        if not settings.use_nearest:
            ciftify.utils.run(['wb_command', '-label-to-volume-mapping',
                os.path.join(tmpdir, 'atlas.{}.label.gii'.format(hemi)),
                settings.surfs[hemi]['midthickness'],
                settings.volume_in.path,
                os.path.join(tmpdir, '{}.nii.gz'.format(hemi)),
                '-ribbon-constrained',
                settings.surfs[hemi]['white'],
                settings.surfs[hemi]['pial']])
        else:
            ciftify.utils.run(['wb_command', '-label-to-volume-mapping',
                os.path.join(tmpdir, 'atlas.{}.label.gii'.format(hemi)),
                settings.surfs[hemi]['midthickness'],
                settings.volume_in.path,
                os.path.join(tmpdir, '{}.nii.gz'.format(hemi)),
                '-nearest-vertex', settings.use_nearest])

    # if there is a volume component - then separate that out to nii files
    if not settings.dlabel_in.has_volume:
        ciftify.utils.run(['wb_command', '-volume-math',
            '"Lsurf + Rsurf"',
            settings.output_nifti,
            '-var Lsurf',os.path.join(tmpdir, 'L.nii.gz'),
            '-var Rsurf', os.path.join(tmpdir, 'R.nii.gz')])
    else:
        subcort_first_labels = os.path.join(tmpdir, 'subcort1.nii.gz')
        ciftify.utils.run(['wb_command', '-cifti-separate',
            dlabel_file, 'COLUMN',
            '-volume-all', subcort_first_labels])

        ## add bit here that checks if the two match in voxel resolution
        if ciftify.niio.voxel_spacing(subcort_first_labels) != ciftify.niio.voxel_spacing(settings.volume_in.path):
        ## if not then resample
            subcort_final_labels = os.path.join(tmpdir, 'subcort2.nii.gz')
            resampled_ref_vol1 = resample_to_img(
                source_img = subcort_first_labels,
                target_img = settings.volume_in.path)
            resampled_ref_vol1.to_filename(subcort_final_labels)
        else:
            subcort_final_labels = subcort_labels

        ## then add all three together
        ciftify.utils.run(['wb_command', '-volume-math',
            '"Lsurf + Rsurf + subcort"',
            settings.output_nifti,
            '-var Lsurf', os.path.join(tmpdir, 'L.nii.gz'),
            '-var Rsurf', os.path.join(tmpdir, 'R.nii.gz'),
            '-var subcort', subcort_final_labels])

    ## get the labels dictionary out of the dlabel files and write it into the outputs
    ciftify.utils.run(['wb_command', '-cifti-label-export-table',
        dlabel_file, settings.map_number,
        os.path.join(tmpdir, 'label_table.txt')])

    ciftify.utils.run(['wb_command', '-volume-label-import',
       settings.output_nifti,
       os.path.join(tmpdir, 'label_table.txt'),
       settings.output_nifti])

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
