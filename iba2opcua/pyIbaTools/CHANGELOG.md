# pyIbaTools - Changelog

### 0.0.10 (2019-06-03)

* function `get_channels(iba_file, ids=None)`

    - Fixed minor bug that added channel name as a list of single characters instead of a single string (only appeared when ids where passed).

### 0.0.9 (2019-05-13)

* function `getFiles(directory=None, file_type='dat', scan_sub_folders=True, verbose=False)`
 
  - input file_type may be input with or without the leading dot.
  - default file_type is 'dat'

## 0.0.8 (2019-04-18)

* function `getFiles(directory=None, file_type='', scan_sub_folders=True, verbose=False)`

  - Slight performance improvement. Also directory is now an optional input parameter.
  - Added file_name parameter to define file name (or parts of it) when searching for files.
  
* function `getSortedIbaFiles(directory, scan_sub_folders=True, verbose=False)`

  - Gutted function into new function 'sortIbaFiles' and 'getFiles'
  
* function `sortIbaFiles(iba_files)`

  - Added this function.

## 0.0.7 (2019-04-17)

* function `readIbaFiles(iba_file_list, channels=None, names=None, tbase=0, delimiter=',')`

  - Added this function to receive a single pandas DataFrame with the collected data of all files given in iba_file_list.

  
* function `get_channels(iba_file, ids=None)`<br />

  - Fixed a bug with comparing channel ids.
  
* function `__read_channel__(reader, iba_file, channel, tbase, clk, frames, ignore=False)`<br />

  - Updated functions description.

## 0.0.6 (2019-03-15)

* function `readIbaFile(iba_file, channels=None, names=None, tbase=0, delimiter=',', caching=True, ignore=False)`<br />

  - Extracted preprocessing of channels and names and put it into seperate function (__declaraction_check__).
  - Typo fix
  
* function `__declaration_check__(iba_file, channels, names, delimiter)`<br />
  - Added this function to handle channels and names inputs.
  
* function `get_channels(iba_file, ids=None)`<br />

  - Modified this function to return only channel names of specific channels (given by input ids).

## 0.0.5 (2019-03-15)

* function `readIbaFile(iba_file, channels=None, names=None, tbase=0, delimiter=',', caching=True, ignore=False)`<br />

  - Added optional ignore parameter.
  - Modified to work with a list of ids for a single channel.
    - The list will be looped and the first channel with valid data will be used.
    - This is good if the id of a certain signal is changing over time.

* function `__read_channel__(reader, iba_file, channel, tbase, clk, frames, ignore=False)`<br />

  - Added optional ignore parameter accordingly.
  
## 0.0.4 (2019-03-06)

* function `__read_numeric_channel__(chan_reader, tbase, clk)`<br />

  - Modified to make sure that only 1-dimensional data is returned.

## 0.0.3 (2018-01-25)

### Added (1 Change)

+ function `get_channel_info(iba_file, channels=None)`<br />
   Use to get information about each channel.

## 0.0.2 (2019-01-24)

### Added (1 Changes)

* function `is_channel(chan, file)`<br />
  Use to check the existing of a certain channel in a given iba file.
  
### Changed (1 Changes)

* function `readIbaFile(iba_file, channels=None, names=None, tbase=0, delimiter=',', caching=True)`<br />
  - Added possibility to cache the file
  - Added support of TextChannels
  - added the ability to define channels/names as single line strings delimited by a delimiters
  - added the ability to define channels/names by passing a `dict()` to the channels input. The keys are interpreted a channel names and the values are the desired data frame columns names
  - function will raise `ChannelNotFoundError`, `IbaFileDamagedError`, `IbaFileNotCompleteError` or `DataStackingError`
  
## 0.0.1 (2018-08-30)

### Added (4 Changes)

* function `getFiles(directory, file_type="", scan_sub_folders=True, verbose=False)`<br />
  obtain a list of paths of files within a folder and its subfolders
* function `getSortedIbaFiles(directory, scan_sub_folders=True)`<br />
  obatin a list of iba files within a folder and its subfolders sorted by their starttime in ascending order
* context manager  `ibaReader(iba_file)`<br />
  conveniently load and read data from iba files
* function `readIbaFile(iba_file, channel, names, tbase=0)`<br />
  load a iba file with a custom time base
