# ciftify usage example


The following example uses data from the Consortium for Neuropsychiatric Phenomics (CNP) dataset described in (Poldrack et al. 2016). This data was obtained from the OpenfMRI database. Its accession number is ds000030. In this example we, work from the proprocessed data release v1.0.4. The release includes both structural outputs preprocessed with freesurfer (version 6.0.0, (Fischl 2012)) and resting state fMRI data preprocessed with the fmriprep pipeline (see (Gorgolewski et al. 2017)).

## Step one download the data

We will download and unzip the freesurfer and fmriprep outputs from subjects 50004-50008
```sh
cd /local/source/dir ## change this to the location of the files on your system
## the fmriprep outputs
wget https://s3.amazonaws.com/openneuro/ds000030/ds000030_R1.0.4/compressed/ds000030_R1.0.4_derivatives_sub50004-50008.zip
unzip ds000030_R1.0.4_derivatives_sub50004-50008.zip
wget https://s3.amazonaws.com/openneuro/ds000030/ds000030_R1.0.4/compressed/ds000030_R1.0.4_derivatives_freesurfer_sub50004-50008.zip
unzip ds000030_R1.0.4_derivatives_freesurfer_sub50004-50008.zip
```

This outputs are organized into BIDS data structure for "deritives" calculated in this manner.
Speciftically, all outputs are nested within subfolders "freesurfer" (for freesurfer)
and "fmriprep" (for fmri), which are sitting within ds000030_R1.0.4/derivatives.
Within the freesurfer subfolder are the full freesurfer recon-all data structure where subject id is the
top level and folders (label, mri, etc) sit below that.
The fmriprep derivatives also are organized into a subfolder for each participant.
Within these folders sit anatomical ("anat") and functional ("func") derivatives.
For ciftify, we require the preprocessed fmri data in T1w ("native") space.
In this example, we will select the resting state run. For participant sub-50005,
this file is named "sub-50005_task-rest_bold_space-T1w_preproc.nii.gz"

```
ds000030_R1.0.4
└── derivatives
    ├── fmriprep
    │   ├── sub-50005
    |   │   ├── anat
    │   │   └── func
    |   |       ├── sub-50004_task-rest_bold_space-T1w_preproc.nii.gz
    |   |       └── ...   
    │   ├── sub-50006...
    │   └── sub-...
    └── freesurfer
        ├── sub-50005
        │   ├── label
        │   ├── mri
        │   ├── scripts
        │   ├── stats
        │   ├── surf
        │   ├── tmp
        │   ├── touch
        │   └── trash
        ├── sub-50006...
        └── sub-...

```

## loading the ciftify package
```sh
module load Freesurfer/6.0.0
module load FSL
module load GNU_PARALLEL/20170122
module load connectome-workbench/1.2.3
module load python/3.6_ciftify_01
```
## running ciftify_recon_all for participant sub-50004

```sh
ciftify_recon_all --hcp-data-dir /local_dir/ciftify --fs-subjects-dir /local_dir/ds000030_R1.0.4/derivatives/freesurfer sub-50005
```

## building qc snaps after recon-all

```sh
cifti_vis_recon_all snaps --hcp-data-dir /local_dir/ciftify sub-50005
cifti_vis_recon_all index --hcp-data-dir /local_dir/ciftify
```

## running ciftify_subject_fmri

```sh
ciftify_subject_fmri --hcp-data-dir /local_dir/ciftify /local_dir/ds000030_R1.0.4/derivatives/fmriprep/sub-50005/func/sub-50005_task-rest_bold_space-native_preproc.nii.gz sub-50005 rest
```

## building qc snaps from fmri

```sh
cifti_vis_fmri snaps --hcp-data-dir /local_dir/ciftify rest sub-50005
cifti_vis_fmri index --hcp-data-dir /local_dir/ciftify
```

## using qbatch to run everybody


```sh
export HCP_DATA=/local_dir/ciftify
export SUBJECTS_DIR=/local_dir/ds000030_R1.0.4/derivatives/freesurfer
SUBJECTS=`cd $SUBJECTS_DIR; ls -1d sub*`
mkdir ${HCP_DATA}
cd ${HCP_DATA}
parallel "echo ciftify_recon_all {}" ::: $SUBJECTS |
  qbatch --walltime '01:30:00' --ppj 6 -c 3 -j 3 -N ciftify1 -
```

## running all the ciftify_subject_fmri runs.

```sh
export HCP_DATA=/local_dir/ciftify
src_data=/local_dir/ds000030_R1.0.4/derivatives/fmriprep
qstat
mkdir ${HCP_DATA}
cd ${HCP_DATA}
SUBJECTS=`ls -1d sub*`
parallel "echo ciftify_subject_fmri ${src_data}/{}/func/{}_task-rest_bold_space-T1w_preproc.nii.gz {} rest" ::: $SUBJECTS |
  qbatch --walltime '01:30:00' --ppj 6 -c 3 -j 3 -N ciftify2 -
```
## running all the recon-all qc as a loop...

```sh
export HCP_DATA=/local_dir/ciftify
cd ${HCP_DATA}
SUBJECTS=`ls -1d sub*`
for subject in $SUBJECTS; 
do 
  cifti_vis_recon_all snaps ${subject} 
done
cifti_vis_recon_all index
```

## Example outputs

A zip file of the expected outputs for sub-50005 as well as QA images for sub-50004-sub-50008 can be downloaded from [here](https://drive.google.com/open?id=0B7RQvc5-M37_dVFNd09zTkhBTzA).
