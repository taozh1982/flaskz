"""
pip install paramiko
"""
import errno
import os
import re
import socket
import stat
import time
from contextlib import contextmanager
from datetime import datetime

import paramiko
from paramiko.ssh_exception import SSHException
from paramiko.util import retry_on_signal


@contextmanager
def ssh_session(hostname, username, password=None, port=22, **kwargs):
    """
    with ssh_session(host, username, password, timeout=20) as ssh:
        ssh.run_command("ls -l")
    """
    ssh_client = SSH(hostname=hostname, username=username, password=password, port=port, **kwargs)
    yield ssh_client
    ssh_client.close()


class SSH(object):
    def __init__(self, hostname, username, password=None, port=22, **kwargs):
        """
        ssh = SSH(host, username, password, timeout=20)
        """
        self._username = username
        self._password = password

        self._timeout = kwargs.pop('timeout', 0)
        self.transport = paramiko.Transport(_create_socket(hostname=hostname, port=port, timeout=self._timeout))
        # self.transport = paramiko.Transport((hostname, port))
        self.transport.connect(username=username, password=password, **kwargs)

        self.ssh = paramiko.SSHClient()
        self.ssh._transport = self.transport
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    @property
    def sftp(self):
        if not hasattr(self, '_sftp'):
            self._sftp = paramiko.SFTPClient.from_transport(self.transport)
        return self._sftp

    @property
    def channel(self):
        if not hasattr(self, '_channel'):
            self._channel = self.ssh.invoke_shell(height=100000)
            if self._timeout > 0:
                self._channel.settimeout(self._timeout)
        return self._channel

    def run_command(self, command):
        """
        Run the command
        ssh.run_command("ls -l")
        """
        command = command.strip()
        self.channel.send(command + '\n')
        output = self._get_output(command)

        if self._password and command.lower().startswith('sudo') and 'assword' in output:  # input password
            pwd_ouput = self.run_command(self._password)
            if 'assword' in pwd_ouput:
                return output
            return self.run_command(command)

        return output

    def run_command_list(self, command_list, last_result=False):
        """
        Run a command list
        By default, returns the list of results , if last_result==True returns the result of the last command
        ssh.run_command_list(['cd /usr/projects/git/srte',
                      'pwd',
                      'git pull origin master',
                      'wiui@hotmail.com',
                      '11111111'
                      ], True)
        """
        re_list = []
        for command in command_list:
            re_list.append(self.run_command(command))
        if last_result is True:
            return re_list[-1]
        return re_list

    def sftp_get_dir(self, remote_dir, local_dir):
        """
        Download remote direction to local
        Return the local files list
        ssh.sftp_get_dir("/usr/projects/git/srte/src/", "/Users/taozh/Work/Codes/ssh_test/sftp")
        """
        if not self._path_exists(remote_dir):
            return False
        remote_dir = _remove_end_slash(remote_dir)
        local_dir = _remove_end_slash(local_dir)
        if not os.path.exists(local_dir):
            os.mkdir(local_dir)
        all_files = self.listdir(remote_dir, True)
        local_files = []
        for f in all_files:
            local_filename = f.replace(remote_dir, local_dir)
            local_filepath = os.path.dirname(local_filename)
            local_files.append(local_filepath)
            if not os.path.exists(local_filepath):
                os.makedirs(local_filepath)
            self.sftp.get(f, local_filename)
        return local_files

    def listdir(self, path, recursion=False):
        """
        List all files in the given path
        ssh.listdir("/usr/projects/git/srte/src/")
        """
        all_files = []
        path = _remove_end_slash(path)
        if path[-1] == '/':
            path = path[0:-1]
        files = self.sftp.listdir_attr(path)
        for f in files:
            filename = path + '/' + f.filename
            if stat.S_ISDIR(f.st_mode):  # 如果是文件夹的话递归处理
                if recursion is True:
                    all_files.extend(self.listdir(filename, recursion))
            else:
                all_files.append(filename)
        return all_files

    def close(self):
        """Close the connect"""
        self.channel.close()
        self.ssh.close()

    def _path_exists(self, path):
        """Return whether the path exists"""
        try:
            self.sftp.stat(path)
        except IOError as e:
            if e.errno == errno.ENOENT:
                return False
            raise
        else:
            return True

    def _get_output(self, command):
        output = self._recv_data()
        output = _clear_redundant(output, command)
        return output

    def _recv_data(self):
        """Receive the command output"""
        while not self.channel.recv_ready():
            time.sleep(0.01)
        res_list = []
        time.sleep(0.2)  # Solve the problem of incomplete data
        # cmd_pattern = re.compile('.*[#$] ' + command) # Does not work with password entry
        while True:
            data = self.channel.recv(1024)
            info = data.decode()
            res = info.replace(' \r', '')
            res_list.append(res)
            if len(info) < 1024:  # read speed > write speed
                if info.endswith(('# ', '$ ', ': ', '? ')):
                    break

        return ''.join(res_list)


