#!/usr/bin/env python
"""
Makes temporary seed corr maps using a chosen roi for each network and
correlation maps

Usage:
    cifti_vis_PINT snaps [options] <func.dtseries.nii> <subject> <PINT_summary.csv>
    cifti_vis_PINT subject [options] <func.dtseries.nii> <subject> <PINT_summary.csv>
    cifti_vis_PINT index [options]

Arguments:
    <func.dtseries.nii>        A dtseries file to feed into
                               ciftify_PINT_vertices.py map
    <subject>                  Subject ID for HCP surfaces
    <PINT_summary.csv>         The output csv (*_summary.csv) from the PINT
                               analysis step

Options:
  --qcdir PATH             Full path to location of QC directory
  --ciftify-work-dir PATH  The directory for HCP subjects (overrides
                           CIFTIFY_WORKDIR/ HCP_DATA enivironment variables)
  --hcp-data-dir PATH      The directory for HCP subjects (overrides
                           CIFTIFY_WORKDIR/ HCP_DATA enivironment variables) DEPRECATED
  --subjects-filter STR    A string that can be used to filter out subject
                           directories
  --roi-radius MM          Specify the radius [default: 6] of the plotted rois
                           (in mm)
  -v,--verbose             Verbose logging
  --debug                  Debug logging in Erin's very verbose style
  -n,--dry-run             Dry run
  --help                   Print help

DETAILS
This makes pretty pictures of your hcp views using connectome workbenches
"show scene" commands. It pastes the pretty pictures together into some .html
QC pages

There are two subfunctions:

    snaps: will create all the pics as well as the subjects specific html view
    for one subject. This option requires the cifti file of functionl
    timeseries. The hcp subject id so that it can find the surface information
    to plot on. And the *_summary.csv file that was the output of
    find-PINT-vertices

    index: will make an index out of all the subjects in the qcdir

Note: this script requires the seaborn package to make the correlation
heatmaps...

Written by Erin W Dickie (erin.w.dickie@gmail.com) Jun 20, 2016
"""
import os
import sys
import logging
import logging.config
from abc import ABCMeta

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(context="paper", font="monospace")
import pandas as pd
import numpy as np
import nibabel as nib
from docopt import docopt

import ciftify
from ciftify.utils import VisSettings, add_metaclass, run
from ciftify.qc_config import replace_all_references, replace_path_references


DRYRUN = False
DEBUG = False

