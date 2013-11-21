#!/usr/bin/python
#--------------------------------------------------------------
# Script with functions to automate many OpenStack networking
# commands. Use this module to import in your script
#
# 			!ASSUMPTIONS!
# 1. Data and dhcp port profiles have been already created 
#    on the VSM 
#--------------------------------------------------------------

import sys
from time import sleep
import subprocess
import math
import logging

# Initialize logging
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(name)s - %(message)s', level=logging.WARNING)
lib_log = logging.getLogger( __name__ )

#lib_log.setLevel(logging.INFO)
lib_log.setLevel(logging.DEBUG)

# Global data
VSM_RESP_DELAY 		= 15
PORT_DELETE_DELAY 	= 2
NET_DELETE_DELAY 	= 2
USER_DELETE_DELAY	= 2
TENANT_DELETE_DELAY	= 2

# Create network profile depending on various parameters
def create_nw_profile( nw_prof_name, seg_type, **kwargs ):

    # Reference dictionary for specifying cmd options
    # There are many optional arguments available for 
    # quantum cisco-network-profile-create command. Add more to the
    # reference dictionary as needed
    nw_prf_ref_dict = { 'tenant_id': "--tenant-id", 'sub_type': "--sub_type",
			'seg_range': "--segment_range", 'phys_nw': "--physical_network"}

    cmd = "quantum cisco-network-profile-create %s %s" % (nw_prof_name, seg_type)

    # Build the cmd string using ref dict above
    for arg, value in kwargs.items():

	cmd = cmd + " " + "".join( "%s %s" % ( nw_prf_ref_dict[ arg ], value )) 
	
    lib_log.info( cmd )

    try:
        cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
        lib_log.debug( "%s\n%s\n" % ( cmd, cmd_out ))
    except subprocess.CalledProcessError as err:
        lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
        sys.exit(1)

    for line in cmd_out.split('\n'):
        temp = line.split('|')
        # We need to exclude the first line of the output which can not be split on '|'
        if len( temp ) > 1:
            # Extract the network guid from the output
            if temp[ 1 ].strip() == 'id':
                nw_prf_id = temp[ 2 ].strip()
                lib_log.info( "nw profile id:\n%s\n ", nw_prf_id )
                break

        else:
            continue

    lib_log.info( "nw profile id:\n%s\n ", nw_prf_id )
    return nw_prf_id


def get_policy_profiles():

    # Dictionary to maintain parsed policy profile guids and their names
    pp_table = {}

    try:
        cmd_out = subprocess.check_output( "quantum cisco-policy-profile-list", shell=True, stderr=subprocess.STDOUT )
        lib_log.debug( "quantum cisco-policy-profile-list\n%s\n" % cmd_out )
    except subprocess.CalledProcessError as err:
        lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
        sys.exit(1)

    for line in cmd_out.split('\n'):
        temp = line.split('|')
        # We need to exclude the first line of the output which can not be split on '|'
        if len( temp ) > 1:
            # Extract the policy profile id and its name and add it into a dict
	    pp_guid = temp[ 1 ].strip( )
            pp_name = temp[ 2 ].strip( )
	    if pp_guid != 'id':
		pp_table[ pp_guid ] = pp_name
		
        else:
            continue

    lib_log.info( "Policy Profile Table:\n%s\n ", pp_table )
    return pp_table

# Given a policy name, this function will return the policy id
def get_policy_profile_id( policy_name, policy_table ):

    policy_id = ""
    
    # policy table must be a dict object created through get_policy_profiles
    if not isinstance( policy_table, dict ):
	lib_log.warning( "policy_table is not 'dict' object")
	return policy_id

    for key, value in policy_table.items():
	#lib_log.debug( "%s, %s" % (key, value) )
	if value == policy_name:
	    policy_id = key
	    lib_log.info( "policy_id: %s" % policy_id )
	    break
	    
    return policy_id	


def get_n1k_network_profiles():

    # Dictionary to maintain parsed network profile guids and their names
    nw_prf_table = {}

    try:
        cmd_out = subprocess.check_output( "quantum cisco-network-profile-list", shell=True, stderr=subprocess.STDOUT )
        lib_log.debug( "quantum cisco-network-profile-list\n%s\n" % cmd_out )
    except subprocess.CalledProcessError as err:
        lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
        sys.exit(1)

    for line in cmd_out.split('\n'):
        temp = line.split('|')
        # We need to exclude the first line of the output which can not be split on '|'
        if len( temp ) > 1:
            # Extract the policy profile id and its name and add it into a dict
            np_guid = temp[ 1 ].strip( )
            np_name = temp[ 2 ].strip( )
            if np_guid != 'id':
                nw_prf_table[ np_guid ] = np_name

        else:
            continue

    lib_log.info( "Policy Profile Table:\n%s\n ", nw_prf_table )
    return nw_prf_table

