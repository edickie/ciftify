# ciftify

The tools of the Human Connectome Project (HCP) adapted for working with non-HCP datasets

*cifity* is a set of three types of command line tools:

1. [**conversion tools**] (#conversiontools) : bash scripts adapted from HCP Minimal processing pipeline to put preprocessed T1 and fMRI data into an HCP like folder structure
2. [**ciftify tools**](#ciftifytools) : Command line tools for making working with cifty format a little easier
3. [**cifti-vis tools**](#cifti-vistools) : Visualization tools, these use connetome-workbench tools to create pngs of standard views the present theme together in fRML pages. 

## Download and Install

Right now I haven't gotten around to figuring out a nicer install, so the easiest is to just clone the repo and set some enviroment variables:
+ add the `ciftify/bin` to your `PATH`
+ add the `ciftify` directory to your `PYTHONPATH`
+ create a new environment variable (`HCP_SCENE_TEMPLATES`) that point to the location of the template scene files
+ create an environment variable for the location of your `HCP_DATA`

```sh
git clone 
export PATH=$PATH:<ciftify/bin>
export PYTHONPATH=$PYTHONPATH:<ciftify>
export HCP_DATA=/path/to/hcp/subjects/data/
export HCP_SCENE_TEMPLATES=<ciftify/data/scene_templates>
```

## Conversion Tools

## ciftify Tools

## cifti-vis Tools


