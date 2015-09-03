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

# Authors: Antonio Lopez, Pablo Montes, Alfonso Tierno
# June 2015

# Personalize RHEL7.1 on compute nodes
# Prepared to work with the following network card drivers:
# 	tg3, igb drivers for management interfaces
# 	ixgbe (Intel Niantic) and i40e (Intel Fortville) drivers for data plane interfaces

# To download:
# wget https://raw.githubusercontent.com/nfvlabs/openmano/master/scripts/configure-compute-node-RHEL7.1.sh
# To execute:
# chmod +x ./configure-compute-node-RHEL7.1.sh
# sudo ./configure-compute-node-RHEL7.1.sh <user> <iface>

# Assumptions:
# All virtualization options activated on BIOS (vt-d, vt-x, SR-IOV, no power savings...)
# RHEL7.1 installed without /home partition and with the following packages selection:
# @base, @core, @development, @network-file-system-client, @virtualization-hypervisor, @virtualization-platform, @virtualization-tools


function usage(){
    echo -e "Usage: sudo $0 [-y] <user-name>  [ <iface-name>  [<ip-address>|dhcp] ]"
    echo -e "  Configure compute host for VIM usage. (version 0.4). Params:"
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
apt-get -y update
#apt-get -y install grub-common screen virt-manager ethtool build-essential x11-common x11-utils x11-apps libguestfs-tools hwloc libguestfs-tools numactl vlan nfs-common nfs-kernel-server
apt-get -y install grub-common screen virt-manager ethtool build-essential x11-common x11-utils libguestfs-tools hwloc libguestfs-tools numactl vlan nfs-common nfs-kernel-server

echo "Remove unneeded packages....."
apt-get -y autoremove
# Selinux management
#yum install -y policycoreutils-python



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
#####       INSTALL HUGEPAGES ISOLCPUS GRUB                 #####
#################################################################'

# Huge pages 1G auto mount
mkdir -p /mnt/huge
if ! grep -q "Huge pages" /etc/fstab
then
  echo "" >> /etc/fstab
  echo "# Huge pages" >> /etc/fstab
  echo "nodev /mnt/huge hugetlbfs pagesize=1GB 0 0" >> /etc/fstab
  echo "" >> /etc/fstab
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


echo "CPUS: $isolcpus"

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
    memory=$((memory+1048576-1))   #memory must be ceiled  
    memory=$((memory/1048576))   #from `kB to GB 
    #if memory 
    [ $memory -gt 4 ] && echo "reserve_pages $((memory-4)) node$node" >> /usr/lib/systemd/hugetlb-reserve-pages
  done

  # Run the following commands to enable huge pages early boot reservation:
  chmod +x /usr/lib/systemd/hugetlb-reserve-pages
  systemctl enable hugetlb-gigantic-pages
fi

# Prepares the text to add at the end of the grub line, including blacklisting ixgbevf driver in the host
memtotal=`grep MemTotal /proc/meminfo | awk '{ print $2 }' `
hpages=$(( ($memtotal/(1024*1024))-8 ))

memtotal=$((memtotal+1048576-1))   #memory must be ceiled
memtotal=$((memtotal/1048576))   #from `kB to GBa
hpages=$((memtotal-6))




echo "------> memtotal: $memtotal"

textokernel="intel_iommu=on default_hugepagesz=1G hugepagesz=1G hugepages=$hpages isolcpus=$isolcpus modprobe.blacklist=ixgbevf modprobe.blacklist=i40evf"  

echo "Text to kernel: $textokernel"


# Add text to the kernel line
if ! grep -q "intel_iommu=on default_hugepagesz=1G hugepagesz=1G" /etc/default/grub
then
  echo ">>>>>>>  adding cmdline ${textokernel}"
  sed -i "/^GRUB_CMDLINE_LINUX_DEFAULT=/s/\"\$/${textokernel}\"/" /etc/default/grub
  # grub2 upgrade
  #grub2-mkconfig -o /boot/grub2/grub.cfg
  update-grub
fi

echo '
#################################################################
#####       OTHER CONFIGURATION                             #####
#################################################################'

# Links the OpenMANO required folder /opt/VNF/images to /var/lib/libvirt/images. The OS installation
# should have only a / partition with all possible space available

echo " link /opt/VNF/images to /var/lib/libvirt/images"
if [ "$user_name" != "" ]
then
  #mkdir -p /home/${user_name}/VNF_images
  #chown -R ${user_name}:admin /home/${user_name}/VNF_images
  #chmod go+x $HOME

  # The orchestator needs to link the images folder 
  rm -f /opt/VNF/images
  mkdir -p /opt/VNF/
  ln -s /var/lib/libvirt/images /opt/VNF/images
  chown -R ${user_name}:admin /opt/VNF
  chown -R root:admin /var/lib/libvirt/images
  chmod g+rwx /var/lib/libvirt/images

  # Selinux management
  #echo "configure  Selinux management"
  #semanage fcontext -a -t virt_image_t "/home/${user_name}/VNF_images(/.*)?"
  #cat /etc/selinux/targeted/contexts/files/file_contexts.local |grep virt_image
  #restorecon -R -v /home/${user_name}/VNF_images
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
  echo "iface_names:"  >> /opt/VNF/images/hostinfo.yaml
  echo "  em1: ${interface}" >> /opt/VNF/images/hostinfo.yaml
fi
chmod o+r /opt/VNF/images/hostinfo.yaml

# deactivate memory overcommit
#echo "deactivate memory overcommit"
#service ksmtuned stop
#service ksm stop
#chkconfig ksmtuned off
#chkconfig ksm off


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
echo "Interface ==> $interface"
if [ -n "$interface" ]
then


  # For management and data interfaces
  rm -f /etc/udev/rules.d/pci_config.rules # it will be created to define VFs


  # Set ONBOOT=on and MTU=9000 on the interface used for the bridges
  echo "configuring iface $interface"

#MTU for interfaces and bridges
MTU=9000

cp /etc/network/interfaces interfaces.tmp


  #Create infrastructure bridge, normally used for connecting to compute nodes, openflow controller, ...  


    #Create VLAN for infrastructure bridge

 echo "
######### CUTLINE #########

auto ${interface}
iface ${interface} inet static
	mtu $MTU

auto ${interface}.1001
iface ${interface}.1001 inet static
	mtu $MTU
" >> interfaces.tmp

 echo "ifconfig ${interface} mtu $MTU
 ifconfig ${interface} up
" > mtu.tmp


  #Create bridge interfaces
  echo "Creating bridge ifaces: "
  for ((i=1;i<=20;i++))
  do
    i2digits=$i
    [ $i -lt 10 ] && i2digits="0$i"
    echo "    virbrMan$i  vlan 20$i2digits"

    j=$i

 echo "
auto ${interface}.20$i2digits
iface ${interface}.20$i2digits inet static
	mtu $MTU

auto virbrMan$j
iface virbrMan$j inet static
	bridge_ports ${interface}.20$i2digits
	mtu $MTU
" >> interfaces.tmp

 echo "ifconfig ${interface}.20$i2digits mtu $MTU
ifconfig virbrMan$j mtu $MTU
ifconfig virbrMan$j up
" >> mtu.tmp

  done

 echo "
auto em2.1001
iface em2.1001 inet static

auto virbrInf
iface virbrInf inet static
	bridge_ports em2.1001
" >> interfaces.tmp

 echo "ifconfig em2.1001 mtu $MTU
ifconfig virbrInf mtu $MTU
ifconfig virbrInf up
" >> mtu.tmp

if ! grep -q "#### CUTLINE ####" /etc/network/interfaces
then
	echo "====== Copying interfaces.tmp to /etc/network/interfaces"
	cp interfaces.tmp /etc/network/interfaces
fi


  #popd
fi


# Activate 8 Virtual Functions per PF on Niantic cards (ixgbe driver)
if [[ `lsmod | cut -d" " -f1 | grep "ixgbe" | grep -v vf` ]]
then
	if ! grep -q "ixgbe" /etc/modprobe.d/ixgbe.conf
	then
	echo "options ixgbe max_vfs=8" >> /etc/modprobe.d/ixgbe.conf
	fi

fi

# Set dataplane MTU

echo "sleep 10" >> mtu.tmp

interfaces=`ifconfig -a | grep ^p | cut -d " " -f 1`
for ph in $interfaces
do
        echo "ifconfig $ph mtu $MTU" >> mtu.tmp
        echo "ifconfig $ph up" >> mtu.tmp
done



cp mtu.tmp /etc/setmtu.sh
chmod +x /etc/setmtu.sh

# To define 8 VFs per PF we do it on rc.local, because the driver needs to be unloaded and loaded again
#if ! grep -q "NFV" /etc/rc.local
#then
  echo "#!/bin/sh -e
" > /etc/rc.local
  echo "# NFV" >> /etc/rc.local
  echo "modprobe -r ixgbe" >> /etc/rc.local
  echo "modprobe ixgbe max_vfs=8" >> /etc/rc.local
  echo "/etc/setmtu.sh" >> /etc/rc.local
  echo "
exit 0" >> /etc/rc.local
  echo "" >> /etc/rc.local

  chmod +x /etc/rc.d/rc.local

#fi

chmod a+rwx /var/lib/libvirt/images
mkdir /usr/libexec/
pushd /usr/libexec/
ln -s /usr/bin/qemu-system-x86_64 qemu-kvm
popd

#Deactivating apparmor while looking for a better solution
/etc/init.d/apparmor stop
update-rc.d -f apparmor remove

echo 
echo "Do not forget to create a shared (NFS, Samba, ...) where original virtual machine images are allocated"
echo
echo "Do not forget to copy the public ssh key into /home/${user_name}/.ssh/authorized_keys for authomatic login from openvim controller"
echo

echo "Reboot the system to make the changes effective"


