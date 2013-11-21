#!/usr/bin/python
import sys
sys.path.append('../lib')
import fileinput
import subprocess
import json
import logging
from os_nw_lib import *
from time import sleep


NET_CREATE_DELAY = 5
SUBNET_CREATE_DELAY = 5
PORT_CREATE_DELAY = 5
VM_CREATE_DELAY = 5

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

class dhcp_test( ):

    def __init__( self ):

        # Define network profile list by name
        self.vlan_nw_prf_name = 'cyberport-pool'

        # Define segment ranges
        self.vlan_seg_range = "402-700"

        # Define number of networks
        self.num_vlans = 240

	# Create a list of vxlan based networks names
        self.vlan_nw_names = []
        for i in range( 402, ( self.num_vlans + 402 )):
            self.vlan_nw_names.append( ( "vlan-%s" % i ) )
        cbp_log.debug( "dhcp_test: self.vlan_nw_names\n %s", self.vlan_nw_names )

        # Create a list of subnet names for vlan
        self.vlan_subnet_names = []
        for i in range( 402, ( self.num_vlans + 402 )):
            self.vlan_subnet_names.append( ( "pool-%s" % i ) )
        cbp_log.debug( "dhcp_test: self.vlan_subnet_names\n %s", self.vlan_subnet_names )

        # Create a list of vlan based cidrs
        self.vlan_cidr_list = []
        for i in range( 1, ( self.num_vlans + 1 )):
            self.vlan_cidr_list.append( ( "40.40.%s.0/24" % i ) )
        cbp_log.debug( "dhcp_test: self.vlan_cidr_list\n %s", self.vlan_cidr_list )

        # Define a place holder for vlan subnets
        self.vlan_subnet_list = []

    def cyberport_vlan_net_create( self ):

        # Get the network profile id first
        nw_prf_table = get_n1k_network_profiles()
        cbp_log.debug( "dhcp_test: nw_prf_table\n %s", nw_prf_table )

        # Retrieve the network profile for vlan
        vlan_nw_prof_id = get_n1k_nw_profile_id( self.vlan_nw_prf_name, nw_prf_table )


        if vlan_nw_prof_id != "":
            # Create vxlans and their subnets
            # Please absolutely ensure that
            # length of self.vlan_nw_names = length of self.vlan_cidr_list
            for vlan_name, vlan_cidr, vlan_subnet_name in zip( self.vlan_nw_names, self.vlan_cidr_list,
                                                                        self.vlan_subnet_names ):

                self.vlan_net_id = create_nw( vlan_name, vlan_nw_prof_id )
                sleep( NET_CREATE_DELAY )
                self.vlan_subnet_id = create_subnet( vlan_name, vlan_cidr, vlan_subnet_name )
                sleep( SUBNET_CREATE_DELAY )
        else:
            cbp_log.warning( "cyberport_vlan_net_create: vlan_nw_prof_id not found" )
            sys.exit( 1 )


def main():

    tst  = dhcp_test()
    
    tst.cyberport_vlan_net_create()

    exclude_dhcp_ports = False
    #cbp_test.clean_up_quantum_data()
    #delete_keystone_users()
    #delete_keystone_tenants()

if __name__ == '__main__':

    main()

