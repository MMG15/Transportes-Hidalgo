--[[
Filtro de pandoc para los documentos Word de Transportes Hidalgo.
Lo usa scripts/generar_word.py. Pandoc convierte el Markdown en un árbol de elementos
(títulos, párrafos, enlaces...) y este filtro lo modifica antes de escribir el .docx:

1. Enlaces a archivos del proyecto (ej. ../src/flota/...) -> texto simple: fuera de VS Code no abren nada.
   Se conservan los enlaces web (https://) y los internos del documento (#seccion).
2. Lo marcado con <!-- solo-md:inicio --> ... <!-- solo-md:fin --> no pasa al Word.
3. El primer título (#) pasa a ser el título del documento, con el logo arriba y un subtítulo;
   el resto de los títulos sube un nivel (## -> Título 1 de Word, ### -> Título 2).
]]

local function es_enlace_externo_o_interno(destino)
  return destino:match("^%a[%w+.-]*:") ~= nil or destino:sub(1, 1) == "#"
end

function Link(enlace)
  if not es_enlace_externo_o_interno(enlace.target) then
    return enlace.content
  end
end

local function marcador(bloque, nombre)
  return bloque.t == "RawBlock" and bloque.format == "html" and bloque.text:find(nombre, 1, true)
end

local function con_estilo(estilo, contenido)
  return pandoc.Div({ pandoc.Para(contenido) }, pandoc.Attr("", {}, { ["custom-style"] = estilo }))
end

function Pandoc(documento)
  local bloques, omitir, hay_titulo = {}, false, false

  for _, bloque in ipairs(documento.blocks) do
    if marcador(bloque, "solo-md:inicio") then
      omitir = true
    elseif marcador(bloque, "solo-md:fin") then
      omitir = false
    elseif not omitir then
      if bloque.t == "Header" and bloque.level == 1 and not hay_titulo then
        hay_titulo = true
        table.insert(bloques, con_estilo("Title", bloque.content))
        if documento.meta.subtitulo then
          local subtitulo = pandoc.utils.stringify(documento.meta.subtitulo)
          table.insert(bloques, con_estilo("Subtitle", { pandoc.Str(subtitulo) }))
        end
      else
        if bloque.t == "Header" and bloque.level > 1 then
          bloque.level = bloque.level - 1
        end
        table.insert(bloques, bloque)
      end
    end
  end

  if documento.meta.logo then
    local ruta = pandoc.utils.stringify(documento.meta.logo)
    local logo = pandoc.Image({}, ruta, "", pandoc.Attr("", {}, { height = "1.5cm" }))
    table.insert(bloques, 1, pandoc.Para({ logo }))
  end

  documento.blocks = bloques
  return documento
end
