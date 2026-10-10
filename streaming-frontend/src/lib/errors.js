export class SessionExpiredError extends Error {
  constructor() {
    super('Sessão expirada. Faça login novamente.')
    this.name = 'SessionExpiredError'
  }
}
