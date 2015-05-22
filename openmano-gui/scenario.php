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

    Author: Alfonso Tierno, Gerardo Garcia
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
<link rel="stylesheet" type="text/css" href="css/jstree.min.css">
<script src="js/jstree.min.js"></script>

<link rel="stylesheet" type="text/css" href="css/tidgui.css">
<title>openMANO web</title>
</head>

<body>
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
				<h4 style="text-align: center">Scenarios/Instances</h4>
				<hr>
				<?php
				global $db_server, $db_user, $db_passwd, $db_name, $mano_port, $mano_path, $mano_domain, $mano_tenant;
				require 'config.php';
				require 'get_scenarios.php';
				require 'get_vnfs.php';
				getConfig();
				getVnfs(false);
				getScenarios();
				echo "<script>\n";
				echo "    mano_url_base='http://" . ($mano_domain!=null? "{$mano_domain}" : "'+window.location.host+'"). ":{$mano_port}{$mano_path}';\n";
				#echo "    mano_url_base='http://" . ($mano_domain!=null? "{$mano_domain}" : $_SERVER['HTTP_HOST']). ":{$mano_port}{$mano_path}';\n";
				echo "    mano_tenant='{$mano_tenant}';\n";
				echo "</script>\n";
				?>
			</div>
			<div id="aux1">
				<div id="containerCommands">
					<select title="Select DataCenter" id="datacenterCombo" >
						<option	value="TODO1">Datacenter 1</option>
						<option value="TODO2">Datacenter 2</option>
					</select>
				</div>
				<div id="containerLogicalDrawing"></div>
			</div>
		</div>
	</div>

	<script>

	<?php
		getVnfs_js();
	?>
				
	/* Global variables */
	var selected_item={}; 
	selected_item["name"]="";  
	selected_item["uuid"]="";  
	selected_item["type"]=""; 
	var instances_vnfs={}; 
	var textDiv=null;
	var connectorPaintStyle = {lineWidth:4, strokeStyle:'rgba(0,0,0,0.5)', joinstyle:"round", outlineColor:"ivory", outlineWidth:1};
	var connectorHoverStyle = {lineWidth:5, strokeStyle:'SteelBlue', outlineWidth:1, outlineColor:"ivory"};
	
	$('#containerCommands').append('<input id="newButton"    type="button" class="actionButton scenarioNew"  value="New" title="Creates a new scenario">').button();
	$('#containerCommands').append('<input id="editButton"   type="button" class="actionButton scenarioEdit" value="Save" title="Saves changes of current scenario">').button();
	$('#containerCommands').append('<input id="deployButton" type="button" class="actionButton scenarioEdit" value="Deploy" title="Launches a new instance of the scenario">').button();
	$('#containerCommands').append('<input id="reserveButton" type="button" class="actionButton scenarioEdit" value="Reserve" title="Launches a new instance of the scenario without starting virtual machines">').button();
/*	$('#containerCommands').append('<input id="downloadButton" type="button" class="actionButton scenarioEdit" value="Download" title="Download the selected scenario">').button();
*/
	$('#containerCommands').append('<input id="deleteButton" type="button" class="actionButton scenarioEdit" value="Delete" title="Deletes the scenario">').button();
	$('#containerCommands').append('<input id="cloneButton"  type="button" class="actionButton scenarioEdit" value="Clone" title="Creates a new scenario based on current one">').button();
	$('#containerCommands').append('<input id="textButton"  type="button" class="actionButton scenarioEdit" value="See as text" title="Show the scenario definiton text template">').button();
		
