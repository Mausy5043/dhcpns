#! /bin/bash

fversion="$HOME/.dhcpns.version"
fbranch="$HOME/.dhcpns.branch"

VERSION="2.1"
BRANCH="py3"

install_package()
{
  # See if packages are installed and install them.
  package=$1
  echo "*********************************************************"
  echo "* Requesting ${package}"
  status=$(dpkg-query -W -f='${Status} ${Version}\n' "${package}" 2>/dev/null | wc -l)
  if [ "${status}" -eq 0 ]; then
    echo "* Installing ${package}"
    echo "*********************************************************"
    sudo apt-get -yuV install "${package}"
  else
    echo "* Already installed !!!"
    echo "*********************************************************"
  fi
}


if [ ! -e "$fversion" ]; then
  echo $VERSION > "$fversion"
fi
if [ ! -e "$fbranch" ]; then
  echo $BRANCH > "$fbranch"
fi

# MySQL support (python3)
install_package "mysql-client"
install_package "libmariadbclient-dev"
install_package "traceroute"
install_package "nmap"
sudo pip3 install mysqlclient