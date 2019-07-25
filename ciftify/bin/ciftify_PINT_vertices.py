#!/usr/bin/env python3
"""
Beta version of script find PINT (Personal Instrisic Network Topography)

Usage:
  ciftify_PINT_vertices [options] <func.dtseries.nii> <left-surface.gii> <right-surface.gii> <input-vertices.csv> <outputprefix>

Arguments:
    <func.dtseries.nii>    Paths to directory source image
    <left-surface.gii>     Path to template for the ROIs of network regions
    <right-surface.gii>    Surface file .surf.gii to read coordinates from
    <input-vertices.csv>   Table of template vertices from which to Start
    <outputprefix>         Output csv file

Options:
  --outputall            Output vertices from each iteration.

  --pre-smooth FWHM      Add smoothing [default: 0] for PINT iterations. See details.
  --sampling-radius MM   Radius [default: 6] in mm of sampling rois
  --search-radius MM     Radius [default: 6] in mm of search rois
  --padding-radius MM    Radius [default: 12] in mm for min distance between roi centers

  --pcorr                Use maximize partial correlation within network (instead of pearson).
  --corr                 Use full correlation instead of partial (default debehviour is --pcorr)

  -v,--verbose           Verbose logging
  --debug                Debug logging in Erin's very verbose style
  -h,--help              Print help

DETAILS:
The pre-smooth option will add smoothing in order to make larger resting state gradients
more visible in noisy data. Final extration of the timeseries use the original (un-smoothed)
functional input.

Written by Erin W Dickie, April 2016
"""
import random
import os
import sys
import logging
import pandas as pd
import nibabel.gifti.giftiio
from scipy import stats, linalg
import numpy as np
import nibabel as nib
from docopt import docopt

import ciftify

# Read logging.conf
logger = logging.getLogger('ciftify')
logger.setLevel(logging.DEBUG)

############################## maub starts here ######################
def run_PINT(arguments, tmpdir):
    global RADIUS_SAMPLING
    global RADIUS_SEARCH
    global RADIUS_PADDING

    func          = arguments['<func.dtseries.nii>']
    surfL         = arguments['<left-surface.gii>']
    surfR         = arguments['<right-surface.gii>']
    origcsv       = arguments['<input-vertices.csv>']
    output_prefix = arguments['<outputprefix>']
    pcorr         = arguments['--pcorr']
    corr         = arguments['--corr']
    pre_smooth_fwhm = arguments['--pre-smooth']
    outputall     = arguments['--outputall']
    RADIUS_SAMPLING = arguments['--sampling-radius']
    RADIUS_SEARCH = arguments['--search-radius']
    RADIUS_PADDING = arguments['--padding-radius']

    logger.debug(arguments)

    logger.info("Arguments: ")
    logger.info('    functional data: {}'.format(func))
    logger.info('    left surface: {}'.format(surfL))
    logger.info('    right surface: {}'.format(surfR))
    logger.info('    pint template csv: {}'.format(origcsv))
    logger.info('    output prefix: {}'.format(output_prefix))

    ## calc and report the pre-smoothing
    pre_smooth_sigma = ciftify.utils.FWHM2Sigma(pre_smooth_fwhm)
    if pre_smooth_sigma > 0:
        logger.info('Pre-smoothing FWHM: {} (Sigma {})'.format(pre_smooth_fwhm,
                                                               pre_smooth_sigma))
    else:
        logger.info('Pre-smoothing: None')

    logger.info('    Sampling ROI radius (mm): {}'.format(RADIUS_SAMPLING))
    logger.info('    Search ROI radius (mm): {}'.format(RADIUS_SEARCH))
    logger.info('    Paddding ROI radius (mm): {}'.format(RADIUS_PADDING))

    if corr and pcorr:
        logger.critical("Error: --corr and --pcorr options cannot be used together")
        sys.exit(1)

    if corr: pcorr == False

    if not pcorr and not corr: pcorr = True

    if pcorr:
        logger.info('    Maximizing partial correlation')
    else:
        logger.info('    Maximizing full correlation')

    logger.info(ciftify.utils.section_header('Starting PINT'))

    ## loading the dataframe
    df = pd.read_csv(origcsv)
    if 'roiidx' not in df.columns:
        df.loc[:,'roiidx'] = pd.Series(np.arange(1,len(df.index)+1), index=df.index)

    ## cp the surfaces to the tmpdir - this will cut down on i-o is tmpdir is ramdisk
    tmp_surfL = os.path.join(tmpdir, 'surface.L.surf.gii')
    tmp_surfR = os.path.join(tmpdir, 'surface.R.surf.gii')
    docmd(['cp', surfL, tmp_surfL])
    docmd(['cp', surfR ,tmp_surfR])
    surfL = tmp_surfL
    surfR = tmp_surfR

    ## run the main iteration
    df, max_distance, distance_outcol, iter_num = iterate_pint(df, 'tvertex',
                                                        func, surfL, surfR,
                                                        pcorr, pre_smooth_sigma)

    if outputall:
        cols_to_export = list(df.columns.values)
    else:
        cols_to_export = ['hemi','NETWORK','roiidx','tvertex','pvertex','distance']
        if max_distance > 1:
            cols_to_export.extend([distance_outcol, 'vertex_{}'.format(iter_num - 2)])

    df.to_csv('{}_summary.csv'.format(output_prefix), columns = cols_to_export, index = False)

    ## load the sampling data
    func_data, func_zeros, _ = read_func_data(func,
                                    smooth_sigma = 0, surfL = None, surfR = None)

    ## output the tvertex meants
    sampling_rois = rois_bilateral(df, 'tvertex', RADIUS_SAMPLING, surfL, surfR)
    sampling_rois[func_zeros] = 0
    calc_sampling_meants(func_data, sampling_rois,
    outputcsv_name="{}_tvertex_meants.csv".format(output_prefix))
    ## output the pvertex meants
    sampling_rois = rois_bilateral(df, 'pvertex', RADIUS_SAMPLING, surfL, surfR)
    sampling_rois[func_zeros] = 0
    calc_sampling_meants(func_data, sampling_rois,
    outputcsv_name="{}_pvertex_meants.csv".format(output_prefix))


