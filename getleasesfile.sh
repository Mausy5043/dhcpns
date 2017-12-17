#!/bin/bash

DNSMASQCONF=/etc/dnsmasq.conf
DNSMASQDIR=/etc/dnsmasq.d

# abort if dnsmasq is not properly installed
if [ ! -f "${DNSMASQCONF}" ]; then
  echo "${DNSMASQCONF} not found. Is dnsmasq installed?"
  exit 1
fi

cat "${DNSMASQCONF}" "${DNSMASQDIR}/*" | egrep "^dhcp-leasefile" | awk -F "=" '{print $2}'
