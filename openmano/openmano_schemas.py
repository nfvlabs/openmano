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
nameshort_schema={"type" : "string", "minLength":1, "maxLength":24, "pattern" : "^[^,;()'\"]+$"}
name_schema={"type" : "string", "minLength":1, "maxLength":36, "pattern" : "^[^,;()'\"]+$"}
xml_text_schema={"type" : "string", "minLength":1, "maxLength":1000, "pattern" : "^[^']+$"}
description_schema={"type" : ["string","null"], "maxLength":200, "pattern" : "^[^'\"]+$"}
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
metadata_schema={
    "type":"object",
    "properties":{
        "architecture": {"type":"string"},
        "use_incremental": {"type":"string","enum":["yes","no"]},
        "vpci": pci_schema,
        "os_distro": {"type":"string"},
        "os_type": {"type":"string"},
        "os_version": {"type":"string"},
        "bus": {"type":"string"}
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
        "http_host": name_schema,
        "vnf_repository": path_schema,
        "db_host": name_schema,
        "db_user": name_schema,
        "db_passwd": {"type":"string"},
        "db_name": name_schema,
        # Next fields will disappear once the MANO API includes appropriate primitives
        "vim_url": http_schema,
        "vim_url_admin": http_schema,
        "vim_name": nameshort_schema,
        "vim_tenant_name": nameshort_schema,
        "mano_tenant_name": nameshort_schema,
        "mano_tenant_id": id_schema
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
                "name": name_schema,
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
                "type": {"type":"string","enum":["openvim","openstack"]},
                "vim_url": description_schema,
                "vim_url_admin": description_schema,
                "config": {
                    "type":"object",
                    "properties":{
                        "network_vlan_ranges": {"type": "string"}
                    },
                    "additionalProperties": False
                }
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
        }
    
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
                "vim_tenant_name": name_schema,
                "vim_username": name_schema,
                "vim_password": name_schema,
            },
#            "required": ["vim_tenant"],
            "additionalProperties": True
        }
    },
    "required": ["datacenter"],
    "additionalProperties": False
}
                             
host_schema = {
    "type":"object",
    "properties":{
        "id":id_schema,
        "name": name_schema,
    },
    "required": ["id"]
}
image_schema = {
    "type":"object",
    "properties":{
        "id":id_schema,
        "name": name_schema,
    },
    "required": ["id","name"]
}
server_schema = {
    "type":"object",
    "properties":{
        "id":id_schema,
        "name": name_schema,
    },
    "required": ["id","name"]
}
new_host_response_schema = {
    "title":"host response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "host": host_schema
    },
    "required": ["host"],
    "additionalProperties": False
}

get_images_response_schema = {
    "title":"openvim images response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "images":{
            "type":"array",
            "items": image_schema,
        }
    },
    "required": ["images"],
    "additionalProperties": False
}

get_hosts_response_schema = {
    "title":"openvim hosts response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "hosts":{
            "type":"array",
            "items": host_schema,
        }
    },
    "required": ["hosts"],
    "additionalProperties": False
}

get_host_detail_response_schema = new_host_response_schema # TODO: Content is not parsed yet

get_server_response_schema = {
    "title":"openvim server response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "servers":{
            "type":"array",
            "items": server_schema,
        }
    },
    "required": ["servers"],
    "additionalProperties": False
}

new_tenant_response_schema = {
    "title":"tenant response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "tenant":{
            "type":"object",
            "properties":{
                "id":id_schema,
                "name": nameshort_schema,
                "description":description_schema,
                "enabled":{"type" : "boolean"}
            },
            "required": ["id"]
        }
    },
    "required": ["tenant"],
    "additionalProperties": False
}

new_network_response_schema = {
    "title":"network response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "network":{
            "type":"object",
            "properties":{
                "id":id_schema,
                "name":name_schema,
                "type":{"type":"string", "enum":["bridge_man","bridge_data","data", "ptp"]},
                "shared":{"type":"boolean"},
                "tenant_id":id_schema,
                "admin_state_up":{"type":"boolean"},
                "vlan":vlan1000_schema
            },
            "required": ["id"]
        }
    },
    "required": ["network"],
    "additionalProperties": False
}