### Erin's little function for running things in the shell
def docmd(cmdlist):
    '''run command and echo it to debug log '''
    ciftify.utils.run(cmdlist, suppress_echo = True)

def pint_logo():
    ''' logo from ascii text with font fender'''
    logo = """
'||'''|, |''||''| '||\   ||` |''||''|
 ||   ||    ||     ||\\  ||     ||
 ||...|'    ||     || \\ ||     ||
 ||         ||     ||  \\||     ||
.||      |..||..| .||   \||.   .||.
"""
    return(logo)

def log_build_environment():
    '''print the running environment info to the logs (info)'''
    logger.info("{}---### Environment Settings ###---".format(os.linesep))
    logger.info("Username: {}".format(get_stdout(['whoami'], echo = False).replace(os.linesep,'')))
    logger.info(ciftify.config.system_info())
    logger.info(ciftify.config.ciftify_version(os.path.basename(__file__)))
    logger.info(ciftify.config.wb_command_version())
    logger.info("---### End of Environment Settings ###---{}".format(os.linesep))
## measuring distance

def read_func_data(func, smooth_sigma, surfL, surfR):
    ''' read in the functional surface data (with or without pre-smoothing)'''

    ## separate the cifti file into left and right surfaces
    with ciftify.utils.TempDir() as lil_tempdir:
        # separate the data and the rois from the cifti file.
        L_data_surf=os.path.join(lil_tempdir, 'Ldata.func.gii')
        R_data_surf=os.path.join(lil_tempdir, 'Rdata.func.gii')
        L_roi = os.path.join(lil_tempdir, 'L_roi.shape.gii')
        R_roi = os.path.join(lil_tempdir, 'R_roi.shape.gii')
        docmd(['wb_command','-cifti-separate', func, 'COLUMN',
            '-metric', 'CORTEX_LEFT', L_data_surf, '-roi', L_roi,
            '-metric', 'CORTEX_RIGHT', R_data_surf, '-roi', R_roi])

        ## do the optional smoothing
        if smooth_sigma > 0:
            # smooth the data using the roi output from the cifti file
            L_data_sm = os.path.join(lil_tempdir, 'Ldata_sm.func.gii')
            R_data_sm = os.path.join(lil_tempdir, 'Rdata_sm.func.gii')
            docmd(['wb_command', '-metric-smoothing',
                surfL, L_data_surf, str(smooth_sigma), L_data_sm, '-roi', L_roi])
            docmd(['wb_command', '-metric-smoothing',
                surfR, R_data_surf, str(smooth_sigma), R_data_sm, '-roi', R_roi])
        else:
            # if no smoothing use the un-smoothed data for the next step
            L_data_sm = L_data_surf
            R_data_sm = R_data_surf

        ## load both surfaces and concatenate them together
        func_dataL = ciftify.niio.load_gii_data(L_data_sm)
        func_dataR = ciftify.niio.load_gii_data(R_data_sm)
        Lroi_data = ciftify.niio.load_gii_data(L_roi)
        Rroi_data = ciftify.niio.load_gii_data(R_roi)

    ## stack the left and right surfaces
    num_Lverts = func_dataL.shape[0]
    func_data = np.vstack((func_dataL, func_dataR))

    ## determiner the roi
    func_zeros1 = np.where(func_data[:,5]<5)[0]
    logger.debug('Shape of func_zeros1: {}'.format(func_zeros1.shape))
    cifti_roi_data = np.vstack((Lroi_data, Rroi_data))
    func_zeros2 = np.where(cifti_roi_data[:,0]<1)[0]
    logger.debug('Shape of func_zeros2: {}'.format(func_zeros2.shape))
    func_zeros = np.intersect1d(func_zeros1, func_zeros2)
    logger.debug('Shape of func_zeros: {}'.format(func_zeros.shape))

    return func_data, func_zeros, num_Lverts


