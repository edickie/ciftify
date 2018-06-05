![](imgs/ciftify_banner.jpg)

# ciftify

The tools of the Human Connectome Project (HCP) adapted for working with non-HCP datasets

*ciftify* is a set of three types of command line tools:

1. [**conversion tools**](#conversion-tools) : command line tools adapted from HCP Minimal processing pipeline to put preprocessed T1 and fMRI data into an HCP like folder structure
2. [**ciftify tools**](#ciftifytools) : Command line tools for making working with cifty format a little easier
3. [**cifti_vis tools**](#cifti_vistools) : Visualization tools, these use connectome-workbench tools to create pngs of standard views the present theme together in fRML pages.

## Check out our wiki for more details on individual tools!
https://edickie.github.io/ciftify/

## Download and Install

### Install latest release python package
First, install the python package and all of its bundled data and scripts. You
can do this with a single command with pip.

**Note** the newest release of ciftify requires python 3 (python 2 no longer supported).

To install with pip, type the following in a terminal.
```sh
pip install https://github.com/edickie/ciftify/archive/v2.0.2-beta.tar.gz
```

## Requirements (outside python)

ciftify draws upon the tools and templates of the HCP minimally processed pipelines, and therefore is dependent on them and their prereqs:
+ connectome-workbench version 1.2.3) [http://www.humanconnectome.org/software/get-connectome-workbench]
   + **Note** only the `cifti_vis*` tool currently only works with version 1.2.3. Work is underway to surpport the newest release of connectome-workbench
+ FSL [http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/]
+ FreeSurfer [https://surfer.nmr.mgh.harvard.edu/fswiki]
+ Multimodal Surface Matching (MSM), for MSMSulc surface realignment
   + Note: while an older version of this software is now packaged with FSL, the
      version required for this workflow is available for academic use from [this link](https://www.doc.ic.ac.uk/~ecr05/MSM_HOCR_v2/)

For other installation options see [this installation documentation.](https://edickie.github.io/ciftify/#/01_installation.md)


## ciftify workflows

Scripts adapted from HCP Minimal processing pipeline to put preprocessed T1 and fMRI data into an HCP like folder structure

+ **ciftify_recon_all**
  + Will convert any freeserfer output directory into an HCP (cifti space) output directory
+ **ciftify_subject_fmri**
  + Will project a nifti functional scan to a cifti .dtseries.nii in that subjects hcp analysis directory
  + The subject's hcp analysis directory is created by runnning ciftify_recon_all on that participants freesurfer output
  + will do fancy outlier removal to optimize the mapping in the process and then smooth the data in cifti space

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
+ **cifity_vol_result**
  +  Will project a nifti scan to cifti space (4D nifti -> .dtseries.nii or 3D nifti -> .dsclar.nii) with no fancy steps or smoothing
  +  intended for conversion of 3D statistical maps (or 3D regions of interest) for visualization with wb_view


## cifti_vis Tools
+ **citfi_vis_recon_all**:
  + builds visual qc pages for verification of ciftify_recon_all conversion
  + Note: these pages can also be used for qc of freesurfer's recon-all pipeline
  + (they easier to generate (i.e. no display needed) than freesurfer QAtools, and a little prettier too)
+ **cifti_vis_fmri**:
  + builds visual qc pages for verification of ciftify_subject_fmri volume to surface mapping
  + also show surface smoothed images of seed based connectivity to give an impression of preprocessed fmri data quality
+ **cifti_vis_map**:
  +  generates picture of standard views from any cifti map (combined into on .html page)
  +  One can loop over multiple files (i.e. maps from multiple subjects) and combine all outputs so that all subjects can viewed together in one index page.
  +  can also take a nifti input which is internally converted to cifti using *ciftify_vol_result*
+ **cifti_vis_RSN**:
  +  From a functional file input, Will run seed-based correlations  from 4 ROIS of interest then generate pics of standard views
  +  One can loop over multiple files (i.e. maps from multiple subjects) and combine all outputs so that all subjects can viewed together in one index page.
  +  can also take a nifti input which is internally converted to cifti using *ciftify_vol_result*

## And also in the bin there is

These two are part of a work in progress (something I need to validate first)
ciftify_PINT_vertices
cifti_vis_PINT
epi_hcpexport

## References / Citing ciftify

The workflows and template files employed in ciftify were adapted from those of the Human Connectome Project's minimal proprocessing pipeline.  As such, any work employing ciftify's conversion of visualization tools should cite:

Glasser MF, Sotiropoulos SN, Wilson JA, Coalson TS, Fischl B, Andersson JL, Xu J, Jbabdi S, Webster M, Polimeni JR, Van Essen DC, Jenkinson M, WU-Minn HCP Consortium. The minimal preprocessing pipelines for the Human Connectome Project. Neuroimage. 2013 Oct 15;80:105-24. PubMed PMID: 23668970; PubMed Central PMCID: PMC3720813.

Additionally, any work employing the parcellation files included here should cite their original sources. They are:

**Yeo 7 or (17) Network Parcellation**:
Yeo, B. T. Thomas, Fenna M. Krienen, Jorge Sepulcre, Mert R. Sabuncu, Danial Lashkari, Marisa Hollinshead, Joshua L. Roffman, et al. 2011. “The Organization of the Human Cerebral Cortex Estimated by Intrinsic Functional Connectivity.” Journal of Neurophysiology 106 (3): 1125–65.

**The freesurfer DK atlas (i.e. 'aparc' segmentation)**:
Desikan, Rahul S., Florent Ségonne, Bruce Fischl, Brian T. Quinn, Bradford C. Dickerson, Deborah Blacker, Randy L. Buckner, et al. 2006. “An Automated Labeling System for Subdividing the Human Cerebral Cortex on MRI Scans into Gyral Based Regions of Interest.” NeuroImage 31 (3): 968–80.

**The Glasser MMP1.0 Parcellation**:
Glasser, Matthew F., Timothy S. Coalson, Emma C. Robinson, Carl D. Hacker, John Harwell, Essa Yacoub, Kamil Ugurbil, et al. 2016. “A Multi-Modal Parcellation of Human Cerebral Cortex.” Nature 536 (7615): 171–78.
