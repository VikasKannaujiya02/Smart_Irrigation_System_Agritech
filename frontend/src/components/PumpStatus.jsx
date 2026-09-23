import React, { useState } from 'react'
import { Gauge, Power } from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

const PumpStatus = () => {
  const { isDark } = useDarkMode()
  const { data, loading, error, refetch } = useApiData(() => api.getPump(), [], { intervalMs: 5000 })
  const [controlError, setControlError] = useState(null)
  const [controlLoading, setControlLoading] = useState(false)

  const hasPumpData = Boolean(data?.last_start || data?.last_stop || data?.runtime_seconds || data?.total_runtime_today || data?.cycles_today)
  const pumpOn = data?.state === 'on'
  const desiredAction = pumpOn ? 'off' : 'on'

  const handlePumpControl = async () => {
    if (!hasPumpData || controlLoading) return
    try {
      setControlError(null)
      setControlLoading(true)
      await api.controlPump(desiredAction)
      await refetch()
      setTimeout(refetch, 2000)
    } catch (err) {
      setControlError(err)
    } finally {
      setControlLoading(false)
    }
  }

  return (
    <div className={`rounded-xl p-6 shadow-sm border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Pump Status</h3>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${pumpOn ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
          : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
          }`}>
          {loading ? '...' : hasPumpData ? data.state.toUpperCase() : 'NO DATA'}
        </span>
      </div>
      {error && (
        <p className="text-sm text-red-500 mb-4">Unable to load live pump status.</p>
      )}
      {!loading && !error && !hasPumpData && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">No Live Data Available</p>
      )}
      <div className="flex items-center gap-4 mb-4">
        <div className={`p-4 rounded-full ${pumpOn ? 'bg-green-500/20 text-green-500' : 'bg-gray-500/20 text-gray-500'
          }`}>
          <Gauge className="w-10 h-10" />
        </div>
        <div className="flex-1">
          <p className="text-2xl font-bold">
            {formatFlowRate(data?.current_flow_rate, pumpOn)}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Flow Rate</p>
        </div>
      </div>
      {controlError && (
        <p className="text-sm text-red-500 mb-3">{formatControlError(controlError)}</p>
      )}
      <button
        onClick={handlePumpControl}
        disabled={!hasPumpData || controlLoading}
        className={`w-full py-3 rounded-lg font-semibold flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed ${pumpOn
          ? 'bg-red-500 hover:bg-red-600 text-white'
          : 'bg-primary-500 hover:bg-primary-600 text-white'
          }`}
      >
        <Power className="w-5 h-5" />
        {controlLoading ? `Switching ${desiredAction.toUpperCase()}...` : pumpOn ? 'Switch OFF' : 'Switch ON'}
      </button>
    </div>
  )
}

const formatFlowRate = (flowRate, pumpOn) => {
  if (flowRate != null) return `${Number(flowRate).toFixed(1)} L/s`
  return pumpOn ? '0.05 L/s' : '0.0 L/s'
}

const formatControlError = (error) => {
  const detail = error?.detail?.detail || error?.detail?.message || error?.message
  return detail ? `Pump control failed: ${detail}` : 'Pump control request failed.'
}

export default PumpStatus
