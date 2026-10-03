import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { useAuth } from '@/context/AuthContext.jsx'

function AccountPage() {
  const { isAuthenticated, user, loading, makeAuthenticatedRequest } = useAuth()
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  if (loading) {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSuccess('')

    if (form.new_password !== form.confirm_password) {
      setError('A confirmação da nova senha não confere.')
      return
    }

    setSaving(true)
    try {
      const response = await makeAuthenticatedRequest('/api/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: form.current_password,
          new_password: form.new_password,
        }),
      })
      const data = await response.json()
      if (!response.ok) {
        setError(data.error || 'Não foi possível alterar a senha.')
        return
      }
      setSuccess(data.message)
      setForm({ current_password: '', new_password: '', confirm_password: '' })
    } catch (err) {
      setError(err.message || 'Erro ao alterar senha.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-12 max-w-lg">
      <Card>
        <CardHeader>
          <CardTitle>Minha conta</CardTitle>
          <CardDescription>
            Logado como <strong>@{user.username}</strong>. O username é imutável.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            {success && (
              <Alert>
                <AlertDescription>{success}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="current_password">Senha atual</Label>
              <Input
                id="current_password"
                type="password"
                value={form.current_password}
                onChange={(e) => setForm((prev) => ({ ...prev, current_password: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new_password">Nova senha</Label>
              <Input
                id="new_password"
                type="password"
                value={form.new_password}
                onChange={(e) => setForm((prev) => ({ ...prev, new_password: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm_password">Confirmar nova senha</Label>
              <Input
                id="confirm_password"
                type="password"
                value={form.confirm_password}
                onChange={(e) => setForm((prev) => ({ ...prev, confirm_password: e.target.value }))}
                required
              />
            </div>
            <Button type="submit" disabled={saving}>
              {saving ? 'Salvando...' : 'Alterar senha'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

export default AccountPage
