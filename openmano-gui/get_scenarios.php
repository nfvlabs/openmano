<?php 
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

    # Author: Alfonso Tierno
    # Version: 0.51
    # Date: Feb 2015

//require 'config.php' variables;

/** 
 * Obtain openmano scenarios reading direcly from the openmano database
 * the result is a html tree, scenarios as the first level, instances the scond level
 */
function getScenarios()
{
	//getConfig();
	
	$conn = new mysqli($GLOBALS['db_server'], $GLOBALS['db_user'], $GLOBALS['db_passwd'], $GLOBALS['db_name']);

	// Check connection
	if ($conn->connect_error) {
		echo "Internal error: connection to database error";
	    die("Connection failed: " . $conn->connect_error);
	}
	
	$sql = "SELECT uuid,name,description FROM scenarios ORDER BY name";
	$result = $conn->query($sql);
	if ($result->num_rows > 0) {
		
	    while($nodo = $result->fetch_assoc()) {
    		echo "    <p>\n";
	        echo "      <img id='{$nodo['uuid']}__' class='minus' src='images/minus_icon.gif' width='16' height='16' style='vertical-align:middle; margin-left:5px;'>\n";
	        echo "      <img src='images/small/scenario.png' width='30' height='30' style='vertical-align:middle; margin-left:5px'>\n";
	        echo "      <span class='lpnode' id='{$nodo['uuid']}' style='margin-left:5px'><b>{$nodo['name']}</b></span>\n";
		echo "    </p>\n";

			//get innstances
			$sql = "SELECT uuid, name, description " .
					"FROM instance_scenarios " .
					"WHERE scenario_id='" . $nodo['uuid'] . "'" .
					"ORDER BY name";
			$result2 = $conn->query($sql);
			if ($result2->num_rows > 0) {
   				echo "      <div id='{$nodo['uuid']}_' style='margin-left:40px'>\n";
				while($instance = $result2->fetch_assoc()) {
			   		echo "        <p><img  src='images/small/instance.png' width='30' height='30' style='z-index:20;font-size:10;vertical-align:middle; margin-left:5px;'>\n";
					echo "          <span class='lpson' id='{$instance['uuid']}' style='margin-left:5px'><b>{$instance['name']}</b></span>\n";
					echo "        </p>\n";
				}
				echo "      </div>\n";
			}
	    }
	} else {
		echo "NO SCENARIOS\n";
	}
	$conn->close();
}

/** 
 * Obtain the information of a concrete openmano scenarios reading direcly from the openmano database
 * the result is a javascript variable declaration, so that this function must be called inside a <script> html section
 */
