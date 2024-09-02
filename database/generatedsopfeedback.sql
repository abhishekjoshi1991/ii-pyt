-- imai.sop_feedback definition

CREATE TABLE `sop_feedback` (
  `id` int NOT NULL AUTO_INCREMENT,
  `msa_id` int NOT NULL,
  `generated_sop` text,
  `customer_specific_sop` text,
  `modified_generated_sop` text,
  `modified_customer_specific_sop` text,
  `feedback` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `msa_id` (`msa_id`),
  CONSTRAINT `sop_feedback_ibfk_1` FOREIGN KEY (`msa_id`) REFERENCES `master_module_state_agent` (`id`)
);