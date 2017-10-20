# building a figure in wb_view
![Pretty Figure](https://github.com/edickie/docpics/blob/master/wb_view_demo/final_figure.png)
## Step 1: open wb_view

When you see the splash screen click **Skip**, we will load the files manually..

Click on **File -> Open File** to open the file browser
*Note: the filter (at the bottom) is set to only show you *.spec files...* Click on this and switch to "Any Files" 
Click on "null_WG33" and select all files (CRTL-A) and click "Open".
+ S900_AverageT1w_restore.nii.gz
+ S900.L.white_MSMAll.32k_fs_LR.surf.gii
+ S900.L.pial_MSMAll.32k_fs_LR.surf.gii
+ S900.L.very_inflated_MSMAll.32k_fs_LR.surf.gii
+ S900.R.pial_MSMAll.32k_fs_LR.surf.gii
+ S900.R.very_inflated_MSMAll.32k_fs_LR.surf.gii
+ S900.R.white_MSMAll.32k_fs_LR.surf.gii
+ S900.sulc_MSMAll.32k_fs_LR.dscalar.nii

Click on the "neurosynth_maps" folder and then select both files and click "Open"
+ working_memory_pFgA_z_FDR_0.01.nii.gz
+ working_memory_pFgA_z_FDR_0.01.dscalar.nii  

## Getting our tabs in order..

1. Click on the first tab **(1) Montage**
  + at the bottom you should see the **Overlay toolbox**.
    + click on the top toggle under **File** and select the *working_memory_pFgA_z_FDR_0.01.dscalar.nii*
     + make sure it is checked on
    + click on the bottom toggle and select the *S900.sulc_MSMAll.32k_fs_LR.dscalar.nii*
     + and check it on

2. Click on the **(2) Volume tab**:
   + At the bottom **Overlay Toolbox** - Select **Layers** Tab:
     + For the top layer - toggle the **File** to *working_memory_pFgA_z_FDR_0.01.nii.gz*
     + click on the wrench to the left of the filename to open up the **Overlay and Map Settings**
     + In **Overlay and Map Settings**, change the **Palette** (middle left toggle) to "PSYCH"
   + Click on the **Vol/Surf Outline** Tab:
     + Click on the outlines for the white and pial surfaces..
        + * *Note:* the locations of the group "white and "pial" average surfaces, are they where you expected them to be??*
   + At the top of the screen in the **Slice Plane** section, click on the **All** button to show all three views..
   + Click around the image to explore it a little.. note every time you click, the **Information toolbox** will pop up to tell you the intensity values at the curser..
   + keep clicking around until you have chosen your favourite view of the images

3. **Close** the Tabs **(3) All**, **(4) CortexLeft** and **(5)CortexRight**

4. From the File menu: Click on **View -> Enter Tile Tabs**

+ move the **(2) Volume Tab** *to the Left* of the **(1) Montage Tab** by clicking and dragging
 
## make the colour scales of the two images match

It seems like a color scale of 3 to 8 sounds reasonable let's do this for both images:
Click on the wrench beside the top layer of the overlay toolbox to open the **Overlay and Map Settings** toolbox.
+ Turn on the threshold and change to set to 3.5
+ change the palette to "PSYCH"
+ change the palette to from "Percent" to "Fixed"
+ change the Pos Max "Fixed" value to 8.5
+ un-check "Negative" so that only Positive Values are showing  

![Palette Change](https://github.com/edickie/docpics/blob/master/wb_view_demo/palette_change.png)

Now do the same for the dscalar image..

## Add the RSN networks to the background of the surface view..

+ Load the Yeo 7 Network Atlas: **File -> Open File** (Select *null_WG33/RSN-networks.32k_fs_LR.dlabel.nii*)
+ Click on the **(1) Montage Tab**
+ In the overlay toolbox, toggle the middle overlap to *RSN-networks.32k_fs_LR.dlabel.nii" and click the checkbox to display it
+ Click on the wrench beside the *RSN-Networks* to open the **Overlay and Map Settings toolbox**
   + Note: now that we are dealing with label data..the *Labels* dialog is visible instead
   + change the **Drawing Type** to **Outline Color**
+ Now click on the Briefcase Icon on the top right corner to open the **Features Toolbox** 
   + Turn all labels off by click the All: **Off** button
   + Under the *7 RSN Networks*.. Menu check the *7Networks_6 label*..

![Features Toolbox](https://github.com/edickie/docpics/blob/master/wb_view_demo/features_toolbox.png)

## Add some labels to the figure

-In the **Mode** Section of the Toolbar Click the **Annotate** Button
  + The Annotation let's you add Text, Objects and Images directly into the scene
  + You have 4 option for how to anchor the object you would like to add
      + **St**: Anchor to an MNI coordinate
      + **Sf**: Anchor to a surface vertex
      + **T**: Anchor to a location within a tab
      + **W**: Anchor to a location within the whole window (or figure)
   + For this example let's add text (**T**) anchored to the window (**W**) After clicking on these buttons click on the location where you would like to add text and a text box should pop up.
   + Add the text "Working Memory (neurosynth.org)"

## Save your figure into a scene!

+ Click on the directors slate (top right corner) to open the **Scene's Dialogue**
+ Click on **new** to create a new scene file..*PUT is one directory above the source files you have loaded*
+ Click **Add** to add you new figure to the scene file
 
## Save everything you have done

In the file menu, click on **File -> Save/Manage Files -> Save Checked Files**
+ also save the changes you have made to the palette for the working memory maps..

## And we are done

