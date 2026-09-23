import React, { useEffect, useState } from 'react'
import { Settings, Save } from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

const Config = () => {
  const { isDark } = useDarkMode()
  const { data, loading, error } = useApiData(() => api.getConfig())
  const [config, setConfig] = useState({
    irrigationMode: '',
    emergencyMoistureThreshold: '',
    aiConfidenceThreshold: '',
    maxPumpRuntimeSeconds: '',
    rainDelayHours: '',
    weatherLatitude: '',
    weatherLongitude: ''
  })
  const [saveError, setSaveError] = useState(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saving, setSaving] = useState(false)

  const confidenceToPercent = (value) => {
    const numericValue = Number(value)
    if (!Number.isFinite(numericValue)) return ''
    return numericValue <= 1 ? numericValue * 100 : numericValue
  }

  const confidenceToFraction = (value) => {
    const numericValue = Number(value)
    if (!Number.isFinite(numericValue)) return 0.7
    return numericValue > 1 ? numericValue / 100 : numericValue
  }

  const getErrorMessage = (err) => {
    const detail = err?.detail?.detail ?? err?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map(item => item.msg || JSON.stringify(item)).join(', ')
    return err?.message || 'Unable to save configuration.'
  }

  useEffect(() => {
    if (!data) return
    setConfig({
      irrigationMode: data.irrigation_mode ?? '',
      emergencyMoistureThreshold: data.emergency_moisture_threshold ?? '',
      aiConfidenceThreshold: confidenceToPercent(data.ai_confidence_threshold),
      maxPumpRuntimeSeconds: data.max_pump_runtime_seconds ?? '',
      rainDelayHours: data.rain_delay_hours ?? '',
      weatherLatitude: data.weather_latitude ?? '',
      weatherLongitude: data.weather_longitude ?? ''
    })
  }, [data])

  const handleChange = (key, value) => {
    setSaveSuccess(false)
    setConfig(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    try {
      setSaveError(null)
      setSaveSuccess(false)
      setSaving(true)
      await api.updateConfig({
        irrigation_mode: config.irrigationMode,
        emergency_moisture_threshold: Number(config.emergencyMoistureThreshold),
        ai_confidence_threshold: confidenceToFraction(config.aiConfidenceThreshold),
        max_pump_runtime_seconds: Number(config.maxPumpRuntimeSeconds),
        rain_delay_hours: Number(config.rainDelayHours),
        weather_latitude: Number(config.weatherLatitude),
        weather_longitude: Number(config.weatherLongitude)
      })
      setSaveSuccess(true)
    } catch (err) {
      setSaveError(err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-3">
        <Settings className="w-8 h-8 text-primary-500" />
        Configuration
      </h2>
      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading configuration...</p>
      )}
      {error && (
        <p className="text-sm text-red-500">Unable to load configuration.</p>
      )}
      {saveError && (
        <p className="text-sm text-red-500">Unable to save configuration: {getErrorMessage(saveError)}</p>
      )}
      {saveSuccess && (
        <p className="text-sm text-green-500">Configuration saved.</p>
      )}
      <div className={`rounded-xl p-6 shadow-sm border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">Irrigation Mode</label>
            <select
              value={config.irrigationMode}
              onChange={(e) => handleChange('irrigationMode', e.target.value)}
              className="w-full p-3 rounded-lg border bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600"
            >
              <option value="">No Live Data Available</option>
              <option value="ai">AI Driven</option>
              <option value="rules">Rule Based</option>
              <option value="manual">Manual</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Emergency Moisture Threshold (%)</label>
            <input
              type="number"
              value={config.emergencyMoistureThreshold}
              onChange={(e) => handleChange('emergencyMoistureThreshold', e.target.value)}
              className="w-full p-3 rounded-lg border bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">AI Confidence Threshold (%)</label>
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={config.aiConfidenceThreshold}
              onChange={(e) => handleChange('aiConfidenceThreshold', e.target.value)}
              className="w-full p-3 rounded-lg border bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Max Pump Runtime (seconds)</label>
            <input
              type="number"
              value={config.maxPumpRuntimeSeconds}
              onChange={(e) => handleChange('maxPumpRuntimeSeconds', e.target.value)}
              className="w-full p-3 rounded-lg border bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Rain Delay (hours)</label>
            <input
              type="number"
              value={config.rainDelayHours}
              onChange={(e) => handleChange('rainDelayHours', e.target.value)}
              className="w-full p-3 rounded-lg border bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Weather Latitude</label>
              <input
                type="number" step="any"
                value={config.weatherLatitude}
                onChange={(e) => handleChange('weatherLatitude', e.target.value)}
                className="w-full p-3 rounded-lg border bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Weather Longitude</label>
              <input
                type="number" step="any"
                value={config.weatherLongitude}
                onChange={(e) => handleChange('weatherLongitude', e.target.value)}
                className="w-full p-3 rounded-lg border bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600"
              />
            </div>
          </div>
          <button
            onClick={handleSave}
            disabled={loading || saving || !config.irrigationMode}
            className="w-full py-3 rounded-lg font-semibold bg-primary-500 hover:bg-primary-600 text-white flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <Save className="w-5 h-5" />
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default Config