# Given an n1k network policy name, this function will return the policy id
def get_n1k_nw_profile_id( nw_prf_name, nw_prf_table ):

    nw_prf_id = ""

    # policy table must be a dict object created through get_n1k_network_profiles
    if not isinstance( nw_prf_table, dict ):
        lib_log.warning( "nw_prf_table is not 'dict' object")
        return nw_prf_id

    for key, value in nw_prf_table.items():
        #lib_log.debug( "%s, %s" % (key, value) )
        if value == nw_prf_name:
            nw_prf_id = key
            lib_log.info( "nw_prf_id: %s" % nw_prf_id )
            return nw_prf_id


# Returns a list of all quantum n1k network profile ids for quantum networks on the system
def get_nw_prf_ids( nw_prf_table ):

    nw_prf_id_list = []

    # nw_prf_table  must be a dict object created through get_n1k_network_profiles
    if not isinstance( nw_prf_table, dict ):
        lib_log.warning( "nw_prf_table is not 'dict' object")
        return nw_prf_id_list

    # Get all the nw_prf_id from the nw_prf_table
    for nw_prf_id in nw_prf_table:
        # If dhcp ports have to be excluded then just return all the port ids
        nw_prf_id_list.append( nw_prf_id )

    lib_log.info( "Quantum network profile id list:\n %s" % nw_prf_id_list )
    return nw_prf_id_list


# Function to delete quantum network profiles
def delete_n1k_nw_profiles( ):

    quantum_nw_prf_list = []

    # First get the net profile ids
    nw_prf_table = get_n1k_network_profiles()

    if len( nw_prf_table ) == 0:
        lib_log.info( "nw_prf_table is perhaps empty. No network profiles to delete on the system" )
        return

    # Get the list of network profiles
    quantum_nw_prf_list = get_nw_prf_ids( nw_prf_table )
    if len( quantum_nw_prf_list ) == 0:
        lib_log.info( "quantum_nw_prf_list is empty. No network profiles to delete on the system" )
        return

    # Delete ports one by one
    for nw_prf in quantum_nw_prf_list:

        # Set the number of attempts
        num_attempts = 2
        cmd = "quantum cisco-network-profile-delete %s" % nw_prf

        # Due to a known issue with VSM, sometimes profile delete fails, we retry after 30
        # seconds
        while num_attempts >= 1 :

            # Execute net-delete command
            try:
                lib_log.info( "\nDeleting n1k network profile %s" % nw_prf )
                cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
                lib_log.debug( "%s\n%s" % ( cmd, cmd_out ))
                sleep( NET_DELETE_DELAY )
                break

            except subprocess.CalledProcessError as err:
                lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
                num_attempts = num_attempts - 1
                if num_attempts != 0:
                    lib_log.warning( "Retrying after waiting for %s seconds.." % VSM_RESP_DELAY )
                    sleep( VSM_RESP_DELAY )
            else:
                # If try clause succeeds then parse the cmd_out
                if cmd_out.count( "Deleted network_profile" ) == 1:
                    lib_log.info( "quantum n1k network profile %s deleted" % nw_prf )
                else:
                    lib_log.warning( "quantum n1k network profile %s may not have been deleted. Check quantum cisco-network-profile-list output" % nw_prf )
        else:
            lib_log.warning( "Retrying quantum n1k network profile delete for %s did not work!" % nw_prf )

 

