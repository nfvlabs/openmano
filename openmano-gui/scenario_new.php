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
    Version: 0.52
    Date: Feb 2015
-->

<html>
  <head>
	<meta http-equiv="Content-Type" content="text/html;charset=utf-8">
	<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"></script> 
	<script src="js/jquery-ui-1.9.2-min.js"></script>
	<script src="https://rawgit.com/sporritt/jsPlumb/1.5.0/dist/js/jquery.jsPlumb-1.5.0-min.js"></script>
	<script src="js/contextmenu.js"></script>
	<script src="js/js-yaml.js"></script>
	<script src="js/common.js"></script>
	
	<link rel="stylesheet" type="text/css" href="css/tidgui.css">
	<title>openMANO web</title>
  </head>

  <body oncontextmenu="return(false);">
	<div id="containerPadre">
		<div id="containerSettings"></div>
		<div id="containerUp">
			<div id="containerTabs">
				<ul id="menu">
					<li class="tabselected" id="menu_scenario"><a href="scenario.php">Scenarios</a></li>
					<li class="tab" id="menu_vnf"><a href="vnfs.php">VNFs</a></li>
					<li class="tab" id="menu_physical"><a href="physical.php">Physical</a></li>
				</ul>
			</div>
			<div id="containerLogo">openmano-gui</div>
			<div id="logo"><img height="60" src="images/nfvlabs_.png" /></div>
		</div>

		<div id="containerDown" style="visibility: visible">
			<div id="containerVNFs">
				<h4 style="text-align: center">Virtual Network Functions</h4>
				<hr>
				<?php
				require 'config.php';
				require 'get_vnfs.php';
				require 'get_scenarios.php';
				$uuid=null;
				parse_str($_SERVER['QUERY_STRING'], $myArray);
				if (key_exists('uuid', $myArray)){
					$uuid=$myArray['uuid'];
				}
				getConfig();
				getVnfs(true);
				?>
			</div>
			<div id="aux1">
				<div id="containerCommands">
					<select title="Select DataCenter" id="datacenterCombo">
						<option	value="TODO1">Datacenter 1</option>
						<option value="TODO2">Datacenter 2</option>
					</select>  
				</div>
				<div id="containerLogicalDrawing">
					<form> 
						Scenario Name:<input type="text" id="scenarioName"/>  <br>
						Description: <input type="text" id="scenarioDescription"/> 
					</form>
				</div>
			</div>
		</div>
	</div>
	<div id="dialog" title="Titulo dialog">
		<p>Contenido de la ventana.</p>
	</div>

	<script src="js/scenario_utils.js"></script>
<script>

/* Global variables */
var instances_vnfs={};  // dictionary of drawn vnf instances  
var active_vnf="";      // selected vnf instance
var vnf_id_selected=""; // selected vnf from the catalogue, at the left panel
var connectorPaintStyle = {lineWidth:4,strokeStyle:'rgba(0,0,0,0.5)',joinstyle:"round",outlineColor:"ivory",outlineWidth:1};
var connectorHoverStyle = {lineWidth:5,strokeStyle:'SteelBlue',outlineWidth:1,outlineColor:"ivory"};
//var connectorPaintStyle_array={
//		"d": {lineWidth:4, strokeStyle:'rgba(1,0,0,0.5)', joinstyle:"round", outlineColor:"ivory", outlineWidth:1},
//		"m": {lineWidth:4, strokeStyle:'rgba(0,1,0,0.5)', joinstyle:"round", outlineColor:"ivory", outlineWidth:1},
//		"v": {lineWidth:4, strokeStyle:'rgba(0,0,1,0.5)', joinstyle:"round", outlineColor:"ivory", outlineWidth:1},
//		"o": {lineWidth:4, strokeStyle:'rgba(0,0,0,0.5)', joinstyle:"round", outlineColor:"ivory", outlineWidth:1},
//	};

//vnfsDefs
<?php
	getVnfs_js();
	global $db_server, $db_user, $db_passwd, $db_name, $mano_port, $mano_path, $mano_domain, $mano_tenant;
	echo "    mano_url_base='http://" . ($mano_domain!=null? "{$mano_domain}" : "'+window.location.host+'"). ":{$mano_port}{$mano_path}';\n";
	echo "    mano_tenant='{$mano_tenant}';\n";
	if ($uuid != null){
		getScenarioId_js($uuid);
	}else{
		echo "var scenario=null\n";
	}				
