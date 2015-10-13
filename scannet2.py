#! /usr/bin/python

# Scans the LAN for all hosts and reports some statistics about them

import sys, syslog, traceback
import subprocess as sp
import datetime
import MySQLdb as mdb

def lstvssql(lstOut):
  try:
    lastseen = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # connect to the database
    con = mdb.connect(host='sql.lan', user='dhcpns', passwd='MySqlDb', db='dhcpnsdb')
    # activate a cursor
    cur = con.cursor()
    # test the connection
    cur.execute("SELECT VERSION()")
    ver = cur.fetchone()
    print ver, lastseen
    for idx,line in enumerate(lstOut):
      print line[1], line[2], line[3]
      mac = line[3]
      ipoctet4 = line[8]
      nodename = line[1]
      #if nodename == "*"
      # TO DO:
      # check if MAC exists in DB
      if (len(mac) == 17):
        cmd = 'SELECT * FROM lantbl WHERE mac="' + mac +'"'
        cur.execute(cmd)
        rsl = cur.fetchone()
        if (rsl == None):
          #print "add"
          # MAC not found & host is pingable:
          if (line[5] != 0):
            cmd = ('INSERT INTO lantbl '
              '(mac, ipoctet4, lastseen, nodename) '
              'VALUES (%s, %s, %s, %s)')
            dat = ( mac, ipoctet4, lastseen, nodename )
            # - add data to DB
            print ".........", cmd, dat
            cur.execute(cmd, dat)
            con.commit()
        else:
          print "check"
          # MAC exists:
          # - update data in DB
          # - update hostname in lstOut is needed
          # - add lastseen date/time

  except mdb.Error, e:
    syslog.syslog(syslog.LOG_ALERT, e.__doc__)
    syslog_trace(traceback.format_exc())

  finally:
    if con:
        cur.close()
        con.close()

  return lstOut

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
    #lstOut[idx][8] = int(ip.split('.')[3])
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
      lstOut[adx][8] = int(ip.split('.')[3])
    except ValueError:
      lstOut = lstOut + [[None] * listsize]
      adx = len(lstOut)-1
      lstOut[adx][0] = ip
      lstOut[adx][8] = int(ip.split('.')[3])
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
    if pong[0] == 0:
      if lstOut[idx][9] == None:
        lstOut[idx][9] = 0

  return lstOut

def ping(ip,cnt):
  cmd = ["ping", "-w", "1", "-q", "-i", "0.5", "-c", str(cnt), ip]
  ping = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
  output, err = ping.communicate()

  # get last line of output
  line = output.splitlines()[-1]
  # => rtt min/avg/max/mdev = 1.069/1.257/1.777/0.302 ms
  if (len(line) < 12) :
    line = 'rtt min/avg/max/mdev = 0.00/0.00/0.00/0.00 ms'

  # get third field
  field3 = line.split()[3]
  # ==> 1.069/1.257/1.777/0.302
  # split the field at "/"
  result = field3.split('/')
  # ===> ['1.036', '1.224', '1.496', '0.171']
  return result

def getKey(item):
  return item[8]

def red(text):
  print ("\033[91m {}\033[00m" .format(text))
  return

def syslog_trace(trace):
  '''Log a python stack trace to syslog'''
  log_lines = trace.split('\n')
  for line in log_lines:
    if len(line):
      syslog.syslog(syslog.LOG_ALERT,line)

if __name__ == '__main__':
  DEBUG = False
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
      if len(lstOut[idx][1]) > lenhost:
        lenhost=len(lstOut[idx][1])
    #{endfor}

    lstOut = sorted(lstOut, key=getKey)

    lstOut = pingpong(lstOut)

    lstOut = lstvssql(lstOut)

    for idx,line in enumerate(lstOut):
      spc0 = ' ' * ( 16 - len(line[0]) )
      spc1 = ' ' * ( lenhost - len(line[1]) + 1 )
      spc2 = ' ' * ( 17 - len(line[3]) + 1 )
      print line[0], spc0, line[1], spc1, line[3], spc2, "avg=", line[5], "\tstdev=", line[7], "\tT2R=", line[9]
    #{endfor}

  except Exception as e:
    if DEBUG:
      print("Unexpected error:")
      red(e.message)
    syslog.syslog(syslog.LOG_ALERT,e.__doc__)
    syslog_trace(traceback.format_exc())
    raise
  #{endtry}
