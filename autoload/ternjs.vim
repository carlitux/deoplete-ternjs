if get(s:, 'loaded', 0)
    finish
endif
let s:loaded = 1

function! ternjs#Enable()
endfunction

augroup ternjs
  autocmd!
  autocmd VimLeavePre * call ternjs#deleteTernPort()
augroup END

function! ternjs#deleteTernPort()
    if !empty(glob(join([getcwd(), ".tern-port"], "/")))
        echo delete(fnameescape(join([getcwd(), ".tern-port"], "/"))) == 0 ? "Success" : "Fail"
    endif
endfunction
