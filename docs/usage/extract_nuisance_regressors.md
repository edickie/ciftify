# extract_nuisance_regressors

Tries to match the preprocessing described in "Functional connectome
fingerprinting: identifying individuals using patterns of brain connectivity".

i.e. generates an eroded white matter mask, eroded CSF mask, and calculates
mean time courses in the white matter and CSF. May also calulate the global
signal.

## Usage 
```
    extract_nuisance_regressors.py [options] <input_dir> <rest_file>...

Arguments:
    <input_dir>                 Full path to the MNINonLinear folder of a
                                subject's hcp outputs.

    <rest_file>                 The full path to a rest image to generate
                                the mean time courses + global signal for.
                                Can be repeated if multiple files must be
                                processed

Options:
    --output_dir PATH           Sets a path for all outputs (if unset, outputs
                                will be left in the directory of the results
                                file they were generated for)
    --debug
