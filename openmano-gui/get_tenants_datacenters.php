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
    # Version: 0.53
    # Date: Mar 2016

//require 'config.php' variables;


#$vnfs = array();

/**
 * Obtain the list of VNFs scenarios reading direcly from the openmano database
 * Generates a PHP global variable ($vnfs) with this information
 * It can generate a html tree id $echoPhp is true
 */
function getTenantDatacenter($echoPhp)
{
	//getConfig();
	global $tenants;
	//$class='';
	$conn = new mysqli($GLOBALS['db_server'], $GLOBALS['db_user'], $GLOBALS['db_passwd'], $GLOBALS['db_name']);

	// Check connection
	if ($conn->connect_error) {
	    die("Connection failed: " . $conn->connect_error);
	}
	
	$sql = "SELECT uuid,name FROM nfvo_tenants ORDER BY created_at";
	$result = $conn->query($sql);
	if ($result->num_rows > 0) {
		
	    while($nodo = $result->fetch_assoc()) {
	    	
	   		#array_push($tenants, "        '{$nodo['uuid']}':{'type':'VNF','model': '{$nodo['name']}', 'img':'{$image_big}','description':'{$nodo['description']}','ifaces':{\n            ");	        
	    	if ($echoPhp==true){
		   		echo "\t\t\t\t\t\t<option	value='{$nodo['uuid']}'>{$nodo['name']}</option>\n";
	    	}
	    }
	}
}

?>


