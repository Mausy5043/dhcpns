#!/bin/bash

DNSMASQCONF=/etc/dnsmasq.conf
DNSMASQDIR=/etc/dnsmasq.d
cat "${DNSMASQCONF}" "${DNSMASQIR}/*" | egrep "^dhcp-leasefile" | awk -F "=" '{print $2}'
