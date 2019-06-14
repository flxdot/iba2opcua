# pyIbaTools

A package containing often used python functions when analyzing ibaFiles

## Getting Started

Currently available functions:

* `getFiles(directory, file_type="", scan_sub_folders=True, verbose=False)`<br />
   Find all file of a specific type within a folder and its sub folders.
* `ibaReader(iba_file)`<br />
   Context manager which yields a ibaFilesLite.FileReader() which opened the wanted iba_file
* `ibaChannelReader(channel_, freader_)`<br />
   A context manager to read a iba channel from a file
* `getSortedIbaFiles(directory, scan_sub_folders=True, verbose=False)`<br />
   Find iba files within a given directory and sort the files by start time in ascending order
* `readIbaFile(iba_file, channels=None, names=None, tbase=0, delimiter=',', caching=True)`<br />
   Read the wanted channel from a iba_file with a specified tbase.
   The Caching is especially useful when reading data from a network drive.
* `get_channels(iba_file)`<br />
   Use this method to get a list of all available channels in the given file
* `get_channel_info(iba_file, channels=None)`<br />
   Use to get information about each channel.
* `checkFile(iba_file)`<br />
   Use this method to check if a iba file is valid and to retrieve some basic
   information like the sample rate and number of frames.
* `is_channel(chan, file)`<br />
   Use to check the existing of a certain channel in a given iba file.


### Prerequisites

This package only works with **python 3.5, 3.6 and 3.7** on **Windows** systems which have **ibaFilesLite > 6.0** installed!

**Note: This version is not compatible with ibaFiles written by ibaPDA, ibaAnalyzer >= 7.0**

### Installing

Simply clone this repository into your working directory and use it as package.

```python
import pyIbaTools.pyIbaTools as pyIbaTools
```

## Contributing

If you want to contribute to this project please follow the **[PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)**.

## Versioning

We use **[SemVer](http://semver.org/)** Versioning.

## Changelog

The complete changelog can be found here: **[CHANGELOG.md](http://svduseas098.dev.sms-group.com/FEFA/pyIbaTools/blob/master/CHANGELOG.md)**.

## Authors

* **Felix Fanghänel** - Package Maintainer - [Email](mailto:fefa@sms-group.com)

Special Thanks goes to **Stefan Klanke** - [Email](mailto:fefa@sms-group.com) for implementing ibaFilesPro.pyd and ibaFilesLite.pyd.
