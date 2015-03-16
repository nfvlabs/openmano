#!/bin/bash
if [ $EUID -ne 0  -o -z "$SUDO_USER" ]; then
        echo "usage: sudo $0 db_user db_passwd"
        echo "execte using sudo"
        exit 1
fi
if [ -z "$1" -o -z "$2" ]; then
        echo "provide database user and password"
        exit 1
fi

echo '
#################################################################
#####        INSTALL PACKETS                                #####
#################################################################'
apt-get update -y
apt-get -y install python-yaml python-libvirt python-bottle python-mysqldb python-jsonschema python-paramiko git screen


echo '
#################################################################
#####        DOWNLOAD SOURCE                                #####
#################################################################'
su $SUDO_USER -c 'git clone https://github.com/nfvlabs/openmano.git openmano'

echo '
#################################################################
#####        CREATE DATABASE                                #####
#################################################################'
mysqladmin -u$1 -p$2 create vim_db
mysqladmin -u$1 -p$2 create mano_db

echo "CREATE USER 'vim'@'localhost' identified by 'vimpw';"  | mysql -u$1 -p$2
echo "GRANT ALL PRIVILEGES ON vim_db.* TO 'vim'@'localhost';" | mysql -u$1 -p$2
echo "CREATE USER 'mano'@'localhost' identified by 'manopw';" | mysql -u$1 -p$2
echo "GRANT ALL PRIVILEGES ON mano_db.* TO 'mano'@'localhost';" | mysql -u$1 -p$2


echo "vim database"
su $SUDO_USER -c './openmano/openvim/database_utils/init_vim_db.sh vim vimpw vim_db'
echo "mano database"
su $SUDO_USER -c './openmano/openmano/database_utils/init_mano_db.sh mano manopw mano_db'

echo "Automatic openflow controller instalation comming soon ..."

echo
echo "Done!   Run './scripts/start-all.sh' for starting openvim,openmano in a screen"

