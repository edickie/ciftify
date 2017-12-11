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
