# Personalized Intrinsic Network Topograpy

Personalized Instrinsic Network Topography (PINT) is a techinique for using fMRI data to find "personalized" regions of interest for sampling intrinsic connectivity presented in this paper:

Dickie EW, Ameis SH, Shahab S, Calarco N, Smith DE, Miranda D, et al. Personalized Intrinsic Network Topography Mapping and Functional Connectivity Deficits in Autism Spectrum Disorder. *Biol Psychiatry* [Internet]. 2018 Mar 17; Available from: http://www.sciencedirect.com/science/article/pii/S0006322318313040

For each participant in a dataset, the PINT algorithm shifts the locations of so-called template regions of interest (ROIs) to a nearby cortical location, or “personalized” ROI, that maximizes the correlation of the ROI with the rest of the ROIs from its network.

The "tempate" regions of interest are defined by an input text file.  The input regions
used for the Dickie (2018) paper are available for download [here](https://raw.githubusercontent.com/edickie/ciftify/master/ciftify/data/PINT/Yeo7_2011_80verts.csv)

Personalized Instrinsic Network Topography is run using the `ciftify_PINT_vertices` function.

# ciftify_PINT_vertices

```
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

```

### ciftify_PINT_vertices example

#### Note before running PINT, you first need preprossed fMRI data in cifti format that has been mapped to the `LR_32k` surface. For more on doing that, check out the rest of the ciftify package.

For the example, we will continue from the outputs generated [in this example tutorial](tutorials/example-usage.md).

*Note: we will take the clean functional file*

ciftify_PINT_vertices is run for sub-50004 like follows.

**Note:** we will take the "cleanned" functional rest file as our input
**Note:** for simplicity (but recommended), we placed the `Yeo7_2011_80verts.csv` file, [downloaded from here](https://raw.githubusercontent.com/edickie/ciftify/master/ciftify/data/PINT/Yeo7_2011_80verts.csv). Inside the our output directory  - `PINT_out`.  

```sh
export CIFTIFY_WORKDIR=/path/to/derviatives/ciftify

# note I like to output the files into a separate directory for each input
mkdir PINT_out/sub-50004

ciftify_PINT_vertices --pcorr \
        ${CIFTIFY_WORKDIR}/sub-50004/MNINonLinear/clean.dtseries.nii \
        ${CIFTIFY_WORKDIR}/sub-50004/MNINonLinear/fsaverage_LR32k/sub-50004.L.midthickness.32k_fs_LR.surf.gii \
        ${CIFTIFY_WORKDIR}/sub-50004/MNINonLinear/fsaverage_LR32k/sub-50004.R.midthickness.32k_fs_LR.surf.gii \
        /PINT_out/Yeo7_2011_80verts.csv \
        /PINT_out/sub-50004/sub-50004_task-rest

```

After PINT runs, we should see four output files in `/PINT_out/sub-50004`

```

  /PINT_out/sub-50004/
  ├── sub-50004_task-rest_pint.log
  ├── sub-50004_task-rest_summary.csv
  ├── sub-50004_task-rest_tvertex_meants.csv
  └── sub-50004_task-rest_pvertex_meants.csv

```


|  output file          |  description 	|
|---	                  |---	|
| `_pint.log`  	        |  log file containing the settings and number of iterations 	|
| `_summary.csv`        |  summary file of vertices, the `pvertex` column contains the new "personalized" vertex locations 	|
| `_tvertex_meants.csv` |  The fMRI timecourses extracted from the "template" (i.e. before) PINT ROIs 	|
| `_pvertex_meants.csv` |  The fMRI timecourses extracted from the "personalized" (i.e. after) PINT ROIs 	|

After running PINT. We strongly recommend that you generate QC visualizations using `cifti_vis_PINT`

## cifti_vis_PINT

```
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
  --subjects-filter STR    A string that can be used to filter out subject
                           directories
  --roi-radius MM          Specify the radius [default: 6] of the plotted rois
                           (in mm)
  --pvertex-col COLNAME    The column [default: pvertex] to read the personlized vertices
  --hcp-data-dir PATH      DEPRECATED, use --ciftify-work-dir instead
  -v,--verbose             Verbose logging
  --debug                  Debug logging in Erin's very verbose style
  -n,--dry-run             Dry run
  --help                   Print help

```

### cifti_vis_PINT example

Using the outputs we set above

```sh
export CIFTIFY_WORKDIR=/path/to/derviatives/ciftify

# cifti_vis_PINT subject <func.dtseries.nii> <subject> <PINT_summary.csv>
cifti_vis_PINT subject \
  ${CIFTIFY_WORKDIR}/sub-50004/MNINonLinear/clean.dtseries.nii \
  sub-50004 \
  PINT_out/sub-50004/sub-50004_task-rest_summary.csv
```

This will create a QC visualizations inside `${CIFTIFY_WORKDIR}/qc_PINT` folder. Note, you can change the output directory for the qc visualizations using teh `--qcdir /path/to/qcdir` option.

Lastly, when all "subject" level qc pages have been created. `cifti_vis_PINT` should be called in `index` mode to create top level index html pages.

```
export CIFTIFY_WORKDIR=/path/to/derviatives/ciftify

# create the index pages
cifti_vis_PINT index

# view the QA page index
cd ${CIFTIFY_WORKDIR}/qc_PINT
firefox index.html
```


# Other operations after PINT

### Concatenating the summary files into one csv for stats

It's helpful for statistics to combine all the data all scans' `_summary.csv` files into one larger csv.
Moreover, this utility also recalcuates the distance between the "tvertex" and "pvertex" vertices on a standard surface from the HCP S1200 release. This output - the `std_distance` column in the concatenated file - was the "distance" metric where effects of age and ASD diagnosis were observed in Dickie et al (2018).

## ciftify_postPINT1_concat

```
Usage:
  ciftify_postPINT1_concat [options] <concatenated-pint> <PINT_summary.csv>...

Arguments:
    <concatenated-pint>    The concatenated PINT output to write
    <PINT_summary.csv>     The PINT summary files (repeatable)

Options:
  --surfL SURFACE            The left surface on to measure distances on (see details)
  --surfR SURFACE            The right surface to to measure distances on (see details)
  --no-distance-calc         Will not calculate the distance from the template vertex
  --pvertex-col COLNAME      The column [default: pvertex] to read the personlized vertices
  --debug                    Debug logging in Erin's very verbose style
  -n,--dry-run               Dry run
  --help                     Print help

```

### ciftify_postPINT1_concat example

```
cd PINT_out

# ciftify_postPINT1_concat [options] <concatenated-pint> <PINT_summary.csv>...
ciftify_postPINT1_concat all_PINT_summaries_concat.csv sub*/*_summary.csv

```

Note - again - the `std_distance` column in the `all_PINT_summaries_concat.csv` would be the recommended column for final analyses. It was the "distance" metric where effects of age and ASD diagnosis were observed in Dickie et al (2018).

## ciftify_postPINT2_sub2sub

This utility measures the distance between personalized vertices across subjects. It was important for the test-retest calculation reported in the Dickie et al 2018 paper.  

## Usage

```
  ciftify_postPINT2_sub2sub [options] <concatenated-pint> <output_sub2sub.csv>

Arguments:
    <concatenated-pint>    The concatenated PINT outputs (csv file)
    <output_sub2sub.csv>   The outputfile name

Options:
  --surfL SURFACE        The left surface on to measure distances on (see details)
  --surfR SURFACE        The right surface to to measure distances on (see details)
  --roiidx INT           Measure distances for only this roi (default will loop over all ROIs)
  --pvertex-col COLNAME  The column [default: pvertex] to read the personlized vertices
  --debug                Debug logging in Erin's very verbose style
  -n,--dry-run           Dry run
  --help                 Print help


```
[ciftify_postPINT2_sub2sub usage](usage/ciftify_postPINT2_sub2sub.md)

## ciftify reference

If using reporting on PINT, please cite:

Dickie EW, Ameis SH, Shahab S, Calarco N, Smith DE, Miranda D, et al. Personalized Intrinsic Network Topography Mapping and Functional Connectivity Deficits in Autism Spectrum Disorder. *Biol Psychiatry* [Internet]. 2018 Mar 17; Available from: http://www.sciencedirect.com/science/article/pii/S0006322318313040
