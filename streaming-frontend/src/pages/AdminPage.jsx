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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import PlatformsPanel from '@/components/PlatformsPanel.jsx'
import { useAuth } from '@/context/AuthContext.jsx'
import { ROLE_ADMIN, USER_STATUS, USER_STATUS_LABELS, accountLabel } from '@/lib/constants.js'


const USERS_PER_PAGE = 50

function AdminPage() {
  const { isAuthenticated, isAdmin, loading, login, makeAuthenticatedRequest, user, meta, pendingCount, refreshPendingCount } = useAuth()
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [resetUser, setResetUser] = useState(null)
  const [newPassword, setNewPassword] = useState('')
  const [page, setPage] = useState(1)
  const [totalUsers, setTotalUsers] = useState(0)

  const loadUsers = useCallback(async (signal) => {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (status !== 'all') params.set('status', status)
    params.set('page', String(page))
    params.set('per_page', String(USERS_PER_PAGE))
    const response = await makeAuthenticatedRequest(`/api/admin/users?${params.toString()}`, { signal })
    if (response.ok) {
      setUsers(await response.json())
      setTotalUsers(Number(response.headers.get('X-Total-Count')) || 0)
    }
  }, [makeAuthenticatedRequest, page, search, status])

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
      await Promise.all([loadUsers(), refreshPendingCount()])
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
    item.role === ROLE_ADMIN || item.username === meta?.admin_username ? '/' : `/${item.username}`
  )

  return (
    <div className="container mx-auto px-4 py-6 space-y-4">
      <div>
        <h2 className="text-2xl font-bold">Painel administrativo</h2>
        <p className="text-muted-foreground">
          Gerencie cadastros, senhas e as plataformas usadas em todas as watchlists.
        </p>
      </div>

      <Tabs defaultValue="users">
        <TabsList>
          <TabsTrigger value="users">
            Usuários
            {pendingCount > 0 && (
              <Badge variant="destructive" className="ml-2">
                {pendingCount > 99 ? '99+' : pendingCount}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="platforms">Plataformas</TabsTrigger>
        </TabsList>

        <TabsContent value="users">
      <Card>
        <CardHeader>
          <CardTitle>Usuários</CardTitle>
          <CardDescription>
            Aprove cadastros, altere o status das contas e redefina senhas.
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
                onChange={(e) => { setSearch(e.target.value.toLowerCase()); setPage(1) }}
                placeholder="ex: maria"
              />
            </div>
            <div>
              <Label>Status</Label>
              <Select value={status} onValueChange={(value) => { setStatus(value); setPage(1) }}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {Object.entries(USER_STATUS_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>{label}</SelectItem>
                  ))}
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
                  <TableCell>{accountLabel(item)}</TableCell>
                  <TableCell>{item.role}</TableCell>
                  <TableCell>
                    <Badge variant={item.status === USER_STATUS.ACTIVE ? 'default' : 'secondary'}>
                      {USER_STATUS_LABELS[item.status] || item.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {item.status === USER_STATUS.ACTIVE ? (
                      <Button variant="link" className="px-0" asChild>
                        <Link to={watchlistPath(item)}>Ver watchlist</Link>
                      </Button>
                    ) : (
                      <span className="text-muted-foreground text-sm">Indisponível</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      {item.status === USER_STATUS.PENDING && (
                        <>
                          <Button size="sm" onClick={() => runAction(`/api/admin/users/${item.id}/approve`, { method: 'POST' })}>
                            Aprovar
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => runAction(`/api/admin/users/${item.id}/reject`, { method: 'POST' })}>
                            Rejeitar
                          </Button>
                        </>
                      )}
                      {item.status === USER_STATUS.REJECTED && (
                        <Button size="sm" onClick={() => runAction(`/api/admin/users/${item.id}/approve`, { method: 'POST' })}>
                          Aprovar
                        </Button>
                      )}
                      {item.status === USER_STATUS.ACTIVE && item.id !== user.id && (
                        <Button size="sm" variant="secondary" onClick={() => runAction(`/api/admin/users/${item.id}/deactivate`, { method: 'POST' })}>
                          Desativar
                        </Button>
                      )}
                      {item.status === USER_STATUS.INACTIVE && (
                        <Button size="sm" onClick={() => runAction(`/api/admin/users/${item.id}/activate`, { method: 'POST' })}>
                          Ativar
                        </Button>
                      )}
                      <Button size="sm" variant="outline" onClick={() => { setError(''); setResetUser(item) }}>
                        Redefinir senha
                      </Button>
                      {item.id !== user.id && item.role !== ROLE_ADMIN && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button size="sm" variant="destructive">Excluir</Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Excluir {accountLabel(item)}?</AlertDialogTitle>
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

          {totalUsers > USERS_PER_PAGE && (
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Página {page} de {Math.ceil(totalUsers / USERS_PER_PAGE)} · {totalUsers} usuários
              </span>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={page === 1} onClick={() => setPage((current) => current - 1)}>
                  Anterior
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page * USERS_PER_PAGE >= totalUsers}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Próxima
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
        </TabsContent>

        <TabsContent value="platforms">
          <PlatformsPanel />
        </TabsContent>
      </Tabs>

      <Dialog open={Boolean(resetUser)} onOpenChange={(open) => { if (!open) { setResetUser(null); setNewPassword(''); setError('') } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Redefinir senha {resetUser ? (resetUser.role === ROLE_ADMIN ? 'do Administrador' : `de @${resetUser.username}`) : ''}
            </DialogTitle>
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
