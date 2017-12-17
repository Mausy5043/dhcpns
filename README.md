# dhcpns
Executables for DHCP/DNS servers running `dnsmasq`

Keeps track of network clients
* node or computer name
* IP-address assigned
* machine specific MAC-address 
* date/time last seen
* optional: ping min/avg/max and time until IP needs to be renewed

Requires `dnsmasq`.

This also assumes you have a MySQL server on the local network.
Make sure you create a database called `dhcpnsdb`.

Create a file (`~/.dns.cnf`) containing
```
[client]
user=dhcpns
password="MySqlDbPassword"
```
(pick a safe password)

On the MySQL server create a user `dhcpns` with the password you picked and priviledges on the `dhcpnsdb` database. 
