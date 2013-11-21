#!/usr/bin/python
import sys
sys.path.append('../../lib')
import subprocess
import json
import logging
from os_nw_lib import *
from time import sleep


NET_CREATE_DELAY    = 5
SUBNET_CREATE_DELAY = 5
PORT_CREATE_DELAY   = 2
VM_CREATE_DELAY     = 5

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

class vxlan_1k_test( ):

    def __init__( self ):

        # Define network profile list by name
        self.vxlan_nw_prf_name = 'vxlan_1000_ports'

        # Define segment ranges
        self.vxlan_seg_range = "6000-6999"

        # Define number of networks
        self.num_vxlans = 240

	# Create a list of vxlan based networks names
        self.vxlan_nw_name = "vxlan-6000"
        cbp_log.debug( "vxlan_1k_test: self.vxlan_nw_name - %s", self.vxlan_nw_name )

        # Create a list of subnet names for vxlan
        self.vxlan_subnet_names = []
        for i in range( 1, 5 ):
            self.vxlan_subnet_names.append( ( "vxpool-%s" % i ) )
        cbp_log.debug( "vxlan_1k_test: self.vxlan_subnet_names\n %s", self.vxlan_subnet_names )

        # Create a list of vxlan based cidrs
        self.vxlan_cidr_list = []
        for i in range( 1, 5 ):
            self.vxlan_cidr_list.append( ( "192.168.%s.0/24" % i ) )
        cbp_log.debug( "vxlan_1k_test: self.vxlan_cidr_list\n %s", self.vxlan_cidr_list )

	# Get the policy profiles from vsm
        self.pp_table = get_policy_profiles()
        cbp_log.debug( "vxlan_1k_test: self.pp_table\n %s", self.pp_table )

        # Number of VMs to be instantiated
        self.num_of_VMs = 500

	# Number of ports to be created
        self.num_of_ports = 1000

        # VM data table
        self.vm_cfg_data = {}

        # List of vlan ports
        self.vxlan_ports = []

        # List of VM names
        self.vm_names_list = []

        # VM image name to be used
        self.img_name = "ubuntu-image"
        self.img_flavor = "m1.small"

        # Table to hold instantiated VM information
        self.vm_table = {}

    def nw_prf_create( self ):

        # Create a n/w profile for vxlan based n/w
        self.vxlan_nw_prof_id = create_nw_profile( self.vxlan_nw_prf_name, 'vxlan', seg_range=self.vxlan_seg_range, sub_type="unicast" )


    def vxlan_net_create( self ):

        # Get the network profile id first
        nw_prf_table = get_n1k_network_profiles()
        cbp_log.debug( "vxlan_1k_test: nw_prf_table\n %s", nw_prf_table )

        # Retrieve the network profile for vxlan
        vxlan_nw_prof_id = get_n1k_nw_profile_id( self.vxlan_nw_prf_name, nw_prf_table )

	self.vxlan_net_id = create_nw( self.vxlan_nw_name, vxlan_nw_prof_id )
        sleep( NET_CREATE_DELAY )

        if vxlan_nw_prof_id != "":
            # Create vxlans and their subnets
            # Please absolutely ensure that
            # length of self.vxlan_subnet_names = length of self.vlan_cidr_list
            for vxlan_cidr, vxlan_subnet_name in zip( self.vxlan_cidr_list, self.vxlan_subnet_names ):

                self.vxlan_subnet_id = create_subnet( self.vxlan_nw_name, vxlan_cidr, vxlan_subnet_name )
                sleep( SUBNET_CREATE_DELAY )
        else:
            cbp_log.warning( "vxlan_1k_test: vxlan_nw_prof_id not found" )
            sys.exit( 1 )

    def create_ports( self ):

        # Retreive the policy profile id
        pp_id = get_policy_profile_id( policy_profile_name, self.pp_table )
        if pp_id == "":
            cbp_log.warning( "policy profile id for '%s' not found. can not continue with port creation" % policy_profile_name )
            sys.exit( 1 )

        # We need to create 1000 vxlan based ports for 1 vxlan segment.
        # For this purpose, we would need 4 subnets with 250 hosts each.

	# Create 2 vxlan ports per tenant, 1 for each VM
        for i in range( self.num_of_ports ):

            # Create the vxlan based port
            vxlan_port_id = create_port( self.vxlan_nw_name, pp_id )
	    if vxlan_port_id != "":
                self.vxlan_ports.append( vxlan_port_id )
	    sleep( PORT_CREATE_DELAY )

        cbp_log.debug( "vxlan_1k_test: self.vm_names_list\n %s", self.vm_names_list )

	# Dump the vm_boot_data and vm_names_list to a file for future use
        with open( "vm_names_list.json", 'w' ) as f:
            json.dump( self.vm_names_list, f )


    # Create VM config data to instantiate VMs later. We need to create 500 VMs each with 
    # 2 vxlan ports. Each port must be on a different subnet
    def create_vm_cfg( self ):
	
	# First get the port_info_table
	port_info_table = get_port_info_table()

	# Get the ip_address to port mappings to construct the vm data
	exclude_dhcp_ports = True
	ip_address_port_map = get_ip_addr_port_table( port_info_table, exclude_dhcp_ports )

	# Create VM names
	for i in range( self.num_of_VMs ):

            vm_name = "vm-%s" % i
            self.vm_names_list.append( vm_name )	
	
	cbp_log.debug( "vxlan_1k_test: self.vm_names_list\n %s", self.vm_names_list )

	# Get the ip addresses and sort them, so that ip addresses from different subnets
	# can be used for each vm
	ip_addr_list = ip_address_port_map.keys()
	ip_addr_list.sort()
	ip_addr_list_len = len( ip_addr_list )

	cbp_log.debug( "vxlan_1k_test: ip_addr_list\n %s", ip_addr_list )
	cbp_log.debug( "vxlan_1k_test: number of ports -  %s", ip_addr_list_len )
   
	# Create vm boot data as a dictionary in the following format
	# {vm_name:[port1, port2]}
	# Use zip function to simeltaneously assign 2 different ports to a VM
	# sorting of ip address list ensures that ports from 2 different subnets
	# are assigned to a VM
    	for vm_name, i, j in zip( self.vm_names_list, range( ip_addr_list_len/2 ), 
				range( ip_addr_list_len/2, ip_addr_list_len ) ):
		
	    self.vm_cfg_data[ vm_name ] = []	
	    self.vm_cfg_data[ vm_name ].append( ip_address_port_map[ ip_addr_list[ i ] ] )
	    cbp_log.debug( "vxlan_1k_test: self.vm_cfg_data[ %s ] -  %s" % ( vm_name, self.vm_cfg_data[ vm_name ] ))
	    self.vm_cfg_data[ vm_name ].append( ip_address_port_map[ ip_addr_list[ j ] ] )
	    cbp_log.debug( "vxlan_1k_test: self.vm_cfg_data[ %s ] -  %s" % ( vm_name, self.vm_cfg_data[ vm_name ] ))
	

	cbp_log.debug( "vxlan_1k_test: self.vm_cfg_data - %s", self.vm_cfg_data )
	
	# Dump the vm_boot_data and vm_names_list to a file for future use
        with open( "vm_cfg_data.json", 'w' ) as f:
            json.dump( self.vm_cfg_data, f )


	# Create Virtual Machines
	for vm_name in self.vm_cfg_data:

	    # First get the ports for this VM
	    port1 = self.vm_cfg_data[ vm_name ][ 0 ]
	    port2 = self.vm_cfg_data[ vm_name ][ 1 ]
	
	    # Format the VM command
            vm_create_cmd = "nova boot --image %s --flavor %s --nic port-id=%s --nic port-id=%s %s" \
                        % ( self.img_name, self.img_flavor, port1, port2, vm_name )

            cbp_log.info( "VM create command\n '%s'" % vm_create_cmd )
	    
	    # Spawn virtual machines
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

    def create_topo( self ):

        #self.nw_prf_create()
        #self.vxlan_net_create()
        #self.create_ports()

        self.create_vm_cfg()


def main():

    tst  = vxlan_1k_test()
    
    #tst.create_topo()

    exclude_dhcp_ports = False
    clean_up_quantum_data( exclude_dhcp_ports )

if __name__ == '__main__':

    main()

