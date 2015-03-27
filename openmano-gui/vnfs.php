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
    Version: 0.50
    Date: Feb 2015
-->

<html>
  <head>
	<meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
	<link rel="stylesheet" type="text/css" href="css/tidgui.css">
	<title>openMANO web</title>
	<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"></script>
	<script src="js/common.js"></script>
  </head>  

  <body>
	<div id="containerPadre">
    	<div id="containerSettings" ></div>
		<div id="containerUp" >
			<div id="containerTabs">
				<ul id="menu">
					<li class="tab" id="menu_scenario"><a href="scenario.php">Scenarios</a></li>
					<li class="tabselected" id="menu_vnf"><a href="vnfs.php">VNFs</a></li>
					<li class="tab" id="menu_physical"><a href="physical.php">Physical</a></li>
				</ul>            
			</div>
			<div id="containerLogo">openmano-gui</div>
			<div id="logo"><img height="60" src="images/nfvlabs_.png" /></div>
      	</div>

		<div id="containerDown" style="visibility:visible">
			<div id="containerVNFs">
				<h4 style="text-align:center">Virtual Network Functions</h4><hr>
				<?php
					require 'config.php';
					require 'get_vnfs.php';
					getConfig();
					getVnfs(true);
				?>
			</div>
			<div id="aux1" >
            	<div id="containerCommands" > 
                	<select title="Select DataCenter" id="datacenterCombo">
						<option	value="TODO1">Datacenter 1</option>
						<option value="TODO2">Datacenter 2</option>
					</select>  
				</div>
				<div id="containerLogicalDrawing">
				</div>
			</div>
		</div>
	</div>
  </body>
</html>
