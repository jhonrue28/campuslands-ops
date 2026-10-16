/** Hotspots Torre Zenith — alineados a los cuadros de color de la imagen de referencia (1152×648). */
export const FLOOR_PLAN_SRC = '/plano-campuslands.png?v=5'
export const FLOOR_PLAN_WIDTH = 1152
export const FLOOR_PLAN_HEIGHT = 648

export const FLOOR_HOTSPOTS = [
  { id: 'aula-apolo', name: 'Apolo', color: '#e11d48', left: 17.19, top: 23.46, width: 8.77, height: 13.27 },
  { id: 'aula-artemis', name: 'Artemis', color: '#2563eb', left: 17.19, top: 36.73, width: 8.51, height: 13.27 },
  { id: 'aula-sputnik', name: 'Sputnik', color: '#a21caf', left: 26.04, top: 23.46, width: 8.85, height: 13.89 },
  { id: 'aula-skylab', name: 'Skylab', color: '#ea580c', left: 27.6, top: 40.74, width: 7.47, height: 8.95 },
  { id: 'sala-cosmos', name: 'Cosmos', color: '#7c2d12', left: 48.09, top: 40.28, width: 5.3, height: 8.8 },
  { id: 'sala-verde-1', name: 'Sala verde 1', color: '#6b21a8', left: 49.91, top: 56.17, width: 1.65, height: 4.63 },
  { id: 'sala-verde-2', name: 'Sala verde 2', color: '#4c1d95', left: 49.83, top: 61.11, width: 1.91, height: 4.01 },
  { id: 'sala-amarilla-1', name: 'Sala Amarilla 1', color: '#ca8a04', left: 61.46, top: 43.98, width: 1.82, height: 4.01 },
  { id: 'sala-amarilla-2', name: 'Sala Amarilla 2', color: '#db2777', left: 63.37, top: 43.98, width: 1.82, height: 4.01 },
  // Ala derecha: Auditorio arriba-izquierda; Azul y Blanca debajo, Azul a la izquierda de Blanca
  { id: 'sala-auditorio', name: 'Auditorio', color: '#a16207', left: 56.68, top: 2.62, width: 7.64, height: 21.6 },
  { id: 'sala-azul', name: 'Azul', color: '#0284c7', left: 57.99, top: 23.77, width: 3.65, height: 8.95 },
  { id: 'sala-blanca', name: 'Blanca', color: '#65a30d', left: 61.81, top: 23.77, width: 2.95, height: 8.95 },
]

export function hotspotById(id) {
  return FLOOR_HOTSPOTS.find((item) => item.id === id) || null
}
