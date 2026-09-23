import React from 'react'
import { BarChart3 } from 'lucide-react'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

const Analytics = () => {
  const { isDark } = useDarkMode()
  const { data: summary, loading: summaryLoading, error: summaryError } = useApiData(() => api.getAnalyticsSummary(30), [], { intervalMs: 30000 })
  const { data: full, loading: fullLoading, error: fullError } = useApiData(() => api.getAnalyticsFull(), [], { intervalMs: 30000 })
  const dailyUsage = full?.water_consumption?.daily_usage || {}
  const dailyEntries = Object.entries(dailyUsage)
  const peakUsage = dailyEntries.reduce((peak, entry) => !peak || entry[1] > peak[1] ? entry : peak, null)
  const hasSummaryData = Boolean(
    summary?.total_irrigation_events ||
    summary?.total_water_used_liters ||
    summary?.avg_soil_moisture_pct ||
    summary?.ai_predictions_made
  )

  const chartData = {
    labels: dailyEntries.map(([day]) => day),
    datasets: [
      {
        label: 'Water Used (L)',
        data: dailyEntries.map(([, value]) => value),
        backgroundColor: '#10b981'
      }
    ]
  }

  const chartOptions = {
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
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-3">
        <BarChart3 className="w-8 h-8 text-primary-500" />
        Analytics
      </h2>
      {(summaryLoading || fullLoading) && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading live analytics...</p>
      )}
      {(summaryError || fullError) && (
        <p className="text-sm text-red-500">Unable to load live analytics.</p>
      )}
      {!summaryLoading && !fullLoading && !summaryError && !fullError && !hasSummaryData && dailyEntries.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">No Live Data Available</p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <StatCard title="Total Irrigation" value={hasSummaryData ? formatCount(summary?.total_irrigation_events, 'Events') : null} color="blue" />
        <StatCard title="Water Used" value={hasSummaryData ? formatValue(summary?.total_water_used_liters, ' L') : null} color="green" />
        <StatCard title="Avg Moisture" value={hasSummaryData ? formatValue(summary?.avg_soil_moisture_pct, '%') : null} color="yellow" />
        <StatCard title="AI Predictions" value={hasSummaryData ? formatCount(summary?.ai_predictions_made) : null} color="purple" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className={`rounded-xl p-6 shadow-sm border ${
            isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
          }`}>
            <h3 className="text-lg font-semibold mb-4">Weekly Water Usage</h3>
            {!fullLoading && !fullError && dailyEntries.length === 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400">No Live Data Available</p>
            )}
            <div className="h-80">
              <Bar data={chartData} options={chartOptions} />
            </div>
          </div>
        </div>
        <div className={`rounded-xl p-6 shadow-sm border ${
          isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
          <h3 className="text-lg font-semibold mb-4">Summary</h3>
          <div className="space-y-4">
            <div className="p-3 bg-green-50 dark:bg-green-900/30 rounded-lg">
              <p className="text-sm text-gray-500 dark:text-gray-400">Best Day</p>
              <p className="text-xl font-bold">{peakUsage ? peakUsage[0] : '--'}</p>
            </div>
            <div className="p-3 bg-yellow-50 dark:bg-yellow-900/30 rounded-lg">
              <p className="text-sm text-gray-500 dark:text-gray-400">Peak Usage</p>
              <p className="text-xl font-bold">{peakUsage ? `${Number(peakUsage[1]).toFixed(1)} L` : '--'}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const StatCard = ({ title, value, color }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    yellow: 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
    purple: 'bg-purple-50 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400'
  }
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
      <p className="text-2xl font-bold mt-1">{value || '--'}</p>
      {!value && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">No Live Data Available</p>
      )}
    </div>
  )
}

const formatValue = (value, unit) => {
  if (value === null || value === undefined) return null
  return `${Number(value).toFixed(1)}${unit}`
}

const formatCount = (value, suffix = '') => {
  if (value === null || value === undefined) return null
  return `${Number(value)}${suffix ? ` ${suffix}` : ''}`
}

export default Analytics