# Function to create a quantum network
def create_nw( nw_name, nw_prf_id, **kwargs ):

    net_id = ""

    # Set the number of attempts
    num_attempts = 2

    # Reference dictionary for specifying cmd options
    # There are many optional arguments available for
    # quantum net-create command. Add more to the
    # reference dictionary as needed
    nw_create_ref_dict = { 'tenant_id': "--tenant-id", 'admin_state': "--admin-state-down",
                        'shared': "--shared"}

    cmd = "quantum net-create %s --n1kv:profile_id %s" % ( nw_name, nw_prf_id )

    # Build the cmd string for optional args using ref dict above
    for arg, value in kwargs.items():

        cmd = cmd + " " + "".join( "%s %s" % ( nw_create_ref_dict[ arg ], value ))

    lib_log.info( cmd )
    
    # Due to a known issue with VSM, sometimes net-delete fails, we retry after 30
    # seconds
    while num_attempts >= 1 :   
        # Execute the command 
    	try:
            cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
            lib_log.debug( "%s\n%s\n" % ( cmd, cmd_out ))
	except subprocess.CalledProcessError as err:
            lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
            num_attempts = num_attempts - 1
            if num_attempts != 0:
                lib_log.warning( "Retrying after waiting for %s seconds.." % VSM_RESP_DELAY )
	    	sleep( VSM_RESP_DELAY )
        else:
	    # If try clause succeeds then parse the cmd_out
	    for line in cmd_out.split('\n'):
	        temp = line.split('|')
                # We need to exclude the first line of the output which can not be split on '|'
                if len( temp ) > 1:
	            # Extract the network guid from the output
        	    if temp[ 1 ].strip() == 'id':
                        net_id = temp[ 2 ].strip()
                        lib_log.debug( "Net id:\n%s\n ", net_id )
                        break
    	
	    # Break out of the while loop
            break
    
    else:
	# Retries did not work, cant do much
        lib_log.warning( "Retrying quantum network create for %s did not work!. Returning from create_net" % nw_name )

    lib_log.info( "Net id:\n%s\n ", net_id )
    return net_id

def get_quantum_networks():

    # Dictionary to maintain parsed network guids and their names
    q_nw_table = {}

    try:
        cmd_out = subprocess.check_output( "quantum net-list", shell=True, stderr=subprocess.STDOUT )
        lib_log.debug( "quantum net-list\n%s\n" % cmd_out )
    except subprocess.CalledProcessError as err:
        lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
        sys.exit(1)

    for line in cmd_out.split('\n'):
        temp = line.split('|')
        # We need to exclude the first line of the output which can not be split on '|'
        if len( temp ) > 1:
            # Extract the policy profile id and its name and add it into a dict
            net_guid = temp[ 1 ].strip( )
            net_name = temp[ 2 ].strip( )
            if net_guid != 'id':
                q_nw_table[ net_guid ] = net_name

        else:
            continue

    lib_log.info( "quantum networks Table:\n%s\n ", q_nw_table )
    return q_nw_table

# Given a quantum network name, this function will return the net id
def get_quantum_net_id( net_name, q_nw_table ):

    net_id = ""

    # quantum network table must be a dict object created through get_quantum_networks
    if not isinstance( q_nw_table, dict ):
        lib_log.warning( "q_nw_table is not 'dict' object")
        return net_id

    for key, value in q_nw_table.items():
       # lib_log.debug( "%s, %s" % (key, value) )
        if value == net_name:
            net_id = key
            lib_log.info( "net_id: %s" % net_id )
            return net_id

# Returns a list of all quantum net ids for quantum networks on the system
def get_net_ids( q_net_table ):

    q_net_id_list = []

    # q_net_table  must be a dict object created through get_quantum_networks
    if not isinstance( q_net_table, dict ):
        lib_log.warning( "q_net_table is not 'dict' object")
        return q_net_id_list

    # Get all the net_id from the q_net_table
    for net_id in q_net_table:
        # If dhcp ports have to be excluded then just return all the port ids
	q_net_id_list.append( net_id )

    lib_log.info( "Quantum net id list:\n %s" % q_net_id_list )
    return q_net_id_list


# Function to delete the created quantum networks
def delete_quantum_networks(  ):

    quantum_net_list = []

    # First get the net ids
    q_net_table = get_quantum_networks()

    if len( q_net_table ) == 0:
        lib_log.info( "q_net_table is perhaps empty. No networks to delete on the system" )
        return

    # Get the list of networks
    quantum_net_list = get_net_ids( q_net_table )
    if len( quantum_net_list ) == 0:
    	lib_log.info( "quantum_net_list is empty. No networks to delete on the system" )
        return

    # Delete ports one by one
    for net in quantum_net_list:
	
	# Set the number of attempts
        num_attempts = 2
        cmd = "quantum net-delete %s" % net

        # Due to a known issue with VSM, sometimes net-delete fails, we retry after 30
        # seconds
        while num_attempts >= 1 :

            # Execute net-delete command
            try:
                lib_log.info( "\nDeleting quantum network %s" % net )
                cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
                lib_log.debug( "%s\n%s" % ( cmd, cmd_out ))
                sleep( NET_DELETE_DELAY )
                break
	
	    except subprocess.CalledProcessError as err:
                lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
		num_attempts = num_attempts - 1
            	if num_attempts != 0:
                    lib_log.warning( "Retrying after waiting for %s seconds.." % VSM_RESP_DELAY )
                    sleep( VSM_RESP_DELAY )
            else:
                # If try clause succeeds then parse the cmd_out
                if cmd_out.count( "Deleted network" ) == 1:
                    lib_log.info( "quantum network %s deleted" % net )
                else:
                    lib_log.warning( "quantum network %s may not have been deleted. Check quantum net-list output" % net )
        else:
            lib_log.warning( "Retrying quantum network delete for %s did not work!" % net )


