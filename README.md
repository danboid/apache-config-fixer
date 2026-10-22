# apache-config-fixer

Python script to help get apache servers started. It must be run as root to work.

This script enables you to get to get an apache web server back up and running faster when `systemctl status apache2.service` is failing to start apache because some of its pages are not configured correctly by commenting out the problematic lines in apache config files.

This script doesn't really "fix" any apache configuration files. All it does is work out which bits of your apache servers config files are problematic for apache to start and then prompts you before commenting out those lines and trying to restart apache successfully. It does this in a loop with all apache config files until it can start apache without errors.

This script was tested with Python 3.10.12 and Apache 2.4.52 under Ubuntu. It has not been tested with Red Hat or Fedora based distros and in all cases I accept no responsibility far any data loss or damage that could arise from using this script. You use it entirely at your own risk.
