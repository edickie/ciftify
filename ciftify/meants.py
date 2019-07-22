#!/usr/bin/env python3
"""
These functions are called by both ciftify_meants and ciftify_seed_corr.
"""

import os
import sys
import subprocess
import logging
import numpy as np

import ciftify.utils
import ciftify.niio

class NibInput(object):
    def __init__(self, path):
        self.path = ciftify.utils.check_input_readable(path)
        self.type, self.base = ciftify.niio.determine_filetype(path)

class MeantsSettings(object):
    def __init__(self, arguments):
        self.func = NibInput(arguments['<func>'])
        self.seed = NibInput(arguments['<seed>'])
        self.mask = self.get_mask(arguments['--mask'])
        self.roi_label = arguments['--roi-label']
        self.hemi = self.get_hemi(arguments['--hemi'])
        self.weighted = arguments['--weighted']

    def get_mask(self, mask):
        '''parse mask.type if mask exists'''
        if mask:
            mask =  NibInput(mask)
        else:
            mask = None
        return(mask)

    def get_hemi(self, hemi):
        logger = logging.getLogger(__name__)
        if hemi:
            if hemi == "L" or hemi == "R":
                return hemi
            else:
                logger.error("--hemi {} not valid option. Exiting.\n"
                    "Specify 'L' (for left) or 'R' (for right)".format(hemi))
                sys.exit(1)
        else:
            if self.seed.type == 'gifti':
                logger.error("If seed type is gifti, Hemisphere needs to be specified with --hemi")
                sys.exit(1)
        return(hemi)

def verify_nifti_dimensions_match(file1, file2):
    ''' tests that voxel dimensions match for nifti files, exits if false '''
    logger = logging.getLogger(__name__)
    if ciftify.niio.voxel_spacing(file1) != ciftify.niio.voxel_spacing(file2):
        logger.error('Voxel dimensions of {} and {} do not match. Exiting'
            ''.format(file1, file2))
        sys.exit(1)

def load_data_as_numpy_arrays(settings, tempdir):
    '''
    loads the data using ciftify.niio tools according to their type
    read the settings object to know about func, seed and mask files
    '''
    logger = logging.getLogger(__name__)

    if not settings.mask: mask_data = None

    if settings.seed.type == "cifti":
        seed_info = ciftify.niio.cifti_info(settings.seed.path)
        func_info = ciftify.niio.cifti_info(settings.func.path)
        if not all((seed_info['maps_to_volume'], func_info['maps_to_volume'])):
            seed_data = ciftify.niio.load_concat_cifti_surfaces(settings.seed.path)
            if settings.func.type == "cifti":
                func_data = ciftify.niio.load_concat_cifti_surfaces(settings.func.path)
            else:
                sys.exit('If <seed> is in cifti, func file needs to match.')
            if settings.mask:
                if settings.mask.type == "cifti":
                    mask_data = ciftify.niio.load_concat_cifti_surfaces(settings.mask.path)
                else:
                    sys.exit('If <seed> is in cifti, func file needs to match.')
        else:
            seed_data = ciftify.niio.load_cifti(settings.seed.path)
            if settings.func.type == "cifti":
                func_data = ciftify.niio.load_cifti(settings.func.path)
            else:
                sys.exit('If <seed> is in cifti, func file needs to match.')
            if settings.mask:
                if settings.mask.type == "cifti":
                     mask_data = ciftify.niio.load_cifti(settings.mask.path)
                else:
                  sys.exit('If <seed> is in cifti, mask file needs to match.')

    elif settings.seed.type == "gifti":
        seed_data = ciftify.niio.load_gii_data(settings.seed.path)
        if settings.func.type == "gifti":
            func_data = ciftify.niio.load_gii_data(settings.func.path)
            if settings.mask:
                if settings.mask.type == "gifti":
                    mask_data = ciftify.niio.load_gii_data(settings.mask.path)
                else:
                    sys.exit('If <seed> is in gifti, mask file needs to match.')
        elif settings.func.type == "cifti":
            if settings.hemi == 'L':
                func_data = ciftify.niio.load_hemisphere_data(settings.func.path, 'CORTEX_LEFT')
            elif settings.hemi == 'R':
                func_data = ciftify.niio.load_hemisphere_data(settings.func.path, 'CORTEX_RIGHT')
            ## also need to apply this change to the mask if it matters
            if settings.mask:
                if settings.mask.type == "cifti":
                    if settings.hemi == 'L':
                        mask_data = ciftify.niio.load_hemisphere_data(settings.mask.path, 'CORTEX_LEFT')
                    elif settings.hemi == 'R':
                        mask_data = ciftify.niio.load_hemisphere_data(settings.mask.path, 'CORTEX_RIGHT')
        else:
            sys.exit('If <seed> is in gifti, <func> must be gifti or cifti')

    elif settings.seed.type == "nifti":
        seed_data, _, _, _ = ciftify.niio.load_nifti(settings.seed.path)
        if settings.func.type == "nifti":
            verify_nifti_dimensions_match(settings.seed.path, settings.func.path)
            func_data, _, _, _ = ciftify.niio.load_nifti(settings.func.path)
        elif settings.func.type == 'cifti':
            subcort_func = os.path.join(tempdir, 'subcort_func.nii.gz')
            ciftify.utils.run(['wb_command',
              '-cifti-separate', settings.func.path, 'COLUMN',
              '-volume-all', subcort_func])
            verify_nifti_dimensions_match(settings.seed.path, subcort_func)
            func_data, _, _, _ = ciftify.niio.load_nifti(subcort_func)
        else:
            logger.error('If <seed> is in nifti, func file needs to match.')
            exit(1)
        if settings.mask:
            if settings.mask.type == "nifti":
                verify_nifti_dimensions_match(settings.seed.path, settings.mask.path)
                verify_nifti_dimensions_match(settings.func.path, settings.mask.path)
                mask_data, _, _, _ = ciftify.niio.load_nifti(settings.mask.path)
            elif settings.mask.type == 'cifti':
                subcort_mask = os.path.join(tempdir, 'subcort_mask.nii.gz')
                ciftify.utils.run(['wb_command',
                  '-cifti-separate', settings.mask.path, 'COLUMN',
                  '-volume-all', subcort_mask])
                verify_nifti_dimensions_match(settings.seed.path, subcort_mask)
                mask_data, _, _, _ = ciftify.niio.load_nifti(subcort_mask)
            else:
                logger.error('<mask> file needs to be cifti or nifti')
                sys.exit(1)

    ## check that dim 0 of both seed and func
    if func_data.shape[0] != seed_data.shape[0]:
        logger.error("<func> and <seed> images have different number of voxels/vertices")
        sys.exit(1)

    if seed_data.shape[1] != 1:
        logger.warning("your seed volume has more than one timepoint")

    if settings.mask:
        if func_data.shape[0] != mask_data.shape[0]:
            logger.error("<func> and <mask> images have different number of voxels/vertices")
            sys.exit(1)
        if seed_data.shape[0] != mask_data.shape[0]:
            logger.error("<seed> and <mask> images have different number of voxels/vertices")
            sys.exit(1)

    return(func_data, seed_data, mask_data)

