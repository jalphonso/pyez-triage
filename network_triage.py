import sys
from jnpr.junos import Device
from jnpr.junos.exception import ConnectError
from jnpr.junos.op.phyport import PhyPortErrorTable
from jnpr.junos.op.bgp import bgpTable
from myTables.OpTables import PortFecTable
from myTables.OpTables import PhyPortDiagTable
from myTables.OpTables import bgpSummaryTable
from myTables.OpTables import bgpTable


def main():
    hostname = sys.argv[1]
    port = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]
    try:
        print("")
        print("################################### DEVICE BEGIN ########################################")
        print("Conducting triage of device {hostname}".format(hostname=hostname))
        with Device(host=hostname, port=port, user=username, passwd=password) as dev:
            ts_interface(dev)
            ts_bgp(dev)
        print("################################### DEVICE END ##########################################\n")
    except ConnectError as err:
        print("Cannot connect to device: {0}".format(err))
        sys.exit(1)
    except Exception as err:
        print(err)
        sys.exit(1)

def ts_interface(dev):
    optics = PhyPortDiagTable(dev).get()
    phy_errs = PhyPortErrorTable(dev).get()
    phy_fec_errs = PortFecTable(dev).get()
    print("############################# BEGIN TROUBLESHOOT INTERFACES #############################\n")
    for err in phy_errs:
        fec_err = phy_fec_errs[err.name]
        print("INTERFACE: {}".format(err.name))
        print("  Input Errors:\n    Errors: {}  Drops: {}  Framing errors: {}"\
              "  Runts: {}  Policed discards: {}  L3 incompletes: {}\n  "\
              "  L2 channel errors: {}  L2 mismatch timeouts: {}  FIFO errors: {}"\
              "  Resource errors: {}"\
              .format(err.rx_err_input, err.rx_err_drops,
                      err.rx_err_frame, err.rx_err_runts,
                      err.rx_err_discards, err['rx_err_l3-incompletes'],
                      err['rx_err_l2-channel'], err['rx_err_l2-mismatch'],
                      err.rx_err_fifo, err.rx_err_resource))
        print("  Output Errors:\n    Carrier transitions: {}  Errors: {}"\
              "  Drops: {}  Collisions: {}  Aged packets: {}  FIFO errors: {}\n  "\
              "  HS link CRC errors: {}  MTU errors: {}  Resource errors: {}"\
              .format(err['tx_err_carrier-transitions'],
                      err.tx_err_output, err.tx_err_drops,
                      err.tx_err_collisions, err.tx_err_aged,
                      err.tx_err_fifo, err['tx_err_hs-crc'],
                      err.tx_err_mtu, err.tx_err_resource))
        if(fec_err.fec_ccw_count is not None):
            print("  Ethernet FEC statistics\n    FEC Corrected Errors: {}"\
                  "  FEC Uncorrected Errors: {}\n    FEC Corrected Errors Rate: {}"\
                  "  FEC Uncorrected Errors Rate: {}"\
                  .format(fec_err.fec_ccw_count, fec_err.fec_nccw_count,
                          fec_err.fec_ccw_error_rate, fec_err.fec_nccw_error_rate))
        if(err.name in optics and optics[err.name].rx_optic_power is not None):
            optic = optics[err.name]
            print("  Optic Diag:\n    RX Optic Power: {}  TX Optic Power: {}\n  "\
                  "  Module Temp: {}  Module Voltage: {}".\
                  format(optic.rx_optic_power, optic.tx_optic_power,
                         optic.module_temperature, optic.module_voltage))
            if(optic.rx_power_low_alarm or optic.rx_power_high_alarm):
                print("  **Receiver power is too high or low. Interface possibly off**")
            elif(optic.rx_power_low_warn or optic.rx_power_high_warn):
                print("  **Receiver power is marginal. Possible errors**")
            if(optic.bias_current_high_alarm or optic.bias_current_low_alarm or
               optic.bias_current_high_warn or optic.bias_current_low_warn or
               optic.tx_power_high_alarm or optic.tx_power_low_alarm or
               optic.tx_power_high_warn or optic.tx_power_low_warn):
                print("  **Transmit Problems. Please check SFP.**")
        print("")
    print("############################# END OF TROUBLESHOOT INTERFACES ############################\n")

def ts_bgp(dev):
    print("############################# BEGIN TROUBLESHOOT BGP ####################################\n")
    neighbors = bgpTable(dev).get()
    neighsumm = bgpSummaryTable(dev).get()
    for neighbor in neighbors:
        peer_address = neighbor.peer_address.split("+")[0]
        peer_state = neighbor.peer_state
        if(peer_state == "Established"):
            print("Local ID: {:15} Local AS: {:7} Local Address: {}\nPeer  ID: {:15} Peer  AS: {:7} "\
                  "Peer Address: {:17}\nNum Routes Received: {:4} Local Interface: {}\nElapsed Time(secs): {}\n"\
                  .format(neighbor.local_id, neighbor.local_as, neighbor.local_address,
                          neighbor.peer_id, neighbor.peer_as, neighbor.peer_address,
                          neighbor.route_received, neighbor.local_interface,
                          neighsumm[peer_address].elapsed_time_secs))
        elif(peer_state == "Active"):
            print("Neighbor {} in active state, check configuration".format(neighbor.peer_address))
        elif(peer_state == "Connect"):
            print("Neighbor {} in connect state, check protocol configuration".format(neighbor.peer_address))
        elif(peer_state == "Idle"):
            print("Neighbor {} in idle state, check reachability".format(neighbor.peer_address))
        else:
            print("Unxpected state of {}. Neighbor {} may be in transition, rerun command in a few seconds".\
                  format(peer_state, neighbor.peer_address))


    print("############################# END OF TROUBLESHOOT BGP ###################################\n")


if __name__ == "__main__":
    main()
