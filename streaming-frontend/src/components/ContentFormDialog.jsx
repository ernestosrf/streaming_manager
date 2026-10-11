import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Checkbox } from '@/components/ui/checkbox.jsx'
import { useAuth } from '@/context/AuthContext.jsx'
import { CONTENT_TYPE_LABELS, getContentTypeLabel } from '@/lib/constants.js'

const MIN_QUERY_LENGTH = 2
const SEARCH_DEBOUNCE_MS = 300

const emptyForm = {
  title: '',
  year: '',
  type: 'movie',
  genre: '',
  poster_url: '',
  streaming_ids: [],
}

const suggestionKey = (item) => `${item.title.trim().toLowerCase()}|${item.year ?? ''}`

// Busca com debounce; cancela o timer e a requisição em andamento quando a URL muda,
// evitando resultados obsoletos. Sem URL, a lista é esvaziada.
function useDebouncedResults(url) {
  const { makeAuthenticatedRequest } = useAuth()
  const [results, setResults] = useState([])

  useEffect(() => {
    if (!url) {
      setResults([])
      return undefined
    }

    const controller = new AbortController()
    const handle = setTimeout(async () => {
      try {
        const response = await makeAuthenticatedRequest(url, { signal: controller.signal })
        setResults(response.ok ? await response.json() : [])
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Erro ao buscar sugestões:', err)
        }
      }
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      clearTimeout(handle)
      controller.abort()
    }
  }, [url, makeAuthenticatedRequest])

  return results
}

function SuggestionButton({ item, onSelect }) {
  const thumbnail = item.thumbnail_url || item.poster_url
  return (
    <button
      type="button"
      className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-accent focus:bg-accent focus:outline-none"
      onClick={() => onSelect(item)}
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
    </button>
  )
}

function ContentFormDialog({
  open,
  onOpenChange,
  streamings,
  editingContent,
  onSaved,
}) {
  const { makeAuthenticatedRequest } = useAuth()
  const [formData, setFormData] = useState(emptyForm)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) {
      return
    }
    setError('')
    setShowSuggestions(false)
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

  const query = formData.title.trim()
  const searching = open && !editingContent && showSuggestions && query.length >= MIN_QUERY_LENGTH
  let suggestionsUrl = null
  let lookupUrl = null
  if (searching) {
    const params = new URLSearchParams({ q: query })
    // O TMDB sugere o tipo e o ano; filtrar por eles só faz sentido nas watchlists.
    lookupUrl = `/api/content/lookup?${params.toString()}`
    if (formData.type) {
      params.set('type', formData.type)
    }
    if (formData.year) {
      params.set('year', String(formData.year))
    }
    suggestionsUrl = `/api/content/suggestions?${params.toString()}`
  }

  const suggestions = useDebouncedResults(suggestionsUrl)
  const lookupResults = useDebouncedResults(lookupUrl)
  const localKeys = new Set(suggestions.map(suggestionKey))
  const externalSuggestions = lookupResults.filter((item) => !localKeys.has(suggestionKey(item)))
  const hasSuggestions = searching && (suggestions.length > 0 || externalSuggestions.length > 0)

  const applySuggestion = (item) => {
    setFormData({
      title: item.title || '',
      year: item.year || '',
      type: item.type || 'movie',
      genre: item.genre || '',
      poster_url: item.poster_url || '',
      streaming_ids: item.streamings?.map((streaming) => streaming.id) || [],
    })
    setShowSuggestions(false)
  }

  // O TMDB não informa streamings: mantém os que já estiverem marcados.
  const applyLookupResult = (item) => {
    setFormData((current) => ({
      ...current,
      title: item.title || '',
      year: item.year || '',
      type: item.type || current.type,
      genre: item.genre || '',
      poster_url: item.poster_url || '',
    }))
    setShowSuggestions(false)
  }

  const handleTitleAreaBlur = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setShowSuggestions(false)
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
          if (hasSuggestions) {
            e.preventDefault()
            setShowSuggestions(false)
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
                }}
                autoComplete="off"
                required
              />
              {hasSuggestions && (
                // Ocupa a largura das duas colunas. O mouseDown não tira o foco do campo;
                // pelo teclado, Tab percorre as opções.
                <div
                  className="absolute left-0 z-20 mt-1 max-h-80 w-[calc(200%+1rem)] overflow-y-auto rounded-md border bg-popover shadow-md"
                  onMouseDown={(e) => e.preventDefault()}
                >
                  {suggestions.length > 0 && (
                    <div>
                      <p className="px-3 pt-2 text-xs font-medium text-muted-foreground">Nas watchlists</p>
                      {suggestions.map((item) => (
                        <SuggestionButton key={item.id} item={item} onSelect={applySuggestion} />
                      ))}
                    </div>
                  )}
                  {externalSuggestions.length > 0 && (
                    <div>
                      <p className="px-3 pt-2 text-xs font-medium text-muted-foreground">Do TMDB</p>
                      {externalSuggestions.map((item) => (
                        <SuggestionButton key={item.id} item={item} onSelect={applyLookupResult} />
                      ))}
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
