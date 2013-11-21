#!/usr/bin/python
#--------------------------------------------------------------
# This script creates OpenStack keystone tenants and users
# It also defines functions to retrieve already created users
# and tenants
#
#--------------------------------------------------------------

import sys
sys.path.append('../lib')
import subprocess
import logging
from time import sleep
from os_nw_lib import *

# Delay between commands 
CMD_DELAY = 2

# Initialize logging
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(name)s - %(message)s', level=logging.WARNING)
t_log = logging.getLogger('t_log')

t_log.setLevel(logging.INFO)

# Template for keystone tenant-create command parameters
t_name = "tenant"
description = "tenant"
enabled = "true"
UNIT_DIGIT_RANGE = 10

# Set the number of tenants
num_of_tenants = 51

# Template for keystone user-create command parameters
u_name = "user"
passwd = "n1k12345"
email = ""
 
# Set the number of users
num_of_users = 51

def create_tenants():

    # Create the tenants in tenant00, tenant01, tenant02..... range
    for i in range( num_of_tenants/10 ):
	# Inner loop to add a digit
	for j in range( UNIT_DIGIT_RANGE ):
	    
	    # Formulate the keystone tenant-create command
            cmd = ( "keystone tenant-create --name %s%s%s --description '%s%s%s' --enabled %s" % 
	        	( t_name, i, j, description, i, j, enabled ) )  
	    t_log.info( cmd )
	
	    # Execute command
	    try:
	        cmd_out = subprocess.check_output( cmd, stderr=subprocess.STDOUT, shell=True )
	        t_log.info( cmd_out )
	    except subprocess.CalledProcessError as err:
	        t_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
	        sys.exit(1)	    
	
	    sleep(CMD_DELAY)	

# Create users. Optionally the users can be associated with individual tenants
# with 1 user - 1 tenant mapping. So the number of users to be created must 
# equal the number of tenants
def create_users( associate_with_tenants=False ):
    
    tenant_ids_list = []

    # If the tenants have to be associated we need to get the tenants list
    if associate_with_tenants: 
	
	# First get all the tenants on the system
	tenant_table = get_keystone_tenants()
	
	# Now get the user created tenant ids for sorted tenant names 
	tenant_ids_list = get_custom_tenant_ids( tenant_table )

     # Create the tenants in user00, user01, user02..... range
    for i in range( num_of_users/10 ):
		
	for j in range( UNIT_DIGIT_RANGE ):
	    
	    if associate_with_tenants:
		
		# First check if the number of tenants == number of users - 1
		if len( tenant_ids_list ) != ( num_of_users - 1 ):
		    t_log.info( "Number of tenants is not equal to number of users to be created" )
		    t_log.info( "Not all users will have a tenant associated with each one of them" )
		    t_log.info( "Ensure that num of tenants = num of users to be created" )
		    return

		# Fetch the individual tenant-id by creating the idx
		indx = int( "%s%s" % (i , j) )
		tenant_id = tenant_ids_list[ indx ]
		cmd = ( "keystone user-create --name %s%s%s --tenant_id %s --pass '%s' --email %s@n1kv" %
                    ( u_name, i, j, tenant_id, passwd, u_name  ) )
            	t_log.info( cmd )
	
	    else:
		# Formulate the keystone user-create command
            	cmd = ( "keystone user-create --name %s%s%s --pass '%s' --email %s@n1kv" %
                        ( u_name, i, j, passwd, u_name  ) )
            	t_log.info( cmd )

    	    # Execute command
            try:
                cmd_out = subprocess.check_output( cmd, stderr=subprocess.STDOUT, shell=True )
                t_log.info( cmd_out )
            except subprocess.CalledProcessError as err:
	        t_log.warning( "Something went wrong! \nreturncode - '%s'\ncmd - '%s'\noutput - %s" % ( err.returncode, err.cmd, err.output ))
 	        sys.exit(1)
	
	    sleep(CMD_DELAY)

# Execute the script        
if __name__ == '__main__':
    # create_tenants()
    create_users(associate_with_tenants=True)

     
