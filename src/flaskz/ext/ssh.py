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
from typing import Optional, Tuple, Union

import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException


@contextmanager
def ssh_session(hostname: str, username: str, password: str = None, port: Optional[int] = 22, **kwargs):
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


def ssh_run_command(connect_kwargs: dict, command: Union[str, list], run_kwargs: Optional[dict] = None) -> Tuple[bool, str]:
    """
    Run the specified command.
    If command is a list, by default, returns the list of results , if run_kwargs.last_result==True returns the result of the last command

    .. versionadded:: 1.6.4
    .. versionupdated::
        1.8.1   - add retries

    Example:
        ssh_run_command({'hostname': hostname, 'username': username, 'password': password},'show running-config')

        ssh_run_command(
            # connect_kwargs
            {'hostname': 'host', 'username': 'username', 'password': 'password',  # host
             'timeout': 10, 'retries': 3,  # connect timeout and retry
             'secondary_password': 'enable_pwd',  # enable password
             'recv_endswith': ['# ', '$ ', ': ', '? ', '#'],  # recv endswith
             'channel_kwargs': {'width': 1000, 'timeout': 2}},  # channel kwargs
            # command
            'show running-config',
            # run_kwargs
            {
                'clean': False,  # not clean output info
                'prompt': False,  # disable prompt
            })

    :param connect_kwargs: the connect kwargs, ex) {'hostname': hostname, 'username': username, 'password': password, 'timeout': 10}
    :param command: the specified command, ex) ls -l
    :param run_kwargs: the run command kwargs, ex) {'recv': False, 'prompt': False}
    :return: (success, result_or_err)
    """
    connect_kwargs = connect_kwargs or {}
    run_kwargs = run_kwargs or {}
    retries = connect_kwargs.pop('retries', None)
    if type(retries) is not int:  # @2025-01-12 add
        retries = 1
    else:
        retries = max(retries, 1)
    retry_count = 0
    while retry_count < retries:
        try:
            with ssh_session(**connect_kwargs) as ssh:
                if type(command) is list:
                    return True, ssh.run_command_list(command, **run_kwargs)
                else:
                    return True, ssh.run_command(command, **run_kwargs)
        except Exception as e:
            if retry_count == retries - 1:
                return False, str(e)
            retry_count = retry_count + 1
            time.sleep(0.1)


def ssh_run_command_list(connect_kwargs: dict, command_list: list, run_kwargs: Optional[dict] = None) -> Tuple[bool, Union[list, str]]:
    """
    Run a command list.
    By default, returns the list of results , if run_kwargs.last_result==True returns the result of the last command

    .. versionadded:: 1.6.4
    .. versionupdated::
        1.8.1   - add retries

    Example:
        ssh.run_command_list({'hostname': hostname, 'username': username, 'password': password}, ['show version', 'show running-config'])

        ssh_run_command_list(
            # connect_kwargs
            {'hostname': 'host', 'username': 'username', 'password': 'password',  # host
             'timeout': 10, 'retries': 3,  # connect timeout and retry
             'secondary_password': 'enable_pwd',  # enable password
             'recv_endswith': ['# ', '$ ', ': ', '? ', '#'],  # recv endswith
             'channel_kwargs': {'width': 1000, 'timeout': 2}},  # channel kwargs
            # command
            ['enable', 'show version'],
            # run_kwargs
            {
                'last_result': True,  # only return last result
                'prompt': False,  # disable prompt
            })

    :param connect_kwargs: the connect kwargs, ex) {'hostname': hostname, 'username': username, 'password': password, 'timeout': 10}
    :param command_list: the command list, ex) ['terminal length 0', 'show version', 'show running-config']
    :param run_kwargs: the run command kwargs, ex) {'recv': False, 'prompt': False}

    :return: (success, result_or_err)
    """
    connect_kwargs = connect_kwargs or {}
    run_kwargs = run_kwargs or {}
    retries = connect_kwargs.pop('retries', None)
    if type(retries) is not int:  # @2025-01-12 add
        retries = 1
    else:
        retries = max(retries, 1)
    retry_count = 0
    while retry_count < retries:
        try:
            with ssh_session(**connect_kwargs) as ssh:
                return True, ssh.run_command_list(command_list, **run_kwargs)
        except Exception as e:
            if retry_count == retries - 1:
                return False, str(e)
            retry_count = retry_count + 1
            time.sleep(0.1)


