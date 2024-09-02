-- imai.master_project_type definition

CREATE TABLE `master_project_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `identifier` varchar(200) DEFAULT NULL,
  `type` varchar(200) DEFAULT NULL,
  `module` varchar(200) DEFAULT NULL,
  `state` varchar(200) DEFAULT NULL,
  `agent` varchar(200) DEFAULT NULL,
  `sop_column` varchar(200) DEFAULT NULL,
  `sop_delimeter` varchar(200) DEFAULT NULL,
  `special_case1` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`)
);