def calc_surf_distance(surf, orig_vertex, target_vertex, radius_search):
    '''
    uses wb_command -surface-geodesic-distance command to measure
    distance between two vertices on the surface
    '''
    if int(orig_vertex) == int(target_vertex):
        distance = 0
    else:
        distances = ciftify.niio.get_surf_distances(surf, orig_vertex,
                                                         radius_search = radius_search,
                                                         suppress_echo = True)
        distance = distances[target_vertex,0]
    return(distance)

def calc_distance_column(df, orig_vertex_col, target_vertex_col,distance_outcol,
                         radius_search, surfL, surfR):
    df.loc[:,distance_outcol] = -99.9
    for idx in df.index.tolist():
        orig_vertex = df.loc[idx, orig_vertex_col]
        target_vertex = df.loc[idx, target_vertex_col]
        hemi = df.loc[idx,'hemi']
        if hemi == "L":
            df.loc[idx, distance_outcol] = calc_surf_distance(surfL, orig_vertex,
                                            target_vertex, radius_search)
        if hemi == "R":
            df.loc[idx, distance_outcol] = calc_surf_distance(surfR, orig_vertex,
                                            target_vertex, radius_search)
    return df

def roi_surf_data(df, vertex_colname, surf, hemisphere, roi_radius):
    '''
    uses wb_command -surface-geodesic-rois to build rois (3D files)
    then load and collasp that into 1D array
    '''
    ## right the L and R hemisphere vertices from the table out to temptxt
    with ciftify.utils.TempDir() as lil_tmpdir:
        ## write a temp vertex list file
        vertex_list = os.path.join(lil_tmpdir, 'vertex_list.txt')
        df.loc[df.hemi == hemisphere, vertex_colname].to_csv(vertex_list,sep='\n',index=False, header=False)

        ## from the temp text build - func masks and target masks
        roi_surf = os.path.join(lil_tmpdir,'roi_surf.func.gii')
        docmd(['wb_command', '-surface-geodesic-rois', surf,
            str(roi_radius),  vertex_list, roi_surf,
            '-overlap-logic', 'EXCLUDE'])
        rois_data = ciftify.niio.load_gii_data(roi_surf)

    ## multiply by labels and reduce to 1 vector
    vlabels = df[df.hemi == hemisphere].roiidx.tolist()
    rois_data = np.multiply(rois_data, vlabels)
    rois_data1D = np.max(rois_data, axis=1)

    return rois_data1D

def rois_bilateral(df, vertex_colname, roi_radius, surfL, surfR):
    '''
    runs roi_surf_data for both surfaces and combines them to one numpy array
    '''
    rois_L = roi_surf_data(df, vertex_colname, surfL, 'L', roi_radius)
    rois_R = roi_surf_data(df, vertex_colname, surfR, 'R', roi_radius)
    rois = np.hstack((rois_L, rois_R))
    return rois