class SSH(object):
    def __init__(self, hostname, username, password=None, port=22, **kwargs):
        """
        Create a SSH instance.

        .. versionupdated::
            1.6   - add secondary_password and recv_endswith kwargs
            1.6.4 - add connect_kwargs and channel_kwargs kwargs
                  - add prompt param
                  - add prompt param and logic
                  - optimize _recv_data function
            1.7.0 - add transport.is_authenticated() and channel.exit_status_ready() check
                  - add recv_start_delay kwargs
            1.7.3 - add pre_commands kwargs

        Example:
            ssh = SSH(host, username, password)
            ssh.run_command('show version')
            ssh.run_command('ls -l')

            ssh = SSH(host, username, password, timeout=20)
            ssh.run_command_list(['show version', 'show running-config'])
            ssh.run_command_list(['enable', enable_pwd, 'show run'])

            ssh = SSH(host, username, password, timeout=20, secondary_password=enable_pwd, recv_endswith=['# ', '$ ', ': ', '? ', '#'], pre_commands=['terminal length 0'])
            ssh.run_command_list(['enable', 'show run'])
            ssh.run_command_list(['enable', 'show run'], last_result=True) # return last command output
            ssh.run_command_list(['show version', 'show clock', 'show running-config'])

        :param hostname: the host(address) to ssh
        :param username: the username of the host
        :param password: the password of the host
        :param port: the ssh port, default is 22
        :param kwargs:
                - secondary_password: use for enable/sudo action, if None, the password needs to be sent through the command
                - recv_endswith: use for stop receiving, default is ['# ', '$ ', ': ', '? ']
                - pre_commands: the commands that are run before the command/commands are actually run
                - timeout: timeout on blocking read/write operations & socket timer, default is 10
                - connect_kwargs: kwargs for Transport.connect()
        """
        self._username = username
        self._password = password
        self._secondary_password = kwargs.pop('secondary_password', None)  # for enable/sudo
        # recv_endswith = kwargs.pop('recv_endswith', None)  # for stop receiving
        self.recv_endswith = tuple(kwargs.pop('recv_endswith', None) or ['# ', '$ ', ': ', '? '])  # for stop receiving
        self.recv_start_delay = kwargs.pop('recv_start_delay', 0.1)  # @2023-12-31 add, delay before receiving data start
        if 'timeout' in kwargs:
            self._timeout = kwargs.pop('timeout', 0)
        else:
            self._timeout = 10

        if hostname is None and 'host' in kwargs:
            hostname = kwargs.pop('host', None)

        self._pre_commands = None  # @2024-04-14 add
        self._pre_commands_run = False
        pre_commands = kwargs.pop('pre_commands', None)
        if type(pre_commands) is str:
            pre_commands = [pre_commands]
        if type(pre_commands) is list and len(pre_commands) > 0:
            self._pre_commands = pre_commands

        # self.transport = paramiko.Transport((hostname, port))
        self.transport = paramiko.Transport(_create_socket(hostname=hostname, port=port, timeout=self._timeout))
        _connect_kwargs = kwargs.pop('connect_kwargs', None) or {}  # kwargs for Transport.connect()
        self.transport.connect(username=username, password=password, **_connect_kwargs)
        if self.transport.is_authenticated() is not True:  # @2023-12-28 add(Oops, unhandled type 3 ('unimplemented'))
            raise AuthenticationException('Authentication failed.')

        self._channel_kwargs = {'width': 100000, 'height': 100000}
        self._channel_kwargs.update(kwargs.pop('channel_kwargs', {}))
        if 'timeout' in self._channel_kwargs:
            self._channel_timeout = self._channel_kwargs.pop('timeout', 0)
        else:
            self._channel_timeout = self._timeout

        self.ssh = paramiko.SSHClient()
        self.ssh._transport = self.transport
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    @property
    def channel(self):
        if not hasattr(self, '_channel'):
            self._channel = self.ssh.invoke_shell(**self._channel_kwargs)  # @2023-10-31 add width
            if self._channel_timeout > 0:
                self._channel.settimeout(self._channel_timeout)
        return self._channel

    def run_command(self, command: str, recv: bool = True, clean: bool = True, prompt=None) -> Union[str, None]:
        """
        Run the specified command.
        If recv is False, just run the command and return immediately, without waiting for the result

        .. versionupdated::
            1.6.1   - @2023-06-26 add recv parameter
            1.6.3   - @2023-07-10 add clean parameter
            1.6.4   - @2023-10-30 add prompt parameter & logic

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
         :param prompt: the prompt of the command line

         :return: the output of the command
        """

        if self._pre_commands_run is False and self._pre_commands:
            self._run_command('', False)
            pre_command_len = len(self._pre_commands)
            for index, pre_command in enumerate(self._pre_commands):
                self._run_command(pre_command, index == pre_command_len - 1)
            self._pre_commands_run = True

        if prompt is None:  # prompt is False for config
            prompt = self.get_prompt()  # 1.get prompt 2.remove welcome

        command, recv, clean = _get_command_arg(command, recv, clean)
        output = self._run_command(command, recv, prompt)
        if output is None:
            return None

        if self._is_secondary_login(command, output):
            secondary_login_output = self._secondary_login(output)
            if secondary_login_output is False:
                return output
            else:
                if _is_enable_command(command, True):  # sudo ls --> secondary_login --> return result, no need to resend
                    output = secondary_login_output
                else:
                    if prompt is not False:
                        prompt = self.get_prompt()
                    output = self._run_command(command, recv)

        if output is None:
            return output

        if clean is not False:
            output = _clean_output(output, command, prompt)

        return output

    def run_command_list(self, command_list: list, last_result: bool = False, **kwargs) -> Union[list, str]:
        """
        Run a command list.
        By default, returns the list of results , if last_result==True returns the result of the last command

        Example:
            ssh.run_command_list(['show version', 'show running-config'])
            ssh.run_command_list(['enable', 'show version'], True)
            ssh.run_command_list(['enable',secondary_password, 'show version'], True)
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
        prompt = kwargs.get('prompt', None)  # @2024-03-26 kwargs.get('kwargs', None) --> kwargs.get('prompt', None)
        if prompt is None:
            kwargs['prompt'] = self.get_prompt()  # for reuse
        count = len(command_list)
        for index, command in enumerate(command_list):
            if last_result is True:
                if index == count - 1:  # last
                    return self.run_command(command, **kwargs)
                else:
                    self.run_command(command, **kwargs)  # recv can not be false, ex)enable --> recv --> secondary_password
            else:
                re_list.append(self.run_command(command, **kwargs))
        return re_list

    def get_prompt(self) -> str:
        """
        Return the prompt of the command line

        .. versionadded:: 1.6.4

        Example:
            ssh.get_prompt()

        :return:
        """
        output = self._run_command('', recv=True)
        newline_pos = max(output.rfind('\n'), output.rfind('\r'))

        return output[newline_pos + 1:].lstrip('\r\n') if newline_pos != -1 else output

    def close(self):
        """Close the connect"""
        self.channel.close()
        self.ssh.close()

    @property
    def sftp(self):
        if not hasattr(self, '_sftp'):
            self._sftp = paramiko.SFTPClient.from_transport(self.transport)
        return self._sftp

    def sftp_get_dir(self, remote_dir, local_dir):
        """
        Download remote direction to local.
        Return the local files list.

        Example:
            ssh.sftp_get_dir('/usr/projects/git/srte/src/', '/Users/taozh/Work/Codes/ssh_test/sftp')
        """
        if not self._is_path_exists(remote_dir):
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

    def _run_command(self, command, recv=True, prompt=None):
        _command = command  # @2025-02-03 remove strip()
        if not _command.strip(' ').endswith(('?', '\t')):  # @2025-02-03 add
            _command = _command + '\n'
        self.channel.send(_command)
        if recv is False:
            return None
        output = self._recv_data(prompt)
        return output

    def _is_secondary_login(self, command, output):
        """
        Determine whether a secondary login is required by checking output text
        """
        if 'assword' not in output:  # input password
            return False
        secondary_password = self._secondary_password  # or self._password
        if secondary_password is None:
            return False
        return _is_enable_command(command)

    def _secondary_login(self, output):
        """
        Secondary login
        return
            - True, if success
            - False, if fail
        """
        secondary_password = self._secondary_password
        pwd_output = self._run_command(secondary_password)
        if pwd_output == output:
            return False
        return pwd_output

    def _is_path_exists(self, path):
        """Return whether the path exists"""
        try:
            self.sftp.stat(path)
        except IOError as e:
            if e.errno == errno.ENOENT:
                return False
            raise
        else:
            return True

    def _recv_data(self, prompt=None):
        """Receive the command output"""
        # cmd_pattern = re.compile('.*[#$] ' + command) # Does not work with password entry

        res_list = []
        if type(prompt) is not str:
            prompt = None

        recv_ready_timeout = self._channel_timeout if self._channel_timeout > 0 else 6
        recv_start = None
        count = 0
        recv_max_bytes = 1024
        recv_start_delay = self.recv_start_delay
        while True:
            if self.channel.exit_status_ready() is True:  # @2023-12-27 add for 'exit' command
                break
            if not self.channel.recv_ready():
                now = datetime.now()
                if recv_start is None:
                    recv_start = now
                else:
                    if (now - recv_start).total_seconds() > recv_ready_timeout:
                        if count == 0:
                            raise socket.timeout()
                        else:
                            break
                time.sleep(0.01)
                continue
            else:
                recv_start = None
                if count == 0:  # Solve the problem of incomplete data
                    time.sleep(recv_start_delay)
            count += 1
            data = self.channel.recv(recv_max_bytes)
            info = data.decode('utf-8', 'backslashreplace')  # @2024-04-18 data.decode() --> current
            res = info.replace(' \r', '')
            res = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', res)  # @2025-02-03 add
            res_list.append(res)
            if len(info) < recv_max_bytes:  # read speed > write speed
                if (prompt is not None and info.endswith(prompt)) or info.endswith(self.recv_endswith):
                    time.sleep(0.02)  # Make sure recv is finished, info.endswith(self.recv_endswith) Not 100% sure
                    if not self.channel.recv_ready():
                        break

        return ''.join(res_list)


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


def _get_command_arg(command, recv, clean):
    if type(command) is dict:
        _command = command.get('command')  # @2025-02-03 remove strip()
        _recv = command.get('recv') is not False if 'recv' in command else recv
        _clean = command.get('clean') is not False if 'clean' in command else clean
    else:
        _command = command  # @2025-02-03 remove strip()
        _recv = recv
        _clean = clean
    return _command, _recv, _clean


def _is_enable_command(command, sudo=False):
    if sudo is True:
        return command.lower().startswith('sudo ')
    else:
        return command.lower().startswith(('sudo ', 'enable'))


def _clean_output(output, command, prompt):
    """
    Clear the redundant information.
    - Welcome info      ex)Welcome to Ubuntu...
    - Last login info   ex)Last login...
    - Path info         ex)[root@localhost ~]...
    - Command info      ex) [root@localhost ~] ls -l
    - Return prompt     ex) [root@localhost ~]

    """
    # remove the start command  ex) ls -l
    if output.startswith(command):
        output = output[len(command):].lstrip('\r\n')  # 2024-04-05 add '\r\n' to keep space

    prompt_matched = False
    if type(prompt) is str:  # for show
        # 1.remove text before command ex) [root@localhost ~]# ls -l
        cmd_prompt = prompt + command
        cmd_start = output.rfind(cmd_prompt)
        if cmd_start > -1:
            output = output[cmd_start + len(cmd_prompt):]
        prompt_start = output.rfind(prompt)
        # 2.remove the last prompt ex) [root@localhost ~]#
        if prompt_start > -1:
            output = output[:prompt_start]
        prompt_matched = cmd_start > -1 or prompt_start > -1

    if prompt_matched is False:  # for config
        # 1.remove text before command ex) [root@localhost ~]# ls -l
        cmd_pattern = re.compile('.*([#$])( )*' + re.escape(command))  # @2023-06-07 change ([#$])? --> ([#$])
        last_match = None
        for match in cmd_pattern.finditer(output):
            last_match = match
        if last_match:
            output = output[last_match.end():]
        # 2.remove the last prompt ex) [root@localhost ~]#
        path_pattern = re.compile('.*[#$]( )?$')  # @2023-07-06 change '.*[#$] ' --> '.*[#$]( )?'
        path_match = path_pattern.search(output)  # @2023-10-26 change sub()-->search(), '.*[#$]( )?'-->'.*[#$]( )?$'
        if path_match:
            path_match_start, path_match_end = path_match.span()
            output = output[:path_match_start] + '' + output[path_match_end:]
        output = output.replace(command + '\r\n', '')

    return output.strip('\r\n')  # 2024-04-05 add '\r\n' to keep space


def _remove_end_slash(path):
    """Remove ending slash """
    if path[-1] == '/':
        return path[0:-1]
    return path
