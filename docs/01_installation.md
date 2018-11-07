# Download and Install

ciftify is now available in a docker container! (actually a choice of two docker containers).
The main one of interest is the fmriprep_ciftify BIDS-app.

---
## Docker Container

In order to run fmriprep_ciftify in a Docker container, Docker must be installed.

To install:

```sh
docker run -ti --rm \
    -v filepath/to/data/dir:/data:ro \
    -v filepath/to/output/dir:/out \
    tigrlab/fmriprep_ciftify:<version> \
    /data /out/out participant --debug --dry-run
```

For example:

```sh
docker run -ti --rm \
    -v $HOME/fullds005:/data:ro \
    -v $HOME/dockerout:/out \
    tigrlab/fmriprep_ciftify:latest \
    /data /out/out \
    participant --anat_only
```

**Note:** while we use "latest" in the version tag. We recommend that you pull a specific version code instead so that you know exactly what you are running.

i.e.

```sh
docker run -ti --rm \
    -v filepath/to/data/dir:/data:ro \
    -v filepath/to/output/dir:/out \
    tigrlab/fmriprep_ciftify:1.1.8-2.1.1 \
    /data /out/out participant
```

Note for all version codes take the form [fmriprep version]-[ciftify version]

So version code 1.1.8-2.1.1 is version 1.1.8 of fmriprep with version 2.1.1 of the ciftify code.

## Docker to Singularity Container

For security reasons, many HPCs (e.g., SciNet) do not allow Docker containers, but do allow Singularity containers.

*Note: while singularity _should_ be able to build directly from dockerhub, it apprears to not work very well for the case of ciftify*. There appears to be a problem with singularity installs of some python dependancies when building inside ciftify.

Start with a machine (e.g., your personal computer) with Docker installed. Use docker2singularity to create a singularity image. You will need an active internet connection and some time.

```sh
docker run --privileged -t --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /absolute/path/to/output/folder:/output \
    singularityware/docker2singularity \
    tigrlab/fmriprep_ciftify:<version>
```

Where `<version>` should be replaced with the desired version of fmriprep_ciftify that you want to download.

Beware of the back slashes, expected for Windows systems. For `*nix` users the command translates as follows:

Transfer the resulting Singularity image to the HPC, for example, using scp.

```sh
scp tigrlab_fmriprep_ciftify*.img user@hcpserver.edu:/my_images
```

### Running a Singularity Image

If the data to be preprocessed is also on the HPC, you are ready to run fmriprep_ciftify.

```sh
singularity run --cleanenv /my_images/fmriprep_cifitfy-1.1.2-2.1.0.simg \
    path/to/data/dir path/to/output/dir \
    participant \
    --participant-label label
```

See the (running the BIDS-App section)[02_bids-app.md] for more information.

## Manually Prepared Environment

### Install latest release python package (python 3)

First, install the python package and all of its bundled data and scripts. You
can do this with a single command, with either pip or conda if you have one of
them installed. If you don't want to use either of these tools, skip to the
'manual install' step.

**Note** the newest release of ciftify requires python 3 (python 2 no longer supported).

To install with pip, type the following in a terminal.
```sh
pip install ciftify
```

### Requirements (outside python)

ciftify draws upon the tools and templates of the HCP minimally processed pipelines, and therefore is dependent on them and their prereqs:
+ connectome-workbench [http://www.humanconnectome.org/software/get-connectome-workbench]
+ FSL [http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/]
+ FreeSurfer [https://surfer.nmr.mgh.harvard.edu/fswiki]
+ Multimodal Surface Matching (MSM), for MSMSulc surface realignment
   + Note: while an older version of this software is now packaged with FSL, the
      version required for this workflow is available for academic use from [this link](https://github.com/ecr05/MSM_HOCR/releases)

#### Python Requirements

ciftify is mostly written in python 3 with the following package dependencies:

+ docopt
+ matplotlib
+ nibabel
+ numpy
+ pandas
+ pyyaml
+ seaborn (only for PINT vis)
+ scipy
+ nilearn
+ Pillow (for cifti-vis image manipulation)

### Bleeding Edge Manual Installation (for developers)

First clone the ciftify repo. Then set some environment variables:
+ add the `ciftify/bin` to your `PATH`
+ add the `ciftify` directory to your `PYTHONPATH`
+ create a new environment variable (`CIFTIFY_TEMPLATES`) that points to the location of the data directory.
+ (optional) create an environment variable for the location of your `CIFTIFY_WORKDIR`

Lastly, install the python package dependencies listed in the 'requirements'
section.

```sh
MYBASEDIR=${HOME}/code  ## change this to the directory you want to clone/download the ciftify code into

cd ${MYBASEDIR}
git clone https://github.com/edickie/ciftify.git
export PATH=$PATH:${MYBASEDIR}/ciftify/ciftify/bin
export PYTHONPATH=$PYTHONPATH:${MYBASEDIR}/ciftify
export CIFTIFY_TEMPLATES=${MYBASEDIR}/ciftify/data

### optional: you can also set an environment variable to the location of your data
export HCP_DATA=/path/to/hcp/subjects/data/
```

To check if ciftify is correctly configured, open a new terminal and type in a
ciftify command (like ciftify_vol_result).
```sh
ciftify_vol_result --help
```
If the terminal prints the command's help string, you're good to go! Otherwise, if the terminal gives you an error
like 'command not found', and your spelling of the command was correct, the path you provided has an error in it.

---

### Possible installation issues

#### Pip/Conda gives an error like UnicodeDecodeError: 'ascii' codec can't decode byte etc. etc.
This is the result of a system that doesn't have a proper UTF-8 environment set.
It can be fixed permanently by installing the 'locales' package or fixed
temporarily (if you don't have sudo permissions) by setting the LC_ALL variable.

For example, if your system uses US english you can fix it with
```sh
export LC_ALL=en_US.UTF-8
## The above should fix it, but these variables may need to be set as well if not
export LANG=en_US.UTF-8
export LANGUAGE=en_US.UTF-8
```
