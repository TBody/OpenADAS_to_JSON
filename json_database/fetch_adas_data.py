# Program name: OpenADAS_to_JSON/json_database/fetch_adas_data.py
# Author: Thomas Body
# Author email: tajb500@york.ac.uk
# Date of creation: 12 July 2017
# 
# This program combines the ./fetch_adas_data.py and adas.py files from cfe316/atomic,
# with no modification except for translating into Python3
# 
# This program downloads the ADF11 and ADF15 data files from open.adas.ac.uk
# ADF11: Iso-nuclear master files
#   Effective (collisional–radiative) coefficients which are required to establish
#   the ionisation state of a dynamic or steady-state plasma.
# ADF15: Photon emissivity coefficients
#   Fully density dependent and metastable resolved effective emissivity
#   coefficients from a collisional–radiative model.
#   
# The impurities to search for are supplied as ('name', year_shorthand) pairs to
#   elements_years = ...
#   in the __main__ section
#   
# The program downloads all relevant .dat data files to ./adas_data and all code files to
# ./src. A seperate function (adas_to_json.py) is provided for converting these files to 
# JSON databases, for incorporation into python or C++ code.
# 
# Note that it is not currently possible to process metastable-resolved data files (in this
# program, nor in cfe316/atomic)

import tarfile
import os
import errno
import shutil
import urllib.parse
import urllib.request
import sys #For processing commmand line arguments
import warnings

# Code originally from atomic-master/adas.py
open_adas_url = 'http://open.adas.ac.uk/'

class OpenAdas(object):
    def search_adf11(self, element, year='', ms='metastable_unresolved'):
        p = [('element', element), ('year', year), (ms, 1),
                ('searching', 1)]
        s = AdasSearch('adf11')
        return s.search(p)

    def search_adf15(self, element, charge=''):
        p = [('element', element), ('charge', charge), ('resolveby', 'file'),
                ('searching', 1)]
        s = AdasSearch('adf15')
        return s.search(p)

    def fetch(self, url_filename, dst_directory=None):
        if dst_directory == None:
            dst_directory = os.curdir
        self.dst_directory = dst_directory

        url = self._construct_url(url_filename)
        nested = False # this switch makes files save flat
        if nested:
            path = self._construct_path(url_filename)
        else:
            __, path = url_filename

        tmpfile, __ = urllib.request.urlretrieve(url)

        dst_filename = os.path.join(self.dst_directory, path)
        self._mkdir_p(os.path.dirname(dst_filename))


        shutil.move(tmpfile, dst_filename)

    def _construct_url(self, url_filename):
        """
        >>> db = OpenAdas()
        >>> db._construct_url(('detail/adf11/prb96/prb96_c.dat', 'foo.dat'))
        'http://open.adas.ac.uk/download/adf11/prb96/prb96_c.dat'
        """
        url, __ = url_filename
        query = url.replace('detail','download')
        return open_adas_url + query

    def _construct_path(self, url_filename):
        """
        This function constructs a path to store the file in.
        >>> db = OpenAdas()
        >>> db._construct_path(('detail/adf11/prb96/prb96_c.dat', 'foo.dat'))
        'adf11/prb96/prb96_c.dat'
        """
        url, filename = url_filename
        path = url.replace('detail/','')
        path = path.replace('][','#')
        return path

    def _mkdir_p(self,path):
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise


class AdasSearch(object):
    def __init__(self, class_):
        if class_ not in ['adf11', 'adf15']:
            raise NotImplementedError('ADAS class %s is not supported.' %s)

        self.url = open_adas_url + '%s.php?' % class_
        self.class_ = class_
        self.data = 0
        self.parameters = []

    def search(self, parameters):
        self.parameters = parameters
        self._retrieve_search_page()
        return self._parse_data()

    def _retrieve_search_page(self):
        search_url =  self.url + urllib.parse.urlencode(self.parameters)
        res, __ = urllib.request.urlretrieve(search_url)
        self.data = open(res).read()
        os.remove(res)

    def _parse_data(self):
        parser = SearchPageParser()
        parser.feed(self.data)
        lines = parser.lines

        if lines == []: return {}
        header = lines.pop(0)

        db = []
        for l in lines:
            if self.class_ == 'adf11':
                element, class_, comment, year, resolved, url, cl, typ, name = l
                name = name.strip()
                db.append((url, name))
            elif self.class_ == 'adf15':
                element, ion, w_lo, w_hi, url, cl, typ, name = l
                name = name.strip()
                db.append((url, name))
            else:
                raise NotImplementedError('this should never happen')

        return db

    def _strip_url(self, url):
        __, id_ = url.split('=')
        return int(id_)