def create_subnet( nw_name, cidr, subnet_name, **kwargs ):

    subnet_id = ""    

    # Set the number of attempts
    num_attempts = 2

    # Reference dictionary for specifying cmd options
    # There are many optional arguments available for
    # quantum subnet-create command. Add more to the
    # reference dictionary as needed
    subnet_create_ref_dict = { 'tenant_id': "--tenant-id", 'ip_ver': "--ip-version", 
		'dns_servers': "--dns-nameserver", 'gateway': "--gateway",
		'alloc_pool': "--allocation-pool", 'disable_dhcp': "--disable-dhcp" }

    cmd = "quantum subnet-create %s %s --name %s" % ( nw_name, cidr, subnet_name )

    # Build the cmd string for optional args using ref dict above
    for arg, value in kwargs.items():

        cmd = cmd + " " + "".join( "%s %s" % ( subnet_create_ref_dict[ arg ], value ))

    lib_log.info( cmd )
    
    # Due to a known issue with VSM, sometimes net-delete fails, we retry after 30
    # seconds
    while num_attempts >= 1 :
	
    	# Execute the command
    	try:
            cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
            lib_log.debug( "%s\n%s\n" % ( cmd, cmd_out ))
    	except subprocess.CalledProcessError as err:
            lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
            num_attempts = num_attempts - 1
            if num_attempts != 0:
                lib_log.warning( "Retrying after waiting for %s seconds.." % VSM_RESP_DELAY )
		sleep( VSM_RESP_DELAY )
        else:
	    # If try clause succeeds then parse the cmd_out
	    for line in cmd_out.split('\n'):
        	temp = line.split('|')
        	# We need to exclude the first line of the output which can not be split on '|'
        	if len( temp ) > 1:
            	    # Extract the subnet guid from the output
            	    if temp[ 1 ].strip() == 'id':
                        subnet_id = temp[ 2 ].strip()
                        lib_log.debug( "Subnet id:\n%s\n ", subnet_id )
                        break
	
	    # Break out of the while loop
            break

    else:
	# Retries did not work, cant do much
        lib_log.warning( "Retrying quantum subnet-create for %s did not work!. Returning from create_subnet" % subnet_name )

    lib_log.info( "Subnet id:\n%s\n ", subnet_id )
    return subnet_id

def get_quantum_subnets():

    # Dictionary to maintain parsed subnet guids, their names, cidr info and allocation pool infor
    q_subnet_table = {}

    try:
        cmd_out = subprocess.check_output( "quantum subnet-list", shell=True, stderr=subprocess.STDOUT )
        lib_log.debug( "quantum subnet-list\n%s\n" % cmd_out )
    except subprocess.CalledProcessError as err:
        lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
        sys.exit(1)

    for line in cmd_out.split('\n'):
        temp = line.split('|')
        # We need to exclude the first line of the output which can not be split on '|'
        if len( temp ) > 1:
            # Extract the subnet id,its name, cidr info and allocation pool
            subnet_guid = temp[ 1 ].strip( )
            if subnet_guid != 'id':
		subnet_name = temp[ 2 ].strip( )
            	subnet_cidr = temp[ 3 ].strip( )
            	subnet_alloc_pool =  eval( temp[ 4 ].strip( ) )
                q_subnet_table[ subnet_guid ] = {'name':subnet_name, 'cidr':subnet_cidr, 'alloc_pool':subnet_alloc_pool}

        else:
            continue

    lib_log.info( "quantum subnets Table:\n%s\n ", q_subnet_table )
    return q_subnet_table

# Given a quantum subnet name, this function will return the subnet id
def get_quantum_subnet_id( subnet_name, q_subnet_table ):

    subnet_id = ""

    # quantum subnet table must be a dict object created through get_quantum_subnets
    if not isinstance( q_subnet_table, dict ):
        lib_log.warning( "q_subnet_table is not 'dict' object")
        return net_id

    for key, value in q_subnet_table.items():
       # lib_log.debug( "%s, %s" % (key, value) )
        if value[ 'name' ] == subnet_name:
            subnet_id = key
            lib_log.info( "subnet_id: %s" % subnet_id )
            return subnet_id

