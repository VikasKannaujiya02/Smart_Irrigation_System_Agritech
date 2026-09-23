import React from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const SensorChart = () => {
  const { isDark } = useDarkMode()
  const { data: sensorResponse, loading, error } = useApiData(() => api.getSensors(60), [], { intervalMs: 5000 })
  const sensorRows = sensorResponse?.sensors || []

  // Filter moisture readings — exclude clearly zero / null values
  const moistureReadings = sensorRows
    .filter(s => s.sensor_id.startsWith('soil_moisture_'))
    .slice()
    .reverse()

  // Filter temperature readings — exclude zero (uncalibrated / missing sensor)
  const temperatureReadings = sensorRows
    .filter(s => s.sensor_id.startsWith('temp_') && s.value !== 0 && s.value !== null)
    .slice()
    .reverse()

  // Build unified time-labels from whichever dataset has more points
  const labels = buildLabels(moistureReadings, temperatureReadings)
  const hasChartData = labels.length > 0
  const hasTempData = temperatureReadings.length > 0

  const gridColor = isDark ? '#374151' : '#e5e7eb'
  const tickColor = isDark ? '#9ca3af' : '#6b7280'

  const data = {
    labels,
    datasets: [
      {
        label: 'Soil Moisture (%)',
        data: labels.map(l => findValueForLabel(moistureReadings, l)),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.12)',
        tension: 0.4,
        fill: true,
        pointRadius: 4,
        pointHoverRadius: 6,
        yAxisID: 'yMoisture',
      },
      ...(hasTempData ? [{
        label: 'Temperature (°C)',
        data: labels.map(l => findValueForLabel(temperatureReadings, l)),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.08)',
        tension: 0.4,
        fill: false,
        pointRadius: 4,
        pointHoverRadius: 6,
        yAxisID: 'yTemp',
        borderDash: [4, 2],
      }] : []),
    ]
  }

  // Compute moisture min/max for better axis scaling
  const moistureVals = moistureReadings.map(r => r.value).filter(v => v !== null)
  const mMin = moistureVals.length ? Math.max(0, Math.min(...moistureVals) - 5) : 0
  const mMax = moistureVals.length ? Math.min(100, Math.max(...moistureVals) + 5) : 100

  const tempVals = temperatureReadings.map(r => r.value).filter(v => v !== null)
  const tMin = tempVals.length ? Math.floor(Math.min(...tempVals) - 2) : 10
  const tMax = tempVals.length ? Math.ceil(Math.max(...tempVals) + 2) : 50

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        labels: { color: isDark ? '#e5e7eb' : '#374151', padding: 16, usePointStyle: true }
      },
      tooltip: {
        callbacks: {
          label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(1) ?? '--'}`
        }
      }
    },
    scales: {
      x: {
        ticks: { color: tickColor, maxTicksLimit: 8 },
        grid: { color: gridColor }
      },
      yMoisture: {
        type: 'linear',
        position: 'left',
        min: mMin,
        max: mMax,
        ticks: {
          color: '#10b981',
          callback: v => `${v}%`
        },
        grid: { color: gridColor },
        title: { display: true, text: 'Moisture (%)', color: '#10b981', font: { size: 11 } }
      },
      ...(hasTempData ? {
        yTemp: {
          type: 'linear',
          position: 'right',
          min: tMin,
          max: tMax,
          ticks: {
            color: '#f59e0b',
            callback: v => `${v}°C`
          },
          grid: { drawOnChartArea: false },
          title: { display: true, text: 'Temp (°C)', color: '#f59e0b', font: { size: 11 } }
        }
      } : {})
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Sensor Readings</h3>
        {!loading && hasChartData && (
          <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1">
              <span className="w-3 h-0.5 bg-green-500 inline-block rounded" />
              Moisture: {moistureReadings.length > 0 ? `${moistureReadings[moistureReadings.length - 1]?.value?.toFixed(1) ?? '--'}%` : '--'}
            </span>
            {hasTempData && (
              <span className="flex items-center gap-1">
                <span className="w-3 h-0.5 bg-amber-500 inline-block rounded" />
                Temp: {temperatureReadings[temperatureReadings.length - 1]?.value?.toFixed(1) ?? '--'}°C
              </span>
            )}
          </div>
        )}
      </div>

      {loading && <p className="text-sm text-gray-500 dark:text-gray-400">Loading live sensor chart...</p>}
      {error && !hasChartData && <p className="text-sm text-red-500">Unable to load live sensor chart.</p>}
      {error && hasChartData && <p className="text-sm text-amber-500">Showing cached sensor readings.</p>}

      {!hasTempData && hasChartData && (
        <p className="text-xs text-amber-500 mb-2">
          ⚠ Temperature sensor returning 0 — check sensor calibration or LoRa packet data.
        </p>
      )}

      <div className="h-80">
        {hasChartData ? (
          <Line data={data} options={options} />
        ) : (
          <div className="h-full flex flex-col items-center justify-center gap-2 text-sm text-gray-400 dark:text-gray-500">
            <svg className="w-10 h-10 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span>No Live Sensor Data Available</span>
            <span className="text-xs">Waiting for LoRa packets from field nodes...</span>
          </div>
        )}
      </div>
    </div>
  )
}

const buildLabels = (...groups) => {
  const labels = groups
    .flat()
    .map(reading => formatTime(reading.timestamp))
    .filter(Boolean)
  return [...new Set(labels)]
}

const findValueForLabel = (readings, label) => {
  const reading = readings.find(item => formatTime(item.timestamp) === label)
  return reading?.value ?? null
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default SensorChart
