import React from 'react'
import { Droplets, Thermometer, Gauge, Settings } from 'lucide-react'
import SensorChart from './SensorChart'
import PumpStatus from './PumpStatus'
import WeatherWidget from './WeatherWidget'
import { api } from '../api'
import useApiData from '../hooks/useApiData'
import { useTranslation } from 'react-i18next'

const Dashboard = () => {
  const { t } = useTranslation()
  const { data: sensorsData, loading: sensorsLoading, error: sensorsError } = useApiData(() => api.getSensors(40), [], { intervalMs: 5000 })
  const { data: pumpData, loading: pumpLoading, error: pumpError } = useApiData(() => api.getPump(), [], { intervalMs: 5000 })
  const { data: configData, loading: configLoading, error: configError } = useApiData(() => api.getConfig(), [], { intervalMs: 30000 })

  const latestSoilN1 = getLatestSensorValue(sensorsData?.sensors, 'soil_moisture_2') // Device 2 = node 1
  const latestSoilN2 = getLatestSensorValue(sensorsData?.sensors, 'soil_moisture_3') // Device 3 = node 2
  const latestTemp = getLatestSensorValue(sensorsData?.sensors, 'temp_')
  const hasPumpData = Boolean(pumpData?.last_start || pumpData?.last_stop || pumpData?.runtime_seconds || pumpData?.total_runtime_today || pumpData?.cycles_today)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          icon={Droplets}
          title={t('dashboard.node1Moisture')}
          value={formatApiValue(latestSoilN1?.value, latestSoilN1?.unit)}
          loading={sensorsLoading}
          error={sensorsError}
          color="blue"
          t={t}
        />
        <StatCard
          icon={Droplets}
          title={t('dashboard.node2Moisture')}
          value={formatApiValue(latestSoilN2?.value, latestSoilN2?.unit)}
          loading={sensorsLoading}
          error={sensorsError}
          color="blue"
          t={t}
        />
        <StatCard
          icon={Thermometer}
          title={t('dashboard.temperature')}
          value={formatApiValue(latestTemp?.value, latestTemp?.unit)}
          loading={sensorsLoading}
          error={sensorsError}
          color="red"
          t={t}
        />
        <StatCard
          icon={Gauge}
          title={t('dashboard.pumpRuntime')}
          value={hasPumpData ? formatRuntime(pumpData.runtime_seconds) : null}
          loading={pumpLoading}
          error={pumpError}
          color="green"
          t={t}
        />
        <StatCard
          icon={Settings}
          title={t('dashboard.irrigationMode')}
          value={formatMode(configData?.irrigation_mode, t)}
          loading={configLoading}
          error={configError}
          color="purple"
          t={t}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SensorChart />
        </div>
        <div className="space-y-6">
          <PumpStatus />
          <WeatherWidget />
        </div>
      </div>
    </div>
  )
}

const StatCard = ({ icon: Icon, title, value, loading, error, color, t }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    red: 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    green: 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    purple: 'bg-purple-50 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400'
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
      <p className="text-3xl font-bold mt-1">
        {loading ? t('loading') : error ? t('error') : value || '--'}
      </p>
      {!loading && !error && !value && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">{t('dashboard.noLiveData')}</p>
      )}
    </div>
  )
}

const getLatestSensorValue = (sensors = [], prefix) => {
  return sensors
    .filter((sensor) => sensor.sensor_id.startsWith(prefix))
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0]
}

const formatApiValue = (value, unit = '') => {
  if (value === null || value === undefined) return null
  const numericValue = Number(value)
  const displayValue = Number.isInteger(numericValue) ? numericValue : numericValue.toFixed(1)
  const suffix = unit === 'deg C' ? ' °C' : unit
  return `${displayValue}${suffix}`
}

const formatRuntime = (seconds = 0) => {
  const totalSeconds = Number(seconds || 0)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const secs = Math.floor(totalSeconds % 60)
  if (hours > 0) return `${hours}h ${minutes}m`
  if (minutes > 0) return `${minutes}m ${secs}s`
  return `${secs}s`
}

const formatMode = (mode, t) => {
  if (!mode) return null
  const labels = {
    ai: t('dashboard.aiDriven'),
    rules: t('dashboard.ruleBased'),
    manual: t('dashboard.manual')
  }
  return labels[String(mode).toLowerCase()] || String(mode)
}

export default Dashboard