# Returns a list of all quantum subnet ids for quantum networks on the system
def get_subnet_ids( q_subnet_table ):

    q_subnet_id_list = []

    # q_net_table  must be a dict object created through get_quantum_networks
    if not isinstance( q_subnet_table, dict ):
        lib_log.warning( "q_subnet_table is not 'dict' object")
        return q_subnet_id_list

    # Get all the subnet_id from the q_subnet_table
    for subnet_id in q_subnet_table:
        # Just iterate and append to the list
        q_subnet_id_list.append( subnet_id )

    lib_log.info( "Quantum subnet id list:\n %s" % q_subnet_id_list )
    return q_subnet_id_list

# Function to delete the created quantum networks
def delete_quantum_subnets(  ):

    quantum_subnet_list = []

    # First get the subnet ids
    q_subnet_table = get_quantum_subnets()

    if len( q_subnet_table ) == 0:
        lib_log.info( "q_subnet_table is perhaps empty. No subnets to delete on the system" )
        return

    # Get the list of networks
    quantum_subnet_list = get_subnet_ids( q_subnet_table )
    if len( quantum_subnet_list ) == 0:
        lib_log.info( "quantum_subnet_list is empty. No subnets to delete on the system" )
        return

    # Delete ports one by one
    for subnet in quantum_subnet_list:

        cmd = "quantum subnet-delete %s" % subnet

	# Set the number of attempts
        num_attempts = 2

        # Due to a known issue with VSM, sometimes subnet-delete fails, we retry after 30
        # seconds
        while num_attempts >= 1 :

            # Execute net-delete command
            try:
                lib_log.info( "\nDeleting quantum subnet %s" % subnet )
                cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
                lib_log.debug( "%s\n%s" % ( cmd, cmd_out ))
                sleep( NET_DELETE_DELAY )
            except subprocess.CalledProcessError as err:
                lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
		num_attempts = num_attempts - 1
            	if num_attempts != 0:
                    lib_log.warning( "Retrying after waiting for %s seconds.." % VSM_RESP_DELAY )
                    sleep( VSM_RESP_DELAY )
            else:
                # If try clause succeeds then parse the cmd_out
                if cmd_out.count( "Deleted subnet" ) == 1:
                    lib_log.info( "quantum subnet %s deleted" % subnet )
		else:
                    lib_log.warning( "quantum subnet %s may not have been deleted. Check quantum subnet-list output" % subnet )
		break
        else:
            lib_log.warning( "Retrying quantum subnet delete for %s did not work!. Continuing with remaining subnets" % subnet )


def create_port( nw_name, pp_prf_id, **kwargs ):
    
    port_id = ""
    num_attempts = 2

    # Reference dictionary for specifying cmd options
    # There are many optional arguments available for
    # quantum port-create command. Add more to the
    # reference dictionary as needed
    port_create_ref_dict = { 'tenant_id': "--tenant-id", 'port_name':"--name", 'admin_state': "--admin-state-down",
                           'mac_addr': "--mac-address", 'fixed_ip':"--fixed-ip"}

    cmd = "quantum port-create %s --n1kv:profile_id %s" % ( nw_name, pp_prf_id )

    # Build the cmd string for optional args using ref dict above
    for arg, value in kwargs.items():

        cmd = cmd + " " + "".join( "%s %s" % ( port_create_ref_dict[ arg ], value ))

    lib_log.info( cmd )
    
    # Due to a known issue with VSM, sometimes port-create fails, we retry after 30
    # seconds 
    while num_attempts >= 1 :

	# Execute port-create command
	try:
            cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
            lib_log.debug( "%s\n%s\n" % ( cmd, cmd_out ))
	except subprocess.CalledProcessError as err:
            lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
	    num_attempts = num_attempts - 1
	    if num_attempts != 0:
		lib_log.warning( "Retrying after waiting for %s seconds.." % VSM_RESP_DELAY )
	    	sleep( VSM_RESP_DELAY )
	else:
	    # If try clause succeeds then parse the cmd_out 
	    for line in cmd_out.split('\n'):
		temp = line.split('|')
	        # We need to exclude the first line of the output which can not be split on '|'
        	if len( temp ) > 1:
	            # Extract the network guid from the output
	            if temp[ 1 ].strip() == 'id':
	                port_id = temp[ 2 ].strip()
	                lib_log.debug( "Port id:\n%s\n ", port_id )
	                break

	    # Break out of the while loop
	    break
    else:
	# Retries did not work, cant do much
	lib_log.warning( "Retry did not work! returning from create_port" )

    lib_log.info( "Port id:\n%s\n ", port_id )
    return port_id


