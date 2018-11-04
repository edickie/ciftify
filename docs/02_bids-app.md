# Running the fmriprep_ciftify BIDS-App

![ciftify_workflow](_img/CIFTIFY_fig1_2018-05-04.png)

[bids-app usage](usage/ciftify_recon_all.md ':include')
```sh
docker run -ti --rm \
    -v $HOME/fullds005:/data:ro \
    -v $HOME/dockerout:/out \
    tigrlab/fmriprep_ciftify:latest \
    /data /out/out \
    participant \
    --ignore fieldmaps
```

If the data to be preprocessed is also on the HPC, you are ready to run fmriprep_ciftify.

```sh
singularity run --cleanenv /my_images/fmriprep_cifitfy-1.1.2-2.1.0.simg \
    path/to/data/dir path/to/output/dir \
    participant \
    --participant-label label
```

##

See the running the BIDS-App section for more information.

Singularity by default exposes all environment variables from the host inside the container. Because of this your host libraries (such as nipype) could be accidentally used instead of the ones inside the container - if they are included in PYTHONPATH. To avoid such situation we recommend using the --cleanenv singularity flag in production use. For example:

$ singularity run --cleanenv ~/poldracklab_fmriprep_latest-2016-12-04-5b74ad9a4c4d.img \
  /work/04168/asdf/lonestar/ $WORK/lonestar/output \
  participant \
  --participant-label 387 --nthreads 16 -w $WORK/lonestar/work \
  --omp-nthreads 16
or, unset the PYTHONPATH variable before running:

$ unset PYTHONPATH; singularity run ~/poldracklab_fmriprep_latest-2016-12-04-5b74ad9a4c4d.img \
  /work/04168/asdf/lonestar/ $WORK/lonestar/output \
  participant \
  --participant-label 387 --nthreads 16 -w $WORK/lonestar/work \
  --omp-nthreads 16
Note

Depending on how Singularity is configured on your cluster it might or might not automatically bind (mount or expose) host folders to the container. If this is not done automatically you will need to bind the necessary folders using the -B <host_folder>:<container_folder> Singularity argument. For example:

$ singularity run --cleanenv -B /work:/work ~/poldracklab_fmriprep_latest-2016-12-04-5b74ad9a4c4d.simg \
  /work/my_dataset/ /work/my_dataset/derivatives/fmriprep \
  participant \
  --participant-label 387 --nthreads 16 \

---
