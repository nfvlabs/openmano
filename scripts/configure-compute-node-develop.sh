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

# v1.0: 2015 June 
# Authors: Antonio Lopez, Pablo Montes, Alfonso Tierno

# Personalize RHEL7/CENTOS compute nodes for using openvim in 'development' mode: 
#   not using huge pages neither isolcpus

# To download:
# wget https://raw.githubusercontent.com/nfvlabs/openmano/master/scripts/configure-compute-node-develop.sh
# To execute:
# chmod +x ./configure-compute-node-develop.sh
# sudo ./configure-compute-node-develop.sh <user> <iface>

function usage(){
    echo -e "Usage: sudo $0 [-y] <user-name>  [ <iface-name>  [<ip-address>|dhcp] ]"
    echo -e "  Configure compute host for VIM usage in mode 'development'. Params:"
    echo -e "     -y  do not prompt for confirmation. If a new user is created, the user name is set as password"
    echo -e "     <user-name> Create if not exist and configure this user for openvim to connect"
    echo -e "     <iface-name> if supplied creates bridge interfaces on this interface, needed for openvim"
    echo -e "     ip or dhcp if supplied, configure the interface with this ip address (/24) or 'dhcp' "
}

#1 CHECK input parameters
#1.1 root privileges
[ "$USER" != "root" ] && echo "Needed root privileges" && usage && exit -1

#1.2 input parameters
FORCE=""
while getopts "y" o; do
    case "${o}" in
        y)
            FORCE="yes"
            ;;
        *)
            usage
            exit -1
            ;;
    esac
done
shift $((OPTIND-1))


