<!DOCTYPE html>

<!--
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

    Author: Alfonso Tierno
    Version: 0.51
    Date: Feb 2015
-->

<html>
<head>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8">
<!-- already loaded at scenario.php 
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"></script> 
<script src="js/jquery-ui-1.9.2-min.js"></script>
  <script src="https://rawgit.com/sporritt/jsPlumb/1.5.0/dist/js/jquery.jsPlumb-1.5.0-min.js"></script> 
<script src="js/jstree.min.js"></script>
--> 
<script src="js/contextmenu.js"></script>
<script src="js/js-yaml.js"></script>

<title>Scenario details</title>
</head>

<body>

<?php
	require 'config.php';
	require 'get_scenarios.php';
	parse_str($_SERVER['QUERY_STRING'], $myArray);
	$uuid=$myArray['uuid'];
	$type=$myArray['type'];
	
	getConfig();
	if  ($type=='scenario'){
		echo "<script>\n";
		getScenarioId_js($uuid);
		echo "</script>\n";
		echo "<p><b>uuid:</b>        <a id='scenario_uuid'>Loading</a> </p>\n";
		echo "<p><b>name:</b>        <a id='scenario_name' title='doble click to change' >Loading</a> </p>\n";
		echo "<p><b>description:</b> <a id='scenario_description' title='doble click to change'>Loading</a> </p>\n";
		echo "<p><b>created:</b>     <a id='scenario_created'>Loading</a> </p>\n";
		//echo "<p><b>modified:</b>    <a id='scenario_modified'>Loading</a> </p>\n";
	}else{
		getInstance($uuid);
	}			
?>
<script src="js/scenario_utils.js"></script>
<script>

// for testing
/*{
	var connectorPaintStyle = {lineWidth:4, strokeStyle:'rgba(0,0,0,0.5)', joinstyle:"round", outlineColor:"ivory", outlineWidth:1};
	var connectorHoverStyle = {lineWidth:5, strokeStyle:'SteelBlue', outlineWidth:1, outlineColor:"ivory"};
	vnfsDefs={
        '5512afc4-8df6-11e4-9fd3-0800273e724c':{'type':'VNF','model': 'NEC_DHCP_2P', 'img':'images/big/vnf_default.png','description':'NEC_DHCP_2P','ifaces':{
            'left':[['xe1','data'],['xe0','data'],],'bottom':[['ge0','bridge'],['eth0','bridge'],],
        }},
        '61b969fc-8df6-11e4-9fd3-0800273e724c':{'type':'VNF','model': 'NEC_VCPEIPFE_1_1_4P', 'img':'images/big/vnf_default.png','description':'NEC_VCPEIPFE_1_1_4P','ifaces':{
            'left':[['xe1','data'],['xe0','data'],],'right':[['xe3','data'],['xe2','data'],],'bottom':[['ge0','bridge'],['eth0','bridge'],],
        }},
        '5c5bfd8a-8df6-11e4-9fd3-0800273e724c':{'type':'VNF','model': 'NEC_VCPENAT_1_1_4P', 'img':'images/big/vnf_default.png','description':'NEC_VCPENAT_1_1_4P','ifaces':{
            'left':[['xe1','data'],['xe0','data'],],'right':[['xe3','data'],['xe2','data'],],'bottom':[['ge0','bridge'],['eth0','bridge'],],
        }},
        '3ae18a8a-8df6-11e4-9fd3-0800273e724c':{'type':'VNF','model': 'TIDGEN_2P', 'img':'images/big/vnf_tidgen_2p.png','description':'TIDGEN_2P','ifaces':{
            'left':[['xe1','data'],['xe0','data'],],'bottom':[['eth0','bridge'],],
        }},
        'aaaaaaaa-3333-aaaa-aaaa-aaaaaaaaaaaa':{'type':'external_network','model': 'MAN', 'img':'images/big/man.png','description':'MAN_NET','ifaces':{
            'left':[['0','data']],
        }},
    };
//} */



$(document).ready(function(){

	$(this)[0].addEventListener("contextmenu", 
		function(event) {event.preventDefault();}, false
	);

<?php
	if  ($type!='scenario'){
		echo "    \$(document).ready(function(){\n";
		echo "        \$('#instance_details').jstree()\n";
		echo "        \$('#instance_items').jstree({'checkbox' : {'keep_selected_style' : false}, 'plugins' : [ 'checkbox' ]  })\n";
		echo "    });\n";
		echo "    return;\n";
	}
?>
    //create scenario, with edit=false
	load_scenario(scenario, false);   
    $('#scenario_uuid').text(        scenario["uuid"] );
    $('#scenario_name').text(        scenario["name"] );
    $('#scenario_description').text( scenario["description"] );
    $('#scenario_created').text(     scenario["created_at"] );
    //$('#scenario_modified').text(    scenario["modified_at"] );
	$("#scenario_name").dblclick(function(){
		var new_name=prompt("Please enter a new name", $(this).text());
		if (new_name!=null && new_name!=""){
			$(this).text(new_name);
		}
	});
	$("#scenario_description").dblclick(function(){
		var new_name=prompt("Please enter a new description", $(this).text() );
		if (new_name!=null && new_name!=""){
			$(this).text(new_name);
		}
	});
	setTimeout(function(){jsPlumb.repaintEverything();}, 1000);
	
        	
});


</script>
	

</body>
</html>
