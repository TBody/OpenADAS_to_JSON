# Program name: OpenADAS_to_JSON/json_database/setup_fortran_programs.py
# Author: Thomas Body
# Author email: tajb500@york.ac.uk
# Date of creation: 12 July 2017
# 
# This program is copied from setup.py from cfe316/atomic, with a slight modification to 
# make Python3 compatible (changed .iteritems() to .items())
# 
# Builds the fortran helper functions contained in src into a python callable state (makes
# _xxdata_##module.c functions, and also creates the 'build' directory)
# 
# Note that in order to run successfully the program must be called as
# >>python setup_fortran_programs.py build_ext --inplace
# (see https://docs.python.org/3.6/distutils/configfile.html for info on setup files)
# The following files must be provided in source
#   src/helper_functions.for
#   src/xxdata_11.pyf
#   src/xxdata_15.pyf
#   

import os

extension_modules = {}
directory = 'src/xxdata_11'
sources = ['xxdata_11.for', 'xxrptn.for', 'i4unit.for',
    'i4fctn.for', 'xxword.for', 'xxcase.for', 'xfelem.for', 'xxslen.for',
     '../xxdata_11.pyf', '../helper_functions.for']
extension_modules['_xxdata_11'] = dict(sources=sources, directory=directory)

directory = 'src/xxdata_15'
sources = ['xxdata_15.for', 'xxrptn.for', 'xxmkrp.for', 'i4unit.for',
    'i4fctn.for', 'r8fctn.for', 'xxhkey.for', 'xxword.for', 'xxcase.for',
    'i4eiz0.for', 'xfelem.for', 'xxslen.for',
     '../xxdata_15.pyf', '../helper_functions.for']
extension_modules['_xxdata_15'] = dict(sources=sources, directory=directory)

def configuration(parent_package='', top_path=None):
    #
    # class numpy.distutils.misc_util.Configuration(package_name=None,
    #   parent_name=None, top_path=None, package_path=None, **attrs)[source]
    #   ->  Construct a configuration instance for the given package name.
    #       If parent_name is not None, then construct the package as a sub-package
    #       of the parent_name package. If top_path and package_path are None then they
    #       are assumed equal to the path of the file this instance was created in. The
    #       setup.py files in the numpy distribution are good examples of how to use
    #       the Configuration instance.

    # todict()[source] (method on Configuration class)
    #   ->  Return a dictionary compatible with the keyword arguments of distutils setup function.
      
    from numpy.distutils.misc_util import Configuration
    config = Configuration('src', parent_package, top_path)

    for module, values in extension_modules.items():
        directory = values['directory']
        sources = values['sources']
        sources = [os.path.join(directory, i) for i in sources]

        config.add_extension(module, sources)
    return config

if __name__ == '__main__':
    print('>> setup_fortran_programs.py called')
    print('\nBuilding fortran helper functions in src\n')

    from numpy.distutils.core import setup
    setup(**configuration(top_path='').todict())
    
    print('\n>> setup_fortran_programs.py exited')

