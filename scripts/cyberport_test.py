#!/usr/bin/python
#--------------------------------------------------------------
# Cyberport setup with following requirements
#--------------------------------------------------------------
# 10 nodes Setup
#	1.100 VMs
#	2.2 ports per VM
#	3.50 Tenants
#	4.1 VLAN
#	5.50 VXLAN (5 Gbps per server)
#	6.256 Flows per port
#-------------------------------------------------------------
#
# 			!ASSUMPTIONS!
# 1. Data and dhcp port profiles have been already created 
#    on the VSM 
#--------------------------------------------------------------

import sys
sys.path.append('../lib')
import subprocess
import json
import logging
from os_nw_lib import *
from time import sleep

NET_CREATE_DELAY = 5
SUBNET_CREATE_DELAY = 5
PORT_CREATE_DELAY = 5
VM_CREATE_DELAY = 8

# Initialize logging
logging.basicConfig( format='%(asctime)s [%(levelname)s] %(name)s - %(message)s', level=logging.WARNING )
cbp_log = logging.getLogger( __name__ )

cbp_log.setLevel(logging.DEBUG)

#------------------------------------------------
# Global data
#------------------------------------------------
# For this test the data policy profile name is 
# set here. It must match with the policy profile
# created on the VSM
policy_profile_name = "data-policy1"

