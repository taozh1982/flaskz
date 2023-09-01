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

import paramiko
from paramiko.ssh_exception import SSHException


@contextmanager
def ssh_session(hostname, username, password=None, port=22, **kwargs):
    """
    SSH contextmanager.

    Example:
        with ssh_session(host, username, password, timeout=20) as ssh:
            ssh.run_command('ls -l')

        with ssh_session(host, username, password, timeout=20) as ssh:
            ssh.run_command_list(['show version', 'show running-config'])

        with ssh_session(host, username, password, timeout=20, secondary_password=enable_pwd, recv_endswith=['# ', '$ ', ': ', '? ', '#']) as ssh:
            ssh.run_command_list(['enable', 'show run'])

    """
    ssh_client = SSH(hostname=hostname, username=username, password=password, port=port, **kwargs)
    yield ssh_client
    ssh_client.close()


class SSH(object):
    def __init__(self, hostname, username, password=None, port=22, **kwargs):
        """
        Create a SSH instance.

        .. versionupdated:: 1.6 - add secondary_password and recv_endswith kwargs

        Example:
            ssh = SSH(host, username, password, timeout=20)
            ssh.run_command('ls -l')

            ssh = SSH(host, username, password, timeout=20)
            ssh.run_command_list(['enable', enable_pwd, 'show run'])

            ssh = SSH(host, username, password, timeout=20, secondary_password=enable_pwd, recv_endswith=['# ', '$ ', ': ', '? ', '#'])
            ssh.run_command_list(['enable', 'show run'])


        :param hostname: the host(address) to ssh
        :param username: the username of the host
        :param password: the password of the host
        :param port: the ssh port, default is 22
        :param kwargs:
                - secondary_password: use for enable/sudo action, if None, the password needs to be sent through the command
                - recv_endswith: use for stop receiving, default is ['# ', '$ ', ': ', '? ']
                - timeout: timeout on blocking read/write operations & socket timer, default is 0
                - connect_kwargs: kwargs for Transport.connect()
        """
        self._username = username
        self._password = password
        self._secondary_password = kwargs.pop('secondary_password', None)  # for enable/sudo
        # recv_endswith = kwargs.pop('recv_endswith', None)  # for stop receiving
        self.recv_endswith = tuple(kwargs.pop('recv_endswith', None) or ['# ', '$ ', ': ', '? '])  # for stop receiving
        self._timeout = kwargs.pop('timeout', 0)

        # self.transport = paramiko.Transport((hostname, port))
        self.transport = paramiko.Transport(_create_socket(hostname=hostname, port=port, timeout=self._timeout))
        _connect_kwargs = kwargs.pop('connect_kwargs', None) or {}  # kwargs for Transport.connect()
        self.transport.connect(username=username, password=password, **_connect_kwargs)

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

    def run_command(self, command, recv=True, clean=True):
        """
        Run the command.
        If recv is False, just run the command and return immediately, without waiting for the result

        .. versionupdated::
            1.6.1   - @2023-06-26 add recv parameter
            1.6.3   - @2023-07-10 add clean parameter

        Example:
            ssh.run_command('ls -l')
            ssh.run_command('show run')
            ssh.run_command({
                'command': ' ',
                'clean': False,
            })

         :param command: the command to run.
         :param recv: wait for the result or not.
         :param clean: clean output info or not, default True(clean)

         :return: the output of the command
        """
        _command, _recv, _clean = _get_command_arg(command, recv=recv, clean=clean)

        _command = _command.strip()
        self.channel.send(_command + '\n')
        if _recv is False:
            return None

        output = self._get_output(_command, clean=_clean)
        enable_commands = ('sudo', 'enable')
        secondary_password = self._secondary_password  # or self._password
        if secondary_password and \
                _command.lower().startswith(enable_commands) and \
                'assword' in output:  # input password
            pwd_output = self.run_command(secondary_password)
            # if 'assword' in pwd_output:
            if pwd_output == output:
                return output
            return self.run_command(_command)

        return output

    def run_command_list(self, command_list, last_result=False):
        """
        Run a command list.
        By default, returns the list of results , if last_result==True returns the result of the last command

        Example:
            ssh.run_command_list(['cd /usr/projects/git/srte',
                      'pwd',
                      'git pull origin master',
                      'wiui@hotmail.com',
                      '11111111'
                      ], True)

         :param command_list: the command list to run.
         :param last_result: if True, return the result of the last command, otherwise, return the result list

         :return: command output result(list/last)
        """
        re_list = []
        for command in command_list:
            re_list.append(self.run_command(command))
        if last_result is True:
            return re_list[-1]
        return re_list

    def sftp_get_dir(self, remote_dir, local_dir):
        """
        Download remote direction to local.
        Return the local files list.

        Example:
            ssh.sftp_get_dir('/usr/projects/git/srte/src/', '/Users/taozh/Work/Codes/ssh_test/sftp')
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
        List all files in the given path.

        Example:
            ssh.listdir('/usr/projects/git/srte/src/')
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

    def _get_output(self, command, clean=True):
        output = self._recv_data()
        if clean is not False:
            output = _clean_output_info(output, command)
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
                if info.endswith(self.recv_endswith):  # Cisco C9300:# /
                    break

        return ''.join(res_list)


def _get_command_arg(command, recv, clean):
    if type(command) is dict:
        _command = command.get('command')
        _recv = command.get('recv') is not False if 'recv' in command else recv
        _clean = command.get('clean') is not False if 'clean' in command else clean
    else:
        _command = command
        _recv = recv
        _clean = clean
    return _command, _recv, _clean


def _create_socket(hostname, port, timeout=0):
    """
    Create socket instance.
    If timeout>0, set the timeout of the instance, otherwise use the default timeout(maybe 75s).

    :param hostname:
    :param port:
    :param timeout:
    :return:
    """

    reason = 'No suitable address family'
    addrinfos = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    for family, socktype, proto, canonname, sockaddr in addrinfos:
        if socktype == socket.SOCK_STREAM:
            sock = socket.socket(family, socket.SOCK_STREAM)
            if timeout > 0:
                sock.settimeout(timeout)
            try:
                # retry_on_signal(lambda: sock.connect((hostname, port))) # @2023-06-09 change, remove paramiko.util.retry_on_signal(Paramiko3.0.0 2023-01-20)
                sock.connect((hostname, port))
            except socket.error as e:
                reason = str(e)
            else:
                break
    else:
        raise SSHException(
            'Unable to connect to {}: {}'.format(hostname, reason)
        )
    return sock


def _clean_output_info(txt, command):
    """
    Clear the redundant information.
    - Welcome info      ex)Welcome to Ubuntu...
    - Last login info   ex)Last login...
    - Path info         ex)[root@localhost ~]...
    - Command info      ex)ls -l

    """
    # remove the start command  ex) ls -l
    if txt.startswith(command):
        txt = txt[len(command):].lstrip()

    # remove text before command ex) [root@localhost ~]# ls -l
    cmd_pattern = re.compile('.*([#$])( )*' + re.escape(command))  # @2023-06-07 change ([#$])? --> ([#$])
    last_match = None
    for match in cmd_pattern.finditer(txt):
        last_match = match
    if last_match:
        txt = txt[last_match.end():]
    path_pattern = re.compile('.*[#$]( )?')  # @2023-07-06 change '.*[#$] ' --> '.*[#$]( )?'
    txt = path_pattern.sub('', txt)  # remove the path info
    txt = txt.replace(command + '\r\n', '')  # remove the command
    return txt.strip()


def _remove_end_slash(path):
    """Remove ending slash """
    if path[-1] == '/':
        return path[0:-1]
    return path
