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
JSON schemas used by openmano httpserver.py module to parse the different files and messages sent through the API 
'''
__author__="Alfonso Tierno, Gerardo Garcia"
__date__ ="$09-oct-2014 09:09:48$"

#Basis schemas
passwd_schema={"type" : "string", "minLength":1, "maxLength":60}
nameshort_schema={"type" : "string", "minLength":1, "maxLength":60, "pattern" : "^[^,;()'\"]+$"}
name_schema={"type" : "string", "minLength":1, "maxLength":255, "pattern" : "^[^,;()'\"]+$"}
xml_text_schema={"type" : "string", "minLength":1, "maxLength":1000, "pattern" : "^[^']+$"}
description_schema={"type" : ["string","null"], "maxLength":255, "pattern" : "^[^'\"]+$"}
id_schema_fake = {"type" : "string", "minLength":2, "maxLength":36 }  #"pattern": "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$"
id_schema = {"type" : "string", "pattern": "^[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$"}
pci_schema={"type":"string", "pattern":"^[0-9a-fA-F]{4}(:[0-9a-fA-F]{2}){2}\.[0-9a-fA-F]$"}
http_schema={"type":"string", "pattern":"^https?://[^'\"=]+$"}
bandwidth_schema={"type":"string", "pattern" : "^[0-9]+ *([MG]bps)?$"}
memory_schema={"type":"string", "pattern" : "^[0-9]+ *([MG]i?[Bb])?$"}
integer0_schema={"type":"integer","minimum":0}
integer1_schema={"type":"integer","minimum":1}
path_schema={"type":"string", "pattern":"^(\.(\.?))?(/[^/"":{}\ \(\)]+)+$"}
vlan_schema={"type":"integer","minimum":1,"maximum":4095}
vlan1000_schema={"type":"integer","minimum":1000,"maximum":4095}
mac_schema={"type":"string", "pattern":"^[0-9a-fA-F][02468aceACE](:[0-9a-fA-F]{2}){5}$"}  #must be unicast LSB bit of MSB byte ==0 
#mac_schema={"type":"string", "pattern":"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$"}
ip_schema={"type":"string","pattern":"^([0-9]{1,3}.){3}[0-9]{1,3}$"}
port_schema={"type":"integer","minimum":1,"maximum":65534}
object_schema={"type":"object"}

metadata_schema={
    "type":"object",
    "properties":{
        "architecture": {"type":"string"},
        "use_incremental": {"type":"string","enum":["yes","no"]},
        "vpci": pci_schema,
        "os_distro": {"type":"string"},
        "os_type": {"type":"string"},
        "os_version": {"type":"string"},
        "bus": {"type":"string"},
        "topology": {"type":"string", "enum": ["oneSocket"]}
    }
}

#Schema for the configuration file
config_schema = {
    "title":"configuration response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "http_port": port_schema,
        "http_admin_port": port_schema,
        "http_host": nameshort_schema,
        "vnf_repository": path_schema,
        "db_host": nameshort_schema,
        "db_user": nameshort_schema,
        "db_passwd": {"type":"string"},
        "db_name": nameshort_schema,
        # Next fields will disappear once the MANO API includes appropriate primitives
        "vim_url": http_schema,
        "vim_url_admin": http_schema,
        "vim_name": nameshort_schema,
        "vim_tenant_name": nameshort_schema,
        "mano_tenant_name": nameshort_schema,
        "mano_tenant_id": id_schema, 
        "http_console_ports": {
            "type": "array", 
            "items": {"OneOf" : [
                port_schema, 
                {"type":"object", "properties":{"from": port_schema, "to": port_schema}, "required": ["from","to"]} 
            ]}
        },
    },
    "required": ['db_host', 'db_user', 'db_passwd', 'db_name'],
    "additionalProperties": False
}

tenant_schema = {
    "title":"tenant information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "tenant":{
            "type":"object",
            "properties":{
                "name": nameshort_schema,
                "description": description_schema,
            },
            "required": ["name"],
            "additionalProperties": True
        }
    },
    "required": ["tenant"],
    "additionalProperties": False
}
tenant_edit_schema = {
    "title":"tenant edit information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "tenant":{
            "type":"object",
            "properties":{
                "name": name_schema,
                "description": description_schema,
            },
            "additionalProperties": False
        }
    },
    "required": ["tenant"],
    "additionalProperties": False
}

datacenter_schema_properties={
                "name": name_schema,
                "description": description_schema,
                "type": nameshort_schema, #currently "openvim" or "openstack", can be enlarge with plugins
                "vim_url": description_schema,
                "vim_url_admin": description_schema,
                "config": { "type":"object" }
            }

datacenter_schema = {
    "title":"datacenter information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "datacenter":{
            "type":"object",
            "properties":datacenter_schema_properties,
            "required": ["name", "vim_url"],
            "additionalProperties": True
        }
    },
    "required": ["datacenter"],
    "additionalProperties": False
}


datacenter_edit_schema = {
    "title":"datacenter edit nformation schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "datacenter":{
            "type":"object",
            "properties":datacenter_schema_properties,
            "additionalProperties": False
        }
    },
    "required": ["datacenter"],
    "additionalProperties": False
}


netmap_new_schema = {
    "title":"netmap new information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "netmap":{   #delete from datacenter
            "type":"object",
            "properties":{
                "name": name_schema,  #name or uuid of net to change
                "vim_id": id_schema,
                "vim_name": name_schema
            },
            "minProperties": 1,
            "additionalProperties": False
        },
    },
    "required": ["netmap"],
    "additionalProperties": False
}

netmap_edit_schema = {
    "title":"netmap edit information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "netmap":{   #delete from datacenter
            "type":"object",
            "properties":{
                "name": name_schema,  #name or uuid of net to change
            },
            "minProperties": 1,
            "additionalProperties": False
        },
    },
    "required": ["netmap"],
    "additionalProperties": False
}

datacenter_action_schema = {
    "title":"datacenter action information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "net-update":{"type":"null",},
        "net-edit":{
            "type":"object",
            "properties":{
                "net": name_schema,  #name or uuid of net to change
                "name": name_schema,
                "description": description_schema,
                "shared": {"type": "boolean"}
            },
            "minProperties": 1,
            "additionalProperties": False
        },
        "net-delete":{
            "type":"object",
            "properties":{
                "net": name_schema,  #name or uuid of net to change
            },
            "required": ["net"],
            "additionalProperties": False
        },
    },
    "minProperties": 1,
    "maxProperties": 1,
    "additionalProperties": False
}


datacenter_associate_schema={
    "title":"datacenter associate information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "datacenter":{
            "type":"object",
            "properties":{
                "vim_tenant": id_schema,
                "vim_tenant_name": nameshort_schema,
                "vim_username": nameshort_schema,
                "vim_password": nameshort_schema,
            },
#            "required": ["vim_tenant"],
            "additionalProperties": True
        }
    },
    "required": ["datacenter"],
    "additionalProperties": False
}

internal_connection_element_schema = {
    "type":"object",
    "properties":{
        "VNFC": name_schema,
        "local_iface_name": name_schema
    }
}

internal_connection_schema = {
    "type":"object",
    "properties":{
        "name": name_schema,
        "description":description_schema,
        "type":{"type":"string", "enum":["bridge","data","ptp"]},
        "elements": {"type" : "array", "items": internal_connection_element_schema, "minItems":2}
    },
    "required": ["name", "type", "elements"],
    "additionalProperties": False
}

external_connection_schema = {
    "type":"object",
    "properties":{
        "name": name_schema,
        "type":{"type":"string", "enum":["mgmt","bridge","data"]},
        "VNFC": name_schema,
        "local_iface_name": name_schema ,
        "description":description_schema
    },
    "required": ["name", "type", "VNFC", "local_iface_name"],
    "additionalProperties": False
}

interfaces_schema={
    "type":"array",
    "items":{
        "type":"object",
        "properties":{
            "name":name_schema,
            "dedicated":{"type":"string","enum":["yes","no","yes:sriov"]},
            "bandwidth":bandwidth_schema,
            "vpci":pci_schema,
            "mac_address": mac_schema
        },
        "additionalProperties": False,
        "required": ["name","dedicated", "bandwidth"]
    }
}

bridge_interfaces_schema={
    "type":"array",
    "items":{
        "type":"object",
        "properties":{
            "name": name_schema,
            "bandwidth":bandwidth_schema,
            "vpci":pci_schema,
            "mac_address": mac_schema,
            "model": {"type":"string", "enum":["virtio","e1000","ne2k_pci","pcnet","rtl8139"]}
        },
        "additionalProperties": False,
        "required": ["name"]
    }
}

devices_schema={
    "type":"array",
    "items":{
        "type":"object",
        "properties":{
            "type":{"type":"string", "enum":["disk","cdrom","xml"] },
            "image": path_schema,
            "image metadata": metadata_schema, 
            "vpci":pci_schema,
            "xml":xml_text_schema,
        },
        "additionalProperties": False,
        "required": ["type"]
    }
}


numa_schema = {
    "type": "object",
    "properties": {
        "memory":integer1_schema,
        "cores":integer1_schema,
        "paired-threads":integer1_schema,
        "threads":integer1_schema,
        "cores-id":{"type":"array","items":integer0_schema},
        "paired-threads-id":{"type":"array","items":{"type":"array","minItems":2,"maxItems":2,"items":integer0_schema}},
        "threads-id":{"type":"array","items":integer0_schema},
        "interfaces":interfaces_schema
    },
    "additionalProperties": False,
    #"required": ["memory"]
}

vnfc_schema = {
    "type":"object",
    "properties":{
        "name": name_schema,
        "description": description_schema,
        "VNFC image": {"oneOf": [path_schema, http_schema]},
        "image metadata": metadata_schema, 
        "processor": {
            "type":"object",
            "properties":{
                "model":description_schema,
                "features":{"type":"array","items":nameshort_schema}
            },
            "required": ["model"],
            "additionalProperties": False
        },
        "hypervisor": {
            "type":"object",
            "properties":{
                "type":nameshort_schema,
                "version":description_schema
            },
        },
        "ram":integer0_schema,
        "vcpus":integer0_schema,
        "disk": integer1_schema,
        "numas": {
            "type": "array",
            "items":numa_schema
        },
        "bridge-ifaces": bridge_interfaces_schema,
        "devices": devices_schema
    },
    "required": ["name", "VNFC image"],
    "additionalProperties": False
}

vnfd_schema_v01 = {
    "title":"vnfd information schema v0.1",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "vnf":{
            "type":"object",
            "properties":{
                "name": name_schema,
                "description": description_schema,
                "class": nameshort_schema,
                "public": {"type" : "boolean"},
                "physical": {"type" : "boolean"},
                "tenant_id": id_schema, #only valid for admin
                "external-connections": {"type" : "array", "items": external_connection_schema, "minItems":1},
                "internal-connections": {"type" : "array", "items": internal_connection_schema, "minItems":1},
                "VNFC":{"type" : "array", "items": vnfc_schema, "minItems":1}
            },
            "required": ["name","external-connections"],
            "additionalProperties": True
        }
    },
    "required": ["vnf"],
    "additionalProperties": False
}

#Future VNFD schema to be defined
vnfd_schema_v02 = {
    "title":"vnfd information schema v0.2",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "version": {"type": "string", "pattern":"^v0.2$"},
        "vnf":{
            "type":"object",
            "properties":{
                "name": name_schema,
            },
            "required": ["name"],
            "additionalProperties": True
        }
    },
    "required": ["vnf", "version"],
    "additionalProperties": False
}

#vnfd_schema = vnfd_schema_v01
#{
#    "title":"vnfd information schema v0.2",
#    "$schema": "http://json-schema.org/draft-04/schema#",
#    "oneOf": [vnfd_schema_v01, vnfd_schema_v02]
#}

graph_schema = {
    "title":"graphical scenario descriptor information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "x":      integer0_schema,
        "y":      integer0_schema,
        "ifaces": {
            "type":"object",
            "properties":{
                "left": {"type":"array"},
                "right": {"type":"array"},
                "bottom": {"type":"array"},
            }
        }
    },
    "required": ["x","y"]
}

nsd_schema_v01 = {
    "title":"network scenario descriptor information schema v0.1",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "name":name_schema,
        "description": description_schema,
        "tenant_id": id_schema, #only valid for admin
        "topology":{
            "type":"object",
            "properties":{
                "nodes": {
                    "type":"object",
                    "patternProperties":{
                        ".": {
                            "type": "object",
                            "properties":{
                                "type":{"type":"string", "enum":["VNF", "other_network", "network", "external_network"]},
                                "vnf_id": id_schema,
                                "graph": graph_schema,
                            },
                            "patternProperties":{
                                "^(VNF )?model$": {"type": "string"}
                            },
                            "required": ["type"]
                        }
                    }
                },
                "connections": {
                    "type":"object",
                    "patternProperties":{
                        ".": {
                            "type": "object",
                            "properties":{
                                "nodes":{"oneOf":[{"type":"object", "minProperties":2}, {"type":"array", "minLength":1}]},
                                "type": {"type": "string", "enum":["link", "external_network", "dataplane_net", "bridge_net"]},
                                "graph": graph_schema
                            },
                            "required": ["nodes"]
                        },
                    }
                }
            },
            "required": ["nodes"],
            "additionalProperties": False
        }
    },
    "required": ["name","topology"],
    "additionalProperties": False
}

#Future NSD schema to be defined
nsd_schema_v02 = {
    "title":"network scenario descriptor information schema v0.2",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "schema_version": {"type": "string", "enum": ["0.2"]},
        "name":name_schema,
        "description": description_schema,
        "tenant_id": id_schema, #only valid for admin
        "vnfs": {
            "type":"object",
            "patternProperties":{
                ".": {
                    "type": "object",
                    "properties":{
                        "vnf_id": id_schema,
                        "graph": graph_schema,
                        "vnf_model": name_schema,
                    },
                }
            },
            "minProperties": 1
        },
        "networks": {
            "type":"object",
            "patternProperties":{
                ".": {
                    "type": "object",
                    "properties":{
                        "interfaces":{"type":"array", "minLength":1},
                        "type": {"type": "string", "enum":["link", "external_network", "dataplane_net", "bridge_net"]},
                        "graph": graph_schema
                    },
                    "required": ["interfaces"]
                },
            }
        },
    },
    "required": ["vnfs", "networks","name", "schema_version"],
    "additionalProperties": False
}

#scenario_new_schema = {
#    "title":"new scenario information schema",
#    "$schema": "http://json-schema.org/draft-04/schema#",
#    #"oneOf": [nsd_schema_v01, nsd_schema_v02]
#    "oneOf": [nsd_schema_v01]
#}

scenario_edit_schema = {
    "title":"edit scenario information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "name":name_schema,
        "description": description_schema,
        "topology":{
            "type":"object",
            "properties":{
                "nodes": {
                    "type":"object",
                    "patternProperties":{
                        "^[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$": {
                            "type":"object",
                            "properties":{
                                "graph":{
                                    "type": "object",
                                    "properties":{
                                        "x": integer0_schema,
                                        "y": integer0_schema,
                                        "ifaces":{ "type": "object"}
                                    }
                                },
                                "description": description_schema,
                                "name": name_schema
                            }
                        }
                    }
                }
            },
            "required": ["nodes"],
            "additionalProperties": False
        }
    },
    "additionalProperties": False
}

scenario_action_schema = {
    "title":"scenario action information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "start":{
            "type": "object",
            "properties": {
                "instance_name":name_schema,
                "description":description_schema,
                "datacenter": {"type": "string"}
            },
            "required": ["instance_name"]
        },
        "deploy":{
            "type": "object",
            "properties": {
                "instance_name":name_schema,
                "description":description_schema,
                "datacenter": {"type": "string"}
            },
            "required": ["instance_name"]
        },
        "reserve":{
            "type": "object",
            "properties": {
                "instance_name":name_schema,
                "description":description_schema,
                "datacenter": {"type": "string"}
            },
            "required": ["instance_name"]
        },
        "verify":{
            "type": "object",
            "properties": {
                "instance_name":name_schema,
                "description":description_schema,
                "datacenter": {"type": "string"}
            },
            "required": ["instance_name"]
        }
    },
    "minProperties": 1,
    "maxProperties": 1,
    "additionalProperties": False
}

instance_scenario_create_schema = {
    "title":"instance scenario create information schema v0.1",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "schema_version": {"type": "string", "enum": ["0.1"]},
        "instance":{
            "type":"object",
            "properties":{
                "name":name_schema,
                "description":description_schema,
                "datacenter": name_schema,
                "scenario" : name_schema, #can be an UUID or name
                "action":{"enum": ["deploy","reserve","verify" ]},
                "connect_mgmt_interfaces": {"oneOff": [{"type":"boolean"}, {"type":"object"}]},# can be true or a dict with datacenter: net_name
                "vnfs":{             #mapping from scenario to datacenter
                    "type": "object",
                    "patternProperties":{
                        ".": {
                            "type": "object",
                            "properties":{
                                "name":   name_schema,#override vnf name
                                "datacenter": name_schema,
                                "metadata": {"type": "object"},
                                "user_data": {"type": "string"}
                            }
                        }
                    },
                },
                "networks":{             #mapping from scenario to datacenter
                    "type": "object",
                    "patternProperties":{
                        ".": {
                            "type": "object",
                            "properties":{
                                "netmap-create": {"oneOf":[name_schema,{"type": "null"}]}, #datacenter network to use. Null if must be created as an internal net
                                "netmap-use": name_schema,
                                "name":   name_schema,#override network name
                                "datacenter": name_schema,
                            }
                        }
                    },
                },
            },
            "additionalProperties": False,
            "required": ["scenario", "name"]
        },
    },
    "required": ["instance"],
    "additionalProperties": False
    
}

instance_scenario_action_schema = {
    "title":"instance scenario action information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "start":{"type": "null"},
        "pause":{"type": "null"},
        "resume":{"type": "null"},
        "shutoff":{"type": "null"},
        "shutdown":{"type": "null"},
        "forceOff":{"type": "null"},
        "rebuild":{"type": "null"},
        "reboot":{
            "type": ["object","null"],
        },
        "console": {"type": ["string", "null"], "enum": ["novnc", "xvpvnc", "rdp-html5", "spice-html5", None]},
        "vnfs":{"type": "array", "items":{"type":"string"}},
        "vms":{"type": "array", "items":{"type":"string"}}
    },
    "minProperties": 1,
    #"maxProperties": 1,
    "additionalProperties": False
}
