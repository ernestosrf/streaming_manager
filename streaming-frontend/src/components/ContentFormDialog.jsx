import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Checkbox } from '@/components/ui/checkbox.jsx'
import { useAuth } from '@/context/AuthContext.jsx'
import { CONTENT_TYPE_LABELS, getContentTypeLabel } from '@/lib/constants.js'
import { cn } from '@/lib/utils.js'

const MIN_QUERY_LENGTH = 2
const SEARCH_DEBOUNCE_MS = 300
const LISTBOX_ID = 'title-suggestions'
const NO_RESULTS = { items: [], failed: false }

const emptyForm = {
  title: '',
  year: '',
  type: 'movie',
  genre: '',
  poster_url: '',
  streaming_ids: [],
}

const suggestionKey = (item) => `${item.title.trim().toLowerCase()}|${item.year ?? ''}`
const optionDomId = (key) => `${LISTBOX_ID}-${key}`

// Busca com debounce. Cada resposta fica marcada com a URL que a gerou e só a da URL atual
// é devolvida: enquanto a busca nova não termina, ou se ela falha, a lista fica vazia em
// vez de mostrar resultados de outra consulta.
function useDebouncedResults(url) {
  const { makeAuthenticatedRequest } = useAuth()
  const [results, setResults] = useState({ url: null, ...NO_RESULTS })

  useEffect(() => {
    if (!url) {
      return undefined
    }

    const controller = new AbortController()
    const handle = setTimeout(async () => {
      try {
        const response = await makeAuthenticatedRequest(url, { signal: controller.signal })
        const items = response.ok ? await response.json() : []
        setResults({ url, items, failed: !response.ok })
      } catch (err) {
        if (err.name === 'AbortError') {
          return
        }
        console.error('Erro ao buscar sugestões:', err)
        setResults({ url, items: [], failed: true })
      }
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      clearTimeout(handle)
      controller.abort()
    }
  }, [url, makeAuthenticatedRequest])

  return url && results.url === url ? results : NO_RESULTS
}

// O foco fica sempre no campo de título (aria-activedescendant aponta a opção destacada),
// por isso a opção não é um botão focável.
function SuggestionOption({ option, active }) {
  const { item } = option
  const thumbnail = item.thumbnail_url || item.poster_url
  return (
    <div
      id={optionDomId(option.key)}
      role="option"
      aria-selected={active}
      className={cn(
        'flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-accent',
        active && 'bg-accent',
      )}
      onClick={() => option.apply(item)}
    >
      {thumbnail ? (
        <img src={thumbnail} alt="" loading="lazy" className="h-12 w-8 shrink-0 rounded object-cover" />
      ) : (
        <div className="h-12 w-8 shrink-0 rounded bg-muted" />
      )}
      <span className="min-w-0">
        <span className="block truncate font-medium">{item.title}</span>
        <span className="block truncate text-muted-foreground">
          {item.year ? `${item.year} · ` : ''}
          {getContentTypeLabel(item.type)}
          {item.genre ? ` · ${item.genre}` : ''}
        </span>
      </span>
    </div>
  )
}

function ContentFormDialog({
  open,
  onOpenChange,
  streamings,
  editingContent,
  onSaved,
}) {
  const { makeAuthenticatedRequest, meta } = useAuth()
  const [formData, setFormData] = useState(emptyForm)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [activeKey, setActiveKey] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  // Indica se os streamings marcados vieram de uma sugestão das watchlists (e não da pessoa).
  const streamingsFromSuggestion = useRef(false)

  useEffect(() => {
    if (!open) {
      return
    }
    setError('')
    setShowSuggestions(false)
    setActiveKey(null)
    streamingsFromSuggestion.current = false
    if (editingContent) {
      setFormData({
        title: editingContent.title || '',
        year: editingContent.year || '',
        type: editingContent.type || 'movie',
        genre: editingContent.genre || '',
        poster_url: editingContent.poster_url || '',
        streaming_ids: editingContent.streamings?.map((item) => item.id) || [],
      })
    } else {
      setFormData(emptyForm)
    }
  }, [open, editingContent])

  useEffect(() => {
    if (activeKey) {
      document.getElementById(optionDomId(activeKey))?.scrollIntoView({ block: 'nearest' })
    }
  }, [activeKey])

  const closeSuggestions = () => {
    setShowSuggestions(false)
    setActiveKey(null)
  }

  const applySuggestion = (item) => {
    setFormData({
      title: item.title || '',
      year: item.year || '',
      type: item.type || 'movie',
      genre: item.genre || '',
      poster_url: item.poster_url || '',
      streaming_ids: item.streamings?.map((streaming) => streaming.id) || [],
    })
    streamingsFromSuggestion.current = true
    closeSuggestions()
  }

  // O TMDB não informa streamings. Os que vieram de outra sugestão pertencem a outro título
  // e são descartados; os marcados pela pessoa ficam.
  const applyLookupResult = (item) => {
    const keepStreamings = !streamingsFromSuggestion.current
    streamingsFromSuggestion.current = false
    setFormData((current) => ({
      ...current,
      title: item.title || '',
      year: item.year || '',
      type: item.type || current.type,
      genre: item.genre || '',
      poster_url: item.poster_url || '',
      streaming_ids: keepStreamings ? current.streaming_ids : [],
    }))
    closeSuggestions()
  }

  const query = formData.title.trim()
  const searching = open && !editingContent && showSuggestions && query.length >= MIN_QUERY_LENGTH
  let suggestionsUrl = null
  let lookupUrl = null
  if (searching) {
    const params = new URLSearchParams({ q: query })
    // O TMDB sugere o tipo e o ano; filtrar por eles só faz sentido nas watchlists.
    if (meta.tmdb_enabled) {
      lookupUrl = `/api/content/lookup?${params.toString()}`
    }
    if (formData.type) {
      params.set('type', formData.type)
    }
    if (formData.year) {
      params.set('year', String(formData.year))
    }
    suggestionsUrl = `/api/content/suggestions?${params.toString()}`
  }

  const local = useDebouncedResults(suggestionsUrl)
  const lookup = useDebouncedResults(lookupUrl)
  const localKeys = new Set(local.items.map(suggestionKey))
  const localOptions = local.items.map((item) => ({ key: `local-${item.id}`, item, apply: applySuggestion }))
  const tmdbOptions = lookup.items
    .filter((item) => !localKeys.has(suggestionKey(item)))
    .map((item) => ({ key: `tmdb-${item.id}`, item, apply: applyLookupResult }))
  const options = [...localOptions, ...tmdbOptions]
  const activeIndex = options.findIndex((option) => option.key === activeKey)
  const listVisible = searching && (options.length > 0 || lookup.failed)

  const handleTitleKeyDown = (event) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if (!listVisible) {
        if (event.key === 'ArrowDown' && query.length >= MIN_QUERY_LENGTH) {
          event.preventDefault()
          setShowSuggestions(true)
        }
        return
      }
      if (options.length === 0) {
        return
      }
      event.preventDefault()
      const step = event.key === 'ArrowDown' ? 1 : -1
      const next = activeIndex === -1
        ? (step === 1 ? 0 : options.length - 1)
        : (activeIndex + step + options.length) % options.length
      setActiveKey(options[next].key)
    } else if (event.key === 'Enter' && searching) {
      // Com a busca ativa, Enter escolhe a sugestão destacada (ou só fecha a lista)
      // em vez de enviar o formulário só com o texto digitado.
      event.preventDefault()
      if (activeIndex >= 0) {
        options[activeIndex].apply(options[activeIndex].item)
      } else {
        closeSuggestions()
      }
    }
  }

  const handleTitleAreaBlur = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      closeSuggestions()
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const url = editingContent ? `/api/content/${editingContent.id}` : '/api/content'
      const method = editingContent ? 'PUT' : 'POST'
      const response = await makeAuthenticatedRequest(url, {
        method,
        body: JSON.stringify({
          ...formData,
          year: formData.year === '' ? null : Number(formData.year),
        }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        setError(data.error || 'Não foi possível salvar o conteúdo.')
        return
      }
      onOpenChange(false)
      onSaved()
    } catch (err) {
      setError(err.message || 'Erro ao salvar conteúdo.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl"
        onEscapeKeyDown={(e) => {
          // Com sugestões abertas, Esc fecha só a lista, não o diálogo.
          if (listVisible) {
            e.preventDefault()
            closeSuggestions()
          }
        }}
      >
        <DialogHeader>
          <DialogTitle>{editingContent ? 'Editar Conteúdo' : 'Adicionar Novo Conteúdo'}</DialogTitle>
          <DialogDescription>
            {editingContent
              ? 'Atualize as informações do conteúdo'
              : 'Digite o título e escolha uma sugestão para preencher ano, tipo, gênero e pôster. Depois, confira o tipo e marque os streamings.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="grid grid-cols-2 gap-4">
            <div className="relative" onBlur={handleTitleAreaBlur}>
              <Label htmlFor="title">Título *</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => {
                  setFormData({ ...formData, title: e.target.value })
                  setShowSuggestions(true)
                  setActiveKey(null)
                }}
                onKeyDown={handleTitleKeyDown}
                role="combobox"
                aria-autocomplete="list"
                aria-expanded={listVisible}
                aria-controls={LISTBOX_ID}
                aria-activedescendant={activeIndex >= 0 ? optionDomId(activeKey) : undefined}
                autoComplete="off"
                required
              />
              {listVisible && (
                // Ocupa a largura das duas colunas. O mouseDown não tira o foco do campo.
                <div
                  id={LISTBOX_ID}
                  role="listbox"
                  aria-label="Sugestões de títulos"
                  className="absolute left-0 z-20 mt-1 max-h-80 w-[calc(200%+1rem)] overflow-y-auto rounded-md border bg-popover shadow-md"
                  onMouseDown={(e) => e.preventDefault()}
                >
                  {localOptions.length > 0 && (
                    <div role="group" aria-labelledby={`${LISTBOX_ID}-local`}>
                      <p id={`${LISTBOX_ID}-local`} className="px-3 pt-2 text-xs font-medium text-muted-foreground">
                        Nas watchlists
                      </p>
                      {localOptions.map((option) => (
                        <SuggestionOption key={option.key} option={option} active={option.key === activeKey} />
                      ))}
                    </div>
                  )}
                  {(tmdbOptions.length > 0 || lookup.failed) && (
                    <div role="group" aria-labelledby={`${LISTBOX_ID}-tmdb`}>
                      <p id={`${LISTBOX_ID}-tmdb`} className="px-3 pt-2 text-xs font-medium text-muted-foreground">
                        Do TMDB
                      </p>
                      {lookup.failed ? (
                        <p className="px-3 py-2 text-sm text-muted-foreground">
                          Sugestões do TMDB indisponíveis no momento.
                        </p>
                      ) : (
                        tmdbOptions.map((option) => (
                          <SuggestionOption key={option.key} option={option} active={option.key === activeKey} />
                        ))
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div>
              <Label htmlFor="year">Ano</Label>
              <Input
                id="year"
                type="number"
                value={formData.year}
                onChange={(e) => setFormData({ ...formData, year: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="type">Tipo *</Label>
              <Select value={formData.type} onValueChange={(value) => setFormData({ ...formData, type: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CONTENT_TYPE_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="genre">Gênero</Label>
              <Input
                id="genre"
                value={formData.genre}
                onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="poster_url">URL do Poster</Label>
            <div className="flex items-center gap-3">
              <Input
                id="poster_url"
                value={formData.poster_url}
                onChange={(e) => setFormData({ ...formData, poster_url: e.target.value })}
              />
              {formData.poster_url && (
                <img
                  src={formData.poster_url}
                  alt="Pré-visualização do pôster"
                  className="h-16 w-11 shrink-0 rounded object-cover"
                />
              )}
            </div>
          </div>

          <div>
            <Label>Streamings Disponíveis</Label>
            <div className="grid grid-cols-2 gap-2 mt-2">
              {streamings.map((streaming) => (
                <div key={streaming.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={`streaming-${streaming.id}`}
                    checked={formData.streaming_ids.includes(streaming.id)}
                    onCheckedChange={(checked) => {
                      streamingsFromSuggestion.current = false
                      if (checked) {
                        setFormData({
                          ...formData,
                          streaming_ids: [...formData.streaming_ids, streaming.id],
                        })
                      } else {
                        setFormData({
                          ...formData,
                          streaming_ids: formData.streaming_ids.filter((id) => id !== streaming.id),
                        })
                      }
                    }}
                  />
                  <Label htmlFor={`streaming-${streaming.id}`} className="text-sm">
                    {streaming.name}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end space-x-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={saving}>
              {editingContent ? 'Salvar Alterações' : 'Adicionar'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default ContentFormDialog
