"""
Contains the QC settings dictionary for all cifti_vis scripts, as well as
a class to make access to settings easy to read.
"""
import os
import logging

import ciftify.config as config

class Config(object):
    def __init__(self, mode):
        self.__qc_settings = qc_modes[mode]
        self.template = self.__get_template()
        self.scenes = self.__qc_settings['scene_list']
        self.montages = self.__qc_settings['montage_list']

    def __get_template(self):
        template_name = self.__qc_settings['TemplateFile']
        template_dir = config.find_scene_templates()
        return os.path.join(template_dir, template_name)

# Settings dictionary
qc_modes = {
    "func2cifti":{
        "TemplateFile":"func2cifti_template.scene",
        "scene_list" :  [
            {"Idx": 7, "Name": "funcVolPialCor", "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 8, "Name": "VolFuncPialAx",  "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 9, "Name": "volfuncpialSag",   "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 2, "Name": "dtDorsal",  "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 3, "Name": "dtVentral", "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 4, "Name": "dfVolCor", "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 5, "Name": "dtVolSag",  "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 6, "Name": "dtVolAx",  "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 1, "Name": "dtLat",     "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True}],
        "montage_list" : [{"Name": "DorsalVental",
                       "Pics":["dtDorsal","dtVentral"],
                       "Layout":"2x1",
                       "MakeIndex": True}]
    },

    "mapvis":{
        "TemplateFile": "mapvis_template.scene",
        "scene_list" :  [
            {"Idx": 2, "Name": "dtDorsal",  "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 3, "Name": "dtVentral", "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 4, "Name": "dtAnt",  "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 5, "Name": "dtPost", "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 6, "Name": "VolAx", "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 7, "Name": "VolCor",  "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 8, "Name": "VolSag",  "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 1, "Name": "LateralMedial",     "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True}],
        "montage_list" : [{"Name": "CombinedView",
                       "Pics":["dtAnt","dtPost","dtDorsal","dtVentral"],
                       "Layout":"4x1",
                       "MakeIndex": True}]
    },

    "scrois":{
        "TemplateFile": "scrois_template.scene",
        "scene_list" :  [
            {"Idx": 2, "Name": "dtDorsal",  "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 3, "Name": "dtVentral", "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 4, "Name": "dtAnt",  "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 5, "Name": "dtPost", "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 6, "Name": "VolAx", "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 7, "Name": "VolCor",  "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 8, "Name": "VolSag",  "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 1, "Name": "dtLat",     "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True}],
        "montage_list" : [{"Name": "CombinedView",
                       "Pics":["dtAnt","dtPost","dtDorsal","dtVentral"],
                       "Layout":"4x1",
                       "MakeIndex": True}]
    },

    "MNIfsaverage32k":{
        "TemplateFile":"MNIfsaverage32k_template.scene",
        "scene_list" :  [
            {"Idx": 1, "Name": "aparc",            "MakeIndex": True,
                    "SplitHorizontal" : True, "Keep":True},
            {"Idx": 2, "Name": "SurfOutlineAxial",  "MakeIndex": True,
                    "SplitHorizontal" : True,"Keep":True},
            {"Idx": 3, "Name": "SurfOutlineCoronal", "MakeIndex": False,
                    "SplitHorizontal" : True,"Keep":True},
            {"Idx": 4, "Name": "SurfOutlineSagittal", "MakeIndex": True,
                    "SplitHorizontal" : True,"Keep":True},
            {"Idx": 5, "Name": "AllLeft",          "MakeIndex": False,
                    "SplitHorizontal" : False, "Keep": False},
            {"Idx": 6, "Name": "AllRight",          "MakeIndex": False,
                    "SplitHorizontal" : False, "Keep": False},
            {"Idx": 7, "Name": "AllVentral",          "MakeIndex": False,
                    "SplitHorizontal" : False, "Keep": False},
            {"Idx": 8, "Name": "AllDorsal",          "MakeIndex": False,
                    "SplitHorizontal" : False, "Keep": False}],
        "montage_list" : [{"Name": "CombinedView",
                       "Pics":["AllLeft","AllRight","AllDorsal","AllVentral"],
                       "Layout":"4x1",
                       "MakeIndex": True}]
    },

    "native":{
        "TemplateFile":"native_template.scene",
        "scene_list" :  [
            {"Idx": 10, "Name": "asegAxial",  "MakeIndex": True,
                        "SplitHorizontal" : True,"Keep":True},
            {"Idx": 9, "Name": "asegCoronal", "MakeIndex": False,
                        "SplitHorizontal" : True,"Keep":True},
            {"Idx": 11, "Name": "asegSagittal", "MakeIndex": True,
                        "SplitHorizontal" : True,"Keep":True},
            {"Idx": 2, "Name": "SurfOutlineAxial",  "MakeIndex": True,
                        "SplitHorizontal" : True,"Keep":True},
            {"Idx": 3, "Name": "SurfOutlineCoronal", "MakeIndex": False,
                        "SplitHorizontal" : True,"Keep":True},
            {"Idx": 4, "Name": "SurfOutlineSagittal", "MakeIndex": True,
                        "SplitHorizontal" : True,"Keep":True},
            {"Idx": 5, "Name": "AllLeft",          "MakeIndex": False,
                        "SplitHorizontal" : False, "Keep": False},
            {"Idx": 6, "Name": "AllRight",          "MakeIndex": False,
                        "SplitHorizontal" : False, "Keep": False},
            {"Idx": 7, "Name": "AllVentral",          "MakeIndex": False,
                        "SplitHorizontal" : False, "Keep": False},
            {"Idx": 8, "Name": "AllDorsal",          "MakeIndex": False,
                        "SplitHorizontal" : False, "Keep": False},
            {"Idx": 12, "Name": "Curvature",          "MakeIndex": False,
                        "SplitHorizontal" : True, "Keep": True},
            {"Idx": 13, "Name": "Thickness",          "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep": True},
            {"Idx": 1, "Name": "aparc",            "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True}],
        "montage_list" : [{"Name": "CombinedView",
                       "Pics":["AllLeft","AllRight","AllDorsal","AllVentral"],
                       "Layout":"4x1",
                       "MakeIndex": True}]
    },

    "seedcorr":{
        "TemplateFile":"seedcorr_template.scene",
        "scene_list" :  [
            {"Idx": 2, "Name": "dtDorsal",  "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 3, "Name": "dtVentral", "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 4, "Name": "dtAnt",  "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 5, "Name": "dtPost", "MakeIndex": False,
                        "SplitHorizontal" : False,"Keep":False},
            {"Idx": 6, "Name": "VolAx", "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 7, "Name": "VolCor",  "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 8, "Name": "VolSag",  "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True},
            {"Idx": 1, "Name": "dtLat",     "MakeIndex": True,
                        "SplitHorizontal" : True, "Keep":True}],
        "montage_list" : [{"Name": "CombinedView",
                       "Pics":["dtAnt","dtPost","dtDorsal","dtVentral"],
                       "Layout":"4x1",
                       "MakeIndex": True}]
    }
}
