#! /bin/bash

fversion="~/.dhcpns.version"
fbranch="~/.dhcpns.branch"

VERSION="1.0"
BRANCH="master"

if [ ! -e $fversion ]; then
  echo $VERSION > $fversion
fi
if [ ! -e $fbranch ]; then
  echo $BRANCH > $fbranch
fi

sudo apt-get -yuV install python-mysqldb mysql-client
