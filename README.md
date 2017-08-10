# deoplete-ternjs
[deoplete.nvim](https://github.com/Shougo/deoplete.nvim) source for javascript.

Based on tern_for_vim and deoplete-jedi

## Required

- Neovim and neovim/python-client
  - https://github.com/neovim/neovim
  - https://github.com/neovim/python-client

- deoplete.nvim
  - https://github.com/Shougo/deoplete.nvim

- ternjs
  - http://ternjs.net/  - This needs to be installed globally

## Important!

If no .tern-project file is found in the current buffer's directory that is
being edited or its ancestors, deoplete-ternjs will start the ternjs server
in the current working directory:

```vim
:pwd
```

allowing ternjs use the default setup.


## Install

Using [NeoBundle](https://github.com/Shougo/neobundle.vim)

```vim
NeoBundle 'carlitux/deoplete-ternjs', { 'build': { 'mac': 'npm install -g tern', 'unix': 'npm install -g tern' }}
```

or using [Plug](https://github.com/junegunn/vim-plug)

```vim
Plug 'carlitux/deoplete-ternjs', { 'do': 'npm install -g tern' }
```

## Ternjs Configuration

[Tern configuration docs](http://ternjs.net/doc/manual.html#configuration).


## Vim Configuration example
```vim
" Set bin if you have many instalations
let g:deoplete#sources#ternjs#tern_bin = '/path/to/tern_bin'
let g:deoplete#sources#ternjs#timeout = 1

"Add extra filetypes
let g:deoplete#sources#ternjs#filetypes = [
                \ 'jsx',
                \ 'javascript.jsx',
                \ 'vue',
                \ '...'
                \ ]
```

If you are using [tern_for_vim](https://github.com/ternjs/tern_for_vim), you also want to use the same tern command with deoplete-ternjs
```vim
" Use tern_for_vim.
let g:tern#command = ["tern"]
let g:tern#arguments = ["--persistent"]
```

Also if you are using add loadEagerly - * many files * - this to your .bashrc or .zshrc, this will
allow you load all files you need when ternjs is started.

```bash
ulimit -n 2048
```
