#!/usr/bin/env python3
# https://community.cisco.com/t5/security-analytics-and/remote-backup-of-cisco-switch-configs/m-p/3844894
import csv
import datetime
import getpass
import glob
import netmiko
import paramiko
import re
import tarfile

from argparse import ArgumentParser
from datetime import datetime
from scp import SCPClient


PLAT_DICT = {"cisco_ios": {"run_cmd": "show run",
                           "regex": "Current configuration.*(P<hostname>hostname\s.*?\n).*!\nend"},
             "juniper_junos": {"run_cmd": "show configuration",
                               "regex": "## Last commit.*(?P<hostname>host-name\s.*?);.*"}
             }

REMOTE_SERVER_IP = "127.0.0.1"


def main():
    parser = ArgumentParser(description='Arguments for running tar_then_copy')
    parser.add_argument('-c', '--csv', required=True, action='store', help='Location of CSV file')
    args = parser.parse_args()

    ssh_username = input("SSH username: ")
    ssh_password = getpass.getpass("SSH Password: ")
    remote_username = input("Server username:")
    remote_password = getpass.getpass("Server SSH Password: ")

    with open(args.csv, "r") as file:
        reader = csv.DictReader(file)
        for device_row in reader:
            try:
                ssh_session = netmiko.ConnectHandler(device_type=device_row["type"], ip=device_row["device_ip"],
                                                     username=ssh_username, password=ssh_password)

                print("+++++ {0} +++++".format(device_row["device_ip"]))
                ssh_session.send_command("terminal length 0")
                run_output = ssh_session.send_command(PLAT_DICT[device_row["type"]]["run_cmd"])

                m = re.match(PLAT_DICT[device_row["type"]]["regex"], run_output.strip(), flags=re.DOTALL)
                if m:
                    with open("./output/{0}.cfg".format(m.group("hostname").split()[1]), "w", newline="") as f:
                        f.write(m.group())
                else:
                    print("regex failed to match output!! {0}".format(PLAT_DICT[device_row["type"]]["regex"]))

                ssh_session.disconnect()

            except (netmiko.ssh_exception.NetMikoTimeoutException,
                    netmiko.ssh_exception.NetMikoAuthenticationException,
                    paramiko.ssh_exception.SSHException) as s_error:
                print(s_error)

        tarfile_name = "configs-{0}.tar.gz".format(datetime.now().strftime("%Y-%m-%d-%H%M"))

        tar_file = tarfile.open("./output/{0}".format(tarfile_name), "w:gz")
        for c_file in glob.glob("./output/*.cfg"):
            tar_file.add(c_file)
        tar_file.close()

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(REMOTE_SERVER_IP, username=remote_username, password=remote_password)

        with SCPClient(ssh_client.get_transport()) as scp:
            scp.put("./output/{0}".format(tarfile_name))


if __name__ == "__main__":
    main()
