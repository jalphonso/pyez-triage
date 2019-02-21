import argparse
import getpass
import json
import os
import sys
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager
from colorama import Fore
from colorama import Style
from datetime import datetime
from jnpr.junos import Device
from jnpr.junos.exception import ConnectError, ProbeError, ConnectAuthError
from jnpr.junos.op.phyport import PhyPortErrorTable
from jnpr.junos.op.bgp import bgpTable
from jnpr.junos.utils.scp import SCP
from math import floor, ceil
from myTables.OpTables import PortFecTable
from myTables.OpTables import PhyPortDiagTable
from myTables.OpTables import EthMacStatTable
from myTables.OpTables import EthPcsStatTable
from myTables.OpTables import EthPortExtTable
from myTables.OpTables import EthPortTable
from myTables.OpTables import bgpSummaryTable
from myTables.OpTables import bgpTable


def _reached_threshold(actual, threshold):
    oper, val = threshold.split()
    if(eval(actual + oper + val)):
        return True
    return False


def _create_header(name):
    lpad = ceil((89-len(name))/2)
    rpad = floor((89-len(name))/2)
    return f"{'#'*lpad} {name.upper()} {'#'*rpad}"


def _print_if_msg(msg):
    if msg:
        print(msg)


def ints(dev):

    def print_interface_header():
        if ae:
            print(f"INTERFACE: {eth.name} which is part of ae bundle {ae}")
        else:
            print(f"INTERFACE: {eth.name}")
        if eth.description:
            print(f"Description: {eth.description}")

    def _check_optic(optic, header, print_interface):
        optic_rx_msg = optic_tx_msg = ""
        if(optic.rx_power_low_alarm or optic.rx_power_high_alarm):
            optic_rx_msg = f"{Fore.RED}  **Receiver power is too high or low. Interface possibly off**{Style.RESET_ALL}"
        elif(optic.rx_power_low_warn or optic.rx_power_high_warn):
            optic_rx_msg = f"{Fore.RED}  **Receiver power is marginal. Possible errors**{Style.RESET_ALL}"
        if(optic.bias_current_high_alarm or optic.bias_current_low_alarm or
        optic.bias_current_high_warn or optic.bias_current_low_warn or
        optic.tx_power_high_alarm or optic.tx_power_low_alarm or
        optic.tx_power_high_warn or optic.tx_power_low_warn):
            optic_tx_msg = f"{Fore.RED}  **Transmit Problems. Please check SFP.**{Style.RESET_ALL}"
        f"    RX Optic Power: {optic.rx_optic_power}  TX Optic Power: {optic.tx_optic_power}"
        if optic_rx_msg or optic_tx_msg:
            if print_interface:
                print_interface_header()
                print_interface = False
                print(f"Admin State: {eth['admin']}  Oper State: {eth['oper']}")
            print(header)
            print(f"    RX Optic Power: {optic.rx_optic_power}  TX Optic Power: {optic.tx_optic_power}")
            print(f"    Module Temp: {phy_optic.module_temperature}  Module Voltage: {phy_optic.module_voltage}")
            _print_if_msg(optic_rx_msg)
            _print_if_msg(optic_tx_msg)
        return print_interface

    def _save_curr_run(hostname, json_dict):
        fname = f"counters/{hostname}_prev_run.json"
        try:
            os.remove(fname)
            with open(fname, "w") as f:
                json.dump(json_dict, f)
            os.chmod(fname, 0o664)
        except Exception as err:
            print("Unable to save counters")
            print(err.__class__.__name__, err)

    def _get_prev_run(hostname):
        try:
            with open(f"counters/{hostname}_prev_run.json", "r") as f:
                return json.load(f)
        except Exception as err:
            print(f"No existing counters for device {hostname}")
            return None

    try:
        with open("thresholds.json", "r") as f:
            json_thresholds = json.load(f)
    except Exception as err:
        print("JSON load error")
        print("Skipping interface troubleshooting...")
        return

    hostname = dev.facts['hostname']

    json_prev_run = _get_prev_run(hostname)
    json_curr_run = {}

    timestamp = datetime.now()
    json_curr_run['timestamp'] = timestamp.__str__()

    optics = PhyPortDiagTable(dev).get()
    phy_errs = PhyPortErrorTable(dev).get()
    fec_errs = PortFecTable(dev).get()
    pcs_stats = EthPcsStatTable(dev).get()
    mac_stats = EthMacStatTable(dev).get()
    eths = EthPortTable(dev).get()
    eth_exts = EthPortExtTable(dev).get()

    print(f"{Fore.YELLOW}{_create_header('begin troubleshoot interfaces')}{Style.RESET_ALL}\n")

    for eth in eths:
        if eth['admin'] == 'down':
            print(f"{Fore.GREEN}{eth.name} is admin down, skipping remaining checks{Style.RESET_ALL}")
            continue
        logicals = eth_exts[eth.name].logical
        ae = None
        for logical in logicals:
            if logical.address_family_name == "aenet":
                ae = logical.ae_bundle_name
        json_curr_run[eth.name] = {}
        print_interface = True
        if eth.name in optics:
            optic = optics[eth.name]
            phy_optic = optic
            if(optic.lanes):
                for lane in optic.lanes:
                    #For channelized interfaces
                    if(":" in eth.name):
                        if(eth.name[-1] != str(lane.lane_index)):
                            continue
                    #Handles QSFPs as well
                    header = f"  Optic Diag Lane# {lane.name}:"
                    print_interface = _check_optic(lane, header, print_interface)
            elif(optic.rx_optic_power):
                header = "  Optic Diag:"
                print_interface = _check_optic(optic, header, print_interface)

        tables = [ phy_errs, fec_errs, pcs_stats, mac_stats ]
        for table in tables:
            if eth.name in table:
                row = table[eth.name]
                if row.__class__.__name__ == "PortFecView":
                    key = 'fec_errs'
                elif row.__class__.__name__ == "PhyPortErrorView":
                    key = 'phy_errs'
                elif row.__class__.__name__ == "EthPcsStatView":
                    key = 'pcs_stats'
                elif row.__class__.__name__ == "EthMacStatView":
                    key = 'mac_stats'

                for subkey in json_thresholds[key].keys():
                    if subkey in row.keys() and row[subkey]:
                        if _reached_threshold(str(row[subkey]), str(json_thresholds[key][subkey])):
                            json_curr_run[eth.name][subkey] =  row[subkey]
                            if print_interface:
                                print_interface_header()
                                print_interface = False
                            print(f"  {Fore.RED}'{subkey}' threshold is {str(json_thresholds[key][subkey])} with value of {str(row[subkey])}{Style.RESET_ALL}")
                            try:
                                diff = row[subkey] - json_prev_run[eth.name][subkey]
                                prevtimestamp = datetime.strptime(json_prev_run['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                                timediff = timestamp - prevtimestamp
                                seconds = timediff.seconds
                                if diff !=0:
                                    print(f"     {Fore.MAGENTA}previous value was {str(json_prev_run[eth.name][subkey])}"
                                            f" which is a difference of {str(diff)} from the last run {seconds}s ago"
                                            f" or about {round(diff/seconds,2):0.2f}/second"
                                            f"{Style.RESET_ALL}")
                            except Exception:
                                pass
        if not json_curr_run[eth.name]:
            del json_curr_run[eth.name]
    _save_curr_run(hostname, json_curr_run)
    print(f"{Fore.YELLOW}{_create_header('end of troubleshoot interfaces')}{Style.RESET_ALL}\n")


def bgp(dev):
    print(f"{Fore.YELLOW}{_create_header('begin troubleshoot bgp')}{Style.RESET_ALL}\n")
    neighbors = bgpTable(dev).get()
    neighsumm = bgpSummaryTable(dev).get()
    for neighbor in neighbors:
        peer_address = neighbor.peer_address.split("+")[0]
        peer_state = neighbor.peer_state
        if(peer_state == "Established"):
            print(f"Local ID: {neighbor.local_id:15} Local AS: {neighbor.local_as:7} Local Address: {neighbor.local_address}\nPeer  ID: {neighbor.peer_id:15} Peer  AS: {neighbor.peer_as:7} "\
                  f"Peer Address: {neighbor.peer_address:17}\nNum Routes Received: {neighbor.route_received} Local Interface: {neighbor.local_interface}\nElapsed Time(secs): {neighsumm[peer_address].elapsed_time_secs}\n")
        elif(peer_state == "Active"):
            print(f"{Fore.RED}Neighbor {neighbor.peer_address} in active state, check configuration{Style.RESET_ALL}")
        elif(peer_state == "Connect"):
            print(f"{Fore.RED}Neighbor {neighbor.peer_address} in connect state, check protocol configuration{Style.RESET_ALL}")
        elif(peer_state == "Idle"):
            print(f"{Fore.RED}Neighbor {neighbor.peer_address} in idle state, check reachability{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Unxpected state of {peer_state}. Neighbor {neighbor.peer_address} may be in transition, rerun command in a few seconds{Style.RESET_ALL}")

    print(f"{Fore.YELLOW}{_create_header('end of troubleshoot bgp')}{Style.RESET_ALL}\n")


def logs(dev):
    print(f"{Fore.YELLOW}{_create_header('begin parse syslog')}{Style.RESET_ALL}\n")

    ntp_issue = False
    license_issue=False

    print("Transferring /var/log/messages from device")
    with SCP(dev, progress=True) as scp1:
        scp1.get("/var/log/messages", local_path="logs/"+dev.hostname+"-messages")
    with open("logs/"+dev.hostname+"-messages") as messages:
        lines = messages.readlines()
        ntp_color = license_color = "Fore.RESET"
        for line in lines:
            if "NTP" in line and "Unreachable" in line:
                ntp_issue = True
                ntp_color = "Fore.RED"
            elif "License" in line:
                license_issue = True
                license_color = "Fore.RED"
    print(f"{eval(ntp_color)}ntp_issue: {ntp_issue}{Style.RESET_ALL}, {eval(license_color)}license_issue: {license_issue}{Style.RESET_ALL}\n")
    print(f"{Fore.YELLOW}{_create_header('end of parse syslog')}{Style.RESET_ALL}\n")


def info(dev):
    print(f"{Fore.YELLOW}{_create_header('begin get info (device facts)')}{Style.RESET_ALL}\n")
    print(f"Hostname: {dev.facts['hostname']:21} Version: {dev.facts['version']}\n"
            f"Model:    {dev.facts['model']:21} SN:      {dev.facts['serialnumber']}")
    print(f"RE0 Uptime: {dev.facts['RE0']['up_time']}")
    if dev.facts['2RE']:
        print(f"  RE1 Uptime: {dev.facts['RE1']['up_time']}")
    print(f"{Fore.YELLOW}{_create_header('end of get info (device facts)')}{Style.RESET_ALL}\n")


def main():
    oper_choices = ["all", "ints", "bgp", "logs", "info"]
    parser = argparse.ArgumentParser(description='Execute troubleshooting operation(s)')
    parser.add_argument('-o', '--oper', dest='operations', metavar='<oper>',
                        choices=oper_choices, default=['all'],
                        nargs='+', help='select operation(s) to run from list')
    parser.add_argument('-u', '--user', dest='user', metavar='<username>', required=True,
                        help='provide username for ssh login to devices')
    parser.add_argument('-p', '--pass', dest='passwd', metavar='<password>',
                        help='provide ssh password or passphrase')
    parser.add_argument('-n', '--nopass', action='store_true',
                        help='disable password prompting')
    parser.add_argument('-c', '--config', dest='ssh_config', metavar='<ssh_config>', default='',
                        help='provide ssh config path')
    parser.add_argument('-i', '--inventory', dest='inventory_path', metavar='<inventory_path>',
                        required=True, help='provide ansible inventory path')
    parser.add_argument('-l', '--limit', dest='limit', metavar='<limit>',
                        help='specify host or group to run operations on')
    parser.add_argument('-g', '--getoper', action='store_true',
                        help='print available operations')

    args = parser.parse_args()

    if args.getoper:
        print(f"Valid choices for operations are: {oper_choices}")
        sys.exit(0)

    if args.operations == ['all']:
        operations = list(oper_choices)
        operations.remove('all')
    else:
        operations = args.operations

    if args.passwd:
        passwd = args.passwd
    elif not args.nopass:
        passwd = getpass.getpass("Enter your password: ")
    else:
        passwd = None

    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=args.inventory_path)
    variables = VariableManager(loader=loader, inventory=inventory)
    success = 0
    failure = 0
    failed_hosts = []
    for host in inventory.get_hosts():
        hostname = host.get_name()
        if args.limit:
            if not args.limit in [str(g) for g in host.get_groups()] and not args.limit == hostname:
                continue

        netconf_port = variables.get_vars(host=host)['netconf_port']

        try:
            print(f"{Fore.BLUE}{Style.BRIGHT}Conducting triage of device {hostname}{Style.RESET_ALL}")
            with Device(host=hostname, port=netconf_port, user=args.user, passwd=passwd, ssh_config=args.ssh_config, auto_probe=5) as dev:
                for operation in operations:
                    globals()[operation](dev)
            success = success + 1
        except ConnectAuthError as err:
            print(f"{Fore.RED}Unable to login. Check username/password: {err}")
            print(f"Exiting so you don't lock yourself out :){Style.RESET_ALL}")
            sys.exit(1)
        except (ProbeError, ConnectError) as err:
            print(f"{Fore.RED}Cannot connect to device: {err}\nMake sure device is reachable and {Style.BRIGHT}'set system services netconf ssh'{Style.NORMAL} is set{Style.RESET_ALL}")
            failure = failure + 1
            failed_hosts.append(hostname)
        except Exception as err:
            print(f"{Fore.RED}Abnormal termination: {err.__class__.__name__, err}{Style.RESET_ALL}")
            sys.exit(1)
    if success > 0:
        print(f"{Fore.GREEN}Successfully connected to: {success} device(s){Style.RESET_ALL}")
    if failure > 0:
        print(f"{Fore.RED}Failed to connect to {failure} device(s)\nFailed Hosts: {failed_hosts}{Style.RESET_ALL}")
    if not success and not failure:
        print(f"{Fore.RED}No Hosts/Groups matched limit '{args.limit}'{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
