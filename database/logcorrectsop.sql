-- imai.master_module_state_agent definition

CREATE TABLE `master_module_state_agent` (
  `id` int NOT NULL AUTO_INCREMENT,
  `module` varchar(200) DEFAULT NULL,
  `state` varchar(200) DEFAULT NULL,
  `agent` varchar(200) DEFAULT NULL,
  `project` varchar(200) DEFAULT NULL,
  `user_email` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`)
);

-- imai.correct_sop definition

CREATE TABLE `correct_sop` (
  `id` int NOT NULL AUTO_INCREMENT,
  `mod_state_agent_id` int NOT NULL,
  `page_number` int DEFAULT NULL,
  `prepared_query` varchar(200) DEFAULT NULL,
  `generated_sop` varchar(200) DEFAULT NULL,
  `correct_sop` varchar(200) DEFAULT NULL,
  `sop_type` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `mod_state_agent_id` (`mod_state_agent_id`),
  CONSTRAINT `correct_sop_ibfk_1` FOREIGN KEY (`mod_state_agent_id`) REFERENCES `master_module_state_agent` (`id`)
);