# Dictionary to maintain parsed port_ids, subnet and ip_address information
def get_port_info_table():

    # Dictionary to maintain parsed port_ids, subnet and ip_address information
    port_info_table = {}

    try:
        cmd_out = subprocess.check_output( "quantum port-list", shell=True, stderr=subprocess.STDOUT )
        lib_log.debug( "quantum port-list\n%s\n" % cmd_out )
    except subprocess.CalledProcessError as err:
        lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
        sys.exit(1)

    for line in cmd_out.split('\n'):
        temp = line.split('|')
        # We need to exclude the first line of the output which can not be split on '|'
        if len( temp ) > 1:
            # Extract the port id as key, subnet id and ip address of the port as value
	    #  into the table
            p_guid = temp[ 1 ].strip( )
            if p_guid != 'id':
		subnet_ip_info = eval( temp[ 4 ].strip( ) )
                port_info_table[ p_guid ] = subnet_ip_info

        else:
            continue

    lib_log.debug( "quantum port, subnet and ip Table:\n%s\n ", port_info_table )
    return port_info_table


# Returns a list of quantum ports. Use exclude_dhcp_ports flag
# to specify whether you want dhcp port ids as well.
# Default is to exclude dhcp port ids
def get_port_ids( port_info_table, exclude_dhcp_ports=True ):

    port_id_list = []

    if not isinstance( exclude_dhcp_ports, bool ):
	lib_log.warning( "exclude_dhcp_ports must be 'bool' type" )
	lib_log.warning( "setting it to default value 'True'" )
	exclude_dhcp_ports = True

    # port_id_table  must be a dict object created through get_quantum_networks
    if not isinstance( port_info_table, dict ):
        lib_log.warning( "port_info_table is not 'dict' object")
        return port_id_list

    for port_id, subnet_ip_info in port_info_table.items():
	# If dhcp ports have to be excluded then just return all the port ids 	
	if not exclude_dhcp_ports:
	    port_id_list.append( port_id )
	# Else exclude dhcp ports from the list
	else:
	    # From value, extract the ip address and check if its 
	    # a dhcp address (x.x.x.2)
	    ip_addr = subnet_ip_info[ 'ip_address'].split('.')
	    # If its not a dhcp port, then add the port id to the list
	    if int( ip_addr[ 3 ] ) != 2:
		port_id_list.append( port_id )
	    else:
		continue
    
    lib_log.info( "Port id list:\n %s" % port_id_list )
    return port_id_list


# Dictionary to maintain ip_address (of a port) and its associated port mapping
# !! In case you are using multiple subnets with same ip address range (since it is 
# permitted my quantum using ip netns) this funtion will not work as expected!!
def get_ip_addr_port_table( port_info_table, exclude_dhcp_ports=True ):

    ip_addr_port_table = {}

    if not isinstance( exclude_dhcp_ports, bool ):
        lib_log.warning( "exclude_dhcp_ports must be 'bool' type" )
        lib_log.warning( "setting it to default value 'True'" )
        exclude_dhcp_ports = True

    # port_id_table  must be a dict object created through get_quantum_networks
    if not isinstance( port_info_table, dict ):
        lib_log.warning( "port_info_table is not 'dict' object")
        return ip_addr_port_table

    # Get the port list
    port_list = get_port_ids( port_info_table, exclude_dhcp_ports )

    for port_id in port_list:
	
	ip_address = port_info_table[ port_id ][ 'ip_address' ]
	ip_addr_port_table[ ip_address ] = port_id
 
    lib_log.debug( "quantum ip address and port Table:\n%s\n ", ip_addr_port_table )
    return ip_addr_port_table

    

