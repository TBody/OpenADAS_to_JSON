# Program name: OpenADAS_to_JSON/json_database/build_json.py
# Author: Thomas Body
# Author email: tajb500@york.ac.uk
# Date of creation: 12 July 2017
# 

import numpy as np
import os

# Supported adf11 data classes.  See src/xxdata_11/xxdata_11.for for all the
# twelve classes.
# TBody: added charge exchange reccombination (15/7/15) in addition to classes supported by cfe316/atomic
adf11_classes = {
    'acd' : 1, # recombination coefficients
    'scd' : 2, # ionisation coefficients
    'ccd' : 3, # charge-exchange reccombination
    'prb' : 4, # continuum radiation power
    'plt' : 8, # line radiation power
    'prc' : 5, # charge-exchange recombination radiation
    'ecd' : 12 # effective ionisation potential
}

datatype_abbrevs = {
        'ionisation'           : 'scd',
        'recombination'        : 'acd',
        'cx_recc'              : 'ccd',
        'continuum_power'      : 'prb',
        'line_power'           : 'plt',
        'cx_power'             : 'prc',
        'ionisation_potential' : 'ecd',
}

# Invert the mapping of datatype_abbrevs
inv_datatype_abbrevs = {v: k for k, v in datatype_abbrevs.items()}

def check_cwd():
    # Checks that current working directory or its parent contains adas_data. If not, raises FileNotFoundError
    # If adas_data folder found, returns the contents as a list
    print('Current working directory is: {}'.format(os.getcwd()))
    if os.path.isdir('adas_data'):
        print('adas_data/ sub-directory found - proceeding')
    else:
        if os.path.isdir('../adas_data'):
            print('adas_data/ sub-directory found in parent directory')
            os.chdir("..")
            print('changing directory to {}'.format(os.getcwd()))
            print(' - proceeding')
        else:
            print('adas_data not found - check adas_data/ is a subdirectory of current working directory')
            raise(FileNotFoundError)
    
    return os.listdir(os.getcwd()+"/adas_data")

class Sniffer(object):
    """Inspector for a filename.
    << From cfe316/atomic-master/atomic/adf11.py >>

    Holds a split-apart adf11 filename.

    Attributes:
        file_ (str): full filename
        name (str): file's basename 'scd96r_li.dat'
        element (str): short element name 'li'
        year (str): short year name '96'
        class_ (str): file type 'scd'
        extension (str): should always be 'dat'
        resolved (bool): true for this example, but should always be False.
    """
    def __init__(self, file_):
        self.file_ = file_
        self.name = os.path.basename(file_)

        self._sniff_name()
        self._check()

    def _sniff_name(self):
        name, extension = self.name.split(os.path.extsep)

        type_, element = name.split('_')
        class_ = type_[:3]
        year = type_[3:]
        resolved = year.endswith('r')

        self.element = element
        self.year = year
        self.class_ = class_
        self.extension = extension
        self.resolved = resolved

    def _check(self):
        assert self.extension == 'dat'
        assert self.resolved == False, 'Metastable resolved data not supported.'

def read_xxdata_11(file_full_path,file_class):
    # Use fortran helper functions to read .dat file into a python-readable raw_return_value
    # Inputs: file_full_path -> the absolute path of the .dat file
    #         file_class    -> the adf11 class (i.e. 'acd', 'scd', etc)

    # <<will need to find the correct path for _xxdata_11 - may be either the version in atomic or in src>>
    
    from src import _xxdata_11

    # Some hard coded parameters to run xxdata_11.for routine.  The values have
    # been take from src/xxdata_11/test.for, and should be OK for all files.
    parameters = {
        'isdimd' : 200,
        'iddimd' : 40,
        'itdimd' : 50,
        'ndptnl' : 4,
        'ndptn' : 128,
        'ndptnc' : 256,
        'ndcnct' : 100
    }
    # Key to inputs (from xxdata_11.pdf)
    # type  | name   | description
    # (i*4) | iunit  | unit to which input file is allocated
    # (i*4) | iclass | class of data (numerical code) - see table below
    # ----------------------------------------------------------
    # use defaults (set in parameters) for everything below this
    # ----------------------------------------------------------
    # (i*4) | isdimd | maximum number of (sstage, parent, base)
    #       |        | blocks in isonuclear master files
    # (i*4) | iddimd | maximum number of dens values in 
    #       |        | isonuclear master files
    # (i*4) | itdimd | maximum number of temp values in 
    #       |        | isonuclear master files
    # (i*4) | ndptnl | maximum level of partitions
    # (i*4) | ndptn  | maximum no. of partitions in one level
    # (i*4) | ndptnc | maximum no. of components in a partition
    # (i*4) | ndcnct | maximum number of elements in connection vector

    iclass = adf11_classes[file_class]
    iunit = _xxdata_11.helper_open_file(file_full_path)
    raw_return_value =  _xxdata_11.xxdata_11(iunit, iclass, **parameters)
    _xxdata_11.helper_close_file(iunit)

    return raw_return_value

