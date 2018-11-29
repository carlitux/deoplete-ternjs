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

## Important!

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

" Whether to include the types of the completions in the result data. Default: 0
let g:deoplete#sources#ternjs#types = 1

" Whether to include the distance (in scopes for variables, in prototypes for 
" properties) between the completions and the origin position in the result 
" data. Default: 0
let g:deoplete#sources#ternjs#depths = 1

" Whether to include documentation strings (if found) in the result data.
" Default: 0
let g:deoplete#sources#ternjs#docs = 1

" When on, only completions that match the current word at the given point will
" be returned. Turn this off to get all results, so that you can filter on the 
" client side. Default: 1
let g:deoplete#sources#ternjs#filter = 0

" Whether to use a case-insensitive compare between the current word and 
" potential completions. Default 0
let g:deoplete#sources#ternjs#case_insensitive = 1

" When completing a property and no completions are found, Tern will use some 
" heuristics to try and return some properties anyway. Set this to 0 to 
" turn that off. Default: 1
let g:deoplete#sources#ternjs#guess = 0

" Determines whether the result set will be sorted. Default: 1
let g:deoplete#sources#ternjs#sort = 0

" When disabled, only the text before the given position is considered part of 
" the word. When enabled (the default), the whole variable name that the cursor
" is on will be included. Default: 1
let g:deoplete#sources#ternjs#expand_word_forward = 0

" Whether to ignore the properties of Object.prototype unless they have been 
" spelled out by at least two characters. Default: 1
let g:deoplete#sources#ternjs#omit_object_prototype = 0

" Whether to include JavaScript keywords when completing something that is not 
" a property. Default: 0
let g:deoplete#sources#ternjs#include_keywords = 1

" If completions should be returned when inside a literal. Default: 1
let g:deoplete#sources#ternjs#in_literal = 0


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
