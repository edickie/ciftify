# ciftify_subject_fmri

Projects a fMRI timeseries to and HCP dtseries file and does smoothing

## Usage
```
  ciftify_subject_fmri [options] <func.nii.gz> <Subject> <NameOffMRI>

Arguments:
    <func.nii.gz>           Nifty 4D volume to project to cifti space
    <Subject>               The Subject ID in the HCP data folder
    <NameOffMRI>            The outputname for the cifti result folder

Options:
  --SmoothingFWHM MM          The Full-Width-at-Half-Max for smoothing steps
  --ciftify-work-dir PATH     The directory for HCP subjects (overrides
                              CIFTIFY_WORKDIR/ HCP_DATA enivironment variables)
  --hcp-data-dir PATH         The directory for HCP subjects (overrides
                              CIFTIFY_WORKDIR/ HCP_DATA enivironment variables) DEPRECATED
  --already-in-MNI            Functional volume has already been registered to MNI
                              space using the same transform in as the hcp anatoical data
  --FLIRT-template NII        Optional 3D image (generated from the func.nii.gz)
                              to use calculating the FLIRT registration
  --FLIRT-dof DOF             Degrees of freedom [default: 12] for FLIRT
                              registration (Not used with --already-in-MNI)
  --FLIRT-cost COST           Cost function [default: corratio] for FLIRT
                              registration (Not used with '--already-in-MNI')
  --OutputSurfDiagnostics     Output some extra files for QCing the surface
                              mapping.
  --DilateBelowPct PCT        Add a step to dilate places where signal intensity
                              is below this percentage.
  --Dilate-MM MM              Distance in mm [default: 10] to dilate when
                              filling holes
  -v,--verbose                Verbose logging
  --debug                     Debug logging in Erin's very verbose style
  -n,--dry-run                Dry run
  -h,--help                   Print help


```
## DETAILS

FSL's flirt is used to register the native fMRI ('--FLIRT-template')
to the native T1w image. This is concatenated to the non-linear transform to
MNIspace in the xfms folder. Options for FSL's flirt can be changed using the
"--FLIRT-dof" and "--FLIRT-cost". If a "--FLIRT-template" image is not given,
it will be calcuated using as the temporal mean of the func.nii.gz input image.

To skip the transform to MNI space, and resampling to 2x2x2mm (if this has been
done already), use the --already-in-MNI option.

Adapted from the fMRISurface module of the Human Connectome
Project's minimal proprocessing pipeline. Please cite:

Glasser MF, Sotiropoulos SN, Wilson JA, Coalson TS, Fischl B, Andersson JL, Xu J,
Jbabdi S, Webster M, Polimeni JR, Van Essen DC, Jenkinson M, WU-Minn HCP Consortium.
The minimal preprocessing pipelines for the Human Connectome Project. Neuroimage. 2013 Oct 15;80:105-24.
PubMed PMID: 23668970; PubMed Central PMCID: PMC3720813.

Written by Erin W Dickie, Jan 12, 2017
