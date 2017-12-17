#! /usr/bin/env python3

"""Scans the LAN for all hosts and reports some statistics about them"""

import MySQLdb as mdb
import subprocess as sp
import os
import sys
import syslog
import time
import traceback

def lstvssql(hostlist):
  """
  Compare the gathered data to what is in the database.
  """
  try:
    lastseen = time.strftime('%Y-%m-%d %H:%M:%S')
    # connect to the database
    con = mdb.connect(host='sql', db='dhcpnsdb', read_default_file='~/.dns.cnf')
    # activate a cursor
    cur = con.cursor()
    # test the connection
    cur.execute("SELECT VERSION()")
    ver = cur.fetchone()
    print("SQL database version: %s" % ver)
    print("Scan performed on:    %s" % lastseen)
    for idx, line in enumerate(hostlist):
      mac = line[3]
      ipoctet4 = str(line[8]).zfill(3)
      nodename = line[1]
      # check if MAC exists in DB
      if (len(mac) == 17):
        # MAC is valid: search for it in the DB
        cmd = ('SELECT * '
               'FROM lantbl '
               'WHERE mac="' + mac + '"')
        cur.execute(cmd)
        rsl = cur.fetchone()
        if (rsl is None):
          if DEBUG:
            print("MAC is not found in DB")
          if (line[5] != 0):
            if DEBUG:
              print("... new host found")
            # & host is pingable -> new host, so add it to the DB
            cmd = ('INSERT INTO lantbl '
                   '(mac, ipoctet4, lastseen, nodename) '
                   'VALUES (%s, %s, %s, %s)')
            dat = (mac, ipoctet4, lastseen, nodename)
            syslog.syslog(syslog.LOG_NOTICE, "INSERTed " + mac + " @ " + nodename)
            cur.execute(cmd, dat)
            con.commit()
            line[10] = lastseen
          # {endif}
        else:
          if DEBUG:
            print("MAC is present in DB")
          if (line[5] != 0):
            if DEBUG:
              print("... updating existing hostdata")
            if nodename != "*":
              cmd = ('UPDATE lantbl '
                     'SET lastseen = %s, nodename = %s, ipoctet4 = %s '
                     'WHERE mac = %s ')
              dat = (lastseen, nodename, ipoctet4, mac)
            else:
              cmd = ('UPDATE lantbl '
                     'SET lastseen = %s, ipoctet4 = %s '
                     'WHERE mac = %s ')
              dat = (lastseen, ipoctet4, mac)
            cur.execute(cmd, dat)
            con.commit()
            line[10] = lastseen
          else:
            # & host is not pingable -> update local data (arp-data may be stale)
            # print "exists in DB; not pingable. Local data may not be up-to-date."
            # print "update info ", mac, rsl
            # print line[1],line[2]
            line[1] = "* " + rsl[3]
            line[2] = "* " + rsl[3]
            line[10] = rsl[2]
          # {endif}
        # {endif}
      else:
        # sometimes nodename = "?" and mac = "<incomplete>"
        if (nodename == "?"):
          # then lookup the last user of the IP-address
          cmd = ('SELECT * '
                 'FROM lantbl '
                 'WHERE ipoctet4="' + ipoctet4 + '"')
          cur.execute(cmd)
          rsl = cur.fetchone()
          # example output
          # rsl <= ('00:00:00:00:00:00', '182', datetime.datetime(2015, 10, 18, 14, 45, 26), 'hostname')
          if (rsl is not None):
            line[1] = "-" + rsl[3]
            line[2] = "-" + rsl[3]
            line[3] = "-" + rsl[0]
            line[10] = rsl[2]
        else:
          print(nodename, mac, ipoctet4)
      # {endif}
    # {endfor}
  except mdb.Error as e:
    print(e.__doc__)
    syslog.syslog(syslog.LOG_ALERT, e.__doc__)
    syslog_trace(traceback.format_exc())
  finally:
    if con:
        cur.close()
        con.close()
  # {endtry}
  return hostlist

