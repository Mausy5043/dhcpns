# Below are the commands required to recreate (without data) the table for DHCPNS

USE dhcpnsdb;
# mysql> SHOW TABLES;
# +--------------------+
# | Tables_in_dhcpnsdb |
# +--------------------+
# | lantbl             |
# +--------------------+
# 1 row in set (0.00 sec)

# +--------+
# | Table  |
# +--------+
# | lantbl |
# +--------+

DROP TABLE IF EXISTS lantbl;

CREATE TABLE `lantbl` (
  `mac` varchar(24) NOT NULL,
  `ipoctet4` varchar(3) DEFAULT NULL,
  `lastseen` datetime DEFAULT NULL,
  `nodename` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`mac`)
  ) ENGINE=InnoDB DEFAULT CHARSET=latin1 ;
