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
    let l:tern_port_path = join([fnamemodify('~', ':p'), ".tern-port"], "")
    if !empty(glob(l:tern_port_path))
        echo delete(fnameescape(l:tern_port_path)) == 0 ? "Success" : "Fail"
    endif
endfunction
