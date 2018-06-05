## Download and Install

### Install latest release python package (python 3)
First, install the python package and all of its bundled data and scripts. You
can do this with a single command, with either pip or conda if you have one of
them installed. If you don't want to use either of these tools, skip to the
'manual install' step.

**Note** the newest release of ciftify requires python 3 (python 2 no longer supported).

To install with pip, type the following in a terminal.
```sh
pip install https://github.com/edickie/ciftify/archive/v2.0.2-beta.tar.gz
```

## Requirements (outside python)

ciftify draws upon the tools and templates of the HCP minimally processed pipelines, and therefore is dependent on them and their prereqs:
+ connectome-workbench version 1.2.3) [http://www.humanconnectome.org/software/get-connectome-workbench]
   + **Note** only the `cifti_vis*` tool currently only works with version 1.2.3. Work is underway to surpport the newest release of connectome-workbench
+ FSL [http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/]
+ FreeSurfer [https://surfer.nmr.mgh.harvard.edu/fswiki]
+ Multimodal Surface Matching (MSM), for MSMSulc surface realignment
   + Note: while an older version of this software is now packaged with FSL, the
      version required for this workflow is available for academic use from [this link](https://www.doc.ic.ac.uk/~ecr05/MSM_HOCR_v2/)

## Python Requirements

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

### Manual Installation
First clone the ciftify repo. Then set some environment variables:
+ add the `ciftify/bin` to your `PATH`
+ add the `ciftify` directory to your `PYTHONPATH`
+ create a new environment variable (`CIFTIFY_TEMPLATES`) that points to the location of the data directory.
+ (optional) create an environment variable for the location of your `HCP_DATA`

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

----

## Existing Installs of cifitfy on Canadian clusters

On the scinet cluster

```sh
source /scinet/course/ss2017/21_hcpneuro/ciftify_env.sh
```

On the CAMH SCC

```sh
module load Freesurfer/6.0.0
module load FSL
module load GNU_PARALLEL/20170122
module load connectome-workbench/1.2.3
module load python/3.6_ciftify_01
```
