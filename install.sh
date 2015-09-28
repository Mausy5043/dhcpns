#! /bin/bash

fversion="~/.dhcpns.version"
branch="~/.dhcpns.branch"

VERSION="1.0"

if [ ! -e $fversion ]; then
  echo $VERSION > $fversion
fi
sudo apt-get -yuV install python-mysqldb mysql-client
