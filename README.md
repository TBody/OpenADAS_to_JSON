# OpenADAS to JSON converter
---
## Acknowledgments

The majority of this code is based on the excellent OpenADAS analysis tool provided at [_cfe316/atomic_](https://github.com/cfe316/atomic). Main changes were to convert the code into python3 and add a JSON read/write function.

### Purpose of this code

This code is intended to convert OpenADAS .dat files into .json files, which are more easily integrated into larger programs. This is performed in a python3 script which calls fortran-77 helper functions to process the .dat file.

**Note on install/uninstall**
The program is controlled with a basic `make` system, which is simply used to execute the python3 programs in the desired order. Unless the `JSON_database_path` variable in the `makefile` is modified, the code will not modify anything outside of the `OpenADAS_to_JSON` folder so can be safely deleted simply by removing this directory.
# Requirements
* An installation of `python3` with the Scipy stack, aliased to `python`
    - run `alias python=python3` if on a `bash` terminal to alias, if it hasn't already been done for you (try run `python` from terminal and see that it loads python3 with the Scipy stack). N.b. unless you add this command to your `~/.bash-profile` it will revert to orginal when you close your terminal.
    - Alternatively, modify the `python = python` line in the `makefile` header to point to your python3 installation.
* A fortran compiler such as `gfortran`
* `gmake` to run the make commands
#Running the code
*Quickstart:* run **`make json_update`**, let the code run for a minute and look in `json_database/json_data` for `.json` files corresponding to ADAS-11 files for your specified element-year pairs. This is essentially the same as running `make fetch && make setup && make json`.

There are 3 main functions of this code;

1. **`make fetch`**
  - Fetch `.dat` files from [_OpenADAS_](http://open.adas.ac.uk) and copy them into a directory at `json_database/adas_data`
  - Files are downloaded for the (*element*, *year(shorthand)*) pairs supplied as the `element=` variable in the `makefile` header, or alternatively as the `--elements=$(elements)` argument supplied to `fetch_adas_data.py`.
  - Modifying the `makefile` header is the preferred method for setting this command.
  - Be careful with the syntax if setting this variable to a custom list. The [command-line argument interpreter](#python_syntax) is listed below in case you run into errors.

2. **`make setup`**
  - Build the fortran helper files in `src`.
  - Requires a fortran compiler such as `gfortran`
  - Will probably return a huge amount of warnings if you run with the `make` variable `verbose = true`. To pipe these into `setup_fortran_programs_log.txt` change to `verbose = false` (to date - have not found that these errors affect the program)

3. **`make json`**

  - Uses the fortran helper functions to read the .dat files, and then writes them into json files which are saved into `json_database/json_data`. The file base-name is unchanged, but the extension is changed from `.dat` to `.json`. i.e. `scd96_c.dat` (the ADF-11 effective ionisation rate-coefficients for Carbon from 1996 in case you were curious) will be written to `scd96_c.dat`

N.b. **`make clean`** and **`make clean_refetch`**

  - To revert to the clean-install state run `make clean_refetch`.
  - To clean out the functions from `make setup` but keep the downloaded `.dat` and processed `.json` files run `make clean`.

##<a name="python_syntax"></a> Code for reading the command line argument 
For interpreting list supplied to `fetch_adas_data.py` via `--elements=$(elements)` 

If the code is returning errors while you are trying to define your own list of (*element*, *year(shorthand)*) pairs in the `makefile` header then they will almost certainly be coming from `fetch_adas_data.py` (line 225-245). This is included to check expected syntax (feel free to edit, or even comment out this whole section and manually define the list-of-tuples via `elements_years = [('carbon', 96),('nitrogen', 96)]` (see line 253)) or similar.
```python
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
```

##<a name="reader"></a> Code for unpacking data from the JSON files
The key outputs are

* `log_coeff[charge_state][plasma_temperature][plasma_density]` which stores the base-10 logarithm of the rate coefficient (in m^3/s).
* `charge_state`, either 0, 1, ... Z-1 (for electron-bound interactions) or 1, 2, ..., Z (for charged-target interactions). Note that this depends on the process you're considering!
* `log_temperature` which stores the temperature points for which a `log_coeff` point is given.
* `log_density` which stores the density points for which a `log_coeff` point is given.

###python3

*To return a JSON object*
```python
def retrieveFromJSON(file_name):
  # Inputs - a JSON file corresponding to an OpenADAS .dat file or SD1D output file
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

  if  set(data_dict.keys()) != {'numpy_ndarrays', 'charge', 'help', 'log_density', 'number_of_charge_states', 'log_temperature', 'element', 'log_coeff', 'name', 'class'}:
    warn('Imported JSON file {} does not have the expected set of keys - could result in an error'.format(file_name))

  # Convert jsonified numpy.ndarrays back from nested lists
  data_dict_dejsonified = deepcopy(data_dict)

  for key in data_dict['numpy_ndarrays']:
    data_dict_dejsonified[key] = np.array(data_dict_dejsonified[key])

  return data_dict_dejsonified
```

*To copy to variables*
```python
atomic_number   = data_dict['charge']
element         = data_dict['element']
adf11_file      = filename
log_temperature = data_dict['log_temperature']
log_density     = data_dict['log_density']
log_coeff       = data_dict['log_coeff']

splines = []
for k in range(atomic_number):
  x = log_temperature
  y = log_density
  z = log_coeff[k]
  splines.append(RectBivariateSpline(x, y, z))
```

###C++
Relies on the (frankly awesome) 'JSON for modern C++' library by nlohmann.
Github: [github.com/nlohmann/json](https://github.com/nlohmann/json)
You need to include the [json.hpp](https://github.com/nlohmann/json/blob/develop/src/json.hpp) header file in the same directory as your source at compile-time.

*To return a JSON object*

```cpp
#include <string>
#include <fstream>

#include "json.hpp"
using json = nlohmann::json;

using namespace std; //saves having to prepend std:: onto common functions

json retrieveFromJSON(string path_to_file){
// Do not pass path_to_file by reference - results in error!
// Reads a .json file given at path_to_file
// Uses the json module at https://github.com/nlohmann/json/
// This relies upon the "json.hpp" header which must be included in the same folder as the source
  
// Open a file-stream at path_to_file
ifstream json_file(path_to_file);
// Initialise a json file object at j_object
json j_object;
json_file >> j_object;
return j_object;
};
```

*To copy to variables*
```cpp
json data_dict = retrieveFromJSON(filename);

atomic_number   = data_dict["charge"];
element         = data_dict["element"];
adf11_file      = filename;

vector<vector< vector<double> > > extract_log_coeff = data_dict["log_coeff"];
vector<double> extract_log_temperature = data_dict["log_temperature"];
vector<double> extract_log_density = data_dict["log_density"];
// Doing this as a two-step process - since the first is casting JSON data into the stated type.
// The second copies the value to the corresponding RateCoefficient attribute
log_coeff = extract_log_coeff; // log10 of rate coefficent in [m3/s]
log_temperature = extract_log_temperature; // log10 of temperature in [eV]
log_density = extract_log_density; // log10 of density in [m^-3]
// Would be great to turn this into a bivariate interpolation function -- if you find a good header-only package for this please get in touch
```






