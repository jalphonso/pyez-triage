from colorama import Fore, Style


class InvalidInput(Exception):
  def __init__(self):
    super().__init__("Invalid Input")
