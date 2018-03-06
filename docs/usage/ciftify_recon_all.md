# ciftify_recon_all

Converts a freesurfer recon-all output to a working directory

## Usage
```
  ciftify_recon_all [options] <Subject>

Arguments:
    <Subject>               The Subject ID in the HCP data folder

Options:
  --ciftify-work-dir PATH     The directory for HCP subjects (overrides
                              CIFTIFY_WORKDIR/ HCP_DATA enivironment variables)
  --hcp-data-dir PATH         The directory for HCP subjects (overrides
                              CIFTIFY_WORKDIR/ HCP_DATA enivironment variables) DEPRECATED
  --fs-subjects-dir PATH      Path to the freesurfer SUBJECTS_DIR directory
                              (overides the SUBJECTS_DIR environment variable)
  --resample-to-T1w32k        Resample the Meshes to 32k Native (T1w) Space
  --MSMSulc                   Run MSMSulc surface registration (instead of using FS)
  --MSM-config PATH           The path to the configuration file to use for
                              MSMSulc mode. By default, the configuration file
                              is ciftify/data/hcp_config/MSMSulcStrainFinalconf
                              This setting is ignored when not running MSMSulc mode.
  --T2                        Include T2 files from freesurfer outputs
  --settings-yaml PATH        Path to a yaml configuration file. Overrides
                              the default settings in
                              ciftify/data/cifti_recon_settings.yaml
  -v,--verbose                Verbose logging
  --debug                     Debug logging in Erin's very verbose style
  -n,--dry-run                Dry run
  -h,--help                   Print help


```
## DETAILS
Adapted from the PostFreeSurferPipeline module of the Human Connectome
Project's minimal proprocessing pipeline. Please cite:

Glasser MF, Sotiropoulos SN, Wilson JA, Coalson TS, Fischl B, Andersson JL, Xu J,
Jbabdi S, Webster M, Polimeni JR, Van Essen DC, Jenkinson M, WU-Minn HCP Consortium.
The minimal preprocessing pipelines for the Human Connectome Project. Neuroimage. 2013 Oct 15;80:105-24.
PubMed PMID: 23668970; PubMed Central PMCID: PMC3720813.

The default outputs are condensed to include in 4 mesh "spaces" in the following directories:
  + T1w/Native: The freesurfer "native" output meshes
  + MNINonLinear/Native: The T1w/Native mesh warped to MNINonLinear
  + MNINonLinear/fsaverage_LR32k
     + the surface registered space used for fMRI and multi-modal analysis
     + This 32k mesh has approx 2mm vertex spacing
  + MNINonLinear_164k_fs_LR (in the MNINonLinear folder):
     + the surface registered space used for HCP's anatomical analysis
     + This 164k mesh has approx 0.9mm vertex spacing

In addition, the optional flag '--resample-to-T1w32k' can be used to output an
additional T1w/fsaverage_LR32k folder that occur in the HCP Consortium Projects.

Note: --MSMSulc and --MSM-config options are still experimental. While the --T2
option does allow you to extract T2 weighted outputs that were submitted to recon_all.
If T2 weighted data is available, we strongly recommend using the HCP pipelines
rather than this command..

Written by Erin W Dickie
