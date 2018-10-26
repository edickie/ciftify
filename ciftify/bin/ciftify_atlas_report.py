#!/usr/bin/env python3
"""
Takes a atlas or cluster map ('dlabel.nii') and outputs a csv of results

Usage:
    ciftify_atlas_report [options] <clust.dlabel.nii>

Arguments:
    <clust.dlabel.nii>    Input atlas or cluster map.

Options:
    --outputcsv PATH    Path for csv report. (defaults to location of input)

    --left-surface GII     Left surface file (default is HCP S1200 Group Average)
    --right-surface GII    Right surface file (default is HCP S1200 Group Average)
    --left-surf-area GII   Left surface vertex areas file (default is HCP S1200 Group Average)
    --right-surf-area GII  Right surface vertex areas file (default is HCP S1200 Group Average)

    --map-number INT    The map number [default: 1] within the dlabel file to report on.

    --debug                Debug logging
    -n,--dry-run           Dry run
    -h, --help             Prints this message

DETAILS:

If an outputcsv argument is not given, the output will be set to the location of dlabel input.

"""
from docopt import docopt
import os, sys
import numpy as np
import pandas as pd
import logging
import logging.config
import ciftify.niio
import ciftify.report
import ciftify.utils
from ciftify.meants import NibInput

config_path = os.path.join(os.path.dirname(ciftify.config.find_ciftify_global()), 'bin', "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

def load_LR_vertex_areas(surf_settings):
    ''' loads the vertex areas and stacks the dataframes'''
    surf_va_L = ciftify.niio.load_gii_data(surf_settings.L.vertex_areas)
    surf_va_R = ciftify.niio.load_gii_data(surf_settings.R.vertex_areas)
    surf_va_LR = np.vstack((surf_va_L, surf_va_R))
    return(surf_va_LR)


def report_atlas_overlap(df, label_data, atlas, surf_va_LR, min_percent_overlap = 5):
    # read the atlas
    atlas_data, atlas_dict = ciftify.niio.load_LR_label(atlas['path'],
                                                    int(atlas['map_number']))
    # write an overlap report to the outputfile
    o_col = '{}_overlap'.format(atlas['name'])
    df[o_col] = ""
    for pd_idx in df.index.get_values():
        df.loc[pd_idx, o_col] = ciftify.report.get_label_overlap_summary(
                        pd_idx, label_data, atlas_data, atlas_dict, surf_va_LR,
                        min_percent_overlap = min_percent_overlap)
    return(df)


def run_ciftify_dlabel_report(arguments, tmpdir):

    dlabel = NibInput(arguments['<clust.dlabel.nii>'])
    dlabel_map_number = int(arguments['--map-number'])
    outputcsv = arguments['--outputcsv']
    logger.info('Outputcsv: {}'.format(outputcsv))

    surf_settings = ciftify.report.CombinedSurfaceSettings(arguments, tmpdir)
    atlas_settings = ciftify.report.define_atlas_settings()

    ## load the data
    label_data, label_dict = ciftify.niio.load_LR_label(dlabel.path,
                                                      dlabel_map_number)

    ## define the outputcsv
    if not outputcsv:
        outputname = '{}_label_report.csv'.format(dlabel.base)
        outputcsv = os.path.join(os.path.dirname(dlabel.path), outputname)
        ciftify.utils.check_output_writable(outputcsv, exit_on_error = True)
        logger.info('Output table: {}'.format(outputcsv))

    ## load the vertex areas
    surf_va_LR = load_LR_vertex_areas(surf_settings)

    ## assert that the dimensions match
    if not (label_data.shape[0] == surf_va_LR.shape[0]):
        logger.error('label file vertices {} not equal to vertex areas {}'
                     ''.format(label_data.shape[0], surf_va_LR.shape[0]))
        sys.exit(1)

    ## use the label dict to start the report dataframe
    df = pd.DataFrame.from_dict(label_dict, orient = "index")
    df['label_idx'] = df.index
    df = df.rename(index=str, columns={0: "label_name"})


    # calculate a column of the surface area for row ROIs
    df['area'] = -999
    for pd_idx in df.index.get_values():
        df.loc[pd_idx, 'area']  = ciftify.report.calc_cluster_area(pd_idx,
                                                        label_data, surf_va_LR)

    for atlas in atlas_settings.values():
        df = report_atlas_overlap(df, label_data, atlas,
                                  surf_va_LR, min_percent_overlap = 5)


    df.to_csv(outputcsv)

def main():
    arguments = docopt(__doc__)

    logger.setLevel(logging.WARNING)

    if arguments['--debug']:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ## set up the top of the log
    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
        ciftify.utils.section_header('Starting ciftify_atlas_report')))

    ciftify.utils.log_arguments(arguments)

    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = run_ciftify_dlabel_report(arguments, tmpdir)

if __name__ == '__main__':
    main()
