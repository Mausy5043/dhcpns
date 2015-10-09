#! /usr/bin/python

# Scans the LAN for all hosts and reports some statistics about them

import syslog, traceback
import subprocess as sp
import MySQLdb as mdb

def storeinsql(line):
  #print line
  return

def readsql():
  #
  return

def getuxtime():
  cmd = ["date", "+'%s'"]
  dt = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
  output, err = dt.communicate()
  entries = output.replace("'", "").splitlines()
  return entries

def getleases(listsize):
  lstOut = []
  cmd = ["cat", "/var/lib/misc/dnsmasq.leases"]
  cat = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
  output, err = cat.communicate()
  entries = output.splitlines()

  # fill the array with datafrom the leases
  for idx, line in enumerate(entries):
    if DEBUG:print idx,line
    lstOut = lstOut + [[None] * listsize]
    items = line.split()
    # IP
    ip = items[2]
    lstOut[idx][0] = ip
    lstOut[idx][8] = int(ip.split('.')[3])
    # hostname
    lstOut[idx][1] = items[3]
    # MAC
    lstOut[idx][3] = items[1]
    # T2R
    lstOut[idx][9] = (int(items[0]) - ux)/60

  return lstOut

def getarp(lstOut):
  listsize = len(lstOut[0])
  cmd = ["/usr/sbin/arp", "-a"]
  arp = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
  output, err = arp.communicate()
  if DEBUG:print err
  if DEBUG:print output
  entries = output.splitlines()

  # make a list of the IPs
  colList = [ lstOut[i][0] for i in xrange(len(lstOut)) ]
  if DEBUG:print "\t",colList

  # Add `arp` data to the array
  for idx,line in enumerate(entries):
    if DEBUG:print idx,line
    items = line.split()
    # IP according to arp
    ip=items[1][1:-1]
    try:
      adx = colList.index(ip)
      # arp hostname
      lstOut[adx][2] = items[0]
    except ValueError:
      lstOut = lstOut + [[None] * listsize]
      adx = len(lstOut)-1
      lstOut[adx][0] = ip
      lstOut[idx][8] = int(ip.split('.')[3])
      lstOut[adx][1] = items[0]
      lstOut[adx][3] = items[3]
      lstOut[adx][2] = items[0]
      lstOut[adx][9] = -1
      colList = colList + [ lstOut[i][0] ]

  return lstOut

def pingpong(lstOut):
  # Ping the hosts
  for idx,line in enumerate(lstOut):
    ip = line[0]
    pong =  map(float,ping(ip,1))
    if pong[0] > 0:
      pong =  map(float,ping(ip,10))
    lstOut[idx][4] = pong[0]
    lstOut[idx][5] = pong[1]
    lstOut[idx][6] = pong[2]
    lstOut[idx][7] = pong[3]

  return lstOut

def ping(ip,cnt):
  cmd = ["ping", "-i", "0.5", "-c", str(cnt), ip]
  ping = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
  # Get and parse output
  output, err = ping.communicate()
  if DEBUG:print "!!! ",err," !!!"
  if DEBUG:print output

  # get last line of output
  line = output.splitlines()[-1]
  # => rtt min/avg/max/mdev = 1.069/1.257/1.777/0.302 ms
  if DEBUG:print len(line)
  # get third field
  if (len(line) < 12) :
    line = 'rtt min/avg/max/mdev = 0.00/0.00/0.00/0.00 ms'

  field3 = line.split()[3]
  # ==> 1.069/1.257/1.777/0.302
  if DEBUG:print field3
  # split the field at "/"
  result = field3.split('/')
  # ===> ['1.036', '1.224', '1.496', '0.171']
  return result

def getKey(item):
  return item[8]

def red(text):
  print ("\033[91m {}\033[00m" .format(text))

def syslog_trace(trace):
	'''Log a python stack trace to syslog'''
	log_lines = trace.split('\n')
	for line in log_lines:
		if len(line):
			syslog.syslog(syslog.LOG_ALERT,line)

if __name__ == '__main__':
  DEBUG = True
  try:
    print "*** ScanNet ***"
    ux = getuxtime()
    ux = map(int,ux)[0]

    # 0 = IP
    # 1 = hostname (dhcp lease)
    # 2 = hostname (arp)
    # 3 = MAC
    # 4 = ping min
    # 5 = ping avg
    # 6 = ping max
    # 7 = ping stdev
    # 8 = IP(...4)
    # 9 = Time to release (minutes)
    lstOut = getleases(10)
    if DEBUG:print len(lstOut),"\n"

    lstOut =  getarp(lstOut)
    if DEBUG:print len(lstOut),"\n"

    lenhost=0
    for idx,line in enumerate(lstOut):
      #ip = line[0]
      # get 4th element of IP
      #lstOut[idx][8] = int(ip.split('.')[3])
      # find length of longest hostname
      if len(lstOut[idx][1]) > lenhost:
        lenhost=len(lstOut[idx][1])

    lstOut = sorted(lstOut, key=getKey)
    lstOut = pingpong(lstOut)

      storeinsql(line)
      spc0 = ' ' * ( 16 - len(line[0]) )
      spc1 = ' ' * ( lenhost - len(line[1]) + 1 )
      spc2 = ' ' * ( 17 - len(line[3]) + 1 )
      print line[0], spc0, line[1], spc1, line[3], spc2, "avg=", line[5], "\tstdev=", line[7], "\tT2R=", line[9]
  except Exception as e:
    if DEBUG:
      print("Unexpected error:")
      red(e.message)
    syslog.syslog(syslog.LOG_ALERT,e.__doc__)
    syslog_trace(traceback.format_exc())
    raise