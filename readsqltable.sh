#!/bin/bash

sortorder="mac"

if [ $# -gt 0 ]; then
  sortorder=$1
  case ${sortorder} in
    "mac")
  # sort by MAC address
        sortorder="mac"
  ;;
    "ipoctet4"|"ip")
  # sort by last octet of IP address
        sortorder="ipoctet4"
  ;;
    "lastseen"|"date"|"time")
  # sort by date/time last seen
  sortorder="lastseen"
  ;;
    "node"|"nodename"|"host")
  # sort by hostname
  sortorder="nodename"
  ;;
    *)
  # default: sort by nodename
  sortorder="nodename"
  ;;
    esac
fi

mysql --defaults-file="~/.dns.cnf" -h sql --database="dhcpnsdb" --execute="select * from lantbl order by ${sortorder};"

