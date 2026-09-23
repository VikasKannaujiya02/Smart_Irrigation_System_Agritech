import React, { useState } from 'react'
import { AlertTriangle, CheckCircle, Info } from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

const Alerts = () => {
  const { isDark } = useDarkMode()
  const { data, loading, error, refetch } = useApiData(() => api.getAlerts(50), [], { intervalMs: 10000 })
  const [resolveError, setResolveError] = useState(null)
  const alerts = [...(data?.active || []), ...(data?.resolved || [])].filter((alert) => {
    const message = alert.message || ''
    return !(
      alert.type === 'SYSTEM_ERROR' &&
      message.startsWith('Packet processing failed: Packet')
    )
  })

  const resolveAlert = async (id) => {
    try {
      setResolveError(null)
      await api.resolveAlert(id)
      await refetch()
    } catch (err) {
      setResolveError(err)
    }
  }

  const alertIcons = {
    warning: AlertTriangle,
    critical: AlertTriangle,
    info: Info,
    success: CheckCircle
  }

  const alertColors = {
    warning: 'text-yellow-500 bg-yellow-50 dark:bg-yellow-900/30',
    critical: 'text-red-500 bg-red-50 dark:bg-red-900/30',
    info: 'text-blue-500 bg-blue-50 dark:bg-blue-900/30',
    success: 'text-green-500 bg-green-50 dark:bg-green-900/30'
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-3">
        <AlertTriangle className="w-8 h-8 text-primary-500" />
        Alerts
      </h2>
      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading live alerts...</p>
      )}
      {error && (
        <p className="text-sm text-red-500">Unable to load live alerts.</p>
      )}
      {resolveError && (
        <p className="text-sm text-red-500">Unable to resolve alert.</p>
      )}
      {!loading && !error && alerts.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">No Live Data Available</p>
      )}
      <div className="space-y-4">
        {alerts.map((alert) => {
          const level = alert.level || 'info'
          const Icon = alert.resolved ? CheckCircle : alertIcons[level] || Info
          const title = alert.type || level
          return (
            <div
              key={alert.alert_id}
              className={`rounded-xl p-6 shadow-sm border flex items-start gap-4 ${
                isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              } ${alert.resolved ? 'opacity-60' : ''}`}
            >
              <div className={`p-3 rounded-lg ${alertColors[level] || alertColors.info}`}>
                <Icon className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-semibold">{title}</h3>
                  <span className="text-sm text-gray-500 dark:text-gray-400">{formatTime(alert.timestamp)}</span>
                </div>
                <p className="text-gray-500 dark:text-gray-400">{alert.message}</p>
                {!alert.resolved && (
                  <button
                    onClick={() => resolveAlert(alert.alert_id)}
                    className="mt-3 text-primary-500 hover:text-primary-600 font-medium text-sm"
                  >
                    Mark as Resolved
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString()
}

export default Alerts
