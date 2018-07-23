#!/usr/bin/env python3
'''
these tools are for building the html pages in cifti-vis
'''

import os

import ciftify.utils

def write_index_pages(qc_dir, qc_config, page_subject, title="",
        title_formatter = None, user_filter=None):
    subjects = list(ciftify.utils.get_subj(qc_dir, user_filter=user_filter))

    index_html = os.path.join(qc_dir, 'index.html')
    ciftify.utils.check_output_writable(index_html)
    with open(index_html, 'w') as index_page:
        add_page_header(index_page, qc_config, page_subject,
                active_link='index.html')
        add_image_and_subject_index(index_page, qc_config.images, subjects,
                page_subject, qc_config.subtitle)

    for image in qc_config.images:
        if not image.make_index:
            continue
        # If {} is left in title string, will fill in with current image name,
        # otherwise this line has no effect
        if image.index_title:
            image_title = image.index_title
            if title_formatter:
                image_title = image_title.format(**title_formatter)
        else:
            image_title = title.format(image.name)
        write_image_index(qc_dir, subjects, qc_config, page_subject,
                image.name, title=image_title)

def add_page_header(html_page, qc_config, page_subject, subject=None,
        active_link=None, path='', title=None):
    """
    Adds a QC page header for a 'snap' or index page in the cifti_vis_* scripts.
    """
    if title is None:
        title = page_subject

    first_line = '<!DOCTYPE html>\n<HTML><TITLE>'
    if subject is not None:
        first_line = first_line + " QC {}".format(subject)
    first_line = first_line + " {} </TITLE>\n".format(title)

    html_page.write(first_line)
    write_header(html_page)

    html_page.write('<body>\n')
    nav_list = qc_config.get_navigation_list(path)
    write_navbar(html_page, page_subject, nav_list, active_link)

    if subject is not None:
        html_page.write('\n<h1>QC {} {}</h1>\n'.format(subject, page_subject))

def add_images(qc_page, qc_dir, image_list, scene_file,
                wb_logging = 'WARNING', add_titles = False, title_formatter = None):
    """
    Takes a list of scenes and montages, generates them, and adds them to
    qc_page.
    """
    for image in image_list:
        if add_titles:
            if image.subject_title:
                image_title = image.subject_title
                if title_formatter:
                    image_title = image_title.format(**title_formatter)
                qc_page.write('<h4>{}</h4>\n'.format(image_title))
        pic_name = "{}.png".format(image.name)
        write_image(qc_page, 12, pic_name, pic_name, "")
        output_path = os.path.join(qc_dir, pic_name)
        image.make_image(output_path, scene_file, logging = wb_logging)

def add_image_and_subject_index(index_page, images, subjects, page_subject, subtitle):
    """
    Writes links to images and subject qc.html pages.

    Arguments:
        index_page          An 'open' file to write the html to
        images              A list of Scene and/or Montage instances, such as
                            what is returned from qc_config.py's Config().images
                            attribute
        subjects            List of subjects whose qc.html pages are to be
                            linked onto index_page
        page_subject        The description of the topic/content of index_page
        subtitle            The subtitle at the top of the page
    """
    index_page.write('<h1>{} Index</h1>\n'.format(page_subject))
    index_page.write('<h3>{}</h3>\n'.format(subtitle))
    index_page.write('<h2>All subjects together</h2>\n')
    index_page.write('<ul>\n  ')
    for image in images:
        if not image.make_index:
            continue
        index_page.write('<li><a href="{}.html">{} View</a>' \
                ''.format(image.name, image.name))
        if image.index_title:
            index_page.write('<ul><li>{}</ul></li>\n' \
                ''.format(image.index_title))
        index_page.write('</li>\n')
    index_page.write('</ul>\n')
    index_page.write('<h2>Subject Pages</h2>\n')
    index_page.write('<ul>\n  ')
    for subject in subjects:
        index_page.write('<li><a href="{}/qc.html">{}</a>' \
                '</li>\n'.format(subject, subject))
    index_page.write('</ul>\n')
    index_page.write('</body>')

def write_image_index(qc_dir, subjects, qc_config, page_subject, image_name,
        title=None, colwidth=12):
    '''
    Writes html file with all subjects for one pic shown together
    '''
    pic_name = "{}.png".format(image_name)
    html_name = "{}.html".format(image_name)
    # open the file
    html_index = os.path.join(qc_dir, html_name)
    with open(html_index, 'w') as image_page:
        add_page_header(image_page, qc_config, page_subject, title=title,
                active_link=html_name)
        ## add the main title
        if title:
            image_page.write('<h2>{}</h2>\n'.format(title))
        for subject in subjects:
            add_image_and_subject_page_link(image_page, subject, pic_name,
                    colwidth)
        ## close the html page
        image_page.write('</body>\n')

def add_image_and_subject_page_link(image_page, subject, pic_name, colwidth):
    image_page.write('<div class="container" style="width: 100%;">')
    subject_page = os.path.join(subject, 'qc.html')
    pic = os.path.join(subject, pic_name)
    write_image(image_page, colwidth, subject_page, pic, subject)
    image_page.write('</div>\n</br>')

def write_header(htmlhandle):
    ''' writes some style elements into the html header '''
    htmlhandle.write('''
    <head>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">
    <style>
    body{
      background-color: rgba(0, 0, 0, 0.1);
      margin-top: 100px;
    }
    h1 {
      text-indent: 15px
    }
    </style>
    </head>
    ''')

def write_image(htmlhandle, colwidth, href, src, label):
    ''' writes an image to the html page with hyperlink'''
    htmlhandle.write('''
    <div class="theme-table-image col-sm-{colwidth}">
      <a href="{href}"><img src="{src}" class="img-responsive img-rounded">{label}</a><br>
    </div>
    '''.format(colwidth = colwidth,
               href = href,
               src = src,
               label = label))

def write_navbar(htmlhandle, brandname, nav_list, activelink=None):
    '''
    uses information from the nav_dict to build a fixed navigation bar
    nav dict contains a list of item to go in the Navigation bar
    '''
    htmlhandle.write('''
  <nav class="navbar navbar-inverse navbar-fixed-top">
    <div class="container-fluid">
      <div class="navbar-header">
        <a class="navbar-brand">{}</a>
      </div>
    <ul class="nav navbar-nav navbar-right">
    '''.format(brandname))
    for nav_dict in nav_list:
        activeclass = ' class="active"' if nav_dict['href'] == activelink else ''
        htmlhandle.write('<li{}><a href="{}">{}</a></li>\n'.format(
            activeclass,
            nav_dict['href'],
            nav_dict['label']
            ))
    htmlhandle.write('   </ul>\n  </div>\n</nav>\n')
