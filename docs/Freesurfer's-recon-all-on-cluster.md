The following is a script for using qbatch to run freesurfer's recon-all on a the scinet cluster in toronto

It uses two lovely bits of software to run scripts in parallel:

1. GNU-parallel (runs parallel inside the cluster):[https://www.gnu.org/software/parallel/parallel_tutorial.html]
2. qbatch (for writing chunked array jobs): [https://github.com/pipitone/qbatch]


```sh
#!/bin/bash

## set the site variable here
projectname='myproject'
NIIDIR=${SCRATCH}/myproject/inputs/

#load the ciftify enviroment
module load gnu-parallel/20140622
module load /home/a/arisvoin/edickie/quarantine/modules/edickie_quarantine
module load freesurfer/5.3.0
module load python ## you need any version of python loaded for qbatch to work
module load qbatch
export SUBJECTS_DIR=${SCRATCH}/myproject/FSout/

## make the $SUBJECTS_DIR if it does not already exist
mkdir -p $SUBJECTS_DIR

## get the session 1 subjects list from the NIIDIR
Session1Files=`cd ${NIIDIR}; ls -1d 002????/session_1/anat_1/anat.nii.gz`
Session1Subjects=""
for file in ${Session1Files}; 
do 
  sub=$(dirname $(dirname $(dirname ${file}))) 
  Session1Subjects="${Session1Subjects} ${sub}" 
done

## submit the files to the queue
cd $SUBJECTS_DIR
parallel "echo recon-all -subject {} -i ${NIIDIR}/{}/session_1/anat_1/anat.nii.gz -sd ${SUBJECTS_DIR} -all" ::: ${Session1Subjects} | \
  qbatch --walltime 24:00:00 -c 4 -j 4 --ppj 8 -N fss1${projectname} -
```