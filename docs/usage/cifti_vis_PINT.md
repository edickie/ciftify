# cifti_vis_PINT

Makes temporary seed corr maps using a chosen roi for each network and
correlation maps

## Usage
```
    cifti_vis_PINT snaps [options] <func.dtseries.nii> <subject> <PINT_summary.csv>
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


```
## DETAILS
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
