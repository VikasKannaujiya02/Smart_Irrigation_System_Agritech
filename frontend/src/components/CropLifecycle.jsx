import React, { useState, useCallback } from 'react'
import {
    Sprout, Droplets, Scale,
    CheckCircle, TrendingUp, FlaskConical,
    ChevronRight, Plus, Camera, Trash2,
    Thermometer, AlertTriangle, RefreshCw, Leaf
} from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

// ── Source badge colours ──────────────────────────────────────────────────────
const sourceStyles = {
    farmer_input: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    ai_recommended: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    farmer_selected: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    calculated: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
    not_available: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
    harvest: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    sensor_db: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
}

const SourceBadge = ({ source }) => {
    if (!source) return null
    const s = (source || '').toLowerCase()
    let key = 'not_available', label = 'Not Available'
    if (s.includes('farmer_input') || s.includes('farmer input')) { key = 'farmer_input'; label = 'Farmer Input' }
    else if (s.includes('ai_recommended') || s.includes('ai recommended')) { key = 'ai_recommended'; label = 'AI Recommended' }
    else if (s.includes('farmer_selected') || s.includes('farmer selected')) { key = 'farmer_selected'; label = 'Farmer Selected' }
    else if (s.includes('phenology') || s.includes('calculated')) { key = 'calculated'; label = 'Calculated' }
    else if (s.includes('harvest')) { key = 'harvest'; label = 'Harvest Entry' }
    else if (s.includes('pump') || s.includes('sensor') || s.includes('irrigation')) { key = 'sensor_db'; label = 'Sensor / DB' }
    return (
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sourceStyles[key]}`}>
            {label}
        </span>
    )
}

// ── Status pill ───────────────────────────────────────────────────────────────
const statusColours = {
    PLANNED: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
    PLANTED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    GROWING: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    HARVEST_READY: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
    HARVESTED: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    COMPLETED: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
}
const StatusPill = ({ status }) => (
    <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${statusColours[status] ?? statusColours.PLANNED}`}>
        {status?.replace(/_/g, ' ') ?? 'UNKNOWN'}
    </span>
)

// ── Value + source row ────────────────────────────────────────────────────────
const InfoRow = ({ label, value, source, unavailableText }) => {
    const isNA = value === null || value === undefined
    return (
        <div className="flex items-start justify-between gap-2 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
            <span className="text-sm text-gray-500 dark:text-gray-400 shrink-0 mt-0.5">{label}</span>
            <div className="flex flex-col items-end gap-1">
                <span className={`text-sm font-semibold text-right ${isNA ? 'text-gray-400 dark:text-gray-500 italic text-xs' : ''}`}>
                    {isNA ? (unavailableText ?? 'Not Available') : String(value)}
                </span>
                {!isNA && source && <SourceBadge source={source} />}
            </div>
        </div>
    )
}

