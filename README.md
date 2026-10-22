# apache-config-fixer

apache-fix.py is a Python script to help get apache servers with faulty config files started faster.

It enables you to get to get an apache web server back up and running faster when `systemctl status apache2.service` is failing to start apache because some of its pages are not configured correctly by commenting out the problematic lines in apache configuration files. It must be run as root or using sudo with suitable permissions to edit all apache config files.

It doesn't really "fix" any apache configuration files. All it does is work out which bits of your apache site's config files are problematic for apache to start and then prompts you with a suggested fix before commenting out those lines (simply by typing 'y' and pushing ENTER) before restarting apache and retrying to start the apache service. apache-fix.py does this with all active and problematic apache config files until it can start apache without errors.

apache-fix.py was tested with Python 3.10.12 and Apache 2.4.52 under Ubuntu. It should aldo work fine on Debian based apache servers but it has not been tested with Red Hat or Fedora based distros so YMMV. In all cases I accept no responsibility far any data loss or damage that could arise from using this script. You use it entirely at your own risk.
