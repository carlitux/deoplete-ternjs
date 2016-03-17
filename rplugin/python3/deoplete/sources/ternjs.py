# pylint: disable=E0401,C0111,R0903

import os
import re
import json
import sys
import platform
import subprocess
import time

from deoplete.sources.base import Base
# from deoplete.util import load_external_module
from logging import getLogger

PY2 = int(sys.version[0]) == 2

if PY2:
    import urllib2 as request
    from urllib2 import HTTPError
else:  # Py3
    from urllib import request
    from urllib.error import HTTPError


opener = request.build_opener(request.ProxyHandler({}))
current = __file__
# load_external_module(current, 'sources/deoplete_ternjs')
# from profiler import timeit

logger = getLogger(__name__)
windows = platform.system() == "Windows"


class RequestError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class Source(Base):

    def __init__(self, vim):
        super(Source, self).__init__(vim)

        self.name = 'ternjs'
        self.mark = '[ternjs]'
        self.input_pattern = r'\.\w*'
        self.rank = 700
        self.filetypes = ['javascript', 'jsx', 'javascript.jsx']

        self._project_directory = None
        self.port = None
        self.localhost = (windows and "127.0.0.1") or "localhost"
        self.proc = None
        self.last_failed = 0
        self.cached = {'row': -1, 'end': -1}
        self._tern_command = 'tern'
        self._tern_arguments = ''
        self._tern_buffer_sent_at = {'undo_tree': None, 'ch': None}

        if vim.eval('exists("g:tern_request_timeout")'):
            self._tern_timeout = float(vim.eval("g:tern_request_timeout"))
        else:
            self._tern_timeout = 1

        # Used to avoid try to start server if not file found
        self._not_tern_project_file_found = False

        # Start server
        self.start_server()

    def __del__(self):
        self.stop_server()

    def start_server(self):
        if not self._tern_command:
            return None

        if time.time() - self.last_failed < 30:
            return None

        self._search_tern_project_dir()
        env = None

        if platform.system() == 'Darwin':
            env = os.environ.copy()
            env['PATH'] += ':/usr/local/bin'

        self.proc = subprocess.Popen(self._tern_command + ' ' + self._tern_arguments,
                                     cwd=self._project_directory, env=env,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     shell=True)
        output = ""

        while True:
            line = self.proc.stdout.readline().decode("utf-8")
            if not line:
                print("Failed to start server" + (output and ":\n" + output))
                self.last_failed = time.time()
                return None

            match = re.match("Listening on port (\\d+)", line)
            if match:
                self.port = int(match.group(1))
                return
            else:
                output += line

    def stop_server(self):
        if self.proc is None:
            return

        self.proc.stdin.close()
        self.proc.wait()
        self.proc = None

    def _search_tern_project_dir(self):
        if not self._project_directory and not self._not_tern_project_file_found:
            directory = self.vim.eval("expand('%:p:h')")

            if PY2:
                directory = directory.decode(self.vim.eval('&encoding'))

            if not os.path.isdir(directory):
                return ''

            if directory:
                self._project_directory = directory
                while True:
                    parent = os.path.dirname(directory[:-1])

                    if not parent:
                        self._not_tern_project_file_found = True
                        break

                    if os.path.isfile(os.path.join(directory, '.tern-project')):
                        self._project_directory = directory
                        break

                    directory = parent

    def make_request(self, doc, silent):
        payload = json.dumps(doc)
        # self.debug(payload)
        if not PY2:
            payload = payload.encode('utf-8')
        try:
            req = opener.open("http://" + self.localhost + ":" + str(self.port) + "/", payload, self._tern_timeout)
            result = req.read()
            if not PY2:
                result = result.decode('utf-8')
            return json.loads(result)
        except HTTPError as error:
            message = error.read()
            if not PY2:
                message = message.decode('utf-8')
            # self.debug(message)
            if not silent:
                logger.error(message)
            return None

    def run_command(self, query, pos, fragments=True, silent=False):
        if self.port is None:
            self.start_server()

        if isinstance(query, str):
            query = {"type": query}

        current_seq = self.vim.eval("undotree()['seq_cur']")

        doc = {"query": query, "files": []}
        if current_seq == self._tern_buffer_sent_at['undo_tree'] and self._tern_buffer_sent_at['ch'] == pos['ch']:
            fname, sending_file = self.relative_file(), False
        elif len(self.vim.current.buffer) > 250 and fragments:
            f = self.buffer_fragment()
            doc["files"].append(f)
            pos = {"line": pos["line"] - f["offsetLines"], "ch": pos["ch"]}
            fname, sending_file = "#0", False
        else:
            doc["files"].append(self.full_buffer())
            fname, sending_file = "#0", True

        query["file"] = fname
        query["end"] = pos
        query["lineCharPositions"] = True
        data = None
        try:
            data = self.make_request(doc, silent)
            if data is None:
                return None
        except:
            pass

        if data is None:
            try:
                self.start_server()
                if self.port is None:
                    return

                data = self.make_request(doc, silent)

                if data is None:
                    return None
            except Exception as e:
                if not silent:
                    raise e

        if sending_file:
            self._tern_buffer_sent_at['undo_tree'] = current_seq
            self._tern_buffer_sent_at['ch'] = pos['ch']

        return data

    def full_buffer(self):
        text = self.buffer_slice(self.vim.current.buffer, 0,
                                 len(self.vim.current.buffer))
        return {"type": "full",
                "name": self.relative_file(),
                "text": text}

    def buffer_slice(self, buf, pos, end):
        text = ""
        while pos < end:
            text += buf[pos] + "\n"
            pos += 1
        return text

    def relative_file(self):
        filename = self.vim.eval("expand('%:p')")
        if PY2:
            filename = filename.decode(self.vim.eval('&encoding'))

        return filename[len(self._project_directory) + 1:]

    def buffer_fragment(self):
        line = self.vim.eval("line('.')") - 1
        buffer = self.vim.current.buffer
        min_indent = None
        start = None

        for i in range(max(0, line - 50), line):
            if not re.match(".*\\bfunction\\b", buffer[i]):
                continue
            indent = len(re.match("^\\s*", buffer[i]).group(0))
            if min_indent is None or indent <= min_indent:
                min_indent = indent
                start = i

        if start is None:
            start = max(0, line - 50)

        end = min(len(buffer) - 1, line + 20)

        return {"type": "part",
                "name": self.relative_file(),
                "text": self.buffer_slice(buffer, start, end),
                "offsetLines": start}

    def completion_icon(self, type):
        _type = '(obj)'
        if type is None or type == "?":
            _type = "(?)"
        elif type.startswith("fn("):
            _type = "(fn)"
        elif type.startswith("["):
            _type = "([])"
        elif type == "number":
            _type = "(num)"
        elif type == "string":
            _type = "(str)"
        elif type == "bool":
            _type = "(bool)"

        return _type

    def completation(self, pos):
        current_row = pos['line']
        current_col = pos['ch']
        current_line = self.vim.current.line

        cached = current_row == int(self.cached["row"])
        cached = cached and current_col >= int(self.cached["end"])
        cached = cached and current_line[0:int(self.cached["end"])] == self.cached["word"]
        cached = cached and not re.match(".*\\W", current_line[int(self.cached["end"]):current_col])

        if cached and self.cached['data']:
            return self.cached['data']

        command = {
            "type": "completions",
            "types": True,
            "docs": True
        }

        data = self.run_command(command, pos)
        completions = []

        if data is not None:

            for rec in data["completions"]:
                completions.append({"word": rec["name"],
                                    "menu": self.completion_icon(rec.get("type")),
                                    "info": self.type_doc(rec)})

            start, end = (data["start"]["ch"], data["end"]["ch"])
            self.cached = {
                "row": current_row,
                "start": start,
                "end": end,
                "word": current_line[0:end],
                "data": completions
            }

        return completions

    def type_doc(self, rec):
        tp = rec.get("type")
        result = rec.get("doc", " ")
        if tp and tp != "?":
            result = tp + "\n" + result
        return result

    def get_complete_position(self, context):
        m = re.search(r'\w*$', context['input'])
        return m.start() if m else -1

    def gather_candidates(self, context):
        # if file was not found skip it
        if (self._not_tern_project_file_found):
            return []
        line = context['position'][1]
        col = context['complete_position']
        pos = {"line": line - 1, "ch": col + 1}
        # self.debug(pos)
        result = self.completation(pos)
        # self.debug('*' * 100)
        # self.debug(result)
        # self.debug('*' * 100)
        return result
