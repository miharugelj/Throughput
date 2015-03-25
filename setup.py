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


from distutils.core import setup


# Get long description from the README.rst file
try:
    with open('README.rst', 'r') as file:
        long_description = file.read()
except:
    long_description = ''


setup(name='Throughput',
      version='0.1',
      py_modules=['speedlib'],
      scripts=['Throughput.py'],

      author='Miha Rugelj',
      author_email="rugelj.miha@gmail.com",
      description="Testing network performance using speedtest.net or custom download and upload servers",
      long_description=long_description,
      license="GPL3",
      url="GITHUB",

      classifiers=[
          "Development Status :: 5 - Production/Stable",
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: Unix',
          'Programming Language :: Python :: 2',
          'Topic :: System :: Networking',
          'Topic :: System :: Networking :: Measuring',
        ],
)