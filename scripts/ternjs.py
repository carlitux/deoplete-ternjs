import os
import platform
import subprocess

import vim

_tern_servers_by_path = {}


def tern_startServer():
    global _tern_servers_by_path

    try:
        tern_command = vim.eval('g:deoplete#sources#ternjs#tern_bin') or 'tern'
    except vim.error:
        tern_command = 'tern'

    env = None

    if platform.system() == 'Darwin':
        env = os.environ.copy()
        env['PATH'] += ':/usr/local/bin'

    cwd = os.getcwd()

    _tern_servers_by_path[cwd] = subprocess.Popen(
        [tern_command, '--persistent'],
        cwd=cwd,
        shell=platform.system() == "Windows",
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def tern_killServer():
    global _tern_servers_by_path
    for proc in _tern_servers_by_path.values():
        proc.stdin.close()
        proc.wait()
        proc = None
