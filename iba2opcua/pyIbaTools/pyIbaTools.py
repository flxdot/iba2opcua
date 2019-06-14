"""The pyIbaTools package contains several function which help you to analyze ibaFiles.

Currently available functions:

* `getFiles(directory=None, file_type="", file_name="*", scan_sub_folders=True, verbose=False)`
   Find all file of a specific type within a folder and its sub folders.
* `ibaReader(iba_file)`
   Context manager which yields a ibaFilesLite.FileReader() which opened the wanted iba_file
* `ibaChannelReader(channel_, freader_)`
   A context manager to read a iba channel from a file
* `getSortedIbaFiles(directory, scan_sub_folders=True, verbose=False)`
   Find iba files within a given directory and sort the files by start time in ascending order
* `readIbaFile(iba_file, channels=None, names=None, tbase=0, delimiter=',', caching=True, ignore=False)`
   Read the wanted channel from a iba_file with a specified tbase.
   The Caching is especially useful when reading data from a network drive.
* `readIbaFiles(iba_file_list, channels=None, names=None, tbase=0, delimiter=',')`
   Read each file from the given list of files and try to stack them.
* `get_channels(iba_file)`
   Use this method to get a list of all available channels in the given file
* `get_channel_info(iba_file, channels=None)`
   Use to get information about each channel.
* `checkFile(iba_file)`
   Use this method to check if a iba file is valid and to retrieve some basic
   information like the sample rate and number of frames.
* `is_channel(chan, file)`
  Use to check the existing of a certain channel in a given iba file.

"""
import os
from datetime import datetime
import re
import glob
import numpy as np
import pandas as pd
from contextlib import contextmanager
from pyIbaTools import ibaFilesLite

class ChannelNotFoundError(Exception):
    """The ChannelNotFountError will be raised when ever a given channel was not found."""
    pass


class IbaFileDamagedError(Exception):
    """The IbaFileDamagedError will be thrown when ever an iba file seems to be damaged."""
    pass


class IbaFileNotCompleteError(Exception):
    """The IbaFileNotCompleteError will be thrown when ever a iba files open is not completely written by the ibaPDA."""
    pass


class DataStackingError(Exception):
    """The DataStackingError will be thrown when ever the data stacking fails."""
    pass


class IbaFileIsCurrentlyWrittenError(Exception):
    """The IbaFileIsCurrentlyWrittenError will be raised when ever an iba file is opened which is currently written by
    the ibaPDA."""
    pass


def getFiles(directory=None, file_type='dat', file_name='*', scan_sub_folders=True, verbose=False):
    """Use to find files of a certain kind within a folder and its sub folders.

    :param directory: (string, optional) Path to the directory which shall be searched
    :param file_type: (string, optional) File extension of file type which shall be found, e.g. dat for ibaFiles.
    If the string is empty every file will be returned. 
    :param file_name: (string, optional) Files name or parts of it. Use * or ? to denote unknown characters. 
    :param scan_sub_folders: (bool, optional) Specifies whether the sub folders shall be scanned to. Default: True
    :param verbose: (bool, optional) If set to true the current executed path displayed in the command line output
    :return: List of full qualified paths to the iba files
    """

    # should local directory be searched?
    if directory is None:
        directory = os.getcwd()
        
    # create list to collect files
    files_found = list()

    # generate verbose output
    if verbose:
        print(directory)

    # if the user input a file type with the leading .
    # remove it ;-)
    if str(file_type).startswith('.'):
        file_type = file_type[1:]

    # get content of current folder
    files_found += glob.glob(os.path.join(directory, file_name + '.' + file_type))

    # should all subfolders be searched?
    if scan_sub_folders:
        # find all 1st subfolders
        sub_folders = [folder.path for folder in os.scandir(directory) if folder.is_dir()]
        # loop over them
        for sub_folder in sub_folders:
            # dive into next subfolder
            files_found += getFiles(directory=sub_folder, file_type=file_type, file_name=file_name, scan_sub_folders=scan_sub_folders, verbose=verbose)
            
    # return files
    return files_found


