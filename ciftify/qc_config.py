#!/usr/bin/env python3
"""
Contains the QC settings dictionary for all cifti_vis scripts, as well as
a class to make access to settings easy to read.
"""
import os
import sys
import logging
from abc import ABCMeta, abstractmethod
from PIL import Image

import yaml

import ciftify.config as config
from ciftify.utils import run, TempDir, add_metaclass

class Config(object):
    def __init__(self, mode):
        self.__qc_settings = self.__read_mode(mode)
        self.template_name = self.__qc_settings['TemplateFile']
        self.template = self.__get_template()
        self.__scene_dict = self.__get_scene_dict()
        # self.__montages = self.__get_montages()
        self.images = self.__get_images()
        self.subtitle = self.__get_subtitle()

    def get_navigation_list(self, path=''):
        nav_list = [{'href': '', 'label':'View:'}]

        for image in self.images:
            if image.make_index:
                image_path = os.path.join(path, '{}.html'.format(image.name))
                nav_list.append({ 'href': image_path,
                                  'label': image.name})

        index_path = os.path.join(path, 'index.html')
        nav_list.append({'href': index_path, 'label':'Index'})

        return nav_list

    def get_template_contents(self):
        try:
            with open(self.template, 'r') as template_txt:
                template_contents = template_txt.read()
        except:
            logger.error("{} cannot be read.".format(self.template))
            sys.exit(1)

        if not template_contents:
            logger.error("Template {} is empty".format(self.template))
            sys.exit(1)

        return template_contents

    def __read_mode(self, mode):
        logger = logging.getLogger(__name__)
        ciftify_data = config.find_ciftify_global()
        qc_settings = os.path.join(ciftify_data, 'qc_modes.yaml')
        try:
            with open(qc_settings, 'r') as qc_stream:
                qc_modes = yaml.load(qc_stream)
        except:
            logger.error("Cannot read qc_modes file: {}".format(qc_settings))
            sys.exit(1)
        try:
            settings = qc_modes[mode]
        except KeyError:
            logger.error("qc_modes file {} does not define mode {}"
                    "".format(qc_settings, mode))
            sys.exit(1)
        return settings

    def __get_template(self):
        logger = logging.getLogger(__name__)
        template_dir = config.find_scene_templates()
        if not template_dir:
            logger.error("Cannot find scene templates. Please ensure "
                    "CIFTIFY_DATA shell variable is properly set.")
            sys.exit(1)
        template = os.path.join(template_dir, self.template_name)
        if not os.path.exists(template):
            logger.error("Expected template {} does not exist at path {}. "
                    "Please check CIFTIFY_DATA variable is correctly "
                    "set.".format(self.template_name, template))
            sys.exit(1)
        return template

    def __get_subtitle(self):
        try:
            subtitle = self.__qc_settings['IndexSubtitle']
        except KeyError:
            subtitle = None
        return(subtitle)

    def __get_scene_dict(self):
        """
        Generates a dict to help separate the scenes that are montage only
        from the scenes that appear individually on the page.
        """
        scene_dict = {}
        for scene_type in self.__qc_settings['scene_list']:
            cur_scene = Scene(scene_type)
            scene_dict[cur_scene.name] = cur_scene
        return scene_dict

    # def __get_montages(self):
    #     """
    #     When montages are made, scenes may be deleted from scene dict
    #     if they are a member of a montage but not labeled 'Keep'
    #     """
    #     montages = []
    #     qc_settings = self.__qc_settings
    #     if 'montage_list' in qc_settings.keys():
    #         for montage_type in qc_settings['montage_list']:
    #             cur_montage = Montage(montage_type, self.__scene_dict)
    #             montages.append(cur_montage)
    #     return montages

    def __get_images(self):
        images = []
        # images.extend(self.__montages)
        images.extend(self.__scene_dict.values())
        images = sorted(images, key=lambda image: image.order)
        return images

@add_metaclass(ABCMeta)
class QCScene(object):
    """
    This abstract class acts as a base class for both Montage and Image so
    both can be used interchangeably in ciftify-vis scripts.
    """

    _attributes = {}
    name = ''
    path = ''
    make_index = False
    order = 0

    def _get_attribute(self, key, manditory = True):
        logger = logging.getLogger(__name__)
        try:
            attribute = self._attributes[key]
        except KeyError:
            if manditory:
                logger.error("Scene {} does not contain the key {}. " \
                        "Exiting".format(self._attributes, key))
                sys.exit(1)
            attribute = None
        return attribute

    @abstractmethod
    def make_image(self, output_path, scene_file):
        pass

