#!/usr/bin/env python3
"""
Tries to match the preprocessing described in "Functional connectome
fingerprinting: identifying individuals using patterns of brain connectivity".

i.e. generates an eroded white matter mask, eroded CSF mask, and calculates
mean time courses in the white matter and CSF. May also calulate the global
signal.

Usage:
    extract_nuisance_regressors.py [options] <input_dir> <rest_file>...

Arguments:
    <input_dir>                 Full path to the MNINonLinear folder of a
                                subject's hcp outputs.

    <rest_file>                 The full path to a rest image to generate
                                the mean time courses + global signal for.
                                Can be repeated if multiple files must be
                                processed

Options:
    --output_dir PATH           Sets a path for all outputs (if unset, outputs
                                will be left in the directory of the results
                                file they were generated for)
    --debug
"""
import os
import sys
import logging
import logging.config

from ciftify.utils import TempDir, run, check_output
import ciftify

from docopt import docopt

config_path = os.path.join(os.path.dirname(__file__), "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

def main():
    arguments = docopt(__doc__)
    input_dir = arguments['<input_dir>']
    rest_files = arguments['<rest_file>']
    user_output_dir = arguments['--output_dir']
    debug = arguments['--debug']

    if debug:
        logger.setLevel(logging.DEBUG)

    ciftify.utils.log_arguments(arguments)
    verify_wb_available()
    verify_FSL_available()

    if user_output_dir and os.listdir(user_output_dir):
        logger.debug("Outputs found at {}. No work to do.".format(user_output_dir))
        return

    with TempDir() as temp:

        brainmask = get_brainmask(input_dir)
        wm_mask, csf_mask = generate_masks(input_dir, temp)

        for image in rest_files:
            if not os.path.exists(image):
                logger.error("Rest file {} does not exist. Skipping".format(image))
                continue

            resampled_wm = resample_mask(image, wm_mask, temp)
            resampled_csf = resample_mask(image, csf_mask, temp)
            resampled_brainmask = resample_mask(image, brainmask, temp)

            image_name = get_image_name(image)
            output_path = get_output_path(user_output_dir, image)

            wm_csv = os.path.join(output_path, image_name + '_WM.csv')
            csf_csv = os.path.join(output_path, image_name + '_CSF.csv')
            global_signal_csv = os.path.join(output_path, image_name + '_GS.csv')

            ciftify_meants(image, resampled_wm, wm_csv, mask=resampled_brainmask)
            ciftify_meants(image, resampled_csf, csf_csv, mask=resampled_brainmask)
            ciftify_meants(image, resampled_brainmask, global_signal_csv)

def get_brainmask(input_dir):
    brainmask = os.path.join(input_dir, 'brainmask_fs.nii.gz')
    if not os.path.exists(brainmask):
        sys.exit("{} does not exist".format(brainmask))
    return brainmask

def generate_masks(input_path, output_path):
    run_filter(input_path, output_path)

    wm_mask = os.path.join(output_path, "anat_wm_ero.nii.gz")
    csf_mask = os.path.join(output_path, "anat_vent_ero.nii.gz")
    if not os.path.exists(wm_mask) or not os.path.exists(csf_mask):
        sys.exit("filter_hcp.sh has failed to generate the white matter mask "
                "or the csf mask for inputs in {}".format(input_path))

    return wm_mask, csf_mask

def run_filter(input_path, output):
    run_filter = "filter_hcp.sh {} {}".format(input_path, output)
    rtn = run(run_filter)
    if rtn:
        sys.exit("filter_hcp.sh experienced an error while generating "
                "masks for {}".format(input_path))

def get_output_path(user_path, image):
    if user_path:
        return user_path
    return os.path.dirname(image)

def resample_mask(rest_image, mask, output_path):
    vol_dims = ciftify.niio.voxel_spacing(rest_image)
    mask_dims = ciftify.niio.voxel_spacing(mask)

    if mask_dims == vol_dims:
        return mask

    new_mask = os.path.join(output_path, 'resampled_' + os.path.basename(mask))
    if os.path.exists(new_mask):
        prev_resample_dims = get_nifti_dimensions(new_mask)
        if prev_resample_dims == vol_dims:
            return new_mask
        # Remove old resampled mask if it doesnt match the dims of current image
        os.remove(new_mask)

    resample = "flirt -in {} -ref {} -out {} -applyxfm".format(mask, rest_image,
            new_mask)
    run(resample)

    binarize = "fslmaths {} -thr 0.5 -bin {}".format(new_mask, new_mask)
    run(binarize)

    if not os.path.exists(new_mask):
        sys.exit("Failed to resample {} to size {}".format(mask, vol_dims))
    return new_mask

def get_fslinfo_fields(nii_path):
    fsl_info = "fslinfo {}".format(nii_path)
    nii_info = check_output(fsl_info, shell=True)
    fields = nii_info.strip().split('\n')
    return fields

def get_image_name(image):
    image_bn = os.path.basename(image)
    return image_bn.replace('.nii', '').replace('.gz', '')

def ciftify_meants(image, seed, csv, mask=None):
    meants = "ciftify_meants {} {} --outputcsv {}".format(image, seed, csv)
    if mask:
        meants = meants + ' --mask {}'.format(mask)
    rtn = check_output(meants, shell=True)

    if rtn or not os.path.exists(csv):
        sys.exit("Error experienced while generating {}".format(csv))

def verify_wb_available():
    """ Raise SystemExit if connectome workbench is not installed """
    wb = ciftify.config.find_workbench()
    if not wb:
        logger.error("wb_command not found. Please check that Connectome "
                "Workbench is installed.")
        sys.exit(1)

def verify_FSL_available():
    """ Raise SystemExit if FSL is not installed. """
    fsl = ciftify.config.find_fsl()
    if not fsl:
        logger.error("fslinfo not found. Please check that FSL is installed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