?>
/* Preload VNF image so that VNFs interfaces are painted correctly*/
   	var cacheImage = document.createElement('img');
	cacheImage.src = "images/big/vnf_default.png";


$(document).ready(function(){
	dynamicResize();
	
});


function dynamicResize() {
	
	var winh=$(window).height();
	var winw=$(window).width(); 
	ratioW=(winw / parseFloat(2071)) ;
	ratioH=(winh / parseFloat(1071)) ;
	  
	
	$('#containerPadre').css("height",Math.round(984 *ratioH));
	$('#containerPadre').css("width",Math.round(1920*ratioW));
	$('#containerDown').css("height", Math.round(960*ratioH));
	$('#containerDown').css("width", Math.round(1918*ratioW) );
	$('#containerDown2').css("height", Math.round(1000*ratioH));
	$('#containerDown2').css("width", Math.round(1918*ratioW) );
	$('#containerLogicalScenario').css("height", Math.round(1000*ratioH));
	$('#containerLogicalScenario').css("width", Math.round(1780*ratioW) );
	$('#containerVNFs').css("height", Math.round(988*ratioH));
	$('#containerVNFs').css("width", Math.round(300*ratioW) );
	$('#containerPVL').css("height", Math.round(998*ratioH));
	$('#containerPVL').css("width", Math.round(400*ratioW) );
	$('#containerPVR').css("height", Math.round(998*ratioH));
	$('#containerPVR').css("width", Math.round(1504*ratioW));
	
	$('#containerCommands').css("width", Math.round(1600*ratioW) );
	$('#containerCommands').css("left", Math.round(308*ratioW) );
	
	
	
	$('#containerLogicalDrawing').css("height", Math.round(944*ratioH) );
	$('#containerLogicalDrawing').css("width", Math.round(1600*ratioW) );
	$('#containerLogicalDrawing').css("left", Math.round(312*ratioW) );
	
	$('#containerPhysicalScenario').css("height", Math.round(490*ratioH) );
	$('#containerPhysicalScenario').css("width", Math.round(800*ratioW) );
	
	
	$('#container').css("height", Math.round(600*ratioH)  );
	$('#aux1').css("width", Math.round(1700*ratioW) );
	$('#containerTabs').css("width", Math.round(500) );
	$('#containerSettings').css("width", Math.round(300*ratioW)  );

}


var jsPlumbSelectedEndPoint;