def getSortedIbaFiles(directory, scan_sub_folders=True, verbose=False):
    """Use this function to find all iba files in a directory and its sub directories. The function will sort all found
    files by their start time in ascending order.

    :param directory: (string, mandatory) path to the iba files
    :param scan_sub_folders: (bool, optional) specifies whether the sub folders shall be scanned to. Default: True
    :param verbose: (bool, optional) If set to true the current executed path displayed in the command line output
    :return: list of iba files sorted by date in asc order
    """

    # get all iba files
    iba_files = getFiles(directory=directory, file_type='dat', scan_sub_folders=scan_sub_folders, verbose=verbose)

    # sort them chronologically
    sorted_iba_files = sortIbaFiles(iba_files)
    
    # return sorted list
    return sorted_iba_files


def sortIbaFiles(iba_files):
    """
    Open each iba file given in iba_files and get their start time. Sort all given files by this time and return a list of sorted files.
    
    :param iba_files: (list, mandatory) List of path to iba files.
    :return: List of chronological sorted iba files.
    """
    # more elegant way
    sort_dict = dict()
    for iba_file in iba_files:
        # read iba file
        try:
            sort_dict[iba_file] = get_start_time(iba_file)
        except:
            print('Could not load iba file {}. Marking it as damaged.'.format(iba_file))
            continue
        
    # return sorted list by date in asc order
    return sorted(sort_dict, key=sort_dict.get)            


@contextmanager
def ibaReader(iba_file):
    """A context manager to help loading iba files. It will yield the actual reader which opened the iba file.

    :param iba_file: (string, mandatory) path to the iba file to load
    :return: yields a ibaFilesLite.FileReader with the desired file opened
    """
    # make sure to use \\ instead of /
    iba_file = os.path.normpath(iba_file)

    # check if file is currently written by the ibaPDA
    if ibaFilesLite.isCurrentPDA(iba_file):
        raise IbaFileIsCurrentlyWrittenError(
            'You are about to read a iba file which is currently written by the ibaPDA.')

    # open the reader
    reader = ibaFilesLite.FileReader()
    try:
        reader.Open(iba_file)
    except RuntimeError as e:
        if not os.path.isfile(iba_file):
            raise FileNotFoundError('File {0} does not exist or can not be accessed.'.format(iba_file))
        else:
            raise e

    # yield the reader
    yield reader

    # close the file again
    reader.Close()


@contextmanager
def ibaChannelReader(channel_, freader_):
    """A context manager to read a iba channel from a file

    :param channel_: (mandatory) either ibaFilesLite.ChannelId, the channel id [0:0], channel name as string
    :param freader_: (mandatory, ibaFilesLite.FileReader) the file read used to read the channel.
    :return: yields the channel read
    """

    yield __get_iba_channel_reader__(channel_, freader_)


