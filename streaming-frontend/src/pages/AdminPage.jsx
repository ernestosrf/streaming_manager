import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table.jsx'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog.jsx'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog.jsx'
import { useAuth } from '@/context/AuthContext.jsx'

const STATUS_LABELS = {
  pending: 'Pendente',
  active: 'Ativo',
  inactive: 'Inativo',
  rejected: 'Rejeitado',
}

function AdminPage() {
  const { isAuthenticated, isAdmin, loading, login, makeAuthenticatedRequest, user, meta } = useAuth()
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [resetUser, setResetUser] = useState(null)
  const [newPassword, setNewPassword] = useState('')

  const loadUsers = useCallback(async (signal) => {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (status !== 'all') params.set('status', status)
    const response = await makeAuthenticatedRequest(`/api/admin/users?${params.toString()}`, { signal })
    if (response.ok) {
      setUsers(await response.json())
    }
  }, [makeAuthenticatedRequest, search, status])

  useEffect(() => {
    if (!isAdmin) {
      return undefined
    }
    // Debounce da busca e cancelamento da requisição anterior para evitar respostas fora de ordem.
    const controller = new AbortController()
    const handle = setTimeout(() => {
      loadUsers(controller.signal).catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message)
        }
      })
    }, 300)
    return () => {
      clearTimeout(handle)
      controller.abort()
    }
  }, [isAdmin, loadUsers])

  if (loading) {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (!isAdmin) {
    return <Navigate to="/" replace />
  }

  const runAction = async (url, options = {}) => {
    setError('')
    setMessage('')
    try {
      const response = await makeAuthenticatedRequest(url, options)
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        setError(data.error || 'Não foi possível concluir a ação.')
        return false
      }
      if (data.access_token) {
        // Redefinir a própria senha invalida o token atual.
        login(data.access_token, user)
      }
      setMessage(data.message || 'Ação concluída.')
      await loadUsers()
      return true
    } catch (err) {
      setError(err.message || 'Erro de conexão. Tente novamente.')
      return false
    }
  }

  const handleReset = async (event) => {
    event.preventDefault()
    if (!resetUser) return
    const ok = await runAction(`/api/admin/users/${resetUser.id}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ new_password: newPassword }),
    })
    if (ok) {
      setResetUser(null)
      setNewPassword('')
    }
  }

  const watchlistPath = (item) => (
    item.role === 'admin' || item.username === meta?.admin_username ? '/' : `/${item.username}`
  )

  return (
    <div className="container mx-auto px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle>Painel administrativo</CardTitle>
          <CardDescription>
            Gerencie cadastros, status das contas e senhas. Plataformas de streaming continuam globais.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && <p className="text-sm text-destructive">{error}</p>}
          {message && <p className="text-sm text-green-600">{message}</p>}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="search">Buscar por username</Label>
              <Input
                id="search"
                value={search}
                onChange={(e) => setSearch(e.target.value.toLowerCase())}
                placeholder="ex: maria"
              />
            </div>
            <div>
              <Label>Status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="pending">Pendente</SelectItem>
                  <SelectItem value="active">Ativo</SelectItem>
                  <SelectItem value="inactive">Inativo</SelectItem>
                  <SelectItem value="rejected">Rejeitado</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Username</TableHead>
                <TableHead>Papel</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Watchlist</TableHead>
                <TableHead>Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>@{item.username}</TableCell>
                  <TableCell>{item.role}</TableCell>
                  <TableCell>
                    <Badge variant={item.status === 'active' ? 'default' : 'secondary'}>
                      {STATUS_LABELS[item.status] || item.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {item.status === 'active' ? (
                      <Button variant="link" className="px-0" asChild>
                        <Link to={watchlistPath(item)}>Ver watchlist</Link>
                      </Button>
                    ) : (
                      <span className="text-muted-foreground text-sm">Indisponível</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      {item.status === 'pending' && (
                        <>
                          <Button size="sm" onClick={() => runAction(`/api/admin/users/${item.id}/approve`, { method: 'POST' })}>
                            Aprovar
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => runAction(`/api/admin/users/${item.id}/reject`, { method: 'POST' })}>
                            Rejeitar
                          </Button>
                        </>
                      )}
                      {item.status === 'rejected' && (
                        <Button size="sm" onClick={() => runAction(`/api/admin/users/${item.id}/approve`, { method: 'POST' })}>
                          Aprovar
                        </Button>
                      )}
                      {item.status === 'active' && item.id !== user.id && (
                        <Button size="sm" variant="secondary" onClick={() => runAction(`/api/admin/users/${item.id}/deactivate`, { method: 'POST' })}>
                          Desativar
                        </Button>
                      )}
                      {item.status === 'inactive' && (
                        <Button size="sm" onClick={() => runAction(`/api/admin/users/${item.id}/activate`, { method: 'POST' })}>
                          Ativar
                        </Button>
                      )}
                      <Button size="sm" variant="outline" onClick={() => { setError(''); setResetUser(item) }}>
                        Redefinir senha
                      </Button>
                      {item.id !== user.id && item.role !== 'admin' && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button size="sm" variant="destructive">Excluir</Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Excluir @{item.username}?</AlertDialogTitle>
                              <AlertDialogDescription>
                                Esta ação remove definitivamente a conta e todos os seus conteúdos. Não pode ser desfeita.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancelar</AlertDialogCancel>
                              <AlertDialogAction onClick={() => runAction(`/api/admin/users/${item.id}`, { method: 'DELETE' })}>
                                Excluir definitivamente
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={Boolean(resetUser)} onOpenChange={(open) => { if (!open) { setResetUser(null); setNewPassword(''); setError('') } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redefinir senha {resetUser ? `de @${resetUser.username}` : ''}</DialogTitle>
            <DialogDescription>
              Defina uma nova senha sem precisar da senha atual.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleReset} className="space-y-4">
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="space-y-2">
              <Label htmlFor="new-password">Nova senha</Label>
              <Input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                minLength={8}
                required
              />
            </div>
            <Button type="submit">Salvar senha</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default AdminPage
