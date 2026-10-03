import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Checkbox } from '@/components/ui/checkbox.jsx'
import { useAuth } from '@/context/AuthContext.jsx'

const emptyForm = {
  title: '',
  year: '',
  type: 'movie',
  genre: '',
  poster_url: '',
  streaming_ids: [],
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
  const [suggestions, setSuggestions] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) {
      return
    }
    setError('')
    setSuggestions([])
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
    if (!open || editingContent || formData.title.trim().length < 2) {
      setSuggestions([])
      return undefined
    }

    const handle = setTimeout(async () => {
      try {
        const params = new URLSearchParams({ q: formData.title.trim() })
        if (formData.type) {
          params.set('type', formData.type)
        }
        if (formData.year) {
          params.set('year', String(formData.year))
        }
        const response = await makeAuthenticatedRequest(`/api/content/suggestions?${params.toString()}`)
        if (response.ok) {
          setSuggestions(await response.json())
        }
      } catch (err) {
        console.error('Erro ao buscar sugestões:', err)
      }
    }, 300)

    return () => clearTimeout(handle)
  }, [formData.title, formData.type, formData.year, open, editingContent, makeAuthenticatedRequest])

  const applySuggestion = (item) => {
    setFormData({
      title: item.title || '',
      year: item.year || '',
      type: item.type || 'movie',
      genre: item.genre || '',
      poster_url: item.poster_url || '',
      streaming_ids: item.streamings?.map((streaming) => streaming.id) || [],
    })
    setSuggestions([])
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
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{editingContent ? 'Editar Conteúdo' : 'Adicionar Novo Conteúdo'}</DialogTitle>
          <DialogDescription>
            {editingContent
              ? 'Atualize as informações do conteúdo'
              : 'Preencha as informações do filme, série ou anime. Sugestões de outros catálogos aparecem ao digitar o título.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="grid grid-cols-2 gap-4">
            <div className="relative">
              <Label htmlFor="title">Título *</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                autoComplete="off"
                required
              />
              {!editingContent && suggestions.length > 0 && (
                <div className="absolute z-20 mt-1 w-full rounded-md border bg-popover shadow-md">
                  {suggestions.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className="block w-full px-3 py-2 text-left text-sm hover:bg-accent"
                      onClick={() => applySuggestion(item)}
                    >
                      <span className="font-medium">{item.title}</span>
                      <span className="ml-2 text-muted-foreground">
                        {item.year ? `${item.year} · ` : ''}
                        {item.type === 'movie' ? 'Filme' : item.type === 'series' ? 'Série' : 'Anime'}
                      </span>
                    </button>
                  ))}
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
                  <SelectItem value="movie">Filme</SelectItem>
                  <SelectItem value="series">Série</SelectItem>
                  <SelectItem value="anime">Anime</SelectItem>
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
            <Input
              id="poster_url"
              value={formData.poster_url}
              onChange={(e) => setFormData({ ...formData, poster_url: e.target.value })}
            />
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