def calc_meants_with_numpy(settings, outputlabels = None):
    '''calculate the meants using numpy and write to file '''
    logger = logging.getLogger(__name__)
    ## even if no mask given, mask out all zero elements..
    with ciftify.utils.TempDir() as tempdir:
        func_data, seed_data, mask_data = load_data_as_numpy_arrays(settings, tempdir)

    mask_indices = np.where(np.isfinite(func_data[:,0]))[0]

    if settings.mask:
        # attempt to mask out non-brain regions in ROIs
        n_seeds = len(np.unique(seed_data))
        if seed_data.shape[0] != mask_data.shape[0]:
            logger.error('the mask and seed images have different number of voxels')
            sys.exit(1)
        mask_idx = np.where(mask_data > 0)[0]
        mask_indices = np.intersect1d(mask_indices, mask_idx)
        if len(np.unique(np.multiply(seed_data,mask_data))) != n_seeds:
            logger.error('At least 1 ROI completely outside mask for {}.'.format(outputcsv))
            sys.exit(1)

    if settings.weighted:
        out_data = np.average(func_data[mask_indices,:], axis=0,
                              weights=np.ravel(seed_data[mask_indices]))
        out_data = out_data.reshape(1,out_data.shape[0]) ## reshaping to match non-weigthed output
    else:
        # init output vector
        if settings.roi_label:
            if float(settings.roi_label) not in np.unique(seed_data)[1:]:
               sys.exit('ROI {}, not in seed map labels: {}'.format(settings.roi_label, np.unique(seed_data)[1:]))
            else:
               rois = [float(settings.roi_label)]
        else:
            rois = np.unique(seed_data)[1:]
        out_data = np.zeros((len(rois), func_data.shape[1]))

        # get mean seed dataistic from each, append to output
        for i, roi in enumerate(rois):
            idx = np.where(seed_data == roi)[0]
            idxx = np.intersect1d(mask_indices, idx)
            out_data[i,:] = np.mean(func_data[idxx, :], axis=0)

    # write out csv
    if settings.outputcsv: np.savetxt(settings.outputcsv, out_data, delimiter=",")
    if outputlabels: np.savetxt(outputlabels, rois, delimiter=",")

    # return the meants
    return(out_data)
