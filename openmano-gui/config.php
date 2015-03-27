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

# modify the variables, do not forget the quotes and the semicolom at the end
function getConfig(){
	global $db_server, $db_user, $db_passwd, $db_name;
	global $db_vim_server, $db_vim_user, $db_vim_passwd, $db_vim_name;
	global $mano_http, $mano_tenant;
	
	#openmano database server name or ip address
	$db_server = 'localhost';
	
	#openmano database user, password and name
	$db_user = 'mano';
	$db_passwd = 'manopw';
	$db_name ='mano_db';
	
	#openmano server URL
	$mano_http='http://localhost:9090/openmano';
	
	#openmano server tenant. 
	#TODO change this to be a choose option in the web
	$mano_tenant='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';

	#openvim database server name or ip address
	$db_vim_server = 'localhost';

	#openvim database user, password and name
	$db_vim_user = 'vim';
	$db_vim_passwd = 'vimpw';
	$db_vim_name ='vim_db';
	
 }


?>


