import React, { useState } from 'react'
import {
  BrainCircuit, Activity, Cpu, Gauge, CheckCircle2,
  XCircle, AlertTriangle, RefreshCw, Layers, Zap,
  BarChart3, Info, ChevronDown, ChevronUp, TrendingUp, CloudRain
} from 'lucide-react'
import { Line } from 'react-chartjs-2'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

// ── Horizon labels ────────────────────────────────────────────────────────────
const HORIZON_LABEL = { 1: '1h', 6: '6h', 12: '12h', 24: '24h', 168: '7d' }

// ── Model status badge ────────────────────────────────────────────────────────
const ModelBadge = ({ model, isDark }) => {
  const { horizon_hours, label, registered, loaded, model_type, version, metrics } = model
  const [expanded, setExpanded] = useState(false)

  const statusColor = loaded
    ? 'text-green-500 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
    : registered
      ? 'text-amber-500 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'
      : 'text-gray-400 bg-gray-50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-700'

  const icon = loaded ? <CheckCircle2 className="w-4 h-4 text-green-500" />
    : registered ? <AlertTriangle className="w-4 h-4 text-amber-500" />
      : <XCircle className="w-4 h-4 text-gray-400" />

  return (
    <div className={`rounded-lg border p-3 ${statusColor} transition-all`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <div>
            <p className="text-sm font-bold">{label}</p>
            <p className="text-xs opacity-70">
              {loaded ? `${model_type} · v${version?.slice(-6) ?? '?'}` : registered ? 'Registered — not loaded' : 'Not registered'}
            </p>
          </div>
        </div>
        {registered && Object.keys(metrics || {}).length > 0 && (
          <button onClick={() => setExpanded(v => !v)} className="p-1 rounded hover:bg-black/10">
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        )}
      </div>
      {expanded && metrics && Object.keys(metrics).length > 0 && (
        <div className="mt-2 pt-2 border-t border-current/20 grid grid-cols-2 gap-1">
          {Object.entries(metrics).slice(0, 6).map(([k, v]) => (
            <div key={k} className="text-xs">
              <span className="opacity-60">{k}: </span>
              <span className="font-mono font-semibold">{typeof v === 'number' ? v.toFixed(4) : String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Feature window progress ───────────────────────────────────────────────────
const WindowProgress = ({ window, isDark }) => {
  if (!window) return null
  const { filled, required, percent, can_predict } = window
  const color = can_predict ? 'bg-green-500' : percent >= 50 ? 'bg-amber-500' : 'bg-blue-500'
  return (
    <div className={`rounded-xl p-5 border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold flex items-center gap-1.5">
          <Layers className="w-4 h-4 text-blue-500" /> Rolling Feature Window
        </h4>
        {can_predict
          ? <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 font-semibold">READY</span>
          : <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 font-semibold">FILLING</span>}
      </div>
      <div className="flex items-end gap-3 mb-2">
        <p className="text-3xl font-bold">{filled}</p>
        <p className="text-lg text-gray-400 mb-0.5">/ {required} readings</p>
      </div>
      <div className="w-full h-3 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden mb-2">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${Math.min(percent, 100)}%` }} />
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        {can_predict
          ? '✅ Window full — AI model can make predictions.'
          : `📡 Collecting LoRa sensor packets... ${required - filled} more needed before AI runs.`}
      </p>
    </div>
  )
}

// ── Sensor feature grid ───────────────────────────────────────────────────────
const FEATURE_ICONS = {
  node_1_soil_moisture: '💧', node_2_soil_moisture: '💧',
  temperature: '🌡', humidity: '💦', rainfall: '🌧️', wind_speed: '💨', solar_radiation: '☀️',
  soil_moisture: '💧', ambient_temperature: '🌡', soil_temperature: '🌡',
  soil_ph: '⚗', nitrogen: '🧪', phosphorus: '🧪', potassium: '🧪',
}
const FEATURE_UNIT = {
  node_1_soil_moisture: '%', node_2_soil_moisture: '%',
  temperature: '°C', humidity: '%', rainfall: 'mm', wind_speed: 'm/s', solar_radiation: 'W/m²',
  soil_moisture: '%', ambient_temperature: '°C', soil_temperature: '°C',
  soil_ph: 'pH', nitrogen: 'mg/kg', phosphorus: 'mg/kg', potassium: 'mg/kg',
}

const FeatureGrid = ({ features, featureOrder, isDark }) => {
  if (!features || !featureOrder) return null
  return (
    <div className={`rounded-xl p-5 border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <h4 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
        <Activity className="w-4 h-4 text-purple-500" /> Live Feature State
        <span className="text-xs font-normal text-gray-400 ml-1">(carried-forward until new packet)</span>
      </h4>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {featureOrder.map(key => {
          const val = features[key]
          const hasData = val !== null && val !== undefined
          return (
            <div key={key}
              className={`rounded-lg p-2.5 ${isDark ? 'bg-gray-700' : 'bg-gray-50'} ${hasData ? '' : 'opacity-50'}`}>
              <p className="text-xs text-gray-400 mb-0.5">{FEATURE_ICONS[key] ?? '📊'} {key.replace(/_/g, ' ')}</p>
              <p className={`text-base font-bold ${hasData ? '' : 'text-gray-400 italic'}`}>
                {hasData ? `${Number(val).toFixed(1)} ${FEATURE_UNIT[key] ?? ''}` : '--'}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Main AIPrediction component ───────────────────────────────────────────────
const AIPrediction = () => {
  const { isDark } = useDarkMode()

  const { data: statusData, loading: statusLoading, error: statusError, refetch: refetchStatus } =
    useApiData(() => api.getAIStatus(), [], { intervalMs: 10000 })

  const { data: predData, loading: predLoading } =
    useApiData(() => api.getAIPredictions(30), [], { intervalMs: 15000 })

  const predictions = (predData?.history || []).slice().reverse()
  const hasPredictions = predictions.some(p => p.data?.predicted_moisture_pct != null)

  // Build chart data from DB prediction history
  const chartData = {
    labels: predictions.map(p => formatTime(p.timestamp)),
    datasets: [{
      label: 'Predicted Soil Moisture (%)',
      data: predictions.map(p => p.data?.predicted_moisture_pct ?? null),
      borderColor: '#6366f1',
      backgroundColor: 'rgba(99,102,241,0.08)',
      borderDash: [5, 4],
      tension: 0.4,
      fill: true,
      pointRadius: 5,
      pointHoverRadius: 7,
    }]
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: isDark ? '#e5e7eb' : '#374151' } },
      tooltip: { callbacks: { label: ctx => `${ctx.parsed.y?.toFixed(1) ?? '--'}%` } }
    },
    scales: {
      x: { ticks: { color: isDark ? '#9ca3af' : '#6b7280', maxTicksLimit: 8 }, grid: { color: isDark ? '#374151' : '#e5e7eb' } },
      y: { ticks: { color: isDark ? '#9ca3af' : '#6b7280', callback: v => `${v}%` }, grid: { color: isDark ? '#374151' : '#e5e7eb' }, min: 0, max: 100 }
    }
  }

  const gridCls = `rounded-xl p-5 shadow-sm border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`
  const models = statusData?.registered_models || []
  const window = statusData?.feature_window
  const lastPred = statusData?.last_prediction
  const irrigationMode = statusData?.irrigation_mode
  const statusOk = statusData?.status_ok

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-3">
          <BrainCircuit className="w-8 h-8 text-indigo-500" />
          AI Prediction Engine
        </h2>
        <div className="flex items-center gap-3">
          {irrigationMode && (
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${irrigationMode === 'AI' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'}`}>
              Mode: {irrigationMode}
            </span>
          )}
          <button onClick={refetchStatus} disabled={statusLoading}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
            title="Refresh AI status">
            <RefreshCw className={`w-4 h-4 ${statusLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Status banner */}
      {!statusLoading && statusData && (
        <div className={`flex items-start gap-3 p-4 rounded-xl border ${statusOk
          ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800 text-green-800 dark:text-green-300'
          : 'bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800 text-amber-800 dark:text-amber-300'}`}>
          {statusOk ? <Zap className="w-5 h-5 shrink-0 mt-0.5" /> : <Info className="w-5 h-5 shrink-0 mt-0.5" />}
          <p className="text-sm">{statusData.status_message}</p>
        </div>
      )}
      {statusError && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300">
          <XCircle className="w-4 h-4 shrink-0" />
          <p className="text-sm">Cannot connect to AI status endpoint. Backend may be starting up.</p>
        </div>
      )}

      {/* Top row: Layout from old UI (Moisture Forecast chart left, Prediction Info right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Moisture Forecast Chart (lg:col-span-2) */}
        <div className="lg:col-span-2">
          <div className={gridCls}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-indigo-500" /> Moisture Forecast
              </h3>
              {hasPredictions && (
                <span className="text-xs font-semibold px-2 py-1 rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                  {predictions.length} records
                </span>
              )}
            </div>
            <div className="h-80">
              {hasPredictions ? (
                <Line data={chartData} options={chartOptions} />
              ) : (
                <div className="h-full flex flex-col items-center justify-center gap-3 text-gray-400 dark:text-gray-500">
                  <BrainCircuit className="w-12 h-12 opacity-30" />
                  <p className="text-sm text-center">
                    No predictions stored yet.<br />
                    <span className="text-xs">Predictions will appear here once the feature window is full.</span>
                  </p>
                  {window && !window.can_predict && (
                    <div className="flex items-center gap-2 text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 px-4 py-2 rounded-full">
                      <Layers className="w-3.5 h-3.5" />
                      {window.filled}/{window.required} readings collected ({window.percent}%)
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Prediction Info (lg:col-span-1) - using the latest from DB */}
        <div className="space-y-6">
          <div className={gridCls}>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-indigo-500" /> Prediction Info
            </h3>

            {lastPred ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center bg-gray-50 dark:bg-gray-800/50 p-2 rounded mb-1">
                  <span className="text-sm font-semibold flex-1">Horizon</span>
                  <span className="text-sm font-semibold w-16 text-right">Node 1</span>
                  <span className="text-sm font-semibold w-16 text-right">Node 2</span>
                </div>
                {['1h', '6h', '12h', '24h', '7d'].map((hz) => {
                  const labels = { '1h': '1 Hour', '6h': '6 Hours', '12h': '12 Hours', '24h': '24 Hours', '7d': '7 Days' }
                  const node1 = lastPred.data?.raw_output?.[hz]?.node_1
                  const node2 = lastPred.data?.raw_output?.[hz]?.node_2
                  return (
                    <div key={hz} className="flex justify-between items-center text-sm border-b border-gray-100 dark:border-gray-700 pb-2">
                      <span className="text-gray-500 dark:text-gray-400 font-medium flex-1">{labels[hz]}</span>
                      <span className="font-mono w-16 text-right">{node1 != null ? `${Number(node1).toFixed(1)}%` : '--'}</span>
                      <span className="font-mono w-16 text-right">{node2 != null ? `${Number(node2).toFixed(1)}%` : '--'}</span>
                    </div>
                  )
                })}
                <div className="grid grid-cols-2 gap-2 mt-4 text-xs bg-indigo-50 dark:bg-indigo-900/10 p-3 rounded-lg border border-indigo-100 dark:border-indigo-800">
                  <div className="flex flex-col">
                    <span className="text-indigo-600 dark:text-indigo-400 mb-1">Water Req (L)</span>
                    <span className="font-bold text-sm">{lastPred.data?.water_requirement_liters != null ? Number(lastPred.data.water_requirement_liters).toFixed(1) : '--'}</span>
                  </div>
                  <div className="flex flex-col text-right">
                    <span className="text-indigo-600 dark:text-indigo-400 mb-1">Confidence</span>
                    <span className="font-bold text-sm text-green-500">{(lastPred.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <div className="flex justify-between items-center text-xs text-gray-400">
                  <span>Model: {lastPred.type ?? '--'}</span>
                  <span>{lastPred.timestamp ? new Date(lastPred.timestamp).toLocaleTimeString() : '--'}</span>
                </div>
              </div>
            ) : (
              <div className="h-40 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400 italic text-center">
                No predictions mapped yet.<br />Data will populate when AI completes an inference cycle.
              </div>
            )}

            <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Active mode:{' '}
                {irrigationMode === 'AI' || irrigationMode === 'ai'
                  ? <span className="font-semibold text-indigo-600 dark:text-indigo-400">AI Mode ✅</span>
                  : irrigationMode === 'EMERGENCY' || irrigationMode === 'emergency'
                    ? <span className="font-semibold text-red-600 dark:text-red-400">Emergency Mode 🚨</span>
                    : <span className="font-semibold text-amber-600 dark:text-amber-400">Rule-Based Mode</span>
                }
                <br />
                <span className="opacity-75">
                  {irrigationMode === 'AI' || irrigationMode === 'ai'
                    ? 'AI model is making irrigation decisions.'
                    : 'Rule-based fallback active — AI window filling.'}
                </span>
              </p>
            </div>
          </div>

          {/* Feature Window Progress fits nicely under Prediction Info */}
          <WindowProgress window={window} isDark={isDark} />

          {/* Weather & Rain Gate widget */}
          {statusData?.rain_forecast && (
            <div className={`rounded-xl p-5 border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
              <h4 className="text-sm font-semibold flex items-center justify-between mb-3">
                <div className="flex items-center gap-1.5">
                  <CloudRain className="w-4 h-4 text-blue-500" /> Weather & Rain Gate
                </div>
                {statusData.rain_forecast.should_irrigate ? (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 font-semibold border border-blue-200 dark:border-blue-800">
                    GATE OPEN
                  </span>
                ) : (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300 font-semibold border border-red-200 dark:border-red-800">
                    GATE BLOCKED
                  </span>
                )}
              </h4>
              <div className="grid grid-cols-2 gap-3 mb-2">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Probable Rain</p>
                  <p className="text-lg font-bold">{Number(statusData.rain_forecast.rain_probability).toFixed(0)}%</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Volume</p>
                  <p className="text-lg font-bold">{Number(statusData.rain_forecast.expected_rainfall_mm).toFixed(1)} mm</p>
                </div>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 border-t border-gray-100 dark:border-gray-700 pt-2">
                <span className="font-semibold text-gray-700 dark:text-gray-300">Impact: </span>
                {statusData.rain_forecast.reason}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Feature state grid */}
      <FeatureGrid
        features={statusData?.current_sensor_state}
        featureOrder={statusData?.feature_order}
        isDark={isDark}
      />

      {/* Model registry */}
      <div className={gridCls}>
        <h3 className="text-base font-semibold mb-4 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-purple-500" /> Registered AI Models
          <span className="text-xs font-normal text-gray-400 ml-1">(all horizons)</span>
        </h3>
        {models.length === 0 ? (
          <p className="text-sm text-gray-400 italic">No models found in registry. Run training to register a model.</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {models.map(m => <ModelBadge key={m.horizon_hours} model={m} isDark={isDark} />)}
          </div>
        )}
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-3">
          Expected input shape: (1, {window?.required ?? 30} timesteps, {statusData?.expected_feature_count ?? 22} features).
          Features: {(statusData?.feature_order || []).join(', ')}.
        </p>
      </div>
    </div>
  )
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default AIPrediction
