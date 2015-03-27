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
import socket
import select
import struct
import threading
import Queue
import timeit
import pycurl
import xml.etree.cElementTree as ET
from datetime import datetime
from cStringIO import StringIO
from urlparse import urlparse
from urllib import urlencode


class Ping:
    """
    A pure python ping implementation using raw socket.

    Note that ICMP messages can only be sent from processes running as root.

    Derived from ping.c distributed in Linux's netkit. That code is
    copyright (c) 1989 by The Regents of the University of California.
    That code is in turn derived from code written by Mike Muuss of the
    US Army Ballistic Research Laboratory in December, 1983 and
    placed in the public domain. They have my thanks.

    Bugs are naturally mine. I'd be glad to hear about them. There are
    certainly word - size dependenceies here.

    Copyright (c) Matthew Dixon Cowles, <http://www.visi.com/~mdc/>.
    Distributable under the terms of the GNU General Public License
    version 2. Provided with no warranties of any sort.

    Original Version from Matthew Dixon Cowles:
      -> ftp://ftp.visi.com/users/mdc/ping.py

    Rewrite by Jens Diemer:
      -> http://www.python-forum.de/post-69122.html#69122

    Rewrite by George Notaras:
      -> http://www.g-loaded.eu/2009/10/30/python-ping/

    Fork by Pierre Bourdon:
      -> http://bitbucket.org/delroth/python-ping/
    """


    # From /usr/include/linux/icmp.h; your milage may vary.
    ICMP_ECHO_REQUEST = 8   # Seems to be the same on Solaris.

    def __init__(self, dest_addr, timeout=5, count=5, psize=64):
        self.dest_addr = dest_addr
        self.timeout = timeout
        self.count = count
        self.psize = psize


    def checksum(self, source_string):
        """
        I'm not too confident that this is right but testing seems
        to suggest that it gives the same answers as in_cksum in ping.c
        """
        sum = 0
        count_to = (len(source_string) / 2) * 2
        for count in xrange(0, count_to, 2):
            this = ord(source_string[count + 1]) * 256 + ord(source_string[count])
            sum = sum + this
            sum = sum & 0xffffffff # Necessary?

        if count_to < len(source_string):
            sum = sum + ord(source_string[len(source_string) - 1])
            sum = sum & 0xffffffff # Necessary?

        sum = (sum >> 16) + (sum & 0xffff)
        sum = sum + (sum >> 16)
        answer = ~sum
        answer = answer & 0xffff

        # Swap bytes. Bugger me if I know why.
        answer = answer >> 8 | (answer << 8 & 0xff00)

        return answer


    def receive_one_ping(self, my_socket, id):
        """
        Receive the ping from the socket.
        """
        time_left = self.timeout
        while True:
            started_select = timeit.default_timer()
            what_ready = select.select([my_socket], [], [], time_left)
            how_long_in_select = (timeit.default_timer() - started_select)
            if what_ready[0] == []: # Timeout
                return

            time_received = timeit.default_timer()
            received_packet, addr = my_socket.recvfrom(1024)
            icmpHeader = received_packet[20:28]
            type, code, checksum, packet_id, sequence = struct.unpack(
                "bbHHh", icmpHeader
            )
            if packet_id == id:
                bytes = struct.calcsize("d")
                time_sent = struct.unpack("d", received_packet[28:28 + bytes])[0]
                return time_received - time_sent

            time_left = time_left - how_long_in_select
            if time_left <= 0:
                return


    def send_one_ping(self, my_socket, id):
        """
        Send one ping to the given >dest_addr<.
        """
        dest_addr = socket.gethostbyname(self.dest_addr)


        # Remove header size from packet size
        psize = self.psize - 8

        # Header is type (8), code (8), checksum (16), id (16), sequence (16)
        my_checksum = 0

        # Make a dummy heder with a 0 checksum.
        header = struct.pack("bbHHh", self.ICMP_ECHO_REQUEST, 0, my_checksum, id, 1)
        bytes = struct.calcsize("d")
        data = (psize - bytes) * "Q"
        data = struct.pack("d", timeit.default_timer()) + data

        # Calculate the checksum on the data and the dummy header.
        my_checksum = self.checksum(header + data)

        # Now that we have the right checksum, we put that in. It's just easier
        # to make up a new header than to stuff it into the dummy.
        header = struct.pack(
            "bbHHh", self.ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), id, 1
        )
        packet = header + data
        my_socket.sendto(packet, (dest_addr, 1)) # Don't know about the 1


    def do_one(self):
        """
        Returns either the delay (in seconds) or none on timeout.
        """
        icmp = socket.getprotobyname("icmp")
        try:
            my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
        except socket.error, (errno, msg):
            if errno == 1:
                # Operation not permitted
                msg = msg + (" - Note that ICMP messages can only be sent from processes running as root.")
                raise socket.error(msg)

            raise # raise the original error

        my_id = os.getpid() & 0xFFFF

        self.send_one_ping(my_socket, my_id)
        delay = self.receive_one_ping(my_socket, my_id)

        my_socket.close()
        return delay


    def quiet_ping(self):
        """
        Send `count' ping with `psize' size to `dest_addr' with
        the given `timeout' and display the result.
        Returns `percent' lost packages, `max' round trip time
        and `avrg' round trip time.
        """
        max_rtt = None
        min_rtt = None
        avg_rtt = None
        lost = 0
        plist = []

        for i in xrange(self.count):
            try:
                delay = self.do_one()
            except socket.gaierror, e:
                print "failed. (socket error: '%s')" % e[1]
                break

            if delay != None:
                delay = delay * 1000
                plist.append(delay)

        # Find lost package percent
        percent_lost = 100 - (len(plist) * 100 / self.count)

        # Find max, min and avg round trip time
        if plist:
            max_rtt = max(plist)
            min_rtt = min(plist)
            avg_rtt = sum(plist) / len(plist)

        return percent_lost, max_rtt, min_rtt, avg_rtt


