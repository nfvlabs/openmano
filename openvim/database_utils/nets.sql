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
    This table contains a list of networks created from the begining
    The following fields are needed
        uuid: provide a valid uuid format
        type: ptp, data (point to point, or point to multipoint) are openflow dadaplane nets
              bridge_man, bridge_data are virtio/bridge controlplane nets
        name: useful human readable name
        shared: by default true
        vlan:  default vlan of the dataplane net
        bind: for control plane:
                  default: default network
                  macvtap:host_iface. Connect to a direct macvtap host interface
                  bridge:bridge_name. Connect to this host bridge_name interface
              for dataplane: NULL, because the binding is done with a external port
*/


LOCK TABLES `nets` WRITE;
/*
INSERT INTO `nets`
  (uuid,                                  `type`,       name,        shared, vlan, bind)
VALUES
  ('00000000-0000-0000-0000-000000000000','bridge_man', 'default',   'true', NULL, 'default'),
  ('11111111-1111-1111-1111-111111111111','bridge_man', 'direct:em1','true', NULL, 'macvtap:em1'),
  ('aaaaaaaa-1111-aaaa-aaaa-aaaaaaaaaaaa','data',       'coreIPv4',  'true', 702,  NULL),
  ('aaaaaaaa-aaaa-0000-1111-aaaaaaaaaaaa','bridge_data','virbrMan2', 'true', 2002, 'bridge:virbrMan2')  # last row without ','
;
*/

UNLOCK TABLES;

/*  External PORTS are necessary to connect a dataplane network to an external switch port
    The following fields are needed
        uuid: provide a valid uuid format
        name: useful human readable name
        net_id: uuid of the net where this port must be connected
        Mbps: only informative, indicates the expected bandwidth in megabits/s
        type: only external has meaning here
        vlan: if the traffic at that port must be vlan tagged
        switch_port: port name at switch:
*/

LOCK TABLES `ports` WRITE;
/*
INSERT INTO `ports` 
  (uuid,                                  name,        net_id,                                Mbps, type,      vlan, switch_port)
VALUES
  ('6d536a80-52e9-11e4-9e31-5254006d6777','CoreIPv4',  'aaaaaaaa-1111-aaaa-aaaa-aaaaaaaaaaaa',10000,'external',702,  'Te0/47') # last row without ','
;
*/

UNLOCK TABLES;

