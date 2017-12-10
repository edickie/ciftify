# cifti_vis_RSN

Makes temporary seed correlation maps using 3 rois of interest
then makes pretty picture of these maps.

## Usage 
```
    cifti_vis_RSN cifti-snaps [options] <func.dtseries.nii> <subject>
    cifti_vis_RSN nifti-snaps [options] <func.nii.gz> <subject>
    cifti_vis_RSN index [options]

Arguments:
    <func.dtseries.nii>  A 3D cifti dtseries file to view RSN maps from
    <func.nii.gz>        A 4D nifti file to view RSN maps from
    <subject>            Subject ID for HCP surfaces

Options:
  --qcdir PATH             Full path to location of QC directory
  --hcp-data-dir PATH      The directory for HCP subjects (overrides HCP_DATA enviroment variable)
  --subjects-filter STR    A string that can be used to filter out subject directories for index
  --subjects-list TXT      Input a text file of subject ids to include in index
  --colour-palette STR     Specify the colour palette for the seed correlation maps
  -v,--verbose             Verbose logging
  --debug                  Debug logging in Erin's very verbose style
  --help                   Print help


```
## DETAILS 
This makes pretty pictures of your hcp views using connectome workbenches "show scene" commands
It pastes the pretty pictures together into some .html QC pages

By default, all subjects in the qc directory will be included in the index.
The --subject-list argument to specify a text file containing the subject list.

You can changed the color palette for all pics using the --colour-palette flag.
The default colour palette is videen_style. Some people like 'PSYCH-NO-NONE' better.
For more info on palettes see wb_command help.

Requires connectome workbench (i.e. wb_command and imagemagick)

Written by Erin W Dickie, Feb 2016
