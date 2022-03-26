#! /usr/bin/env python3

import os
import netmiko
from netmiko.ssh_exception import NetMikoTimeoutException
from paramiko.ssh_exception import SSHException
from netmiko.ssh_exception import AuthenticationException
from netmiko import ConnectHandler

'''This script will remove specific IP address entries for any extended ACL in a Cisco router config.  
For this script to work, the first octect of the IP address must be known.  This is not meant to be a RegEx specific script or 
for a range of IP addresses.  This is for simple removals where the first octet is known.
hostsfile.txt is in standard /etc/hosts file format with IP address followed by hostname'''


os.system("touch IP_Removal_ACL.txt")  # creating dummy text file so that the loop below has something to remove

numerical_list = ['1', '2', '3', '4', '5', '6', '7', '8', '9']  # Index so that we can filter on IP addresses in CPE hosts file 

with open("hostsfile.txt", "r") as r:
    for line in r:
        os.system("rm IP_Removal_ACL.txt") # remove previous file as we iterate to new host
        os.system("touch IP_Removal_ACL.txt") # create new file to write the commands that will remove the IP addresss
        if line[0] in numerical_list:
            line = line.split()        # create an indexed list separated by spaces, this now makes line[0] the IP address
            Cisco_Host = {
                'device_type': 'cisco_ios',
                'ip': line[0],
                'username': '<username>',
                'password': '<password>'
            }                                   # Loops through text file by IP address.  Credentials must be the same for each host
            hostname = line[1]     # setting hostname for this iteration.  Hostname is second string in line
            try:
                SESSION = ConnectHandler(**Cisco_Host)      # Connect to router
                output = SESSION.send_command("show running-config | s extended")   # Gather all extended ACLs and their entries beneath
                with open(f"{hostname}_output.txt", 'w') as f:                      # Creating specific output file for each host, and writing the output of the above command
                    f.write(output)
                print ("Gathering ACL data from " + hostname  + " router\n")
                IP_removal_commands = []                                # Initializing blank list to store the 'no' IP address removal commands 
                with open(f"{hostname}_output.txt", "r") as w:          # open the host output we just created with the full ACL output 
                    for line in w:                                      # Loop through each line in output file check for the specific IP string we're looking to remove
                        if " <IP_string>" in line:      
                            with open("IP_Removal_ACL.txt", "a") as a:  # create a new file and write the removal commands starting with 'no' to remove this entry from the ACL
                                a.write("no" + line)
                        elif "extended" and "access-list" in line:      # search for the name of the ACL entries and write to the file so that we can configure each ACL and add the removal commands underneath if needed
                            with open("IP_Removal_ACL.txt", "a") as a:  # This new textfile specifically stores the commands we'll need to remove the IP entries
                                a.write(line)
                with open ("IP_Removal_ACL.txt", "r") as rw:            # Loop through this new textfile, and append each command to our IP_removal_list.  The commands will be pushed from the list as opposed to the textfile
                    for line in rw:
                        IP_removal_commands.append(line)
                IP_removal_commands = [i.replace('\n', '') for i in IP_removal_commands]    # removing the newline character from textfile
                IP_removal_commands.append('end')                                           # exiting ACL configuration mode
                IP_removal_commands.append('write memory')                                  # save running-config
                IP_removal_commands.append('show running | s extended')                     # this is a post-check to look at each ACL and confirm that the IP address entries are removed
                IP_removal_commands.append('show running | i <IP_string>')                  # confirm that the IP string is no longer in config
                IP_removal_commands.append('show run | i Last')                             # confirm that write memory command was successful.  Confirm timestamp
                print(IP_removal_commands)
                ssh_connect = ConnectHandler(**Cisco_Host)
                ssh_connect.enable()
                result = ssh_connect.send_config_set(IP_removal_commands)                   # connect to device and send the commands from above to remove IPs and save config
                print ("Removing IPs from ACL in " + hostname + " CPE Router\n")
                print(result)
            except(AuthenticationException):                                                # Authentication Failure exception handling.  If authentication fails, make a note and move on to next device in list
                print('Authentication Failure: ' + hostname)
            except(NetMikoTimeoutException):                                                # If there's an SSH timeout, move on to next device in list
                print('Timeout to device: ' + hostname)
            except(SSHException):
                print('SSH may not be enabled, check config on: ' + hostname)               # If SSH is not listening on interface, move on to next device in list

