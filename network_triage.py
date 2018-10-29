import json
import sys
from jnpr.junos import Device
from jnpr.junos.exception import ConnectError
from jnpr.junos.op.intopticdiag import PhyPortDiagTable
from jnpr.junos.op.ethernetswitchingtable import EthernetSwitchingTable
from jnpr.junos.op.phyport import PhyPortErrorTable
from myTables.OpTables import PortFecTable
from pprint import pprint


def main():
    hostname = sys.argv[1]
    port = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]
    try:
        print("#####################################################################")
        print("\nConducting triage of device {hostname}\n".format(hostname=hostname))
        with Device(host=hostname, port=port, user=username, passwd=password) as dev:
            optics = PhyPortDiagTable(dev).get()
            phy_errs = PhyPortErrorTable(dev).get()
            phy_fec_errs = PortFecTable(dev).get()
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
                print("")
        print("#####################################################################")
    except ConnectError as err:
        print("Cannot connect to device: {0}".format(err))
        sys.exit(1)
    except Exception as err:
        print(err)
        sys.exit(1)

if __name__ == "__main__":
    main()