def readIbaFile(iba_file, channels=None, names=None, tbase=0, delimiter=',', caching=True, ignore=False):
    """Use this function to read an iba file.

    :param iba_file: (mandatory, string) Path to the iba file.
    :param channels: (optional, string or list of strings or dict) Contains channel identifications.
    :param names: (optional, string or list of strings) List that defines the names of the extracted channels.
    :param tbase:  (optional, int) Defines timebase in that the data will be returned.
    :param delimiter: (optional, string) Defines the delimiter if the channels or names input is a single string.
    :param caching: (optional, bool) Flag whether to cache to file or not
    :param ignore: (optional, bool) if ignore is set False, channels that could not be found will raise an error.
    :return: (pandas.DataFrame) The actual data represented as pandas data frame


    Note(1): If tbase is 0 the original (minimal) timebase is returned. If e.g. tbase is 0.5,
             than a value for every 0.5s of the data is returned.

    Note(3): channels and names can also be given as a single string. if that is the case, the given delimiter is
    expected.

    Note(4): If channels is '' or '*', all channels will be extracted. This could result in very large DataFrame!

    Note(5): If names is '' or '*', the original channel names will be returned.

    Note(6): If channels is a dict, the keys will act as channel ids and values as desired channel names.
             In this case the parameter names will be ignored.

    Note(7): channels can either contain the precise name of the desired channel (e.g. 'ActCastingSpeed')
             in the iba file, or the actual id (e.g. '3:12').

    This function is originally written by Frank Eschner (nerf@sms-group.com)"""

    # check given channels and names and format them if necessary
    (channels, names) = __declaration_check__(iba_file, channels, names, delimiter)

    # cache the iba file
    if caching and len(channels) > 10:
        __cache_prep__(iba_file)

    with ibaReader(iba_file) as reader:

        # get clk and number of frames from the iba file and also check if the values are valid
        clk, frames = __check_file__(reader, iba_file)

        # get some time data to compute time array with new number of frames
        start_time = pd.Timestamp(reader.GetStartTime())
        end_time = start_time + pd.Timedelta(seconds=(clk * (frames - 1)))

        # create time array
        time_data = np.linspace(start_time.value, end_time.value, frames)

        # only take data points at a certain timebase
        if tbase != 0:
            time_data = time_data[::int(tbase / clk)]

        # convert time data to actual pd Timestamp
        time_data = pd.to_datetime(time_data)

        # reset collected file data
        df = pd.DataFrame()

        # loop over channels
        for num, chn in enumerate(channels):
            # is given channel a list of channels?
            if isinstance(chn, list):
                # only one of the given channels should contain data. find it.
                any_channel_found = False
                for alt_chn in chn:
                    # get the data of the current channel
                    try:
                        chan_data = __read_channel__(reader=reader, iba_file=iba_file, channel=alt_chn,
                                                     tbase=tbase, clk=clk, frames=frames)
                        # we could load the data. yay :-)
                        any_channel_found = True
                        # stop trying the rest of the alternative channels
                        break
                    except ChannelNotFoundError:
                        # no problem just try the next channel
                        continue
                    except Exception as e:
                        # oh... something else bad happened
                        raise e

                # has any of the alternative channels been found?
                if not any_channel_found and not ignore:
                    raise ChannelNotFoundError('Could not find any of the specified channel alternatives {0} '
                                               'in ibaFile {1}.'.format(', '.join(chn), iba_file))
            else:
                # get the data of the current channel
                try:
                    chan_data = __read_channel__(reader=reader, iba_file=iba_file, channel=chn,
                                                 tbase=tbase, clk=clk, frames=frames)
                except ChannelNotFoundError as e:
                    if ignore:
                        continue
                    else:
                        raise e

            # add the data to the data frame
            try:
                df[names[num]] = chan_data
            except Exception:
                raise DataStackingError('Failed to add channel {0} to DataFrame.'.format(chn))

        # create data frame and concat them
        # so far I did not find any better solution in order to keep the date times and not converting them to
        # floats
        tf = pd.DataFrame(data=time_data, columns=['Time'])
        df = pd.concat([tf, df], axis=1)

    # TODO: check if DataFrame has been filled properly
    return df

def readIbaFiles(iba_file_list, channels=None, names=None, tbase=0, delimiter=','):
    """Use this method to receive a single pandas DataFrame with data from all given iba files.

    :param iba_file_list: (mandatory, list of strings) Path to each file.
    :param channels: (optional, string or list of strings or dict) Contains channel identifications.
    :param names: (optional, string or list of strings) List that defines the names of the extracted channels.
    :param tbase:  (optional, int) Defines timebase in that the data will be returned.
    :param delimiter: (optional, string) Defines the delimiter if the channels or names input is a single string.
    :return: (pandas DataFrame) Containing the desired -stacked- data.
    
    Note(1): If channels is a dict, the keys will act as channel ids and values as desired channel names.
             In this case the parameter names will be ignored.
    
    Note(2): channels can either contain the precise name of the desired channel (e.g. 'ActCastingSpeed')
             in the iba file, or the actual id (e.g. '3:12').
    
    Note(3): If some of the given files are missing some channels, these values will be filled with None's.
    """
    
    # create list to collect dataframes
    dfs = []
    # create list to collect channel names of each file
    columns = []
    
    # loop over given list of files
    for file in iba_file_list:
            # get data from single file
            temp_df = readIbaFile(iba_file=file, channels=channels, names=names, 
                                  tbase=tbase, delimiter=delimiter, caching=True, ignore=True)
            
            # add copy of dataframe to list
            dfs = dfs + [temp_df.copy()]
            # add columns to list
            columns = columns + list(temp_df.columns)
       
    # get all possibly available channels
    all_columns = list(set(columns))
    
    # check each dataframe for having all required columns.
    for df in dfs:
        # get missing channels
        missing_columns = list(set(all_columns) - set(df.columns.values))
        # loop over missing columns
        for column in missing_columns:
            # print msg
            print('%s was missing in a DataFrame!' % column)
            # add missing column
            df[column] = None
    
    # stack all dataframes to one and return it
    return pd.concat(dfs, ignore_index=True)
        

