# cifti_vis_map

Creates pngs of standard surface and subcortical views from a nifti or cifti
input map.

## Usage
```
    cifti_vis_map cifti-snaps [options] <map.dscalar.nii> <subject> <map-name>
    cifti_vis_map nifti-snaps [options] <map.nii> <subject> <map-name>
    cifti_vis_map index [options]

Arguments:
    <map.dscalar.nii>        A 2D cifti dscalar file to view
    <map.nii>                A 3D nifti file to view to view
    <subject>                Subject ID for HCP surfaces
    <map-name>               Name of dscalar map as it will appear in qc page
                             filenames

Options:
  --qcdir PATH             Full path to location of QC directory.
  --ciftify-work-dir PATH  The directory for HCP subjects (overrides
                           CIFTIFY_WORKDIR/ HCP_DATA enivironment variables)
  --hcp-data-dir PATH      The directory for HCP subjects (overrides
                           CIFTIFY_WORKDIR/ HCP_DATA enivironment variables) DEPRECATED
  --subjects-filter STR    A string that can be used to filter out subject
                           directories when creating index
  --colour-palette STR     Specify the colour palette for the seed correlation
                           maps
  --resample-nifti         The nifti file needs to be resampled to the voxel
                           space of the hcp subject first
  --v,--verbose            Verbose logging
  --debug                  Debug logging
  --help                   Print help


```
## DETAILS
This makes pretty pictures of your hcp views using connectome workbenches
"show scene" commands. It pastes the pretty pictures together into some .html
QC pages. Requires connectome workbench (i.e. wb_command and imagemagick)

By default, all folder in the qc directory will be included in the index.

You can change the color palette for all pics using the --colour-palette flag.
The default colour palette is videen_style. Some people like 'PSYCH-NO-NONE'
better. For more info on palettes see wb_command help.

Written by Erin W Dickie
