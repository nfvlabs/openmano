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
This is the generic abstract class that defines the common methods to interact
with any Openflow Controller through the openflow program.
'''

import abc

class ofconnector(object):
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def print_of_switches(self, verbose):
    """Print list of switches and their dpid"""
    return

  @abc.abstractmethod
  def print_of_list(self, verbose):
    """Print list of openflow rules"""
    return
    
  @abc.abstractmethod
  def print_of_dump(self):
    """Dump openflow rules"""
    return

  @abc.abstractmethod
  def of_clear(self):
    """Clear openflow rules"""
    return

  @abc.abstractmethod
  def of_install(self, dumpfile):
    """Install openflow rules from file"""
    return

  @abc.abstractmethod
  def of_add(self, name, inport, outport, verbose, priority, matchmac, matchvlan, stripvlan, setvlan):
    """Add a new openflow rule"""
    return

  @abc.abstractmethod
  def of_delete(self, name, verbose):
    """Delete an openflow rule from its name"""
    return


