
# coding: utf-8

# In[1]:


import os
import unittest
import logging
import shutil
import tempfile
import ciftify.config
from ciftify.utils import run


# In[2]:





# In[3]:


def get_test_data_path():
    return 'data/'

left_surface = os.path.join(get_test_data_path(),
        'sub-50005.L.midthickness.32k_fs_LR.surf.gii')
right_surface = os.path.join(get_test_data_path(),
        'sub-50005.R.midthickness.32k_fs_LR.surf.gii')


# In[4]:


left_surface


# In[18]:


test_dtseries = os.path.join(get_test_data_path(),
        'sub-50005_task-rest_Atlas_s0.dtseries.nii')


# In[5]:


tmpdir = tempfile.mkdtemp()


# In[6]:


vertices_csv = os.path.join(tmpdir, 'vertices.csv')

with open(vertices_csv, "w") as text_file:
    text_file.write('''hemi,vertex
L,11801
L,26245
L,26235
L,26257
L,13356
L,289
L,13336
L,13337
L,26269
L,13323
L,26204
''')

Lgauss_dscalar = os.path.join(tmpdir, 'gaussian.dscalar.nii')
run(['ciftify_surface_rois', vertices_csv, '10', '--gaussian',
     left_surface,
     right_surface,
     Lgauss_dscalar])


# In[28]:


vertices1_csv = os.path.join(tmpdir, 'vertices1.csv')

with open(vertices1_csv, "w") as text_file:
    text_file.write('''hemi,vertex
L,11801
''')

Lcircle_dscalar = os.path.join(tmpdir, 'circle.dscalar.nii')
run(['ciftify_surface_rois', vertices1_csv, '16',
     left_surface,
     right_surface,
     Lcircle_dscalar])

run(['wb_command', '-cifti-create-dense-from-template', test_dtseries, Lcircle_dscalar, '-cifti', Lcircle_dscalar])


# In[29]:


Glasser_atlas = os.path.join(ciftify.config.find_HCP_S1200_GroupAvg(),
'Q1-Q6_RelatedValidation210.CorticalAreas_dil_Final_Final_Areas_Group_Colors.32k_fs_LR.dlabel.nii')


# In[31]:


tmp1 = os.path.join(tmpdir, 'out1.dscalar.nii')
run(['wb_command', '-cifti-label-to-roi', Glasser_atlas,tmp1, '-name', 'R_10v_ROI']) 
run(['wb_command', '-cifti-math "(x*2)"', tmp1, '-var', 'x', tmp1])
run(['wb_command', '-cifti-create-dense-from-template', test_dtseries, tmp1, '-cifti', tmp1])


# In[32]:


tmp2 = os.path.join(tmpdir, 'out2.dscalar.nii')
run(['wb_command', '-cifti-label-to-roi', Glasser_atlas,tmp2, '-name', 'R_LIPv_ROI']) 
run(['wb_command', '-cifti-math "(x*3)"', tmp2, '-var', 'x', tmp2])
run(['wb_command', '-cifti-create-dense-from-template', test_dtseries, tmp2, '-cifti', tmp2])


# In[16]:


tmpdir


# In[24]:


tmp3 = os.path.join(tmpdir, 'output3.nii.gz')

run(['wb_command', '-cifti-separate', test_dtseries, 'COLUMN', 
     '-volume', 'HIPPOCAMPUS_LEFT', os.path.join(tmpdir, 'hipp.nii.gz'), '-roi', tmp3])
run(['wb_command', '-volume-math "(x*4)"', tmp3, '-var', 'x', tmp3])
tmp3_cifti = os.path.join(tmpdir, 'output3.dscalar.nii')
run(['wb_command', '-cifti-create-dense-from-template', test_dtseries, tmp3_cifti, '-volume-all', tmp3])


# In[33]:


final_dscalar = os.path.join(tmpdir, 'merge4.dscalar.nii')
run(['wb_command', '-cifti-math "(a+b+c+d)"', final_dscalar, 
     '-var', 'a', Lcircle_dscalar,
    '-var', 'b', tmp1,
    '-var', 'c', tmp2,
    '-var', 'd', tmp3_cifti,
    '-override-mapping-check'])


# In[34]:


final_dlabel = os.path.join(tmpdir, 'rois_for_tests.dlabel.nii')
run(['wb_command', '-cifti-label-import', final_dscalar, '""', final_dlabel])


# In[38]:


run(['wb_command', '-cifti-label-export-table', final_dlabel, '1', os.path.join(tmpdir, 'labels.txt')])


# In[ ]:


outputlabels = '''
L11801_16mm
1 219 9 59 255
R_10v_ROI
2 10 223 94 255
R_LIPv_ROI
3 86 226 14 255
HIPPOCAMPUS_LEFT
4 89 74 190 255
'''

