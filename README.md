# ciftify

The tools of the Human Connectome Project (HCP) adapted for working with non-HCP datasets

*ciftify* is a set of three types of command line tools:

1. [**conversion tools**](#conversiontools) : bash scripts adapted from HCP Minimal processing pipeline to put preprocessed T1 and fMRI data into an HCP like folder structure
2. [**ciftify tools**](#ciftifytools) : Command line tools for making working with cifty format a little easier
3. [**cifti_vis tools**](#cifti_vistools) : Visualization tools, these use connectome-workbench tools to create pngs of standard views the present theme together in fRML pages.

## Download and Install

Right now I haven't gotten around to figuring out a nicer install, so the easiest is to just clone the repo and set some enviroment variables:
+ add the `ciftify/bin` to your `PATH`
+ add the `ciftify` directory to your `PYTHONPATH`
+ create a new environment variable (`HCP_SCENE_TEMPLATES`) that point to the location of the template scene files
+ create an environment variable for the location of your `HCP_DATA`

```sh
git clone https://github.com/edickie/ciftify.git
export PATH=$PATH:<ciftify/bin>
export PYTHONPATH=$PYTHONPATH:<ciftify>
export HCP_DATA=/path/to/hcp/subjects/data/
export HCP_SCENE_TEMPLATES=<ciftify/data/scene_templates>
```
## Requirements

ciftify draws upon the tools and templates of the HCP minimally processed pipelines and therefore is dependant on them and there prereqs:
+ HCP Minimal Processing Pipeline (any release) [https://github.com/Washington-University/Pipelines/releases]
+ connectome-workbench (tested with version 1.1.1) [http://www.humanconnectome.org/software/get-connectome-workbench]
+ FSL [http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/]
+ freesurfer [https://surfer.nmr.mgh.harvard.edu/fswiki]
+ ImageMagick (for cifti-vis image manipultion)

ciftify is mostly written in python 2 with the following package dependancies:
+ numpy
+ nibabel
+ docopt
+ pandas
+ seaborn (only for PINT vis)

## Conversion Tools

Scripts adapted from HCP Minimal processing pipeline to put preprocessed T1 and fMRI data into an HCP like folder structure

+ **fs2hcp**
  + Will convert any freeserfer output directory into an HCP (cifti space) output directory
+ **func2hcp**
  + Will project a nifti functional scan to a cifti .dtseries.nii in that subjects hcp analysis directory
  + The subject's hcp analysis directory is created by runnning fs2hcp on that participants freesurfer output
  + will do fancy outlier removal to optimize the mapping in the process and then smooth the data in cifti space
+ **cifity_a_nifti**
  +  Will project a nifti scan to cifti space (4D nifti -> .dtseries.nii or 3D nifti -> .dsclar.nii) with no fancy steps or smoothing
  +  intended for conversion of 3D statistical maps (or 3D regions of interest) for visualization with wb_view

## ciftify Tools

+ **ciftify_meants**:
  + extracts mean timeseries(es) (similar to FSL' fslmeants) that can take nifti, cifti or gifti inputs
+ **ciftify_seed_corr**:
  + builds seed-based correlation maps using cifti, gifti or nifti inputs  
+ **ciftify_peaktable**:
  + similar to FSL's clusterize, outputs a csv table of peak locations from a cifti statisical map
+ **ciftify_surface_rois**:
  + a tool for building circular rois on the cortical surface. Multiple roi locations can be read at once from a csv table.
+ **ciftify_groupmask**:
  + a tools for building a group mask for statiscal analyses using multiple .dtseries.nii files as the input

## cifti_vis Tools
+ **citfi_vis_qc**:
  + builds visual qc pages for verification of fs2hcp and func2hcp conversion
  + Note: these pages can also be used for qc of freesurfer's recon-all pipeline
  + (they easier to generate (i.e. no display needed) than freesurfer QAtools, and a little prettier too)
+ **cifti_vis_map**:
  +  generates picture of standard views from any cifti map (combined into on .html page)
  +  One can loop over multiple files (i.e. maps from multiple subjects) and combine all outputs so that all subjects can viewed together in one index page.
  +  can also take a nifti input which is internally converted to cifti using *ciftify_a_nifti*
+ **cifti_vis_RSN**:
  +  From a functional file input, Will run seed-based correlations  from 4 ROIS of interest then generate pics of standard views
  +  One can loop over multiple files (i.e. maps from multiple subjects) and combine all outputs so that all subjects can viewed together in one index page.
  +  can also take a nifti input which is internally converted to cifti using *ciftify_a_nifti*

## And also in the bin there is

These two are part of a work in progress (something I need to validate first)
ciftify_PINT_vertices
cifti_vis_PINT
epi_hcpexport