def extract_data_dict(raw_return_value,file_class,file_element,file_full_path):
    # Based on _convert_to_dictionary method of adf11.py
    # Extract information from ret.
    iz0, is1min, is1max, nptnl, nptn, nptnc, iptnla, iptna, iptnca, ncnct,\
    icnctv, iblmx, ismax, dnr_ele, dnr_ams, isppr, ispbr, isstgr, idmax,\
    itmax, ddens, dtev, drcof, lres, lstan, lptn = raw_return_value

    # Key to outputs (from xxdata_11.pdf)
        # type   | name       | description
        # (i*4)  | iz0        | nuclear charge
        # (i*4)  | is1min     | minimum ion charge + 1
        #        |            | (generalised to connection vector index)
        # (i*4)  | is1max     | maximum ion charge + 1
        #        |            | (note excludes the bare nucleus)
        #        |            | (generalised to connection vector index and excludes
        #        |            | last one which always remains the bare nucleus)
        # (i*4)  | nptnl      | number of partition levels in block
        # (i*4)  | nptn()     | number of partitions in partition level
        #        |            | 1st dim: partition level
        # (i*4)  | nptnc(,)   | number of components in partition
        #        |            | 1st dim: partition level
        #        |            | 2nd dim: member partition in partition level
        # (i*4)  | iptnla()   | partition level label (0=resolved root,1=
        #        |            | unresolved root)
        #        |            | 1st dim: partition level index
        # (i*4)  | iptna(,)   | partition member label (labelling starts at 0)
        #        |            | 1st dim: partition level index
        #        |            | 2nd dim: member partition index in partition level
        # (i*4)  | iptnca(,,) | component label (labelling starts at 0)
        #        |            | 1st dim: partition level index
        #        |            | 2nd dim: member partition index in partition level
        #        |            | 3rd dim: component index of member partition
        # (i*4)  | ncnct      | number of elements in connection vector
        # (i*4)  | icnctv()   | connection vector of number of partitions
        #        |            | of each superstage in resolved case
        #        |            | including the bare nucleus
        #        |            | 1st dim: connection vector index
        # (i*4)  | iblmx      | number of (sstage, parent, base)
        #        |            | blocks in isonuclear master file
        # (i*4)  | ismax      | number of charge states
        #        |            | in isonuclear master file
        #        |            | (generalises to number of elements in
        #        |            |  connection vector)
        # (c*12) | dnr_ele    | CX donor element name for iclass = 3 or 5
        #        |            | (blank if unset)
        # (r*8)  | dnr_ams    | CX donor element mass for iclass = 3 or 5
        #        |            | (0.0d0 if unset)
        # (i*4)  | isppr()    | 1st (parent) index for each partition block
        #        |            | 1st dim: index of (sstage, parent, base)
        #        |            |          block in isonuclear master file
        # (i*4)  | ispbr()    | 2nd (base) index for each partition block
        #        |            | 1st dim: index of (sstage, parent, base)
        #        |            |          block in isonuclear master file
        # (i*4)  | isstgr()   | s1 for each resolved data block
        #        |            | (generalises to connection vector index)
        #        |            | 1st dim: index of (sstage, parent, base)
        #        |            |          block in isonuclear master file
        # (i*4)  | idmax      | number of dens values in
        #        |            | isonuclear master files
        # (i*4)  | itmax      | number of temp values in
        #        |            | isonuclear master files
        # (r*8)  | ddens()    | log10(electron density(cm-3)) from adf11
        # (r*8)  | dtev()     | log10(electron temperature (eV) from adf11
        # (r*8)  | drcof(,,)  | if(iclass <=9):
        #        |            | 	log10(coll.-rad. coefft.) from
        #        |            | 	isonuclear master file
        #        |            | if(iclass >=10):
        #        |            | 	coll.-rad. coefft. from
        #        |            | 	isonuclear master file
        #        |            | 1st dim: index of (sstage, parent, base)
        #        |            | 		 block in isonuclear master file
        #        |            | 2nd dim: electron temperature index
        #        |            | 3rd dim: electron density index
        # (l*4)  | lres       | = .true. => partial file
        #        |            | = .false. => not partial file
        # (l*4)  | lstan      | = .true. => standard file
        #        |            | = .false. => not standard file
        # (l*4)  | lptn       | = .true. => partition block present
        #        |            | = .false. => partition block not present

    # Make a new blank dictionary, data_dict
    data_dict = {}
    # Save data to data_dict
    data_dict['charge']                  = iz0                            # nuclear charge
    data_dict['log_density']             = ddens[:idmax]                  # log10(electron density(cm-3)) from adf11
    data_dict['log_temperature']         = dtev[:itmax]                   # log10(electron temperature (eV) from adf11
    data_dict['number_of_charge_states'] = ismax                          # number of charge states in isonuclear master file (generalises to number of elements in connection vector)
    data_dict['log_coeff']               = drcof[:ismax, :itmax, :idmax]  # if(iclass <=9):
                                                                          #     log10(coll.-rad. coefft.) from isonuclear master file
                                                                          # if(iclass >=10):
                                                                          #     coll.-rad. coefft. from isonuclear master file
                                                                          # 1st dim: index of (sstage, parent, base) block in isonuclear master file
                                                                          # 2nd dim: electron temperature index
                                                                          # 3rd dim: electron density index

    data_dict['class']   = file_class                                     # adf11 class (i.e. 'acd', 'scd', ...)
    data_dict['element'] = file_element                                   # element symbol (i.e. 'c' for carbon, ...)
    data_dict['name']    = file_full_path                                 # full path to the data file

    # convert everything to SI + eV units
    data_dict['log_density'] += 6 # log(cm^-3) = log(10^6 m^-3) = 6 + log(m^-3)
    # N.b. the ecd (ionisation potential) class is already in eV units.
    if data_dict['class'] != 'ecd':
        data_dict['log_coeff'] -= 6 # log(m^3/s) = log(10^-6 m^3/s) = -6 + log(m^3/s)
    else:
        data_dict['log_coeff'] = np.log10(data_dict['log_coeff'][1:])

    return data_dict

