# ciftify_subject_fmri

Projects a fMRI timeseries to and HCP dtseries file and does smoothing

## Usage
```
  ciftify_subject_fmri [options] <func.nii.gz> <subject> <task_label>

Arguments:
    <func.nii.gz>           Nifty 4D volume to project to cifti space
    <subject>               The Subject ID in the HCP data folder
    <task_label>            The outputname for the cifti result folder

Options:
  --SmoothingFWHM MM          The Full-Width-at-Half-Max for smoothing steps
  --ciftify-work-dir PATH     The ciftify working directory (overrides
                              CIFTIFY_WORKDIR enivironment variable)

  --surf-reg REGNAME          Registration sphere prefix [default: MSMSulc]
  --T1w-anat <T1w.nii.gz>     The path to the T1w anatomical this func is registered to
                              (will do a linear re-registration of this anat to the T1w in ciftify)
  --FLIRT-to-T1w              Will register to T1w space (not recommended, see DETAILS )
  --func-ref ref              Type/or path of image to use [default: first_vol]
                              as reference for when realigning or resampling images. DETAILS.
  --already-in-MNI            Functional volume has already been registered to MNI
                              space using the same transform in as the ciftified anatomical data
  --OutputSurfDiagnostics     Output some extra files for QCing the surface
                              mapping.
  --ciftify-conf YAML         Path to a yaml file that would override template
                              space defaults Only recommended for expert users.
  --DilateBelowPct PCT        Add a step to dilate places where signal intensity
                              is below this percentage. (DEPRECATED)
  --hcp-data-dir PATH         DEPRECATED, use --ciftify-work-dir instead
  --n_cpus INT                Number of cpu's available. Defaults to the value
                              of the OMP_NUM_THREADS environment variable
  -v,--verbose                Verbose logging
  --debug                     Debug logging in Erin's very verbose style
  -n,--dry-run                Dry run
  -h,--help                   Print help


```
## DETAILS

The default surface registration is now FS (freesurfer), althought MSMSulc is highly recommended.
If MSMSulc registration has been done specifiy this with "--surf-reg MSMSulc".

The default behaviour assumes that the functional data has already been distortion
corrected and realigned to the T1w anatomical image.  If this is not the case, the
"--FLIRT-to-T1w" flag can be used to run a simple linear tranform (using FSL's FLIRT)
between the functional and the anatomical data. Note, that is linear transform is
not ideal as it is other packages (i.e. fmriprep) do offer much better registation results.

The "--func-ref" flag allows the user to specify how a reference image for the
functional data should be calcualted (by using the "first_vol" or "median" options)
or to provide the path to an additional file to use as a registation intermediate.
Acceptable options are "first_vol" (to use the first volume), "median"
to use the median. The default is to use the first volume.

To skip the transform to MNI space, and resampling to 2x2x2mm (if this has been
done already), use the --already-in-MNI option.

Adapted from the fMRISurface module of the Human Connectome
Project's minimal proprocessing pipeline. Please cite:

Glasser MF, Sotiropoulos SN, Wilson JA, Coalson TS, Fischl B, Andersson JL, Xu J,
Jbabdi S, Webster M, Polimeni JR, Van Essen DC, Jenkinson M, WU-Minn HCP Consortium.
The minimal preprocessing pipelines for the Human Connectome Project. Neuroimage. 2013 Oct 15;80:105-24.
PubMed PMID: 23668970; PubMed Central PMCID: PMC3720813.

Written by Erin W Dickie, Jan 12, 2017
