import React from 'react'
import { Tractor, Play, Pause, Droplets, Gauge, Leaf, Ruler } from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

const DigitalTwin = () => {
  const { isDark } = useDarkMode()
  const { data, loading, error } = useApiData(() => api.getDigitalTwinState(), [], { intervalMs: 10000 })
  const [simulating, setSimulating] = React.useState(false)
  const [simulationError, setSimulationError] = React.useState(null)
  const hasTwinData = Boolean(data?.timestamp)

  const handleSimulation = async () => {
    if (simulating) {
      setSimulating(false)
      return
    }
    try {
      setSimulationError(null)
      await api.runDigitalTwinSimulation({ duration_hours: 24 })
      setSimulating(true)
    } catch (err) {
      setSimulationError(err)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-3">
        <Tractor className="w-8 h-8 text-primary-500" />
        Digital Twin
      </h2>
      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading digital twin state...</p>
      )}
      {error && (
        <p className="text-sm text-red-500">Unable to load digital twin state.</p>
      )}
      {simulationError && (
        <p className="text-sm text-red-500">Unable to start simulation.</p>
      )}
      {!loading && !error && !hasTwinData && (
        <p className="text-sm text-gray-500 dark:text-gray-400">No Live Data Available</p>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className={`rounded-xl p-6 shadow-sm border ${
            isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
          }`}>
            <div className="aspect-video rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 p-6 flex flex-col justify-between">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Live Field State</p>
                  <p className="text-2xl font-bold mt-1">{hasTwinData ? formatPercent(data.soil_moisture_pct) : '--'}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  data?.pump_state === 'on'
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                    : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                }`}>
                  {hasTwinData ? data.pump_state?.toUpperCase() : 'NO DATA'}
                </span>
              </div>
              <div>
                <div className="h-44 rounded-lg overflow-hidden border border-green-300 dark:border-green-700 bg-amber-100 dark:bg-amber-900/30 flex items-end">
                  <div
                    className="w-full bg-green-400/80 dark:bg-green-500/70 transition-all"
                    style={{ height: `${clampPercent(data?.soil_moisture_pct)}%` }}
                  />
                </div>
                <div className="mt-3 flex justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>Dry</span>
                  <span>Moisture Fill</span>
                  <span>Wet</span>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <TwinMetric icon={Droplets} label="Moisture" value={hasTwinData ? formatPercent(data.soil_moisture_pct) : '--'} />
                <TwinMetric icon={Gauge} label="Pump" value={hasTwinData ? data.pump_state?.toUpperCase() : '--'} />
                <TwinMetric icon={Leaf} label="Crop" value={hasTwinData ? data.crop_stage : '--'} />
                <TwinMetric icon={Ruler} label="Area" value={hasTwinData ? formatArea(data.field_area_m2) : '--'} />
              </div>
            </div>
          </div>
        </div>
        <div className="space-y-6">
          <div className={`rounded-xl p-6 shadow-sm border ${
            isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
          }`}>
            <h3 className="text-lg font-semibold mb-4">Simulation</h3>
            <button
              onClick={handleSimulation}
              className={`w-full py-3 rounded-lg font-semibold flex items-center justify-center gap-2 ${
                simulating
                  ? 'bg-orange-500 hover:bg-orange-600 text-white'
                  : 'bg-primary-500 hover:bg-primary-600 text-white'
              }`}
            >
              {simulating ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
              {simulating ? 'Stop Simulation' : 'Start Simulation'}
            </button>
            <div className="mt-4 space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-500 dark:text-gray-400">Soil Moisture</span>
                <span className="font-semibold">{hasTwinData ? formatPercent(data.soil_moisture_pct) : '--'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500 dark:text-gray-400">Crop Stage</span>
                <span className="font-semibold">{hasTwinData ? data.crop_stage : '--'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500 dark:text-gray-400">Pump State</span>
                <span className="font-semibold text-green-500">{hasTwinData ? data.pump_state?.toUpperCase() : '--'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500 dark:text-gray-400">ETo</span>
                <span className="font-semibold">{hasTwinData ? `${Number(data.eto_mm_day || 0).toFixed(2)} mm/day` : '--'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500 dark:text-gray-400">Last Update</span>
                <span className="font-semibold">{hasTwinData ? formatDateTime(data.timestamp) : '--'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const formatPercent = (value) => {
  if (value === null || value === undefined) return '--'
  return `${Number(value).toFixed(1)}%`
}

const clampPercent = (value) => {
  if (value === null || value === undefined) return 0
  return Math.max(0, Math.min(100, Number(value)))
}

const formatArea = (value) => {
  if (value === null || value === undefined) return '--'
  return `${Number(value).toFixed(0)} m2`
}

const formatDateTime = (timestamp) => {
  if (!timestamp) return '--'
  return new Date(timestamp).toLocaleString()
}

const TwinMetric = ({ icon: Icon, label, value }) => (
  <div className="rounded-lg bg-white/70 dark:bg-gray-800/70 p-3 border border-white/70 dark:border-gray-700">
    <Icon className="w-5 h-5 text-primary-500 mb-2" />
    <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
    <p className="text-sm font-semibold truncate">{value}</p>
  </div>
)

export default DigitalTwin