# from HTMLParser import HTMLParser
from html.parser import HTMLParser
class SearchPageParser(HTMLParser):
    """
    Filling in a search form on http://open.adas.ac.uk generates a HTML document
    with a table that has the following structure:

    >>> html = '''
    ... <table summary='Search Results'>
    ...     <tr>
    ...     <td>Ne</td> <td><a href='filedetail.php?id=32147'>rc89_ne.dat</a></td>
    ...     <tr>
    ...     </tr>
    ...     <td>C</td> <td><a href='filedetail.php?id=32154'>rc89_c.dat</a></td>
    ...     </tr>
    ... </table>'''

    The SearchPageParser can parse this document looking for a table with a
    class `searchresults`.
    >>> parser = SearchPageParser()
    >>> parser.feed(html)
    >>> for l in parser.lines: print l
    ['Ne', 'filedetail.php?id=32147', 'rc89_ne.dat']
    ['C', 'filedetail.php?id=32154', 'rc89_c.dat']
    """
    def reset(self):
        self.search_results = False
        self.line = []
        self.lines = []

        HTMLParser.reset(self)

    #def handle_starttag(self, tag, attrs):
    #    attrs = dict(attrs)
    #    if tag == 'table' and attrs.get('class') == 'searchresults':
    #        self.search_results = True
    #    if not self.search_results: return
    #
    #    if tag == 'a' and self.line != None:
    #        self.line.append(attrs['href'])

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if (tag == 'table'
                and 'summary' in attrs
                and 'Results' in attrs['summary']):
            self.search_results = True
        if not self.search_results: return

        if tag == 'a' and self.line != None:
            self.line.append(attrs['href'])

    def handle_endtag(self, tag):
        if tag == 'table':
            self.search_results = False
        if not self.search_results: return

        if tag == 'tr':
            self.lines.append(self.line)
            self.line = []

    def handle_data(self, data):
        if not self.search_results: return

        if data.strip() != '':
            self.line.append(data)

# Code originally from atomic-master/./fetch_adas_data

if __name__ == '__main__':

    elements_years = [];

    elements_set = False
    for command_line_arg_index in range(1,len(sys.argv)):
        # Will not enter this loop if only 1 argument (i.e. function name) supplied
        if str(sys.argv[command_line_arg_index][0:10]) == '--elements':
            # Extract the section after the equals
            print(sys.argv[command_line_arg_index][11:])
            
            CL_elements_string = sys.argv[command_line_arg_index][11:]
            for element_string in CL_elements_string.split(','):
                [element_name, element_year] = element_string.split(':')
                element_name = element_name.strip().lower()
                element_year = int(element_year.strip())
                elements_years.append((element_name,element_year))
            elements_set = True;
        else:
            warnings.warn('Command line argument {} not recognised by fetch_adas_data.py'.format(sys.argv[command_line_arg_index]))

    if not(elements_set):
        raise BaseException("--elements=\{...\} argument not given to fetch_adas_data.py. See makefile header and set the elements variable.")

    print('>> fetch_adas_data.py called')

    print('\nDownloading ADF11 and ADF15 files from OpenADAS')
    print('Database url: {}\n'.format(open_adas_url))
    
    atomic_data = './adas_data'
    # elements_years = [('carbon', 96),('nitrogen', 96)]
    print('Element-data will be downloaded for')
    for element, year in elements_years:
        print('{} (year = 19{})'.format(element,year))
    print('\nDownloading files - please wait\n')

    db = OpenAdas()

    # Downloads ADF11 data
    for element, year in elements_years:
        res = db.search_adf11(element, year)

        for r in res:
            print(r[1])
            db.fetch(r, atomic_data)

    # Downloads ADF15 data
    for element, year in elements_years:
        res = db.search_adf15(element)

        for r in res:
            print(r[1])
            db.fetch(r, atomic_data)

    # Downloads codes for unpacking data
    destination = './src'
    for routine in (11,15):
        fname = 'xxdata_' + str(routine) + '.tar.gz'
        print("Downloading " + fname)
        db.fetch(('/code/' + fname, fname), destination)
        tar = tarfile.open(destination + '/' + fname)
        # here we specifically go against the prohibition in
        # https://docs.python.org/2/library/tarfile.html#tarfile.TarFile.extractall
        print("Extracting " + fname)
        tar.extractall(path=destination)

    print('>> fetch_adas_data.py exited without error')