# get_network_response_schema = {
#     "title":"get network response information schema",
#     "$schema": "http://json-schema.org/draft-04/schema#",
#     "type":"object",
#     "properties":{
#         "network":{
#             "type":"object",
#             "properties":{
#                 "id":id_schema,
#                 "name":name_schema,
#                 "type":{"type":"string", "enum":["bridge_man","bridge_data","data", "ptp"]},
#                 "shared":{"type":"boolean"},
#                 "tenant_id":id_schema,
#                 "admin_state_up":{"type":"boolean"},
#                 "vlan":vlan1000_schema
#             },
#             "required": ["id"]
#         }
#     },
#     "required": ["network"],
#     "additionalProperties": False
# }


new_port_response_schema = {
    "title":"port response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "port":{
            "type":"object",
            "properties":{
                "id":id_schema,
            },
            "required": ["id"]
        }
    },
    "required": ["port"],
    "additionalProperties": False
}

new_flavor_response_schema = {
    "title":"flavor response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "flavor":{
            "type":"object",
            "properties":{
                "id":id_schema,
            },
            "required": ["id"]
        }
    },
    "required": ["flavor"],
    "additionalProperties": False
}

new_image_response_schema = {
    "title":"image response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "image":{
            "type":"object",
            "properties":{
                "id":id_schema,
            },
            "required": ["id"]
        }
    },
    "required": ["image"],
    "additionalProperties": False
}

new_vminstance_response_schema = {
    "title":"server response information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "server":{
            "type":"object",
            "properties":{
                "id":id_schema,
            },
            "required": ["id"]
        }
    },
    "required": ["server"],
    "additionalProperties": False
}

internal_connection_element_schema = {
    "type":"object",
    "properties":{
        "VNFC": name_schema,
        "local_iface_name": nameshort_schema
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
        "local_iface_name": nameshort_schema ,
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
            "name":nameshort_schema,
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
            "name": nameshort_schema,
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
                "features":{"type":"array","items":name_schema}
            },
            "required": ["model"],
            "additionalProperties": False
        },
        "hypervisor": {
            "type":"object",
            "properties":{
                "type":name_schema,
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
                "class": name_schema,
                "public": {"type" : "boolean"},
                "physical": {"type" : "boolean"},
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

vnfd_schema = {
    "title":"vnfd information schema v0.2",
    "$schema": "http://json-schema.org/draft-04/schema#",
    #"oneOf": [vnfd_schema_v01, vnfd_schema_v02]
    "oneOf": [vnfd_schema_v01]
}

get_processor_rankings_response_schema = {
    "title":"processor rankings information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type":"object",
    "properties":{
        "rankings":{
            "type":"array",
            "items":{
                "type":"object",
                "properties":{
                    "model": description_schema,
                    "value": integer0_schema
                },
                "additionalProperties": False,
                "required": ["model","value"]
            }
        },
        "additionalProperties": False,
        "required": ["rankings"]
    }
}


nsd_schema_v01 = {
    "title":"network scenario descriptor information schema v0.1",
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
                        ".": {
                            "type": "object",
                            "properties":{
                                "type":{"type":"string", "enum":["VNF", "other_network", "network", "external_network"]}
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
                                "nodes":{"oneOf":[{"type":"object", "minProperties":2}, {"type":"array", "minLength":2}]}
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
        "version": {"type": "string", "pattern":"^v0.2$"},
        "topology":{
            "type":"object",
            "properties":{
                "name": name_schema,
            },
            "required": ["name"],
            "additionalProperties": True
        }
    },
    "required": ["topology", "version"],
    "additionalProperties": False
}

scenario_new_schema = {
    "title":"new scenario information schema",
    "$schema": "http://json-schema.org/draft-04/schema#",
    #"oneOf": [nsd_schema_v01, nsd_schema_v02]
    "oneOf": [nsd_schema_v01]
}

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
        "vnfs":{"type": "array", "items":{"type":"string"}},
        "vms":{"type": "array", "items":{"type":"string"}}
    },
    "minProperties": 1,
    #"maxProperties": 1,
    "additionalProperties": False
}