class Throughput:

    def __init__(self, id=None, dl=None, ul=None, maxThreads=3, timeout=20,  outputFile='results'):
        self.id = id
        self.dl = dl
        self.ul = ul
        self.maxThreads = maxThreads
        self.timeout = timeout
        self.outputFile = outputFile


    def getServersInfo(self):
        """
        Get speedtest.net servers info
        """

        serverInfo = None
        url = 'http://www.speedtest.net/speedtest-servers-static.php'

        buf = StringIO()
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.CONNECTTIMEOUT, 5)
        curl.setopt(pycurl.TIMEOUT, 10)
        curl.setopt(pycurl.FAILONERROR, True)
        curl.setopt(pycurl.FOLLOWLOCATION, True)
        curl.setopt(pycurl.WRITEFUNCTION, buf.write)
        m_curl = pycurl.CurlMulti()
        m_curl.add_handle(curl)

        start = timeit.default_timer()
        while 1:
            (code, num_handles) = m_curl.perform()
            if code != pycurl.E_CALL_MULTI_PERFORM:
                break
        while num_handles:
            if (timeit.default_timer() - start) >= 10:
                m_curl.remove_handle(curl)

            while 1:
                (code, num_handles) = m_curl.perform()
                if code != pycurl.E_CALL_MULTI_PERFORM:
                    break

        if curl.getinfo(curl.RESPONSE_CODE) != 200:
            curl.close()
            return None
        else:
            curl.close()

        try:
            root = ET.fromstring(buf.getvalue())
            elements = root.iter('server')
        except SyntaxError:
            print('Failed to parse list of speedtest.net servers')
            sys.exit(1)

        if self.id is not None:
            for server in elements:
                try:
                    if server.attrib['id'] == self.id:
                        serverInfo = server.attrib
                except AttributeError:
                    sys.exit(1)

            return serverInfo
        else:
            return elements


    class FileDL(threading.Thread):
        """
        Thread class for retrieving a URL
        """

        def __init__(self, url, start_thread_time, end_thread_time):
            threading.Thread.__init__(self)
            self.transfer_bytes = 0
            self.url = url
            self.start_thread_time = start_thread_time
            self.end_thread_time = end_thread_time
            self.buf = StringIO()
            self.curl = pycurl.Curl()
            self.curl.setopt(pycurl.NOSIGNAL, 1)
            self.curl.setopt(pycurl.URL, self.url)
            self.curl.setopt(pycurl.CONNECTTIMEOUT, 5)
            self.curl.setopt(pycurl.TIMEOUT, self.end_thread_time)
            self.curl.setopt(pycurl.FAILONERROR, True)
            self.curl.setopt(pycurl.WRITEFUNCTION, self.buf.write)


        def run(self):
            try:
                if (timeit.default_timer() - self.start_thread_time) <= self.end_thread_time:
                    self.curl.perform()
            except pycurl.error, e:
                pass
            finally:
                self.transfer_bytes = self.curl.getinfo(self.curl.SIZE_DOWNLOAD)
                self.curl.close()


    def downloadSpeed(self, files):
        """
        Download speed measurement
        """

        start_dl = timeit.default_timer()
        finished = []
        threads = []

        def producer(q, files):
            for file in files:
                thread = self.FileDL(file, start_dl, self.timeout)
                q.put(thread, True)

        def consumer(q, total_files, total_threads):
            while len(finished) < total_files:

                if (len(threads) < total_threads) and not q.empty():
                    try:
                        thread = q.get(True, timeout=0.1)
                        threads.append(thread)
                        thread.start()
                    except Queue.Empty:
                        pass

                for t in threads:
                    if t.isAlive():
                        t.join(timeout=0.1)
                        continue
                    else:
                        threads.remove(t)
                        finished.append(t)
                        q.task_done()

                        sys.stdout.write('.')
                        sys.stdout.flush()


        q = Queue.Queue(self.maxThreads)
        prod_thread = threading.Thread(target=producer, args=(q, files))
        cons_thread = threading.Thread(target=consumer, args=(q, len(files), self.maxThreads))

        start_measurement = timeit.default_timer()
        prod_thread.start()
        cons_thread.start()

        while cons_thread.isAlive():
            cons_thread.join(timeout=0.1)

        end_measurement = timeit.default_timer()

        transfer_bits = 0
        for res in finished:
            transfer_bits += res.transfer_bytes*8

        return transfer_bits/(end_measurement-start_measurement)


    class FileUL(threading.Thread):
        """
        Thread class for posting data
        """

        def __init__(self, url, size, start_thread_time, end_thread_time):
            threading.Thread.__init__(self)
            self.transfer_bytes = 0
            self.url = url
            self.start_thread_time = start_thread_time
            self.end_thread_time = end_thread_time

            chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            data = chars * (int(round(int(size) / 36.0)))
            post_data = {'content1': (data[0:int(size) - 9]).encode()}
            self.post_data = urlencode(post_data)

            self.buf = StringIO()
            self.curl = pycurl.Curl()
            self.curl.setopt(pycurl.URL, self.url)
            self.curl.setopt(pycurl.NOSIGNAL, 1)
            self.curl.setopt(pycurl.CONNECTTIMEOUT, 5)
            self.curl.setopt(pycurl.TIMEOUT, self.end_thread_time)
            self.curl.setopt(pycurl.FAILONERROR, True)
            self.curl.setopt(pycurl.WRITEFUNCTION, self.buf.write)


        def run(self):
            try:
                if (timeit.default_timer() - self.start_thread_time) <= self.end_thread_time:
                    self.curl.setopt(self.curl.POSTFIELDS, self.post_data)
                    self.curl.perform()
            except pycurl.error, e:
                pass
            finally:
                self.transfer_bytes = self.curl.getinfo(self.curl.SIZE_UPLOAD)
                self.curl.close()


    def uploadSpeed(self, url, sizes):
        """
        Upload speed measurement
        """

        start_ul = timeit.default_timer()
        finished = []
        threads = []

        def producer(q, sizes):
            for size in sizes:
                thread = self.FileUL(url, size, start_ul, self.timeout)
                q.put(thread, True)

        def consumer(q, total_sizes, total_threads):
            while len(finished) < total_sizes:
                if (len(threads) < total_threads) and not q.empty():
                    try:
                        thread = q.get(True, timeout=0.1)
                        threads.append(thread)
                        thread.start()
                    except Queue.Empty:
                        pass

                for t in threads:
                    if t.isAlive():
                        t.join(timeout=0.1)
                        continue
                    else:
                        threads.remove(t)
                        finished.append(t)
                        q.task_done()

                        sys.stdout.write('.')
                        sys.stdout.flush()


        q = Queue.Queue(self.maxThreads)
        prod_thread = threading.Thread(target=producer, args=(q, sizes))
        cons_thread = threading.Thread(target=consumer, args=(q, len(sizes), self.maxThreads))

        start_measurement = timeit.default_timer()
        prod_thread.start()
        cons_thread.start()

        while cons_thread.isAlive():
            cons_thread.join(timeout=0.1)

        end_measurement = timeit.default_timer()

        transfer_bits = 0
        for res in finished:
            transfer_bits += res.transfer_bytes*8

        return transfer_bits/(end_measurement-start_measurement)


    def writeResults(self, results):
        """
        Write results to .csv file
        """

        outputFile = self.outputFile
        file_exists = False

        if os.path.isfile(outputFile):
            file_exists = True

        with open(outputFile, 'a+') as file:
            if not file_exists:
                file.write('Timestamp,DL_server,UL_server,Avg_RTT_(ms),Min_RTT_(ms),Max_RTT_(ms),Loss_(%),'
                           'DL_speed_(Mbit/s),UL_speed_(Mbit/s)\n')

            file.write(datetime.now().strftime("%Y-%m-%d_%H:%M:%S")+',')
            file.write(urlparse(results['dl_url']).netloc+',')
            file.write(urlparse(results['ul_url']).netloc+',')

            if results['RTT']['avg_rtt'] is not None:
                file.write(str(round(results['RTT']['avg_rtt'], 3))+',')
                file.write(str(round(results['RTT']['min_rtt'], 3))+',')
                file.write(str(round(results['RTT']['max_rtt'], 3))+',')
                file.write(str(results['RTT']['percent_lost'])+',')
            else:
                file.write('0'+',')
                file.write('0'+',')
                file.write('0'+',')
                file.write(str(round(results['RTT']['percent_lost']))+',')

            if results['dl_speed'] is not None:
                file.write(str(round(results['dl_speed']/1000000, 3))+',')
            else:
                file.write('0'+',')

            if results['ul_speed'] is not None:
                file.write(str(round(results['ul_speed']/1000000, 3)))
            else:
                file.write('0')

            file.write('\n')
