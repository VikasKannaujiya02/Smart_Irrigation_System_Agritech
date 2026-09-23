import React, { useState } from 'react'
import { History as HistoryIcon, Calendar, Database } from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

const History = () => {
  const { isDark } = useDarkMode()
  const [tab, setTab] = useState('logs')
  const { data: logData, loading, error } = useApiData(() => api.getLogs(100), [], { intervalMs: 10000 })
  const { data: sensorData } = useApiData(() => api.getSensors(30), [], { intervalMs: 10000 })

  const events = logData?.logs || []
  const sensorsRaw = sensorData?.sensors || []

  const typeColors = {
    DEBUG: 'text-gray-500',
    INFO: 'text-blue-500',
    WARNING: 'text-yellow-500',
    ERROR: 'text-red-500',
    CRITICAL: 'text-red-600'
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h2 className="text-2xl font-bold flex items-center gap-3">
          <HistoryIcon className="w-8 h-8 text-primary-500" />
          System Records
        </h2>
        <div className="flex gap-2">
          <button onClick={() => setTab('logs')} className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${tab === 'logs' ? 'bg-primary-500 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700'}`}>System Logs</button>
          <button onClick={() => setTab('raw')} className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition ${tab === 'raw' ? 'bg-primary-500 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700'}`}><Database className="w-4 h-4" /> Raw CSV / DB Data</button>
        </div>
      </div>

      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading live history...</p>
      )}
      {error && (
        <p className="text-sm text-red-500">Unable to load live history.</p>
      )}
      {!loading && !error && events.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">No Live Data Available</p>
      )}

      {tab === 'logs' ? (
        <div
          className={`rounded-xl shadow-sm border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
            }`}
        >
          <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-[70vh] overflow-y-auto">
            {events.map((event, index) => (
              <div key={`${event.timestamp}-${index}`} className="p-6 flex items-start gap-4">
                <div className={`p-2 rounded-full ${typeColors[event.level] || typeColors.INFO} bg-opacity-10 shrink-0`}>
                  <Calendar className="w-5 h-5" />
                </div>

                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold">{event.module}</h3>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {formatTime(event.timestamp)}
                    </span>
                  </div>

                  <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
                    {event.message}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className={`rounded-xl shadow-sm border overflow-hidden ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <p className="text-sm text-gray-500 dark:text-gray-400">Showing the latest raw data records saved in the backend databases and sync CSVs. This proves the hardware is actively collecting and saving authentic packets.</p>
          </div>
          <div className="overflow-x-auto max-h-[65vh]">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800/80 sticky top-0">
                <tr>
                  <th className="p-4 font-semibold">Timestamp</th>
                  <th className="p-4 font-semibold">Sensor ID</th>
                  <th className="p-4 font-semibold">Logged Value</th>
                  <th className="p-4 font-semibold">Metric</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {sensorsRaw.map((s, i) => (
                  <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-default">
                    <td className="p-4 whitespace-nowrap text-gray-500 dark:text-gray-400">{formatTime(s.timestamp)}</td>
                    <td className="p-4 font-mono text-xs">{s.sensor_id}</td>
                    <td className="p-4 font-bold text-green-600 dark:text-green-400">{Number(s.value).toFixed(2)}</td>
                    <td className="p-4 text-gray-500">{s.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {sensorsRaw.length === 0 && <p className="p-6 text-center text-sm text-gray-500">No raw data currently available.</p>}
          </div>
        </div>
      )}
    </div>
  )
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString()
}

export default History