def findleasesfile(filename):
  """
  Find the path to the leases file of dnsmasq
  """
  cmd = ["./getleasesfile.sh"]
  ping = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
  output, err = ping.communicate()
  output = output.decode("utf-8").strip('\n')
  if output:
    filename = output
  # {endif}
  if DEBUG:
    print("Leases file: {0}".format(filename))
  # {endif}
  if not os.path.isfile(filename):
    raise OSError("File not found")
  # {endif}
  return filename

def getleases(listsize, ux):
  """
  Read the contents of the dnsmasq leases file
  Normally: /var/lib/misc/dnsmasq.leases
  """
  leasesfile = findleasesfile("/var/lib/misc/dnsmasq.leases")
  hostlist = []

  with open(leasesfile, 'r') as f:
    cat = f.read().strip('\n')
  # {endwith}
  entries = cat.splitlines()

  # fill the array with data from the leases
  if DEBUG:
    print("Existing leases:")
  for idx, line in enumerate(entries):
    if DEBUG:
      print(idx, len(line), line)
    # {endif}
    hostlist.extend([[None] * listsize])
    items = line.split()
    # T2R (expiry time)
    hostlist[idx][9] = (int(items[0]) - ux)/60
    # MAC
    hostlist[idx][3] = items[1]
    # IP
    hostlist[idx][0] = items[2]
    # hostname
    hostlist[idx][1] = items[3]
  # {endfor}
  return hostlist

def getarp(hostlist):
  """
  Get the contents of the arp table (arp -a)
  """
  listsize = len(hostlist[0])
  cmd = ["/usr/sbin/arp", "-a"]
  arp = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
  output, err = arp.communicate()
  output = output.decode("utf-8").strip('\n')
  if DEBUG:
    print("Cached by arp:")
  if DEBUG:
    print(err.decode("utf-8").strip('\n'))
    print(output)
  # {endif}
  entries = output.splitlines()

  # make a list of the leased IPs
  column0list = [hostlist[i][0] for i in range(len(hostlist))]
  if DEBUG:
    print("List of leased IPs")
    print("\t%s" % column0list)
  # {endif}

  # Add `arp` data to the array
  for idx, line in enumerate(entries):
    if DEBUG:
      print(idx, line)
    # {endif}
    items = line.split()

    # IP according to arp
    ip = items[1][1:-1]
    try:
      # first we check if the IP is already being leased
      # if not this will create an exception.
      # we use the exception to add the IP and relevant data from the arp cache
      # into the hostlist
      adx = column0list.index(ip)
      # add additional data to the existing entry
      # arp hostname
      hostlist[adx][2] = items[0].split('.')[0]
      # ipoctet4
      hostlist[adx][8] = int(ip.split('.')[3])
    except ValueError:
      # add a new entry...
      hostlist.extend([[None] * listsize])
      # ...and point there
      adx = len(hostlist)-1
      # add the relevant data from the arp cache into the hostlist
      hostlist[adx][0] = ip
      hostlist[adx][8] = int(ip.split('.')[3])
      hostlist[adx][1] = items[0].split('.')[0]
      hostlist[adx][2] = items[0].split('.')[0]
      hostlist[adx][3] = items[3]
      hostlist[adx][9] = -1
      pass
    # {endtry}

  return hostlist

def pingpong(hostlist):
  """
  Ping each host in the list and store the timings.
  """
  for idx, line in enumerate(hostlist):
    ip = line[0]
    # ping once to check for live host:
    pong = list(map(float, ping(ip, 1)))
    # if we get an answer ping 10 more times to get some stats:
    if pong[0] > 0:
      pong = list(map(float, ping(ip, 10)))
    # {endif}
    hostlist[idx][4] = pong[0]
    hostlist[idx][5] = pong[1]
    hostlist[idx][6] = pong[2]
    hostlist[idx][7] = pong[3]
    if (pong[0] == 0) and (hostlist[idx][9] is None):
      hostlist[idx][9] = 0
    # {endif}
  # {endfor}
  return hostlist

