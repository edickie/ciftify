# cifti_vis_recon_all

Makes pictures of standard views from ciftify_recon_all outputs and pastes them
together into a html page for quality assurance.

## Usage 
```
    cifti_vis_recon_all snaps [options] <subject>
    cifti_vis_recon_all index [options]

Arguments:
  <subject>                The subject to make snaps for.

Options:
  --qcdir PATH             Full path to location of QC directory
  --hcp-data-dir PATH      The directory for HCP subjects (overrides HCP_DATA
                           enviroment variable)
  --debug                  Debug logging in Erin's very verbose style
  --verbose                More log messages, less than debug though
  --help                   Print help


```
## DETAILS 
Produces picture of surface outlines on slices as well as the recontruced surfaces.
Other views include the freesurfer automatic segmentation.

Two "spaces" are visualized ("native" and "MNI"). "Native" space are the "raw"
converted freesurfer outputs. The MNI transformed brains and fsaverage_LR surfaces
(32k meshes) is the "space" where fMRI analysis is done

Requires connectome workbench (i.e. wb_command and imagemagick)

Written by Erin W Dickie
