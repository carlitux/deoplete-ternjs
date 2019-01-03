if exists('g:loaded_deoplete_ternjs')
  finish
endif

let g:loaded_deoplete_ternjs = 1

call ternjs#Enable()

let g:deoplete#sources#ternjs#tern_bin = get(g:, 'deoplete#sources#ternjs#tern_bin', 'tern')

if !exists('g:tern#filetypes')
let g:tern#filetypes = [
            \ 'jsx',
            \ 'javascript.jsx',
            \ 'vue'
            \ ]
endif
