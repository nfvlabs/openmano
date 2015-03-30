# -*- coding: utf-8 -*-

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

'''
Definitions of classes for the Host operating server, ...  
'''

__author__="Pablo Montes"


class Units():
    memory_1000 = 1
    memory_1024 = 2
    memory_full = 3
    bw = 4
    freq = 5
    no_units = 6
    name = 7
    boolean = 8
    
class definitionsClass():
    user = 'n2'
    password = 'n2'
    extrict_hugepages_allocation = True
    processor_possible_features = ['64b','iommu','lps','tlbps','hwsv','dioc','ht']
    processor_possible_manufacturers = ['Intel','AMD']
    processor_possible_families = ['Xeon']
    processor_possible_versions = ['Intel(R) Xeon(R) CPU E5-4620 0 @ 2.20GHz', 'Intel(R) Xeon(R) CPU E5-2680 0 @ 2.70GHz','Intel(R) Xeon(R) CPU E5-2697 v2 @ 2.70GHz']
    memory_possible_types = ['DDR2','DDR3']
    memory_possible_form_factors = ['DIMM']
    hypervisor_possible_types = ['QEMU']
    hypervisor_possible_domain_types = ['kvm'] #['qemu', 'kvm']
    os_possible_id = ['Red Hat Enterprise Linux Server release 6.4 (Santiago)',
                      'Red Hat Enterprise Linux Server release 6.5 (Santiago)',
                      'Red Hat Enterprise Linux Server release 6.6 (Santiago)',
                      'CentOS release 6.5 (Final)',
                      'CentOS release 6.6 (Final)',
                      'Red Hat Enterprise Linux Server release 7.0 (Maipo)',
                      'Red Hat Enterprise Linux Server release 7.1 (Maipo)',
                    ]
    os_possible_types = ['GNU/Linux']
    os_possible_architectures = ['x86_64']
    hypervisor_possible_composed_versions = ['QEMU-kvm']
    units = dict() 
    units[Units.bw] = ['Gbps', 'Mbps', 'kbps', 'bps']
    units[Units.freq] = ['GHz', 'MHz', 'KHz', 'Hz']
    units[Units.memory_1000] = ['GB', 'MB', 'KB', 'B']
    units[Units.memory_1024] = ['GiB', 'MiB', 'KiB', 'B']
    units[Units.memory_full] = ['GB', 'MB', 'KB', 'GiB', 'MiB', 'KiB', 'B']
    valid_hugepage_sz = [1073741824, 2097152] #In bytes
    valid_VNFC_iface_types = ['mgmt','data']
    
    def __init__(self):
        return
        
