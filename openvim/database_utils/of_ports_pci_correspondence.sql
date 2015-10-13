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

/*
   READ THIS please:
   This table contains the matching between dataplane host ports 
   and openflow switch ports. 
   The two first column identifies the host and the pci bus
       command ethtool -i provides the pci bus port (at host)
       command ethtool -p makes this port blinking (at host)
   Last column identifies the switch port name
       openvim prints at starting the openflow ports naming 
   NOTE: if a host has already been inserted, you must execute 
   UpdateSwitchPort database procedure to associate ports with 
   the switch connection
*/

LOCK TABLES `of_ports_pci_correspondence` WRITE;

/* DATA for fakehost examples*/
INSERT INTO `of_ports_pci_correspondence` 
    (ip_name, pci, switch_port)
VALUES
    ('fake-host-0', '0000:06:00.0', 'port0/0'),
    ('fake-host-0', '0000:06:00.1', 'port0/1'),
    ('fake-host-0', '0000:08:00.0', 'port0/2'),
    ('fake-host-0', '0000:08:00.1', 'port0/3'),

    ('fake-host-1', '0000:44:00.0', 'port0/4'),
    ('fake-host-1', '0000:44:00.1', 'port0/5'),
    ('fake-host-1', '0000:43:00.0', 'port0/6'),
    ('fake-host-1', '0000:43:00.1', 'port0/7'),
    ('fake-host-1', '0000:04:00.0', 'port0/8'),
    ('fake-host-1', '0000:04:00.1', 'port0/9'),
    ('fake-host-1', '0000:06:00.0', 'port0/10'),
    ('fake-host-1', '0000:06:00.1', 'port0/11'),

    ('fake-host-2', '0000:44:00.0', 'port0/12'),
    ('fake-host-2', '0000:44:00.1', 'port0/13'),
    ('fake-host-2', '0000:43:00.0', 'port0/14'),
    ('fake-host-2', '0000:43:00.1', 'port0/15'),
    ('fake-host-2', '0000:04:00.0', 'port0/16'),
    ('fake-host-2', '0000:04:00.1', 'port0/17'),
    ('fake-host-2', '0000:06:00.0', 'port0/18'),
    ('fake-host-2', '0000:06:00.1', 'port0/19'),

    ('fake-host-3', '0000:44:00.0', 'port1/0'),
    ('fake-host-3', '0000:44:00.1', 'port1/1'),
    ('fake-host-3', '0000:43:00.0', 'port1/2'),
    ('fake-host-3', '0000:43:00.1', 'port1/3'),
    ('fake-host-3', '0000:04:00.0', 'port1/4'),
    ('fake-host-3', '0000:04:00.1', 'port1/5'),
    ('fake-host-3', '0000:06:00.0', 'port1/6'),
    ('fake-host-3', '0000:06:00.1', 'port1/7')
;


UNLOCK TABLES;
