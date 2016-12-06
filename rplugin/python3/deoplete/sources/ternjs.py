# pylint: disable=E0401,C0111,R0903

import os
import re
import json
import sys
import platform
import subprocess
import time

from deoplete.source.base import Base
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

logger = getLogger(__name__)
windows = platform.system() == "Windows"

import_re = r'=?\s*require\(["\'"][\w\./-]*$|\s+from\s+["\'][\w\./-]*$'
import_pattern = re.compile(import_re)


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
        self.input_pattern = (r'\.\w*$|^\s*@\w*$|' + import_re)
        self.rank = 700
        self.filetypes = self.vim.vars['deoplete#sources#ternjs#filetypes']

        self._project_directory = None
        self.port = None
        self.localhost = (windows and "127.0.0.1") or "localhost"
        self.proc = None
        self.last_failed = 0
        self._tern_command = \
            self.vim.vars['deoplete#sources#ternjs#tern_bin'] or 'tern'
        self._tern_arguments = '--persistent'
        self._tern_timeout = 1
        self._tern_show_signature = True
        self._tern_first_request = False
        self._tern_last_length = 0
        self._trying_to_start = False

        if vim.eval('exists("g:tern_request_timeout")'):
            self._tern_timeout = float(vim.eval("g:tern_request_timeout"))

        if vim.eval('exists("g:tern_show_signature_in_pum")'):
            self._tern_show_signature = \
                vim.eval('g:tern_show_signature_in_pum') != '0'

    def __del__(self):
        self.stop_server()

    def start_server(self):
        if self._trying_to_start:
            return

        if not self._tern_command:
            return None

        if time.time() - self.last_failed < 30:
            return None

        self._trying_to_start = True
        self._search_tern_project_dir()
        env = None

        portFile = os.path.join(self._project_directory, ".tern-port")
        if os.path.isfile(portFile):
            self.port = int(open(portFile, "r").read())
            return

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
                self._trying_to_start = False
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
        if not self._project_directory:
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
                        self._project_directory = self.vim.eval('getcwd()')
                        if PY2:
                            self._project_directory = self._project_directory.decode(self.vim.eval('&encoding'))

                        break

                    if os.path.isfile(os.path.join(directory, '.tern-project')):
                        self._project_directory = directory
                        break

                    directory = parent

    def make_request(self, doc, silent):
        payload = json.dumps(doc)
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
            if not silent:
                logger.error(message)
            return None

    def run_command(self, query, pos, fragments=True, silent=False):
        if self.port is None:
            self.start_server()

        if isinstance(query, str):
            query = {"type": query}

        doc = {"query": query, "files": []}

        file_length = len(self.vim.current.buffer)

        if not self._file_changed and self._tern_first_request:
            fname = self.relative_file()
        elif file_length > 250 and fragments:
            f = self.buffer_fragment()
            doc["files"].append(f)
            pos = {"line": pos["line"] - f["offsetLines"], "ch": pos["ch"]}
            fname = "#0"
        else:
            self._tern_first_request = True
            doc["files"].append(self.full_buffer())
            fname = "#0"

        query["file"] = fname
        query["end"] = pos
        query["lineCharPositions"] = True
        query["omitObjectPrototype"] = False
        query["sort"] = False
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
            except:
                pass
            # except Exception as e:
            #     if not silent:
            #         raise e

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
            if (self._tern_show_signature):
                _type = type
            else:
                _type = "(fn)"
        elif type.startswith("["):
            if self._tern_show_signature:
                _type = "(" + type + ")"
            else:
                _type = "([])"
        elif type == "number":
            _type = "(num)"
        elif type == "string":
            _type = "(str)"
        elif type == "bool":
            _type = "(bool)"

        return _type

    def completation(self, pos):
        command = {
            "type": "completions",
            "types": True,
            "docs": True
        }

        data = self.run_command(command, pos)
        completions = []

        if data is not None:

            for rec in data["completions"]:
                completions.append({
                    "word": rec["name"],
                    "menu": self.completion_icon(rec.get("type")),
                    "info": self.type_doc(rec)})

        return completions

    def type_doc(self, rec):
        tp = rec.get("type")
        result = rec.get("doc", " ")
        if tp and tp != "?":
            result = tp + "\n" + result
        return result

    def get_complete_position(self, context):
        m = import_pattern.search(context['input'])
        if m:
            # need to tell from what position autocomplete as
            # needs to autocomplete from start quote return that
            return re.search(r'["\']', context['input']).start()

        m = re.search(r'\w*$', context['input'])
        return m.start() if m else -1

    def gather_candidates(self, context):
        self._file_changed = 'TextChanged' in context['event'] or \
            self._tern_last_length != len(self.vim.current.buffer)
        line = context['position'][1]
        col = context['complete_position']
        pos = {"line": line - 1, "ch": col}

        # Update autocomplete position need to send the position
        # where cursor is because the position is the start of
        # quote
        m = import_pattern.search(context['input'])
        if m:
            pos['ch'] = m.end()

        result = self.completation(pos) or []
        return result