def data_dict_types(data_dict):
    # Print out the type of each element in data_dict (helps to identify which ones need to be jsonified)
    for key, element in data_dict.items():
        print("data key: {:30} data type: {:30}".format(key,str(type(element))))

def store_as_JSON(data_dict,file_basename):
    from copy import deepcopy
    import json
    
    # Need to 'jsonify' the numpy arrays (i.e. convert to nested lists) so that they can be stored in plain-text
    # Deep-copy data to a new dictionary and then edit that one (i.e. break the data pointer association - keep data_dict unchanged in case you want to run a copy-verify on it)
    
    data_dict_jsonified = deepcopy(data_dict)

    numpy_ndarrays = [];
    for key, element in data_dict.items():
        if type(element) == np.ndarray:
            # Store which keys correspond to numpy.ndarray, so that you can de-jsonify the arrays when reading
            numpy_ndarrays.append(key)
            data_dict_jsonified[key] = data_dict_jsonified[key].tolist()

    data_dict_jsonified['numpy_ndarrays'] = numpy_ndarrays

    # Encode help
    data_dict_jsonified["help"] = "JSON file corresponding to an OpenADAS data file\nCreated by TBody/OpenADAS_to_JSON/build_json.py/store_as_JSON\nDocumentation at https://github.com/TBody/OpenADAS_to_JSON"
    
    # <<Use original filename, except with .json instead of .dat extension>>
    with open('json_data/{}.json'.format(file_basename),'w') as fp:
        json.dump(data_dict_jsonified, fp, sort_keys=True, indent=4)


