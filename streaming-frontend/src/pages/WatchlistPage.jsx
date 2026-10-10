import { Navigate, useParams } from 'react-router-dom'
import WatchlistView from '@/components/WatchlistView.jsx'
import { useAuth } from '@/context/AuthContext.jsx'

function WatchlistPage() {
  const { username } = useParams()
  const { meta, loading } = useAuth()

  if (loading) {
    return null
  }

  if (username && meta?.admin_username && username === meta.admin_username) {
    return <Navigate to="/" replace />
  }

  if (!username) {
    return <WatchlistView isHome />
  }

  return <WatchlistView ownerUsername={username} />
}

export default WatchlistPage
