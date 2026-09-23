import React from 'react'
import { Leaf } from 'lucide-react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
} from 'chart.js'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend)

const NPK = () => {
  const { isDark } = useDarkMode()
  const { data, loading, error } = useApiData(() => api.getNPK(10), [], { intervalMs: 10000 })
  const latest = data?.latest
  const history = (data?.history || []).slice().reverse()

  const npkData = [
    { name: 'Nitrogen (N)', value: latest?.nitrogen_mg_kg, unit: 'mg/kg', status: latest?.status, color: '#10b981' },
    { name: 'Phosphorus (P)', value: latest?.phosphorus_mg_kg, unit: 'mg/kg', status: latest?.status, color: '#10b981' },
    { name: 'Potassium (K)', value: latest?.potassium_mg_kg, unit: 'mg/kg', status: latest?.status, color: '#10b981' },
    { name: 'pH', value: latest?.ph, unit: '', status: latest?.status, color: '#10b981' },
    { name: 'EC', value: latest?.ec, unit: 'dS/m', status: latest?.status, color: '#10b981' },
    { name: 'Soil Temp', value: latest?.soil_temp_c, unit: '°C', status: latest?.status, color: '#10b981' },
    { name: 'Soil Moisture', value: latest?.soil_moisture_percent, unit: '%', status: latest?.status, color: '#10b981' },
    { name: 'Battery', value: latest?.battery_voltage, unit: 'V', status: latest?.status, color: '#10b981' }
  ]

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-3">
        <Leaf className="w-8 h-8 text-primary-500" />
        NPK Sensors
      </h2>
      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading live NPK data...</p>
      )}
      {error && (
        <p className="text-sm text-red-500">Unable to load live NPK data.</p>
      )}
      {!loading && !error && !latest && (
        <p className="text-sm text-gray-500 dark:text-gray-400">No Live Data Available</p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {npkData.map((item) => (
          <div
            key={item.name}
            className={`rounded-xl p-6 shadow-sm border ${
              isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
            }`}
          >
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">{item.name}</p>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                item.value !== null && item.value !== undefined
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
              }`}>
                {item.value !== null && item.value !== undefined ? (item.status || 'healthy') : 'no data'}
              </span>
            </div>
            <p className="text-4xl font-bold" style={{ color: item.value !== null && item.value !== undefined ? item.color : 'inherit' }}>
              {formatNpkValue(item.value)}
              {item.value !== null && item.value !== undefined && item.unit && <span className="text-lg ml-1">{item.unit}</span>}
            </p>
          </div>
        ))}
      </div>
      <div className={`rounded-xl p-6 shadow-sm border ${
        isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}>
        <h3 className="text-lg font-semibold mb-4">NPK History</h3>
        <div className="h-80">
          {history.length > 0 ? (
            <Line data={buildChartData(history)} options={buildChartOptions(isDark)} />
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
              No Live Data Available
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const formatNpkValue = (value) => {
  if (value === null || value === undefined) return '--'
  const numericValue = Number(value)
  return Number.isInteger(numericValue) ? numericValue : numericValue.toFixed(1)
}

const buildChartData = (history) => ({
  labels: history.map((item) => formatTime(item.timestamp)),
  datasets: [
    {
      label: 'Nitrogen',
      data: history.map((item) => item.nitrogen_mg_kg ?? null),
      borderColor: '#10b981',
      tension: 0.3,
      pointRadius: 4
    },
    {
      label: 'Phosphorus',
      data: history.map((item) => item.phosphorus_mg_kg ?? null),
      borderColor: '#3b82f6',
      tension: 0.3,
      pointRadius: 4
    },
    {
      label: 'Potassium',
      data: history.map((item) => item.potassium_mg_kg ?? null),
      borderColor: '#f59e0b',
      tension: 0.3,
      pointRadius: 4
    },
    {
      label: 'Soil Moisture',
      data: history.map((item) => item.soil_moisture_percent ?? null),
      borderColor: '#8b5cf6',
      tension: 0.3,
      pointRadius: 4
    },
    {
      label: 'Soil Temp',
      data: history.map((item) => item.soil_temp_c ?? null),
      borderColor: '#ef4444',
      tension: 0.3,
      pointRadius: 4
    }
  ]
})

const buildChartOptions = (isDark) => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: isDark ? '#e5e7eb' : '#374151'
      }
    }
  },
  scales: {
    x: {
      ticks: { color: isDark ? '#9ca3af' : '#6b7280' },
      grid: { color: isDark ? '#374151' : '#e5e7eb' }
    },
    y: {
      ticks: { color: isDark ? '#9ca3af' : '#6b7280' },
      grid: { color: isDark ? '#374151' : '#e5e7eb' }
    }
  }
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default NPK