# Read logging.conf
config_path = os.path.join(os.path.dirname(__file__), "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

PINTnets = [{ 'NETWORK': 2, 'network':'VI', 'roiidx': 72, 'best_view': "APDV", 'Order': 6},
                { 'NETWORK': 3, 'network': 'DA', 'roiidx': 2, 'best_view': "APDV", 'Order': 1},
                { 'NETWORK': 4, 'network': 'VA', 'roiidx': 44, 'best_view': "LM", 'Order': 4},
                { 'NETWORK': 5, 'network': 'SM', 'roiidx': 62, 'best_view': "LM", 'Order': 5},
                { 'NETWORK': 6, 'network': 'FP', 'roiidx': 28, 'best_view': "LM", 'Order': 3},
                { 'NETWORK': 7, 'network': 'DM', 'roiidx': 14, 'best_view': "LM", 'Order': 2}]

class UserSettings(VisSettings):
    def __init__(self, arguments):
        VisSettings.__init__(self, arguments, qc_mode='PINT')
        ## Hack to account for fact that index doesnt expect these variables
        if arguments['subject'] or arguments['snaps']:
            self.subject = arguments['<subject>']
            self.func = self.__get_input_file(arguments['<func.dtseries.nii>'])
            self.pint_summary = self.__get_input_file(
                    arguments['<PINT_summary.csv>'])
            self.left_surface = self.__get_surface('L')
            self.right_surface = self.__get_surface('R')
        else:
            self.subject = None
            self.func = None
            self.pint_summary = None
        self.subject_filter = arguments['--subjects-filter']
        self.roi_radius = arguments['--roi-radius']

    def __get_surface(self, surface_type):
        surface = os.path.join(self.hcp_dir, self.subject, 'MNINonLinear',
                'fsaverage_LR32k',
                '{}.{}.midthickness.32k_fs_LR.surf.gii'.format(self.subject,
                surface_type))
        return self.__get_input_file(surface)

    def __get_input_file(self, file_path):
        if not os.path.exists(file_path):
            logger.critical("{} not found".format(file_path))
            sys.exit(1)
        return file_path

class FakeNifti(object):
    def __init__(self, func_path, tmp_dir):
        self.__func_fnifti = self.__make_fake_nifti(func_path, tmp_dir)
        self.data, self.affine, self.header, \
                self.dims = ciftify.io.load_nifti(self.__func_fnifti)
        self.template = self.__get_template(func_path, tmp_dir)

    def __make_fake_nifti(self, func_path, tmp_dir):
        nifti_path = os.path.join(tmp_dir, 'func.nii.gz')
        command_list = ['wb_command', '-cifti-convert', '-to-nifti', func_path,
                        nifti_path]
        run(command_list)
        if not os.path.exists(nifti_path):
            logger.critical("Failed to generate file critical file: {} failed "
                    "command: {}".format(nifti_path, " ".join(command_list)))
            sys.exit(1)
        return nifti_path

    def __get_template(self, func_path, tmp_dir):
        template_path = os.path.join(tmp_dir, 'template.dscalar.nii')
        command_list = ['wb_command', '-cifti-reduce', func_path, 'MIN',
                        template_path]
        run(command_list)
        if not os.path.exists(template_path):
            logger.critical("Failed to generate critical file: {} failed"
                    "command: {}".format(template_path, " ".format(
                    command_list)))
            sys.exit(1)
        return template_path

@add_metaclass(ABCMeta)
class PDDataframe(object):

    dataframe = None

    def make_dataframe(self, csv_path, header='infer'):
        try:
            data_frame = pd.read_csv(csv_path, header=header)
        except:
            logger.critical("Cannot make dataframe from file {}".format(
                    csv_path))
            sys.exit(1)
        return data_frame

class SummaryData(PDDataframe):
    vertex_types = ['tvertex', 'ivertex']

    def __init__(self, summary_csv):
        self.dataframe = self.make_dataframe(summary_csv)
        self.vertices = self.__make_vertices(summary_csv)

    def __make_vertices(self, summary_csv):
        vert_list = []
        for vertex in self.vertex_types:
            vert_list.append(Vertex(summary_csv, vertex))
        return vert_list

class Vertex(PDDataframe):
    def __init__(self, summary_csv, vert_type):
        self.vert_type = vert_type
        self.dataframe = self.__get_dataframe_type(summary_csv)

    def __get_dataframe_type(self, csv_path):
        new_path = csv_path.replace('_summary',
                '_{}_meants'.format(self.vert_type))
        data_frame = self.make_dataframe(new_path, header=None)
        return data_frame.transpose()

    def make_heat_map(self, summary_dataframe, output_dir):
        vertex_corrpic = os.path.join(output_dir,
                                      '{}_corrmat.png'.format(self.vert_type))

        ## Sets title to associate with this image
        if self.vert_type == 'tvertex':
            self.title = "Pre (tvertex)"
        else:
            self.title = "Post (ivertex)"

        corrmat = self.dataframe.corr()
        # Set up the matplotlib figure
        f, ax = plt.subplots(figsize=(10, 8))

        # Draw the heatmap using seaborn
        sns.heatmap(corrmat, vmax=.9, square=True)

        # Use matplotlib directly to emphasize known networks
        for i in summary_dataframe.index:
            if i and summary_dataframe.loc[i, 'NETWORK'] != \
                    summary_dataframe.loc[i-1, 'NETWORK']:
                ax.axhline(len(summary_dataframe) - i, c="w", linewidth=3.0)
                ax.axvline(i, c="w", linewidth=3.0)
        f.tight_layout()
        f.savefig(vertex_corrpic)
        self.heat_map = vertex_corrpic
        return vertex_corrpic

    def make_rois(self, network_csv, network_df, left_surface, right_surface,
            seed_radius, output_dir):
        self.xrois = os.path.join(output_dir, 'xrois.dscalar.nii')
        self.__generate_roi(self.vert_type, network_csv, seed_radius,
                left_surface, right_surface, self.xrois)

        if self.__needs_yrois(network_df):
            self.yrois = os.path.join(output_dir, 'yrois.dscalar.nii')
            self.__generate_roi('vertex_48', network_csv, seed_radius,
                    left_surface, right_surface, self.yrois)
        else:
            self.yrois = self.xrois

        self.rois = self.__combine_rois_and_set_palette(output_dir)

    def __needs_yrois(self, network_df):
        if self.vert_type == 'tvertex':
            return False
        # if vertex_48 is in df, means failed to stop iterating
        if 'vertex_48' not in network_df.columns:
            return False
        if network_df.loc[:,'dist_49'].sum() <= 0:
            return False
        return True

    def __generate_roi(self, vert_type, network_csv, seed_radius, l_surface,
            r_surface, output):
        ## make the overlaying ROIs
        run(['ciftify_surface_rois', '--vertex-col', vert_type, network_csv,
                str(seed_radius), l_surface, r_surface, output])
        if not os.path.exists(output):
            logger.error("Could not generate needed ROIs output file: "
                    "{}".format(output))
            sys.exit(1)
        return

    def __combine_rois_and_set_palette(self, output_dir):
        rois = os.path.join(output_dir, 'rois.dscalar.nii')
        ## combine xrois and yrois into one roi result
        run(['wb_command -cifti-math "((x*2)+y)"', rois, '-var','x',
                self.xrois, '-var', 'y', self.yrois],suppress_stdout=True)
        ## set the palette on the roi to power_surf (mostly grey)
        run(['wb_command', '-cifti-palette', rois, 'MODE_AUTO_SCALE', rois,
                '-palette-name', 'power_surf'])
        if not os.path.exists(rois):
            logger.error("Could not generate final ROI file: {}".format(rois))
            sys.exit(1)
        return rois

    def make_seed_corr(self, summary_df, network, func_fnifti, temp_dir):
        self.seed_corr = os.path.join(temp_dir, 'scorr{}{}.dscalar.nii'.format(
                self.vert_type, network))
        meants = self.dataframe.loc[:, summary_df.loc[:, 'NETWORK'] ==
                network].mean(axis=1)

        temp_nifti_seed = os.path.join(temp_dir, 'seedcorr{}.nii.gz'.format(
                network))
        ## correlated the mean timeseries with the func data
        out = np.zeros([func_fnifti.dims[0]*func_fnifti.dims[1]*func_fnifti.dims[2],
                1])
        ## determine brainmask bits..
        std_array = np.std(func_fnifti.data, axis=1)
        m_array = np.mean(func_fnifti.data, axis=1)
        std_nonzero = np.where(std_array > 0)[0]
        m_nonzero = np.where(m_array != 0)[0]
        mask_indices = np.intersect1d(std_nonzero, m_nonzero)
        for i in mask_indices:
            out[i] = np.corrcoef(meants, func_fnifti.data[i, :])[0][1]
        ## reshape data and write it out to a fake nifti file
        out = out.reshape([func_fnifti.dims[0], func_fnifti.dims[1],
                func_fnifti.dims[2], 1])
        out = nib.nifti1.Nifti1Image(out, func_fnifti.affine)
        out.to_filename(temp_nifti_seed)

        ## convert back
        run(['wb_command','-cifti-convert','-from-nifti',
                temp_nifti_seed, func_fnifti.template, self.seed_corr])

        run(['wb_command', '-cifti-palette', self.seed_corr,
                'MODE_AUTO_SCALE_PERCENTAGE', self.seed_corr,
                '-palette-name', 'PSYCH-NO-NONE'])
        if not os.path.exists(self.seed_corr):
            logger.error("Could not generate seed corr file {} for {}"
                    "".format(self.seed_corr, self.vert_type))
            sys.exit(1)

def main():
    global DEBUG
    arguments  = docopt(__doc__)
    snaps      = arguments['subject'] or arguments['snaps']
    index      = arguments['index']
    verbose    = arguments['--verbose']
    DEBUG      = arguments['--debug']

    if arguments['snaps']:
        logger.warning("The 'snaps' argument has be deprecated. Please use 'subject' in the future.")

    if verbose:
        logger.setLevel(logging.INFO)
        # Also set level for all loggers in ciftify module (or else will be
        # logging.WARN by default)
        logging.getLogger('ciftify').setLevel(logging.INFO)
    if DEBUG:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    ciftify.utils.log_arguments(arguments)

    settings = UserSettings(arguments)
    qc_config = ciftify.qc_config.Config(settings.qc_mode)

    ## make pics and qcpage for each subject
    if snaps:
        with ciftify.utils.TempDir() as temp_dir:
            logger.debug('Created tempdir {} on host {}'.format(temp_dir,
                    os.uname()[1]))
            logger.info("Making snaps for subject: {}".format(
                    settings.subject))
            ret = run_snaps(settings, qc_config, temp_dir, temp_dir)
        return ret

    # Start the index html file
    if index:
        logger.info("Writing Index pages to: {}".format(settings.qc_dir))
        ret = write_all_index_pages(settings, qc_config)
        return ret

def run_snaps(settings, qc_config, scene_dir, temp_dir):
    '''
    Do all the qc stuff for the one subject.
    '''
    qc_subdir = os.path.join(settings.qc_dir, settings.subject)

    ciftify.utils.make_dir(qc_subdir, dry_run=DRYRUN)

    func_nifti = FakeNifti(settings.func, temp_dir)
    summary_data = SummaryData(settings.pint_summary)

    qc_sub_html = os.path.join(qc_subdir, 'qc_sub.html')
    with open(qc_sub_html,'w') as qc_sub_page:
        write_header_and_navbar(qc_sub_page, settings.subject, PINTnets,
                title="{} PINT results".format(settings.subject), path='../')
        qc_sub_page.write('<h1> {} PINT results</h1>\n'.format(settings.subject))
        write_heat_maps(qc_sub_page, qc_subdir, summary_data)
        for pint_dict in PINTnets:
            # for each seed vertex make an roi and generate a seed map
            ## get info from the seed_dict
            roiidx = pint_dict['roiidx']
            network = pint_dict['network']
            NETWORK = pint_dict['NETWORK']

            ## make a dscalar of the network map
            network_csv = os.path.join(temp_dir, 'networkdf.csv')
            networkdf = summary_data.dataframe.loc[
                    summary_data.dataframe.loc[:,'NETWORK'] == NETWORK,:]
            networkdf.to_csv(network_csv, index=False)

            qc_sub_page.write('<div class="container" style="width: 100%;">\n')
            qc_sub_page.write('  <h2>{} Network</h2>\n'.format(network))

            for vertex in summary_data.vertices:
                logging.info('Running {} {} snaps:'.format(network,
                        vertex.vert_type))

                vertex.make_rois(network_csv, networkdf,
                        settings.left_surface, settings.right_surface,
                        settings.roi_radius, temp_dir)
                vertex.make_seed_corr(summary_data.dataframe, NETWORK,
                        func_nifti, temp_dir)

                scene_file = personalize_template(qc_config, settings,
                        scene_dir, network, vertex)

                qc_html = os.path.join(qc_subdir, 'qc_{}{}.html'.format(
                        vertex.vert_type, network))
                with open(qc_html, 'w') as qc_page:
                    write_subject_page(qc_config, qc_page, scene_file,
                            settings.subject, qc_subdir, vertex, network)
                    fav_pic = '{}{}_{}.png'.format(vertex.vert_type, network,
                            pint_dict['best_view'])
                    ciftify.html.write_image(qc_sub_page, 12,
                            os.path.basename(qc_page.name), fav_pic,
                            "Network {} {}".format(network, vertex.vert_type))
            ## add a div around the subject page container
            qc_sub_page.write('</div>\n')

def write_subjects_page_header(qc_sub_page, subject, network_dict):
    qc_sub_page.write('<!DOCTYPE html>\n<HTML><TITLE> {} PINT results'
            '</TITLE>\n'.format(subject))
    ciftify.html.write_header(qc_sub_page)
    qc_sub_page.write('<body>\n')
    write_navigation_bar(network_dict)

def write_header_and_navbar(html_page, page_subject, PINTnets,
        title='PINT results', path='', active_link=None):
    html_page.write('<!DOCTYPE html>\n<HTML><TITLE>{}</TITLE>\n'.format(title))
    ciftify.html.write_header(html_page)
    html_page.write('<body>\n')

    nav_list = [{'href': '', 'label': 'Network:'}]
    for pint_dict in PINTnets:
        network_page = os.path.join(path, "network_{}.html".format(
                pint_dict['network']))
        nav_list.append({'href': network_page,
                         'label': pint_dict['network']})
    corrmat_page = os.path.join(path, "corrmats.html")
    nav_list.append({'href': corrmat_page, 'label':'Correlation Matrixes'})
    index_page = os.path.join(path, "index.html")
    nav_list.append({'href': index_page, 'label':'Index'})
    ciftify.html.write_navbar(html_page, page_subject, nav_list,
                    activelink=active_link)

def write_heat_maps(qc_page, qc_dir, summary_data):
    qc_page.write('<div class="container" style="width: 100%;">')
    qc_parent_dir = os.path.dirname(qc_page.name)
    for vertex in summary_data.vertices:
        heat_map = vertex.make_heat_map(summary_data.dataframe, qc_dir)
        map_relpath = os.path.relpath(heat_map, qc_parent_dir)
        ciftify.html.write_image(qc_page, 6, map_relpath, map_relpath,
                vertex.title)
    qc_page.write('</div>\n')

def personalize_template(qc_config, settings, scene_dir, network, vertex):
    with open(qc_config.template, 'r') as template_text:
        template_contents = template_text.read()

    if not template_contents:
        logger.error("{} cannot be read or is empty".format(qc_config.template))
        sys.exit(1)

    scene_file = os.path.join(scene_dir, 'seedcorr_{}_{}{}.scene'.format(
            settings.subject, network, vertex.vert_type))

    with open(scene_file, 'w') as scene_stream:
        scene_text = modify_template_contents(template_contents, scene_file,
                settings, vertex)
        scene_stream.write(scene_text)

    return scene_file

def modify_template_contents(template_contents, scene_file, settings, vertex):
    """
    Customizes a template file to a specific hcp data directory, by
    replacing all relative path references and place holder paths
    with references to specific files.
    """
    surfs_dir = os.path.join(settings.hcp_dir, settings.subject,
      'MNINonLinear', 'fsaverage_LR32k')
    T1w_nii = os.path.join(settings.hcp_dir, settings.subject,
          'MNINonLinear', 'T1w.nii.gz')
    txt = template_contents.replace('SURFS_SUBJECT', settings.subject)
    txt = txt.replace('SURFS_MESHNAME', '.32k_fs_LR')
    txt = replace_path_references(txt, 'SURFSDIR', surfs_dir, scene_file)
    txt = replace_all_references(txt, 'T1W', T1w_nii, scene_file)
    txt = replace_all_references(txt, 'TOPSCALAR', vertex.rois, scene_file)
    txt = replace_all_references(txt, 'MIDSCALAR', vertex.seed_corr, scene_file)

    return txt

# What's this one needed for? Other one better?
###################
def write_header(qc_page, subject, vert_type, network):
    qc_page.write('<!DOCTYPE html>\n<HTML><TITLE> {} {}{}</TITLE>\n'.format(
            subject, vert_type, network))
    ciftify.html.write_header(qc_page)
    qc_page.write('<body>\n')
    ciftify.html.write_navbar(qc_page,
            "{} Network {} {}".format(subject, network, vert_type),
            [{ 'href': "qc_sub.html", 'label': "Return to Subject Page"}])
    qc_page.write('<h1> {} network {} {} seed correlation </h1>\n'.format(
            subject, network, vert_type))

def write_subject_page(qc_config, qc_page, scene_file, subject, qc_subdir,
        vertex, network):
    write_header(qc_page, subject, vertex.vert_type, network)
    for image in qc_config.images:
        pic_name = '{}{}_{}.png'.format(vertex.vert_type,
                network, image.name)
        ciftify.html.write_image(qc_page, 12, pic_name,
                pic_name, "")
        output_path = os.path.join(qc_subdir, pic_name)
        image.make_image(output_path, scene_file)

def write_index_body(html_page, subjects, PINTnets):
    ## writing the lists to the main index page
    html_page.write('<h1>PINT results index</h1>\n')
    html_page.write('<h2>All subjects together</h2>\n')
    html_page.write('<ul>\n  ')
    html_page.write('<li><a href="corrmats.html">Correlation Matrixes</a>'
            '</li>\n')
    for pint_dict in PINTnets:
        html_page.write('<li><a href="network_{}.html">Network {} Seed'
                ' Correlations</a></li>\n'.format(pint_dict['network'],
                pint_dict['network']))
    html_page.write('</ul>\n')
    html_page.write('<h2>Subject Pages</h2>\n')
    html_page.write('<ul>\n  ')
    for subject in subjects:
        html_page.write('<li><a href="{}/qc_sub.html">{}</a></li>\n'
                ''.format(subject, subject))
    html_page.write('</ul>\n')
    html_page.write('</body>')

def write_all_index_pages(settings, qc_config):
    '''
    Makes all the indices.
    '''
    # get the subjects list
    subjects = list(ciftify.utils.get_subj(settings.qc_dir))

    if settings.subject_filter:
        subjects = list(filter(lambda x: settings.subject_filter in x, subjects))

    index_html = os.path.join(settings.qc_dir, 'index.html')
    with open(index_html, 'w') as main_index:
        write_header_and_navbar(main_index, 'PINT results', PINTnets,
                active_link="index.html")
        write_index_body(main_index, subjects, PINTnets)

    # write the corrmat index
    write_pic_index(settings.qc_dir, subjects, '_corrmat.png',
            "theme-table-image col-sm-6", 'corrmats.html',
            "Correlation Matrixes")

    for pint_dict in PINTnets:
        write_pic_index(settings.qc_dir, subjects,
                '{}_{}.png'.format(pint_dict['network'], pint_dict['best_view']),
                "theme-table-image col-sm-12", 'network_{}.html'.format(
                pint_dict['network']), "{} Network Index".format(
                pint_dict['network']))
    return 0

### Erin's little function for running things in the shell
def docmd(cmdlist):
    "sends a command (inputed as a list) to the shell"
    global DRYRUN
    global DEBUG

    echo_cmd = True if DEBUG else False

    suppress_stdout = False
    if "math" in cmdlist[0]: suppress_stdout = True

    ciftify.utils.run(cmdlist, dryrun=DRYRUN, echo=echo_cmd,
            suppress_stdout=suppress_stdout)

def write_pic_index(qc_dir, subjects, pic_ending, col_width, index_name, title):
    '''
    Writes html file with all subjects for one pic shown together
    '''
    html_index = os.path.join(qc_dir, index_name)
    with open(html_index, 'w') as pic_page:
        write_header_and_navbar(pic_page, 'PINT_results', PINTnets, title=title,
                active_link=index_name)
        pic_page.write('<h1>{}</h1>\n'.format(title))
        for subject in subjects:
            subject_page = os.path.join(qc_dir, subject, 'qc_sub.html')
            pic_page.write('<div class="container" style="width: 100%;">')
            for vert_type in SummaryData.vertex_types:
                pic = os.path.join(qc_dir, subject, '{}{}'.format(vert_type,
                        pic_ending))
                pic_rel_path = os.path.relpath(pic, os.path.dirname(
                        pic_page.name))
                subject_rel_path = os.path.relpath(subject_page,
                        os.path.dirname(pic_page.name))
                ciftify.html.write_image(pic_page, col_width, subject_rel_path,
                        pic_rel_path, "{} {}".format(subject, vert_type))
            pic_page.write('</div>\n</br>')
        pic_page.write('</body>\n')

if __name__=='__main__':
    ret = main()
    sys.exit(ret)
