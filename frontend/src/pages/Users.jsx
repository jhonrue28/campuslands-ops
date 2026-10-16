import { useEffect, useState } from 'react'
import { api } from '../api'
import { Banner, Field, PageHeader } from '../components/ui/index.js'

const emptyForm = {
  full_name: '',
  username: '',
  password: '',
  role: 'operator',
  notes: '',
  active: true,
}

export default function Users() {
  const [users, setUsers] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    setUsers(await api('/users'))
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [])

  function update(event) {
    const { name, value, type, checked } = event.target
    setForm((current) => ({ ...current, [name]: type === 'checkbox' ? checked : value }))
  }

  async function onSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setNotice('')
    try {
      if (editingId) {
        const payload = {
          full_name: form.full_name,
          username: form.username,
          role: form.role,
          notes: form.notes,
          active: form.active,
        }
        if (form.password) payload.password = form.password
        await api(`/users/${editingId}`, { method: 'PATCH', body: JSON.stringify(payload) })
        setNotice('Usuario actualizado.')
      } else {
        await api('/users', { method: 'POST', body: JSON.stringify(form) })
        setNotice('Usuario creado.')
      }
      setForm(emptyForm)
      setEditingId('')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function editUser(user) {
    setEditingId(user.id)
    setForm({
      full_name: user.full_name,
      username: user.username,
      password: '',
      role: user.role,
      notes: user.notes || '',
      active: user.active,
    })
  }

  async function removeUser(id) {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await api(`/users/${id}`, { method: 'DELETE' })
      setNotice('Usuario eliminado.')
      if (editingId === id) {
        setEditingId('')
        setForm(emptyForm)
      }
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section>
      <PageHeader title="Usuarios" />
      {error && <Banner kind="error">{error}</Banner>}
      {notice && <Banner kind="ok">{notice}</Banner>}

      <div className="grid-2">
        <form className="card" onSubmit={onSubmit}>
          <h2>{editingId ? 'Editar usuario' : 'Nuevo usuario'}</h2>
          <Field label="Nombre completo">
            <input name="full_name" value={form.full_name} onChange={update} required />
          </Field>
          <Field label="Usuario de acceso">
            <input name="username" value={form.username} onChange={update} required />
          </Field>
          <Field label={editingId ? 'Nueva contraseña (opcional)' : 'Contraseña'}>
            <input
              name="password"
              type="password"
              value={form.password}
              onChange={update}
              required={!editingId}
              minLength={6}
            />
          </Field>
          <Field label="Rol">
            <select name="role" value={form.role} onChange={update}>
              <option value="admin">Administrador</option>
              <option value="operator">Operador</option>
            </select>
          </Field>
          <Field label="Notas">
            <textarea name="notes" value={form.notes} onChange={update} rows={3} />
          </Field>
          <label className="field checkbox-field">
            <span>Activo</span>
            <input name="active" type="checkbox" checked={form.active} onChange={update} />
          </label>
          <div className="row-actions">
            <button type="submit" disabled={loading}>
              {loading ? 'Guardando…' : editingId ? 'Guardar cambios' : 'Crear usuario'}
            </button>
            {editingId && (
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setEditingId('')
                  setForm(emptyForm)
                }}
              >
                Cancelar
              </button>
            )}
          </div>
        </form>

        <article className="card">
          <h2>Usuarios con acceso</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Usuario</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.full_name}</td>
                    <td>{user.username}</td>
                    <td>{user.role}</td>
                    <td>{user.active ? 'Activo' : 'Inactivo'}</td>
                    <td>
                      <div className="row-actions">
                        <button type="button" className="secondary" onClick={() => editUser(user)} disabled={loading}>
                          Editar
                        </button>
                        <button type="button" className="secondary" onClick={() => removeUser(user.id)} disabled={loading}>
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </div>
    </section>
  )
}
