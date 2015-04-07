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

# v0.3: 2015 March 
# Author: Antonio Lopez, Pablo Montes, Alfonso Tierno

# Personalize RHEL7.1 on compute nodes
# Prepared to work with the following network card drivers:
# tg3 driver for management interfaces
# i40e driver for data plane interfaces

# To download:
# wget wget https://raw.githubusercontent.com/nfvlabs/openmano/master/scripts/configure-compute-node-RHEL7.1-v0.3.sh
# To execute:
# chmod +x ./configure-compute-node-RHEL7.1-v0.3.sh
# sudo ./configure-compute-node-RHEL7.1-v0.3.sh <user> <iface>



function usage(){
    echo -e "Usage: sudo $0 [-y] <user-name>  [ <iface-name>  [<ip-address|dhcp] ]"
    echo -e "  Configure compute host for VIM usage. Params:"
    echo -e "     -y  do not prompt for confirmation. If a new user is created, the user name is set as password"
    echo -e "     <user-name> Create if not exist and configure this user for openvim to connect"
    echo -e "     <iface-name> if suplied creates bridge interfaces on this interface, needed for openvim"
    echo -e "     ip or dhcp if suplied, configure the interface with this ip address (/24) or 'dhcp' "
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
  if ! [ -z "$kk" -o "$kk"=="y" -o "$kk"=="Y" ]
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
#####       INSTALL HUGEPAGES ISOLCPUS GRUB                 #####
#################################################################'

# Huge pages 1G auto mount
#mkdir -p /mnt/huge
#if ! grep -q "Huge pages" /etc/fstab
#then
#  echo "" >> /etc/fstab
#  echo "# Huge pages" >> /etc/fstab
#  echo "nodev /mnt/huge hugetlbfs pagesize=1GB 0 0" >> /etc/fstab
#  echo "" >> /etc/fstab
#fi

# Huge pages reservation service
if ! [ -f /usr/lib/systemd/system/hugetlb-gigantic-pages.service ]
then
  echo "configuring huge pages service"
  cat > /usr/lib/systemd/system/hugetlb-gigantic-pages.service << EOL
[Unit]
Description=HugeTLB Gigantic Pages Reservation
DefaultDependencies=no
Before=dev-hugepages.mount
ConditionPathExists=/sys/devices/system/node
ConditionKernelCommandLine=hugepagesz=1G

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/lib/systemd/hugetlb-reserve-pages

[Install]
WantedBy=sysinit.target
EOL
fi
# Grub virtualization options:

# Get isolcpus
isolcpus=`gawk 'BEGIN{pre=-2;}
  ($1=="processor"){pro=$3;}
  ($1=="core" && $4!=0){
     if (pre+1==pro){endrange="-" pro}
     else{cpus=cpus endrange sep pro; sep=","; endrange="";};
     pre=pro;}
  END{printf("%s",cpus endrange);}' /proc/cpuinfo`


# Huge pages reservation file: reserving all memory apart from 4GB per NUMA node
# Get the number of hugepages: all memory but 8GB reserved for the OS
#totalmem=`dmidecode --type 17|grep Size |grep MB |gawk '{suma+=$2} END {print suma/1024}'`
#hugepages=$(($totalmem-8))

if ! [ -f /usr/lib/systemd/hugetlb-reserve-pages ]
then
  cat > /usr/lib/systemd/hugetlb-reserve-pages << EOL
#!/bin/bash
nodes_path=/sys/devices/system/node/
if [ ! -d \$nodes_path ]; then
        echo "ERROR: \$nodes_path does not exist"
        exit 1
fi

reserve_pages()
{
        echo \$1 > \$nodes_path/\$2/hugepages/hugepages-1048576kB/nr_hugepages
}

# This example reserves all available memory apart from 4 GB for linux
# using 1GB size. You can modify it to your needs or comment the lines
# to avoid reserve memory in a numa node
EOL
  for f in /sys/devices/system/node/node?/meminfo
  do
    node=`head -n1 $f | gawk '($5=="kB"){print $2}'`
    memory=`head -n1 $f | gawk '($5=="kB"){print $4}'`
    memory=$((memory+1048570))   #memory must be ceiled  
    memory=$((memory/1048576))   #from `kB to GB 
    #if memory 
    [ $memory -gt 4 ] && echo "reserve_pages $((memory-4)) node$node" >> /usr/lib/systemd/hugetlb-reserve-pages
  done

  # Run the following commands to enable huge pages early boot reservation:
  chmod +x /usr/lib/systemd/hugetlb-reserve-pages
  systemctl enable hugetlb-gigantic-pages
fi

# Prepares the text to add at the end of the grub line, including blacklisting ixgbevf driver in the host
textokernel="intel_iommu=on default_hugepagesz=1G hugepagesz=1G isolcpus=$isolcpus"  

# Add text to the kernel line
if ! grep -q "intel_iommu=on default_hugepagesz=1G hugepagesz=1G" /etc/default/grub
then
  echo "adding cmdline ${textokernel}"
  sed -i "/^GRUB_CMDLINE_LINUX=/s/\"\$/ ${textokernel}\"/" /etc/default/grub
  # grub2 upgrade
  grub2-mkconfig -o /boot/grub2/grub.cfg
fi

echo '
#################################################################
#####       OTHER CONFIGURATION                             #####
#################################################################'
# Mount shared NFS disk 
# 
#mkdir -p /mnt/NFS/images
#chown nobody:nobody /mnt/NFS/images
#chmod 777 /mnt/NFS/images
#if ! grep -q "10.95.164.177" /etc/fstab
#then
#echo "# Access to the lab disk array by NFS " >> /etc/fstab
#echo "10.95.164.177:/mnt/NFS/images /mnt/NFS/images nfs4 rsize=8192,wsize=8192,timeo=14,intr 0 0" >> /etc/fstab
#echo "" >> /etc/fstab
#fi

# ssh keys, not needed
#if [ ! -f /home/${user_name}/.ssh/authorized_keys ]
#then
#  mkdir -p /home/${user_name}/.ssh
#  touch /home/${user_name}/.ssh/authorized_keys
#  chown -R ${user_name}:admin /home/${user_name}/.ssh
#  chmod 700 /home/${user_name}/.ssh
#  chmod 600 /home/${user_name}/.ssh/authorized_keys
#fi


# Creates a folder to store images in the user home
#Creates a link to the /home folder because in RELH this folder is larger
echo "creating compute node folder for local images /opt/VNF/images"
if [ "$user_name" != "" ]
then
  mkdir -p /home/${user_name}/VNF_images
  chown -R ${user_name}:admin /home/${user_name}/VNF_images
  chmod go+x $HOME

  # The orchestator needs to link the images folder 
  rm -f /opt/VNF/images
  mkdir -p /opt/VNF/
  ln -s /home/${user_name}/VNF_images /opt/VNF/images
  chown -R ${user_name}:admin /opt/VNF

  # Selinux management
  echo "configure  Selinux management"
  semanage fcontext -a -t virt_image_t "/home/${user_name}/VNF_images(/.*)?"
  cat /etc/selinux/targeted/contexts/files/file_contexts.local |grep virt_image
  restorecon -R -v /home/${user_name}/VNF_images
else
  mkdir -p /opt/VNF/images
  chmod o+rx /opt/VNF/images
fi

echo "creating local information /opt/VNF/images/hostinfo.yaml"
echo "#By default openvim assumes control plane interface naming as em0,em1,em2,em3 " > /opt/VNF/images/hostinfo.yaml
echo "#and bridge ifaces as virbrMan1, virbrMan2, ..." >> /opt/VNF/images/hostinfo.yaml
echo "#if compute node contain a different name it must be indicated in this file" >> /opt/VNF/images/hostinfo.yaml
echo "#with the format extandard-name: compute-name" >> /opt/VNF/images/hostinfo.yaml
if [ "$interface" != "" -a "$interface" != "em1" ]
then
  echo "em1: ${interface}" >> /opt/VNF/images/hostinfo.yaml
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

#creating the polkit grant access for libvirt user. 
#This does not work !!!! so commented. No way to get running without uncomented the auth_unix_rw = "none" line
#
#cat > /etc/polkit-1/localauthority/50-local.d/50-org.example-libvirt-remote-access.pkla << EOL
#[libvirt Management Access]
# Identity=unix-user:n2;unix-user:kk
# Action=org.libvirt.unix.manage
# ResultAny=yes
# ResultInactive=yes
# ResultActive=yes
#EOL



# Configuration change of qemu for the numatune bug issue
# RHEL7.1: for this version should not be necesary - to revise
#if ! grep -q "cgroup_controllers = [ \"cpu\", \"devices\", \"memory\", \"blkio\", \"cpuacct\" ]" /etc/libvirt/qemu.conf
#then
#cat /etc/libvirt/qemu.conf | awk '{print $0}($0~"#cgroup_controllers"){print "cgroup_controllers = [ \"cpu\", \"devices\", \"memory\", \"blkio\", \"cpuacct\" ]"}' > tmp
#mv tmp /etc/libvirt/qemu.conf
#fi

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

  # For management and data interfaces
  rm -f /etc/udev/rules.d/pci_config.rules # it will be created to define VFs

  pushd /etc/sysconfig/network-scripts/

  # Management interfaces
#  integrated_interfaces=""
#  nb_ifaces=0
#  for iface in `ifconfig -a | grep ":\ " | cut -f 1 -d":"| grep -v "_" | grep -v "\." | grep -v "lo" | sort`
#  do 
#    driver=`ethtool -i $iface| awk '($0~"driver"){print $2}'`
#    if [ $driver != "ixgbe" ] && [ $driver != "bridge" ]
#    then
#      integrated_interfaces="$integrated_interfaces $iface"
#      nb_ifaces=$((nb_ifaces+1))
#      eval iface${nb_ifaces}=$iface
#    fi
#  done

  #Create bridge interfaces
  echo "Creating bridge ifaces: "
  for ((i=1;i<=20;i++))
  do
    i2digits=$i
    [ $i -lt 10 ] && i2digits="0$i"
    echo "    virbrMan$i  vlan 20$i2digits"
    echo "DEVICE=virbrMan$i
TYPE=Bridge
ONBOOT=yes
DELAY=0
NM_CONTROLLED=no
USERCTL=no

#Without IP:
#BOOTPROTO=static
#IPADDR=10.10.10.$((i+209))
#NETMASK=255.255.255.0" > ifcfg-virbrMan$i

    # create the required interfaces to connect the bridges
    echo "DEVICE=${interface}.20$i2digits
ONBOOT=yes
NM_CONTROLLED=no
USERCTL=no
VLAN=yes
BOOTPROTO=none
BRIDGE=virbrMan$i" > ifcfg-${interface}.20$i2digits
  done

  if [ -n "$ip_iface" ]
  then
    echo "configuring iface $iface interface with ip $ip_iface"
    # Network interfaces
    # 1Gbps interfaces are configured with ONBOOT=yes and static IP address
    cat ifcfg-$iface | grep -e HWADDR -e UUID > $iface.tmp
    echo "TYPE=Ethernet
NAME=$iface
DEVICE=$iface
TYPE=Ethernet
ONBOOT=yes
NM_CONTROLLED=no
IPV6INIT=no" >> $iface.tmp
    [ $ip_iface == "dhcp" ] && echo -e "BOOTPROTO=dhcp\nDHCP_HOSTNAME=$HOSTNAME" >> $iface.tmp
    [ $ip_iface != "dhcp" ] && echo -e "BOOTPROTO=static\nIPADDR=${ip_iface}\nNETMASK=255.255.255.0" >> $iface.tmp
    mv $iface.tmp  ifcfg-$iface
  fi

  for iface in `ifconfig -a | grep ": " | cut -f 1 -d":" | grep -v -e "_" -e "\." -e "lo" -e "virbr" -e "tap"`
  do
    # 10/40 Gbps interfaces
    # Intel X520 cards: driver ixgbe
    # Intel XL710 Fortville cards: driver i40e
    driver=`ethtool -i $iface| awk '($0~"driver"){print $2}'`
    if [ "$driver" == "i40e" -o "$driver" == "ixgbe" ]
    then
      echo "configuring dataplane iface $iface"
      # Create 8 SR-IOV per PF
      #echo 0 > /sys/bus/pci/devices/`ethtool -i $iface | awk '($0~"bus-info"){print $2}'`/sriov_numvfs
      #echo 8 > /sys/bus/pci/devices/`ethtool -i $iface | awk '($0~"bus-info"){print $2}'`/sriov_numvfs
      pci=`ethtool -i $iface | awk '($0~"bus-info"){print $2}'`
      echo "ACTION==\"add\", KERNEL==\"$pci\", SUBSYSTEM==\"pci\", RUN+=\"/usr/bin/bash -c 'echo 8 > /sys/bus/pci/devices/$pci/sriov_numvfs'\"" >> /etc/udev/rules.d/pci_config.rules

      # Configure PF to boot automatically and to have a big MTU
      # 10Gbps interfaces are configured with ONBOOT=yes and  MTU=2000
      cat ifcfg-$iface | grep -e HWADDR -e UUID > $iface.tmp
      echo "TYPE=Ethernet
NAME=$iface
ONBOOT=yes
MTU=2000
NM_CONTROLLED=no
IPV6INIT=no
BOOTPROTO=none" >> $iface.tmp
      mv $iface.tmp ifcfg-$iface
    fi
  done
  popd
fi

echo 
echo "Do not forget to create a shared (NFS, Samba, ...) where original virtual machine images are allocated"
echo
echo "Do not forget to copy the public ssh key into /home/${user_name}/.ssh/authorized_keys for authomatic loging from openvim controller"
echo

echo "Reboot the system to make the changes effective"


