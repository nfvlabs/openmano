/**
* Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
* This file is part of openmano
* All Rights Reserved.
*
* Licensed under the Apache License, Version 2.0 (the "License"); you may
* not use this file except in compliance with the License. You may obtain
* a copy of the License at
*
*         http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
* WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
* License for the specific language governing permissions and limitations
* under the License.
*
* For those usages not covered by the Apache License, Version 2.0 please
* contact with: nfvlabs@tid.es
**/
-- MySQL dump 10.13  Distrib 5.5.35, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: mano_db
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
-- Current Database: `mano_db`
--

/*!40000 DROP DATABASE IF EXISTS `mano_db`*/;

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `mano_db` /*!40100 DEFAULT CHARACTER SET latin1 */;

USE `mano_db`;

--
-- Table structure for table `datacenter_nets`
--

DROP TABLE IF EXISTS `datacenter_nets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `datacenter_nets` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL COMMENT 'To match with sce_nets',
  `vim_net_id` varchar(36) NOT NULL,
  `datacenter_id` varchar(36) NOT NULL,
  `type` enum('bridge','data','ptp') NOT NULL DEFAULT 'data' COMMENT 'Type of network',
  `multipoint` enum('true','false') NOT NULL DEFAULT 'true',
  `shared` enum('true','false') NOT NULL DEFAULT 'false' COMMENT 'If can be shared with serveral scenarios',
  `description` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name_datacenter_id` (`name`,`datacenter_id`),
  KEY `FK_datacenter_nets_datacenters` (`datacenter_id`),
  CONSTRAINT `FK_datacenter_nets_datacenters` FOREIGN KEY (`datacenter_id`) REFERENCES `datacenters` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Contain the external nets of a datacenter';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `datacenters`
--

DROP TABLE IF EXISTS `datacenters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `datacenters` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `description` varchar(100) DEFAULT NULL,
  `type` enum('openvim','openstack') NOT NULL DEFAULT 'openvim',
  `vim_url` varchar(150) NOT NULL COMMENT 'URL of the VIM for the REST API',
  `vim_url_admin` varchar(150) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Datacenters managed by the NFVO.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `instance_interfaces`
--

DROP TABLE IF EXISTS `instance_interfaces`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `instance_interfaces` (
  `uuid` varchar(36) NOT NULL,
  `instance_vm_id` varchar(36) NOT NULL,
  `instance_net_id` varchar(36) NOT NULL,
  `interface_id` varchar(36) NOT NULL,
  `vim_interface_id` varchar(36) NOT NULL COMMENT 'vim identity for that interface',
  `type` enum('internal','external') NOT NULL COMMENT 'Indicates if this interface is external to a vnf, or internal',
  PRIMARY KEY (`uuid`),
  KEY `FK_instance_vms` (`instance_vm_id`),
  KEY `FK_instance_nets` (`instance_net_id`),
  KEY `FK_instance_ids` (`interface_id`),
  CONSTRAINT `FK_instance_ids` FOREIGN KEY (`interface_id`) REFERENCES `interfaces` (`uuid`),
  CONSTRAINT `FK_instance_nets` FOREIGN KEY (`instance_net_id`) REFERENCES `instance_nets` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_instance_vms` FOREIGN KEY (`instance_vm_id`) REFERENCES `instance_vms` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Table with all running associattion among VM instances and net instances';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `instance_nets`
--

