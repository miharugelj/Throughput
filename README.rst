Throughput
==========


Description
-----------

Library for testing network performance using speedtest.net or custom download and upload servers.
It can measure the following KPI parameters:

- PING -> max, min, average RTT (Round Trip Time) and packet loss,
- download and upload throughput speed.

The Throughput script uses python module speedlib. This module can be easily implemented into various applications.
For PING it uses a python-ping library created by George Notaras, Pierre Bourdon and Georgi Kolev, who developed
an implementation of the standard ICMP ping in pure Python.

This library is a fork of speedtest-cli_ developed by Matt Martz. We added support for some useful features, such as:

- the number of parallel streams to run,
- maximum time for download and upload measurements,
- using custom download and upload servers,
- saving results to .csv file.

This library does not support automatic selection of the speedtest.net server. If this is your case, use
speedtest-cli_ by Matt Martz.

.. _speedtest-cli: https://github.com/sivel/speedtest-cli


Version
-------

Library works with Python 2.4-2.7.9. Current version is **0.2**.


Requirements
------------

PycURL
~~~~~~

Ubuntu
______

::

    apt-get install python-pycurl

or

::

    pip install pycurl


Windows
_______

::

    pip install pycurl

or

::

    Download PycURL from: http://pycurl.sourceforge.net/. Use prebuilt version compatible with Python 2.


Root
~~~~

::

    ICMP ping uses raw ICMP sockets. You need to be root to use the functions exported by the speedlib module.


Installation
------------

Download
~~~~~~~~

::

    wget https://github.com/miharugelj/Throughput/raw/master/dist/Throughput-X.X.tar
    tar xvf Throughput-X.X.tar
    python setup.py install

or

::

    wget https://github.com/miharugelj/Throughput/raw/master/dist/Throughput-X.X.tar
    pip install Throughput-X.X.tar

Replace **X.X** with the current version of the package.

Github
~~~~~~

::

    git clone https://github.com/miharugelj/Throughput.git
    python Throughput/setup.py install


Usage
-----

::

    $ Throughput.py -h
    Usage: Throughput.py -i <speedtest.net server id> | -d <DL server URL> & -u <UL server URL> [options]

    Options:
      -h, --help            show this help message and exit
      -d DL, --download=DL  custom download server URL
      -f FILE, --file=FILE  output file to store results
      -i ID, --id=ID        speedtest.net server id
      -L, --list            list speedtest.net server id
      -n, --no-upload-results
                            do not upload results
      -P THREADS, --parallel=THREADS
                             number of parallel threads to run (default 3)
      -t TIME, --timeout=TIME
                            max time in seconds for download and upload
                            measurements (default 20 secs)
      -u UL, --upload=UL    custom upload server URL
      -v, --version         show version number and exit


Custom servers
--------------

You can measure the network performance using custom download and upload servers under your control.
Just put the following files to the HTTP server:

- random1000x1000.jpg
- random1500x1500.jpg
- random2000x2000.jpg
- random2500x2500.jpg
- random3000x3000.jpg
- random3500x3500.jpg
- random4000x4000.jpg


You can find these files in **custom-server** folder.


Use:

::

    $ Throughput.py -d http://x.x.x.x/files/ -u http://x.x.x.x


Crontab (Linux)
---------------

You can periodically measure network performance and writing/appending results to .csv file for further processing.
Add the following line to crontab for periodic measurements at every hour:

::

    0 * * * * python /usr/local/bin/Throughput.py -i <speedtest.net server id> -f <path>/results.csv

or

::

    0 * * * * python /usr/local/bin/Throughput.py  -d http://x.x.x.x/files/ -u http://x.x.x.x -f <path>/results.csv


COPYING
-------

GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007