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

/* This table contains a list of processor ranking
   The larger ranking the better performance
   All physical host models must be included in this table 
   before being adding to openvim
   processor information is obtained with commnand cat /proc/cpuinfo
   NOTE: Current version of openvim ignores the ranking
*/


LOCK TABLES `host_ranking` WRITE;
/*!40000 ALTER TABLE `host_ranking` DISABLE KEYS */;
INSERT INTO `host_ranking` 
    (family, manufacturer, version, description, ranking)
VALUES 
    ('Xeon','Intel','Intel(R) Xeon(R) CPU E5-2680 0 @ 2.70GHz','sandy bridge',170),
    ('Xeon','Intel','Intel(R) Xeon(R) CPU E5-4620 0 @ 2.20GHz','sandy bridge',200),
    ('Xeon','Intel','Intel(R) Xeon(R) CPU E5-2697 v2 @ 2.70GHz','ivy bridge',300),
    ('Xeon','Intel','Intel(R) Xeon(R) CPU E5-2680 v2 @ 2.80GHz','ivy bridge',310); /*last entry ends with   ';'  */

UNLOCK TABLES;
