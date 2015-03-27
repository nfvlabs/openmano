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
 * Obtain compute nodes reading direcly from the openvim database
 * echoing a html "tree"
 */ 
function getHosts()
{
	$conn_vim = new mysqli($GLOBALS['db_vim_server'], $GLOBALS['db_vim_user'], $GLOBALS['db_vim_passwd'], $GLOBALS['db_vim_name']);
	
	// Check connection
	if ($conn_vim->connect_error) {
		echo "Internal error: connection to database error";
	    die("Connection failed: " . $conn_vim->connect_error);
	}
	
	$sql = "SELECT uuid, name, description FROM hosts ORDER BY name";
	$result = $conn_vim->query($sql);
	if ($result->num_rows > 0) {
		
	    while($host = $result->fetch_assoc()) {
    		echo "    <p>\n";
	        echo "      <img id='{$host['uuid']}__' class='minus' src='images/minus_icon.gif' width='16' height='16' style='vertical-align:middle; margin-left:10px;'>\n";
	        echo "      <img src='images/physical/server.png' width='30' height='30' style='vertical-align:middle; margin-left:10px'>\n";
	        echo "      <span class='lpnode' id='{$host['uuid']}' style='margin-left:10px'><b>{$host['name']}</b></span>\n";
	        echo "    </p>\n";

			//get instances
			$sql = "SELECT uuid, name, description, status, last_error " .
					"FROM instances " .
					"WHERE host_id='{$host['uuid']}'" .
					"ORDER BY name";
			$result2 = $conn_vim->query($sql);
			if ($result2->num_rows > 0) {
   				echo "      <div id='{$host['uuid']}_' style='margin-left:30px;'>\n";
				while($instance = $result2->fetch_assoc()) {
					if ($instance['status'] == "ERROR")
						$title = $instance['last_error'];
					else
						$title = $instance['description'];
			   		echo "        <p><img  src='images/small/vm_{$instance['status']}.png' width='30' height='30' style='z-index:20;font-size:10;vertical-align:middle; margin-left:10px;'>\n";
					echo "          <span class='lpson' id='{$instance['uuid']}' title='{$title}' style='margin-left:10px'><b> {$instance['name']}</b></span>\n";
					echo "        </p>\n";
				}
				echo "</div>\n";
			}
	    }
	} else {
		echo "NO HOSTS";
	}
	$conn_vim->close();
}


?>


