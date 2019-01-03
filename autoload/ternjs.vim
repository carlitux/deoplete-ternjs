if get(s:, 'loaded', 0)
    finish
endif
let s:loaded = 1

let s:plug = expand("<sfile>:p:h:h")
let s:script = s:plug . '/scripts/ternjs.py'
if has('python3')
    execute 'py3file ' . fnameescape(s:script)
elseif has('python')
    execute 'pyfile ' . fnameescape(s:script)
endif

function! ternjs#Enable()
    if has('python3')
        py3 tern_startServer()
    elseif has('python')
        py tern_startServer()
    endif
endfunction

augroup ternjs
    autocmd!
    autocmd VimLeavePre * call ternjs#killServer()
augroup END

function! ternjs#killServer()
    if has('python3')
        py3 tern_killServers()
    elseif has('python')
        py tern_killServers()
    endif
endfunction
