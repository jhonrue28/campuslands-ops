export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const isForm = typeof FormData !== 'undefined' && options.body instanceof FormData
  if (!isForm && options.body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  if (!headers.Authorization) {
    const token = localStorage.getItem('campuslands_ops_token')
    if (token) headers.Authorization = `Bearer ${token}`
  }
  const response = await fetch(`/api${path}`, { ...options, headers })
  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { detail: text }
    }
  }
  if (!response.ok) {
    const detail = data?.detail
    let message = 'No se pudo completar la operación.'
    if (typeof detail === 'string') message = detail
    else if (Array.isArray(detail)) {
      message = detail.map((item) => item.msg || JSON.stringify(item)).join(' ')
    }
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  return data
}

export function formatWhen(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function withSeconds(value) {
  if (!value) return value
  return value.length === 16 ? `${value}:00` : value
}
