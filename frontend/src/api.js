const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(message, status, detail = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

const request = async (path, options = {}) => {
  const headers = options.body instanceof FormData
    ? { ...(options.headers || {}) }
    : { 'Content-Type': 'application/json', ...(options.headers || {}) }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
    ...options,
    // don't pass Content-Type for FormData (browser sets boundary automatically)
    ...(options.body instanceof FormData ? { headers: options.headers || {} } : {})
  })

  if (!response.ok) {
    let detail = null
    try {
      detail = await response.json()
    } catch {
      detail = null
    }
    throw new ApiError(`API request failed: ${response.status}`, response.status, detail)
  }

  return response.json()
}

export const api = {
  getSensors: (limit = 20) => request(`/api/sensors?limit=${limit}`),
  getPump: () => request('/api/pump'),
  controlPump: (action) => request('/api/pump/control', {
    method: 'POST',
    body: JSON.stringify({ action })
  }),
  getWeather: () => request('/api/weather'),
  getAIPredictions: (limit = 10) => request(`/api/ai/predictions?limit=${limit}`),
  getAIStatus: () => request('/api/ai/status'),
  getWaterSaving: () => request('/api/water-saving'),
  getAlerts: (limit = 50) => request(`/api/alerts?limit=${limit}`),
  resolveAlert: (alertId) => request(`/api/alerts/${alertId}/resolve`, {
    method: 'PUT'
  }),
  getNPK: (limit = 10) => request(`/api/npk?limit=${limit}`),
  getCropRecommendation: () => request('/api/crop-recommendation'),
  getAnalyticsSummary: (periodDays = 30) => request(`/api/analytics/summary?period_days=${periodDays}`),
  getAnalyticsFull: () => request('/api/analytics/full'),
  getDigitalTwinState: () => request('/api/digital-twin/state'),
  runDigitalTwinSimulation: (payload) => request('/api/digital-twin/simulate', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  getConfig: () => request('/api/config'),
  updateConfig: (config) => request('/api/config', {
    method: 'PUT',
    body: JSON.stringify(config)
  }),
  getLogs: (limit = 100) => request(`/api/logs?limit=${limit}`),

  // Crop Lifecycle API
  getActiveCropCycle: () => request('/api/crop-lifecycle/active'),
  listCropCycles: (limit = 50, activeOnly = false) =>
    request(`/api/crop-lifecycle/history?limit=${limit}&active_only=${activeOnly}`),
  createCropCycle: (data) => request('/api/crop-lifecycle', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getCropCycle: (id) => request(`/api/crop-lifecycle/${id}`),
  confirmCrop: (id, data) => request(`/api/crop-lifecycle/${id}/confirm-crop`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  setPlantingDate: (id, plantingDate) =>
    request(`/api/crop-lifecycle/${id}/planting-date`, {
      method: 'POST',
      body: JSON.stringify({ planting_date: plantingDate }),
    }),
  updateLifecycleStatus: (id, status) =>
    request(`/api/crop-lifecycle/${id}/status`, {
      method: 'PUT',
      body: JSON.stringify({ lifecycle_status: status }),
    }),
  getGrowthStage: (id) => request(`/api/crop-lifecycle/${id}/growth-stage`),
  recordHarvest: (id, data) => request(`/api/crop-lifecycle/${id}/harvest`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getYieldComparison: (id) => request(`/api/crop-lifecycle/${id}/yield-comparison`),
  getWaterProductivity: (id) => request(`/api/crop-lifecycle/${id}/water-productivity`),
  getCropPhenology: (cropName) => request(`/api/crop-lifecycle/phenology/${encodeURIComponent(cropName)}`),
  listSupportedCrops: () => request('/api/crop-lifecycle/phenology'),
  createCycleFromRecommendation: (farmerCrop, plantingDate, fieldArea) => {
    const params = new URLSearchParams({ farmer_selected_crop: farmerCrop })
    if (plantingDate) params.append('planting_date', plantingDate)
    if (fieldArea != null) params.append('field_area_m2', fieldArea)
    return request(`/api/crop-recommendation/start-cycle?${params}`, { method: 'POST' })
  },
  deleteCropCycle: (id) => request(`/api/crop-lifecycle/${id}`, { method: 'DELETE' }),
  updateGdd: (id) => request(`/api/crop-lifecycle/${id}/update-gdd`, { method: 'POST' }),

  // ── Plant Disease Detection API ────────────────────────────────────────────
  predictDisease: (formData) => request('/api/disease/predict', {
    method: 'POST',
    body: formData,
  }),
  getDiseaseHistory: (limit = 50, skip = 0) =>
    request(`/api/disease/history?limit=${limit}&skip=${skip}`),
  getDiseaseRecord: (scanId) => request(`/api/disease/history/${scanId}`),
  deleteDiseaseRecord: (scanId) => request(`/api/disease/history/${scanId}`, { method: 'DELETE' }),
  getDiseaseStatus: () => request('/api/disease/status'),

  // ── Pest Detection API ─────────────────────────────────────────────────────
  predictPest: (formData) => request('/api/pest/predict', {
    method: 'POST',
    body: formData,
  }),
  getPestHistory: (limit = 50, skip = 0) =>
    request(`/api/pest/history?limit=${limit}&skip=${skip}`),
  getPestRecord: (scanId) => request(`/api/pest/history/${scanId}`),
  deletePestRecord: (scanId) => request(`/api/pest/history/${scanId}`, { method: 'DELETE' }),
  getPestStatus: () => request('/api/pest/status'),
}

export { ApiError }