/*	$('#containerCommands').append('<input id="saveButton"   type="button" class="actionButton" value="Save">').button();
	$('#containerCommands').append('<input id="saveAsButton" type="button" class="actionButton" value="Save as">').button();
	$('#containerCommands').append('<input id="clearButton"  type="button" class="actionButton" value="Clear">').button();
	$('#containerCommands').append('<input id="cancelButton" type="button" class="actionButton" value="Cancel">').button();
*/			
	$('#containerCommands').append('<input id="updateButton" type="button" class="actionButton instanceEdit"  value="Update" title="Update status of virtual machines">').button();
	$('#containerCommands').append('<input id="startButton"  type="button" class="actionButton instanceEdit"  value="Start" title="Starts selected VMs">').button();
	$('#containerCommands').append('<input id="stopButton"   type="button" class="actionButton instanceEdit" value="Shutdown" title="Sends a ACPI shutdown to selected VMs">').button();
	$('#containerCommands').append('<input id="forceOffButton" type="button" class="actionButton instanceEdit" value="Force off" title="Forces a shutdown to selected VMs">').button();
	$('#containerCommands').append('<input id="rebootButton" type="button" class="actionButton instanceEdit" value="Reboot" title="Sends ACPI reboot to selected VMs">').button();
	$('#containerCommands').append('<input id="rebuildButton" type="button" class="actionButton instanceEdit" value="Rebuild" title="Deletes and creates the VM">').button();
	$('#containerCommands').append('<input id="delInstanceButton" type="button" class="actionButton instanceEdit" value="Delete" title="Stop VMs and delete current instance scenario">').button();

	/* Preload VNF image so that VNFs interfaces are painted correctly*/
   	var cacheImage = document.createElement('img');
	cacheImage.src = "images/big/vnf_default.png";
		
	
	jsPlumb.ready(function() {
		// Cancel default actions and handle files drag and drop over logicalview container
		
		$(".scenarioNew").show();
		$(".scenarioEdit").hide();
		$(".instanceEdit").hide();
		dynamicResize();
		
		$(".lpnode").click(function(){
			console.log("click on scenario " + this.id);
			selected_item["uuid"] = this.id;
			selected_item["name"] = this.textContent; //innerText is not valid for firefox
			selected_item["type"] = 'scenario';
			console.log(selected_item["name"]);
			$(".scenarioNew").show();
			$(".scenarioEdit").show();
			$(".instanceEdit").hide();
			
			$("#containerLogicalDrawing").load("scenario_id.php?uuid="+selected_item["uuid"]+"&type=scenario");
			//var obj_ = document.getElementById("containerLogicalDrawing");
			console.log("scenario loading");
		});
		
		$(".lpson").click(function(){
			console.log("click on instance-scenario " + this.id);
			selected_item["uuid"] = this.id;
			selected_item["name"] = this.textContent;   //innerText is not valid for firefox
			selected_item["type"] = 'instance';
			console.log(selected_item["name"]);
			$(".scenarioNew").hide();
			$(".scenarioEdit").hide();
			$(".instanceEdit").show();
			
			$("#containerLogicalDrawing").load("scenario_id.php?uuid="+selected_item["uuid"]+"&type=instance");
			console.log("instance-scenario loading");
		});
		
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
	
	};
	
	function generateCommandAction(action){
		var yamlObj = action;
		var selected_array =  $('#instance_items').jstree('get_selected');
		//delete a item if parent item is already selected. Not so easy as it looks at first sight, beleave me
		var items_to_delete=[]
		for (var item=0; item<selected_array.length; item++){
			var item_object = $('#instance_items').jstree('get_node', selected_array[item] );
			for (var i in selected_array){
				if (item_object.parent == selected_array[i]){
					items_to_delete.push(item);
					break;
				}
			}
		}
		for (var i in items_to_delete) delete selected_array[items_to_delete[i] ];
		var temp;
		var vnfs_array=[];
		var vms_array=[];
		var scenario=false;
		for (var i in selected_array){
			if (selected_array[i]==undefined)
				continue;
			temp = selected_array[i].split(".");
			if (temp[0]=="vnf")
				vnfs_array.push(temp[1]);
			else if (temp[0]=="vm")
				vms_array.push(temp[1]);
			else if (temp[0]=="scenario")
				scenario = true;
		}
		if (scenario==false && vnfs_array.length==0 && vnfs_array.length==0)
			return "Error: select at least one item";
		if (vnfs_array.length > 0)
			yamlObj["vnfs"] = vnfs_array;
		if (vms_array.length > 0)
			yamlObj["vms"] = vms_array;
		vms_array=[];
		var doc = jsyaml.dump(yamlObj);
		console.log(doc);
		return doc;
	};
	
	function instance_action(action){
		var yamlCmd = generateCommandAction(action);
		if (yamlCmd.indexOf("Error")==0){
			alert(yamlCmd);
			return;
		}
		$.ajaxSetup({headers:{'Accept':'application/yaml','Content-Type':'application/yaml'}});  //ALF
		var jqxhr=$.post(mano_url_base + mano_tenant +"/instances/" + selected_item.uuid + "/action",
			yamlCmd,
			function(data,status){
				alert("Result: " + status + "\nData: " + data);
			}
		);
		jqxhr.fail(function(data,status) {
			alert("Result: " + status + "\nData: " + data.responseText);
		});
	}
	
	function delete_scenario_instance(what){
		var name = confirm("Delete " + what + " '" + selected_item.name + "' ?");
		if (name == true) {
		
			$.ajaxSetup({headers:{'Accept':'application/yaml','Content-Type':'application/yaml'}});  //ALF
			var jqxhr = $.ajax({
				url: mano_url_base + mano_tenant +"/"+what+"s/" + selected_item.uuid,
				type: 'DELETE',
				success: function(data,status) {
					alert("Status: " + status +"\nData: " + data + "\n");
					location.reload();
					//textDiv = create_text_box(textDiv, "textDiv", "Status: " + status +"\nData: " + data + "\n");
					//$('#containerLogicalDrawing').append(textDiv);
				}
			});
			jqxhr.fail(function(data,status) {
				alert("Status: " + status +"\nData: " + data.responseText + "\n");
			});
		}
	};
	
	$("#startButton").click(function(e){
		instance_action( {"start": null} );
	})
	$("#stopButton").click(function(e){
		instance_action( {"shutdown": null} );
	})
	$("#forceOffButton").click(function(e){
		instance_action( {"forceOff": null} );
	})
	$("#rebootButton").click(function(e){
		instance_action( {"reboot": { "type": null} } );
	})
	$("#rebuildButton").click(function(e){
		instance_action( {"rebuild": null} );
	})
	$("#pauseButton").click(function(e){
		instance_action( {"pause": null } );
	})
	$("#updateButton").click(function(e){ 
		$.ajaxSetup({headers:{'Accept':'application/yaml','Content-Type':'application/yaml'}});  //ALF
		var jqxhr=$.get(mano_url_base + mano_tenant +"/instances/" + selected_item.uuid,
			function(data,status){
				//alert("Result: " + status + "\nData: " + data);
				$("#containerLogicalDrawing").load("scenario_id.php?uuid="+selected_item["uuid"]+"&type=instance");
				console.log("instance-scenario loading");
			}
		);
		jqxhr.fail(function(data,status) {
			alert("Result: " + status + "\nData: " + data.responseText);
		});
	}); 

	/* generate a Yaml string from the nodes and connections in logical view */
	function generateEditScenarioCommand(name, description){
		var yamlTopologyObj={"nodes":{}};   
		var numNodes=0;
		for(var v in instances_vnfs){
			//if (instances_vnfs[v]["changed"]==false)
			//	continue;
			
			numNodes += 1;
			yamlTopologyObj["nodes"][v]={};
			yamlTopologyObj["nodes"][v]['graph']={};
	        yamlTopologyObj["nodes"][v]['graph']["x"]=parseInt(instances_vnfs[v].css('left').split("px")[0],10); 
	        yamlTopologyObj["nodes"][v]['graph']["y"]=parseInt(instances_vnfs[v].css('top').split("px")[0],10); 
			yamlTopologyObj["nodes"][v]['graph']["ifaces"]={};
			if (instances_vnfs[v]["left_ifaces"].length > 0){
				//yamlTopologyObj["nodes"][v]['graph']["ifaces"]["left"]=[];
				yamlTopologyObj["nodes"][v]['graph']["ifaces"]["left"] = [].concat( instances_vnfs[v]["left_ifaces"] );
			}
			if (instances_vnfs[v]["right_ifaces"].length > 0){
				//yamlTopologyObj["nodes"][v]['graph']["ifaces"]["right"]=[];
				yamlTopologyObj["nodes"][v]['graph']["ifaces"]["right"] = [].concat( instances_vnfs[v]["right_ifaces"] );
			}
			if (instances_vnfs[v]["bottom_ifaces"].length > 0){
				//yamlTopologyObj["nodes"][v]['graph']["ifaces"]["bottom"]=[];
				yamlTopologyObj["nodes"][v]['graph']["ifaces"]["bottom"] = [].concat( instances_vnfs[v]["bottom_ifaces"] );
			}
			yamlTopologyObj["nodes"][v]["name"] = instances_vnfs[v]["name"];
	
		}
		var yamlObj = {"name":name};
		if (numNodes > 0){
			yamlObj["topology"]=yamlTopologyObj;
		}
		if (description != null && description != ""){
			yamlObj["description"]=description;
		}
		var doc = jsyaml.dump(yamlObj);
		console.log(doc);
		return doc;
	}

	$("#editButton").click(function(e){ 
		var result = confirm("Save changes of scenario '" + selected_item.name + "' ?");
		if (result == true) {
			var name =        $("#scenario_name").text();
			var description = $("#scenario_description").text();
			//var name = prompt("Provide a name for the scenario");
			if (name==null || name==""){
				alert("Provide a name at Scenario Name text box");
				return;
			}
			var yamlData = generateEditScenarioCommand(name, description);
			if (yamlData.indexOf("Error")==0){
				alert(yamlData);
				return;
			}
		
			$.ajaxSetup({headers:{'Accept':'application/yaml','Content-Type':'application/yaml'}});  //ALF
			var jqxhr = $.ajax({
				url: mano_url_base + mano_tenant +"/scenarios/" + selected_item.uuid,
				type: 'PUT',
				data: yamlData,
				success: function(data,status) {
					alert("Status: " + status +"\nData: " + data + "\n");
					//location.reload();
				}
			});
			jqxhr.fail(function(data,status) {
				alert("Result: " + status + "\nData: " + data.responseText);
			});
		}
	});
	
	$("#cloneButton").click(function(e){ 
		location.assign("scenario_new.php?uuid="+selected_item['uuid']);
	});
	$("#textButton").click(function(e){
		var name =        $("#scenario_name").text();
		var description = $("#scenario_description").text();
		var yamlData = generateNewScenarioCommand(name, description, false);
		/*
		var textDiv = $('<div class="text_div" id=text"' + selected_item['uuid'] + '">');
		textDiv.css({'top': 1,'left': 1});
		var texArea = $('<textarea  rows="40" cols="60">');  
		texArea.css({'top': 5,'left': 5});
		texArea.text(yamlData);
		var closeTextButton = $('<button type="button" class="text_div" id="closeTextButton">Close</button>');
		closeTextButton.css({'top': 5,'right': 5});
		
		textDiv.append(texArea);
		textDiv.append(closeTextButton);
		closeTextButton.click(function(){textDiv.remove(); delete textDiv; });
		$('#containerLogicalDrawing').append(textDiv); 
		*/
		textDiv = create_text_box(textDiv, "text" + selected_item['uuid'], yamlData);
		$('#containerLogicalDrawing').append(textDiv);

	});
	
	$("#newButton").click(function(e){ 
		location.assign("scenario_new.php");
	});
	
	$("#delInstanceButton").click(function(e){ 
		delete_scenario_instance("instance");
	}); 
	
	/* Top panel handlers */
	$("#deleteButton").click(function(e){ 
		delete_scenario_instance("scenario");
	}); 
/*	$("#downloadButton").click(function(e){ 
		$("#deleteButton").copy();
	});*/ 
	
	function start_reserve_scenario(start_reserve){
		var prompt_;
		if (start_reserve=="start")
			prompt_ = "Deploying scenario '";
		else
			prompt_ = "Deploying scenario without startinfg VMs '";
                var name = prompt(prompt_ + selected_item.name + "'. Insert an instance name?", selected_item.name);
                if (name != null) {

                        $.ajaxSetup({headers:{'Accept':'application/yaml','Content-Type':'application/yaml'}});  //ALF
                        var jqxhr=$.post(mano_url_base + mano_tenant +"/scenarios/" + selected_item.uuid + "/action",
                                start_reserve + ": \n  instance_name: " + name + "\n",
                                function(data,status){
                                        alert("Result: " + status + "\nData: " + data);
                                        location.reload();
                                }
                        );
                        jqxhr.fail(function(data,status) {
                                alert("Result: " + status + "\nData: " + data.responseText);
                        });

                }

	};

	$("#deployButton").click(function(e){ 
		start_reserve_scenario("start");
	});
	$("#reserveButton").click(function(e){ 
		start_reserve_scenario("reserve");
	});
	

</script>


</body>
</html>
