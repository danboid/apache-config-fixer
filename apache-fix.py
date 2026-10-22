#!/usr/bin/env python3

# apache-fix.py is a Python script to help get apache servers with faulty config files fixed faster
# by commenting out the problematic lines in apache configuration files.

# It must be run as root or using sudo with suitable permissions to edit all apache config files.
# Only tested under Ubuntu so far.
# By Dan MacDonald, 2026

import subprocess
import re
import glob
import sys
import os

def test_apache_start():
    """Attempts to start Apache via systemctl and retrieves output from both journalctl and error.log."""
    subprocess.run(['systemctl', 'stop', 'apache2'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    result = subprocess.run(['systemctl', 'start', 'apache2'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    output = ""
    # 1. Get journal logs
    journal = subprocess.run(
        ['journalctl', '-u', 'apache2.service', '-n', '300', '--no-pager'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    output += journal.stdout + journal.stderr
    
    # 2. Get explicit text error log content
    error_log_path = '/var/log/apache2/error.log'
    if os.path.exists(error_log_path):
        try:
            with open(error_log_path, 'r') as f:
                lines = f.readlines()
                output += "\n" + "".join(lines[-300:])
        except Exception:
            pass
            
    return result.returncode == 0, output

def find_document_root_in_configs(docroot_path):
    """Searches /etc/apache2/sites-enabled/*.conf for an ACTIVE DocumentRoot pointing to the missing path."""
    conf_files = glob.glob('/etc/apache2/sites-enabled/*.conf')
    for conf_file in conf_files:
        try:
            with open(conf_file, 'r') as f:
                for idx, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        continue
                    if 'DocumentRoot' in line and docroot_path in line:
                        return conf_file, idx
        except Exception:
            continue
    return None, None

def find_ssl_error_in_configs(domain):
    """Searches /etc/apache2/sites-enabled/*.conf for the config matching the domain and finds active SSLEngine on."""
    conf_files = glob.glob('/etc/apache2/sites-enabled/*.conf')
    for conf_file in conf_files:
        try:
            with open(conf_file, 'r') as f:
                content = f.read()
                if domain in content:
                    for idx, line in enumerate(content.splitlines(), 1):
                        stripped = line.strip()
                        if stripped.startswith('#'):
                            continue
                        if 'sslengine' in line.lower() and 'on' in line.lower():
                            return conf_file, idx
        except Exception:
            continue
    return None, None

def parse_error(output):
    """Parses Apache logs in reverse (newest first) for syntax errors, DocumentRoot warnings, and SSL failures."""
    lines = output.splitlines()
    rev_lines = list(reversed(lines))

    # 1. Check for SSL certificate / engine failures first (AH02572)
    for line in rev_lines:
        if 'AH02572' in line or 'Failed to configure at least one certificate' in line:
            domain_match = re.search(r'for\s+([^\s:]+)', line)
            if domain_match:
                domain = domain_match.group(1).strip()
                file_path, line_no = find_ssl_error_in_configs(domain)
                if file_path and line_no:
                    # Ensure line is not already commented out
                    with open(file_path, 'r') as cf:
                        cf_lines = cf.readlines()
                        if not cf_lines[line_no - 1].strip().startswith('#'):
                            return file_path, line_no

    # 2. Check for standard syntax or wrapper errors
    for line in rev_lines:
        match = re.search(r'on line (\d+) of ([^:\n]+)', line)
        if match:
            line_no = int(match.group(1))
            file_path = match.group(2).strip()
            file_path = re.sub(r'[\'"]$', '', file_path)
            
            if os.path.exists(file_path):
                with open(file_path, 'r') as cf:
                    cf_lines = cf.readlines()
                    if 0 <= line_no - 1 < len(cf_lines):
                        if not cf_lines[line_no - 1].strip().startswith('#'):
                            return file_path, line_no

    # 3. Check for DocumentRoot warnings (AH00112)
    for line in rev_lines:
        if 'AH00112' in line or 'DocumentRoot' in line:
            path_match = re.search(r'DocumentRoot\s+\[?([^\]\s]+)\]?', line)
            if path_match:
                docroot_path = path_match.group(1).strip()
                file_path, line_no = find_document_root_in_configs(docroot_path)
                if file_path and line_no:
                    return file_path, line_no

    # 4. Fallback search for any .conf path mentioned in logs
    for line in rev_lines:
        path_match = re.search(r'(/etc/apache2/[^\s]+\.conf)', line)
        if path_match:
            file_path = path_match.group(1).strip()
            line_match = re.search(r'line\s+(\d+)', line, re.IGNORECASE)
            line_no = int(line_match.group(1)) if line_match else 1
            
            if os.path.exists(file_path):
                with open(file_path, 'r') as cf:
                    cf_lines = cf.readlines()
                    if 0 <= line_no - 1 < len(cf_lines):
                        if not cf_lines[line_no - 1].strip().startswith('#'):
                            return file_path, line_no

    return None, None

def comment_out_block(file_path, start_line, num_lines=1):
    """Presents a proposed line to comment out and applies changes if approved."""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return False

    with open(file_path, 'r') as f:
        lines = f.readlines()

    idx = start_line - 1
    if idx < 0 or idx >= len(lines):
        print(f"Error: Line {start_line} is out of bounds for {file_path} (Total lines: {len(lines)}).")
        idx = 0
        start_line = 1

    end_idx = min(idx + num_lines, len(lines))
    
    print(f"\n--- Proposed changes in {file_path} (Lines {start_line} to {start_line + (end_idx - idx) - 1}) ---")
    for i in range(idx, end_idx):
        print(f"{i + 1}: {lines[i].rstrip()}")
    print("-" * 65)

    choice = input("Do you want to comment out these lines? [y/n/custom/quit]: ").strip().lower()
    
    if choice == 'y':
        for i in range(idx, end_idx):
            if not lines[i].strip().startswith('#'):
                indent = len(lines[i]) - len(lines[i].lstrip())
                lines[i] = lines[i][:indent] + '# ' + lines[i][indent:]
        
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print("Changes applied successfully.")
        return True
        
    elif choice == 'custom':
        try:
            custom_count = int(input(f"How many lines to comment out starting from line {start_line}? "))
            end_idx = min(idx + custom_count, len(lines))
            for i in range(idx, end_idx):
                if not lines[i].strip().startswith('#'):
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    lines[i] = lines[i][:indent] + '# ' + lines[i][indent:]
            with open(file_path, 'w') as f:
                f.writelines(lines)
            print("Custom block commented out.")
            return True
        except ValueError:
            print("Invalid number entered. Skipping.")
            return False
            
    elif choice == 'quit':
        sys.exit(0)
    else:
        print("Skipped this error block.")
        return False

def main():
    if os.geteuid() != 0:
        print("Error: This script must be run with root privileges (sudo).")
        sys.exit(1)
    
    print("Starting automated Apache startup repair loop...")
    
    while True:
        success, output = test_apache_start()
        
        if success:
            print("\n[SUCCESS] Apache started successfully!")
            break
        
        print("\n[APACHE STARTUP FAILURE DETECTED]")
        
        file_path, line_no = parse_error(output)
        if not file_path or not line_no:
            print("\nNo more active unhandled configuration errors found in logs.")
            file_path = input("Enter config file path manually (or leave blank to exit): ").strip()
            if not file_path:
                break
            try:
                line_no = int(input("Enter starting line number: "))
            except ValueError:
                print("Invalid line number. Exiting.")
                break
        
        print(f"Found error targeting: {file_path} at line {line_no}")
        applied = comment_out_block(file_path, line_no, num_lines=1)
        if not applied:
            cont = input("No changes were made. Continue fixing next errors or quit? [c/q]: ").strip().lower()
            if cont == 'q':
                break

if __name__ == '__main__':
    main()