class CyberPort_Test( ):

    def __init__( self ):

	# Define network profile list by name
	self.vlan_nw_prf_name = 'cyberport-pool'
	self.vxlan_nw_prf_name = 'cyberport-vxlan-pool'
	
	# Define segment ranges
	self.vlan_seg_range = "401-450"
	self.vxlan_seg_Range = "7000-7100"
	
	# Define number of networks
	self.num_vxlans = 50

	# Define vlan based network name. Since we need just 1 vlan
	# we define single network
	self.vlan_nw_name = "vlan-401"

	# Define the subnet name for this net
	self.vlan_subnet_name = 'pool-401'
	self.vlan_cidr = '10.10.10.0/24'

	# Create a list of vxlan based networks names
	self.vxlan_nw_names = []
	for i in range( 7000, ( self.num_vxlans + 7000 )):
	    self.vxlan_nw_names.append( ( "vxlan-%s" % i ) )
	cbp_log.debug( "CyberPort_Test: self.vxlan_nw_names\n %s", self.vxlan_nw_names )

	# Create a list of subnet names for vxlan
	self.vxlan_subnet_names = []
	for i in range( 7000, ( self.num_vxlans + 7000 )):
	    self.vxlan_subnet_names.append( ( "vxpool-%s" % i ) )
	cbp_log.debug( "CyberPort_Test: self.vxlan_subnet_names\n %s", self.vxlan_subnet_names )

	# Create a list of vxlan based cidrs
	self.vxlan_cidr_list = []
	for i in range( 1, ( self.num_vxlans + 1 )):
	    self.vxlan_cidr_list.append( ( "20.20.%s.0/24" % i ) )
	cbp_log.debug( "CyberPort_Test: self.vxlan_cidr_list\n %s", self.vxlan_cidr_list )

	# Define a place holder for vxlan subnets
	self.vxlan_subnet_list = []

	# Get keystone tenants and users
	self.tenants_table = get_keystone_tenants()
	self.users_list = get_keystone_users()
	cbp_log.debug( "CyberPort_Test: self.tenants_table\n %s", self.tenants_table )
	cbp_log.debug( "CyberPort_Test: self.users_list\n %s", self.users_list )

	# Get the custom tenant ids for tenants
        self.tenant_id_list = get_custom_tenant_ids( self.tenants_table )
	cbp_log.debug( "CyberPort_Test: self.tenant_id_list\n %s", self.tenant_id_list )	

	# Get the user and tenant-id mappings
        self.user_tenant_map = get_user_tenant_mappings()

	# Set the user password
	self.usr_pass = "n1k12345"

	# Set the keystone auth url
	self.os_auth_url = "http://4.4.1.151:5000/v2.0/"

	# Get the policy profiles from vsm
	self.pp_table = get_policy_profiles()
	cbp_log.debug( "CyberPort_Test: self.pp_table\n %s", self.pp_table )
	
	# Number of VMs to be instantiated
	self.num_of_VMs = 500
	
	# VM data table
	self.vm_boot_data = {}

	# List of vlan ports
	self.vlan_ports = []
	
	# List of VM names
	self.vm_names_list = []

	# VM image name to be used
	self.img_name = "ubuntu-image"
	self.img_flavor = "m1.small"

	# Table to hold instantiated VM information
	self.vm_table = {}

    def cyberport_nw_prf_create( self ):

        # Create a n/w profile for vlan based n/w
        self.vlan_nw_prof_id = create_nw_profile( self.vlan_nw_prf_name, 'vlan', seg_range=self.vlan_seg_range, phys_nw="cyberport" )
	 
        # Create a n/w profile for vxlan based n/w
        self.vxlan_nw_prof_id = create_nw_profile( self.vxlan_nw_prf_name, 'vxlan', seg_range=self.vxlan_seg_Range, sub_type="unicast" )

   
    def cyberport_vlan_net_create( self ):

	# Get the network profile id first
	nw_prf_table = get_n1k_network_profiles()

	# Retrieve the network profile for vlan
	vlan_nw_prof_id = get_n1k_nw_profile_id( self.vlan_nw_prf_name, nw_prf_table )
	if vlan_nw_prof_id != "":
	    # Create a shared vlan net and its subnet, 'shared' variable is set to "" since
	    # the option is just '--shared', there is no value to be specified
	    self.vlan_net_id = create_nw( self.vlan_nw_name, vlan_nw_prof_id, shared="" )
	    self.vlan_subnet_id = create_subnet( self.vlan_nw_name, self.vlan_cidr, subnet_name=self.vlan_subnet_name )

	else:
	    cbp_log.warning( "cyberport_vlan_net_create: vlan_nw_prof_id not found" )
	    sys.exit( 1 )

		
    def cyberport_vxlan_net_create( self ):
	
	 # Get the network profile id first
        nw_prf_table = get_n1k_network_profiles()
	cbp_log.debug( "CyberPort_Test: nw_prf_table\n %s", nw_prf_table )	

        # Retrieve the network profile for vlan
        vxlan_nw_prof_id = get_n1k_nw_profile_id( self.vxlan_nw_prf_name, nw_prf_table )
	
	# Check that custom tenant_ids_list is populated
	if not len( self.tenant_id_list ):
	    cbp_log.warning( "cyberport_vxlan_net_create: tenant_id_list is empty" )
	    sys.exit( 1 )

	if vxlan_nw_prof_id != "":
            # Create vxlans and their subnets
	    # Please absolutely ensure that 
	    # length of self.vxlan_nw_names = length of self.vxlan_cidr_list = length of self.tenants_names
	    for vxlan_name, vxlan_cidr, vxlan_subnet_name, tenant_id in zip( self.vxlan_nw_names, self.vxlan_cidr_list, 
									self.vxlan_subnet_names, self.tenant_id_list ):
		
		self.vxlan_net_id = create_nw( vxlan_name, vxlan_nw_prof_id, tenant_id=tenant_id )
		sleep( NET_CREATE_DELAY )
            	self.vxlan_subnet_id = create_subnet( vxlan_name, vxlan_cidr, vxlan_subnet_name, tenant_id=tenant_id )
		sleep( SUBNET_CREATE_DELAY )
        else:
            cbp_log.warning( "cyberport_vxlan_net_create: vxlan_nw_prof_id not found" )
            sys.exit( 1 )

    def create_VM_cfg( self ):

	# Retreive the policy profile id 
	pp_id = get_policy_profile_id( policy_profile_name, self.pp_table )
	if pp_id == "":
	    cbp_log.warning( "policy profile id for '%s' not found. can not continue with port creation" % policy_profile_name )
	    sys.exit( 1 )

	# We need to create 100 vlan based ports for vlan-401 and 2 vxlan port for each of 50 vxlan nets
	# Create 2 vxlan ports per tenant, 1 for each VM (there are 2 VMs per tenant) by looping over
	# 2 times
 
	for i in range( 2 ):

	    # Create 2 vxlan ports per tenant, 1 for each VM (there are 2 VMs per tenant)
	    for idx, tenant_id in enumerate( self.tenant_id_list ):
	   
	    	# Create the vlan-400 based port for each tenant 
	    	vlan_port_id = create_port( self.vlan_nw_name, pp_id, tenant_id=tenant_id )
	        sleep( PORT_CREATE_DELAY )
            	if vlan_port_id != "":
                    self.vlan_ports.append( vlan_port_id )
		
		# Create the vxlan based port
	    	vx_port_id = create_port( self.vxlan_nw_names[ idx ], pp_id, tenant_id=tenant_id )
	    	sleep( PORT_CREATE_DELAY ) 
	    	
		# Add VM data to a config table
	    	vm_name = "cbpvm-%s%s" % (i, idx)	
		self.vm_boot_data[ vm_name ] = { 'tenant': tenant_id, 'vlan_port': vlan_port_id, 'vxlan_port': vx_port_id }
		cbp_log.debug( "vm_boot_cfg: %s" %  self.vm_boot_data[ vm_name ] )
	
		# Also add the data to vm names list
		self.vm_names_list.append( vm_name )


	cbp_log.debug( "CyberPort_Test: self.vm_boot_data\n %s", self.vm_boot_data )

	# Dump the vm_boot_data and vm_names_list to a file for future use
	with open( "vm_boot_data.json", 'w' ) as f:
	    json.dump( self.vm_boot_data, f )

	with open( "vm_names_list.json", 'w' ) as f:
	    json.dump( self.vm_names_list, f )


    def create_virtual_machines( self ):
	
	# Read the VM data to create VMs from json files	
	with open( "vm_boot_data.json", 'r' ) as f:
	    self.vm_boot_data = json.load( f )
	
	with open( "vm_names_list.json", 'r' ) as f:
	    self.vm_names_list = json.load( f )

	cbp_log.debug( "self.vm_boot_data: %s\n" % self.vm_boot_data )
	cbp_log.debug( "self.vm_names_list: %s\n" % self.vm_names_list )

	# Check if the users are mapped with their respective tenants
	if len( self.user_tenant_map ) == 0:
	    cbp_log.warning( "No users are associated with tenants or there are no users on the system!!" )
	    sys.exit(1)

	# Iterate over vm_boot_data dictionary
	for idx, vm_name in enumerate( self.vm_boot_data ):
	    
	    # Get the tenant name for the tenant id and the user associated with that tenant
	    tenant_id = self.vm_boot_data[ vm_name ][ 'tenant' ]
	    tenant_name = self.tenants_table[ tenant_id ]
	    user_name = self.user_tenant_map[ tenant_id ]

	    # Get the vlan and vxlan port ids
	    vlan_port = self.vm_boot_data[ vm_name ][ 'vlan_port' ]
	    vxlan_port = self.vm_boot_data[ vm_name ][ 'vxlan_port' ]

	    # Format the VM command
	    vm_cmd_part1 = "nova --os-tenant-name %s --os-username %s --os-password %s --os-auth-url=%s" \
			% ( tenant_name, user_name, self.usr_pass, self.os_auth_url )
	    vm_cmd_part2 = " boot --image %s --flavor %s --nic port-id=%s --nic port-id=%s %s" \
			% ( self.img_name, self.img_flavor, vlan_port, vxlan_port, vm_name )
	    # Concat the cmd strings
	    vm_create_cmd = vm_cmd_part1 + vm_cmd_part2

	    cbp_log.info( "VM create command\n '%s'" % vm_create_cmd )

	    try:
            	cmd_out = subprocess.check_output( vm_create_cmd, shell=True, stderr=subprocess.STDOUT )
            	lib_log.debug( "%s\n%s\n" % ( vm_create_cmd, cmd_out ))
	    	sleep( VM_CREATE_DELAY )
            except subprocess.CalledProcessError as err:
            	lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
	    	#sys.exit( 1 )
            else:
            	# If try clause succeeds then parse the cmd_out
            	for line in cmd_out.split('\n'):
                    temp = line.split('|')
                    # We need to exclude the first line of the output which can not be split on '|'
                    if len( temp ) > 1:
                        # Extract the network guid from the output
                        if temp[ 1 ].strip() == 'id':
                            vm_id = temp[ 2 ].strip()
                            lib_log.debug( "VM id: %s\n ", vm_id )
                            break
	       
	    # break for debugging purpose
	    #break

    def create_topo( self ):
	
	self.cyberport_nw_prf_create()
	self.cyberport_vlan_net_create()
    	self.cyberport_vxlan_net_create()
    	self.create_VM_cfg()
    

    
def main():

    cbp_test = CyberPort_Test()
    #cbp_test.create_topo()
    
    #cbp_test.create_virtual_machines()

    exclude_dhcp_ports = False
    clean_up_quantum_data( exclude_dhcp_ports )
    #delete_keystone_users()
    #delete_keystone_tenants()

if __name__ == '__main__':
    
    main()
    


