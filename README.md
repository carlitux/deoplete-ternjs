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


## Install

```vim
NeoBundle 'carlitux/deoplete-ternjs'
# or
Plug 'carlitux/deoplete-ternjs'
```

## Configuration example
```vim
" Use deoplete.
let g:tern_request_timeout = 1
```

Also if you are using add loadEagerly this to your .bashrc or .zshrc, this will
allow you load all files you need when ternjs is started.

```bash
ulimit -n 2048
```