DROP TABLE IF EXISTS `instance_nets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `instance_nets` (
  `uuid` varchar(36) NOT NULL,
  `vim_net_id` varchar(36) NOT NULL COMMENT 'Network ID in the VIM DB',
  `instance_scenario_id` varchar(36) NOT NULL,
  `status` enum('ACTIVE','DOWN','BUILD','ERROR') NOT NULL DEFAULT 'BUILD',
  `multipoint` enum('true','false') NOT NULL DEFAULT 'true',
  `external` enum('true','false') NOT NULL DEFAULT 'false' COMMENT 'If external, means that it already exists at VIM',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `vim_net_id_instance_scenario_id` (`vim_net_id`,`instance_scenario_id`),
  KEY `FK_instance_nets_instance_scenarios` (`instance_scenario_id`),
  CONSTRAINT `FK_instance_nets_instance_scenarios` FOREIGN KEY (`instance_scenario_id`) REFERENCES `instance_scenarios` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Instances of networks';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `instance_scenarios`
--

DROP TABLE IF EXISTS `instance_scenarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `instance_scenarios` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `scenario_id` varchar(36) NOT NULL,
  `nfvo_tenant_id` varchar(36) NOT NULL,
  `vim_tenant_id` varchar(36) NOT NULL,
  `datacenter_id` varchar(36) NOT NULL,
  `description` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name` (`name`),
  KEY `FK_scenarios_nfvo_tenants` (`nfvo_tenant_id`),
  KEY `FK_instance_scenarios_vim_tenants` (`vim_tenant_id`),
  KEY `FK_instance_scenarios_datacenters` (`datacenter_id`),
  KEY `FK_instance_scenarios_scenarios` (`scenario_id`),
  CONSTRAINT `FK_instance_scenarios_datacenters` FOREIGN KEY (`datacenter_id`) REFERENCES `datacenters` (`uuid`),
  CONSTRAINT `FK_instance_scenarios_nfvo_tenants` FOREIGN KEY (`nfvo_tenant_id`) REFERENCES `nfvo_tenants` (`uuid`),
  CONSTRAINT `FK_instance_scenarios_scenarios` FOREIGN KEY (`scenario_id`) REFERENCES `scenarios` (`uuid`),
  CONSTRAINT `FK_instance_scenarios_vim_tenants` FOREIGN KEY (`vim_tenant_id`) REFERENCES `vim_tenants` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Instances of scenarios defined by the user';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `instance_vms`
--

DROP TABLE IF EXISTS `instance_vms`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `instance_vms` (
  `uuid` varchar(36) NOT NULL,
  `instance_vnf_id` varchar(36) NOT NULL,
  `vm_id` varchar(36) NOT NULL,
  `vim_vm_id` varchar(36) NOT NULL COMMENT 'VM ID in the VIM DB',
  `status` enum('ACTIVE','PAUSED','INACTIVE','CREATING','ERROR','DELETING') NOT NULL DEFAULT 'CREATING',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `vim_vm_id` (`vim_vm_id`),
  KEY `FK_instance_vms_vms` (`vm_id`),
  KEY `FK_instance_vms_instance_vnfs` (`instance_vnf_id`),
  CONSTRAINT `FK_instance_vms_instance_vnfs` FOREIGN KEY (`instance_vnf_id`) REFERENCES `instance_vnfs` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_instance_vms_vms` FOREIGN KEY (`vm_id`) REFERENCES `vms` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Instances of VMs as part of VNF instances';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `instance_vnfs`
--

DROP TABLE IF EXISTS `instance_vnfs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `instance_vnfs` (
  `uuid` varchar(36) NOT NULL,
  `instance_scenario_id` varchar(36) NOT NULL,
  `vnf_id` varchar(36) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  KEY `FK_instance_vnfs_vnfs` (`vnf_id`),
  KEY `FK_instance_vnfs_instance_scenarios` (`instance_scenario_id`),
  CONSTRAINT `FK_instance_vnfs_instance_scenarios` FOREIGN KEY (`instance_scenario_id`) REFERENCES `instance_scenarios` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_instance_vnfs_vnfs` FOREIGN KEY (`vnf_id`) REFERENCES `vnfs` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Instances of VNFs as part of a scenario';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `interfaces`
--

