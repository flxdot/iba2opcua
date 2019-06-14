import os
import asyncio
import time
from threading import Thread, Event
from asyncua import ua, uamethod, Server
from pyIbaTools.pyIbaTools import getSortedIbaFiles, readIbaFile, get_channels, get_channel_info


class IbaToUaServer():
    """The Server will discover the iba files and prepare the Opc Server accordingly."""

    def __init__(self):
        """Default constructor. Not magic here since everything is hard coded atm.

        Todo: Use config parser to configure the server a little bit
        """

        # init super class constructors
        super().__init__()

        # list of path to iba files
        self.iba_files = list()

        # dictionary containing the channels of the iba files sorted by sample rate
        self.iba_info = dict()

        # dictionary of loaded iba data sorted by sample rate
        self.iba_data = dict()

        # handle to the actual opc ua server
        self._server = None

        # dictionary of threads for each unique sample rate
        self._value_updater = dict()

    async def start(self):
        """The actual run function called by the Thread super class. All the magic happens here.

        1. discover the iba files in the dat sub folder
        2. get channels from the iba files
        3. build the opc ua server
        4. read the data
        5. start the updating of the data

        :return:
        """

        # discover iba files
        print('finding iba files ...')
        self.iba_files = self.discover_iba_files()

        # get channels from first iba file
        print('receiving channel info ...')
        self.iba_info = self.get_file_info(self.iba_files[0])

        # build the opc server
        print('building opc server ...')
        await self.init_opc()

        # start the server
        print('starting opc server ...')
        await self._server.start()

        # create the value updater
        self._write_values()

        while True:
            await asyncio.sleep(0.1)


    def discover_iba_files(self):
        """Call to get a list of iba files in the dat sub directory.

        :return: list of paths to iba files
        :raises: FileNotFoundError
        """

        # where shall i search for files?
        iba_path = os.path.join(os.getcwd(), 'dat')

        # get the list of iba files
        file_list = getSortedIbaFiles(iba_path, scan_sub_folders=False)

        # check if any files have been found
        if not file_list:
            raise FileNotFoundError('Could not find any files at ''{}''.'.format(file_list))

        # TODO: check if all iba files have the same channel configuration. If not this will create problems!

        return file_list


    def get_file_info(self, iba_file):
        """Returns a dict containing all modules defined in the iba file as well as the dictionary with channels group
        by their sample rate.

        :param iba_file: (madatory, string) path to a iba files
        :return: dict with keys: modules (dict), channel (dict)
        """

        # get the actual info
        channel_info = get_channel_info(iba_file)

        # loop over the file to store the info
        modules = dict()
        channels = dict()
        for name, chan in channel_info.items():
            # ignore text channel
            if chan['type'] == 'text' or '$PDA_Tbase' not in chan.keys():
                continue

            # add fields to the channel dict for later use
            chan['opc_obj'] = None
            chan['opc_value'] = None

            # get module
            full_module = '{0} {1}'.format(chan['module_no'], chan['module'])
            if full_module not in modules.keys():
                modules[full_module] = list()
            modules[full_module].append(chan)

            # sort channel
            cur_tbase = chan['$PDA_Tbase']
            if cur_tbase not in channels.keys():
                channels[cur_tbase] = list()
            channels[cur_tbase].append(chan)

        return {'modules': modules, 'channels': channels}

    async def init_opc(self):
        """Initializes the actual OPC Server and creates all folder, nodes, etc.

        :return: None
        """

        self._server = Server()
        await self._server.init()
        self._server.set_endpoint("opc.tcp://localhost:4840/sms-digital/iba-playback/")
        self._server.set_server_name("iba Files Playback OPC UA Server")

        # set all possible endpoint policies for clients to connect through
        self._server.set_security_policy([
            ua.SecurityPolicyType.NoSecurity,
            ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
            ua.SecurityPolicyType.Basic256Sha256_Sign])

        # setup our own namespace
        uri = "http://iba-playback.sms-digital.io"
        idx = await self._server.register_namespace(uri)

        # add modules folder
        modules = await self._server.nodes.objects.add_folder(idx, "Modules")
        for module, channel in self.iba_info['modules'].items():
            print('\tModule: {} ...'.format(module))
            # create a new folder for the module
            module_folder = await modules.add_folder(idx, module)

            # create a folder for analog and digital signals
            analog_folder = await module_folder.add_folder(idx, 'Analog')
            digital_folder = await module_folder.add_folder(idx, 'Digital')

            # add the channel
            for chan in channel:
                # create channel
                if chan['type'] == 'analog':
                    opc_channel = await analog_folder.add_object(idx, chan['name'])
                    val = 0.0
                else:
                    opc_channel = await digital_folder.add_object(idx, chan['name'])
                    val = False

                # define the channel object
                value_var = await opc_channel.add_variable(idx, "value", val)
                value_var.set_writable(True)
                for key, val in chan.items():
                    await opc_channel.add_variable(idx, key, val).set_writable(False)

                # store the handles to the value variable and the opc_channel in the channel dict
                chan['opc_obj'] = opc_channel
                chan['opc_value'] = value_var

    def _write_values(self):
        """Spawn a thread for each sample rate

        :return:
        """

        for sampleRate, channel in self.iba_info['channels'].items():

            # read the data
            channels = list()
            for chan in channel:
                channels.append(chan['id'])

            # TODO: Deal with multiple files
            data = readIbaFile(self.iba_files[0], channels=channels, names=channels)

            # todo: split large files with many channel with the same samplerate into multiple threads

            # create variable update
            VariableUpdater(server=self._server, channel=channel, period=float(sampleRate), data=data).start()


class VariableUpdater(Thread):
    """The VariableUpdater is used to periodically update the values on the opc server."""

    def __init__(self, server, channel, period, data):
        """

        :param channel: (mandatory, list) list with the channels
        :param period: (mandatory, float) the actual sample period
        :param data: (mandatory, pandas.DataFrame) the loaded data
        """

        super().__init__(name='Updater_{}'.format(period))

        self.server = server
        self.channel = channel
        self.period = period
        self.data = data

        # timer stuff
        self._close_event = Event()
        self._nextCall = time.time()

    def run(self):
        """This method will make

        :return: None
        """

        print('Started VariableUpdater {}'.format(self.name))

        idx = 0
        while not self._close_event.is_set():
            # store information about the next call
            self._nextCall = time.time()

            # do your tasks here
            for chan in self.channel:
                # faster than chan['opc_value'].set_value(9.9)
                self.server.set_attribute_value(chan['opc_value'].nodeid, ua.DataValue(self.data[chan['id']][idx]))

            # increase index
            idx += 1
            if idx > self.data.shape[0]:
                idx = 0

            # sleep until next execution
            self._nextCall = self._nextCall + self.period
            sleepLength = self._nextCall - time.time()
            if sleepLength > 0:
                time.sleep(sleepLength)
            else:
                print('{0}: Sample rate exceeded by {1:.2f}ms.'.format(self.name, abs(sleepLength)*1000))

    def stop(self):
        """Call to stop the timer"""

        self._close_event.set()

async def main():
    the_server = IbaToUaServer()
    await the_server.start()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    loop.run_until_complete(main())