def retrive_from_JSON(file_name):
    # Inputs - a JSON file corresponding to an OpenADAS .dat file
    # file_name can be either relative or absolute path to JSON file
    # Must have .json extension and match keys of creation
    # Not need for the .dat -> .json conversion, but included for reference
    import json
    from warnings import warn
    from copy import deepcopy
    import numpy as np

    file_extension  = file_name.split('.')[-1] #Look at the extension only (last element of split on '.')
    if file_extension != 'json':
        raise NotImplementedError('File extension (.{}) is not .json'.format(file_extension))

    with open(file_name,'r') as fp:
        data_dict = json.load(fp)

    if set(data_dict.keys()) != {'charge','class','element', 'help','log_coeff','log_density','log_temperature','name','number_of_charge_states'}:
        warn('Imported JSON file {} does not have the expected set of keys - could result in an error'.format(file_name))

    # Convert jsonified numpy.ndarrays back from nested lists
    data_dict_dejsonified = deepcopy(data_dict)

    for key in data_dict['numpy_ndarrays']:
        data_dict_dejsonified[key] = np.array(data_dict_dejsonified[key])

    # print(data_dict['help'])

    return data_dict_dejsonified



if __name__ == '__main__':
    print('>> build_json.py called')
    print('\nConverting .dat files to .json files\n')
    
    # Check that adas_data can be found relative to current working directory
    # If adas_data folder found, returns the contents as a list
    adas_data_files = check_cwd()

    # Iterate over each file in the directory
    for adas_data_file in adas_data_files:
        file_basename  = adas_data_file.split('.')[0] #remove the .dat extension
        file_full_path = os.path.realpath("adas_data/"+adas_data_file)
        
        # Use Sniffer object to break apart filename to extract information. Also performs basic checks.
        s = Sniffer(file_full_path)
        if s.class_ not in adf11_classes:
            print('{} has class {} - not recognised as ADF11 class'.format(adas_data_file,s.class_))
            print('Skipping - will not produce a JSON file for this data')
            continue
            # raise NotImplementedError('Unknown adf11 class: %s' % s.class_) #If you make sure every file in adas_data gets a JSON made for it by this program
        else:
            # Extract the data from the Sniffer class
            file_element   = s.element
            file_year      = s.year
            file_class     = s.class_
            file_extension = s.extension
            file_resolved  = s.resolved
            # Could add a check here to see if the filename can be recreated

        # Read the fortran-formatted data file with the fortran helper functions
        raw_return_value = read_xxdata_11(file_full_path,file_class)

        # Extract a dictionary of useful data from 
        data_dict = extract_data_dict(raw_return_value,file_class,file_element,file_full_path)

        store_as_JSON(data_dict,file_basename)

    print('\n>> setup_fortran_programs.py exited')



# Full table of ADF11 types (for reference)
    # class index | type | GCR data content
    # ------------\------\--------------------------------
    # 1           | acd  |  recombination coeffts
    # 2           | scd  |  ionisation coeffts
    # 3           | ccd  |  CX recombination coeffts
    # 4           | prb  |  recomb/brems power coeffts
    # 5           | prc  |  CX power coeffts
    # 6           | qcd  |  base meta. coupl. coeffts
    # 7           | xcd  |  parent meta. coupl. coeffts
    # 8           | plt  |  low level line power coeffts
    # 9           | pls  |  represent. line power coefft
    # 10          | zcd  |  effective charge
    # 11          | ycd  |  effective squared charge
    # 12          | ecd  |  effective ionisation potential



























