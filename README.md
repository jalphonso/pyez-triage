# Summary
This tool is a CLI based tool which can be run either interactively or non-interactively.

Mandatory args include (prompted for if not provided):

```
-u <username>, --user <username>
-p <password>, --pass <password>
-i <inventory_path>, --inventory <inventory_path>
-o <oper> [<oper> ...], --oper <oper> [<oper> ...]
```

Optional args (prompted for if not provided):

```
-l <limit>, --limit <limit>
-f <limit>, --iface <limit>
```

The `-q` option will disable prompting for optional args only.

Other Optional args (these are not prompted for):
```
-n, --nopass
-c <ssh_config>, --config <ssh_config>
-q, --quiet
```

This project gathers useful troubleshooting info from a device including interface errors and statistics
as well as optic related info if applicable. If optics are in alarm or warning state, a message indicating as such is output to the screen. When the interface is printed out it includes the following if available: its description, ae it belongs to, lldp info. You can restrict which interfaces are processed by specifying an inteface group either interactively or non-interactively with the `-f` option. See this [host_vars](inventory/dc1/host_vars/qfx5100-b.yml) example on how to configure an interface group. Interface counters are saved for the next run to compare against in the counters directory. Ensure this directory exists by issuing `mkdir counters` before your first run.

Additionally it outputs useful bgp info and searches logs for specific values to aid in t/s.

As seen in the sample output below you can select which operation you want to run on the command line.

Modify [thresholds.json](thresholds.json) to your desired values for your environment and only devices which violate
those thresholds will have printed output to the screen.

To take advantage of Ansibles inventory management capabilities, the Python script uses the Ansible Python API

The Colorama library in conjunction with Python f-strings is used to help visually by color coding terminal output to more easily identify devices, operations, and errors to focus on

*Written for Python 3.6

*PyEZ is the library used here to interact with the network devices.*

Installation instructions can be found in the [INSTALL.md](INSTALL.md)

# Details
### Usage

Supports interactive prompting

`python network_triage.py`
<img src="docs/menu.png">

Can also be run non-interactive provided that all mandatory args are specified (Prompting for optional args can be disabled with the `-q` option):
```
usage: network_triage.py [-h] [-o <oper> [<oper> ...]] [-u <username>]
                         [-p <password>] [-n] [-c <ssh_config>]
                         [-i <inventory_path>] [-l <limit>] [-f <limit>] [-q]

Execute troubleshooting operation(s)

optional arguments:
  -h, --help            show this help message and exit
  -o <oper> [<oper> ...], --oper <oper> [<oper> ...]
                        select operation(s) to run from list
  -u <username>, --user <username>
                        provide username for ssh login to devices
  -p <password>, --pass <password>
                        provide ssh password or passphrase
  -n, --nopass          disable password prompting
  -c <ssh_config>, --config <ssh_config>
                        provide ssh config path
  -i <inventory_path>, --inventory <inventory_path>
                        provide ansible inventory path
  -l <limit>, --limit <limit>
                        specify host or group to run operations on
  -f <limit>, --iface <limit>
                        specify host or group to run operations on
  -q, --quiet           disable optional interactive prompts
```
If password is not provided you will be prompted for it unless you specify the `--nopass` arg

*Short and Long arguments are both supported*

```
$ python network_triage.py -u Lab -i inventory/dc1 -c ~/.ssh/configs/Columbia -l mx240-1 -o blah
usage: network_triage.py [-h] [-o <oper> [<oper> ...]] -u <username>
                         [-p <password>] [-n] [-c <ssh_config>] -i
                         <inventory_path> [-l <limit>]
network_triage.py: error: argument -o/--oper: invalid choice: 'blah' (choose from 'all', 'ints', 'bgp', 'logs')
```

### Examples

`python network_triage.py --config ~/.ssh/configs/Columbia -u Lab -n -o ints -i inventory/dc1 -q -f host_ifaces`
<img src="docs/example4.png">

`python network_triage.py -u Lab -i inventory/dc1 -c ~/.ssh/configs/Columbia -o bgp`
<img src="docs/example1.png">

`python network_triage.py -u Lab -i inventory/dc1 -c ~/.ssh/configs/Columbia -l leaf -o bgp logs`
<img src="docs/example2.png">

`python network_triage.py -u Lab -i inventory/dc1 -c ~/.ssh/configs/Columbia -l mx240-1 -o ints`
<img src="docs/example3.png">

### Customize Thresholds
Set custom thresholds in the thresholds.json file using comparison operators like <, >, <=, >=, ==, != followed by a numerical value.
i.e. >= 100

*Note: Must include a space after the comparison operator