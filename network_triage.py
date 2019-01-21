import getpass
import json
import sys
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager
from colorama import Fore
from colorama import Style
from jnpr.junos import Device
from jnpr.junos.exception import ConnectError
from jnpr.junos.op.phyport import PhyPortErrorTable
from jnpr.junos.op.bgp import bgpTable
from jnpr.junos.utils.scp import SCP
from math import floor, ceil
from myTables.OpTables import PortFecTable
from myTables.OpTables import PhyPortDiagTable
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


def ints(dev):
    try:
        with open("thresholds.json") as f:
            json_data = json.load(f)
    except Exception as e:
        print("JSON load error")
        print("Skipping interface troubleshooting...")
        return

    phy_err_thresh = json_data['phy_errs']
    fec_err_thresh = json_data['fec_errs']

    optics = PhyPortDiagTable(dev).get()
    phy_errs = PhyPortErrorTable(dev).get()
    phy_fec_errs = PortFecTable(dev).get()

    print(f"{Fore.YELLOW}{_create_header('begin troubleshoot interfaces')}{Style.RESET_ALL}\n")
    for err in phy_errs:
        print_interface = True
        fec_err = phy_fec_errs[err.name]
        for key in phy_err_thresh.keys():
            try:
                if _reached_threshold(str(err[key]), str(phy_err_thresh[key])):
                    if print_interface:
                        print(f"INTERFACE: {err.name}")
                        print_interface = False
                    print(f"{Fore.RED}'{key}' threshold is {str(phy_err_thresh[key])} with value of {str(err[key])}{Style.RESET_ALL}")
            except KeyError as e:
                continue

        if(fec_err.fec_ccw_count is not None):
            for key in fec_err_thresh.keys():
                try:
                    if _reached_threshold(str(fec_err[key]), str(fec_err_thresh[key])):
                        if print_interface:
                            print(f"INTERFACE: {err.name}")
                            print_interface = False
                        print(f"{Fore.RED}'{key}' threshold is {str(fec_err_thresh[key])} with value of {str(fec_err[key])}{Style.RESET_ALL}")
                except KeyError as e:
                    continue
        if(err.name in optics):
            optic = optics[err.name]
            if(optic.lanes):
                if print_interface:
                    print(f"INTERFACE: {err.name}")
                    print_interface = False
                for lane in optic.lanes:
                    print(f"  Optic Diag Lane# {lane.name}:\n    RX Optic Power: {lane.rx_optic_power}  TX Optic Power: {lane.tx_optic_power}\n  "\
                        f"  Module Temp: {optic.module_temperature}  Module Voltage: {optic.module_voltage}")
                    if(lane.rx_power_low_alarm or lane.rx_power_high_alarm):
                        print("  **Receiver power is too high or low. Interface possibly off**")
                    elif(lane.rx_power_low_warn or lane.rx_power_high_warn):
                        print("  **Receiver power is marginal. Possible errors**")
                    if(lane.bias_current_high_alarm or lane.bias_current_low_alarm or
                    lane.bias_current_high_warn or lane.bias_current_low_warn or
                    lane.tx_power_high_alarm or lane.tx_power_low_alarm or
                    lane.tx_power_high_warn or lane.tx_power_low_warn):
                        print("  **Transmit Problems. Please check SFP.**")
            elif(optic.rx_optic_power):
                if print_interface:
                    print(f"INTERFACE: {err.name}")
                    print_interface = False
                print(f"  Optic Diag:\n    RX Optic Power: {optic.rx_optic_power}  TX Optic Power: {optic.tx_optic_power}\n  "\
                    f"  Module Temp: {optic.module_temperature}  Module Voltage: {optic.module_voltage}")
                if(optic.rx_power_low_alarm or optic.rx_power_high_alarm):
                    print("  **Receiver power is too high or low. Interface possibly off**")
                elif(optic.rx_power_low_warn or optic.rx_power_high_warn):
                    print("  **Receiver power is marginal. Possible errors**")
                if(optic.bias_current_high_alarm or optic.bias_current_low_alarm or
                optic.bias_current_high_warn or optic.bias_current_low_warn or
                optic.tx_power_high_alarm or optic.tx_power_low_alarm or
                optic.tx_power_high_warn or optic.tx_power_low_warn):
                    print("  **Transmit Problems. Please check SFP.**")
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
                  f"Peer Address: {neighbor.peer_address:17}\nNum Routes Received: {neighbor.route_received:4} Local Interface: {neighbor.local_interface}\nElapsed Time(secs): {neighsumm[peer_address].elapsed_time_secs}\n")
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
        ntp_color = license_color = "Fore.WHITE"
        for line in lines:
            if "NTP" in line and "Unreachable" in line:
                ntp_issue = True
                ntp_color = "Fore.RED"
            elif "License" in line:
                license_issue = True
                license_color = "Fore.RED"
    print(f"{eval(ntp_color)}ntp_issue: {ntp_issue}{Style.RESET_ALL}, {eval(license_color)}license_issue: {license_issue}{Style.RESET_ALL}\n")
    print(f"{Fore.YELLOW}{_create_header('end of parse syslog')}{Style.RESET_ALL}\n")


def main():

    try:
        inventory_path = sys.argv[1]
    except IndexError:
        print(f"{Fore.RED}{_create_header('usage')}")
        print("python network_triage.py <inventory path> <operation comma sep list>")
        print("Supported operations are 'ints,bgp,logs'")
        print(f'i.e. python network_triage.py inventory/dc1 "bgp,logs"\n{Style.RESET_ALL}')
        sys.exit(1)

    try:
        operations = sys.argv[2].split(",")
    except IndexError:
        operations = ["ints", "bgp", "logs"]

    user = input("Enter your user name: ")
    passwd = getpass.getpass("Enter your password: ")
    ssh_config = input("Enter path to ssh_config if applicable: ")

    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=inventory_path)
    variables = VariableManager(loader=loader, inventory=inventory)

    for host in inventory.get_hosts():
        hostname = host.get_name()
        netconf_port = variables.get_vars(host=host)['netconf_port']
        try:
            print(f"{Fore.BLUE}Conducting triage of device {hostname}{Style.RESET_ALL}")
            with Device(host=hostname, port=netconf_port, user=user, passwd=passwd, ssh_config=ssh_config) as dev:
                for operation in operations:
                    globals()[operation](dev)
        except ConnectError as err:
            print(f"Cannot connect to device: {err}")
            sys.exit(1)
        except Exception as err:
            print(err.__class__.__name__, err)
            print("Abnormal termination")
            sys.exit(1)


if __name__ == "__main__":
    main()
