#!/usr/bin/env python3
# https://community.cisco.com/t5/firewalls/editing-access-lists-for-mass-editing-removing-all-and-re-adding/m-p/3830084
import getpass
import csv
import netmiko
import paramiko
import re
from argparse import ArgumentParser

ACL_REGEX = "access-list\s(?P<acl_name>\S*?)\s"


def process_acls(intput_acls):
    all_acls_dict = {}

    acls = intput_acls.split("\n")

    for acl in acls:
        match = re.match(ACL_REGEX, acl)

        if match:
            if match.group("acl_name") not in all_acls_dict:
                all_acls_dict[match.group("acl_name")] = []
            all_acls_dict[match.group("acl_name")].append(acl)

    return all_acls_dict


def main():
    parser = ArgumentParser(description='Arguments for running asa_acl_add_log')
    parser.add_argument('-c', '--csv', required=True, action='store', help='Location of CSV file')
    args = parser.parse_args()

    ssh_username = input("SSH username: ")
    ssh_password = getpass.getpass('SSH Password: ')

    with open(args.csv, "r") as file:
        reader = csv.DictReader(file)
        for device_row in reader:
            try:
                ssh_session = netmiko.ConnectHandler(device_type='cisco_ios', ip=device_row['device_ip'],
                                                     username=ssh_username, password=ssh_password)

                print("+++++ {0} +++++".format(device_row['device_ip']))
                ssh_session.send_command("terminal length 0")
                acl_output = ssh_session.send_command("sh run | inc access-list")

                for acl_name in acl_output:
                    for acl in reversed(acl_output[acl_name]):
                        ssh_session.send_command("no {0}".format(acl))

                    for acl in acl_output[acl_name]:
                        ssh_session.send_command("{0} log".format(acl))

                ssh_session.disconnect()

            except (netmiko.ssh_exception.NetMikoTimeoutException,
                    netmiko.ssh_exception.NetMikoAuthenticationException,
                    paramiko.ssh_exception.SSHException) as s_error:
                print(s_error)


if __name__ == "__main__":
    main()
