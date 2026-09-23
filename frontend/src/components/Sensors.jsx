import React from 'react'
import { Thermometer, Droplets, Zap, Activity } from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

const Sensors = () => {
  const { isDark } = useDarkMode()
  const { data, loading, error } = useApiData(() => api.getSensors(40), [], { intervalMs: 5000 })

  const sensors = (data?.sensors || []).reduce((acc, sensor) => {
    // We expect standard ids like soil_moisture_2, temp_2, battery_3, etc.
    const exists = acc.find(s => s.id === sensor.sensor_id)
    if (exists) {
      if (new Date(sensor.timestamp) > new Date(exists.reading.timestamp)) {
        exists.reading = sensor
      }
    } else {
      let name = sensor.sensor_id
      let icon = Activity
      let color = 'gray'

      const parts = sensor.sensor_id.split('_')
      const deviceIdStr = parts[parts.length - 1]
      const isNode1 = deviceIdStr === '2'
      const isNode2 = deviceIdStr === '3'
      const nodeLabel = isNode1 ? 'Node 1' : isNode2 ? 'Node 2' : `Device ${deviceIdStr}`

      if (sensor.sensor_id.startsWith('soil_moisture')) {
        name = `${nodeLabel} Soil Moisture`
        icon = Droplets
        color = 'blue'
      } else if (sensor.sensor_id.startsWith('temp')) {
        name = `${nodeLabel} Temperature`
        icon = Thermometer
        color = 'red'
      } else if (sensor.sensor_id.startsWith('humidity')) {
        name = `${nodeLabel} Humidity`
        color = 'gray'
      } else if (sensor.sensor_id.startsWith('battery')) {
        name = `${nodeLabel} Battery`
        icon = Zap
        color = 'yellow'
      }

      acc.push({
        id: sensor.sensor_id,
        name: name,
        reading: sensor,
        icon: icon,
        color: color
      })
    }
    return acc
  }, [])
  // Sort them sequentially by ID
  sensors.sort((a, b) => a.id.localeCompare(b.id))

  const statusColors = {
    healthy: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    faulty: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Sensors</h2>
      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading live sensor data...</p>
      )}
      {error && (
        <p className="text-sm text-red-500">Unable to load live sensor data.</p>
      )}
      {!loading && !error && (data?.sensors || []).length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">No Live Data Available</p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {sensors.map((sensor) => {
          const Icon = sensor.icon
          const status = sensor.reading?.status || 'warning'
          return (
            <div
              key={sensor.id}
              className={`rounded-xl p-6 shadow-sm border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
                }`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-lg ${sensor.color === 'blue' ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' :
                    sensor.color === 'red' ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                      sensor.color === 'yellow' ? 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400' :
                        'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                  }`}>
                  <Icon className="w-6 h-6" />
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[status] || statusColors.warning}`}>
                  {sensor.reading ? status : 'no data'}
                </span>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400">{sensor.name}</p>
              <p className="text-3xl font-bold mt-1">
                {sensor.reading ? formatReading(sensor.reading) : '--'}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const formatReading = (reading) => {
  if (reading.value === null || reading.value === undefined) return '--'
  const numericValue = Number(reading.value)
  const value = Number.isInteger(numericValue) ? numericValue : numericValue.toFixed(1)
  return `${value}${reading.unit || ''}`
}

export default Sensors
