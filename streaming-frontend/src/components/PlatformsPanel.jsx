import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table.jsx'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog.jsx'
import { useAuth } from '@/context/AuthContext.jsx'

const EMPTY_FORM = { name: '', color: '#64748b' }

function PlatformsPanel() {
  const { makeAuthenticatedRequest } = useAuth()
  const [platforms, setPlatforms] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [form, setForm] = useState(null)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const loadPlatforms = useCallback(async () => {
    const response = await makeAuthenticatedRequest('/api/streamings?active_only=false')
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.error || 'Não foi possível carregar as plataformas.')
    }
    setPlatforms(await response.json())
  }, [makeAuthenticatedRequest])

  const reloadPlatforms = async () => {
    try {
      await loadPlatforms()
    } catch (err) {
      setError(err.message || 'Não foi possível carregar as plataformas.')
    }
  }

  const openForm = (values) => {
    setFormError('')
    setForm(values)
  }

  useEffect(() => {
    loadPlatforms().catch((err) => setError(err.message || 'Não foi possível carregar as plataformas.'))
  }, [loadPlatforms])

  const savePlatform = async (event) => {
    event.preventDefault()
    if (!form) return
    const name = form.name.trim()
    if (!name) {
      setFormError('Nome é obrigatório.')
      return
    }

    setSaving(true)
    setFormError('')
    setError('')
    setMessage('')
    try {
      const response = await makeAuthenticatedRequest(
        form.id ? `/api/streamings/${form.id}` : '/api/streamings',
        {
          method: form.id ? 'PUT' : 'POST',
          body: JSON.stringify({ name, color: form.color, active: form.active }),
        },
      )
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        setFormError(data.error || 'Não foi possível salvar a plataforma.')
        return
      }
      setMessage(form.id ? 'Plataforma atualizada.' : 'Plataforma criada.')
      setForm(null)
    } catch (err) {
      setFormError(err.message || 'Erro de conexão. Tente novamente.')
      return
    } finally {
      setSaving(false)
    }
    await reloadPlatforms()
  }

  const toggleActive = async (item) => {
    setError('')
    setMessage('')
    try {
      const response = await makeAuthenticatedRequest(`/api/streamings/${item.id}`, {
        method: 'PUT',
        body: JSON.stringify({ active: !item.active }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        setError(data.error || 'Não foi possível alterar a plataforma.')
        return
      }
      setMessage(item.active ? 'Plataforma desativada.' : 'Plataforma ativada.')
    } catch (err) {
      setError(err.message || 'Erro de conexão. Tente novamente.')
      return
    }
    await reloadPlatforms()
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <CardTitle>Plataformas</CardTitle>
          <CardDescription>
            A lista é global. Desativar uma plataforma esconde ela das watchlists, sem apagar os títulos.
          </CardDescription>
        </div>
        <Button onClick={() => openForm({ ...EMPTY_FORM, active: true })}>
          Nova plataforma
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        {message && <p className="text-sm text-green-600">{message}</p>}

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nome</TableHead>
              <TableHead>Cor</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {platforms.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground">
                  Nenhuma plataforma cadastrada.
                </TableCell>
              </TableRow>
            )}
            {platforms.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.name}</TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-2">
                    <span
                      className="inline-block h-4 w-4 rounded-full border"
                      style={{ backgroundColor: item.color || '#64748b' }}
                    />
                    {item.color || '—'}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge variant={item.active ? 'default' : 'secondary'}>
                    {item.active ? 'Ativa' : 'Inativa'}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => openForm({
                        id: item.id,
                        name: item.name,
                        color: item.color || '#64748b',
                        active: item.active,
                      })}
                    >
                      Editar
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => toggleActive(item)}>
                      {item.active ? 'Desativar' : 'Ativar'}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>

      <Dialog open={Boolean(form)} onOpenChange={(open) => { if (!open) setForm(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{form?.id ? 'Editar plataforma' : 'Nova plataforma'}</DialogTitle>
            <DialogDescription>
              O nome aparece nos filtros e nos títulos de todas as watchlists.
            </DialogDescription>
          </DialogHeader>
          {form && (
            <form onSubmit={savePlatform} className="space-y-4">
              {formError && <p className="text-sm text-destructive">{formError}</p>}
              <div className="space-y-2">
                <Label htmlFor="platform-name">Nome</Label>
                <Input
                  id="platform-name"
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  maxLength={100}
                  required
                  disabled={saving}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="platform-color">Cor</Label>
                <Input
                  id="platform-color"
                  type="color"
                  value={form.color}
                  onChange={(event) => setForm((current) => ({ ...current, color: event.target.value }))}
                  disabled={saving}
                  className="h-10 w-20 p-1"
                />
              </div>
              <Button type="submit" disabled={saving}>
                {saving ? 'Salvando...' : 'Salvar'}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  )
}

export default PlatformsPanel