def get_channels(iba_file, ids=None):
    """Use this method to get a list of all available channels in the given file

    :param iba_file: (mandatory, string) the path to the iba file
    :param ids: (optional, list of strings) contains ids of all channels that shall be read
    :return: list of channels
    """
    with ibaReader(iba_file) as reader:
        # get all channel names
        infos = reader.EnumerateChannels()
        # are there specific channel names that should be found?
        if ids is not None:
            # create empty channel list to collect names
            channels = []
            # extract only specific channel names
            for cid in ids:
                # add channel name to list if channel id appears in info
                for info in infos:
                    # does either the channel id or the channel name match?
                    if cid in str(info[0])[3:] or cid == info[1]:
                        channels += [info[1]]
        else:
            # extract all channel names and put them into a list
            channels = [info[1] for info in infos]

    return channels


def get_channel_info(iba_file, channels=None):
    """Use to get information about each channel.

    :param iba_file: (mandatory, string) the path to the iba file
    :param channels: (optional, list or string) list of channels to check
    :return: list dict with the information of each channel
    """

    if channels is None:
        channels = get_channels(iba_file)
    elif isinstance(channels, str):
        channels = [channels]

    # loop over each channel
    channels_info = dict()

    with ibaReader(iba_file) as reader:

        file_info = reader.QueryInfos()

        for channel in channels:
            chan_info = dict()
            # get the channel reader
            try:
                chan_reader = __get_iba_channel_reader__(channel, reader)
            except RuntimeError:
                continue

            # get channel type
            if chan_reader.IsText:
                chan_info['type'] = 'text'
            elif chan_reader.IsDigital:
                chan_info['type'] = 'digital'
            elif chan_reader.IsAnalog:
                chan_info['type'] = 'analog'

            # get module
            chan_info['module_no'] = chan_reader.ChannelId.Module
            chan_info['module'] = file_info['Module_name_{}'.format(chan_reader.ChannelId.Module)]

            # get the channel id
            chan_info['no'] = chan_reader.ChannelId.Nr
            chan_info['id'] = chan_reader.ChannelId.Label

            # get all other infos
            chan_info.update(chan_reader.QueryInfos())

            channels_info[channel] = chan_info

    return channels_info


def is_channel(chan, file):
    """Use to check the existing of a certain channel in a given iba file.

    :param chan: (mandatory, string) name of the channel
    :param file: (mandatory, string) path to the iba file
    """

    try:
        chanReader = None
        with ibaReader(file) as reader:
            chanReader = __get_iba_channel_reader__(chan, reader)
        return isinstance(chanReader, ibaFilesLite.ChannelReader)
    except:
        return False


def checkFile(iba_file):
    """Use this method to check if a iba file is valid and to retrieve some basic information like the sample rate and
    number of frames.

    :param iba_file: (mandatory, string) the path to the iba file
    :return: (clk, frames) Tuple containing the sample rate (clk), number of frames (frames)
    message if the sample rate of frames could not be found or the file is not written completely.
    """
    with ibaReader(iba_file) as reader:
        return __check_file__(reader, iba_file)


def get_start_time(file):
    """Returns the start time of the iba file as datetime

    :param file: (madatory, string) path to the iba files
    :return: datenum
    """

    # read the file
    with open(file, "rb") as f:
        # get size of file
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(0)

        # read lines
        cur_line = f.readline()
        line_idx = 1
        while not cur_line.startswith(b'starttime:'):
            cur_line = f.readline()
            line_idx += 1
            if line_idx > 20:
                break

        # was the start time line read?
        if f.tell() == file_size or line_idx > 20:
            with ibaReader(file) as reader:
                return reader.GetStartTime()

        # convert byte str to utf-8 str
        start_time = cur_line.decode().strip().replace('starttime:', '')

        try:
            return datetime.strptime(start_time, '%d.%m.%Y %H:%M:%S.%f')
        except:
            return datetime.strptime(start_time, '%d.%m.%Y %H:%M:%S')


