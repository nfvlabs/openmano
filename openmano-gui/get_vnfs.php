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


$vnfs = array();

/**
 * Obtain the list of VNFs scenarios reading direcly from the openmano database
 * Generates a PHP global variable ($vnfs) with this information
 * It can generate a html tree id $echoPhp is true
 */
function getVnfs($echoPhp)
{
	//getConfig();
	global $vnfs;
	//$class='';
	$class='alf.tierno'; //just a name not used 
	$conn = new mysqli($GLOBALS['db_server'], $GLOBALS['db_user'], $GLOBALS['db_passwd'], $GLOBALS['db_name']);

	// Check connection
	if ($conn->connect_error) {
	    die("Connection failed: " . $conn->connect_error);
	}
	
	$sql = "SELECT uuid,name,class,description FROM vnfs ORDER BY class,name";
	$result = $conn->query($sql);
	if ($result->num_rows > 0) {
		
	    while($nodo = $result->fetch_assoc()) {
	    	if ($class!=$nodo['class']){
	    		if ($class!='alf.tierno'){
	    			if ($echoPhp==true){
	    				echo "    </div>\n";
	    			}
	    		}
	    		$class=$nodo['class'];
	    		$image_small_default='images/small/vnf_' . strtolower($nodo['class']) . '.png';
	    		if (!file_exists($image_small_default)){
	    			$image_small_default="images/small/vnf_default.png";
	    		}
	    		$image_big_default='images/big/vnf_' . strtolower($nodo['class']) . '.png';
	    		if (!file_exists($image_big_default)){
	    			$image_big_default="images/big/vnf_default.png";
	    		}
	    		if ($echoPhp==true){
		    		echo "    <p class='lpnode' id='{$nodo['class']}'>\n";
			        echo "      <img id='{$nodo['class']}__' class='minus' src='images/minus_icon.gif' width='16' height='16' style='vertical-align:middle; margin-left:10px;'>\n";
			        echo "      <img src='{$image_small_default}' width='30' height='30' style='vertical-align:middle; margin-left:10px'>\n";
			        echo "      <span  style='margin-left:10px'><b> {$nodo['class']} </b></span>\n";
			        echo "    </p>\n";
		   			echo "    <div id='{$nodo['class']}_' style='vertical-align:middle; margin-left:40px;'>\n";
	    		}
			}
			$image_small="images/small/vnf_" . strtolower($nodo['name']) . ".png";
			if (!file_exists($image_small)){
	   			$image_small = $image_small_default;
	   		}
			$image_big="images/big/vnf_" . strtolower($nodo['name']) . ".png";
			if (!file_exists($image_big)){
	   			$image_big = $image_big_default;
	   		}
	   		array_push($vnfs, "        '{$nodo['uuid']}':{'type':'VNF','model': '{$nodo['name']}', 'img':'{$image_big}','description':'{$nodo['description']}','ifaces':{\n            ");	        
	    	if ($echoPhp==true){
		   		echo "        <p class='{$class}'>\n";
				echo "          <img class='lpson' id='{$nodo['uuid']}' src='{$image_small}' width='30' height='30' style='z-index:20;font-size:10;'>\n";
				echo "          <span  style='margin-left:10px'><b> {$nodo['name']}</b></span>\n";
				echo "        </p>\n";
	    	}
			//get interfaces
			$sql = "SELECT bw,external_name,type " .
					"FROM interfaces join vms on interfaces.vm_id=vms.uuid " .
					"WHERE external_name is NOT NULL AND vms.vnf_id='{$nodo['uuid']}' " .
					"ORDER BY type,external_name";
			$result2 = $conn->query($sql);
			if ($result2->num_rows > 0) {
		    	$botton="";
		    	$left="";
		    	$right="";
		    	$left_right=0; # if >=0 left else right
			    while($iface = $result2->fetch_assoc()) {
			    	if ($iface['type']=='mgmt')       $iface_type = 'm';
			    	elseif ($iface['type']=='bridge') $iface_type = 'v';
			    	elseif ($iface['type']=='data')   $iface_type = 'd';
			    	else                              $iface_type = 'o';
			    	if ($iface['type']=='mgmt' or $iface['type']=='bridge'){
			    		$botton .=  "['{$iface['external_name']}','{$iface_type}'],";
			    	}
			    	if ($iface['type']=='data'){
			    		if ($left_right>=0){
			    			$left .=  "['{$iface['external_name']}','{$iface_type}'],";
			    		}else{
			    			$right .= "['{$iface['external_name']}','{$iface_type}'],";
			    		}
		    			$left_right += 1;
		    			if ($left_right==2){ $left_right=-2;} #put 2 interfaces left, 2 right and so on
			    	}
				}
				if (strlen($left)>0){
					$vnfs[count($vnfs)-1] .= "'left':[{$left}],";
				}
				if (strlen($right)>0){
					$vnfs[count($vnfs)-1] .= "'right':[{$right}],";
				}
				if (strlen($botton)>0){
					$vnfs[count($vnfs)-1] .= "'bottom':[{$botton}],";
				}
				$vnfs[count($vnfs)-1] .= "\n        }},";
				
			}
	    }
		if ($echoPhp==true){
	    	echo "    </div>\n";
		}
	} else {
		if ($echoPhp==true){
			echo "NO VNFs";
		}
	}

	array_push($vnfs, "        'bridge_net':{'type':'network','model': 'bridge_net', 'img':'images/big/bridge_net.png','description':'virtio net','ifaces':{'bottom':[ ['0','v']] }},\n");
	array_push($vnfs, "        'dataplane_net':{'type':'network','model': 'dataplane_net', 'img':'images/big/dataplane_net.png','description':'dataplane net','ifaces':{'bottom':[ ['0','d']] }},\n");
	if ($echoPhp==true){
		echo "    <p class='lpnode' id='Networks'>\n";
		echo "      <img id='Networks__' class='minus' src='images/minus_icon.gif' width='16' height='16' style='vertical-align:middle; margin-left:10px;'>\n";
		echo "      <img src='images/small/nube.png' width='30' height='30' style='vertical-align:middle; margin-left:10px'>\n";
		echo "      <span  style='margin-left:10px'><b>Networks</b></span>\n";
		echo "    </p>\n";
		echo "    <div id='Networks_' style='vertical-align:middle; margin-left:40px;'>\n";
		echo "        <p>\n>";
		echo "          <img class='lpson' id='bridge_net' src='images/small/bridge_net.png' width='30' height='30' style='z-index:20;font-size:10;'>\n";
	    echo "          <span style='margin-left:10px'><b>bridge net</b></span>\n";
	    echo "        </p>\n";
		echo "        <p>\n>";
	    echo "          <img class='lpson' id='dataplane_net' src='images/small/dataplane_net.png' width='30' height='30' style='z-index:20;font-size:10;'>\n";
	    echo "          <span style='margin-left:10px'><b>dataplane net</b></span>\n";
	    echo "        </p>\n";
	    echo "    </div>\n";
	}
	
	
	if ($echoPhp==true){
		echo "    <p class='lpnode' id='External_Networks'>\n";
		echo "      <img id='External_Networks__' class='minus' src='images/minus_icon.gif' width='16' height='16' style='vertical-align:middle; margin-left:10px;'>\n";
		echo "      <img src='images/small/nube.png' width='30' height='30' style='vertical-align:middle; margin-left:10px'>\n";
		echo "      <span  style='margin-left:10px'><b>External Networks</b></span>\n";
		echo "    </p>\n";
		echo "    <div id='External_Networks_' style='vertical-align:middle; margin-left:40px;'>\n";
	}
	$sql = "SELECT uuid,name,type,description FROM datacenter_nets";
	$result = $conn->query($sql);
	$image_small_default='images/small/nube.png';
	$image_big_default='images/big/nube.png';
	if ($result->num_rows > 0) {
	    while($dcnet = $result->fetch_assoc()) {
			$image_small="images/small/" . strtolower($dcnet['name']) . ".png";
    		if (!file_exists($image_small)){
	   			$image_small = $image_small_default;
	   		}
			$image_big="images/big/" . strtolower($dcnet['name']) . ".png";
    		if (!file_exists($image_big)){
	   			$image_big = $image_big_default;
	   		}
	   		if ($echoPhp==true){
				echo "        <p>\n>";
				echo "          <img class='lpson' id='{$dcnet['uuid']}' src='{$image_small}' width='30' height='30' style='z-index:20;font-size:10;'>\n";
	    		echo "          <span style='margin-left:10px'><b>'{$dcnet['name']}'</b></span>\n";
	    		echo "        </p>\n";
	   		}
	   		array_push($vnfs, "        '{$dcnet['uuid']}':{'type':'external_network','model': '{$dcnet['name']}', 'img':'{$image_big}','description':'{$dcnet['description']}','ifaces':{\n            ");
	   		if ($dcnet['type'] == "ptp"){	        
				$vnfs[count($vnfs)-1] .= "'left':[['0','d']]";
			}else if ($dcnet['type'] == "data"){
				$vnfs[count($vnfs)-1] .= "'bottom':[ ['0','d']]"; //,['1','d'],['2','d'],['3','d'],['4','d'],['5','d'],['6','d'] ]";
			}else{
				$vnfs[count($vnfs)-1] .= "'bottom':[ ['0','v']]"; //,['1','v'],['2','v'],['3','v'],['4','v'],['5','v'],['6','v'] ]";
			}
			$vnfs[count($vnfs)-1] .= "\n        }},";
	    }
	}
	if ($echoPhp==true){
    	echo "    </div>\n";
	}

	$conn->close();
	
}

/**
 * Generates a javascript variable with the information of vnfs
 * It uses the PHP global variable $vnfs generated with function getVnfs()
 */
function getVnfs_js()
{
	global $vnfs;
	echo "    vnfsDefs={\n";
	for($x=0; $x < count($vnfs); $x++) {
    	echo $vnfs[$x] . "\n";
    }
	echo "    };\n";
}


?>