def _create_socket(hostname, port, timeout=0):
    """
    Create socket instance
    If timeout>0, set the timeout of the instance, otherwise use the default timeout(maybe 75s).
    :param hostname:
    :param port:
    :param timeout:
    :return:
    """
    reason = "No suitable address family"
    addrinfos = socket.getaddrinfo(
        hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM
    )
    for family, socktype, proto, canonname, sockaddr in addrinfos:
        if socktype == socket.SOCK_STREAM:
            sock = socket.socket(family, socket.SOCK_STREAM)
            if timeout > 0:
                sock.settimeout(timeout)
            now = datetime.now()
            try:
                retry_on_signal(lambda: sock.connect((hostname, port)))
            except socket.error as e:
                reason = str(e)
                print(datetime.now() - now)
            else:
                break
    else:
        raise SSHException(
            "Unable to connect to {}: {}".format(hostname, reason)
        )
    return sock


def _clear_redundant(txt, command):
    """
    Clear the redundant information
    - Welcome info      ex)Welcome to Ubuntu...
    - Last login info   ex)Last login...
    - Path info         ex)[root@localhost ~]...
    - Command info      ex)ls -l

    """
    # remove the start command  ex) ls -l
    if txt.startswith(command):
        txt = txt[len(command):].lstrip()

    # remove text before command ex) [root@localhost ~]# ls -l
    cmd_pattern = re.compile('.*([#$])?( )*' + re.escape(command))
    last_match = None
    for match in cmd_pattern.finditer(txt):
        last_match = match
    if last_match:
        txt = txt[last_match.end():]
    path_pattern = re.compile('.*[#$] ')
    txt = path_pattern.sub('', txt)  # remove the path info
    txt = txt.replace(command + '\r\n', '')  # remove the command
    return txt.strip()


def _remove_end_slash(path):
    """Remove ending slash """
    if path[-1] == '/':
        return path[0:-1]
    return path


if __name__ == '__main__':
    servers = [
        {  # Centos
            'host': '10.124.4.21',
            'username': 'admin1',
            'password': 'Cisco@123',
            'commands': ['show int eth3/1']
        },
        # {  # Centos
        #     'host': '10.124.5.222',
        #     'username': 'root',
        #     'password': 'cisco123',
        #     'commands': ['ls -l', 'cd ../opt', '\cp a.txt b.txt']
        # },
        # {  # Ubuntu
        #     'host': '10.124.5.198',
        #     'username': 'root',
        #     'password': 'Cisco@123',
        #     'commands': ['ls -l']
        # },
        # {  # Ubuntu, test input password
        #     'host': '10.124.205.216',
        #     'username': 'cisco',
        #     'password': 'cisco123',
        #     'commands': ['sudo ls -l']
        # },
        # {  # NX-OS
        #     'host': '10.124.11.134',
        #     'username': 'admin',
        #     'password': 'Cisco@123',
        #     'commands': ['show version', 'show running-config']
        # },
        # {  # NX-OS
        #     'host': '10.66.94.62',
        #     'username': 'admin',
        #     'password': 'cisco!123',
        #     'commands': ['show version', 'show running-config']
        # }
    ]
    for item in servers:
        print((item.get('host') + " : " + str(item.get("commands"))).center(100, '*'))
        with ssh_session(item.get('host'), item.get('username'), item.get('password'), timeout=10) as ssh:
            print(ssh.run_command_list(item.get('commands'), True))

    # ssh.sftp_get_dir("/usr/projects/git/srte/src/", "/Users/taozh/Work/Codes/ssh_test/sftp")
    print('\n', 'end'.center(100, '-'))
