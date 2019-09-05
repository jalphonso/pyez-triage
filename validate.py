import re
import sys
from colorama import Fore, Style
from exceptions import InvalidInput
from netaddr import IPAddress, IPNetwork
from netaddr.core import AddrFormatError
from getpass import getpass
from retrying import retry


def _retry_if_invalid_input(exc):
  return isinstance(exc, InvalidInput)


@retry(stop_max_attempt_number=5, retry_on_exception=_retry_if_invalid_input)
def validate_str(prompt, input_min=None, input_max=None, cli_input=None, default=None, choices=None):
  prompt = _update_prompt(prompt, default)
  user_input = _check_input(prompt, cli_input, default)
  return user_input


@retry(stop_max_attempt_number=5, retry_on_exception=_retry_if_invalid_input)
def validate_bool(prompt, input_min=None, input_max=None, cli_input=None, default=None, choices=None):
  if default is False:
    default = 'n'
  elif default is True:
    default = 'y'
  prompt = _update_prompt(prompt, default)
  user_input = _check_input(prompt, cli_input, default)

  bool_input = user_input.lower()
  if bool_input == 'y' or bool_input == 'yes':
    user_input = True
  elif bool_input == 'n' or bool_input == 'no':
    user_input = False
  else:
    print(f"{Fore.YELLOW}Input needs to be yes/no or y/n, please try again{Style.RESET_ALL}")
    raise InvalidInput
  return user_input


@retry(stop_max_attempt_number=5, retry_on_exception=_retry_if_invalid_input)
def validate_password(prompt, input_min=None, input_max=None, cli_input=None, default=None, choices=None):
  if not cli_input:
    passwd = getpass(prompt).strip()
    if passwd:
      passwd_confirm = getpass("Confirm your password: ").strip()
      if passwd == passwd_confirm:
        user_input = passwd
      else:
        print(f"{Fore.YELLOW}Passwords do not match, please try again...{Style.RESET_ALL}")
        raise InvalidInput
    else:
      print(f"{Fore.YELLOW}Password cannot be blank, please try again...{Style.RESET_ALL}")
      raise InvalidInput
  else:
    user_input = cli_input
  return user_input


@retry(stop_max_attempt_number=5, retry_on_exception=_retry_if_invalid_input)
def validate_int(prompt, input_min=None, input_max=None, cli_input=None, default=None, choices=None):
  prompt = _update_prompt(prompt, default)
  user_input = _check_input(prompt, cli_input, default)
  try:
    user_input = int(user_input)
  except ValueError:
    print(f"{Fore.YELLOW}Input needs to be an integer, please try again{Style.RESET_ALL}")
    raise InvalidInput

  if input_min is not None and input_max is not None and input_min < input_max:
    if user_input < input_min or user_input > input_max:
      print(f"{Fore.YELLOW}Input needs to be between {input_min} and {input_max}, please try again{Style.RESET_ALL}")
      raise InvalidInput
  elif input_min is not None and user_input < input_min:
    print(f"{Fore.YELLOW}Input needs to be greater than or equal to {input_min}, please try again{Style.RESET_ALL}")
    raise InvalidInput
  elif input_max is not None and user_input > input_max:
    print(f"{Fore.YELLOW}Input needs to be less than or equal to {input_max}, please try again{Style.RESET_ALL}")
    raise InvalidInput

  return user_input


@retry(stop_max_attempt_number=5, retry_on_exception=_retry_if_invalid_input)
def validate_choice(prompt, input_min=None, input_max=None, cli_input=None, default=None, choices=None):
  prompt = _update_prompt(prompt, default)
  user_input = _check_input(prompt, cli_input, default)
  if user_input not in choices:
    print(f"{Fore.YELLOW}Selection must be one of the following {choices}{Style.RESET_ALL}")
    raise InvalidInput
  return user_input


@retry(stop_max_attempt_number=5, retry_on_exception=_retry_if_invalid_input)
def validate_ip_address(prompt, input_min=None, input_max=None, cli_input=None, default=None, choices=None):
  prompt = _update_prompt(prompt, default)
  user_input = _check_input(prompt, cli_input, default)
  if len(user_input.split('.')) != 4:
    print(f"{Fore.YELLOW}Not a properly formatted IP Address x.x.x.x{Style.RESET_ALL}")
    raise InvalidInput
  try:
    user_input = IPAddress(user_input)
  except AddrFormatError as e:
    print(f"{Fore.YELLOW}{e}{Style.RESET_ALL}")
    raise InvalidInput
  return user_input


@retry(stop_max_attempt_number=5, retry_on_exception=_retry_if_invalid_input)
def validate_ip_network(prompt, input_min=None, input_max=None, cli_input=None, default=None, choices=None):
  prompt = _update_prompt(prompt, default)
  user_input = _check_input(prompt, cli_input, default)
  if len(user_input.split('.')) != 4 or '/' not in user_input:
    print(f"{Fore.YELLOW}Not a properly formatted IP/CIDR x.x.x.x/x{Style.RESET_ALL}")
    raise InvalidInput
  try:
    user_input = IPNetwork(user_input)
  except AddrFormatError as e:
    print(f"{Fore.YELLOW}{e}{Style.RESET_ALL}")
    raise InvalidInput
  return user_input


@retry(stop_max_attempt_number=5, retry_on_exception=_retry_if_invalid_input)
def validate_interface(prompt, input_min=None, input_max=None, cli_input=None, default=None, choices=None):
  prompt = _update_prompt(prompt, default)
  user_input = _check_input(prompt, cli_input, default)
  if not re.match(r"(ge|xe|et)-0/0/(\d|[0-4]\d|5[0-1])$", user_input):
    print(f"{Fore.YELLOW}Interface format must be <type>-0/0/x where type is ge, xe, or et{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}5120 model supported range is from 0/0/0 thru 0/0/51 for hosts{Style.RESET_ALL}")
    raise InvalidInput
  return user_input


def _update_prompt(prompt, default):
  if default is not None:
    prompt = prompt + "[" + str(default) + "]: "
  return prompt


def _check_input(prompt, cli_input, default):
  if cli_input is None:
    user_input = input(prompt).strip()
  else:
    user_input = cli_input

  if user_input == "":
    if default is None:
      print(f"{Fore.YELLOW}Input cannot be blank, please try again{Style.RESET_ALL}")
      raise InvalidInput
    else:
      user_input = default
  return user_input
