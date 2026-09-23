import React from 'react'
import { Cloud, CloudRain, Droplets, Gauge, Umbrella, Wind } from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

const WeatherWidget = () => {
  const { isDark } = useDarkMode()
  const { data, loading, error } = useApiData(() => api.getWeather(), [], { intervalMs: 30000 })
  const forecast = data?.forecast || []
  const hasWeatherData = Boolean(data?.current?.timestamp || forecast.length)
  const current = data?.current || null
  const regionalWetness = data?.regional_wetness || null

  return (
    <div className={`rounded-xl p-6 shadow-sm border ${
      isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
    }`}>
      <h3 className="text-lg font-semibold mb-4">Weather</h3>
      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Loading live weather data...</p>
      )}
      {error && (
        <p className="text-sm text-red-500 mb-4">Unable to load live weather data.</p>
      )}
      {!loading && !error && !hasWeatherData && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">No Live Data Available</p>
      )}
      <div className="flex items-center gap-6 mb-4">
        <div className="text-4xl">
          {(current?.rainfall_mm || 0) > 0 ? (
            <CloudRain className="w-16 h-16 text-blue-500" />
          ) : (
            <Cloud className="w-16 h-16 text-gray-500" />
          )}
        </div>
        <div className="flex-1">
          <p className="text-3xl font-bold">{formatValue(current?.temperature_c, '°C')}</p>
          <p className="text-gray-500 dark:text-gray-400">
            {current ? formatRainfall(current.rainfall_mm) : 'No live weather'}
          </p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Metric icon={Wind} label="Wind Speed" value={formatValue(current?.wind_speed_mps, ' m/s')} iconColor="text-blue-500" />
        <Metric icon={Cloud} label="Humidity" value={formatValue(current?.humidity_pct, '%')} iconColor="text-gray-500" />
        <Metric icon={Gauge} label="Pressure" value={formatValue(current?.pressure_hpa, ' hPa')} iconColor="text-primary-500" />
        <Metric icon={Cloud} label="Cloud Cover" value={formatValue(current?.cloud_cover_pct, '%')} iconColor="text-gray-500" />
        <Metric icon={Droplets} label="Surface Wetness" value={formatWetness(regionalWetness?.gwettop_surface_wetness)} iconColor="text-emerald-500" />
        <Metric icon={Droplets} label="Root Zone Wetness" value={formatWetness(regionalWetness?.gwetroot_zone_wetness)} iconColor="text-teal-500" />
      </div>
      {regionalWetness?.city && (
        <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
          NASA POWER wetness: {regionalWetness.city}
          {regionalWetness.predicted_for_date ? `, ${regionalWetness.predicted_for_date}` : ''}
        </p>
      )}
      {forecast.length > 0 && (
        <div className="mt-5">
          <h4 className="text-sm font-semibold mb-3 text-gray-700 dark:text-gray-200">7 Day Forecast</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-7 gap-3">
            {forecast.slice(0, 7).map((item) => (
              <div
                key={item.date || item.timestamp || item.hours_ahead}
                className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-300">
                    {formatForecastDate(item.date || item.timestamp)}
                  </span>
                  {(item.rain_expected || (item.rainfall_mm || 0) > 0) ? (
                    <CloudRain className="w-5 h-5 text-blue-500" />
                  ) : (
                    <Cloud className="w-5 h-5 text-gray-500" />
                  )}
                </div>
                <p className="text-lg font-bold">{formatValue(item.temperature_c, '°C')}</p>
                <div className="mt-2 space-y-1 text-xs text-gray-500 dark:text-gray-300">
                  <p className="flex items-center gap-1">
                    <Umbrella className="w-3 h-3" />
                    {formatValue(item.rain_probability_pct, '%')} rain
                  </p>
                  <p>{formatRainfall(item.rainfall_mm)}</p>
                  <p>{formatValue(item.humidity_pct, '%')} humidity</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const Metric = ({ icon: Icon, label, value, iconColor }) => (
  <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
    <Icon className={`w-6 h-6 mx-auto mb-1 ${iconColor}`} />
    <p className="text-lg font-semibold">{value}</p>
    <p className="text-xs text-gray-500">{label}</p>
  </div>
)

const formatValue = (value, unit) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return `${Number(value).toFixed(1)}${unit}`
}

const formatRainfall = (rainfall) => {
  if (rainfall === null || rainfall === undefined) return 'Rainfall unavailable'
  return `${Number(rainfall).toFixed(1)} mm rainfall`
}

const formatWetness = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return Number(value).toFixed(3)
}

const formatForecastDate = (value) => {
  if (!value) return '--'
  return new Date(value).toLocaleDateString([], { weekday: 'short', day: 'numeric' })
}

export default WeatherWidget