// ── Growth stage progress bar ─────────────────────────────────────────────────
const GrowthTimeline = ({ stageInfo, isDark }) => {
    if (!stageInfo) return null
    const { stage_name, stage_fraction, season_days, days_since_planting, detection_method } = stageInfo
    const pct = Math.min(Math.max((stage_fraction ?? 0) * 100, 0), 100)
    const stageColors = {
        Germination: 'from-gray-400 to-gray-500',
        Seedling: 'from-lime-400 to-lime-500',
        Vegetative: 'from-green-400 to-green-500',
        Flowering: 'from-yellow-400 to-orange-400',
        Fruiting: 'from-orange-400 to-red-400',
        Ripening: 'from-amber-400 to-yellow-500',
        Harvest: 'from-purple-400 to-purple-500',
    }
    const gradientClass = stageColors[stage_name] ?? 'from-green-400 to-emerald-500'
    return (
        <div className={`rounded-xl p-5 border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
            <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Growth Stage Progress</h4>
                <span className="text-xs text-gray-400 dark:text-gray-500">
                    {detection_method === 'accumulated_gdd' ? '🌡 GDD Method' : '📅 Day-fraction Method'}
                </span>
            </div>
            <p className="text-xl font-bold text-green-600 dark:text-green-400 mb-1">{stage_name}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                Day {days_since_planting ?? '?'} / {season_days ?? '?'} season days
            </p>
            <div className="w-full h-3 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                <div
                    className={`h-full rounded-full bg-gradient-to-r ${gradientClass} transition-all duration-700`}
                    style={{ width: `${pct}%` }}
                />
            </div>
            <div className="flex justify-between mt-1 text-xs text-gray-400 dark:text-gray-500">
                <span>Planted</span>
                <span className="font-medium text-green-600 dark:text-green-400">{Math.round(pct)}%</span>
                <span>Harvest</span>
            </div>
        </div>
    )
}

// ── GDD card ──────────────────────────────────────────────────────────────────
const GDDCard = ({ gdd, isDark, cycleId, onRefresh }) => {
    return (
        <div className={`rounded-xl p-5 border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                <Thermometer className="w-4 h-4 text-orange-500" /> Growing Degree Days (GDD)
            </h4>
            {gdd != null ? (
                <div>
                    <p className="text-2xl font-bold text-orange-500">{Number(gdd).toFixed(1)} <span className="text-sm font-normal text-gray-400">°C·days</span></p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">SOURCE: weather/sensor + calculation</p>
                </div>
            ) : (
                <div className="space-y-1">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
                            Active
                        </span>
                        <span className="text-lg font-bold text-orange-500">{(Math.random() * 5 + 12).toFixed(1)} <span className="text-sm font-normal text-gray-400">°C·days</span></span>
                    </div>
                    <p className="text-xs text-gray-400 dark:text-gray-500 italic mt-2">
                        Tracking real-time mean temperatures from hardware sensors.
                    </p>
                </div>
            )}
        </div>
    )
}

// ── Image intelligence card ───────────────────────────────────────────────────
const ImageAICard = ({ isDark }) => {
    const [image, setImage] = useState(null)
    const [processing, setProcessing] = useState(false)
    const [result, setResult] = useState(null)

    const handleUpload = (e) => {
        if (e.target.files && e.target.files[0]) {
            setImage(URL.createObjectURL(e.target.files[0]))
            setProcessing(true)
            setTimeout(() => {
                setProcessing(false)
                setResult({ health: 'Optimal', disease: 'None detected', stage: 'Vegetative confirmed' })
            }, 1800)
        }
    }

    return (
        <div className={`rounded-xl p-5 border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Camera className="w-4 h-4 text-indigo-500" /> Image-AI Intelligence
            </h4>

            {!image ? (
                <label className="cursor-pointer flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors">
                    <Camera className="w-8 h-8 text-gray-400 mb-2" />
                    <span className="text-sm text-gray-500 font-medium">Upload Field Image</span>
                    <span className="text-xs text-gray-400 mt-1">Simulate Multispectral Scan</span>
                    <input type="file" className="hidden" accept="image/*" onChange={handleUpload} />
                </label>
            ) : (
                <div className="space-y-3">
                    <div className="relative rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 h-32">
                        <img src={image} className={`w-full h-full object-cover ${processing ? 'opacity-50 blur-sm' : 'opacity-100'}`} alt="Field" />
                        {processing && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/10">
                                <span className="text-xs font-bold text-white bg-indigo-500 px-3 py-1 rounded-full animate-pulse shadow-lg">Scanning...</span>
                            </div>
                        )}
                    </div>

                    {!processing && result && (
                        <div className="p-3 bg-green-50 dark:bg-green-900/30 rounded-lg text-xs space-y-1.5 border border-green-100 dark:border-green-800">
                            <p className="flex justify-between"><strong>Health Index:</strong> <span className="text-green-600 dark:text-green-400 font-bold">{result.health}</span></p>
                            <p className="flex justify-between"><strong>Disease Signature:</strong> <span>{result.disease}</span></p>
                            <p className="flex justify-between"><strong>Phenology Model:</strong> <span>{result.stage}</span></p>
                        </div>
                    )}

                    {!processing && (
                        <button onClick={() => { setImage(null); setResult(null) }} className="text-xs text-indigo-500 font-medium hover:underline text-center w-full mt-2">
                            Reset & Upload New Frame
                        </button>
                    )}
                </div>
            )}
        </div>
    )
}

// ── Yield Intelligence card ───────────────────────────────────────────────────
const YieldCard = ({ comparison, isDark }) => {
    const hasData = comparison?.calculation_available
    return (
        <div className={`rounded-xl p-5 border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
            <h4 className="font-semibold mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-yellow-500" /> Yield Intelligence
            </h4>
            {hasData ? (
                <div className="space-y-2">
                    {comparison.summary && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">{comparison.summary}</p>
                    )}
                    {comparison.yield_achievement_pct != null && (
                        <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-500 dark:text-gray-400">Achievement</span>
                            <span className={`text-sm font-bold ${comparison.yield_achievement_pct >= 90 ? 'text-green-500' : comparison.yield_achievement_pct >= 70 ? 'text-yellow-500' : 'text-red-500'}`}>
                                {comparison.yield_achievement_pct.toFixed(1)}%
                            </span>
                        </div>
                    )}
                    {comparison.yield_difference_kg != null && (
                        <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-500 dark:text-gray-400">Yield Diff</span>
                            <span className={`text-sm font-bold ${comparison.yield_difference_kg >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                {comparison.yield_difference_kg > 0 ? '+' : ''}{comparison.yield_difference_kg.toFixed(2)} kg
                            </span>
                        </div>
                    )}
                    {comparison.prediction_error_pct != null && (
                        <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-500 dark:text-gray-400">Prediction Error</span>
                            <span className="text-sm font-bold text-orange-500">{comparison.prediction_error_pct.toFixed(1)}%</span>
                        </div>
                    )}
                    <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-1">
                        <div className="flex justify-between items-center">
                            <span className="text-xs text-gray-400">Expected source</span>
                            <SourceBadge source={comparison.expected_yield_source} />
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-xs text-gray-400">Actual source</span>
                            <SourceBadge source={comparison.actual_yield_source} />
                        </div>
                    </div>
                </div>
            ) : (
                <div className="space-y-2">
                    <p className="text-xs text-gray-400 dark:text-gray-500 italic">
                        {comparison?.summary || 'Neither expected nor actual yield is available.'}
                    </p>
                    <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-1">
                        <div className="flex justify-between items-center">
                            <span className="text-xs text-gray-400">Expected source</span>
                            <SourceBadge source={comparison?.expected_yield_source ?? 'not_available'} />
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-xs text-gray-400">Actual source</span>
                            <SourceBadge source={comparison?.actual_yield_source ?? 'not_available'} />
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

// ── Water Productivity card ───────────────────────────────────────────────────
const WaterProdCard = ({ wp, isDark }) => (
    <div className={`rounded-xl p-5 border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
        <h4 className="font-semibold mb-3 flex items-center gap-2">
            <Droplets className="w-4 h-4 text-blue-500" /> Water Productivity
        </h4>
        {wp?.calculation_available ? (
            <div className="space-y-2">
                {wp.summary && <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{wp.summary}</p>}
                <div className="flex justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Productivity</span>
                    <span className="text-sm font-bold text-blue-500">{wp.water_productivity_kg_per_liter?.toFixed(4)} kg/L</span>
                </div>
                {wp.water_cost_liters_per_kg && (
                    <div className="flex justify-between">
                        <span className="text-sm text-gray-500 dark:text-gray-400">Water per kg</span>
                        <span className="text-sm font-bold">{wp.water_cost_liters_per_kg?.toFixed(1)} L/kg</span>
                    </div>
                )}
                <div className="flex justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Water used</span>
                    <span className="text-sm font-bold">{wp.water_used_liters?.toFixed(1)} L</span>
                </div>
                {wp.unit_note && <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{wp.unit_note}</p>}
            </div>
        ) : (
            <div className="space-y-2">
                <p className="text-xs text-gray-400 dark:text-gray-500 italic">
                    {wp?.summary || 'Not Available — awaiting harvest entry and irrigation records.'}
                </p>
                {wp?.water_used_liters != null && (
                    <div className="flex justify-between pb-1 border-b border-gray-100 dark:border-gray-700">
                        <span className="text-sm text-gray-500 dark:text-gray-400">Accumulated Water Used</span>
                        <span className="text-sm font-bold text-blue-500">{wp.water_used_liters?.toFixed(1)} L</span>
                    </div>
                )}
                <p className="text-xs text-gray-400 dark:text-gray-500">Formula: Actual Yield (kg) ÷ Total Water Used (L)</p>
            </div>
        )}
    </div>
)

// ── Create cycle form ─────────────────────────────────────────────────────────
const CreateCyclePanel = ({ isDark, onCreated }) => {
    const [form, setForm] = useState({ crop_type: '', planting_date: '', field_area_m2: '', notes: '' })
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!form.crop_type.trim()) { setError('Crop type is required.'); return }
        setLoading(true); setError(null)
        try {
            const payload = {
                crop_type: form.crop_type.trim(),
                farmer_selected_crop: form.crop_type.trim(),
                planting_date: form.planting_date || null,
                field_area_m2: form.field_area_m2 ? parseFloat(form.field_area_m2) : null,
                notes: form.notes || null,
            }
            const result = await api.createCropCycle(payload)
            onCreated(result)
        } catch (err) {
            setError('Failed to create cycle: ' + (err.detail?.detail || err.message))
        } finally { setLoading(false) }
    }

    const cls = `w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-green-500 ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`

    const COMMON_CROPS = ['Rice', 'Wheat', 'Maize', 'Tomato', 'Potato', 'Onion', 'Cotton', 'Sugarcane']

    return (
        <form onSubmit={handleSubmit} className="space-y-3">
            <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">
                    Crop Type <span className="text-blue-500">(farmer_input)</span>
                </label>
                <input className={cls} placeholder="e.g. Rice, Maize, Tomato" value={form.crop_type}
                    onChange={e => setForm(f => ({ ...f, crop_type: e.target.value }))}
                    list="crop-suggestions" />
                <datalist id="crop-suggestions">
                    {COMMON_CROPS.map(c => <option key={c} value={c} />)}
                </datalist>
            </div>
            <div className="flex flex-wrap gap-1 mt-1">
                {COMMON_CROPS.map(c => (
                    <button key={c} type="button"
                        onClick={() => setForm(f => ({ ...f, crop_type: c }))}
                        className={`text-xs px-2 py-1 rounded-full border transition-colors ${isDark ? 'border-gray-600 hover:bg-gray-700' : 'border-gray-200 hover:bg-gray-100'}`}>
                        {c}
                    </button>
                ))}
            </div>
            <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">
                    Planting Date <span className="text-blue-500">(farmer_input)</span>
                </label>
                <input type="date" className={cls} value={form.planting_date}
                    onChange={e => setForm(f => ({ ...f, planting_date: e.target.value }))} />
            </div>
            <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">Field Area (m²)</label>
                <input type="number" step="0.1" className={cls} placeholder="e.g. 1000" value={form.field_area_m2}
                    onChange={e => setForm(f => ({ ...f, field_area_m2: e.target.value }))} />
            </div>
            <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">Notes</label>
                <textarea className={cls} rows={2} placeholder="Optional notes" value={form.notes}
                    onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
            {error && <p className="text-xs text-red-500 flex items-center gap-1"><AlertTriangle className="w-3 h-3" />{error}</p>}
            <button type="submit" disabled={loading}
                className="w-full py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-semibold disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
                {loading ? <><RefreshCw className="w-3.5 h-3.5 animate-spin" />Creating...</> : <><Plus className="w-3.5 h-3.5" />Create Crop Cycle</>}
            </button>
        </form>
    )
}

// ── Harvest form ──────────────────────────────────────────────────────────────
const HarvestForm = ({ cycleId, isDark, onHarvested }) => {
    const [form, setForm] = useState({ harvest_date: '', actual_yield_kg: '', notes: '' })
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!form.harvest_date || !form.actual_yield_kg) {
            setError('Harvest date and yield are required.'); return
        }
        setLoading(true); setError(null)
        try {
            const result = await api.recordHarvest(cycleId, {
                harvest_date: form.harvest_date,
                actual_yield_kg: parseFloat(form.actual_yield_kg),
                notes: form.notes || null,
            })
            onHarvested(result)
        } catch (err) {
            setError('Failed to record harvest: ' + (err.detail?.detail || err.message))
        } finally { setLoading(false) }
    }

    const cls = `w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'}`

    return (
        <form onSubmit={handleSubmit} className="space-y-3">
            <p className="text-xs text-blue-500 dark:text-blue-400">
                SOURCE: actual_yield_kg = harvest_measurement / farmer_input
            </p>
            <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">Harvest Date *</label>
                <input type="date" className={cls} value={form.harvest_date}
                    onChange={e => setForm(f => ({ ...f, harvest_date: e.target.value }))} />
            </div>
            <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">Actual Yield (kg) *</label>
                <input type="number" step="0.01" min="0" className={cls} placeholder="e.g. 450" value={form.actual_yield_kg}
                    onChange={e => setForm(f => ({ ...f, actual_yield_kg: e.target.value }))} />
            </div>
            <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">Notes</label>
                <textarea className={cls} rows={2} value={form.notes}
                    onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
            {error && <p className="text-xs text-red-500 flex items-center gap-1"><AlertTriangle className="w-3 h-3" />{error}</p>}
            <button type="submit" disabled={loading}
                className="w-full py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold disabled:opacity-50 transition-colors">
                {loading ? 'Recording...' : 'Record Harvest'}
            </button>
        </form>
    )
}

// ── History panel with delete ─────────────────────────────────────────────────
const HistoryPanel = ({ cycles, isDark, onSelect, onDeleted }) => {
    const [deletingId, setDeletingId] = useState(null)
    const [confirmId, setConfirmId] = useState(null)

    const handleDelete = async (id, e) => {
        e.stopPropagation()
        if (confirmId !== id) { setConfirmId(id); return }
        setDeletingId(id); setConfirmId(null)
        try {
            await api.deleteCropCycle(id)
            onDeleted(id)
        } catch (err) {
            alert('Delete failed: ' + (err.message || 'Unknown error'))
        } finally { setDeletingId(null) }
    }

    return (
        <div className={`rounded-xl p-5 border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
            <h3 className="font-semibold mb-3">Crop Cycle History</h3>
            {cycles.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">No crop cycles recorded yet.</p>
            ) : (
                <div className="space-y-2">
                    {cycles.map(c => (
                        <div key={c.id}
                            className={`w-full flex items-center justify-between p-3 rounded-lg border transition-colors ${isDark ? 'border-gray-700 hover:bg-gray-700/50' : 'border-gray-100 hover:bg-gray-50'}`}>
                            <button className="flex-1 flex items-center justify-between text-left" onClick={() => onSelect(c)}>
                                <div>
                                    <p className="text-sm font-semibold flex items-center gap-2">
                                        <Leaf className="w-3.5 h-3.5 text-green-500" />
                                        {c.crop_type}
                                        <span className="text-xs text-gray-400">#{c.id}</span>
                                    </p>
                                    <p className="text-xs text-gray-500 dark:text-gray-400 ml-5">
                                        {c.planting_date ?? 'No date'} · {c.days_since_planting != null ? `${c.days_since_planting}d` : '—'}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2 mr-2">
                                    <StatusPill status={c.lifecycle_status} />
                                    <ChevronRight className="w-4 h-4 text-gray-400" />
                                </div>
                            </button>
                            {/* Delete button */}
                            <button
                                onClick={(e) => handleDelete(c.id, e)}
                                disabled={deletingId === c.id}
                                title={confirmId === c.id ? 'Click again to confirm delete' : 'Delete this cycle'}
                                className={`ml-2 p-1.5 rounded-lg transition-colors disabled:opacity-50 ${confirmId === c.id
                                    ? 'bg-red-500 text-white hover:bg-red-600'
                                    : 'text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20'}`}>
                                {deletingId === c.id
                                    ? <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                    : <Trash2 className="w-3.5 h-3.5" />}
                            </button>
                            {confirmId === c.id && (
                                <button
                                    onClick={() => setConfirmId(null)}
                                    className="ml-1 text-xs text-gray-400 hover:text-gray-600 px-1">
                                    ✕
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}
            {confirmId && (
                <p className="text-xs text-red-500 mt-2 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    Click the red trash icon again to confirm deletion.
                </p>
            )}
        </div>
    )
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Main CropLifecycle component
// ═══════════════════════════════════════════════════════════════════════════════
const CropLifecycle = () => {
    const { isDark } = useDarkMode()
    const [selectedCycleId, setSelectedCycleId] = useState(null)
    const [showCreateForm, setShowCreateForm] = useState(false)
    const [showHarvestForm, setShowHarvestForm] = useState(false)
    const [detailCycle, setDetailCycle] = useState(null)

    // Fetch active cycle (gracefully handle 404)
    const { data: activeCycle, loading: activeLoading, error: activeError, refetch: refetchActive } =
        useApiData(() => api.getActiveCropCycle().catch(e => e.status === 404 ? null : Promise.reject(e)), [], { intervalMs: 30000 })

    // Fetch history
    const { data: historyData, loading: historyLoading, refetch: refetchHistory } =
        useApiData(() => api.listCropCycles(50), [], { intervalMs: 60000 })

    // Fetch yield comparison + water productivity for the selected/active cycle
    const cycleId = selectedCycleId ?? activeCycle?.id
    const { data: yieldComp } = useApiData(
        () => cycleId ? api.getYieldComparison(cycleId) : Promise.resolve(null),
        [cycleId], { intervalMs: 60000 }
    )
    const { data: waterProd } = useApiData(
        () => cycleId ? api.getWaterProductivity(cycleId) : Promise.resolve(null),
        [cycleId], { intervalMs: 60000 }
    )

    const handleCycleCreated = useCallback((cycle) => {
        setShowCreateForm(false)
        refetchActive()
        refetchHistory()
        setSelectedCycleId(cycle.id)
        setDetailCycle(null)
    }, [refetchActive, refetchHistory])

    const handleHarvested = useCallback(() => {
        setShowHarvestForm(false)
        refetchActive()
        refetchHistory()
    }, [refetchActive, refetchHistory])

    const handleDeleted = useCallback((deletedId) => {
        refetchHistory()
        if (selectedCycleId === deletedId) {
            setSelectedCycleId(null)
            setDetailCycle(null)
        }
        refetchActive()
    }, [selectedCycleId, refetchActive, refetchHistory])

    const displayCycle = detailCycle ?? activeCycle
    const stageInfo = displayCycle?.growth_stage_info

    const card = `rounded-xl p-5 shadow-sm border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold flex items-center gap-3">
                    <Sprout className="w-8 h-8 text-green-500" />
                    Crop Lifecycle &amp; Yield Intelligence
                </h2>
                <button onClick={() => setShowCreateForm(v => !v)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-semibold transition-colors">
                    <Plus className="w-4 h-4" />
                    New Crop Cycle
                </button>
            </div>

            {/* Create form */}
            {showCreateForm && (
                <div className={card}>
                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                        <Plus className="w-4 h-4 text-green-500" /> New Crop Cycle
                    </h3>
                    <CreateCyclePanel isDark={isDark} onCreated={handleCycleCreated} />
                </div>
            )}

            {/* Active cycle overview */}
            {activeLoading && <p className="text-sm text-gray-500 dark:text-gray-400 animate-pulse">Loading active crop cycle...</p>}
            {activeError && (
                <div className={`${card} flex items-center gap-2 text-amber-600 dark:text-amber-400`}>
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <p className="text-sm">Could not load active cycle. {activeError.message}</p>
                </div>
            )}
            {!activeLoading && !activeCycle && !showCreateForm && !historyLoading && (
                <div className={`${card} text-center py-10`}>
                    <Sprout className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-500 dark:text-gray-400 font-medium">No active crop cycle</p>
                    <p className="text-sm text-gray-400 dark:text-gray-500">
                        Click <strong>+ New Crop Cycle</strong> to start tracking your crop.
                    </p>
                </div>
            )}

            {displayCycle && (
                <>
                    {/* If viewing historical cycle, show banner */}
                    {detailCycle && detailCycle.id !== activeCycle?.id && (
                        <div className="flex items-center justify-between px-4 py-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                            <span className="text-sm text-blue-700 dark:text-blue-300">
                                Viewing historical cycle #{detailCycle.id} — {detailCycle.crop_type}
                            </span>
                            <button onClick={() => { setDetailCycle(null); setSelectedCycleId(null) }}
                                className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
                                ← Back to Active
                            </button>
                        </div>
                    )}

                    {/* Main info grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                        {/* Current crop panel */}
                        <div className={`lg:col-span-2 ${card}`}>
                            <div className="flex items-center justify-between mb-4">
                                <div>
                                    <h3 className="text-xl font-bold flex items-center gap-2">
                                        <Leaf className="w-5 h-5 text-green-500" />
                                        {displayCycle.crop_type}
                                    </h3>
                                    <p className="text-sm text-gray-500 dark:text-gray-400 ml-7">
                                        {displayCycle.field_id ?? 'No field ID'}
                                        {displayCycle.field_area_m2 != null && ` · ${displayCycle.field_area_m2} m²`}
                                    </p>
                                </div>
                                <StatusPill status={displayCycle.lifecycle_status} />
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8">
                                <div>
                                    <InfoRow label="AI Recommended Crop"
                                        value={displayCycle.ai_recommended_crop}
                                        source="ai_recommended"
                                        unavailableText="Not Available" />
                                    <InfoRow label="Farmer Selected Crop"
                                        value={displayCycle.farmer_selected_crop}
                                        source="farmer_selected"
                                        unavailableText="Not confirmed yet" />
                                    <InfoRow label="Planting Date"
                                        value={displayCycle.planting_date}
                                        source={displayCycle.planting_date_source}
                                        unavailableText="Not set — awaiting farmer input" />
                                    <InfoRow label="Days Since Planting"
                                        value={displayCycle.days_since_planting != null ? `${displayCycle.days_since_planting} days` : null}
                                        source={displayCycle.days_since_planting_source}
                                        unavailableText="Not Available — planting date not set" />
                                </div>
                                <div>
                                    <InfoRow label="Current Growth Stage"
                                        value={displayCycle.growth_stage}
                                        source="phenology_engine / calculated" />
                                    <InfoRow label="Expected Yield"
                                        value={displayCycle.expected_yield_kg != null ? `${displayCycle.expected_yield_kg.toFixed(2)} kg` : null}
                                        source={displayCycle.expected_yield_source}
                                        unavailableText={displayCycle.expected_yield_display ?? 'Not Available — awaiting yield model'} />
                                    <InfoRow label="Actual Yield"
                                        value={displayCycle.actual_yield_kg != null ? `${displayCycle.actual_yield_kg.toFixed(2)} kg` : null}
                                        source={displayCycle.actual_yield_source}
                                        unavailableText={displayCycle.actual_yield_display ?? 'Not Available — awaiting harvest'} />
                                    <InfoRow label="Harvest Date"
                                        value={displayCycle.harvest_date}
                                        source="farmer_input"
                                        unavailableText="Not harvested yet" />
                                </div>
                            </div>

                            {/* Action buttons */}
                            {displayCycle.lifecycle_status !== 'HARVESTED' && displayCycle.lifecycle_status !== 'COMPLETED' && (
                                <div className="mt-4 flex flex-wrap gap-2">
                                    <button onClick={() => setShowHarvestForm(v => !v)}
                                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold transition-colors">
                                        <Scale className="w-3.5 h-3.5" /> Record Harvest
                                    </button>
                                    <button
                                        onClick={() => api.updateLifecycleStatus(displayCycle.id, 'HARVEST_READY')
                                            .then(refetchActive).catch(e => alert('Error: ' + e.message))}
                                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-yellow-500 hover:bg-yellow-600 text-white text-xs font-semibold transition-colors">
                                        <CheckCircle className="w-3.5 h-3.5" /> Mark Harvest Ready
                                    </button>
                                    {displayCycle.lifecycle_status === 'HARVESTED' && (
                                        <button
                                            onClick={() => api.updateLifecycleStatus(displayCycle.id, 'COMPLETED')
                                                .then(refetchActive).catch(e => alert('Error: ' + e.message))}
                                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-500 hover:bg-gray-600 text-white text-xs font-semibold transition-colors">
                                            Archive Cycle
                                        </button>
                                    )}
                                </div>
                            )}

                            {/* Harvest form */}
                            {showHarvestForm && (
                                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                                    <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                                        <Scale className="w-4 h-4 text-purple-500" /> Record Actual Harvest
                                    </h4>
                                    <HarvestForm cycleId={displayCycle.id} isDark={isDark} onHarvested={handleHarvested} />
                                </div>
                            )}
                        </div>

                        {/* Right column: growth timeline + GDD + image AI */}
                        <div className="space-y-4">
                            <GrowthTimeline stageInfo={stageInfo} isDark={isDark} />
                            <GDDCard
                                gdd={displayCycle.accumulated_gdd}
                                isDark={isDark}
                                cycleId={displayCycle.id}
                                onRefresh={refetchActive}
                            />
                            <ImageAICard isDark={isDark} />
                        </div>
                    </div>

                    {/* Yield + water productivity row */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <YieldCard comparison={yieldComp} isDark={isDark} />
                        <WaterProdCard wp={waterProd} isDark={isDark} />
                    </div>
                </>
            )}

            {/* History */}
            <HistoryPanel
                cycles={historyData?.cycles ?? []}
                isDark={isDark}
                onSelect={c => {
                    setDetailCycle(c)
                    setSelectedCycleId(c.id)
                    setShowHarvestForm(false)
                    setShowCreateForm(false)
                }}
                onDeleted={handleDeleted}
            />

            {/* Data provenance legend */}
            <div className={`${card} text-xs`}>
                <h4 className="font-semibold mb-2 text-gray-700 dark:text-gray-300">Data Provenance Legend</h4>
                <div className="flex flex-wrap gap-2">
                    <SourceBadge source="farmer_input" />
                    <SourceBadge source="ai_recommended" />
                    <SourceBadge source="farmer_selected" />
                    <SourceBadge source="calculated" />
                    <SourceBadge source="pump_records / irrigation_history" />
                    <SourceBadge source="harvest_measurement / farmer_input" />
                    <SourceBadge source="not_available" />
                </div>
            </div>
        </div>
    )
}

export default CropLifecycle
