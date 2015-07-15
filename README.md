<img src="https://github.com/nfvlabs/openmano/raw/master/images/openmano.png" alt="openmano" height="200"/>

**OpenMANO** is an open source project that provides a practical implementation of the reference architecture for Management & Orchestration under standardization at ETSI’s NFV ISG ([NFV MANO](http://www.etsi.org/deliver/etsi_gs/NFV/001_099/002/01.01.01_60/gs_NFV002v010101p.pdf)). It consists of three main SW components:

- **openvim**: reference implementation of an NFV VIM (Virtualised Infrastructure Manager). It interfaces with the compute nodes in the NFV Infrastructure and an openflow controller in order to provide computing and networking capabilities and to deploy virtual machines. It offers a northbound interface, based on REST ([openvim API](http://github.com/nfvlabs/openmano/raw/master/docs/openvim-api-0.6.pdf "openvim API")), where enhanced cloud services are offered including the creation, deletion and management of images, flavors, instances and networks. The implementation follows the recommendations in [NFV-PER001](http://www.etsi.org/deliver/etsi_gs/NFV-PER/001_099/001/01.01.02_60/gs_NFV-PER001v010102p.pdf "ETSI NFV PER001"). 
- **openmano**: reference implementation of an NFV-O (Network Functions Virtualisation Orchestrator). It interfaces with an NFV VIM through its API and offers a northbound interface, based on REST (openmano API), where NFV services are offered including the creation and deletion of VNF templates, VNF instances, network service templates and network service instances.
- **openmano-gui**: web GUI to interact with openmano server, through its northbound API, in a friendly way. 

<img src="https://github.com/nfvlabs/openmano/raw/master/images/openmano-nfv.png" align="middle" alt="openmano-nfv" height="400"/>

#Releases

Current releases/branches in openmano are the following:

- v0.3: current stable release for normal use
- master: development branch intended for contributors, with new features that will be incorporated into the stable release

#Quick installation of current release (v0.3)

- Download a VDI Ubuntu Server 14.10 LAMP image from [here](https://virtualboximages.com/Ubuntu+14.10+amd64+LAMP+Server+VirtualBox+VDI+Virtual+Computer "download VM image").
- Start the VM and execute the following command in a terminal:

        wget https://github.com/nfvlabs/openmano/raw/v0.3/scripts/install-openmano.sh
        chmod +x install-openmano.sh
        sudo ./install-openmano.sh root adminuser
        #NOTE: **root adminuser** are the mysql user and password of this VM image

Manual installation can be done following these [instructions](https://github.com/nfvlabs/openmano/wiki/Getting-started#manual-installation). 

#Full documentation
- [Getting started](https://github.com/nfvlabs/openmano/wiki/Getting-started "getting started")
- [Compute node configuration](https://github.com/nfvlabs/openmano/wiki/Compute-node-configuration "compute node configuration")
- [Openmano NFV descriptors](https://github.com/nfvlabs/openmano/wiki/openmano-descriptors "openmano descriptors")
- [Openmano usage manual](https://github.com/nfvlabs/openmano/wiki/openmano-usage "openmano usage manual")
- [Openvim usage manual](https://github.com/nfvlabs/openmano/wiki/openvim-usage  "openvim usage manual")
- [Openvim API](https://github.com/nfvlabs/openmano/raw/master/docs/openvim-api-0.6.pdf "openvim API")
- Openmano API (coming soon)
- [Guidelines for developers](https://github.com/nfvlabs/openmano/wiki/guidelines-for-developers "guidelines for developers")

#License
Check the [License](https://github.com/nfvlabs/openmano/blob/master/LICENSE "license") file.

#Contact
For bug reports or clarification, contact [nfvlabs@tid.es](mailto:nfvlabs@tid.es "nfvlabs")

