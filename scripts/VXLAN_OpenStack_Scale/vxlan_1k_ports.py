#!/usr/bin/python
import sys
sys.path.append('../../lib')
import subprocess
import json
import logging
from os_nw_lib import *
from time import sleep


NET_CREATE_DELAY    = 2
SUBNET_CREATE_DELAY = 2
PORT_CREATE_DELAY   = 2
VM_CREATE_DELAY     = 3

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

class vxlan_seg_test( ):

    def __init__( self ):

        # Define network profile list by name
        self.vxlan_nw_prf_name = 'vxlan_300'

        # Define segment ranges
        self.vxlan_seg_range = "6000-6999"

        # Define number of networks
        self.num_vxlans = 300

	self.vxlan_nw_names = []
        for i in range( 7000, ( self.num_vxlans + 7000 )):
            self.vxlan_nw_names.append( ( "vxlan-%s" % i ) )
        cbp_log.debug( "vxlan_seg_test: self.vxlan_nw_names\n %s", self.vxlan_nw_names )

        # Create a list of subnet names for vxlan
        self.vxlan_subnet_names = []
        for i in range( 7000, ( self.num_vxlans + 7000 )):
            self.vxlan_subnet_names.append( ( "vxpool-%s" % i ) )
        cbp_log.debug( "vxlan_seg_test: self.vxlan_subnet_names\n %s", self.vxlan_subnet_names )

        # Create a list of vxlan based cidrs for 300 subnets
        self.vxlan_cidr_list = []
	self.subnet_mask_1 = 255
	self.subnet_mask_2 = 45
        for i in range( self.subnet_mask_1 ):
            self.vxlan_cidr_list.append( ( "20.20.%s.0/24" % i ) )
	for i in range( self.subnet_mask_2 ):
	    self.vxlan_cidr_list.append( ( "30.30.%s.0/24" % i ) )
        cbp_log.debug( "vxlan_seg_test: self.vxlan_cidr_list\n %s", self.vxlan_cidr_list )

        # Define a place holder for vxlan subnets
        self.vxlan_subnet_list = []

	# Get the policy profiles from vsm
        self.pp_table = get_policy_profiles()
        cbp_log.debug( "vxlan_seg_test: self.pp_table\n %s", self.pp_table )
	
	self.num_of_ports = 1000
	self.vxlan_ports = []
	
    def nw_prf_create( self ):

        # Create a n/w profile for vxlan based n/w
        self.vxlan_nw_prof_id = create_nw_profile( self.vxlan_nw_prf_name, 'vxlan', seg_range=self.vxlan_seg_range, sub_type="unicast" )


    def vxlan_net_create( self ):

        # Get the network profile id first
        nw_prf_table = get_n1k_network_profiles()
        cbp_log.debug( "vxlan_seg_test: nw_prf_table\n %s", nw_prf_table )

        # Retrieve the network profile for vxlan
        vxlan_nw_prof_id = get_n1k_nw_profile_id( self.vxlan_nw_prf_name, nw_prf_table )

        if vxlan_nw_prof_id != "":
            # Create vxlans and their subnets
            # Please absolutely ensure that
            # length of self.vxlan_subnet_names = length of self.vlan_cidr_list
            for vxlan_name, vxlan_cidr, vxlan_subnet_name in zip( self.vxlan_nw_names, self.vxlan_cidr_list, self.vxlan_subnet_names ):

		self.vxlan_net_id = create_nw( vxlan_name, vxlan_nw_prof_id )
                sleep( NET_CREATE_DELAY )
                self.vxlan_subnet_id = create_subnet( vxlan_name, vxlan_cidr, vxlan_subnet_name )
                sleep( SUBNET_CREATE_DELAY )
        else:
            cbp_log.warning( "vxlan_seg_test: vxlan_nw_prof_id not found" )
            sys.exit( 1 )

    def create_ports( self ):

        # Retreive the policy profile id
        pp_id = get_policy_profile_id( policy_profile_name, self.pp_table )
        if pp_id == "":
            cbp_log.warning( "policy profile id for '%s' not found. can not continue with port creation" % policy_profile_name )
            sys.exit( 1 )

        # We need to create 1000 vxlan based ports for 1000 vxlan networks.
	# Create 1 port per vxlan
	for i in range( 2 ):
	    for vxlan_name in self.vxlan_nw_names:

        	# Create the vxlan based port
                vxlan_port_id = create_port( vxlan_name, pp_id )
	        if vxlan_port_id != "":
                    self.vxlan_ports.append( vxlan_port_id )
	        sleep( PORT_CREATE_DELAY )

	cbp_log.info( "Number of ports created '%s'" % len( self.vxlan_ports ) )


    def create_topo( self ):

    	self.nw_prf_create()
        self.vxlan_net_create()
        self.create_ports()



def main():

    tst  = vxlan_seg_test()
    
    tst.create_topo()

    exclude_dhcp_ports = False
    #clean_up_quantum_data( exclude_dhcp_ports )

if __name__ == '__main__':

    main()

