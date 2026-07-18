#!/usr/bin/env python3
import sys
import os
from simple_term_menu import TerminalMenu

def main():
    options = ["1. System Health Check", "2. Security Tools (Tirith)", "3. Local AI Assistant", "4. Exit"]
    terminal_menu = TerminalMenu(options, title="Hive OS - Control Center")
    menu_entry_index = terminal_menu.show()
    
    if menu_entry_index == 0:
        print("Running Health Checks...")
    elif menu_entry_index == 1:
        print("Opening Security Audit Tools...")
    elif menu_entry_index == 2:
        print("Launching Local AI...")
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
