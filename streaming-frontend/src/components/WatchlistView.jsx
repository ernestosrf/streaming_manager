import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Switch } from '@/components/ui/switch.jsx'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog.jsx'
import { Search, Plus, Film, Tv, Zap, Filter, BarChart3, Edit, Trash2, Eye, EyeOff } from 'lucide-react'
import ContentFormDialog from '@/components/ContentFormDialog.jsx'
import { useAuth } from '@/context/AuthContext.jsx'

function WatchlistView({ ownerUsername, isHome = false }) {
  const navigate = useNavigate()
  const { isAuthenticated, user, logout, makeAuthenticatedRequest, getAuthHeaders } = useAuth()
  const [owner, setOwner] = useState(null)
  const [content, setContent] = useState([])
  const [streamings, setStreamings] = useState([])
  const [filteredContent, setFilteredContent] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedType, setSelectedType] = useState('all')
  const [selectedStreamings, setSelectedStreamings] = useState([])
  const [showInactive, setShowInactive] = useState(false)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingContent, setEditingContent] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const fetchControllerRef = useRef(null)

  const isOwner = Boolean(isAuthenticated && user && owner && user.username === owner.username)

  const fetchData = useCallback(async () => {
    // Cancela a carga anterior para que uma resposta antiga não sobrescreva a atual
    // (ex.: navegar de /alice para /bob ou alternar "Mostrar inativos" rapidamente).
    fetchControllerRef.current?.abort()
    const controller = new AbortController()
    fetchControllerRef.current = controller
    const { signal } = controller

    try {
      setLoading(true)
      setNotFound(false)
      const ownerPath = encodeURIComponent(ownerUsername ?? '')
      const watchlistUrl = isHome
        ? `/api/watchlists${showInactive ? '?show_inactive=true' : ''}`
        : `/api/watchlists/${ownerPath}${showInactive ? '?show_inactive=true' : ''}`
      const statsUrl = isHome
        ? '/api/content/stats'
        : `/api/watchlists/${ownerPath}/stats`

      const headers = getAuthHeaders()
      const [watchlistRes, streamingsRes, statsRes] = await Promise.all([
        fetch(watchlistUrl, { headers, signal }),
        fetch('/api/streamings', { signal }),
        fetch(statsUrl, { headers, signal }),
      ])

      if (watchlistRes.status === 401 || statsRes.status === 401) {
        // Token expirado: encerra a sessão; a troca de token dispara nova carga sem autenticação.
        logout()
        return
      }

      if (watchlistRes.status === 404) {
        setNotFound(true)
        setContent([])
        setOwner(null)
        return
      }

      const watchlistData = await watchlistRes.json()
      const streamingsData = await streamingsRes.json()
      const statsData = statsRes.ok ? await statsRes.json() : null

      setOwner(watchlistData.owner)
      setContent(watchlistData.contents || [])
      setStreamings(streamingsData)
      setStats(statsData)
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Erro ao carregar dados:', error)
      }
    } finally {
      if (fetchControllerRef.current === controller) {
        setLoading(false)
      }
    }
  }, [getAuthHeaders, isHome, logout, ownerUsername, showInactive])

  useEffect(() => {
    fetchData()
    return () => fetchControllerRef.current?.abort()
  }, [fetchData, isAuthenticated])

  const filterContent = useCallback(() => {
    let filtered = content

    if (searchTerm) {
      filtered = filtered.filter((item) =>
        item.title.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    if (selectedType !== 'all') {
      filtered = filtered.filter((item) => item.type === selectedType)
    }

    if (selectedStreamings.length > 0) {
      filtered = filtered.filter((item) =>
        item.streamings.some((streaming) =>
          selectedStreamings.includes(streaming.id.toString())
        )
      )
    }

    setFilteredContent(filtered)
  }, [content, searchTerm, selectedType, selectedStreamings])

  useEffect(() => {
    filterContent()
  }, [filterContent])

  const handleAdd = () => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    setEditingContent(null)
    setIsFormOpen(true)
  }

  const handleEdit = async (item) => {
    try {
      const response = await makeAuthenticatedRequest(`/api/content/${item.id}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      setEditingContent(await response.json())
      setIsFormOpen(true)
    } catch (error) {
      console.error('Erro ao carregar dados para edição:', error)
      if (error.message.includes('Sessão expirada')) {
        navigate('/login')
      }
    }
  }

  const handleDelete = async (id) => {
    try {
      const response = await makeAuthenticatedRequest(`/api/content/${id}`, { method: 'DELETE' })
      if (response.ok) {
        fetchData()
      }
    } catch (error) {
      console.error('Erro ao excluir conteúdo:', error)
      if (error.message.includes('Sessão expirada')) {
        navigate('/login')
      }
    }
  }

  const handleToggleActive = async (item) => {
    try {
      // Envia o estado desejado para que cliques repetidos sejam idempotentes.
      const response = await makeAuthenticatedRequest(`/api/content/${item.id}/toggle`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !item.is_active }),
      })
      if (response.ok) {
        fetchData()
      }
    } catch (error) {
      console.error('Erro ao alternar status do conteúdo:', error)
      if (error.message.includes('Sessão expirada')) {
        navigate('/login')
      }
    }
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case 'movie': return <Film className="w-4 h-4" />
      case 'series': return <Tv className="w-4 h-4" />
      case 'anime': return <Zap className="w-4 h-4" />
      default: return <Film className="w-4 h-4" />
    }
  }

  const getTypeLabel = (type) => {
    switch (type) {
      case 'movie': return 'Filme'
      case 'series': return 'Série'
      case 'anime': return 'Anime'
      default: return type
    }
  }

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Carregando...</p>
        </div>
      </div>
    )
  }

  if (notFound) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <h2 className="text-2xl font-semibold mb-2">Watchlist não encontrada</h2>
        <p className="text-muted-foreground">
          Esta conta não existe, ainda não foi aprovada ou está indisponível.
        </p>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">
            {isHome ? 'Watchlist principal' : `Watchlist de @${owner?.username}`}
          </h2>
          <p className="text-muted-foreground">
            {isOwner ? 'Você pode gerenciar os títulos desta lista.' : 'Catálogo público para visualização.'}
          </p>
        </div>
        {isOwner && (
          <Button onClick={handleAdd}>
            <Plus className="w-4 h-4 mr-2" />
            Adicionar Conteúdo
          </Button>
        )}
      </div>

      {isHome && !isAuthenticated && (
        <Card className="mb-6">
          <CardContent className="py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <p className="text-sm md:text-base">
              Esta é a watchlist pública principal. Entre ou crie uma conta para montar a sua.
            </p>
            <div className="flex gap-2">
              <Button variant="outline" asChild>
                <Link to="/login">Entrar</Link>
              </Button>
              <Button asChild>
                <Link to="/register">Criar conta</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isAuthenticated && isHome && user && owner && user.username !== owner.username && (
        <Card className="mb-6">
          <CardContent className="py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <p className="text-sm md:text-base">Acesse a sua watchlist para adicionar e editar títulos.</p>
            <Button asChild>
              <Link to={`/${user.username}`}>Minha watchlist</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {stats && (
        <div className={`grid grid-cols-1 gap-4 mb-6 ${isOwner ? 'md:grid-cols-5' : 'md:grid-cols-4'}`}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Ativo</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_content}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Filmes</CardTitle>
              <Film className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.by_type.movies}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Séries</CardTitle>
              <Tv className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.by_type.series}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Animes</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.by_type.animes}</div>
            </CardContent>
          </Card>
          {isOwner && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Inativos</CardTitle>
                <EyeOff className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_inactive}</div>
                <p className="text-xs text-muted-foreground mt-1">Temporariamente</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center">
              <Filter className="w-5 h-5 mr-2" />
              Filtros
            </CardTitle>
            <div className="flex items-center gap-4">
              {isOwner && (
                <div className="flex items-center space-x-2">
                  <Switch
                    id="show-inactive"
                    checked={showInactive}
                    onCheckedChange={setShowInactive}
                  />
                  <Label htmlFor="show-inactive" className="text-sm cursor-pointer">
                    Mostrar inativos
                  </Label>
                </div>
              )}
              <div className="text-sm text-muted-foreground">
                {filteredContent.length} resultado{filteredContent.length !== 1 ? 's' : ''} encontrado{filteredContent.length !== 1 ? 's' : ''}
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="search">Buscar</Label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Buscar por título..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="type-filter">Tipo</Label>
              <Select value={selectedType} onValueChange={setSelectedType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="movie">Filmes</SelectItem>
                  <SelectItem value="series">Séries</SelectItem>
                  <SelectItem value="anime">Animes</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Streamings</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {streamings.map((streaming) => (
                  <Badge
                    key={streaming.id}
                    variant={selectedStreamings.includes(streaming.id.toString()) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => {
                      const streamingId = streaming.id.toString()
                      if (selectedStreamings.includes(streamingId)) {
                        setSelectedStreamings(selectedStreamings.filter((id) => id !== streamingId))
                      } else {
                        setSelectedStreamings([...selectedStreamings, streamingId])
                      }
                    }}
                  >
                    {streaming.name}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredContent.map((item) => (
          <Card key={item.id} className={`overflow-hidden ${!item.is_active ? 'opacity-60 border-dashed' : ''}`}>
            {item.poster_url && (
              <div className="aspect-[2/3] overflow-hidden relative">
                <img
                  src={item.poster_url}
                  alt={item.title}
                  className={`w-full h-full object-cover ${!item.is_active ? 'grayscale' : ''}`}
                />
                {!item.is_active && (
                  <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                    <Badge variant="secondary" className="text-xs">
                      <EyeOff className="w-3 h-3 mr-1" />
                      Inativo
                    </Badge>
                  </div>
                )}
              </div>
            )}
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg line-clamp-1">{item.title}</CardTitle>
                <Badge variant="outline" className="flex items-center gap-1">
                  {getTypeIcon(item.type)}
                  {getTypeLabel(item.type)}
                </Badge>
              </div>
              {item.year && <CardDescription>{item.year}</CardDescription>}
            </CardHeader>
            <CardContent>
              {item.genre && (
                <p className="text-sm text-muted-foreground mb-3">{item.genre}</p>
              )}
              {item.streamings.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {item.streamings.map((streaming) => (
                    <Badge
                      key={streaming.id}
                      variant="secondary"
                      className="text-xs"
                      style={{ backgroundColor: streaming.color + '20', color: streaming.color }}
                    >
                      {streaming.name}
                    </Badge>
                  ))}
                </div>
              )}

              {isOwner && (
                <div className="flex flex-col gap-2">
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => handleEdit(item)} className="flex-1">
                      <Edit className="w-4 h-4 mr-1" />
                      Editar
                    </Button>
                    <Button
                      variant={item.is_active ? 'secondary' : 'default'}
                      size="sm"
                      onClick={() => handleToggleActive(item)}
                      className="flex-1"
                    >
                      {item.is_active ? (
                        <>
                          <EyeOff className="w-4 h-4 mr-1" />
                          Desativar
                        </>
                      ) : (
                        <>
                          <Eye className="w-4 h-4 mr-1" />
                          Ativar
                        </>
                      )}
                    </Button>
                  </div>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="destructive" size="sm" className="w-full">
                        <Trash2 className="w-4 h-4 mr-1" />
                        Excluir
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Confirmar Exclusão</AlertDialogTitle>
                        <AlertDialogDescription>
                          Tem certeza que deseja excluir "{item.title}"? Esta ação não pode ser desfeita.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction onClick={() => handleDelete(item.id)}>
                          Excluir
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredContent.length === 0 && (
        <div className="text-center py-12">
          <Film className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Nenhum conteúdo encontrado</h3>
          <p className="text-muted-foreground">
            {content.length === 0
              ? (isOwner ? 'Adicione seu primeiro filme, série ou anime!' : 'Esta watchlist ainda não tem títulos.')
              : 'Tente ajustar os filtros.'}
          </p>
        </div>
      )}

      {isOwner && (
        <ContentFormDialog
          open={isFormOpen}
          onOpenChange={setIsFormOpen}
          streamings={streamings}
          editingContent={editingContent}
          onSaved={fetchData}
        />
      )}
    </div>
  )
}

export default WatchlistView