function getScenarioId_js($uuid)
{
	
	$conn = new mysqli($GLOBALS['db_server'], $GLOBALS['db_user'], $GLOBALS['db_passwd'], $GLOBALS['db_name']);

	// Check connection
	if ($conn->connect_error) {
		die("Connection failed: " . $conn->connect_error);
	}

	$sql = "SELECT name,description,created_at,modified_at FROM scenarios WHERE uuid='$uuid' ORDER BY name";
	$result = $conn->query($sql);
	echo "var scenario={\n";
	if ($result->num_rows <= 0) {
		echo "  'name':'No scenario found',\n";
		echo "};\n"; //var scenario={
		$conn->close();
		return;
	}
	
	$scenario = $result->fetch_assoc();
	echo "  'name':'{$scenario['name']}',\n";
	echo "  'uuid':'{$uuid}',\n";
	echo "  'description':'{$scenario['description']}',\n";
	echo "  'created_at':'{$scenario['created_at']}',\n";
	echo "  'modified_at':'{$scenario['modified_at']}',\n";
	echo "  'topology':{\n";
	echo "    'nodes':{\n";
	$sql = "SELECT uuid,name,description,vnf_id,graph FROM sce_vnfs WHERE scenario_id='$uuid' ORDER BY name";
	$result2 = $conn->query($sql);
	$x=300;
	$y=100;
	while($nodo = $result2->fetch_assoc()) {
		$graph = null;
		if ($nodo['graph'] != null){
			$graph = json_decode($nodo['graph'], true);
		}
		if ($graph != null){
			if (array_key_exists('visible', $graph))
				if ($graph['visible']==false)
					continue; //skip non visible nodes
			if (array_key_exists('x', $graph))
				$x= $graph['x'];
			if (array_key_exists('y', $graph))
				$y= $graph['y'];
			if (array_key_exists('ifaces', $graph))
				$ifaces = $graph['ifaces'];
		}else{
			$ifaces = null;
		}
		echo "      '{$nodo['uuid']}': {\n";
		echo "        'type': 'VNF',\n";
		echo "        'vnf_id': '{$nodo['vnf_id']}',\n";
		echo "        'name': '{$nodo['name']}',\n";
		echo "        'x': {$x},\n";
		echo "        'y': {$y},\n";
		if ($ifaces != null){
			echo "        'ifaces': " . json_encode($ifaces, 0) . ",\n"; #JSON_HEX_QUOT
		}
		echo "      },\n";
		$x += 200;
		if ($x>=1200){
			$x=100;
			$y += 200;
		}
	}
	echo "    },\n";

	
	$sql = "SELECT uuid,name,multipoint,external,type,graph FROM sce_nets WHERE scenario_id='$uuid' ORDER BY name";
	$result = $conn->query($sql);
	if ($result->num_rows <= 0) {
		echo "  }\n};\n"; //var scenario={
		$conn->close();
		return;
	}
	echo "    'connections':{\n";
	$connection = 1;
	while($net = $result->fetch_assoc()) {
		$sql = "SELECT sce_vnf_id, external_name FROM sce_interfaces as si join interfaces as i on si.interface_id=i.uuid " .
			" WHERE sce_net_id='{$net['uuid']}' ORDER BY sce_vnf_id";
		$result2 = $conn->query($sql);
		if ($result2->num_rows <= 0) {
			continue;
		}
		if ($net['external']=='true'){
			$net_type = 'external_network';
		}elseif ($net['type']=='bridge'){
			$net_type = 'bridge_network';
		}elseif ($net['type']=='data'){ 
			$net_type = 'data_network';
		}else{
			$net_type = 'link';
		}
		//consider as lync nets with 2 connections and no graphycal information
		if ($result2->num_rows==2 && $net['graph']== null &&
			($net_type=='bridge_network' || $net_type=='data_network')	){
			$net_type = 'link';
		}
		
		$graph = null;
		$ifaces = null;
//		$visible = true;
		if ($net['graph'] != null)
			$graph = json_decode($net['graph'], true);
		if ($graph != null){
			if (array_key_exists('visible', $graph))
				if ($graph['visible']==false)
//					$visible = false;
					continue; //skip non visible nodes
			if (array_key_exists('x', $graph))
				$x= $graph['x'];
			if (array_key_exists('y', $graph))
				$y= $graph['y'];
			if (array_key_exists('ifaces', $graph))
				$ifaces = $graph['ifaces'];
		}
			
		echo "      '{$net['uuid']}': {\n";
		echo "        'type': '{$net_type}',\n";
		echo "        'name': '{$net['name']}',\n";
		if ($net_type != 'link'){
//			echo "        'visible': {$visible},\n";
			echo "        'x': {$x},\n";
			echo "        'y': {$y},\n";
			if ($ifaces != null){
				echo "        'ifaces': " . json_encode($ifaces, 0) . ",\n"; #JSON_HEX_QUOT
			}
			$x += 200;
			if ($x>=1200){
				$x=100;
				$y += 200;
			}
		}	
		
		echo "        'nodes': [\n";
		while($link = $result2->fetch_assoc()) {
			echo "          ['{$link['sce_vnf_id']}', '{$link['external_name']}'],\n";
		}
		echo "        ]\n      },\n";
	}
	echo "    }\n";	

	echo "  }\n};\n"; //var scenario={
	$conn->close();

#	echo "__" . json_encode($scenario_var, 0) ."__\n";
	

}


/**
 * Obtain the information of a concrete instance scenario reading direcly from the openmano database
 * the result is a javascript object, so that this function must be called inside a <script> html section
 * It also connect with the openvim database in order to get the virtual machine status
 */
