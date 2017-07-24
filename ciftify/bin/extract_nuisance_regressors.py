#!/usr/bin/env python
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
import tempfile
import shutil
import subprocess
import logging
import logging.config

from docopt import docopt

config_path = os.path.join(os.path.dirname(__file__), "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

def main(temp):
    arguments = docopt(__doc__)
    input_dir = arguments['<input_dir>']
    rest_files = arguments['<rest_file>']
    user_output_dir = arguments['--output_dir']
    debug = arguments['--debug']

    if debug:
        logger.setLevel(logging.DEBUG)

    verify_wb_available()
    verify_FSL_available()
    verify_ciftify_available()

    if user_output_dir and os.listdir(user_output_dir):
        logger.debug("Outputs found at {}. No work to do.".format(user_output_dir))
        return

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
    rtn = subprocess.call(run_filter, shell=True)
    if rtn:
        sys.exit("filter_hcp.sh experienced an error while generating "
                "masks for {}".format(input_path))

def get_output_path(user_path, image):
    if user_path:
        return user_path
    return os.path.dirname(image)

def resample_mask(rest_image, mask, output_path):
    vol_dims = get_nifti_dimensions(rest_image)
    mask_dims = get_nifti_dimensions(mask)

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
    subprocess.call(resample, shell=True)

    binarize = "fslmaths {} -thr 0.5 -bin {}".format(new_mask, new_mask)
    subprocess.call(binarize, shell=True)

    if not os.path.exists(new_mask):
        sys.exit("Failed to resample {} to size {}".format(mask, vol_dims))
    return new_mask

def get_nifti_dimensions(nii_path):
    fields = get_fslinfo_fields(nii_path)

    # list() ensures python3 and python2 compatibility
    pixdims = list(filter(lambda x: 'pixdim' in x, fields))
    dims = {}
    for dim in pixdims:
        key, val = dim.split()
        dims[key] = val

    x = dims['pixdim1']
    y = dims['pixdim2']
    z = dims['pixdim3']

    return x, y, z

def get_fslinfo_fields(nii_path):
    fsl_info = "fslinfo {}".format(nii_path)
    nii_info = subprocess.check_output(fsl_info, shell=True)
    fields = nii_info.strip().split('\n')
    return fields

def get_image_name(image):
    image_bn = os.path.basename(image)
    return image_bn.replace('.nii', '').replace('.gz', '')

def ciftify_meants(image, seed, csv, mask=None):
    meants = "ciftify_meants {} {} --outputcsv {}".format(image, seed, csv)
    if mask:
        meants = meants + ' --mask {}'.format(mask)
    rtn = subprocess.check_output(meants, shell=True)

    if rtn or not os.path.exists(csv):
        sys.exit("Error experienced while generating {}".format(csv))

def verify_wb_available():
    """ Raise SystemExit if connectome workbench is not installed """
    which_wb = "which wb_command"
    try:
        subprocess.check_output(which_wb, shell=True)
    except subprocess.CalledProcessError:
        raise SystemExit("wb_command not found. Please check that Connectome "
                "Workbench is installed.")

def verify_FSL_available():
    """ Raise SystemExit if FSL is not installed. """
    which_FSL = "which fslinfo"
    try:
        subprocess.check_output(which_FSL, shell=True)
    except subprocess.CalledProcessError:
        raise SystemExit("fslinfo not found. Please check that FSL is installed.")

def verify_ciftify_available():
    which = "which ciftify_meants"
    try:
        subprocess.check_output(which, shell=True)
    except subprocess.CalledProcessError:
        raise SystemExit("ciftify_meants not found. Please check that Ciftify "
                "is installed.")

class TempDir(object):
    def __init__(self):
        self.path = None
        return

    def __enter__(self):
        self.path = tempfile.mkdtemp()
        return self.path

    def __exit__(self, type, value, traceback):
        if self.path is not None:
            shutil.rmtree(self.path)

if __name__ == "__main__":
    with TempDir() as temp:
        main(temp)
