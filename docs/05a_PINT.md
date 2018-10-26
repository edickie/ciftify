# Personlazied Intrinsic Network Topograpy

Personalized Instrinsic Network Topography (PINT) is a techinique for using fMRI data to find "personalized" regions of interest for sampling intrinsic connectivity presented in this paper:

Dickie EW, Ameis SH, Shahab S, Calarco N, Smith DE, Miranda D, et al. Personalized Intrinsic Network Topography Mapping and Functional Connectivity Deficits in Autism Spectrum Disorder. *Biol Psychiatry* [Internet]. 2018 Mar 17; Available from: http://www.sciencedirect.com/science/article/pii/S0006322318313040

For each participant in a dataset, the PINT algorithm shifts the locations of so-called template regions of interest (ROIs) to a nearby cortical location, or “personalized” ROI, that maximizes the correlation of the ROI with the rest of the ROIs from its network.

The "tempate" regions of interest are defined by an input text file.  The input regions
used for the Dickie (2018) paper are available for download [here](https://raw.githubusercontent.com/edickie/ciftify/master/ciftify/data/PINT/Yeo7_2011_80verts.csv)

Personalized Instrinsic Network Topography is run using the `ciftify_PINT_vertices` function.

[ciftify_PINT_vertices usage](../usage/ciftify_PINT_vertices ':include')

# ciftify_PINT_vertices example:

#### Note before running PINT, you first need preprossed fMRI data in cifti format that has been mapped to the `LR_32k` surface. For more on doing that, check out the rest of the ciftify package.

For the example, we will continue from the outputs generated [in this example tutorial](tutorials/example-usage.md).

*Note: we will take the clean functional file*

ciftify_PINT_vertices is run for sub-50004 like follows.

**Note:** we will take the "cleanned" functional rest file as our input
**Note:** for simplicity (but recommended), we placed the `Yeo7_2011_80verts.csv` file, [downloaded from here](https://raw.githubusercontent.com/edickie/ciftify/master/ciftify/data/PINT/Yeo7_2011_80verts.csv). Inside the our output directory  - `PINT_out`.  

```
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

[cifti_vis_PINT usage](../usage/cifti_vis_PINT ':include')

## cifti_vis_PINT example

Using the outputs we set above

```
export CIFTIFY_WORKDIR=/path/to/derviatives/ciftify

# cifti_vis_PINT subject <func.dtseries.nii> <subject> <PINT_summary.csv>
cifti_vis_PINT subject \
  ${CIFTIFY_WORKDIR}/sub-50004/MNINonLinear/clean.dtseries.nii \
  sub-50004 \
  PINT_out/sub-50004/sub-50004_task-rest_summary.csv
```

This will create a QC visualizations inside ${CIFTIFY_WORKDIR}/qc_PINT folder. Note, you can change the output directory for the qc visualizations using teh `--qcdir /path/to/qcdir` option.

Lastly, when all "subject" level qc pages have been created. `cifti_vis_PINT` should be called in `index` mode to create top level index html pages.

```
export CIFTIFY_WORKDIR=/path/to/derviatives/ciftify

# create the index pages
cifti_vis_PINT index

# view the QA page index
cd ${CIFTIFY_WORKDIR}/qc_PINT
firefox index.html
```


## Other operations after PINT

### Concatenating the summary files into one csv for stats

It's helpful for statistics to combine all the data all scans' `_summary.csv` files into one larger csv.
Moreover, this utility also recalcuates the distance between the "tvertex" and "pvertex" vertices on a standard surface from the HCP S1200 release. This output - the `std_distance` column in the concatenated file - was the "distance" metric where effects of age and ASD diagnosis were observed in Dickie et al (2018).

[ciftify_postPINT1_concat usage](../usage/ciftify_postPINT1_concat ':include')

### ciftify_postPINT1_concat example

```
cd PINT_out

# ciftify_postPINT1_concat [options] <concatenated-pint> <PINT_summary.csv>...
ciftify_postPINT1_concat all_PINT_summaries_concat.csv sub*/*_summary.csv

```

Note - again - the `std_distance` column in the `all_PINT_summaries_concat.csv` would be the recommended column for final analyses. It was the "distance" metric where effects of age and ASD diagnosis were observed in Dickie et al (2018).

### ciftify_postPINT2_sub2sub

This utility measures the distance between personalized vertices across subjects. It was important for the test-retest calculation reported in the Dickie et al 2018 paper.  

[ciftify_postPINT2_sub2sub usage](../usage/ciftify_postPINT2_sub2sub ':include')

# ciftify reference

If using reporting on PINT, please cite:

Dickie EW, Ameis SH, Shahab S, Calarco N, Smith DE, Miranda D, et al. Personalized Intrinsic Network Topography Mapping and Functional Connectivity Deficits in Autism Spectrum Disorder. *Biol Psychiatry* [Internet]. 2018 Mar 17; Available from: http://www.sciencedirect.com/science/article/pii/S0006322318313040
