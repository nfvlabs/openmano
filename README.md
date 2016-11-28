_**This page is obsolete.**_

_**The project OpenMANO has been contributed to the open source community project Open Source MANO (OSM), hosted by ETSI.**_

_**Go to the URL [osm.etsi.org](osm.etsi.org) to know more about OSM.**_

***

<img src="https://github.com/nfvlabs/openmano/raw/master/images/openmano.png" alt="openmano" height="200"/>

**OpenMANO** is an open source project that provides a practical implementation of the reference architecture for Management & Orchestration under standardization at ETSI’s NFV ISG ([NFV MANO](http://www.etsi.org/deliver/etsi_gs/NFV/001_099/002/01.01.01_60/gs_NFV002v010101p.pdf)). It consists of three main SW components:

- **openvim**: reference implementation of an NFV VIM (Virtualised Infrastructure Manager). It interfaces with the compute nodes in the NFV Infrastructure and an openflow controller in order to provide computing and networking capabilities and to deploy virtual machines. It offers a northbound interface, based on REST ([openvim API](http://github.com/nfvlabs/openmano/raw/master/docs/openvim-api-0.6.pdf "openvim API")), where enhanced cloud services are offered including the creation, deletion and management of images, flavors, instances and networks. The implementation follows the recommendations in [NFV-PER001](http://www.etsi.org/deliver/etsi_gs/NFV-PER/001_099/001/01.01.02_60/gs_NFV-PER001v010102p.pdf "ETSI NFV PER001"). 
- **openmano**: reference implementation of an NFV-O (Network Functions Virtualisation Orchestrator). It interfaces with an NFV VIM through its API and offers a northbound interface, based on REST (openmano API), where NFV services are offered including the creation and deletion of VNF templates, VNF instances, network service templates and network service instances.
- **openmano-gui**: web GUI to interact with openmano server, through its northbound API, in a friendly way. 

<img src="https://github.com/nfvlabs/openmano/raw/master/images/openmano-nfv.png" align="middle" alt="openmano-nfv" height="400"/>

#Releases

The relevant releases/branches in openmano are the following:

- **v0.4**: current stable release for normal use. Supports several datacenters, openstack as a VIM, opendaylight as openflow controller
- v0.3: old stable release version
- **master**: development branch intended for contributors, with new features that will be incorporated into the stable release

#Quick installation of current release (v0.4)

- Download e.g. a [Ubuntu Server 14.04 LTS](http://virtualboxes.org/images/ubuntu-server) (ubuntu/reverse). Other tested distributions are [Ubuntu Desktop 64bits 14.04.2 LTS](http://sourceforge.net/projects/osboxes/files/vms/vbox/Ubuntu/14.04/14.04.2/Ubuntu_14.04.2-64bit.7z/download) (osboxes/osboxes.org), [CentOS 7](http://sourceforge.net/projects/osboxes/files/vms/vbox/CentOS/CentOS_7-x86_64.7z/download) (osboxes/osboxes.org)
- Start the VM and execute the following command in a terminal:

        wget https://github.com/nfvlabs/openmano/raw/v0.4/scripts/install-openmano.sh
        chmod +x install-openmano.sh
        sudo ./install-openmano.sh [<database-root-user> [<database-password>]]
        #NOTE: you can provide optionally the DB root user and password.

Manual installation can be done following these [instructions](https://github.com/nfvlabs/openmano/wiki/Getting-started#manual-installation). 

#Full documentation
- [Getting started](https://github.com/nfvlabs/openmano/wiki/Getting-started "getting started")
- [Compute node configuration](https://github.com/nfvlabs/openmano/wiki/Compute-node-configuration "compute node configuration")
- [Openmano NFV descriptors](https://github.com/nfvlabs/openmano/wiki/openmano-descriptors "openmano descriptors")
- [Openmano usage manual](https://github.com/nfvlabs/openmano/wiki/openmano-usage "openmano usage manual")
- [Openvim usage manual](https://github.com/nfvlabs/openmano/wiki/openvim-usage  "openvim usage manual")
- [Openmano API](https://github.com/nfvlabs/openmano/wiki/openmano-api "openmano API")
- [Openvim API](https://github.com/nfvlabs/openmano/raw/master/docs/openvim-api-0.6.pdf "openvim API")
- [Guidelines for developers](https://github.com/nfvlabs/openmano/wiki/guidelines-for-developers "guidelines for developers")

#License
Check the [License](https://github.com/nfvlabs/openmano/blob/master/LICENSE "license") file.

#Contact
For bug reports or clarification, contact [nfvlabs@tid.es](mailto:nfvlabs@tid.es "nfvlabs")

