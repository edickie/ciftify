# Running the fmriprep_ciftify BIDS-App

![ciftify_workflow](_img/CIFTIFY_fig1_2018-05-04.png)

[bids-app usage](usage/fmriprep_ciftify_BIDS-app.md ':include')

## Running with Docker

```sh
docker run -ti --rm \
    -v $HOME/fullds005:/data:ro \
    -v $HOME/dockerout:/out \
    tigrlab/fmriprep_ciftify:latest \
    /data /out/out participant \
    --help
```

## Running with Singularity

If the data to be preprocessed is also on the HPC, you are ready to run fmriprep_ciftify.

```sh
singularity run --cleanenv /my_images/fmriprep_cifitfy-1.1.2-2.1.0.simg \
    path/to/data/dir path/to/output/dir \
    participant \
    --participant_label=<label>
```

### Some tricks to Singularity

Singularity by default exposes all environment variables from the host inside the container. Because of this your host libraries (such as nipype) could be accidentally used instead of the ones inside the container - if they are included in PYTHONPATH. To avoid such situation we recommend using the --cleanenv singularity flag in production use. For example:

```sh
singularity run --cleanenv /my_images/fmriprep_cifitfy-1.1.2-2.1.0.simg \
    path/to/data/dir path/to/output/dir \
    participant \
    --participant_label=01 \
    --n_cpus 8
```
or, unset the PYTHONPATH variable before running:

```sh
unset PYTHONPATH; singularity run /my_images/fmriprep_cifitfy-1.1.2-2.1.0.simg \
    path/to/data/dir path/to/output/dir \
    participant \
    --participant_label=01 \
    --n_cpus 8
```

Depending on how Singularity is configured on your cluster it might or might not automatically bind (mount or expose) host folders to the container. If this is not done automatically you will need to bind the necessary folders using the -B <host_folder>:<container_folder> Singularity argument. For example:

```sh
singularity run --cleanenv -B $SCRATCH/myproject:/work /my_images/fmriprep_cifitfy-1.1.2-2.1.0.simg \
    work/bids_in work/out participant \
    --participant_label=01 \
    --n_cpus 8
```

## Running specific commands with Singularity exec

You can also run specific ciftify package subcommands using `singularity exec`.

```sh
singularity exec --cleanenv -B $SCRATCH/myproject:/work /my_images/fmriprep_cifitfy-1.1.2-2.1.0.simg \
    ciftify_meants /work/my_func.dtseries.nii /work/my_atlas.dlabel.nii

```
