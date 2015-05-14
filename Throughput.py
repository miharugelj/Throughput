#!/usr/bin/env python

#   Copyright 2015 Miha Rugelj
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import sys
import hashlib
import random
import platform
import urllib2
from datetime import datetime
from urlparse import urlparse
from urllib import urlencode
from optparse import OptionParser
from ConfigParser import ConfigParser

try:
    import pycurl
except ImportError:
    print("PycURL is not installed. Read README file.")
    sys.exit(1)
import speedlib


__version__ = '0.2'


def test(throughput):
    """
    Run measurements procedure
    """

    serverInfo = {}
    results = {}

    if throughput.id is not None:
        # Perform speedtest.net test

        print('Retrieving speedtest.net server info ...')
        serverInfo = throughput.getServersInfo()

        # TMP
        #serverInfo = {'name': 'Ljubljana', 'url': 'http://speedtest.simobil.si/speedtest/upload.php',
        #              'country': 'Slovenia', 'lon': '14.5000', 'cc': 'SI', 'host': 'speedtest.simobil.si:8080',
        #              'sponsor': 'Si.mobil d.d.', 'url2': 'http://speedtest1.simobil.si/speedtest/upload.php',
        #              'lat': '46.0500', 'id': '2198'}

        if serverInfo is None:
            print('Cannot retrieve speedtest.net server info. Try again later.')
            sys.exit(1)
        else:
            print('Using server: %(sponsor)s, %(name)s, %(country)s' % serverInfo)

        serverInfo['dl_url'] = serverInfo['url']
        serverInfo['ul_url'] = serverInfo['url']

    elif throughput.dl is not None and throughput.ul is not None:
        # Perform download and upload test using custom servers

        serverInfo['dl_url'] = throughput.dl
        serverInfo['ul_url'] = throughput.ul

        print('Using DL server: %s' % serverInfo['dl_url'])
        print('Using UL server: %s' % serverInfo['ul_url'])

    # DL/UL hostname
    results['dl_hostname'] = urlparse(serverInfo['dl_url']).netloc
    results['ul_hostname'] = urlparse(serverInfo['ul_url']).netloc


    # Get client info
    clientInfo = throughput.getClientInfo()

    if clientInfo is not None:
        results.update(clientInfo)


    # Timestamp
    results['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print('\nTest server latency ...')
    percent_lost = None
    max_rtt = None
    min_rtt = None
    avg_rtt = None

    server_url = urlparse(serverInfo['dl_url'])
    ping = speedlib.Ping(server_url.netloc)
    try:
        (percent_lost, max_rtt, min_rtt, avg_rtt) = ping.quiet_ping()
    except:
        percent_lost = 100

    rtts = {'percent_lost': percent_lost,
            'max_rtt_ms': max_rtt,
            'min_rtt_ms': min_rtt,
            'avg_rtt_ms': avg_rtt}

    if rtts['avg_rtt_ms'] is not None:
        rtts['min_rtt_ms'] = round(rtts['min_rtt_ms'], 2)
        rtts['avg_rtt_ms'] = round(rtts['avg_rtt_ms'], 2)
        rtts['max_rtt_ms'] = round(rtts['max_rtt_ms'], 2)
        print ('Ping RTT: %(avg_rtt_ms)0.2fms (max=%(max_rtt_ms)0.2fms, min=%(min_rtt_ms)0.2fms, '
               'lost=%(percent_lost)1d%%)' % rtts)
    else:
        print ('Ping RTT: %(avg_rtt_ms)s' % rtts)
    results.update(rtts)


    sizes = [1000, 1500, 2000, 2500, 3000, 3500, 4000]
    urls = []
    for size in sizes:
        for i in range(0, throughput.maxThreads):
            urls.append('%s/random%sx%s.jpg' % (os.path.dirname(serverInfo['dl_url']), size, size))

    print('\nTesting download speed')
    try:
        dl_speed = throughput.downloadSpeed(urls)
    except:
        dl_speed = None

    if dl_speed is not None:
        results['dl_speed_kbps'] = round(dl_speed/1000, 3)
        print("\nDownload speed: %0.3f Mbit/s: " % (dl_speed/1000000))
    else:
        print("\nDownload speed: %s: " % dl_speed)

    size_sizes = [int(1*1024*1024), int(5*1024*1024), int(10*1024*1024), int(20*1024*1024), int(50*1024*1024)]
    sizes = []
    for size in size_sizes:
        for i in range(0, throughput.maxThreads):
            sizes.append(size)


    print('\nTesting upload speed')
    try:
        ul_speed = throughput.uploadSpeed(serverInfo['ul_url'], sizes)
    except:
        ul_speed = None

    if ul_speed is not None:
        results['ul_speed_kbps'] = round(ul_speed/1000, 3)
        print("\nUpload speed: %0.3f Mbit/s: " % (ul_speed/1000000))
    else:
        print("\nUpload speed: %s: " % ul_speed)


    # Write results to file
    if throughput.outputFile is not None:
        print("Writing results to file: %s" % throughput.outputFile)
        throughput.writeResults(results)


    # Get config parameters
    os_name = platform.system()
    if os_name in ['Linux', 'Darwin']:
        path = '/opt/.throughput'
    elif os_name in ['Windows'] or os_name.find('CYGWIN') != -1:
        path = r'C:\.throughput'

    if not os.path.exists(path+os.sep+'config'):
        try:
            os.mkdir(path)
        except IOError:
            pass

        config = ConfigParser()
        config.add_section('GENERAL')
        config.add_section('SERVER')

        hash = hashlib.sha1(datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f") + str(random.random())).hexdigest()
        server_ip = '212.101.137.10'
        config.set('GENERAL', 'hash', hash)
        config.set('SERVER', 'ip', server_ip)

        with open(path+os.sep+'config', 'w') as file:
            config.write(file)

    else:
        config = ConfigParser()
        config.read(path+os.sep+'config')

        hash = config.get('GENERAL', 'hash')
        server_ip = config.get('SERVER', 'ip')

    results['hash'] = hash


    # HTTP GET results
    if throughput.noUploadResults is not True:
        data = urlencode(results)
        try:
            req = urllib2.Request('http://'+server_ip+'/getdata/?'+data)
            response = urllib2.urlopen(req)
            page = response.read()

            print page
        except urllib2.URLError:
            pass





########################################################################################################################
def main():

    try:
        # Parse args
        usage = "Usage: %prog -i <speedtest.net server id> | -d <DL server URL> & -u <UL server URL> [options]"
        parser = OptionParser(usage=usage)
        parser.add_option("-d", "--download", action="store", dest="dl", help="custom download server URL")
        parser.add_option("-f", "--file", action="store", dest="file", help="output file to store results")
        parser.add_option("-i", "--id", action="store", dest="id", help="speedtest.net server id")
        parser.add_option("-L", "--list", action="store_true", dest="list", help="list speedtest.net server id")
        parser.add_option("-n", "--no-upload-results", action="store_true", dest="noUploadResults",
                          help="do not upload results")
        parser.add_option("-P", "--parallel", action="store", type=int, default=3, dest="threads",
                          help=" number of parallel threads to run (default 3)")
        parser.add_option("-t", "--timeout", action="store", type=int, default=20, dest="time",
                          help="max time in seconds for download and upload measurements (default 20 secs)")
        parser.add_option("-u", "--upload", action="store", dest="ul", help="custom upload server URL")
        parser.add_option("-v", "--version", action="store_true", dest="version", help="show version number and exit")
        (options, args) = parser.parse_args()

        if options.version is True:
            print(__version__)
            sys.exit(0)

        if options.list is True:
            throughput = speedlib.Throughput()
            servers = throughput.getServersInfo()

            if servers is None:
                print("Cannot retrieve speedtest.net servers's info. Try again later.")
                sys.exit(1)
            else:
                servers_sort = sorted(servers, key=lambda x: x.attrib['country'])
                for server in servers_sort:
                    print("Server: %(country)s, %(name)s, %(sponsor)s, (id=%(id)s)" % server.attrib).encode('UTF-8')
                sys.exit(0)

        if options.id is None and (options.dl is None or options.ul is None):
            print("Throughput: provide speedtest.net server id <-i=id> or DL/UL custom server URL <--download=URL> <--upload=URL>")
            print("\nUse Throughput --help for additional info.")
            sys.exit(1)

        # Start measurements
        throughput = speedlib.Throughput(options.id, options.dl, options.ul, options.threads, options.time,
                                         options.file, options.noUploadResults)
        test(throughput)

    except KeyboardInterrupt:
        print('\nCancelling...')


if __name__ == '__main__':
    main()
