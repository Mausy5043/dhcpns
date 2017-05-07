#! /bin/bash

fversion="$HOME/.dhcpns.version"
fbranch="$HOME/.dhcpns.branch"

VERSION="1.2"
BRANCH="master"

if [ ! -e "$fversion" ]; then
  echo $VERSION > "$fversion"
fi
if [ ! -e "$fbranch" ]; then
  echo $BRANCH > "$fbranch"
fi

sudo apt-get -yuV install python-mysqldb mysql-client
