#!/usr/bin/env python
# functional tests for the run.py script
# note: to start we will just run many dry-runs to insure that the correct
#      command-line calls are generated given the user args..

# also note! pybids has three test datasets! we can use!
# note all the data has been removed from the nifti files to make them fit in github so running them fully won't work..
# but ds005 we could get through datalad..
# also note: ds00005 does have an ok res T2 so it may be worth testing against the HCPPipelines..
# but no public fmriprep derivatives..

from bids.tests import get_test_data_path
from ciftify.utils import run
# bids/tests/data/ds005 - 16 subjects, 1 session, no fmap
ds005_bids = os.path.join(get_test_data_path(), 'ds005')
ds005_output = /scratch/edickie/ds005_output
run(['mkdir -p', ds005_output])


# bids/tests/data/7t_trt - 10 Subject, 2 sessions + fmap (phase) based on ds001168
ds7t_bids = os.path.join(get_test_data_path(), '7t_trt')
ds7t_out = '/tmp/ds7t_out'

# bids/tests/data/synthetic - 5 subjects, 2 sessions, no fmap
synth_bids = os.path.join(get_test_data_path(), 'synthetic')
synth_out = '/tmp/synth_out'
# it would be good to find/generate a test case with 1 session (i.e. no session struct) and fmaps..
# note ds001393 "RewardBeast" on open neuro has this format..
# note ds000256_R1.0.0 on open neuro also has this format..
# individual brain Charting ds000244 is the only one I see with Repolar fieldmaps

# writing my script of things that a functional test would do

# user A (synthetic or ds005) runs all data with no fieldmaps from scratch
# + default args
run(['run.py', ds005_bids, ds005_output, 'participant', '--debug', '--dry-run',
    '--participant_label=14'])

run(['run.py', ds005_bids, ds005_output, 'participant', '--debug', '--dry-run',
    '--participant_label=14', '--anat_only'])
run(['run.py', synth_bids, synth_out, 'participant', '--debug', '--dry-run'])
# + no sdc
## note run in synthetics and ds005 to insure that these flags work..
# + filter for one session, filter for 2 sessions, not filtered for sessions
run(['run.py', synth_bids, synth_out, 'participant', '--debug', '--dry-run', '--participant_label="02"'])
run(['run.py', synth_bids, synth_out, 'participant', '--debug', '--dry-run', '--participant_label="03,04"'])
# + filter for task
run(['run.py', synth_bids, synth_out, 'participant', '--debug', '--dry-run', '--task_label=rest'])
# + filter for one subject, two subjects, not filtering for subjects
run(['run.py', synth_bids, synth_out, 'participant', '--debug', '--dry-run', '--session_label=01'])

# user B (7t_trt) runs all data with fieldmaps from scratch
# + default args (using fieldmaps)
run(['run.py', synth_bids, synth_out, 'participant', '--debug', '--dry-run'])

# + using ignore fieldmaps (should run syn-sdc)
run(['run.py', synth_bids, synth_out, 'participant', '--debug', '--dry-run', '--ignore-fieldmaps'])
# + no sdc
run(['run.py', synth_bids, synth_out, 'participant', '--debug', '--dry-run', '--no-SDC'])

# user C runs (ds005) from freesurfer (note fieldmaps options shoudl not be effected by anat)

# user D runs (ds005) from freesurfer with --anat-only (should only run ciftify_recon_all steps)

# user E run (ds005) from fmriprep (runs ciftify_recon_all and ciftify_subject_fmri)

# - note this brings up the use case where the use may want to run
#   ciftify_subject_fmri in parallel (for many tasks/sessions) AFTER running ciftify_recon_all once
# user F run (ds005) from fmriprep skipping ciftify_recon_all...need to introduce flag for this..
