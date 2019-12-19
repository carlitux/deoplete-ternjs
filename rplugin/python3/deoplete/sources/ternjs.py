# pylint: disable=E0401,C0111,R0903

import os
import re
import json
import platform
import subprocess
import threading

from urllib import request
from urllib.error import HTTPError
from urllib.error import URLError

from deoplete.source.base import Base


is_window = platform.system() == 'Windows'
import_re = r'require\(\s*["\'][@\w\./-]*$|from\s+["\'][@\w\./\-]*$'
import_pattern = re.compile(import_re)
opener = request.build_opener(request.ProxyHandler({}))


class Source(Base):

    def __init__(self, vim):
        super(Source, self).__init__(vim)

        self.name = 'tern'
        self.mark = '[TernJS]'
        self.input_pattern = (r'\w+|[\.\{@\'"]\s*[-/]?\w*')
        self.rank = 900
        self.is_volatile = True
        self.filetypes = ['javascript']
        if 'deoplete#sources#ternjs#filetypes' in vim.vars:
            self.filetypes.extend(vim.vars['deoplete#sources#ternjs#filetypes'])

    def on_init(self, context):
        vars = context['vars']

        self._localhost = (is_window and '127.0.0.1') or 'localhost'

        self._tern_command = self.get_from_vars(vars, 'deoplete#sources#ternjs#tern_bin', 'tern')
        self._tern_types = bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#types', 0))
        self._tern_depths = bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#depths', 0))
        self._tern_docs = bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#docs', 0))
        self._tern_filter = bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#filter', 1))
        self._tern_case_insensitive = \
            bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#case_insensitive', 0))
        self._tern_guess = bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#guess', 1))
        self._tern_sort = bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#sort', 1))
        self._tern_expand_word_forward = \
            bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#expand_word_forward', 1))
        self._tern_omit_object_prototype = \
            bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#omit_object_prototype', 1))
        self._tern_include_keywords = \
            bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#include_keywords', 0))
        self._tern_in_literal = \
            bool(self.get_from_vars(vars, 'deoplete#sources#ternjs#in_literal', 1))

        # Call to vim/nvim on init to do async the source
        self._vim_current_path = self.vim.eval("expand('%:p:h')")
        self._vim_current_cwd = self.vim.eval('getcwd()')

        # Start ternjs in thread
        self._is_server_started = False
        self._port = None
        self._proc = None
        self._buffer_length = 0
        self._current_buffer = []

        # If something was wrong this source will do nothing: Eg. Tern crashed or not installed.
        self._do_nothing = False
        self.candidates = None

    def get_complete_position(self, context):
        if import_pattern.search(context['input']):
            return re.search(r'["\']', context['input']).start()
        m = re.search(r'["\']?\w*$', context['input'])
        return m.start() if m else -1

    def gather_candidates(self, context):
        if not self._do_nothing and context['is_refresh']:
            if not self._is_server_started:
                startThread = threading.Thread(target=self.initialize, name='Start Tern Server')
                startThread.start()
                startThread.join()
                self._is_server_started = True # also if any error no need another thread
            elif self._port:
                if self.candidates is not None:
                    candidates = self.candidates
                    self.candidates = None
                    return candidates
                else:
                    line = context['position'][1]
                    col = context['complete_position']
                    pos = {'line': line - 1, 'ch': col}

                    # Cache variables of neovim
                    self._current_buffer = self.vim.current.buffer[:]
                    self._buffer_length = len(self._current_buffer)
                    # NOTE: This could be pos.line????
                    self._current_line = self.vim.eval("line('.')") - 1
                    self._relative_file = self.vim.eval("expand('%:p')")
                    self._relative_file = self._relative_file[len(
                        self._project_directory) + 1:]

                    # Update autocomplete position need to send the position
                    # where cursor is because the position is the start of
                    # quote
                    m = import_pattern.search(context['input'])
                    if m:
                        # self.vim.err_write('update pos' + str(m) + '\n')
                        pos['ch'] = m.end()

                    startThread = threading.Thread(
                        target=self.completation, name='Request Completion', args=(pos,))
                    startThread.start()
                    startThread.join()

    def initialize(self):
        self._project_directory = self._search_tern_project_dir()
        # self.debug('Directory to use: {}'.format(self._project_directory))
        try:
            self.start_server()
            self._url = 'http://{}:{}/'.format(self._localhost, self._port)
            # self.debug('URL to connect: {}'.format(self._url))
        except FileNotFoundError:
            self._do_nothing = True

    def __del__(self):
        if self.is_initialized:
            self.stop_server()

    def start_server(self):
        if not self._tern_command:
            self.vim.err_write('No tern bin set.')
            return

        if not self._project_directory:
            self.vim.err_write('Project directory is not valid.')
            return

        env = None

        portFile = os.path.join(self._project_directory, '.tern-port')
        if os.path.isfile(portFile):
            self._port = int(open(portFile, 'r').read())
            # self.debug(
            #     'Using running tern server with port: {}'.format(self._port))
            return

        if platform.system() == 'Darwin':
            env = os.environ.copy()
            env['PATH'] += ':/usr/local/bin'

        try:
            self._proc = subprocess.Popen(
                    [self._tern_command, '--persistent', '--no-port-file'],
                    cwd=self._project_directory,
                    shell=is_window,
                    env=env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    )
        except Exception as e:
            self.vim.err_write('Failed to start server: {}\n'.format(e))
            self._do_nothing = False
            return None

        output = '' 

        while True:
            line = self._proc.stdout.readline().decode('utf-8')
            if not line:
                self.vim.err_write('Failed to start server' +
                           (output and ':\n' + output))
                return

            match = re.match('Listening on port (\\d+)', line)
            if match:
                self._port = int(match.group(1))
                # self.debug(
                #     'Tern server started on port: {}'.format(self._port))
                return
            else:
                output += line

    def stop_server(self):
        if self._proc is None:
            return

        self._proc.stdin.close()
        self._proc.wait()
        self._proc = None

    def _search_tern_project_dir(self):
        directory = self._vim_current_path

        # If not a directory, don't start the server
        if not os.path.isdir(directory):
            return None

        if directory:
            while True:
                parent = os.path.dirname(directory[:-1])

                if not parent:
                    return self._vim_current_cwd

                if os.path.isfile(os.path.join(directory, '.tern-project')):
                    return directory

                directory = parent

    def make_request(self, doc, silent):
        payload = json.dumps(doc).encode('utf-8')
        # self.debug('Payload: {}'.format(payload))
        try:
            req = opener.open(self._url, payload)
            result = req.read()
            # self.debug('make_request result: {}'.format(result))
            return json.loads(result.decode('utf8'))
        except HTTPError as error:
            message = error.read()
            self.error(message)
        except URLError as error:
            self._do_nothing = True
            self.vim.err_write(
                'Looks like tern was stopped or crashed. Delete .tern-port file and restart [n]vim\n')

    def run_command(self, query, pos, fragments=True, silent=False):
        if isinstance(query, str):
            query = {'type': query}

        doc = {'query': query, 'files': []}

        if self._buffer_length > 250 and fragments:
            f = self.buffer_fragment()
            doc['files'].append(f)
            pos = {'line': pos['line'] - f['offsetLines'], 'ch': pos['ch']}
            fname = '#0'
        else:
            doc['files'].append(self.full_buffer())
            fname = '#0'

        query['file'] = fname
        query['end'] = pos
        query['lineCharPositions'] = True
        query['omitObjectPrototype'] = False
        query['sort'] = False
        data = self.make_request(doc, silent)

        return data

    def full_buffer(self):
        text = self.buffer_slice(self._current_buffer, 0,
                                 len(self._current_buffer))
        return {'type': 'full',
                'name': self._relative_file,
                'text': text}

    def buffer_slice(self, buf, start, end):
        return '\n'.join(buf[start:end])
        # text = ''
        # while pos < len(buf):
        #     text += buf[pos] + '\n'
        #     pos += 1
        # return text

    def buffer_fragment(self):
        line = self._current_line
        buffer = self._current_buffer
        min_indent = None
        start = None

        for i in range(max(0, line - 50), line):
            if not re.match('.*\\bfunction\\b', buffer[i]):
                continue
            indent = len(re.match('^\\s*', buffer[i]).group(0))
            if min_indent is None or indent <= min_indent:
                min_indent = indent
                start = i

        if start is None:
            start = max(0, line - 50)

        end = min(len(buffer) - 1, line + 20)

        return {'type': 'part',
                'name': self._relative_file,
                'text': self.buffer_slice(buffer, start, end),
                'offsetLines': start}

    def completation(self, pos):
        command = {
            'type': 'completions',
            'types': self._tern_types,
            'depths': self._tern_types,
            'docs': self._tern_docs,
            'filter': self._tern_filter,
            'caseInsensitive': self._tern_case_insensitive,
            'guess': self._tern_guess,
            'sort': self._tern_sort,
            'expandWordForward': self._tern_expand_word_forward,
            'omitObjectPrototype': self._tern_omit_object_prototype,
            'includeKeywords': self._tern_include_keywords,
            'inLiteral': self._tern_in_literal,
        }

        data = self.run_command(command, pos)
        completions = []
        # self.debug('completation data: {}'.format(data))

        if data is not None:

            for rec in data['completions']:
                item = {
                    'dup': 0,
                }

                if isinstance(rec, str):
                    item['word'] = rec
                else:
                    item['kind'] = self.get_kind(rec)
                    item['word'] = rec['name']
                    item['abbr'] = rec['name']
                    # item['abbr'] = '{}{}'.format(rec['name'], self.get_signature(rec))

                    if self._tern_docs:
                        item['info'] = self.type_doc(rec)

                completions.append(item)

        self.candidates = completions
        self.vim.command('call deoplete#auto_complete()')

    def type_doc(self, rec):
        kind = self.get_kind(rec)
        result = rec.get('doc', ' ')

        if kind == 'function':
            kind = '{}{}'.format(rec['name'], self.get_signature(rec))

        if kind and kind != '?':
            result = '{}\n\n{}'.format(kind, result)

        return result

    def get_signature(self, rec):
        kind = rec.get('type', '')

        if kind.startswith('fn('):
            return kind[2:] 

        return ''

    def get_kind(self, rec):
        kind = rec.get('type')
        if kind is None or kind == '?': return '(?)'

        if kind.startswith('fn('):
            return 'function'

        if kind == rec.get('name'):
            return 'object'

        return kind

    def get_from_vars(self, vars, key, default):
        return vars[key] if key in vars else default