if [ $# -lt 1 ]  
then
  usage
  exit
fi

user_name=$1
interface=$2
ip_iface=$3

if [ -n "$interface" ] && ! ifconfig $interface &> /dev/null
then
  echo "Error: interface '$interface' is not present in the system"
  usage
  exit 1
fi

echo '
#################################################################
#####       INSTALL NEEDED PACKETS                          #####
#################################################################'

# Required packages
yum repolist
yum check-update
yum update -y
yum install -y screen virt-manager ethtool gcc gcc-c++ xorg-x11-xauth xorg-x11-xinit xorg-x11-deprecated-libs libXtst guestfish hwloc libhugetlbfs-utils libguestfs-tools
# Selinux management
yum install -y policycoreutils-python

echo '
#################################################################
#####       INSTALL USER                                    #####
#################################################################'

# Add required groups
groupadd -f admin
groupadd -f libvirt   #for other operating systems may be libvirtd

# Adds user, default password same as name
if grep -q "^${user_name}:" /etc/passwd
then 
  #user exist, add to group
  echo "adding user ${user_name} to groups libvirt,admin"
  usermod -a -G libvirt,admin -g admin $user_name
else 
  #create user if it does not exist
  [ -z "$FORCE" ] && read -p "user '${user_name}' does not exist, create (Y/n)" kk
  if ! [ -z "$kk" -o "$kk"="y" -o "$kk"="Y" ]
  then
    exit
  fi
  echo "creating and configuring user ${user_name}"
  useradd -m -G libvirt,admin -g admin $user_name       
  #Password
  if [ -z "$FORCE" ] 
  then 
     echo "Provide a password for $user_name"
     passwd $user_name
  else
     echo -e "$user_name\n$user_name" | passwd --stdin $user_name
  fi
fi

# Allow admin users to access without password
if ! grep -q "#openmano" /etc/sudoers
then
    cat >> /home/${user_name}/script_visudo.sh << EOL
#!/bin/bash
cat \$1 | awk '(\$0~"requiretty"){print "#"\$0}(\$0!~"requiretty"){print \$0}' > tmp
cat tmp > \$1
rm tmp
echo "" >> \$1
echo "#openmano allow to group admin to grant root privileges without password" >> \$1
echo "%admin ALL=(ALL) NOPASSWD: ALL" >> \$1
EOL
    chmod +x /home/${user_name}/script_visudo.sh
    echo "allowing admin user to get root privileges withut password"
    export EDITOR=/home/${user_name}/script_visudo.sh && sudo -E visudo
    rm -f /home/${user_name}/script_visudo.sh
fi

echo '
#################################################################
#####       OTHER CONFIGURATION                             #####
#################################################################'
# Creates a folder to store images in the user home
#Creates a link to the /home folder because in RHEL this folder is larger
echo "creating compute node folder for local images /opt/VNF/images"
if [ "$user_name" != "" ]
then
  mkdir -p /home/VNF_images
  chown -R ${user_name}:admin /home/VNF_images
  chmod go+x /home/VNF_images

  # The orchestator needs to link the images folder 
  rm -f /opt/VNF/images
  mkdir -p /opt/VNF/
  ln -s /home/VNF_images /opt/VNF/images
  chown -R ${user_name}:admin /opt/VNF

else
  mkdir -p /opt/VNF/images
  chmod o+rx /opt/VNF/images
fi

echo "creating local information /opt/VNF/images/hostinfo.yaml"
echo "#By default openvim assumes control plane interface naming as em1,em2,em3,em4 " > /opt/VNF/images/hostinfo.yaml
echo "#and bridge ifaces as virbrMan1, virbrMan2, ..." >> /opt/VNF/images/hostinfo.yaml
echo "#if compute node contain a different name it must be indicated in this file" >> /opt/VNF/images/hostinfo.yaml
echo "#with the format extandard-name: compute-name" >> /opt/VNF/images/hostinfo.yaml
if [ "$interface" != "" -a "$interface" != "em1" ]
then
  echo "iface_names:"        >> /opt/VNF/images/hostinfo.yaml
  echo "  em1: ${interface}" >> /opt/VNF/images/hostinfo.yaml
fi
chmod o+r /opt/VNF/images/hostinfo.yaml

# deactivate memory overcommit
echo "deactivate memory overcommit"
service ksmtuned stop
service ksm stop
chkconfig ksmtuned off
chkconfig ksm off

# Libvirt options (uncomment the following)
echo "configure Libvirt options"
sed -i 's/#unix_sock_group = "libvirt"/unix_sock_group = "libvirt"/' /etc/libvirt/libvirtd.conf
sed -i 's/#unix_sock_rw_perms = "0770"/unix_sock_rw_perms = "0770"/' /etc/libvirt/libvirtd.conf
sed -i 's/#unix_sock_dir = "\/var\/run\/libvirt"/unix_sock_dir = "\/var\/run\/libvirt"/' /etc/libvirt/libvirtd.conf
sed -i 's/#auth_unix_rw = "none"/auth_unix_rw = "none"/' /etc/libvirt/libvirtd.conf

echo '
#################################################################
#####       NETWORK CONFIGURATION                           #####
#################################################################'
# Network config (if the second parameter is net)
if [ -n "$interface" ]
then

  # Deactivate network manager
  #systemctl stop NetworkManager
  #systemctl disable NetworkManager

  pushd /etc/sysconfig/network-scripts/

  #Create infrastructure bridge
  echo "DEVICE=virbrInf
TYPE=Bridge
ONBOOT=yes
DELAY=0
NM_CONTROLLED=no
IPADDR=10.10.0.1
NETMASK=255.255.255.0
USERCTL=no" > ifcfg-virbrInf

  #Create bridge interfaces
  echo "Creating bridge ifaces: "
  for ((i=1;i<=20;i++))
  do
    i2digits=$i
    [ $i -lt 10 ] && i2digits="0$i"
    echo "    virbrMan$i"
    echo "DEVICE=virbrMan$i
TYPE=Bridge
ONBOOT=yes
DELAY=0
NM_CONTROLLED=no
USERCTL=no" > ifcfg-virbrMan$i

  done

  popd
fi

echo 
echo "Do not forget to create a folder where original virtual machine images are allocated (ex. $HOME/static_storage)"
echo
echo "Do not forget to allow openvim machine accessing directly to the host with ssh. Can be done by:"
echo "   Copy the public ssh key of the openvim user from $HOME/.ssh/id_dsa.pub (in openvim) into /home/${user_name}/.ssh/authorized_keys (in the host) for automatic login from openvim controller"
echo "   Or running on openvim machine 'ssh-keygen' (generate ssh keys) and 'ssh-copy-id <user>@<compute host>'"
echo
echo "Do not forget to perform an initial ssh login from openmano VM into the host so the openmano ssh host key is added to /home/${user_name}/.ssh/known_hosts"
echo

echo "Reboot the system to make the changes effective"