class Scene(QCScene):
    def __init__(self, attributes):
        self._attributes = attributes
        self.name = self._get_attribute('Name')
        self.make_index = self._get_attribute('MakeIndex')
        self.index = self._get_attribute('Idx')
        self.split_horizontal = self._get_attribute('SplitHorizontal')
        self.save_image = self._get_attribute('Keep')
        self.order = self._get_attribute('Order')
        self.index_title = self._get_attribute('IndexTitle', manditory = False)
        self.subject_title = self._get_attribute('PreTitle', manditory = False)
        self.width = self.__get_width()
        self.height = self.__get_height()


    def make_image(self, output_loc, scene_file, logging='WARNING'):
        if self.split_horizontal:
            self.path = self.__split(output_loc, scene_file, logging, self.width,
                    self.height)
            return
        self.__show_scene(output_loc, scene_file, logging, self.width, self.height)
        self.path = output_loc

    def __get_width(self):
        width = self._get_attribute('Width', manditory = False)
        if not width: width = 600
        return width

    def __get_height(self):
        height = self._get_attribute('Height', manditory = False)
        if not height: height = 400
        return height

    def __show_scene(self, output, scene_file, logging, width, height):
        run(['wb_command', '-logging', logging, '-show-scene',
                scene_file, str(self.index), output, str(width), str(height)])

    def __split(self, output_loc, scene_file, logging, width, height):
        with TempDir() as tmp_dir:
            tmp_img = os.path.join(tmp_dir, "scene{}.png".format(self.index))
            self.__show_scene(tmp_img, scene_file, logging, width, height)

            with Image.open(tmp_img) as img:
                half_the_height = height // 2
                img_top = img.crop((0, 0, width, half_the_height))
                img_btm = img.crop((0, half_the_height, width, height))
                im2 = Image.new('RGBA', (int(width*2), half_the_height))
                im2.paste(img_top, (0, 0))
                im2.paste(img_btm, (width, 0))
                im2.save(output_loc)

        return output_loc

    def __repr__(self):
        return "<ciftify.qc_config.Scene({})>".format(self.name)

    def __str__(self):
        return self.name

# class Montage(QCScene):
#     def __init__(self, attributes, scene_dict):
#         self._attributes = attributes
#         self.name = self._get_attribute('Name')
#         self.pics = self._get_attribute('Pics')
#         self.layout = self._get_attribute('Layout')
#         self.make_index = self._get_attribute('MakeIndex')
#         self.scenes = self.__get_scenes(scene_dict)
#         self.order = self._get_attribute('Order')
#
#     def __get_scenes(self, scene_dict):
#         """
#         This method will delete scenes from scene_dict if any are included in
#         the montage but not labeled 'Keep'.
#         """
#         scenes = []
#         for pic in self.pics:
#             scene = scene_dict[pic]
#             if not scene.save_image:
#                 del scene_dict[pic]
#             scenes.append(scene)
#         return scenes
#
#     def make_image(self, output_loc, scene_file, logging='WARNING', width=600,
#                 height=400):
#         montage_cmd=['montage', '-mode', 'concatenate', '-tile',
#                 self.layout]
#         with TempDir() as tmp_dir:
#             for scene in self.scenes:
#                 tmp_path = os.path.join(tmp_dir, "{}.png".format(scene.name))
#                 scene.make_image(tmp_path, scene_file, logging, width, height)
#                 montage_cmd.append(tmp_path)
#             montage_cmd.append(output_loc)
#             run(montage_cmd)
#             self.path = output_loc
#
#     def __repr__(self):
#         return "<ciftify.qc_config.Montage({})>".format(self.name)
#
#     def __str__(self):
#         return self.name

def replace_path_references(template_contents, template_prefix, path, scene_file):
    ''' replace refence to a file in a template scene_file in three ways
    absolute path, relative path and basename
    '''
    path = os.path.realpath(path)
    txt = template_contents.replace('{}_ABSPATH'.format(template_prefix),
                                    path)
    txt = txt.replace('{}_RELPATH'.format(template_prefix),
                        os.path.relpath(path,
                                        os.path.dirname(scene_file)))
    return txt

def replace_all_references(template_contents, template_prefix, path, scene_file):
    ''' replaces all three references to a file in the scene template '''
    txt = replace_path_references(template_contents, template_prefix,
                                path, scene_file)
    txt = txt.replace('{}_BASE'.format(template_prefix),
                      os.path.basename(path))
    return txt
