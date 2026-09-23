import React from 'react'
import { Droplets, TrendingUp, Trophy } from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

const WaterSaving = () => {
  const { isDark } = useDarkMode()
  const { data, loading, error } = useApiData(() => api.getWaterSaving(), [], { intervalMs: 30000 })
  const hasWaterData = Boolean(data?.last_updated)

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-3">
        <Droplets className="w-8 h-8 text-primary-500" />
        Water Saving
      </h2>
      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading live water saving data...</p>
      )}
      {error && (
        <p className="text-sm text-red-500">Unable to load live water saving data.</p>
      )}
      {!loading && !error && !hasWaterData && (
        <p className="text-sm text-gray-500 dark:text-gray-400">No Live Data Available</p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <StatCard
          title="Current Month Saved"
          value={hasWaterData ? formatLiters(data.current_month_saved_liters) : null}
          icon={TrendingUp}
          color="green"
          subtitle={hasWaterData ? `${formatPercent(data.current_month_savings_pct)} saved` : ''}
        />
        <StatCard
          title="Total Saved"
          value={hasWaterData ? formatLiters(data.total_saved_liters) : null}
          icon={Trophy}
          color="yellow"
          subtitle={hasWaterData ? 'All time' : ''}
        />
        <StatCard
          title="Daily Avg Saving"
          value={hasWaterData ? formatPercent(data.daily_avg_savings_pct) : null}
          icon={Droplets}
          color="blue"
          subtitle={hasWaterData ? 'vs baseline' : ''}
        />
      </div>
      <div className={`rounded-xl p-8 shadow-sm border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
        <h3 className="text-xl font-semibold mb-4">Saving Progress</h3>
        <div className="mb-4">
          <div className="flex justify-between mb-2">
            <span className="text-gray-500 dark:text-gray-400">Current Month</span>
            <span className="font-semibold">{hasWaterData ? formatPercent(data.current_month_savings_pct) : '--'}</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4">
            <div className="bg-primary-500 h-4 rounded-full" style={{ width: hasWaterData ? `${clampPercent(data.current_month_savings_pct)}%` : '0%' }} />
          </div>
        </div>
      </div>
    </div>
  )
}

const StatCard = ({ title, value, icon: Icon, color, subtitle }) => {
  const colorClasses = {
    green: 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    yellow: 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
    blue: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
  }
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <div className={`p-3 rounded-lg inline-block mb-4 ${colorClasses[color]}`}>
        <Icon className="w-6 h-6" />
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
      <p className="text-3xl font-bold mt-1">{value || '--'}</p>
      {subtitle && <p className="text-sm text-green-500 mt-2">{subtitle}</p>}
    </div>
  )
}

const formatLiters = (value) => {
  if (value === null || value === undefined) return null
  return `${Number(value).toFixed(1)} L`
}

const formatPercent = (value) => {
  if (value === null || value === undefined) return '--'
  return `${Number(value).toFixed(1)}%`
}

const clampPercent = (value) => Math.max(0, Math.min(100, Number(value || 0)))

export default WaterSaving
