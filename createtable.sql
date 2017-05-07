USE dhcpnsdb;

DROP TABLE IF EXISTS lantbl;

CREATE TABLE `lantbl` (
  `mac` varchar(24) NOT NULL,
  `ipoctet4` varchar(3) DEFAULT NULL,
  `lastseen` datetime DEFAULT NULL,
  `nodename` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`mac`),
  INDEX (`ipoctet4`),
  INDEX (`lastseen`),
  INDEX (`nodename`)
  ) ENGINE=InnoDB DEFAULT CHARSET=latin1 ;
