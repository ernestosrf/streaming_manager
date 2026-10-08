import { Link, NavLink } from 'react-router-dom'
import { Badge } from '@/components/ui/badge.jsx'
import { Button } from '@/components/ui/button.jsx'
import { Film, LogOut, Shield, UserRound } from 'lucide-react'
import { useAuth } from '@/context/AuthContext.jsx'

function AppHeader() {
  const { isAuthenticated, user, isAdmin, logout, pendingCount } = useAuth()
  const pendingLabel = pendingCount === 1 ? '1 cadastro pendente' : `${pendingCount} cadastros pendentes`

  return (
    <header className="border-b bg-card">
      <div className="container mx-auto px-4 py-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <Link to="/" className="flex items-center space-x-2">
            <Film className="w-8 h-8 text-primary" />
            <h1 className="text-2xl font-bold">Streaming Manager</h1>
          </Link>

          <nav className="flex flex-wrap items-center gap-2">
            {!isAuthenticated && (
              <>
                <Button variant="outline" asChild>
                  <Link to="/login">Entrar</Link>
                </Button>
                <Button asChild>
                  <Link to="/register">Criar conta</Link>
                </Button>
              </>
            )}

            {isAuthenticated && (
              <>
                <Button variant="outline" asChild>
                  <NavLink to={isAdmin ? '/' : `/${user.username}`}>Minha watchlist</NavLink>
                </Button>
                <Button variant="outline" asChild>
                  <Link to="/account">
                    <UserRound className="w-4 h-4 mr-1" />
                    Minha conta
                  </Link>
                </Button>
                {isAdmin && (
                  <Button variant="outline" asChild>
                    <Link
                      to="/admin"
                      aria-label={pendingCount > 0 ? `Painel, ${pendingLabel}` : 'Painel'}
                    >
                      <Shield className="w-4 h-4 mr-1" />
                      Painel
                      {pendingCount > 0 && (
                        <Badge variant="destructive" className="ml-2">
                          {pendingCount > 99 ? '99+' : pendingCount}
                        </Badge>
                      )}
                    </Link>
                  </Button>
                )}
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>@{user.username}</span>
                  <Button variant="outline" size="sm" onClick={logout}>
                    <LogOut className="w-4 h-4 mr-1" />
                    Sair
                  </Button>
                </div>
              </>
            )}
          </nav>
        </div>
      </div>
    </header>
  )
}

export default AppHeader
