/*
##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
# This file is part of openmano
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact with: nfvlabs@tid.es
##
*/


-- MySQL dump 10.13  Distrib 5.5.40, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: vim_db
-- ------------------------------------------------------
-- Server version	5.5.40-0ubuntu0.14.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `vim_db`
--

/*!40000 DROP DATABASE IF EXISTS `vim_db`*/;

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `vim_db` /*!40100 DEFAULT CHARACTER SET utf8 */;

USE `vim_db`;

--
-- Table structure for table `flavors`
--

DROP TABLE IF EXISTS `flavors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `flavors` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `description` varchar(100) DEFAULT NULL,
  `disk` smallint(5) unsigned DEFAULT NULL,
  `ram` smallint(5) unsigned DEFAULT NULL,
  `vcpus` smallint(5) unsigned DEFAULT NULL,
  `extended` varchar(2000) DEFAULT NULL COMMENT 'Extra description yaml format of needed resources and pining, orginized in sets per numa',
  `public` enum('yes','no') NOT NULL DEFAULT 'no',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='flavors with extra vnfcd info';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `host_ranking`
--

DROP TABLE IF EXISTS `host_ranking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `host_ranking` (
  `id` int(10) NOT NULL AUTO_INCREMENT,
  `family` varchar(50) NOT NULL,
  `manufacturer` varchar(50) NOT NULL,
  `version` varchar(50) NOT NULL,
  `description` varchar(50) DEFAULT NULL,
  `ranking` smallint(4) unsigned NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `family_manufacturer_version` (`family`,`manufacturer`,`version`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `hosts`
--

DROP TABLE IF EXISTS `hosts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `hosts` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `ip_name` varchar(36) NOT NULL COMMENT 'ip or or access name (must be resolved by DNS) to access the host',
  `description` varchar(100) DEFAULT NULL,
  `status` enum('ok','error','notused') NOT NULL DEFAULT 'ok',
  `ranking` smallint(6) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `features` varchar(50) DEFAULT NULL COMMENT 'features of processor',
  `user` varchar(36) NOT NULL,
  `password` varchar(36) DEFAULT NULL,
  `admin_state_up` enum('true','false') NOT NULL DEFAULT 'true',
  `RAM` mediumint(8) unsigned NOT NULL DEFAULT '0' COMMENT 'Host memory in MB not used as hugepages',
  `cpus` smallint(5) unsigned NOT NULL DEFAULT '0' COMMENT 'Host threads(or cores) not isolated from OS',
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `ip_name` (`ip_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='hosts information';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `images`
--

DROP TABLE IF EXISTS `images`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `images` (
  `uuid` varchar(36) NOT NULL,
  `path` varchar(100) NOT NULL,
  `name` varchar(36) NOT NULL,
  `description` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  `public` enum('yes','no') NOT NULL DEFAULT 'no',
  `progress` tinyint(3) unsigned NOT NULL DEFAULT '100',
  `status` enum('ACTIVE','DOWN','BUILD','ERROR') NOT NULL DEFAULT 'ACTIVE',
  `metadata` varchar(2000) DEFAULT NULL COMMENT 'Metatdata in json text format',
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `path` (`path`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `instance_devices`
--

DROP TABLE IF EXISTS `instance_devices`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `instance_devices` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` enum('usb','disk','cdrom','xml') NOT NULL,
  `xml` varchar(1000) DEFAULT NULL COMMENT 'libvirt XML format for aditional device',
  `instance_id` varchar(36) NOT NULL,
  `image_id` varchar(36) DEFAULT NULL COMMENT 'Used in case type is disk',
  `vpci` char(12) DEFAULT NULL COMMENT 'format XXXX:XX:XX.X',
  `dev` varchar(12) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK_instance_devices_instances` (`instance_id`),
  KEY `FK_instance_devices_images` (`image_id`),
  CONSTRAINT `FK_instance_devices_images` FOREIGN KEY (`image_id`) REFERENCES `tenants_images` (`image_id`),
  CONSTRAINT `FK_instance_devices_instances` FOREIGN KEY (`instance_id`) REFERENCES `instances` (`uuid`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `instances`
--

DROP TABLE IF EXISTS `instances`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `instances` (
  `uuid` varchar(36) NOT NULL,
  `flavor_id` varchar(36) NOT NULL,
  `image_id` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `description` varchar(100) DEFAULT NULL,
  `last_error` varchar(200) DEFAULT NULL,
  `progress` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `tenant_id` varchar(36) NOT NULL,
  `status` enum('ACTIVE','PAUSED','INACTIVE','CREATING','ERROR','DELETING') NOT NULL DEFAULT 'ACTIVE',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  `host_id` varchar(36) NOT NULL COMMENT 'HOST where is allocated',
  `ram` mediumint(8) unsigned NOT NULL DEFAULT '0' COMMENT 'used non-hugepages memory in MB',
  `vcpus` smallint(5) unsigned NOT NULL DEFAULT '0' COMMENT 'used non-isolated CPUs',
  PRIMARY KEY (`uuid`),
  KEY `FK_instances_tenants` (`tenant_id`),
  KEY `FK_instances_flavors` (`flavor_id`),
  KEY `FK_instances_images` (`image_id`),
  KEY `FK_instances_hosts` (`host_id`),
  CONSTRAINT `FK_instances_flavors` FOREIGN KEY (`flavor_id`) REFERENCES `tenants_flavors` (`flavor_id`),
  CONSTRAINT `FK_instances_hosts` FOREIGN KEY (`host_id`) REFERENCES `hosts` (`uuid`),
  CONSTRAINT `FK_instances_images` FOREIGN KEY (`image_id`) REFERENCES `tenants_images` (`image_id`),
  CONSTRAINT `FK_instances_tenants` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='VM instances';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `logs`
--

DROP TABLE IF EXISTS `logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `logs` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `tenant_id` varchar(36) DEFAULT NULL,
  `related` enum('hosts','images','flavors','tenants','ports','instances') DEFAULT NULL,
  `uuid` varchar(36) DEFAULT NULL COMMENT 'uuid of host, image, etc that log relates to',
  `level` enum('panic','error','info','debug','verbose') NOT NULL,
  `description` varchar(200) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3425 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nets`
--

DROP TABLE IF EXISTS `nets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `nets` (
  `uuid` varchar(36) NOT NULL,
  `tenant_id` varchar(36) DEFAULT NULL,
  `type` enum('ptp','data','bridge_data','bridge_man') NOT NULL DEFAULT 'bridge_man',
  `status` enum('ACTIVE','DOWN','BUILD','ERROR') NOT NULL DEFAULT 'ACTIVE',
  `last_error` varchar(200) DEFAULT NULL,
  `name` varchar(50) NOT NULL,
  `shared` enum('true','false') NOT NULL DEFAULT 'false',
  `admin_state_up` enum('true','false') NOT NULL DEFAULT 'true',
  `vlan` smallint(6) DEFAULT NULL,
  `bind` varchar(36) DEFAULT NULL COMMENT '''default'', ''macvtap:<iface>'',''bridge:<bridge-name>''',
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `type_vlan` (`type`,`vlan`),
  UNIQUE KEY `physical` (`bind`),
  KEY `FK_nets_tenants` (`tenant_id`),
  CONSTRAINT `FK_nets_tenants` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `numas`
--

DROP TABLE IF EXISTS `numas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `numas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `host_id` varchar(36) NOT NULL,
  `numa_socket` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `hugepages` smallint(5) unsigned NOT NULL DEFAULT '0' COMMENT 'Available memory for guest in GB',
  `status` enum('ok','error','notused') NOT NULL DEFAULT 'ok',
  `memory` smallint(5) unsigned NOT NULL DEFAULT '0' COMMENT 'total memry in GB, not all available for guests',
  `admin_state_up` enum('true','false') NOT NULL DEFAULT 'true',
  PRIMARY KEY (`id`),
  KEY `FK_numas_hosts` (`host_id`),
  CONSTRAINT `FK_numas_hosts` FOREIGN KEY (`host_id`) REFERENCES `hosts` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=47 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `of_flows`
--

DROP TABLE IF EXISTS `of_flows`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `of_flows` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(50) DEFAULT NULL,
  `net_id` varchar(50) DEFAULT NULL,
  `priority` int(10) unsigned DEFAULT NULL,
  `vlan_id` smallint(5) unsigned DEFAULT NULL,
  `ingress_port` varchar(10) DEFAULT NULL,
  `src_mac` varchar(50) DEFAULT NULL,
  `dst_mac` varchar(50) DEFAULT NULL,
  `actions` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `FK_of_flows_nets` (`net_id`),
  CONSTRAINT `FK_of_flows_nets` FOREIGN KEY (`net_id`) REFERENCES `nets` (`uuid`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=119 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `of_ports_pci_correspondence`
--

DROP TABLE IF EXISTS `of_ports_pci_correspondence`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `of_ports_pci_correspondence` (
  `id` int(10) NOT NULL AUTO_INCREMENT,
  `ip_name` varchar(50) DEFAULT NULL,
  `pci` varchar(50) DEFAULT NULL,
  `switch_port` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ports`
--

DROP TABLE IF EXISTS `ports`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ports` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(25) DEFAULT NULL,
  `instance_id` varchar(36) DEFAULT NULL,
  `tenant_id` varchar(36) DEFAULT NULL,
  `net_id` varchar(36) DEFAULT NULL,
  `vpci` char(12) DEFAULT NULL,
  `Mbps` mediumint(8) unsigned DEFAULT NULL COMMENT 'In Mbits/s',
  `admin_state_up` enum('true','false') NOT NULL DEFAULT 'true',
  `status` enum('ACTIVE','DOWN','BUILD','ERROR') NOT NULL DEFAULT 'ACTIVE',
  `type` enum('instance:bridge','instance:data','external') NOT NULL DEFAULT 'instance:bridge',
  `vlan` smallint(5) DEFAULT NULL COMMENT 'vlan of this SRIOV, or external port',
  `vlan_changed` smallint(5) DEFAULT NULL COMMENT '!=NULL when original vlan have been changed to match a pmp net with all ports in the same vlan',
  `switch_port` varchar(12) DEFAULT NULL,
  `mac` char(18) DEFAULT NULL COMMENT 'mac address format XX:XX:XX:XX:XX:XX',
  `model` varchar(12) DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `mac` (`mac`),
  UNIQUE KEY `vlan_switch_port` (`vlan`,`switch_port`),
  KEY `FK_instance_ifaces_instances` (`instance_id`),
  KEY `FK_instance_ifaces_nets` (`net_id`),
  KEY `FK_ports_tenants` (`tenant_id`),
  CONSTRAINT `FK_instance_ifaces_nets` FOREIGN KEY (`net_id`) REFERENCES `nets` (`uuid`),
  CONSTRAINT `FK_ports_instances` FOREIGN KEY (`instance_id`) REFERENCES `instances` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_ports_tenants` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Bridge interfaces used by instances';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `resources_core`
--

DROP TABLE IF EXISTS `resources_core`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `resources_core` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `numa_id` int(11) DEFAULT NULL,
  `core_id` smallint(5) unsigned NOT NULL,
  `thread_id` smallint(5) unsigned NOT NULL,
  `instance_id` varchar(36) DEFAULT NULL COMMENT 'instance that consume this resource',
  `v_thread_id` smallint(6) DEFAULT NULL COMMENT 'name used by virtual machine; -1 if this thread is not used because core is asigned completely',
  `status` enum('ok','error','notused','noteligible') NOT NULL DEFAULT 'ok' COMMENT '''error'': resource not available becasue an error at deployment; ''notused'': admin marked as not available, ''noteligible'': used by host and not available for guests',
  `paired` enum('Y','N') NOT NULL DEFAULT 'N',
  PRIMARY KEY (`id`),
  KEY `FK_resources_core_instances` (`instance_id`),
  KEY `FK_resources_core_numas` (`numa_id`),
  CONSTRAINT `FK_resources_core_instances` FOREIGN KEY (`instance_id`) REFERENCES `instances` (`uuid`),
  CONSTRAINT `FK_resources_core_numas` FOREIGN KEY (`numa_id`) REFERENCES `numas` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1073 DEFAULT CHARSET=utf8 COMMENT='Contain an entry by thread (two entries per core) of all available cores. Threy will be free if instance_id is NULL';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `resources_mem`
--

DROP TABLE IF EXISTS `resources_mem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `resources_mem` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `numa_id` int(11) NOT NULL DEFAULT '0',
  `instance_id` varchar(36) DEFAULT '0' COMMENT 'NULL is allowed in order to allow some memory not used',
  `consumed` int(3) unsigned NOT NULL DEFAULT '0' COMMENT 'In GB',
  PRIMARY KEY (`id`),
  KEY `FK_resources_mem_instances` (`instance_id`),
  KEY `FK_resources_mem_numas` (`numa_id`),
  CONSTRAINT `FK_resources_mem_instances` FOREIGN KEY (`instance_id`) REFERENCES `instances` (`uuid`) ON DELETE CASCADE,
  CONSTRAINT `FK_resources_mem_numas` FOREIGN KEY (`numa_id`) REFERENCES `numas` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=112 DEFAULT CHARSET=utf8 COMMENT='Include the hugepages memory used by one instance (VM) in one host NUMA.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `resources_port`
--

DROP TABLE IF EXISTS `resources_port`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `resources_port` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `numa_id` int(11) NOT NULL DEFAULT '0',
  `instance_id` varchar(36) DEFAULT NULL COMMENT 'Contain instance that use this resource completely. NULL if this resource is free or partially used (resources_port_SRIOV)',
  `port_id` varchar(36) DEFAULT NULL COMMENT 'When resource is used, this point to the ports table',
  `source_name` varchar(20) DEFAULT NULL,
  `pci` char(12) NOT NULL DEFAULT '0' COMMENT 'Host physical pci bus. Format XXXX:XX:XX.X',
  `Mbps` smallint(5) unsigned DEFAULT '10' COMMENT 'Nominal Port speed ',
  `root_id` int(11) DEFAULT NULL COMMENT 'NULL for physical port entries; =id for SRIOV port',
  `status` enum('ok','error','notused') NOT NULL DEFAULT 'ok',
  `Mbps_used` smallint(5) unsigned NOT NULL DEFAULT '0' COMMENT 'Speed bandwidth used when asigned',
  `vlan` smallint(5) unsigned DEFAULT NULL,
  `switch_port` varchar(12) DEFAULT NULL,
  `mac` char(18) DEFAULT NULL COMMENT 'mac address format XX:XX:XX:XX:XX:XX',
  PRIMARY KEY (`id`),
  UNIQUE KEY `mac` (`mac`),
  UNIQUE KEY `vlan_switch_port` (`vlan`,`switch_port`),
  UNIQUE KEY `port_id` (`port_id`),
  KEY `FK_resources_port_numas` (`numa_id`),
  KEY `FK_resources_port_instances` (`instance_id`),
  CONSTRAINT `FK_resources_port_instances` FOREIGN KEY (`instance_id`) REFERENCES `instances` (`uuid`),
  CONSTRAINT `FK_resources_port_numas` FOREIGN KEY (`numa_id`) REFERENCES `numas` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_resources_port_ports` FOREIGN KEY (`port_id`) REFERENCES `ports` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1296 DEFAULT CHARSET=utf8 COMMENT='Contain NIC ports SRIOV and availabes, and current use. Every port contain several entries, one per port (root_id=NULL) and all posible SRIOV (root_id=id of port)';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `schema_version`
--

DROP TABLE IF EXISTS `schema_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `schema_version` (
  `version_int` int(11) NOT NULL COMMENT 'version as a number. Must not contain gaps',
  `version` varchar(20) NOT NULL COMMENT 'version as a text',
  `openvim_ver` varchar(20) NOT NULL COMMENT 'openvim version',
  `comments` varchar(2000) DEFAULT NULL COMMENT 'changes to database',
  `date` date DEFAULT NULL,
  PRIMARY KEY (`version_int`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='database schema control version';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tenants`
--

DROP TABLE IF EXISTS `tenants`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tenants` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(50) DEFAULT NULL,
  `description` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `enabled` enum('true','false') NOT NULL DEFAULT 'true',
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='tenants information';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tenants_flavors`
--

DROP TABLE IF EXISTS `tenants_flavors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tenants_flavors` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `flavor_id` varchar(36) NOT NULL,
  `tenant_id` varchar(36) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `FK__tenants` (`tenant_id`),
  KEY `FK__flavors` (`flavor_id`),
  CONSTRAINT `FK__flavors` FOREIGN KEY (`flavor_id`) REFERENCES `flavors` (`uuid`),
  CONSTRAINT `FK__tenants` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=121 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tenants_images`
--

DROP TABLE IF EXISTS `tenants_images`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tenants_images` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `image_id` varchar(36) NOT NULL,
  `tenant_id` varchar(36) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `FK_tenants_images_tenants` (`tenant_id`),
  KEY `FK_tenants_images_images` (`image_id`),
  CONSTRAINT `FK_tenants_images_images` FOREIGN KEY (`image_id`) REFERENCES `images` (`uuid`),
  CONSTRAINT `FK_tenants_images_tenants` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=72 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `uuids`
--

DROP TABLE IF EXISTS `uuids`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `uuids` (
  `uuid` varchar(36) NOT NULL,
  `root_uuid` varchar(36) DEFAULT NULL COMMENT 'Some related UUIDs can be grouped by this field, so that they can be deleted at once',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `used_at` enum('flavors','hosts','images','instances','nets','ports','tenants') DEFAULT NULL COMMENT 'Table that uses this UUID',
  PRIMARY KEY (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Used to avoid UUID repetitions';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'vim_db'
--
/*!50003 DROP PROCEDURE IF EXISTS `GetAvailablePorts` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE PROCEDURE `GetAvailablePorts`(IN `Numa` INT)
    DETERMINISTIC
    SQL SECURITY INVOKER
BEGIN
SELECT port_id, pci, Mbps, Mbps - Mbps_consumed as Mbps_free, totalSRIOV - coalesce(usedSRIOV,0) as availableSRIOV, switch_port, mac
FROM
	(
	   SELECT id as port_id, Mbps, pci, switch_port, mac
	   FROM resources_port  
		WHERE numa_id = Numa AND id=root_id AND status = 'ok' AND switch_port is not Null AND instance_id IS NULL
	) as A
	INNER JOIN
	(
	   SELECT root_id, sum(Mbps_used) as Mbps_consumed, COUNT(id)-1 as totalSRIOV
		FROM resources_port  
		WHERE numa_id = Numa AND status = 'ok'
		GROUP BY root_id
	) as B
	ON A.port_id = B.root_id
	LEFT JOIN
	(
	   SELECT root_id,  COUNT(id) as usedSRIOV
		FROM resources_port  
		WHERE numa_id = Numa AND status = 'ok' AND instance_id IS NOT NULL AND switch_port is not Null
		GROUP BY root_id
	) as C
	ON A.port_id = C.root_id

ORDER BY Mbps_free, availableSRIOV, pci
;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `GetHostByMemCpu` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE PROCEDURE `GetHostByMemCpu`(IN `Needed_mem` INT, IN `Needed_cpus` INT)
    SQL SECURITY INVOKER
    COMMENT 'Obtain those hosts with the available free Memory(Non HugePages) and CPUS (Non isolated)'
BEGIN

SELECT * 
FROM hosts as H
LEFT JOIN (
	SELECT sum(ram) as used_ram, sum(vcpus) as used_cpus, host_id
	FROM instances
	GROUP BY host_id
) as U ON U.host_id = H.uuid
WHERE Needed_mem<=H.RAM-coalesce(U.used_ram,0) AND Needed_cpus<=H.cpus-coalesce(U.used_cpus,0) AND H.admin_state_up = 'true' 
ORDER BY RAM-coalesce(U.used_ram,0), cpus-coalesce(U.used_cpus,0)

;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `GetIfaces` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE PROCEDURE `GetIfaces`()
    SQL SECURITY INVOKER
    COMMENT 'Used for the http get ports'
BEGIN

SELECT *, 'ACTIVE' as status,'true' as admin_state_up FROM
(
	(
		SELECT ifa.uuid as id, ifa.name as name, instance_id as device_id, net_id, tenant_id
		FROM instance_ifaces AS ifa JOIN instances AS i on ifa.instance_id=i.uuid
	) 
	UNION
	(
		SELECT iface_uuid as id, ifa.name as name, instance_id as device_id, net_id,tenant_id
		FROM resources_port  AS ifa JOIN instances AS i on ifa.instance_id=i.uuid
		WHERE iface_uuid is not NULL
	) 
	UNION
	(
		SELECT uuid as id, name, Null as device_id, net_id, Null as tenant_id
		FROM external_ports 
	) 
) as B 
;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `GetNextAutoIncrement` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE PROCEDURE `GetNextAutoIncrement`()
    SQL SECURITY INVOKER
BEGIN
SELECT table_name, AUTO_INCREMENT
FROM information_schema.tables
WHERE table_name = 'resources_port'
AND table_schema = DATABASE( ) ;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `GetNumaByCore` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE PROCEDURE `GetNumaByCore`(IN `Needed_cores` SMALLINT)
    SQL SECURITY INVOKER
    COMMENT 'Obtain Numas with a concrete number of available cores, with bot'
BEGIN

SELECT numa_id, host_id, numa_socket, freecores FROM
(
    SELECT numa_id, COUNT(core_id) as freecores FROM
    (
        SELECT numa_id, core_id, COUNT(thread_id) AS freethreads
		  FROM resources_core 
		  WHERE instance_id IS NULL AND status = 'ok' 
		  GROUP BY numa_id, core_id
    ) AS FREECORES_TABLE
    WHERE FREECORES_TABLE.freethreads = 2
    GROUP BY numa_id  
) AS NBCORES_TABLE 
INNER JOIN numas ON numas.id = NBCORES_TABLE.numa_id
INNER JOIN hosts ON numas.host_id = hosts.uuid

WHERE NBCORES_TABLE.freecores >= Needed_cores AND numas.status = 'ok' AND numas.admin_state_up = 'true' AND hosts.admin_state_up = 'true'
ORDER BY NBCORES_TABLE.freecores
;

END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `GetNumaByMemory` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE PROCEDURE `GetNumaByMemory`(IN `Needed_mem` SMALLINT)
    DETERMINISTIC
    SQL SECURITY INVOKER
    COMMENT 'Obtain numas with a free quantity of memory, passed by parameter'
BEGIN
SELECT * FROM 
(   SELECT numas.id as numa_id, numas.host_id, numas.numa_socket, numas.hugepages, numas.hugepages - sum(coalesce(resources_mem.consumed,0)) AS freemem
    FROM numas 
	 LEFT JOIN resources_mem ON numas.id = resources_mem.numa_id
    JOIN hosts ON numas.host_id = hosts.uuid
    WHERE numas.status = 'ok' AND numas.admin_state_up = 'true' AND hosts.admin_state_up = 'true'
    GROUP BY numas.id
) AS COMBINED

WHERE COMBINED.freemem >= Needed_mem
ORDER BY COMBINED.freemem
;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `GetNumaByPort` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE PROCEDURE `GetNumaByPort`(IN `Needed_speed` SMALLINT, IN `Needed_ports` SMALLINT)
    SQL SECURITY INVOKER
    COMMENT 'Busca Numas con N puertos fisicos LIBRES de X velocidad'
BEGIN

SELECT numa_id, COUNT(id) AS number_ports  
FROM
(
	SELECT root_id AS id, status, numa_id, Mbps, SUM(Mbps_used) AS Consumed
	FROM resources_port 
	GROUP BY root_id
) AS P
WHERE status = 'ok' AND switch_port is not Null AND Consumed = 0 AND Mbps >= Needed_speed
GROUP BY numa_id
HAVING number_ports  >= Needed_ports
;

END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `GetNumaByThread` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE PROCEDURE `GetNumaByThread`(IN `Needed_threads` SMALLINT)
    SQL SECURITY INVOKER
BEGIN

SELECT numa_id, host_id, numa_socket, freethreads
FROM
(
	SELECT numa_id, COUNT(thread_id) AS freethreads
	FROM resources_core 
	WHERE instance_id IS NULL AND status = 'ok' 
	GROUP BY numa_id
) AS NBCORES_TABLE 
INNER JOIN numas ON numas.id = NBCORES_TABLE.numa_id
INNER JOIN hosts ON numas.host_id = hosts.uuid

WHERE NBCORES_TABLE.freethreads >= Needed_threads AND numas.status = 'ok' AND numas.admin_state_up = 'true' AND hosts.admin_state_up = 'true'
ORDER BY NBCORES_TABLE.freethreads
;

END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `GetPortsFromNuma` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE PROCEDURE `GetPortsFromNuma`(IN `Numa` INT)
    NO SQL
    SQL SECURITY INVOKER
BEGIN
SELECT Mbps, pci, status, Mbps_consumed  
FROM
(
   SELECT id, Mbps, pci, status
   FROM resources_port  
	WHERE numa_id = Numa AND id=root_id AND status='ok' AND switch_port is not Null
) as A
INNER JOIN
(
   SELECT root_id, sum(Mbps_used) as Mbps_consumed
	FROM resources_port  
	WHERE numa_id = Numa 
	GROUP BY root_id
) as B
ON A.id = B.root_id
;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `UpdateSwitchPort` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE PROCEDURE `UpdateSwitchPort`()
    SQL SECURITY INVOKER
BEGIN





UPDATE
	resources_port INNER JOIN (
		SELECT resources_port.id,KK.switch_port  
		FROM resources_port INNER JOIN numas on resources_port.numa_id=numas.id
			INNER JOIN hosts on numas.host_id=hosts.uuid
			INNER JOIN of_ports_pci_correspondence as KK on hosts.ip_name=KK.ip_name and resources_port.pci=KK.pci
		) as TABLA
	ON  resources_port.root_id=TABLA.id
SET resources_port.switch_port=TABLA.switch_port
WHERE resources_port.root_id=TABLA.id
;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2015-02-09 15:49:57





-- MySQL dump 10.13  Distrib 5.5.35, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: vim_db
-- ------------------------------------------------------
-- Server version	5.5.35-1ubuntu1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `schema_version`
--

LOCK TABLES `schema_version` WRITE;
/*!40000 ALTER TABLE `schema_version` DISABLE KEYS */;
INSERT INTO `schema_version` VALUES (1,'0.1','0.2.00','insert schema_version; alter nets with last_error column','2015-05-05');
/*!40000 ALTER TABLE `schema_version` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2015-04-30 10:14:40
