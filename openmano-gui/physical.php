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

    # Author: Alfonso Tierno, Gerardo Garcia
    # Version: 0.52
    # Date: Feb 2015
-->


<html>
  <head>
	<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"></script> 
	<script src="js/common.js"></script>
	<meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
	<link rel="stylesheet" type="text/css" href="css/tidgui.css">
	<title>openMANO web</title>
  </head>  

  <body>
	<div id="containerPadre">
		<div id="containerSettings" ></div>
		<div id="containerUp" >
			<div id="containerTabs">
				<ul id="menu">
					<li class="tab" id="menu_scenario"><a href="scenario.php">Scenarios</a></li>
					<li class="tab" id="menu_vnf"><a href="vnfs.php">VNFs</a></li>
					<li class="tabselected" id="menu_physical"><a href="physical.php">Physical</a></li>
				</ul>            
			</div>
			<div id="containerLogo">openmano-gui</div>
			<div id="logo"><img height="60" src="images/nfvlabs_.png" /></div>
      	</div>
		<div id="containerDown2" >
			<div id="containerPVL">  <h3 style="text-align:center">Physical Infrastructure<br></h3><hr>
				<?php
				require 'config.php';
				require 'get_hosts.php';
				getConfig();
				getHosts();
				echo "<script>\n";
				echo "    mano_url_base='http://" . ($mano_domain!=null? "{$mano_domain}" : "'+window.location.host+'"). ":{$mano_port}{$mano_path}';\n";
				#echo "    mano_url_base='http://" . ($mano_domain!=null? "{$mano_domain}" : $_SERVER['HTTP_HOST']). ":{$mano_port}{$mano_path}';\n";
				echo "    mano_tenant='{$mano_tenant}';\n";
				echo "</script>\n";
				?>
			</div>
			<div id="containerPVR" >   </div>
		</div>
	</div>

<script>
var selected_item={}; 
selected_item["name"]="";  
selected_item["uuid"]="";  
selected_item["type"]=""; 

$(document).ready(function(){
	
	$(".lpnode").click(function(){
		console.log("click on host " + this.id);
		selected_item["uuid"] = this.id;
		selected_item["name"] = this.textContent;   //innerText is not valid for firefox;
		selected_item["type"] = 'host';
		console.log(selected_item["name"]);
	
		//$("#containerLogicalDrawing").load("scenario_id.php?uuid="+selected_item["uuid"]+"&type=scenario");
		console.log("host loading");
	});
	
	$(".lpson").click(function(){
		console.log("click on instance-scenario " + this.id);
		selected_item["uuid"] = this.id;
		selected_item["name"] = this.textContent;   //innerText is not valid for firefox;
		selected_item["type"] = 'vm';
		console.log(selected_item["name"]);
		
		//$("#containerLogicalDrawing").load("scenario_id.php?uuid="+selected_item["uuid"]+"&type=instance");
		console.log("vm loading");
	});
	
});				
</script>

  </body>
</html>