function getInstance($uuid)
{
	
	$conn = new mysqli($GLOBALS['db_server'], $GLOBALS['db_user'], $GLOBALS['db_passwd'], $GLOBALS['db_name']);
	$conn_vim = new mysqli($GLOBALS['db_vim_server'], $GLOBALS['db_vim_user'], $GLOBALS['db_vim_passwd'], $GLOBALS['db_vim_name']);
	
	// Check connection
	if ($conn->connect_error) {
		die("Connection failed: " . $conn->connect_error);
	}
	if ($conn_vim->connect_error) {
		die("Connection failed: " . $conn_vim->connect_error);
	}

	//Obtain host list and populates $host_id2name
	$host_id2name=array();
	$sql = "SELECT name, uuid FROM hosts";
	$result_vim = $conn_vim->query($sql);
	if ($result_vim->num_rows > 0) {
		while($host_vim = $result_vim->fetch_assoc()) {
			$host_id2name[ $host_vim['uuid'] ] = $host_vim['name'];
		}
	}

	//Obtain scenario
	$sql = "SELECT name,description,created_at,modified_at FROM instance_scenarios WHERE uuid='{$uuid}'";
	$result = $conn->query($sql);
	if ($result->num_rows <= 0) {
		echo "<p>can not retreive data of instance scenario {$uuid}</p>\n";
	}
	
	$instance = $result->fetch_assoc();
	echo "<div id='instance_details'>\n";
	echo "  <ul>\n";
	echo "    <li id='instance_name' data-jstree='{\"opened\":true,\"selected\":true}'> name: <b>{$instance['name']}</b>\n";
	echo "      <ul>\n";
	echo "        <li id='instance_uuid'> uuid: {$uuid} </li>\n";
	echo "        <li id='instance_description'>description: {$instance['description']}</li>\n";
	echo "        <li id='instance_created'>created: {$instance['created_at']}</li>\n";
	//echo "        <li id='instance_modified'>modified: {$instance['modified_at']}</li>\n";
	echo "      </ul>\n";
	echo "    </li>\n";
	echo "  </ul>\n";
	echo "</div>\n";
	
	echo "<div id='instance_items'>\n";
	echo "  <ul>\n";
	echo "    <li id='scenario.instance_name' data-jstree='{\"opened\":false,\"selected\":true}'> whole scenario: <b>{$instance['name']}</b>\n";
	echo "      <ul>\n";
	
	$sql = "SELECT iv.uuid as uuid, v.name as name, v.description as description ".
		"FROM instance_vnfs as iv join vnfs as v ON iv.vnf_id=v.uuid ".
		"WHERE iv.instance_scenario_id='{$uuid}' ORDER BY v.name";
	$result2 = $conn->query($sql);
	if ($result2->num_rows <= 0) {
		echo "        <li id='{$uuid}'_>can not retreive vnfs {$result2->num_rows}</li>\n";
	}else{
		while($vnf = $result2->fetch_assoc()) {
		    //echo "        <li id='{$vnf['uuid']}' title='{$vnf['description']}' data-jstree='{\"icon\":\"images/small/vnf_default.png\"}'> \n";
		    echo "        <li id='vnf.{$vnf['uuid']}' title='{$vnf['description']}'> \n";
		    echo "          VNF: {$vnf['uuid']} <b>{$vnf['name']}</b>\n";
		    echo "          <ul>\n";
			$sql = "SELECT vim_vm_id, iv.uuid as uuid, iv.status as status, v.name as name, v.description as description " .
				"FROM instance_vms as iv join vms as v on iv.vm_id=v.uuid " .
				"WHERE iv.instance_vnf_id='{$vnf['uuid']}' ORDER BY v.name";
			$result3 = $conn->query($sql);
			if ($result3->num_rows <= 0) {
				echo "          <li id='vnf.{$vnf['uuid']}_'>can not retreive vms: {$result3}</li>\n";
			}else{
				while($vm = $result3->fetch_assoc()) {
					$vm_status = $vm['status'];
					$vm_error = "";
					$vm_host = "";
					$sql = "SELECT status, last_error, host_id FROM instances WHERE uuid='{$vm['vim_vm_id']}'";
					$result_vim = $conn_vim->query($sql);
					if ($result_vim->num_rows > 0) {
						$vm_vim = $result_vim->fetch_assoc();
						$vm_status = $vm_vim['status'];
						if (array_key_exists($vm_vim['host_id'], $host_id2name))
							$vm_host = "   @" . $host_id2name[ $vm_vim['host_id'] ];
						if ($vm_status=="ERROR")
							$vm_error = " (ERROR: " .$vm_vim['last_error'] .")";
					}
					echo "          <li id='vm.{$vm['uuid']}' title='{$vm['description']}  {$vm_host}' data-jstree='{\"icon\":\"images/small/vm_{$vm_status}.png\"}'> \n";
					echo "            VM: {$vm['uuid']} <b>{$vm['name']}{$vm_error}</b>\n";
					echo "          </li>\n";
				}
			}
	    	echo "          </ul>\n";
	    	echo "        </li>\n";
		}
	}
	echo "      </ul>\n";
	echo "    </li>\n";
	echo "  </ul>\n";
	echo "</div>\n";
	$conn->close();
}

?>


