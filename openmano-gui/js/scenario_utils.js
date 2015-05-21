/**
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
    Version: 0.50
    Date: Feb 2015
*/

	/**
	 * Redraw the interfaces. Needed when the position of an interface has changed
	 */
	function redefineIfaces(jsPlumbObj){
		var numifaces=jsPlumbObj["left_ifaces"].length , offset=1/(numifaces*2);
		for ( var i = 1; i <= numifaces; i++ ) {
			for (var iface_nb in jsPlumbObj.ifaces){
				if (jsPlumbObj.ifaces[iface_nb].name == jsPlumbObj["left_ifaces"][i-1][0]){
					jsPlumbObj.ifaces[iface_nb].setAnchor([-0.1,i/numifaces-offset,-1,0]);
					jsPlumbObj.ifaces[iface_nb].side = "left";
					jsPlumbObj.ifaces[iface_nb].pos = i;
					break;
				}
			}
		}
		var numifaces=jsPlumbObj["right_ifaces"].length , offset=1/(numifaces*2);
		for ( var i = 1; i <= numifaces; i++ ) {
			for (var iface_nb in jsPlumbObj.ifaces){
				if (jsPlumbObj.ifaces[iface_nb].name == jsPlumbObj["right_ifaces"][i-1][0]){
					jsPlumbObj.ifaces[iface_nb].setAnchor([1,i/numifaces-offset,1,0]);
					jsPlumbObj.ifaces[iface_nb].side = "right";
					jsPlumbObj.ifaces[iface_nb].pos = i;
					break;
				}
			}
		}
		var numifaces=jsPlumbObj["bottom_ifaces"].length , offset=1/(numifaces*2);
		for ( var i = 1; i <= numifaces; i++ ) {
			for (var iface_nb in jsPlumbObj.ifaces){
				if (jsPlumbObj.ifaces[iface_nb].name == jsPlumbObj["bottom_ifaces"][i-1][0]){
					jsPlumbObj.ifaces[iface_nb].setAnchor([i/numifaces-offset,1,0,1]);
					jsPlumbObj.ifaces[iface_nb].side = "bottom";
					jsPlumbObj.ifaces[iface_nb].pos = i;
					break;
				}
			}
		}
		//jsPlumb.repaint(jsPlumbObj.);
		//jsPlumb.repaintEverything();
		//console.log("repintandolo todo\n");
	};
	/**
	 * Paint interfaces of vnf
	 * @param nfvobj  vnf object
	 * @param dicIfaces interfaces possition
	 * @param edit if allow drawing connections in this interfaces 
	 * @returns
	 */
	function addifaces( nfvobj, dicIfaces, edit){
		var anchorsArray = null;
		var maxConn = ((nfvobj["type"] == "VNF") ? 1 : 20); 
		var ifaces = {};
		nfvobj["bottom_ifaces"] = []; 
		nfvobj["left_ifaces"]   = [];
		nfvobj["right_ifaces"]  = [];

		for (var side in dicIfaces){ 
			var arrIfaces = dicIfaces[side];
			var numifaces = arrIfaces.length, offset = 1/(numifaces*2);
			for ( var i = 1; i <= numifaces; i++ ) {
				switch(side){
				case "bottom":
					nfvobj["bottom_ifaces"][i-1] = arrIfaces[i-1];
					anchorsArray= [i/numifaces-offset,1,0,1];
					break;
				case "left":
					nfvobj["left_ifaces"][i-1] = arrIfaces[i-1];
					anchorsArray= [-0.1,i/numifaces-offset,-1,0];
					break;
				case "right":
					nfvobj["right_ifaces"][i-1] = arrIfaces[i-1];
					anchorsArray= [1,i/numifaces-offset,1,0];
					break;
				default:
					console.log("Error: bad interfaces format for nvf definition");
					exit();
				}
				var eth=jsPlumb.addEndpoint(
					nfvobj,
					{anchor: anchorsArray},
					{overlays:[[ "Label", {cssClass:"ifacelbl",label:arrIfaces[i-1][0], id:"lbl"}]],  
							connectorStyle:connectorPaintStyle,
							connectorHoverStyle:connectorHoverStyle, 
							maxConnections:maxConn,
							isTarget: edit, 
							isSource: edit, 
							endpoint:["Image", {src:'images/ifaces/Eth-'+arrIfaces[i-1][1]+'.png', width:16,height:16}]
					}
				);
				eth.name = arrIfaces[i-1][0];
				eth.side = side;
				eth.pos  = i;
				eth.vnf = nfvobj;
				eth.bind("mouseenter", function(ep) {ep.showOverlay("lbl");  });
				eth.bind("mouseexit", function(ep) {ep.hideOverlay("lbl"); }); 
				//eth.bind("click", function(ep) {/* console.log("click en la interfaz :"+ep.name);*/  });
				eth.bind("contextmenu", function(ep, event_) {
					//var event_x= event_.screenX;
					//var event_y= event_.screenY;
					var vnfy=ep.endpoint.y - 30;
					var vnfx=ep.endpoint.x - 40;
					jsPlumbSelectedEndPoint = ep,
					console.log("click iterface "+ep.name, vnfx, vnfy);
					var newIfacePosition = $('<div>');
					newIfacePosition.attr('id','Iface_Position').addClass('text_div');
					newIfacePosition.append(
						$('<img style="position:relative;display:inline" src="images/ifaces/IfacePosition.png" ></img>')
						//$('<img style="position:relative;margin-left: auto;margin-right: auto;margin-bottom:auto;margin-top:auto;display:inline" src="images/ifaces/IfacePosition.png" ></img>')
					);
					newIfacePosition.css({'top': vnfy,'left': vnfx});
					newIfacePosition.click(function(e){
						//console.log(e.screenX - event_x+40, e.screenY-event_y+30);
						var x = e.offsetX; //e.pageX - e.target.x;
						var y = e.offsetY; //e.pageY - e.target.y;
						if (x==undefined){ //firefox
							x=e.originalEvent.layerX; 
							y=e.originalEvent.layerY;
						}
						var vnfSelected = jsPlumbSelectedEndPoint.vnf;
						var iface = vnfSelected[jsPlumbSelectedEndPoint.side + "_ifaces"][jsPlumbSelectedEndPoint.pos-1];
						//console.log(x +","+y+"    "+e.pageX+","+e.pageY);
						console.log("removing iface", jsPlumbSelectedEndPoint.side, jsPlumbSelectedEndPoint.pos);
						vnfSelected[jsPlumbSelectedEndPoint.side + "_ifaces"].splice(jsPlumbSelectedEndPoint.pos-1,1);
						if (x<28 && y<28){         vnfSelected["left_ifaces"].splice(0,0,iface); console.log("left top");} 
						else if (x<28 && y>28 && y<65){ vnfSelected["left_ifaces"].push(iface); console.log("left bottom");} 
						else if (x>72 && y<28){         vnfSelected["right_ifaces"].splice(0,0,iface); console.log("right top");} 
						else if (x>72 && y>28 && y<65){ vnfSelected["right_ifaces"].push(iface); console.log("right bottom");} 
						else if (x<50 && y>65){         vnfSelected["bottom_ifaces"].splice(0,0,iface); console.log("bottom left");} 
						else if (x>50 && y>65){         vnfSelected["bottom_ifaces"].push(iface); console.log("bottom right");}
						else{ vnfSelected[jsPlumbSelectedEndPoint.side + "_ifaces"].splice(jsPlumbSelectedEndPoint.pos-1,0,iface); }
						redefineIfaces(vnfSelected);
						$(this).remove();
						//$.when($(this).remove()).then( jsPlumb.repaintEverything() );
						//jsPlumb.repaintEverything();
						//jsPlumb.repaint
						//console.log("repintandolo todo 3\n");
						setTimeout(function(){jsPlumb.repaintEverything();}, 200);
						//TODO: make a selective repaint
					});
				    newIfacePosition.mouseleave(function(){$(this).remove();});
				    				    
				    
				    $('#containerLogicalDrawing').append(newIfacePosition);
										
					//newIfacePosition.remove()
				});
				ifaces[eth.name] = eth;
			}
			nfvobj.ifaces=ifaces;       
		};
		return nfvobj;
	};