def calc_network_meants(sampling_meants, df):
    '''
    calculate the network mean timeseries from many sub rois
    '''
    netmeants = pd.DataFrame(np.nan,
                                index = list(range(sampling_meants.shape[1])),
                                columns = df['NETWORK'].unique())
    for network in netmeants.columns:
        netlabels = df[df.NETWORK == network].roiidx.tolist()
        netmeants.loc[:,network] = np.mean(sampling_meants[(np.array(netlabels)-1), :], axis=0)
    return netmeants

def calc_sampling_meants(func_data, sampling_roi_mask, outputcsv_name=None):
    '''
    output a np.arrary of the meants for every index in the sampling_roi_mask
    '''
    # init output vector
    rois = np.unique(sampling_roi_mask)[1:]
    out_data = np.zeros((len(rois), func_data.shape[1]))

    # get mean seed dataistic from each, append to output
    for i, roi in enumerate(rois):
        idx = np.where(sampling_roi_mask == roi)[0]
        out_data[i,:] = np.mean(func_data[idx, :], axis=0)

    ## if the outputfile argument was given, then output the file
    if outputcsv_name:
        np.savetxt(outputcsv_name, out_data, delimiter=",")

    return(out_data)

def linalg_calc_residulals(X, Y):
    ''' Run regression of X on Y and return the residuals
    Parameters
    ---------------
    X : 2D numpy matrix the predictors/confounds for the model
    Y : 1D vector of dependant variables
    Returns
    ----------------
    Residuals as 1D array
    '''
    betas = np.linalg.lstsq(X, Y, rcond = -1)[0]
    residuals = Y - X.dot(betas)
    return(residuals)

def mass_partial_corr(X,massY,Z):
    ''' mass partial correlation between X and many Y signals after regressing Z from both sides
    Parameters
    -----------
    X : 1D predictor vector (n observations)
    massY : 2D numpy matrix of signals to correlate (k signals by n observations)
    Z : 2D numpy matrix of signals to regress from both X and Y (n observations by p confounds)
    Returns
    -----------
    1D vector or partial correlations (k signals long)
    '''

    assert X.shape[0]==massY.shape[1]
    assert massY.shape[1]==Z.shape[0]

    ## stack X and Y together to prepare to regress
    pre_res = np.vstack((X,massY))

    ## loop over all signals and to regress out confounds
    res_by_z = np.zeros(pre_res.shape) -1
    for i in range(pre_res.shape[0]):
        res_by_z[i,:] = linalg_calc_residulals(Z, pre_res[i,:])

    ## correlate all the residuals, take the relevant values from the first row
    mass_pcorrs = np.corrcoef(res_by_z)[0, 1:]

    assert len(mass_pcorrs)==massY.shape[0]

    return(mass_pcorrs)

def pint_move_vertex(df, idx, vertex_incol, vertex_outcol,
                     func_data, sampling_meants,
                     search_rois, padding_rois, pcorr,
                     num_Lverts, netmeants = None):
    '''
    move one vertex in the pint algorithm
    inputs:
      df: the result dataframe
      idx: this vertices row index
      sampling_meants: the meants matrix calculated from the sampling rois
      search_rois: the search rois (the extent of the search radius)
      padding_rois: the padding rois (the mask that prevent search spaces from overlapping)
      pcorr : wether or not to use partial corr
      netmeants: netmeants object if running pcorr (if set to None, regular correlation is run)
    '''
    vlabel = df.loc[idx,'roiidx']
    network = df.loc[idx,'NETWORK']
    hemi = df.loc[idx,'hemi']
    orig_vertex = df.loc[idx, vertex_incol]

    ## get the meants - excluding this roi from the network
    netlabels = list(set(df[df.NETWORK == network].roiidx.tolist()) - set([vlabel]))
    meants = np.mean(sampling_meants[(np.array(netlabels) - 1), :], axis=0)

    # the search space is the intersection of the search radius roi and the padding rois
    # (the padding rois creates and exclusion mask if rois are to close to one another)
    idx_search = np.where(search_rois == vlabel)[0]
    idx_pad = np.where(padding_rois == vlabel)[0]
    idx_mask = np.intersect1d(idx_search, idx_pad, assume_unique=True)

    # if there padding mask and the search mask have no overlap - size is 0
    # there is nowhere for this vertex to move to so return the orig vertex id
    if not idx_mask.size:
        df.loc[idx,vertex_outcol] = orig_vertex

    else:
        # create output array
        seed_corrs = np.zeros(func_data.shape[0]) - 1

        # loop through each time series, calculating r
        if pcorr:
            o_networks = set(netmeants.columns.tolist()) - set([network])
            seed_corrs[idx_mask] = mass_partial_corr(meants,
                                      func_data[idx_mask, :],
                                      netmeants.loc[:,o_networks].values)
        else:
            seed_corrs[idx_mask] = np.corrcoef(meants,
                                                  func_data[idx_mask, :])[0, 1:]
        ## record the vertex with the highest correlation in the mask
        peakvert = np.argmax(seed_corrs, axis=0)
        if hemi =='R': peakvert = peakvert - num_Lverts
        df.loc[idx,vertex_outcol] = peakvert

    ## return the df
    return df