def ping(ip, cnt):
  """
  Ping the given `ip`  `cnt` times and return responsetimes
  """
  cmd = ["ping", "-w", "1", "-q", "-i", "0.5", "-c", str(cnt), ip]
  ping = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
  output, err = ping.communicate()

  # get last line of output
  line = output.decode("utf-8").splitlines()[-1]
  if DEBUG:
    print(ip, line)
  # {endif}
  # => rtt min/avg/max/mdev = 1.069/1.257/1.777/0.302 ms
  if (len(line) < 12):
    line = 'rtt min/avg/max/mdev = 0.00/0.00/0.00/0.00 ms'
  # {endif}

  # get fourth field...
  field3 = line.split()[3]
  # ==> 1.069/1.257/1.777/0.302
  # ...split the field at "/"...
  result = field3.split('/')
  # ===> ['1.036', '1.224', '1.496', '0.171']
  return result

def getkey(item):
  """
  'row' in list to sort by
  """
  return item[8]

def red(text):
  """
  Format a string to make it show red on an ANSI terminal
  """
  print("\033[91m {}\033[00m" .format(text))

def syslog_trace(trace):
  """
  Log a python stack trace to syslog
  """
  log_lines = trace.split('\n')
  for line in log_lines:
    if line:
      syslog.syslog(syslog.LOG_ALERT, line)


if __name__ == '__main__':
  # preset vars
  DEBUG = False
  PRINTPATTERN = 2
  # check for commandline parameters and take action
  for parm in sys.argv:
    if (parm == '-t'):
      PRINTPATTERN = 1
      print("show timings")
    elif (parm == '-d'):
      DEBUG = True
      print("debugging on")
    # {endif}
  # {endfor}

  try:
    ux = time.time()

    # We are keeping an array <hostlist> that holds these fields
    # for each host on the network:
    #  0 = IP
    #  1 = hostname (dhcp lease)
    #  2 = hostname (arp)
    #  3 = MAC
    #  4 = ping min
    #  5 = ping avg
    #  6 = ping max
    #  7 = ping stdev
    #  8 = IP(...4)
    #  9 = Time to release (minutes); -1 for expired
    # 10 = lastseen

    hostlist = getleases(11, ux)  # parameter is size of the array
    if DEBUG:
      print("List length (LEASES): ", len(hostlist), "\n")

    hostlist = getarp(hostlist)  # add the hosts that no longer have a lease but are still present in the arp cache
    if DEBUG:
      print("List length (ARP)   : ", len(hostlist), "\n")

    hostlist = sorted(hostlist, key=getkey)  # sort the list by the 4th IP octet
    if DEBUG:
      print("----------HOSTLIST----------")
      print(hostlist)

    hostlist = pingpong(hostlist)  # search for signs of life

    hostlist = lstvssql(hostlist)  # compare the list with the database

    # determine fieldlength of hostname for printing.
    lenhost = 0
    for idx, line in enumerate(hostlist):
      if len(hostlist[idx][1]) > lenhost:
        lenhost = len(hostlist[idx][1])
    # {endfor}

    for idx, line in enumerate(hostlist):
      spc0 = ' ' * (16 - len(line[0]))
      spc1 = ' ' * (lenhost - len(line[1]) + 1)
      spc2 = ' ' * (17 - len(line[3]) + 1)
      if (PRINTPATTERN == 1):
        print(line[0], spc0, line[1], spc1, line[3], spc2, "avg=", line[5], "\tstdev=", line[7], "\tT2R=", line[9])
      if (PRINTPATTERN == 2):
        print(line[0], spc0, line[1], spc1, line[3], spc2, "last seen :", line[10])
    # {endfor}

  except Exception as e:
    if DEBUG:
      print("Unexpected error:")
    # red(e.message)
    syslog.syslog(syslog.LOG_ALERT, e.__doc__)
    syslog_trace(traceback.format_exc())
    raise
  # {endtry}

"""
1. Get list of current leases
2. Get contents of arp cache
3. Check against DB entries
4. Ping all hosts in the list
5. Update DB with (1) new hosts and (2) last seen times
#
"""