/**
 * Creates a VNF at the logial view
 * @param uuid identified to be used
 * @param vnf_id id of the vnf model 
 * @param vnf_name name
 * @param vnfx horizontal position
 * @param vnfy vertical position
 * @param ifaces object with the ifaces to be created
 * @param edit if the ifaces admit or not connections. Also if allow a contex menu for allowing deletion
 * @returns {___new_instance_vnf1}
 */	
	function createVNFProgrammatically(uuid, vnf_id, vnf_name, vnfx, vnfy, ifaces, edit){ 
		var new_instance_vnf = $('<div title="' + vnfsDefs[vnf_id]["model"] + '">');
		console.log("vnfsDefs[vnf_id="+ vnf_id+"]=" + vnfsDefs[vnf_id]);
		new_instance_vnf["type"]=vnfsDefs[vnf_id]["type"];
		new_instance_vnf["selected"]=0;
		new_instance_vnf["model"]=vnfsDefs[vnf_id]["model"];  
		new_instance_vnf["name"]=  vnf_name; 
		new_instance_vnf["vnf_id"]=vnf_id; 
		new_instance_vnf["changed"] = false;
		new_instance_vnf.attr('id',uuid).addClass('item');
		var icon=$('<img class="vnfimg" style="position:relative;margin-left: auto;margin-right: auto;margin-bottom:auto;margin-top:auto;display:inline" src="'
				//	+vnfsDefs[vnf_id]['img']+'" ></img>').attr('id',uuid+'_');
					+'images/big/vnf_default.png" ></img>').attr('id',uuid+'_');
			    
		new_instance_vnf.append(icon);
		var title = $('<div>').addClass('title').text(vnf_name);
		if (new_instance_vnf["type"]!="external_network"){
			title.dblclick(function(){
				var new_name=prompt("Please enter a new name", $(this).text());
				if (new_name!=null && new_name!=""){
					title.html(new_name);
					new_instance_vnf["name"]=new_name;
					new_instance_vnf["changed"]=true;
				}
			});
		}
		new_instance_vnf.prepend(title);
		
		new_instance_vnf.css({'top': vnfy,'left': vnfx});
		jsPlumb.draggable(new_instance_vnf, {
			containment: 'parent'
		});
		$('#containerLogicalDrawing').append(new_instance_vnf);
		addifaces(new_instance_vnf, ifaces, edit);
		//console.log(icon);
		icon[0].src=vnfsDefs[vnf_id]['img'];
		if (edit){
			new_instance_vnf.contextPopup({
				//title: 'My Popup Menu',
			 	button: "right", 
			 	items: [ 
					//{label:'Configuration', action:function(){ alert('Configuration should go here!'); } },
					{label:'Rename',action:function(){
						var name=prompt("Please enter a new name");
						if (name!=null && name!=""){
							//var el=$(document.getElementById(active_vnf).getElementsByClassName("title")[0]).html(name);
							instances_vnfs[active_vnf]["name"]=name;
							console.log(instances_vnfs);
						} 
					}},
					{label:'Remove',action: function(e){
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
						// desconectar las conexiones y borrar el objeto
						jsPlumb.detachAllConnections($(instances_vnfs[v]));
						$(instances_vnfs[v]).remove();
						delete instances_vnfs[v] ;//e.stopPropagation(); 
					}},
					//{label:"10.95.164.179", action:function(e){
					//	jsPlumb.repaintEverything();
					//}}
				]
			});  		
		}
		instances_vnfs[uuid]=new_instance_vnf;
		//console.log(instances_vnfs, Object.keys(instances_vnfs).length);
		return new_instance_vnf;
	}

	
	
	/**
	 * Draws a scenario at the logical view pannel
	 * @param scenario scenario object to be loaded
	 * @param edit 
	 *    true when the scenario can be completely edited: connections, deletions, insertions
	 *    false when the scenario can be partially edited: only the position and names, but not deletion neither moving connectios. 
	 */

	function load_scenario(scenario, edit){
		//crear los nodos
	    var nodos = scenario["topology"]["nodes"];
	    var connections = scenario["topology"]["connections"];
	    for (var v in instances_vnfs){
	    	instances_vnfs[v].remove();
	    }
	    instances_vnfs={};
	    for(var n in nodos){
	        var vnf_id = null;
	        if (nodos[n]["type"]=="external_network"){
				//find uuid of external network
				for (var id in vnfsDefs){
					if (vnfDefs[id]["model"]==nodos[n]["name"]){
						vnf_id=id;
						break;
					}
				}
	        }else if (nodos[n]["type"]=="dada_network"){
	            vnf_id = "dataplane_net";
	        }else if (nodos[n]["type"]=="bridge_network"){
	            vnf_id = "brige_net";
	        }else{ //if (nodos[n]["type"]=="VNF"){
	            vnf_id = nodos[n]["vnf_id"];
			}
	        var ifaces = vnfsDefs[vnf_id]["ifaces"];
	        if ('ifaces' in nodos[n]){
	        	ifaces = nodos[n]['ifaces'];
	        }
			//console.log(nodos[n]);
			console.log("carga de nodo " + n + " name=" + nodos[n]['name'] + " vnf_id=" + vnf_id + " type=" + nodos[n]['type']);
			createVNFProgrammatically(n, vnf_id, nodos[n]['name'], nodos[n]['x'], nodos[n]['y'], ifaces, edit);
	    } 
	    // crear las conexiones
	    for(var c in connections)
	    {
	        var net_id = null;
			if (connections[c]['type'] != 'link'){
				if (connections[c]['type']=='bridge_network'){
					net_id='bridge_net';
				}else if (connections[c]['type']=='data_network'){
					net_id='dataplane_net';
				}else{
					//external_network look for network id
					for(var i in vnfsDefs){
						if (vnfsDefs[i].type == 'external_network' && vnfsDefs[i].model==connections[c]["name"]){
							net_id = i;
							break;
						}
					}
				}
		        var ifaces = vnfsDefs[net_id]["ifaces"];
		        if ('ifaces' in connections[c]){
		        	ifaces = connections[c]['ifaces'];
		        } 
				console.log("carga de nodo net " + c + " net_id=" + net_id +" name=" + connections[c]["name"]);
				var newVnf = createVNFProgrammatically(c, net_id, connections[c]["name"], connections[c]['x'], connections[c]['y'], ifaces, edit);
		        for(var n2 in connections[c]["nodes"]){
	               	dst = instances_vnfs[ connections[c]["nodes"][n2][0] ].ifaces[ connections[c]["nodes"][n2][1] ];
		        	console.log("net connecting", c, newVnf.ifaces[0], dst);
			    	jsPlumb.connect({source:newVnf.ifaces['0'], target: dst, detachable: edit});
		        }
		    }else{
		        var src=null, dst,cnt=0, found_=false;
		        for(var n2 in connections[c]["nodes"]){
		        	//console.log(n2,  connections[c]["nodes"][n2]);
					//console.log("alf> ", instances_vnfs[n2].ifaces[i].name, connections[c]["nodes"][n2]);
					if(cnt==0){
						src = instances_vnfs[ connections[c]["nodes"][n2][0] ].ifaces[ connections[c]["nodes"][n2][1] ];
						cnt++;
					}else{
						dst = instances_vnfs[ connections[c]["nodes"][n2][0] ].ifaces[ connections[c]["nodes"][n2][1] ];
						console.log("connection ", c, src, dst);
						jsPlumb.connect({source:src, target: dst, detachable: edit});
						found_= true;
					}
		        }
		        if (!found_){
			        console.log("skipping", connections[c]["nodes"][n2][0],  connections[c]["nodes"][n2][1]);
				}
	        }
		}
	};
	
	
	 
	/** generate the payload to be sent at openmano to insert a scenario
	 *  it composes a Yaml string from the nodes and connections drawn in the logical view
	 */
	function generateNewScenarioCommand(name, description, include_uuid){
		var cnxList = jsPlumb.getConnections();
		var yamlTopologyObj={"nodes":{},"connections":{}};   
		if (include_uuid == undefined )
			include_uuid=true;
		//var date= new Date();
		//generatedTopos++;
		//var topoId = (date.getFullYear().toString())+("0" + date.getDate().toString()).substr(-2)+("0" + (date.getMonth()+ 1).toString()).substr(-2)+"_"+("000"+generatedTopos.toString()).substr(-4);
		var numNodes=0;
		// console.log("\n number of connections "+cnxList.length); 
		/* fill nodes */
		for(var v in instances_vnfs){
			numNodes += 1;
			var nodename=instances_vnfs[v]["name"];
			if (nodename in yamlTopologyObj["nodes"]){
				return "Error: VNF Repeated '"+ nodename + "' used by several VNFs. Change name of one VNF";
			}
			yamlTopologyObj["nodes"][nodename]={};
			yamlTopologyObj["nodes"][nodename]['graph']={};
			yamlTopologyObj["nodes"][nodename]['graph']["x"]=parseInt(instances_vnfs[v].css('left').split("px")[0],10); 
			yamlTopologyObj["nodes"][nodename]['graph']["y"]=parseInt(instances_vnfs[v].css('top').split("px")[0],10); 
			yamlTopologyObj["nodes"][nodename]['graph']["ifaces"]={};
			if (instances_vnfs[v]["left_ifaces"].length > 0){
				yamlTopologyObj["nodes"][nodename]['graph']["ifaces"]["left"] = [].concat( instances_vnfs[v]["left_ifaces"] );
			}
			if (instances_vnfs[v]["right_ifaces"].length > 0){
				yamlTopologyObj["nodes"][nodename]['graph']["ifaces"]["right"] = [].concat( instances_vnfs[v]["right_ifaces"] );
			}
			if (instances_vnfs[v]["bottom_ifaces"].length > 0){
				yamlTopologyObj["nodes"][nodename]['graph']["ifaces"]["bottom"] = [].concat( instances_vnfs[v]["bottom_ifaces"] );
			}
			yamlTopologyObj["nodes"][nodename]["type"] = instances_vnfs[v].type;
			if (instances_vnfs[v].type=="VNF"){
				if (include_uuid)
					yamlTopologyObj["nodes"][nodename]["vnf_id"] = instances_vnfs[v].vnf_id;
				yamlTopologyObj["nodes"][nodename]["VNF model"] = instances_vnfs[v].model;
			}else{
				if (include_uuid)
					yamlTopologyObj["nodes"][nodename]["net_id"] = instances_vnfs[v].vnf_id;
				yamlTopologyObj["nodes"][nodename]["model"] = instances_vnfs[v].model;
			}
	
		}
		if (numNodes == 0){
			return "Error: There is nothing to be saved. Drag VNFs from the left to the drawing area";
		}
		/* fill connections */
		for (var i =0; i <cnxList.length;i++){
			// console.log("\n connection "+i);
			yamlTopologyObj["connections"]["connection "+i] = {"type":"link","nodes": [] };
			yamlTopologyObj["connections"]["connection "+i]["nodes"][0] = {};
			yamlTopologyObj["connections"]["connection "+i]["nodes"][0][ instances_vnfs[ cnxList[i].endpoints[0].elementId ].name ] = cnxList[i].endpoints[0].name;
			yamlTopologyObj["connections"]["connection "+i]["nodes"][1] = {};
			yamlTopologyObj["connections"]["connection "+i]["nodes"][1][ instances_vnfs[ cnxList[i].endpoints[1].elementId ].name ] = cnxList[i].endpoints[1].name;
		} 
		var yamlObj = {"name":name,"topology":yamlTopologyObj};
		if (description != null && description != ""){
			yamlObj["description"]=description;
		}
		var doc = jsyaml.dump(yamlObj);
		console.log(doc);
		return doc;
	}
	
	function create_text_box(oldTextDiv, id, text){
		if (oldTextDiv != null){
			oldTextDiv.remove();
		}
		var textDiv = $('<div class="text_div" id="' + id + '">');
		textDiv.css({'top': 1,'left': 1});
		var texArea = $('<textarea id="textArea" rows="40" cols="60">');  
		texArea.css({'top': 5,'left': 5});
		texArea.text(text);
		var closeTextButton = $('<button type="button" class="text_div" id="closeTextButton">Close</button>');
		closeTextButton.css({'top': 5,'right': 5});
		//console.log(closeTextButton);
		var selectTextButton = $('<button type="button" class="text_div" id="selectTextButton">Select All</button>');
		selectTextButton.css({'top': 5,'right': 50 + 5}); //closeTextButton[0].clientWidth
		
		textDiv.append(texArea);
		textDiv.append(closeTextButton);
		textDiv.append(selectTextButton);
		closeTextButton.click(function(){textDiv.remove(); delete textDiv; });
		selectTextButton.click(function(){$("#textArea").select(); });
		return textDiv;
	}