def __check_file__(reader, iba_file):
    """Internal function to get the sample rate and the number of frames for a specific file. It also checks if the file
    is valid.

    :param reader: (mandatory, ibaFilesLite.FileReader)
    """

    # check if file has been opened
    close_file = False
    if not reader.IsOpen():
        close_file = True
        reader.Open(iba_file)

    try:
        # get original (max) clk rate of file
        clk = float(reader.QueryInfoByName('clk'))
        frames = int(reader.QueryInfoByName('frames'))

        # make sure to close the reader again if it was closed in the beginning
        if close_file:
            reader.Close()
    except:
        # make sure to close the reader again if it was closed in the beginning
        if close_file:
            reader.Close()

        # check which error to raise
        if not os.path.isfile(iba_file):
            raise FileNotFoundError(
                'It seems like ibaFile {0} has been removed after the reading has started'.format(iba_file))
        else:
            raise IbaFileDamagedError('ibaFile {0} seems do be damaged.'.format(iba_file))

    # is file damaged?
    if frames >= 1000000000:
        # make sure to close the reader again if it was closed in the beginning
        if close_file:
            reader.Close()

        raise IbaFileNotCompleteError(
            'It looks like the ibaPDA did not finish writting the ibaFile {0}.'.format(iba_file))

    # everything went well
    return clk, frames


def __get_iba_channel_reader__(channel_, freader_):
    """An internal function to obtain the channel reader based on a given channel.

    :param channel_: (mandatory) either ibaFilesLite.ChannelId, the channel id [0:0], channel name as string
    :param freader_: (mandatory, ibaFilesLite.FileReader) the file read used to read the channel.
    :return: yields the channel read
    """

    # is the current channel a valid channel id?
    if type(channel_) == ibaFilesLite.ChannelId:
        # id is valid!
        return freader_.QueryChannel(channel_)
    elif re.match("[0-9]*[.:][0-9]*", channel_):
        # id is valid!
        return freader_.QueryChannel(channel_)
    else:
        # no valid id given. use as channel name
        return freader_.QueryChannelByName(channel_)


def __read_channel__(reader, iba_file, channel, tbase, clk, frames):
    """Internal function to read a certain channel in a wanted timebase

    :param reader: (mandatory, ibaFilesLite.FileReader) The reader used to open the iba file
    :param iba_file: (mandatory, string) path to the iba file
    :param channel: (mandatory, string or ibaFilesLite.ChannelId) the channel that shall be read
    :param tbase:  (mandatory, float): defines timebase in that the data will be returned.
    :param clk: (mandatory, float): the sample rate of the iba file
    :param frames: (mandatory, int): number of frames available in the iba files
    :return:
    """

    # is channel available?
    try:
        chan_reader = __get_iba_channel_reader__(channel, reader)
    except RuntimeError:
        raise ChannelNotFoundError('Channel {0} is not available in ibaFile {1}'.format(channel, iba_file))

    # read data from channel
    if chan_reader.IsText:
        return __read_text_channel__(chan_reader, tbase, clk, frames)
    else:
        return __read_numeric_channel__(chan_reader, tbase, clk)


def __read_numeric_channel__(chan_reader, tbase, clk):
    """Internal function to read the data from a given channel reader. The data will be returned in the wanted sample
    rate.

    :param chan_reader: (mandatory, iba)
    :param tbase: (mandatory, float) wanted sample rate in seconds
    :param clk: (mandatory, float) sample rate of the iba file
    :return: numpy array holding the data
    """

    # extract data
    channel_data = chan_reader.QueryData()
    
    # is file damaged?
    if channel_data is None:
        raise IbaFileDamagedError('The read channel data was None. It seems like the file is damaged.')

    # get clk of channel
    chn_clk = channel_data.Timebase

    # store as array
    processed_data = np.repeat(channel_data, 1)

    # does channel clk equals max clk?
    if chn_clk != clk:
        # how many copies per data point are needed?
        fct = chn_clk / clk
        # copy data to have equal amount of data points!
        processed_data = np.repeat(processed_data, fct)[np.newaxis].T

    # only take data points at a certain timebase
    if tbase != 0:
        processed_data = processed_data[::int(tbase / clk)]
        
    # make sure returned data has only 1 dimension.
    return processed_data.reshape(-1,)