jsPlumb.ready(function() {
//dynamicResize();
	var i = 0;

	for (var key in vnfsDefs){
		//console.log("alf: draggable222  " + key);
 		$("#"+key).draggable(
 		 	{ helper:"clone" },
			{start:function(key1){
				return function(){
					vnf_id_selected=key1;
					if (active_vnf in instances_vnfs){
						instances_vnfs[active_vnf].css({'background-color':'ivory'});
					} 
					active_vnf="";
				}}(key)
 			}
		);
 	};
	
	
	$('#containerVNFs').droppable();
	//$('#containerVNFs').selectable();
	$('#containerLogicalDrawing').droppable();

	$(document).keydown( function(e){
		if (e.which==46 && active_vnf!=""){  //pressed delete
			// find vnf object
			var objifcs=null;
			for (var v in instances_vnfs) {
				if (instances_vnfs[v][0].id == active_vnf ){
					objifcs=instances_vnfs[v].ifaces; 
					break;
				}
			} 
			if (objifcs==null) 
				return;
			   
			// borrar los endpoints correspondientes
			for(var j in objifcs){
				jsPlumb.deleteEndpoint(objifcs[j]);
			}
			// remove all conections and object
			jsPlumb.detachAllConnections($(instances_vnfs[v]));
			$(instances_vnfs[v]).remove();
			delete instances_vnfs[v] ;//e.stopPropagation(); 
			active_vnf="";
		}
	} );
	
	$('#containerLogicalDrawing').mousedown(function(e){// Remove focus from object when clicking on canvas
		var tgt=$(e.target);
		if (active_vnf in instances_vnfs){
			instances_vnfs[active_vnf].css({'background-color':'ivory'});
		} 
		active_vnf="";
		if(tgt.hasClass("item")){
			active_vnf=e.target.id
		}; 
		if(tgt.hasClass("title")||tgt.hasClass("vnfimg")){
			active_vnf=tgt.parent().attr('id');
		};// ensure active_vnf is new_instance_vnf, not a childnode
		if(active_vnf!=""){
			if (active_vnf in instances_vnfs)
				instances_vnfs[active_vnf].css({'background-color':'Wheat'});
		};
	});
	
	// logicalview file upload
	// Cancel default actions and handle files drag and drop over logicalview container
	$('#containerLogicalDrawing')[0].addEventListener("dragover", 
			function(event) {event.preventDefault();}, false
	);


	$('#containerLogicalDrawing')[0].addEventListener("drop", function(event) {
		console.log("alf: drop de sobre containerLogicalDrawing   222");
		var scenario = null;
	    event.preventDefault();

	    var files = event.dataTransfer.files;
	    var reader = new FileReader(); 
	    reader.onload = function(event) {
		    var contents = event.target.result;
		    //console.log("File contents: " + contents);
	
		    scenario=jsyaml.load(contents );
		    if (scenario != null && "nodes" in scenario && "name" in scenario){
			    //clean up previous scenario
			    jsPlumb.detachEveryConnection();
			    jsPlumb.deleteEveryEndpoint();
			    for (var v in instances_vnfs){instances_vnfs[v].remove();} 
			    instances_vnfs={};
		    	load_scenario(scenario, true);
		    }

	    };

		reader.onerror = function(event) {
			console.error("File could not be read! Code " + event.target.error.code);
	    };
		reader.readAsText(files[0]);
		//lViewYamlData=jsyaml.load(reader.readAsText(files[0]));
	}, false );
	
		
	$('#containerLogicalDrawing').on('drop',function(e){
		console.log("alf: drop de sobre containerLogicalDrawing");
		if (vnf_id_selected==""){
			return;
		} // used to connect dragged object with vnf definition 

		var name =  vnfsDefs[vnf_id_selected]["model"];
		if ("number_items" in vnfsDefs[vnf_id_selected] && vnfsDefs[vnf_id_selected]["number_items"]>0){
			name += "-" + vnfsDefs[vnf_id_selected]["number_items"];
			vnfsDefs[vnf_id_selected]["number_items"] += 1;
		}else{
			vnfsDefs[vnf_id_selected]["number_items"]=1;
		}
		var vnfy=e.pageY-135;
		var vnfx=e.pageX-390;
		var uuid = vnf_id_selected+"_"+i;
		var new_instance_vnf = createVNFProgrammatically(uuid, vnf_id_selected, name, vnfx, vnfy, vnfsDefs[vnf_id_selected]["ifaces"], true);
		console.log("new vnf type: ", vnf_id_selected, " value: ", new_instance_vnf); //ALF
		vnf_id_selected="";
		//active_vnf=uuid;
		i++;
	}); 

	$('#containerCommands').append('<input id="cancelButton" type="button" class="actionButton" value="Discard">').button();
	$('#containerCommands').append('<input id="cleanButton" type="button" class="actionButton" value="Clean">').button();
	$('#containerCommands').append('<input id="saveButton" type="button" class="actionButton" value="Save">').button();
	
	$("#cleanButton").click(function(e){ 
	    //clean up previous scenario
	    jsPlumb.detachEveryConnection();
	    jsPlumb.deleteEveryEndpoint();
	    for (var v in instances_vnfs){instances_vnfs[v].remove();} 
	    for (var v in vnfsDefs){vnfsDefs[v]["number_items"]=0;} 
	    instances_vnfs={};
	});
	
	$("#cancelButton").click(function(e){ 
		location.assign("scenario.php");
	});
	
	/* Top panel handlers */
	$("#saveButton").click(function(e){ 
		var name = document.getElementById("scenarioName").value;
		var description = document.getElementById("scenarioDescription").value;
		//var name = prompt("Provide a name for the scenario");
		if (name==null || name==""){
			alert("Provide a name at Scenario Name text box");
			return;
		}
		var yamlData = generateNewScenarioCommand(name, description);
		if (yamlData.indexOf("Error")==0){
			alert(yamlData);
			return;
		}
	
		$.ajaxSetup({headers:{'Accept':'application/yaml','Content-Type':'application/yaml'}});  //ALF
		var jqxhr=$.post(mano_url_base + mano_tenant +"/scenarios",
				yamlData,
			function(data,status){
				alert("Result: " + status + "\nData: " + data);
				location.assign("scenario.php");
			}
		);
		jqxhr.fail(function(data,status) {
			alert("Result: " + status + "\nData: " + data.responseText);
		});
	
	});


if (scenario != null){
	load_scenario(scenario, true);
	document.getElementById("scenarioName").value        = scenario['name'];
	document.getElementById("scenarioDescription").value = scenario['description'];
}


});


</script>


</body>
</html>
