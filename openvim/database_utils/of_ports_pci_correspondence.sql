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

/* This table contains the matching between dataplane host ports 
   and openflow switch ports. 
   The two first column identifies the host and the pci bus
   Last column identifies the switch port name
   command ethtool -i provides the pci bus port
   command ethtool -p makes this port blinking
   finally openvim prints at starting the openflow ports naming 
   NOTE: if a host has already been inserted, you must execute 
   UpdateSwitchPort database procedure to associate ports with 
   the switch connection
*/

LOCK TABLES `of_ports_pci_correspondence` WRITE;

INSERT INTO `of_ports_pci_correspondence` 
    (ip_name, pci, switch_port)
VALUES
    ('nfv102.hi.inet', '0000:44:00.1', 'Te0/8'),
    ('nfv102.hi.inet', '0000:44:00.0', 'Te0/9'),
    ('nfv102.hi.inet', '0000:43:00.1', 'Te0/10'),
    ('nfv102.hi.inet', '0000:43:00.0', 'Te0/11'),
    ('nfv102.hi.inet', '0000:04:00.0', 'Te0/12'),
    ('nfv102.hi.inet', '0000:04:00.1', 'Te0/13'),
    ('nfv102.hi.inet', '0000:06:00.0', 'Te0/14'),
    ('nfv102.hi.inet', '0000:06:00.1', 'Te0/15'),
    ('nfv103.hi.inet', '0000:44:00.1', 'Te0/16'),
    ('nfv103.hi.inet', '0000:44:00.0', 'Te0/17'),
    ('nfv103.hi.inet', '0000:43:00.1', 'Te0/18'),
    ('nfv103.hi.inet', '0000:43:00.0', 'Te0/19'),
    ('nfv103.hi.inet', '0000:04:00.0', 'Te0/20'),
    ('nfv103.hi.inet', '0000:04:00.1', 'Te0/21'),
    ('nfv103.hi.inet', '0000:06:00.0', 'Te0/22'),
    ('nfv103.hi.inet', '0000:06:00.1', 'Te0/23'),
    ('nfv101.hi.inet', '0000:44:00.1', 'Te0/0'),
    ('nfv101.hi.inet', '0000:44:00.0', 'Te0/1'),
    ('nfv101.hi.inet', '0000:43:00.1', 'Te0/2'),
    ('nfv101.hi.inet', '0000:43:00.0', 'Te0/3'),
    ('nfv101.hi.inet', '0000:04:00.0', 'Te0/4'),
    ('nfv101.hi.inet', '0000:04:00.1', 'Te0/5'),
    ('nfv101.hi.inet', '0000:06:00.0', 'Te0/6'),
    ('nfv101.hi.inet', '0000:06:00.1', 'Te0/7'),
    ('nfv100.hi.inet', '0000:06:00.0', 'Te0/33'),
    ('nfv100.hi.inet', '0000:06:00.1', 'Te0/32'),
    ('nfv100.hi.inet', '0000:08:00.0', 'Te0/35'),
    ('nfv100.hi.inet', '0000:08:00.1', 'Te0/34'),
    ('nfv104.hi.inet', '0000:44:00.0', 'Te0/25'),
    ('nfv104.hi.inet', '0000:44:00.1', 'Te0/24'),
    ('nfv104.hi.inet', '0000:04:00.0', 'Te0/28'),
    ('nfv104.hi.inet', '0000:04:00.1', 'Te0/29'),
    ('nfv104.hi.inet', '0000:43:00.0', 'Te0/27'),
    ('nfv104.hi.inet', '0000:43:00.1', 'Te0/26'),
    ('nfv104.hi.inet', '0000:06:00.0', 'Te0/30'),
    ('nfv104.hi.inet', '0000:06:00.1', 'Te0/31'),
 
    ( '10.95.87.139', '0000:03:00.0', 'eth2/5'),
    ( '10.95.87.139', '0000:03:00.1', 'eth2/6'),
    ( '10.95.87.139', '0000:04:00.1', 'eth2/7'),
    ( '10.95.87.139', '0000:41:00.0', 'eth2/1'),
    ( '10.95.87.139', '0000:41:00.1', 'eth2/2'),
    ( '10.95.87.139', '0000:42:00.0', 'eth2/3'),
    ( '10.95.87.139', '0000:42:00.1', 'eth2/4'),

    ( '10.95.87.138', '0000:04:00.1', 'eth1/5'),
    ( '10.95.87.138', '0000:04:00.0', 'eth1/6'),
    ( '10.95.87.138', '0000:05:00.1', 'eth1/7'),
    ( '10.95.87.138', '0000:43:00.0', 'eth1/3'),
    ( '10.95.87.138', '0000:43:00.1', 'eth1/4'),
    ( '10.95.87.138', '0000:44:00.1', 'eth1/2'),
    ( '10.95.87.138', '0000:44:00.0', 'eth1/1'),

    ( '10.95.87.133', '0000:84:00.1', 'spp0-1'),
    ( '10.95.87.133', '0000:84:00.0', 'spp0-2'),
    ( '10.95.87.133', '0000:82:00.1', 'spp0-3'),
    ( '10.95.87.133', '0000:82:00.0', 'spp0-4'),
    ( '10.95.87.133', '0000:0a:00.1', 'spp0-5'),
    ( '10.95.87.133', '0000:0a:00.0', 'spp0-6'),
    ( '10.95.87.133', '0000:08:00.1', 'spp0-7'),
    ( '10.95.87.133', '0000:08:00.0', 'spp0-8'),
    ( '10.95.87.134', '0000:84:00.1', 'spp0-9'),
    ( '10.95.87.134', '0000:84:00.0', 'spp0-10'),
    ( '10.95.87.134', '0000:82:00.1', 'spp0-11'),
    ( '10.95.87.134', '0000:82:00.0', 'spp0-12'),
    ( '10.95.87.134', '0000:0a:00.1', 'spp0-13'),
    ( '10.95.87.134', '0000:0a:00.0', 'spp0-14'),
    ( '10.95.87.134', '0000:08:00.1', 'spp0-15'),
    ( '10.95.87.134', '0000:08:00.0', 'spp0-16'),
    ( '10.95.87.181', '0000:84:00.1', 'spp0-17'),
    ( '10.95.87.181', '0000:84:00.0', 'spp0-18'),
    ( '10.95.87.181', '0000:82:00.1', 'spp0-19'),
    ( '10.95.87.181', '0000:82:00.0', 'spp0-20'),
    ( '10.95.87.181', '0000:0a:00.1', 'spp0-21'),
    ( '10.95.87.181', '0000:0a:00.0', 'spp0-22'),
    ( '10.95.87.181', '0000:08:00.1', 'spp0-23'),
    ( '10.95.87.181', '0000:08:00.0', 'spp0-24'),
    ( '10.95.87.186', '0000:84:00.1', 'spp0-25'),
    ( '10.95.87.186', '0000:84:00.0', 'spp0-26'),
    ( '10.95.87.186', '0000:82:00.1', 'spp0-27'),
    ( '10.95.87.186', '0000:82:00.0', 'spp0-28'),
    ( '10.95.87.186', '0000:0a:00.1', 'spp0-29'),
    ( '10.95.87.186', '0000:0a:00.0', 'spp0-30'),
    ( '10.95.87.186', '0000:08:00.1', 'spp0-31'),
    ( '10.95.87.186', '0000:08:00.0', 'spp0-32')
;

UNLOCK TABLES;
