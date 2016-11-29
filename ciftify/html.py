'''
these tools are for building the html pages in cifti-vis
'''

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

def add_image(htmlhandle, colwidth, href, src, label):
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
