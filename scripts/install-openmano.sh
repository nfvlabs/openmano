#!/bin/bash

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

#ONLY TESTED for Ubuntu 14.10 14.04, CentOS7 and RHEL7
#Get needed packets, source code and configure to run openvim, openmano and floodlight
#Ask for database user and password if not provided
#        $1: database user
#        $2: database password 

function usage(){
    echo  -e "usage: sudo $0 [db-user [db-passwd]]\n  Install source code in ./openmano"
}

function install_packets(){
    [ -x /usr/bin/apt-get ] && apt-get install -y $*
    [ -x /usr/bin/yum ]     && yum install -y $*   
    
    #check properly installed
    for PACKET in $*
    do
        PACKET_INSTALLED="no"
        [ -x /usr/bin/apt-get ] && dpkg -l $PACKET            &>> /dev/null && PACKET_INSTALLED="yes"
        [ -x /usr/bin/yum ]     && yum list installed $PACKET &>> /dev/null && PACKET_INSTALLED="yes" 
        if [ "$PACKET_INSTALLED" = "no" ]
        then
            echo "failed to install packet '$PACKET'. Revise network connectivity and try again"
            exit -1
       fi
    done
}

#check root privileges and non a root user behind
[ "$1" == "-h" -o "$1" == "--help" ] && usage && exit 0
[ "$USER" != "root" ] && echo "Needed root privileges" >&2 && usage >&2 && exit -1
[ -z "$SUDO_USER" -o "$SUDO_USER" = "root" ] && echo "Must be runned with sudo from a non root user"  >&2 && usage >&2 && exit -1


#Discover Linux distribution
#try redhat type
[ -f /etc/redhat-release ] && _DISTRO=$(cat /etc/redhat-release 2>/dev/null | cut  -d" " -f1) 
#if not assuming ubuntu type
[ -f /etc/redhat-release ] || _DISTRO=$(lsb_release -is  2>/dev/null)            
if [ "$_DISTRO" == "Ubuntu" ]
then
    _RELEASE="14"
    if ! lsb_release -rs | grep -q "14."
    then 
        read -e -p "WARNING! Not tested Ubuntu version. Continue assuming a '$_RELEASE' type? (y/N)" KK
        [ "$KK" != "y" -a  "$KK" != "yes" ] && echo "Cancelled" && exit 0
    fi
elif [ "$_DISTRO" == "CentOS" ]
then
    _RELEASE="7" 
    if ! cat /etc/redhat-release | grep -q "7."
    then
        read -e -p "WARNING! Not tested CentOS version. Continue assuming a '_RELEASE' type? (y/N)" KK
        [ "$KK" != "y" -a  "$KK" != "yes" ] && echo "Cancelled" && exit 0
    fi
elif [ "$_DISTRO" == "Red" ]
then
    _RELEASE="7" 
    if ! cat /etc/redhat-release | grep -q "7."
    then
        read -e -p "WARNING! Not tested Red Hat OS version. Continue assuming a '_RELEASE' type? (y/N)" KK
        [ "$KK" != "y" -a  "$KK" != "yes" ] && echo "Cancelled" && exit 0
    fi
else  #[ "$_DISTRO" != "Ubuntu" -a "$_DISTRO" != "CentOS" -a "$_DISTRO" != "Red" ] 
    _DISTRO_DISCOVER=$_DISTRO
    [ -x /usr/bin/apt-get ] && _DISTRO="Ubuntu" && _RELEASE="14"
    [ -x /usr/bin/yum ]     && _DISTRO="CentOS" && _RELEASE="7"
    read -e -p "WARNING! Not tested Linux distribution '$_DISTRO_DISCOVER '. Continue assuming a '$_DISTRO $_RELEASE' type? (y/N)" KK
    [ "$KK" != "y" -a  "$KK" != "yes" ] && echo "Cancelled" && exit 0
fi



echo '
#################################################################
#####        UPDATE REPOSITORIES                            #####
#################################################################'
[ "$_DISTRO" == "Ubuntu" ] && apt-get update -y

[ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && yum check-update -y
[ "$_DISTRO" == "CentOS" ] && sudo yum install -y epel-release
[ "$_DISTRO" == "Red" ] && wget http://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm \
  && sudo rpm -ivh epel-release-7-5.noarch.rpm && sudo yum install -y epel-release && rm -f epel-release-7-5.noarch.rpm
[ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && sudo yum repolist


echo '
#################################################################
#####        INSTALL LAMP   PACKETS                         #####
#################################################################'
[ "$_DISTRO" == "Ubuntu" ] && install_packets "apache2 mysql-server           php5 php-pear php5-mysql" #TODO revise if php-pear is needed
[ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && install_packets "httpd   mariadb mariadb-server php           php-mysql"

if [ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ]
then
    #start sercices. By default CentOS does not start services
    service mariadb start
    service httpd   start
    systemctl enable mariadb
    systemctl enable httpd
    read -e -p "Do you want to configure mariadb (recomended if not done before) (Y/n)" KK
    [ "$KK" != "n" -a  "$KK" != "no" ] && mysql_secure_installation

    read -e -p "Do you want to set firewall to grant web access port 80,443  (Y/n)" KK
    [ "$KK" != "n" -a  "$KK" != "no" ] && 
        firewall-cmd --permanent --zone=public --add-service=http &&
        firewall-cmd --permanent --zone=public --add-service=https &&
        firewall-cmd --reload
fi

#check and ask for database user password. Must be done after database instalation
[ -n "$1" ] && DBUSER=$1
[ -z "$1" ] && DBUSER=root
[ -n "$2" ] && DBPASSWD="-p$2"
[ -z "$2" ] && DBPASSWD=""
echo -e "\nCheking database connection and ask for credentials"
while !  echo "" | mysql -u$DBUSER $DBPASSWD
do
        [ -n "$logintry" ] &&  echo -e "\nInvalid database credentials!!!. Try again (Ctrl+c to abort)"
        [ -z "$logintry" ] &&  echo -e "\nProvide database credentials"
        read -e -p "database user? ($DBUSER) " DBUSER_
        [ -n "$DBUSER_" ] && DBUSER=$DBUSER_
        read -e -s -p "database password? (Enter for not using password) " DBPASSWD_
        [ -n "$DBPASSWD_" ] && DBPASSWD="-p$DBPASSWD_"
        [ -z "$DBPASSWD_" ] && DBPASSWD=""
        logintry="yes"
done

echo '
#################################################################
#####        INSTALL PYTHON PACKETS                         #####
#################################################################'
[ "$_DISTRO" == "Ubuntu" ] && install_packets "python-yaml python-libvirt python-bottle python-mysqldb python-jsonschema python-paramiko python-argcomplete python-requests git screen wget"
[ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && install_packets "PyYAML      libvirt-python               MySQL-python   python-jsonschema python-paramiko python-argcomplete python-requests git screen wget"

#The only way to install python-bottle on Centos7 is with easy_install or pip
[ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && easy_install -U bottle

#install openstack client needed for using openstack as a VIM
[ "$_DISTRO" == "Ubuntu" ] && install_packets "python-novaclient python-keystoneclient python-glanceclient python-neutronclient"
[ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && install_packets "python-devel" && easy_install python-novaclient python-keystoneclient python-glanceclient python-neutronclient #TODO revise if gcc python-pip is needed

echo '
#################################################################
#####        DOWNLOAD SOURCE                                #####
#################################################################'
su $SUDO_USER -c 'git clone https://github.com/nfvlabs/openmano.git openmano'
#su $SUDO_USER -c 'pushd openmano; git checkout -b v0.3 origin/v0.3; popd'
pushd openmano
su $SUDO_USER -c 'git checkout v0.3'
popd

echo '
#################################################################
#####        CREATE DATABASE                                #####
#################################################################'
mysqladmin -u$DBUSER $DBPASSWD create vim_db
mysqladmin -u$DBUSER $DBPASSWD create mano_db

echo "CREATE USER 'vim'@'localhost' identified by 'vimpw';"     | mysql -u$DBUSER $DBPASSWD
echo "GRANT ALL PRIVILEGES ON vim_db.* TO 'vim'@'localhost';"   | mysql -u$DBUSER $DBPASSWD
echo "CREATE USER 'mano'@'localhost' identified by 'manopw';"   | mysql -u$DBUSER $DBPASSWD
echo "GRANT ALL PRIVILEGES ON mano_db.* TO 'mano'@'localhost';" | mysql -u$DBUSER $DBPASSWD

echo "vim database"
su $SUDO_USER -c './openmano/openvim/database_utils/init_vim_db.sh -u vim -p vimpw'
echo "mano database"
su $SUDO_USER -c './openmano/openmano/database_utils/init_mano_db.sh -u mano -p manopw'


echo '
#################################################################
#####        DOWNLOADING AND CONFIGURE FLOODLIGHT           #####
#################################################################'
#FLoodLight
echo "Installing FloodLight requires Java, that takes a while to download"
read -e -p "Do you agree on download and install FloodLight from http://www.projectfloodlight.org upon the owner license? (y/N)" KK
if [ "$KK" == "y" -o   "$KK" == "yes" ]
then

    echo "downloading v0.90 from the oficial page"
    su $SUDO_USER -c 'wget https://github.com/floodlight/floodlight/archive/v0.90.tar.gz'
    su $SUDO_USER -c 'tar xvzf v0.90.tar.gz'
    #wget http://floodlight-download.projectfloodlight.org/files/floodlight-source-0.90.tar.gz'
    #su $SUDO_USER -c 'tar xvzf floodlight-source-0.90.tar.gz'
    
    #Install Java JDK and Ant packages at the VM 
    [ "$_DISTRO" == "Ubuntu" ] && install_packets "build-essential default-jdk ant python-dev" #TODO revise if packets are needed apart from ant
    [ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && install_packets "                            ant "

    #Configure Java environment variables. It is seem that is not needed!!!
    #export JAVA_HOME=/usr/lib/jvm/default-java" >> /home/${SUDO_USER}/.bashr
    #export PATH=$PATH:$JAVA_HOME
    #echo "export JAVA_HOME=/usr/lib/jvm/default-java" >> /home/${SUDO_USER}/.bashrc
    #echo "export PATH=$PATH:$JAVA_HOME" >> /home/${SUDO_USER}/.bashrc

    #Compile floodlight
    pushd ./floodlight-0.90
    su $SUDO_USER -c 'ant'
    popd
    OPENFLOW_INSTALED="FloodLight, "
else
    echo "skipping!"
fi


echo '
#################################################################
#####        CONFIGURE OPENMANO-GUI WEB                     #####
#################################################################'
#create a link, also a copy can be an alternative
ln -s ${PWD}/openmano/openmano-gui /var/www/html/openmano

#allow apache user: apache(centos), or www-data(ubuntu) grant access to the files, changing user owner
grep -q "^www-data:" /etc/passwd && chown -R www-data ./openmano/openmano-gui
grep -q "^apache:"   /etc/passwd && chown -R apache   ./openmano/openmano-gui
chmod -R g+w ./openmano/openmano-gui  #allow user to write using group permission

#ensure parent folders can be access by apache user
su $SUDO_USER -c 'chmod o+x ./openmano .'
PARENT_FOLDER=".."
while su $SUDO_USER -c "chmod o+x $PARENT_FOLDER &>/dev/null"
do
  #echo $PARENT_FOLDER
  PARENT_FOLDER="../$PARENT_FOLDER"
done

#Allow SELinux security over openmano-gui
[ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && chcon -R --reference=/var/www ${PWD}/openmano/openmano-gui || true

if [ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ]
then
    echo '
#################################################################
#####        CONFIGURE firewalld                            #####
#################################################################'
    read -e -p "Configure firewalld for openmanod port 9090? (Y/n)" KK
    if [ "$KK" != "n" -a  "$KK" != "no" ]
    then
        #Creates a service file for openmano
        echo '<?xml version="1.0" encoding="utf-8"?>
<service>
 <short>openmanod</short>
 <description>openmanod service</description>
 <port protocol="tcp" port="9090"/>
</service>' > /etc/firewalld/services/openmanod.xml
        #put proper permissions
        pushd /etc/firewalld/services > /dev/null
        restorecon openmanod.xml
        chmod 640 openmanod.xml
        popd > /dev/null
        #Add the openmanod service to the default zone permanently and reload the firewall configuration
        firewall-cmd --permanent --add-service=openmanod > /dev/null
        firewall-cmd --reload > /dev/null
        echo "done." 
    else
        echo "skipping."
    fi
fi

echo '
#################################################################
#####        CONFIGURE openvim openmano CLIENTS             #####
#################################################################'
#creates a link at ~/bin
su $SUDO_USER -c 'mkdir -p ~/bin'
rm -f /home/${SUDO_USER}/bin/openvim
rm -f /home/${SUDO_USER}/bin/openmano
ln -s ${PWD}/openmano/openvim/openvim   /home/${SUDO_USER}/bin/openvim
ln -s ${PWD}/openmano/openmano/openmano /home/${SUDO_USER}/bin/openmano
ln -s ${PWD}/openmano/scripts/service-openmano.sh  /home/${SUDO_USER}/bin/service-openmano

#insert /home/<user>/bin in the PATH
#skiped because normally this is done authomatically when ~/bin exist
#if ! su $SUDO_USER -c 'echo $PATH' | grep -q "/home/${SUDO_USER}/bin"
#then
#    echo "    inserting /home/$SUDO_USER/bin in the PATH at .bashrc"
#    su $SUDO_USER -c 'echo "PATH=\$PATH:/home/\${USER}/bin" >> ~/.bashrc'
#fi

#configure arg-autocomplete for this user
#in case of minmal instalation this packet is not installed by default
[[ "$_DISTRO" == "CentOS" || "$_DISTRO" == "Red" ]] && yum install -y bash-completion
su $SUDO_USER -c 'mkdir -p ~/.bash_completion.d'
su $SUDO_USER -c 'activate-global-python-argcomplete --dest=/home/${USER}/.bash_completion.d'
if ! grep -q bash_completion.d/python-argcomplete.sh /home/${SUDO_USER}/.bashrc
then
    echo "    inserting .bash_completion.d/python-argcomplete.sh execution at .bashrc"
    su $SUDO_USER -c 'echo ". .bash_completion.d/python-argcomplete.sh" >> ~/.bashrc'
fi

echo
echo "Done!  you may need to logout and login again for loading the configuration"
echo " Run './openmano/scripts/service-openmano.sh start' for starting ${OPENFLOW_INSTALED}openvim and openmano in a screen"



