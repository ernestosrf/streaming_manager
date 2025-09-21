import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Checkbox } from '@/components/ui/checkbox.jsx'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog.jsx'
import { Search, Plus, Film, Tv, Zap, Filter, BarChart3, Edit, Trash2, LogOut, Shield } from 'lucide-react'
import LoginModal from '@/components/LoginModal.jsx'
import useAuth from '@/hooks/useAuth.js'
import './App.css'

const API_BASE = '/api'

function App() {
  const { isAuthenticated, login, logout, makeAuthenticatedRequest } = useAuth()
  const [content, setContent] = useState([])
  const [streamings, setStreamings] = useState([])
  const [filteredContent, setFilteredContent] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedType, setSelectedType] = useState('all')
  const [selectedStreamings, setSelectedStreamings] = useState([])
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false)
  const [editingContent, setEditingContent] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    year: '',
    type: 'movie',
    genre: '',
    poster_url: '',
    streaming_ids: []
  })

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    filterContent()
  }, [content, searchTerm, selectedType, selectedStreamings])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [contentRes, streamingsRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/content`),
        fetch(`${API_BASE}/streamings`),
        fetch(`${API_BASE}/content/stats`)
      ])

      const contentData = await contentRes.json()
      const streamingsData = await streamingsRes.json()
      const statsData = await statsRes.json()

      setContent(contentData)
      setStreamings(streamingsData)
      setStats(statsData)
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
    } finally {
      setLoading(false)
    }
  }

  const filterContent = () => {
    let filtered = content

    // Filtro por busca
    if (searchTerm) {
      filtered = filtered.filter(item =>
        item.title.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    // Filtro por tipo
    if (selectedType !== 'all') {
      filtered = filtered.filter(item => item.type === selectedType)
    }

    // Filtro por streamings
    if (selectedStreamings.length > 0) {
      filtered = filtered.filter(item =>
        item.streamings.some(streaming =>
          selectedStreamings.includes(streaming.id.toString())
        )
      )
    }

    setFilteredContent(filtered)
  }

  const resetForm = () => {
    setFormData({
      title: '',
      year: '',
      type: 'movie',
      genre: '',
      poster_url: '',
      streaming_ids: []
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!isAuthenticated) {
      setIsLoginModalOpen(true)
      return
    }
    
    try {
      const url = editingContent ? `${API_BASE}/content/${editingContent.id}` : `${API_BASE}/content`
      const method = editingContent ? 'PUT' : 'POST'
      
      const response = await makeAuthenticatedRequest(url, {
        method: method,
        body: JSON.stringify(formData),
      })

      if (response.ok) {
        setIsAddDialogOpen(false)
        setIsEditDialogOpen(false)
        setEditingContent(null)
        resetForm()
        fetchData()
      }
    } catch (error) {
      console.error('Erro ao salvar conteúdo:', error)
      if (error.message.includes('Sessão expirada')) {
        setIsLoginModalOpen(true)
      }
    }
  }

  const handleEdit = async (item) => {
    if (!isAuthenticated) {
      setIsLoginModalOpen(true)
      return
    }
    
    try {
      // Buscar dados completos do item
      const response = await fetch(`${API_BASE}/content/${item.id}`)
      const fullItem = await response.json()
      
      setEditingContent(fullItem)
      setFormData({
        title: fullItem.title || '',
        year: fullItem.year || '',
        type: fullItem.type || 'movie',
        genre: fullItem.genre || '',
        poster_url: fullItem.poster_url || '',
        streaming_ids: fullItem.streamings.map(s => s.id) || []
      })
      setIsEditDialogOpen(true)
    } catch (error) {
      console.error('Erro ao carregar dados para edição:', error)
    }
  }

  const handleDelete = async (id) => {
    if (!isAuthenticated) {
      setIsLoginModalOpen(true)
      return
    }
    
    try {
      const response = await makeAuthenticatedRequest(`${API_BASE}/content/${id}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        fetchData()
      }
    } catch (error) {
      console.error('Erro ao excluir conteúdo:', error)
      if (error.message.includes('Sessão expirada')) {
        setIsLoginModalOpen(true)
      }
    }
  }

  const handleLoginSuccess = (token) => {
    login(token)
  }

  const handleAddNewContent = () => {
    if (!isAuthenticated) {
      setIsLoginModalOpen(true)
      return
    }
    setIsAddDialogOpen(true)
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
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Carregando...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Film className="w-8 h-8 text-primary" />
              <h1 className="text-2xl font-bold">StreamManager</h1>
            </div>
            
            <div className="flex items-center gap-4">
              {isAuthenticated && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Shield className="w-4 h-4 text-green-500" />
                  <span>Modo Admin</span>
                  <Button variant="outline" size="sm" onClick={logout}>
                    <LogOut className="w-4 h-4 mr-1" />
                    Sair
                  </Button>
                </div>
              )}
              
              <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
                <DialogTrigger asChild>
                  <Button onClick={handleAddNewContent}>
                    <Plus className="w-4 h-4 mr-2" />
                    Adicionar Conteúdo
                  </Button>
                </DialogTrigger>
                
                <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Adicionar Novo Conteúdo</DialogTitle>
                  <DialogDescription>
                    Preencha as informações do filme, série ou anime
                  </DialogDescription>
                </DialogHeader>
                
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="title">Título *</Label>
                      <Input
                        id="title"
                        value={formData.title}
                        onChange={(e) => setFormData({...formData, title: e.target.value})}
                        required
                      />
                    </div>
                    <div>
                      <Label htmlFor="year">Ano</Label>
                      <Input
                        id="year"
                        type="number"
                        value={formData.year}
                        onChange={(e) => setFormData({...formData, year: e.target.value})}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="type">Tipo *</Label>
                      <Select value={formData.type} onValueChange={(value) => setFormData({...formData, type: value})}>
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
                        onChange={(e) => setFormData({...formData, genre: e.target.value})}
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="poster_url">URL do Poster</Label>
                    <Input
                      id="poster_url"
                      value={formData.poster_url}
                      onChange={(e) => setFormData({...formData, poster_url: e.target.value})}
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
                                  streaming_ids: [...formData.streaming_ids, streaming.id]
                                })
                              } else {
                                setFormData({
                                  ...formData,
                                  streaming_ids: formData.streaming_ids.filter(id => id !== streaming.id)
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
                    <Button type="button" variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                      Cancelar
                    </Button>
                    <Button type="submit">Adicionar</Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>

            {/* Dialog de Edição */}
            <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Editar Conteúdo</DialogTitle>
                  <DialogDescription>
                    Atualize as informações do conteúdo
                  </DialogDescription>
                </DialogHeader>
                
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="edit-title">Título *</Label>
                      <Input
                        id="edit-title"
                        value={formData.title}
                        onChange={(e) => setFormData({...formData, title: e.target.value})}
                        required
                      />
                    </div>
                    <div>
                      <Label htmlFor="edit-year">Ano</Label>
                      <Input
                        id="edit-year"
                        type="number"
                        value={formData.year}
                        onChange={(e) => setFormData({...formData, year: e.target.value})}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="edit-type">Tipo *</Label>
                      <Select value={formData.type} onValueChange={(value) => setFormData({...formData, type: value})}>
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
                      <Label htmlFor="edit-genre">Gênero</Label>
                      <Input
                        id="edit-genre"
                        value={formData.genre}
                        onChange={(e) => setFormData({...formData, genre: e.target.value})}
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="edit-poster_url">URL do Poster</Label>
                    <Input
                      id="edit-poster_url"
                      value={formData.poster_url}
                      onChange={(e) => setFormData({...formData, poster_url: e.target.value})}
                    />
                  </div>

                  <div>
                    <Label>Streamings Disponíveis</Label>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      {streamings.map((streaming) => (
                        <div key={streaming.id} className="flex items-center space-x-2">
                          <Checkbox
                            id={`edit-streaming-${streaming.id}`}
                            checked={formData.streaming_ids.includes(streaming.id)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setFormData({
                                  ...formData,
                                  streaming_ids: [...formData.streaming_ids, streaming.id]
                                })
                              } else {
                                setFormData({
                                  ...formData,
                                  streaming_ids: formData.streaming_ids.filter(id => id !== streaming.id)
                                })
                              }
                            }}
                          />
                          <Label htmlFor={`edit-streaming-${streaming.id}`} className="text-sm">
                            {streaming.name}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-end space-x-2">
                    <Button type="button" variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                      Cancelar
                    </Button>
                    <Button type="submit">Salvar Alterações</Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>
        </div>
      </header>      <div className="container mx-auto px-4 py-6">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total</CardTitle>
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
          </div>
        )}

        {/* Filters */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center">
                <Filter className="w-5 h-5 mr-2" />
                Filtros
              </CardTitle>
              <div className="text-sm text-muted-foreground">
                {filteredContent.length} resultado{filteredContent.length !== 1 ? 's' : ''} encontrado{filteredContent.length !== 1 ? 's' : ''}
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
                      variant={selectedStreamings.includes(streaming.id.toString()) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => {
                        const streamingId = streaming.id.toString()
                        if (selectedStreamings.includes(streamingId)) {
                          setSelectedStreamings(selectedStreamings.filter(id => id !== streamingId))
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

        {/* Content Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredContent.map((item) => (
            <Card key={item.id} className="overflow-hidden">
              {item.poster_url && (
                <div className="aspect-[2/3] overflow-hidden">
                  <img
                    src={item.poster_url}
                    alt={item.title}
                    className="w-full h-full object-cover"
                  />
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
                {item.year && (
                  <CardDescription>{item.year}</CardDescription>
                )}
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
                
                {/* Botões de Ação */}
                <div className="flex gap-2 mt-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEdit(item)}
                    className="flex-1"
                  >
                    <Edit className="w-4 h-4 mr-1" />
                    Editar
                  </Button>
                  
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="destructive" size="sm" className="flex-1">
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
                ? 'Adicione seu primeiro filme, série ou anime!'
                : 'Tente ajustar os filtros ou adicionar novo conteúdo.'
              }
            </p>
          </div>
        )}
      </div>

      {/* Login Modal */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onLoginSuccess={handleLoginSuccess}
      />
    </div>
  )
}

export default App

