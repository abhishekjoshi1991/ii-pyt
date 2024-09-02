-- imai.severity_level_data definition

CREATE TABLE `severity_level_data` (
  `id` int NOT NULL AUTO_INCREMENT,
  `identifier` varchar(200) DEFAULT NULL,
  `troubleshoot_level` varchar(200) DEFAULT NULL,
  `troubleshoot_flow` varchar(200) DEFAULT NULL,
  `troubleshoot_descripton` varchar(200) DEFAULT NULL,
  `level_content` varchar(1000) DEFAULT NULL,
  PRIMARY KEY (`id`)
);