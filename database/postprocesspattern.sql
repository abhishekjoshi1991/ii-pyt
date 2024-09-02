-- imai.postprocess_pattern definition

CREATE TABLE `postprocess_pattern` (
  `id` int NOT NULL AUTO_INCREMENT,
  `pattern` varchar(200) NOT NULL,
  `replacement` varchar(200) NOT NULL,
  `description` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`)
);