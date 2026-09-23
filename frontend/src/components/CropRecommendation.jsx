import React from 'react'
import { Droplets, Leaf, Sprout, Thermometer, CloudRain, FlaskConical } from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

const CropRecommendation = () => {
  const { isDark } = useDarkMode()
  const { data, loading, error } = useApiData(() => api.getCropRecommendation(), [], { intervalMs: 30000 })
  const selected = data?.selected_crop
  const topCrops = data?.top_crops || []
  const hasLiveRecommendation = data?.status === 'live' && selected
  const context = data?.agronomic_context || {}

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-3">
        <Sprout className="w-8 h-8 text-primary-500" />
        Crop Recommendation
      </h2>
      {loading && <p className="text-sm text-gray-500 dark:text-gray-400">Loading live crop recommendation...</p>}
      {error && <p className="text-sm text-red-500">Unable to load live crop recommendation.</p>}
      {!loading && !error && !hasLiveRecommendation && (
        <p className="text-sm text-gray-500 dark:text-gray-400">{data?.message || 'No Live Data Available'}</p>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={`lg:col-span-2 rounded-xl p-6 shadow-sm border ${
          isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Top 5 Crop Matches</h3>
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
              hasLiveRecommendation
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
            }`}>
              {data?.status || 'no_data'}
            </span>
          </div>
          {topCrops.length > 0 ? (
            <div className="space-y-4">
              {topCrops.map((crop, index) => (
                <CropRow key={crop.crop} crop={crop} rank={index + 1} />
              ))}
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
              No Live Data Available
            </div>
          )}
        </div>

        <div className={`rounded-xl p-6 shadow-sm border ${
          isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
          <h3 className="text-lg font-semibold mb-4">Selected Crop</h3>
          {selected ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                  <Leaf className="w-7 h-7 text-primary-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{selected.crop}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{formatPercent(selected.probability)} match</p>
                </div>
              </div>
              <InfoLine label="Water Need" value={formatValue(selected.water_requirement_mm_day, ' mm/day')} />
              <InfoLine label="Weather Adjusted" value={formatValue(selected.weather_adjusted_water_mm_day, ' mm/day')} />
              <InfoLine label="Rainfall 7d" value={formatValue(context.forecast_rainfall_7d_mm, ' mm')} />
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">No Live Data Available</p>
          )}
        </div>
      </div>

      <div className={`rounded-xl p-6 shadow-sm border ${
        isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}>
        <h3 className="text-lg font-semibold mb-4">Live Model Inputs</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {Object.entries(data?.input_features || {}).map(([name, value]) => (
            <div key={name} className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400">{name}</p>
              <p className="text-lg font-semibold">{formatValue(value, '')}</p>
            </div>
          ))}
          {Object.keys(data?.input_features || {}).length === 0 && (
            <div className="col-span-full h-24 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
              No Live Data Available
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ContextCard
          isDark={isDark}
          title="Weather Context"
          items={[
            { icon: Thermometer, label: 'Temperature', value: formatValue(context.current_temperature_c, '°C') },
            { icon: CloudRain, label: 'Rainfall Now', value: formatValue(context.current_rainfall_mm, ' mm') },
            { icon: Droplets, label: '7d Rainfall', value: formatValue(context.forecast_rainfall_7d_mm, ' mm') },
          ]}
        />
        <ContextCard
          isDark={isDark}
          title="Selected Crop Profile"
          items={profileItems(selected?.ideal_profile)}
        />
      </div>
    </div>
  )
}

const CropRow = ({ crop, rank }) => (
  <div>
    <div className="flex items-center justify-between mb-2">
      <p className="font-semibold">
        <span className="text-sm text-gray-500 dark:text-gray-400 mr-2">#{rank}</span>
        {crop.crop}
      </p>
      <p className="text-sm font-semibold text-primary-500">{formatPercent(crop.probability)}</p>
    </div>
    <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
      <div className="h-full bg-primary-500" style={{ width: `${Math.min(crop.probability, 100)}%` }} />
    </div>
  </div>
)

const ContextCard = ({ isDark, title, items }) => (
  <div className={`rounded-xl p-6 shadow-sm border ${
    isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
  }`}>
    <h3 className="text-lg font-semibold mb-4">{title}</h3>
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {items.map(({ icon: Icon, label, value }) => (
        <div key={label} className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
          <Icon className="w-5 h-5 text-primary-500 mb-2" />
          <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
          <p className="text-sm font-semibold">{value}</p>
        </div>
      ))}
    </div>
  </div>
)

const InfoLine = ({ label, value }) => (
  <div className="flex items-center justify-between text-sm">
    <span className="text-gray-500 dark:text-gray-400">{label}</span>
    <span className="font-semibold">{value}</span>
  </div>
)

const formatPercent = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return `${Number(value).toFixed(1)}%`
}

const formatValue = (value, unit) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return `${Number(value).toFixed(1)}${unit}`
}

const profileItems = (profile = {}) => {
  const entries = Object.entries(profile).slice(0, 3)
  if (entries.length === 0) {
    return [{ icon: FlaskConical, label: 'Profile', value: '--' }]
  }
  return entries.map(([label, value]) => ({
    icon: FlaskConical,
    label,
    value: formatValue(value, '')
  }))
}

export default CropRecommendation
