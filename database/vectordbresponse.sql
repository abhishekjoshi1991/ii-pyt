-- imai.vector_db_response definition

CREATE TABLE `vector_db_response` (
  `id` int NOT NULL AUTO_INCREMENT,
  `module` varchar(200) DEFAULT NULL,
  `state` varchar(200) DEFAULT NULL,
  `agent` varchar(200) DEFAULT NULL,
  `query` varchar(200) DEFAULT NULL,
  `solution` json DEFAULT NULL,
  `user` varchar(200) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
);