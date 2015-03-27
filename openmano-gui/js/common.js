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
 * Common initialitation for sevaral pages.
 */
$(document).ready(function(){
	$("#menu_scenario").click(function(){	location.assign("scenario.php");	});
	$("#menu_vnf").click(function(){		location.assign("vnfs.php");			});
	$("#menu_physical").click(function(){	location.assign("physical.php");		});

	$(".minus").click(function(){
		//console.log("click on minus " + this.id);
		var div_id = this.id;
		div_id = div_id.slice(0, div_id.length-1);
		$("#" + div_id ).toggle();
		if (this.src.match("minus_icon.gif") ) 
	    	this.src = "images/plus_icon.gif";
	    else
	    	this.src = "images/minus_icon.gif";	
	});

});