def iterate_pint(df, vertex_incol, func, surfL, surfR, pcorr, smooth_sigma = 0):
    '''
    The main bit of pint

    Args:
      df : the summary dataframe
      vertex_incol: the name of the column to use as the template rois
      func_data: the numpy array of the data
      func_data_mask: a mask of non-zero values from the func data
      pcorr: wether or not to use partial correlation
      smooth_sigma: the pre-smoothing sigma

    Return:
        the summary dataframe
    '''

    func_data, func_zeros, num_Lverts = read_func_data(func, smooth_sigma,
                                                        surfL, surfR)

    iter_num = 0
    max_distance = 10

    while iter_num < (50) and max_distance > 1:
        vertex_outcol = 'vertex_{}'.format(iter_num)
        distance_outcol = 'dist_{}'.format(iter_num)
        df.loc[:,vertex_outcol] = -999
        df.loc[:,distance_outcol] = -99.9

        ## load the sampling data
        sampling_rois = rois_bilateral(df, vertex_incol, RADIUS_SAMPLING, surfL, surfR)
        sampling_rois[func_zeros] = 0

        ## load the search data
        search_rois = rois_bilateral(df, vertex_incol, RADIUS_SEARCH, surfL, surfR)
        search_rois[func_zeros] = 0

        ## load the padding-radius data
        padding_rois = rois_bilateral(df, vertex_incol, RADIUS_PADDING, surfL, surfR)

        ## calculate the sampling meants array
        sampling_meants = calc_sampling_meants(func_data, sampling_rois)

        ## if we are doing partial corr create a matrix of the network
        if pcorr:
            netmeants = calc_network_meants(sampling_meants, df)
        else:
            netmeants = None

        ## run the pint_move_vertex function for each vertex
        thisorder = df.index.tolist()
        random.shuffle(thisorder)
        for idx in thisorder:
            df = pint_move_vertex(df, idx, vertex_incol, vertex_outcol,
                                  func_data, sampling_meants,
                                  search_rois, padding_rois, pcorr,
                                  num_Lverts, netmeants)

        ## calc the distances
        df = calc_distance_column(df, vertex_incol, vertex_outcol, distance_outcol, RADIUS_SEARCH, surfL, surfR)
        numNotDone = df.loc[df.loc[:,distance_outcol] > 0, 'roiidx'].count()

        ## print the max distance as things continue..
        max_distance = max(df[distance_outcol])
        logger.info('Iteration {} \tmax distance: {}\tVertices Moved: {}'.format(iter_num, max_distance, numNotDone))
        vertex_incol = vertex_outcol
        iter_num += 1

    ## calc a final distance column
    df.loc[:,"pvertex"] = df.loc[:,vertex_outcol]
    df  = calc_distance_column(df, 'tvertex', 'pvertex', 'distance', 150, surfL, surfR)

    ## return the df
    return df, max_distance, distance_outcol, iter_num

def main():
    arguments  = docopt(__doc__)
    verbose      = arguments['--verbose']
    debug        = arguments['--debug']
    output_prefix = arguments['<outputprefix>']

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    if verbose:
        ch.setLevel(logging.INFO)
    if debug:
        ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(message)s')

    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Get settings, and add an extra handler for the subject log
    local_logpath = os.path.dirname(output_prefix)
    if not os.path.exists(local_logpath): os.mkdir(local_logpath)
    fh = logging.FileHandler('{}_pint.log'.format(output_prefix))
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info('{}{}'.format(pint_logo(),
        ciftify.utils.section_header("Personalized Intrinsic Network Topolography (PINT)")))
    with ciftify.utils.TempDir() as tmpdir:
        ret = run_PINT(arguments, tmpdir)
    logger.info(ciftify.utils.section_header("Done PINT"))
    sys.exit(ret)


if __name__ == '__main__':
    main()