# Function to delete the created quantum ports	    
def delete_quantum_ports( exclude_dhcp_ports=True ):

    port_id_list = []

    # First get the port table
    port_info_table = get_port_info_table()

    if len( port_info_table ) == 0:
	lib_log.info( "port_info_table is perhaps empty. No ports to delete on the system" )
	return
    
    # Get the list of ports
    port_id_list = get_port_ids( port_info_table, exclude_dhcp_ports )
    if len( port_id_list ) == 0:
	if exclude_dhcp_ports:
	    lib_log.info( "port_id_list is empty. No ports to delete on the system" )
	    lib_log.info( "However since exclude_dhcp_ports is True, dhcp ports were not deleted" )
	    lib_log.info( "If you wish to delete dhcp ports, set exclude_dhcp_ports to False" \
			  " and run the script again" )
	else:
	    lib_log.info( "port_id_list is empty. No ports to delete on the system" )

        return

    # Delete ports one by one
    for port in port_id_list:
	
	# Set the number of attempts
	num_attempts = 2

	cmd = "quantum port-delete %s" % port

	# Due to a known issue with VSM, sometimes port-delete fails, we retry after 30
    	# seconds
    	while num_attempts >= 1 :

      	    # Execute port-delete command
            try:
		lib_log.info( "\nDeleting port %s" % port )
                cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
            	lib_log.debug( "%s\n%s" % ( cmd, cmd_out ))
		sleep( PORT_DELETE_DELAY )
            except subprocess.CalledProcessError as err:
            	lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
 	   	num_attempts = num_attempts - 1	
		if num_attempts != 0:
		    lib_log.warning( "Retrying after waiting for %s seconds.." % VSM_RESP_DELAY )
            	    sleep( VSM_RESP_DELAY )
            else:
            	# If try clause succeeds then parse the cmd_out
		if cmd_out.count( "Deleted port" ) == 1:
		    lib_log.info( "Port %s deleted\n" % port )
 		else:
		    lib_log.warning( "Port %s may not have been deleted. Check quantum port-list output\n" % port )
		break
     	else:
	    lib_log.warning( "Retrying port delete for %s did not work!. Continuing with remaining ports\n" % port )
	


def get_keystone_tenants():
    # Returns the keystone tenant ids and names on the system in a python dict

    tenant_table = {}

    try:
        cmd_out = subprocess.check_output( "keystone tenant-list", shell=True, stderr=subprocess.STDOUT )
        lib_log.debug( "keystone tenant-list\n%s\n" % cmd_out )
    except subprocess.CalledProcessError as err:
        lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
        sys.exit(1)

    for line in cmd_out.split('\n'):
        temp = line.split('|')
        # We need to exclude the first line of the output which can not be split on '|'
        if len( temp ) > 1:
	    # Extract the tenant id and tenant name
	    tenant_id =  temp[ 1 ].strip( )
	    tenant_name = temp[ 2 ].strip( )

            # From the list we need to remove 'id' title
            if tenant_id != 'id':
                tenant_table[ tenant_id ] = tenant_name
	
        else:
            continue

    lib_log.info( "Tenant table:\n%s\n ", tenant_table )
    return tenant_table

# Given a keystone tenant name, this function will return its id
def get_tenant_id( tenant_name, tenant_table ):

    tenant_id = ""

    # tenant table must be a dict object created through get_keystone_tenants
    if not isinstance( tenant_table, dict ):
        lib_log.warning( "tenant_table is not 'dict' object")
        return tenant_id

    for key, value in tenant_table.items():
        #lib_log.debug( "%s, %s" % (key, value) )
        if value == tenant_name:
            tenant_id = key
            lib_log.info( "tenant_id: %s" % tenant_id )
            return tenant_id


def get_custom_tenant_names( tenant_table ):
    # Returns the user created keystone tenants (excludes 'admin' and services') 
    # on the system as a python list
    
    tenant_names_list = []

    # tenant table must be a dict object created through get_keystone_tenants
    if not isinstance( tenant_table, dict ):
        lib_log.warning( "tenant_table is not 'dict' object")
        return tenant_names_list

    for key, value in tenant_table.items():
        lib_log.debug( "Inside get_custom_tenant_names:\n%s, %s" % (key, value) )
        if value != 'admin' and value != 'services':
            tenant_names_list.append( value )
          
    tenant_names_list.sort()
    lib_log.info( "tenant_names_list: %s" % tenant_names_list )
    return tenant_names_list


# Returns a list of tenant ids for sorted tenant names list
def get_custom_tenant_ids( tenant_table ):

    # Returns the tenant ids for user created keystone tenants
    # (excludes 'admin' and services') on the system as a python list

    tenant_ids_list = []
    tenant_names_list = []

    # tenant table must be a dict object created through get_keystone_tenants
    if not isinstance( tenant_table, dict ):
        lib_log.warning( "tenant_table is not 'dict' object")
        return tenant_ids_list
   
    lib_log.debug("Inside get_custom_tenant_ids\n%s", tenant_table) 

    # First get the sorted list of tenant names
    tenant_names_list = get_custom_tenant_names( tenant_table )
    
    for tenant_name in tenant_names_list:
	tenant_id = get_tenant_id( tenant_name, tenant_table )
	tenant_ids_list.append( tenant_id )
	
    return tenant_ids_list


