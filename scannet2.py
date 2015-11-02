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
    print "SQL database version: ", ver
    print "Scan performed on:    ", lastseen
    for idx,line in enumerate(lstOut):
      mac = line[3]
      ipoctet4 = str(line[8]).zfill(3)
      nodename = line[1]
      # check if MAC exists in DB
      if (len(mac) == 17):
        # MAC is valid: search for it in the DB
        cmd = ('SELECT * '
                'FROM lantbl '
                'WHERE mac="' + mac +'"' )
        cur.execute(cmd)
        rsl = cur.fetchone()
        if (rsl == None):
          # MAC is not found in db
          if (line[5] != 0):
            # & host is pingable -> new host, so add it to the DB
            cmd = ('INSERT INTO lantbl '
                    '(mac, ipoctet4, lastseen, nodename) '
                    'VALUES (%s, %s, %s, %s)')
            dat = ( mac, ipoctet4, lastseen, nodename )
            syslog.syslog(syslog.LOG_NOTICE, "INSERTed " + mac + " @ " + nodename)
            cur.execute(cmd, dat)
            con.commit()
            line[10] = lastseen
          #{endif}
        else:
          # MAC is found in db
          if (line[5] != 0):
            # & host is pingable -> update data in DB
            cmd = ('UPDATE lantbl '
                    'SET lastseen = %s, nodename = %s, ipoctet4 = %s '
                    'WHERE mac = %s ')
            dat = ( lastseen, nodename, ipoctet4, mac )
            cur.execute(cmd, dat)
            con.commit()
            line[10] = lastseen
          else:
            # & host is not pingable -> update local data (arp-data may be stale)
            #print "exists in DB; not pingable. Local data may not be up-to-date."
            #print "update info ", mac, rsl
            #print line[1],line[2]
            line[1] = "* " + rsl[3]
            line[2] = "* " + rsl[3]
            line[10] = rsl[2]
          #{endif}
        #{endif}
      else:
        #sometimes nodename = "?" and mac = "<incomplete>"
        if (nodename == "?"):
          #then lookup the last user of the IP-address
          cmd = ('SELECT * '
                  'FROM lantbl '
                  'WHERE ipoctet4="' + ipoctet4 +'"' )
          cur.execute(cmd)
          rsl = cur.fetchone()
          # example output
          # rsl <= ('00:00:00:00:00:00', '182', datetime.datetime(2015, 10, 18, 14, 45, 26), 'hostname')
          line[1] = "-" + rsl[3]
          line[2] = "-" + rsl[3]
          line[3] = "-" + rsl[0]
          line[10] = rsl[2]
        else:
          print nodename, mac, ipoctet4
      #{endif}
    #{endfor}
  except mdb.Error, e:
    print e.__doc__
    syslog.syslog(syslog.LOG_ALERT, e.__doc__)
    syslog_trace(traceback.format_exc())
  finally:
    if con:
        cur.close()
        con.close()
  #{endtry}
  return lstOut

def readsql():
  # SELECT * FROM lantbl ORDER BY (ipoctet4);
  return

def getuxtime():
  cmd = ["date", "+'%s'"]
  dt = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
  output, err = dt.communicate()
  entries = output.replace("'", "").splitlines()
  return entries

# read the contents /var/lib/misc/dnsmasq.leases
def getleases(listsize):
  lstOut = []
  fi = "/var/lib/misc/dnsmasq.leases"
  f    = file(fi,'r')
  cat = f.read().strip('\n').replace(" ",", ").replace("/",", ")
  f.close()
  if DEBUG:print cat
  
  cmd = ["cat", fi]
  cat = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
  output, err = cat.communicate()
  entries = output.splitlines()
  if DEBUG:print entries

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

# get the contnets of the arp table (arp -a)
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

# ping each host
def pingpong(lstOut):
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
  lsa = len(sys.argv)
  if (lsa == 1):
    sw = 2
  else:
    sw = 2
    if (sys.argv[1] == '-t'):
      sw = 1
    #{endif}
  #{endif}
  try:
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
    #10 = lastseen
    lstOut = getleases(11)  # parameter is size of the array
    if DEBUG:print len(lstOut),"\n"

    lstOut =  getarp(lstOut) # add the hosts that no longer have a lease but are still present in the arp cache
    if DEBUG:print len(lstOut),"\n"

    lstOut = sorted(lstOut, key=getKey) # sort the list by IP octet 4

    lstOut = pingpong(lstOut) # search for signs of life

    lstOut = lstvssql(lstOut) # compare the list with the database

    # determine fieldlength of hostname for printing.
    lenhost=0
    for idx,line in enumerate(lstOut):
      if len(lstOut[idx][1]) > lenhost:
        lenhost=len(lstOut[idx][1])
    #{endfor}

    for idx,line in enumerate(lstOut):
      spc0 = ' ' * ( 16 - len(line[0]) )
      spc1 = ' ' * ( lenhost - len(line[1]) + 1 )
      spc2 = ' ' * ( 17 - len(line[3]) + 1 )
      if (sw == 1):
        print line[0], spc0, line[1], spc1, line[3], spc2, "avg=", line[5], "\tstdev=", line[7], "\tT2R=", line[9]
      if (sw == 2):
        print line[0], spc0, line[1], spc1, line[3], spc2, "last seen :", line[10]
    #{endfor}

  except Exception as e:
    if DEBUG:
      print("Unexpected error:")
      red(e.message)
    syslog.syslog(syslog.LOG_ALERT,e.__doc__)
    syslog_trace(traceback.format_exc())
    raise
  #{endtry}