def __read_text_channel__(chan_reader, tbase, clk, frames):
    """Internal function to read text the data from a given channel reader. The data will be returned in the wanted
     sample rate.

    :param chan_reader: (mandatory, iba)
    :param tbase: (mandatory, float) wanted sample rate in seconds
    :param clk: (mandatory, float) sample rate of the iba file
    :param frames: (mandatory, int): number of frames available in the iba files
    :return: numpy array holding the data
    """

    # extract data
    channel_data = chan_reader.QueryTextData()

    # is file damaged?
    if channel_data is None:
        raise IbaFileDamagedError('The read channel data was None. It seems like the file is damaged.')

    # TODO: find a more efficient way to gather the text data
    processed_data = [''] * frames
    for idx, text_data in enumerate(channel_data):
        start_idx = int(text_data[0] / clk)
        if idx < len(channel_data):
            end_idx = int(channel_data[idx][0] / clk)
        else:
            end_idx = int(frames)

        # fill the list with the string
        cur_str = text_data[1]
        for idx_list in range(start_idx, end_idx):
            processed_data[idx_list] = cur_str

    # only take data points at a certain timebase
    if tbase != 0:
        processed_data = processed_data[::int(tbase / clk)]

    return np.array(processed_data)


def __declaration_check__(iba_file, channels, names, delimiter):
    """
    This function will check the given ids/names of channels and the desired names to assign to them and format
    them accordingly (e.g. extract channel names if only ids are given) etc.
    
    :param iba_file: (mandatory, string) path to file
    :param channels: (mandatory, string or list of strings or dict): channels declaration (e.g. ['3:0', '12.1'] or 'ActCastSpeed')
    :param names: (mandatory, string or list of strings): list that define the names of the extracted channels.
    :param delimiter: (mandatory, string): defines the delimiter if the channels names/ids or desired names input is a single string
    """
    
    # ------------- check desired names for channels --------------
    # check if the desired names are of type string
    if type(names) == str:
        # use delimiter to split the string. make sure to remove whitespaces
        names = [el.strip() for el in names.split(delimiter)]

    # ------------- check channel ids/names --------------
    # check channel input
    # are no channel ids given? (willingly or not)
    if (channels is None) | (channels == '' or channels == '*'):
        # get all available channel names
        channels = get_channels(iba_file)
        names = channels[:]
    # are the channel ids given as a single string?
    elif type(channels) == str:
        # use delimiter to split the string. make sure to remove whitespaces
        channels = [el.strip() for el in channels.split(delimiter)]
    # are the channel ids given as a dict?
    elif type(channels) == dict:
        # ignore names input and only use names in dict.
        names = list(channels.values())
        channels = list(channels.keys())
    # are the channel ids given as a list?
    elif type(channels) == list:
        # make sure list of channels does not include empty strings
        channels = [chn for chn in channels if chn != '']
    
    # ------------ compare channel ids/names with desired names for channels -------------
    # check if channels and names are of same size
    if (not isinstance(names, list)) or (len(channels) != len(names)):
        # use original channel names
        names = get_channels(iba_file, channels)

    # return formatted ids and channel names
    return (channels, names)
        

def __cache_prep__(iba_file):
    """
    This function reads a given file into memory as fast as possible,
    discarding the data afterwards. While the data is not used (since
    IBA Files are encrypted), the data is usually taken into the
    operating systems cache, therefore speeding up the subsequent calls
    of the iba-files routines. Given enough cache memory, the performance
    of the file reading is vastly improved, especially if file is taken
    from a slow hard drive or over a network.
    data is not too small. If system is using an SSD the function only
    generates unnecessary overhead and should be disabled.

    (c) SMS Siemag AG 2011 / written by moor


    :param iba_file: (mandatory, string) path to the file
    :return:
    """

    f = open(iba_file, 'rb')
    f.seek(0, 2)
    f_size = f.tell()
    f.seek(0, 0)
    f.read(f_size)
    f.close()