# Returns a sorted list of user created keystone users
def get_keystone_users():

    user_list = []

    try:
        cmd_out = subprocess.check_output( "keystone user-list", stderr=subprocess.STDOUT, shell=True )
        lib_log.debug( "keystone user-list\n%s\n" % cmd_out )
    except subprocess.CalledProcessError as err:
        lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
        sys.exit(1)

    for line in cmd_out.split('\n'):
        temp = line.split('|')
        # We need to exclude the first line of the output which can not be split on '|'
        if len( temp ) > 1:
            user =  temp[ 2 ].strip( )
            # From the list we need to exclude the users added by quantum, nova, glance etc services
            # We also need to remove 'name' row
            if user != 'name' and user != 'admin' and \
               user != 'quantum' and user != 'cinder' and \
               user != 'glance' and user != 'nova':
                user_list.append( user )
        else:
            continue

    # Sort the list
    user_list.sort()
    lib_log.info( "User list:\n%s\n ", user_list )
    return user_list


# Returns the dictionary of which users belong to a specific tenant-id
#'tenant_id': 'user-name'
def get_user_tenant_mappings():

    user_tenant_map = {}
    tenant_table = {}

    # Get the users list
    user_list = get_keystone_users()

    # Get the tenant table. It will be used to print tenant names once we have the user_tenant_map
    tenant_table = get_keystone_tenants()
    
    if len( user_list ) == 0:
	lib_log.warning( "User list is empty. Please check if there are any user created users on the system" )
	return
	
    for user in user_list:
	
        cmd = "keystone user-get %s" % user
	# Execute user-get command for each user
        try:
            cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
            lib_log.debug( "%s\n%s\n" % ( cmd, cmd_out ))
        except subprocess.CalledProcessError as err:
            lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
    	    sys.exit(1)
        
	# Parse the cmd_out
        for line in cmd_out.split('\n'):
            temp = line.split('|')
            # We need to exclude the first line of the output which can not be split on '|'
            if len( temp ) > 1:
            	# Extract the tenantId from the output
                if temp[ 1 ].strip() == 'tenantId':
                    tenant_id = temp[ 2 ].strip()
		    tenant_name = tenant_table[ tenant_id ]
                    lib_log.debug( "User %s belongs to tenant - '%s' (%s)\n " % ( user, tenant_name, tenant_id ))
		    user_tenant_map[ tenant_id ] = user
                    break

    lib_log.info( "user_tenant_map:\n%s\n" % user_tenant_map )	
    return user_tenant_map

# Delete all the keystone users other than admin, quantum, nova, cinder and glance   
def delete_keystone_users():

    # Get the users list
    user_list = get_keystone_users()

    for user in user_list:

	cmd = "keystone user-delete %s" % user

	# Execute user-delete command
        try:
            lib_log.info( "\nDeleting user %s" % user )
            cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
            lib_log.debug( "%s\n%s" % ( cmd, cmd_out ))
            sleep( USER_DELETE_DELAY )
        except subprocess.CalledProcessError as err:
            lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
        else:
            # If try clause succeeds then parse the cmd_out
            lib_log.info( "User %s deleted\n" % user )
	

# Delete all the keystone tenants other than admin
def delete_keystone_tenants():

    # Get the tenants table
    tenant_table = get_keystone_tenants()

    # Get the tenant names except admin and services
    tenant_list = get_custom_tenant_names( tenant_table )
    if len( tenant_list ) == 0:
	lib_log.info( "tenant_list is perhaps empty. No user created tenants to delete on the system" )
        return

    for tenant_name in tenant_list:

        cmd = "keystone tenant-delete %s" % tenant_name

        # Execute tenant-delete command
        try:
            lib_log.info( "Deleting tenant %s" % tenant_name )
            cmd_out = subprocess.check_output( cmd, shell=True, stderr=subprocess.STDOUT )
            lib_log.debug( "%s\n%s" % ( cmd, cmd_out ))
            sleep( TENANT_DELETE_DELAY )
        except subprocess.CalledProcessError as err:
            lib_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
        else:
            # If try clause succeeds then parse the cmd_out
            lib_log.info( "Tenant %s deleted\n" % tenant_name )



# This method will delete all the quantum network data on the controller 
# including quantum dhcp ports
def clean_up_quantum_data( exclude_dhcp_ports=False ):

    # Delete quantum ports
    delete_quantum_ports( exclude_dhcp_ports )
    # Delete all the subnets
    delete_quantum_subnets()
    # Delete all the networks
    delete_quantum_networks()
    # Delete all the network profiles
    delete_n1k_nw_profiles()




if __name__ == '__main__':
#    get_policy_profiles()
#    get_user_tenant_mappings()
    port_info_table = get_port_info_table()
    get_ip_addr_port_table( port_info_table, exclude_dhcp_ports=True )