DROP TABLE IF EXISTS `interfaces`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `interfaces` (
  `uuid` varchar(36) NOT NULL,
  `internal_name` varchar(25) NOT NULL,
  `external_name` varchar(25) DEFAULT NULL COMMENT 'NULL if the interface is not an external interface',
  `vm_id` varchar(36) NOT NULL,
  `net_id` varchar(36) DEFAULT NULL,
  `type` enum('mgmt','bridge','data') NOT NULL DEFAULT 'data' COMMENT 'Type of network',
  `vpci` char(12) DEFAULT NULL,
  `bw` mediumint(8) unsigned DEFAULT NULL COMMENT 'BW expressed in Mbits/s. Maybe this field is not necessary.',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  `model` varchar(12) DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `internal_name_vm_id` (`internal_name`,`vm_id`),
  KEY `FK_interfaces_vms` (`vm_id`),
  KEY `FK_interfaces_nets` (`net_id`),
  CONSTRAINT `FK_interfaces_nets` FOREIGN KEY (`net_id`) REFERENCES `nets` (`uuid`) ON DELETE CASCADE,
  CONSTRAINT `FK_interfaces_vms` FOREIGN KEY (`vm_id`) REFERENCES `vms` (`uuid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='VM interfaces';
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
  `nfvo_tenant_id` varchar(36) DEFAULT NULL,
  `related` enum('nfvo_tenants','datacenters','vim_tenants','tenants_datacenters','vnfs','vms','interfaces','nets','scenarios','sce_vnfs','sce_interfaces','sce_nets','instance_scenarios','instance_vnfs','instance_vms','instance_nets','instance_interfaces') NOT NULL COMMENT 'Relevant element for the log',
  `uuid` varchar(36) DEFAULT NULL COMMENT 'Uuid of vnf, scenario, etc. that log relates to',
  `level` enum('panic','error','info','debug','verbose') NOT NULL,
  `description` varchar(200) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3286 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nets`
--

DROP TABLE IF EXISTS `nets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `nets` (
  `uuid` varchar(36) NOT NULL,
  `vnf_id` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `type` enum('bridge','data','ptp') NOT NULL DEFAULT 'data' COMMENT 'Type of network',
  `multipoint` enum('true','false') NOT NULL DEFAULT 'false',
  `description` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `vnf_id_name` (`vnf_id`,`name`),
  CONSTRAINT `FK_nets_vnfs` FOREIGN KEY (`vnf_id`) REFERENCES `vnfs` (`uuid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Networks in a VNF definition. These are only the internal networks among VMs of the same VNF.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nfvo_tenants`
--

DROP TABLE IF EXISTS `nfvo_tenants`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `nfvo_tenants` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `description` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Scenarios defined by the user';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sce_interfaces`
--

DROP TABLE IF EXISTS `sce_interfaces`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sce_interfaces` (
  `uuid` varchar(36) NOT NULL,
  `sce_vnf_id` varchar(36) NOT NULL,
  `sce_net_id` varchar(36) DEFAULT NULL,
  `interface_id` varchar(36) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  KEY `FK_sce_interfaces_sce_vnfs` (`sce_vnf_id`),
  KEY `FK_sce_interfaces_sce_nets` (`sce_net_id`),
  KEY `FK_sce_interfaces_interfaces` (`interface_id`),
  CONSTRAINT `FK_sce_interfaces_interfaces` FOREIGN KEY (`interface_id`) REFERENCES `interfaces` (`uuid`),
  CONSTRAINT `FK_sce_interfaces_sce_nets` FOREIGN KEY (`sce_net_id`) REFERENCES `sce_nets` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_sce_interfaces_sce_vnfs` FOREIGN KEY (`sce_vnf_id`) REFERENCES `sce_vnfs` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='VNF interfaces in a scenario definition.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sce_nets`
--

DROP TABLE IF EXISTS `sce_nets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sce_nets` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) DEFAULT NULL,
  `scenario_id` varchar(36) DEFAULT NULL COMMENT 'NULL if net is matched to several scenarios',
  `type` enum('bridge','data','ptp') NOT NULL DEFAULT 'data' COMMENT 'Type of network',
  `multipoint` enum('true','false') NOT NULL DEFAULT 'true',
  `external` enum('true','false') NOT NULL DEFAULT 'false' COMMENT 'If external, net is already present at VIM',
  `description` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  `graph` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  KEY `FK_sce_nets_scenarios` (`scenario_id`),
  CONSTRAINT `FK_sce_nets_scenarios` FOREIGN KEY (`scenario_id`) REFERENCES `scenarios` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Networks in a scenario definition. It only considers networks among VNFs. Networks among internal VMs are only considered in tble ''nets''.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sce_vnfs`
--

DROP TABLE IF EXISTS `sce_vnfs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sce_vnfs` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `scenario_id` varchar(36) NOT NULL,
  `vnf_id` varchar(36) NOT NULL,
  `description` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  `graph` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name_scenario_id` (`name`,`scenario_id`),
  KEY `FK_sce_vnfs_scenarios` (`scenario_id`),
  KEY `FK_sce_vnfs_vnfs` (`vnf_id`),
  CONSTRAINT `FK_sce_vnfs_scenarios` FOREIGN KEY (`scenario_id`) REFERENCES `scenarios` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_sce_vnfs_vnfs` FOREIGN KEY (`vnf_id`) REFERENCES `vnfs` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='VNFs in scenario definitions. This table also contains the Physical Network Functions and the external elements such as MAN, Core, etc.\r\n';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `scenarios`
--

DROP TABLE IF EXISTS `scenarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `scenarios` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `nfvo_tenant_id` varchar(36) DEFAULT NULL,
  `description` varchar(100) DEFAULT NULL,
  `public` enum('true','false') NOT NULL DEFAULT 'false',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name` (`name`),
  KEY `FK_scenarios_nfvo_tenants` (`nfvo_tenant_id`),
  CONSTRAINT `FK_scenarios_nfvo_tenants` FOREIGN KEY (`nfvo_tenant_id`) REFERENCES `nfvo_tenants` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Scenarios defined by the user';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tenants_datacenters`
--

DROP TABLE IF EXISTS `tenants_datacenters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tenants_datacenters` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nfvo_tenant_id` varchar(36) NOT NULL,
  `datacenter_id` varchar(36) NOT NULL,
  `vim_tenant_id` varchar(36) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `datacenter_nfvo_tenant` (`datacenter_id`,`nfvo_tenant_id`),
  KEY `FK_nfvo_tenants_datacenters` (`datacenter_id`),
  KEY `FK_nfvo_tenants_vim_tenants` (`vim_tenant_id`),
  KEY `FK_tenants_datacenters_nfvo_tenants` (`nfvo_tenant_id`),
  CONSTRAINT `FK_tenants_datacenters_datacenters` FOREIGN KEY (`datacenter_id`) REFERENCES `datacenters` (`uuid`),
  CONSTRAINT `FK_tenants_datacenters_nfvo_tenants` FOREIGN KEY (`nfvo_tenant_id`) REFERENCES `nfvo_tenants` (`uuid`),
  CONSTRAINT `FK_tenants_datacenters_vim_tenants` FOREIGN KEY (`vim_tenant_id`) REFERENCES `vim_tenants` (`uuid`)
) ENGINE=InnoDB AUTO_INCREMENT=85 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Scenarios defined by the user';
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
  `used_at` enum('nfvo_tenants','datacenters','vim_tenants','vnfs','vms','interfaces','nets','scenarios','sce_vnfs','sce_interfaces','sce_nets','instance_scenarios','instance_vnfs','instance_vms','instance_nets','instance_interfaces') DEFAULT NULL COMMENT 'Table that uses this UUID',
  PRIMARY KEY (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table with all unique IDs used to avoid UUID repetitions among different elements';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `vim_tenants`
--

DROP TABLE IF EXISTS `vim_tenants`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `vim_tenants` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `vim_tenant_id` varchar(36) NOT NULL COMMENT 'Tenant ID in the VIM DB',
  `created` enum('true','false') NOT NULL DEFAULT 'false' COMMENT 'Indicates if this tenant has been created by openmano, or it existed on VIM',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `vim_tenant_id` (`vim_tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='Scenarios defined by the user';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `vms`
--

DROP TABLE IF EXISTS `vms`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `vms` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `vnf_id` varchar(36) NOT NULL,
  `vim_flavor_id` varchar(36) NOT NULL COMMENT 'Flavor ID in the VIM DB',
  `vim_image_id` varchar(36) NOT NULL COMMENT 'Image ID in the VIM DB',
  `image_path` varchar(100) NOT NULL COMMENT 'Path where the image of the VM is located',
  `description` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name_vnf_id` (`name`,`vnf_id`),
  KEY `FK_vms_vnfs` (`vnf_id`),
  CONSTRAINT `FK_vms_vnfs` FOREIGN KEY (`vnf_id`) REFERENCES `vnfs` (`uuid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='VM definitions. It contains the set of VMs used by the VNF definitions.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `vnfs`
--

DROP TABLE IF EXISTS `vnfs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `vnfs` (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `path` varchar(100) DEFAULT NULL COMMENT 'Path where the YAML descriptor of the VNF can be found. NULL if it is a physical network function.',
  `physical` enum('true','false') NOT NULL DEFAULT 'false',
  `public` enum('true','false') NOT NULL DEFAULT 'true',
  `description` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified_at` timestamp NULL DEFAULT NULL,
  `class` varchar(36) DEFAULT 'MISC',
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `path` (`path`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT COMMENT='VNF definitions. This is the catalogue of VNFs. It also includes Physical Network Functions or Physical Elements.\r\n';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'mano_db'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2015-03-11 17:34:28
