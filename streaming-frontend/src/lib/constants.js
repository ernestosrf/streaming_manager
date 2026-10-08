export const ROLE_ADMIN = 'admin'
export const ADMIN_LABEL = 'Administrador'

export function accountLabel(account) {
  if (account?.role === ROLE_ADMIN) return ADMIN_LABEL
  return account?.username ? `@${account.username}` : ''
}

export const USER_STATUS = {
  PENDING: 'pending',
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  REJECTED: 'rejected',
}

export const USER_STATUS_LABELS = {
  [USER_STATUS.PENDING]: 'Pendente',
  [USER_STATUS.ACTIVE]: 'Ativo',
  [USER_STATUS.INACTIVE]: 'Inativo',
  [USER_STATUS.REJECTED]: 'Rejeitado',
}

export const CONTENT_TYPE_LABELS = {
  movie: 'Filme',
  series: 'Série',
  anime: 'Anime',
}

export const getContentTypeLabel = (type) => CONTENT_TYPE_LABELS[type] ?? type
