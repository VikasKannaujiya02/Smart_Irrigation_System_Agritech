import React, { useState, useRef, useCallback } from 'react'
import {
    Leaf, UploadCloud, History, BarChart3, Search, Trash2, AlertTriangle,
    CheckCircle2, XCircle, RefreshCw, ChevronDown, Info, Camera, X,
    ShieldAlert, Clock, FlaskConical, Sprout, Eye, Download
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

// ── Validation constants ──────────────────────────────────────────────────────
const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
const MAX_SIZE_BYTES = 10 * 1024 * 1024 // 10 MB

// ── Confidence coloring ───────────────────────────────────────────────────────
const confColor = (conf) => {
    if (!conf && conf !== 0) return 'text-gray-400'
    const pct = conf > 1 ? conf : conf * 100
    if (pct >= 80) return 'text-green-500'
    if (pct >= 60) return 'text-amber-500'
    return 'text-red-400'
}

// ── Status badge ─────────────────────────────────────────────────────────────
const StatusBadge = ({ healthy }) => {
    const { t } = useTranslation()
    if (healthy === undefined || healthy === null) return null
    return healthy ? (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 text-xs font-semibold">
            <CheckCircle2 className="w-3 h-3" /> {t('healthy')}
        </span>
    ) : (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 text-xs font-semibold">
            <ShieldAlert className="w-3 h-3" /> {t('diseased')}
        </span>
    )
}

// ── Card wrapper ──────────────────────────────────────────────────────────────
const Card = ({ children, className = '' }) => {
    const { isDark } = useDarkMode()
    return (
        <div className={`rounded-xl border shadow-sm ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} ${className}`}>
            {children}
        </div>
    )
}

// ── Metric card ───────────────────────────────────────────────────────────────
const MetricCard = ({ icon: Icon, label, value, color = 'blue', loading = false }) => {
    const colorMap = {
        blue: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
        green: 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400',
        red: 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400',
        amber: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
    }
    return (
        <Card>
            <div className="p-5">
                <div className={`w-10 h-10 rounded-lg ${colorMap[color]} flex items-center justify-center mb-3`}>
                    <Icon className="w-5 h-5" />
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
                <p className="text-2xl font-bold">{loading ? '—' : (value ?? '—')}</p>
            </div>
        </Card>
    )
}

// ── Upload zone ───────────────────────────────────────────────────────────────
const UploadZone = ({ onFile, isDark, t }) => {
    const [dragOver, setDragOver] = useState(false)
    const inputRef = useRef(null)
    const cameraRef = useRef(null)

    const handle = useCallback((file) => {
        if (!file) return
        if (!ALLOWED_TYPES.includes(file.type)) {
            onFile(null, t('disease.invalidFormat'))
            return
        }
        if (file.size > MAX_SIZE_BYTES) {
            onFile(null, t('disease.fileTooLarge'))
            return
        }
        onFile(file, null)
    }, [onFile, t])

    return (
        <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); handle(e.dataTransfer.files[0]) }}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all ${dragOver
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/10'
                : isDark ? 'border-gray-700 hover:border-gray-500' : 'border-gray-300 hover:border-gray-400'
                }`}
        >
            <div className="w-16 h-16 rounded-full bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center">
                <UploadCloud className="w-8 h-8 text-primary-500" />
            </div>
            <div className="text-center">
                <p className="font-semibold text-base">{t('disease.uploadImage')}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{t('disease.dragDrop')}</p>
                <p className="text-xs text-gray-400 mt-2">{t('disease.supportedFormats')}</p>
                <p className="text-xs text-gray-400">{t('disease.maxSize')}</p>
            </div>
            <div className="flex gap-2 mt-2">
                <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); inputRef.current?.click() }}
                    className="px-4 py-2 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors"
                >
                    {t('disease.browseFiles')}
                </button>
                <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); cameraRef.current?.click() }}
                    className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
                >
                    <Camera className="w-4 h-4" /> {t('disease.captureCamera')}
                </button>
            </div>
            <input ref={inputRef} type="file" accept="image/jpeg,image/jpg,image/png,image/webp" className="hidden" onChange={(e) => handle(e.target.files[0])} />
            <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => handle(e.target.files[0])} />
        </div>
    )
}

// ── Disease info panel ────────────────────────────────────────────────────────
const DISEASE_INFO = {
    'Tomato___Late_blight': {
        overview: 'Late blight is a serious disease caused by the oomycete Phytophthora infestans.',
        symptoms: ['Dark brown water-soaked lesions on leaves', 'White spore growth on undersides', 'Brown lesions on stems', 'Fruit rot'],
        causes: ['Cool, moist conditions', 'Temperature 10–25°C with high humidity', 'Infected seeds or transplants'],
        prevention: ['Avoid overhead irrigation', 'Use certified disease-free seeds', 'Apply copper-based fungicides preventively', 'Ensure good crop spacing'],
        management: ['Remove infected foliage immediately', 'Apply registered fungicides', 'Crop rotation with non-solanaceous crops'],
    },
    'Tomato___Early_blight': {
        overview: 'Early blight is caused by Alternaria solani and commonly affects tomatoes and potatoes.',
        symptoms: ['Target-like concentric rings on older leaves', 'Yellow halo surrounding lesions', 'Dark dry lesions', 'Defoliation in severe cases'],
        causes: ['Warm temperatures 24–29°C', 'High humidity or frequent rain', 'Nutrient-stressed plants'],
        prevention: ['Proper fertilization to maintain plant vigor', 'Mulching to prevent soil splash', 'Crop rotation', 'Resistant varieties'],
        management: ['Remove affected leaves', 'Apply fungicides with mancozeb or chlorothalonil', 'Improve drainage'],
    },
    'Potato___Late_blight': {
        overview: 'Potato late blight caused by Phytophthora infestans can cause total crop loss.',
        symptoms: ['Water-soaked pale green spots on leaves', 'White cottony growth on leaf underside', 'Brown tuber rot'],
        causes: ['Cool, wet conditions', 'Infected tubers or plant debris'],
        prevention: ['Use certified seed potatoes', 'Avoid planting in waterlogged soil', 'Hilling to protect tubers'],
        management: ['Destroy infected foliage', 'Apply metalaxyl-based fungicides', 'Harvest quickly during an outbreak'],
    },
}

const DiseaseInfoPanel = ({ prediction, t, isDark }) => {
    const diseaseKey = prediction?.class
    const info = diseaseKey ? DISEASE_INFO[diseaseKey] : null
    if (!info) return null

    return (
        <Card>
            <div className="p-5">
                <h3 className="font-semibold text-base mb-4 flex items-center gap-2">
                    <FlaskConical className="w-4 h-4 text-emerald-500" />
                    {t('disease.diseaseInfo')}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">{info.overview}</p>
                <div className="space-y-3">
                    {[
                        { key: 'symptoms', icon: Eye, color: 'text-orange-500' },
                        { key: 'causes', icon: Info, color: 'text-blue-500' },
                        { key: 'prevention', icon: ShieldAlert, color: 'text-green-500' },
                        { key: 'management', icon: Sprout, color: 'text-purple-500' },
                    ].map(({ key, icon: Icon, color }) => (
                        info[key]?.length > 0 && (
                            <div key={key}>
                                <p className={`text-xs font-semibold uppercase tracking-wide ${color} mb-1.5 flex items-center gap-1`}>
                                    <Icon className="w-3 h-3" /> {t(`disease.${key}`)}
                                </p>
                                <ul className="space-y-1">
                                    {info[key].map((item, i) => (
                                        <li key={i} className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-1.5">
                                            <span className="mt-1 w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-gray-600 flex-shrink-0" />
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )
                    ))}
                </div>
            </div>
        </Card>
    )
}

// ── Model Unavailable banner ──────────────────────────────────────────────────
const ModelUnavailableBanner = ({ t, isDark }) => (
    <div className={`rounded-xl border p-5 flex items-start gap-4 ${isDark ? 'bg-amber-900/10 border-amber-800' : 'bg-amber-50 border-amber-200'}`}>
        <AlertTriangle className="w-6 h-6 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
            <p className="font-semibold text-amber-700 dark:text-amber-400">{t('disease.modelUnavailable')}</p>
            <p className="text-sm text-amber-600 dark:text-amber-500 mt-1">{t('disease.modelUnavailableMsg')}</p>
        </div>
    </div>
)

// ── History Table ─────────────────────────────────────────────────────────────
const DiseaseHistoryTable = ({ records, onDelete, onView, loading, t, isDark }) => {
    if (loading) return (
        <div className="py-12 flex items-center justify-center text-gray-400">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" /> {t('loading')}
        </div>
    )
    if (!records?.length) return (
        <div className="py-12 flex flex-col items-center gap-2 text-gray-400">
            <Leaf className="w-10 h-10 opacity-30" />
            <p className="text-sm">{t('disease.noHistory')}</p>
        </div>
    )
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className={`text-left text-xs font-semibold uppercase tracking-wide ${isDark ? 'text-gray-400' : 'text-gray-500'} border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                        <th className="px-4 py-3">{t('disease.scanId')}</th>
                        <th className="px-4 py-3">{t('disease.dateTime')}</th>
                        <th className="px-4 py-3">{t('disease.crop')}</th>
                        <th className="px-4 py-3">{t('disease.disease')}</th>
                        <th className="px-4 py-3">{t('disease.confidence')}</th>
                        <th className="px-4 py-3">{t('status')}</th>
                        <th className="px-4 py-3">{t('actions')}</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {records.map((rec) => (
                        <tr key={rec.scan_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                            <td className="px-4 py-3 font-mono text-xs text-gray-500">{rec.scan_id?.slice(0, 8)}...</td>
                            <td className="px-4 py-3 text-xs">{rec.created_at ? new Date(rec.created_at).toLocaleString() : '—'}</td>
                            <td className="px-4 py-3">{rec.crop || '—'}</td>
                            <td className="px-4 py-3 text-xs max-w-32 truncate" title={rec.disease_class}>{rec.disease_class || '—'}</td>
                            <td className={`px-4 py-3 font-mono font-bold ${confColor(rec.confidence)}`}>
                                {rec.confidence != null ? `${(rec.confidence * 100).toFixed(0)}%` : '—'}
                            </td>
                            <td className="px-4 py-3"><StatusBadge healthy={rec.is_healthy} /></td>
                            <td className="px-4 py-3">
                                <div className="flex items-center gap-2">
                                    <button onClick={() => onView(rec)} className="p-1.5 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 text-blue-500 transition-colors" title={t('view')}>
                                        <Eye className="w-4 h-4" />
                                    </button>
                                    <button onClick={() => onDelete(rec.scan_id)} className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-400 transition-colors" title={t('delete')}>
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════════════════════
const PlantDisease = () => {
    const { t } = useTranslation()
    const { isDark } = useDarkMode()
    const [activeTab, setActiveTab] = useState('upload')
    const [imageFile, setImageFile] = useState(null)
    const [imagePreview, setImagePreview] = useState(null)
    const [uploadError, setUploadError] = useState(null)
    const [analyzing, setAnalyzing] = useState(false)
    const [prediction, setPrediction] = useState(null)
    const [inferenceError, setInferenceError] = useState(null)
    const [histSearch, setHistSearch] = useState('')
    const [histCropFilter, setHistCropFilter] = useState('all')
    const [histStatusFilter, setHistStatusFilter] = useState('all')
    const [selectedRecord, setSelectedRecord] = useState(null)

    // History data
    const { data: histData, loading: histLoading, refetch: refetchHistory } =
        useApiData(() => api.getDiseaseHistory(100), [], { intervalMs: 0 })

    // Model status
    const { data: modelStatus } = useApiData(() => api.getDiseaseStatus(), [], { intervalMs: 30000 })
    const modelAvailable = modelStatus?.available === true

    // History records
    const records = histData?.records || []
    const filteredRecords = records.filter(r => {
        const matchSearch = !histSearch || (r.crop?.toLowerCase().includes(histSearch.toLowerCase()) || r.disease_class?.toLowerCase().includes(histSearch.toLowerCase()))
        const matchCrop = histCropFilter === 'all' || r.crop === histCropFilter
        const matchStatus = histStatusFilter === 'all' || (histStatusFilter === 'healthy' ? r.is_healthy : !r.is_healthy)
        return matchSearch && matchCrop && matchStatus
    })

    const uniqueCrops = [...new Set(records.map(r => r.crop).filter(Boolean))]

    // Dashboard metrics from history
    const totalScans = records.length
    const healthyCount = records.filter(r => r.is_healthy).length
    const diseaseCount = records.filter(r => !r.is_healthy).length
    const thisWeek = records.filter(r => {
        if (!r.created_at) return false
        const diff = Date.now() - new Date(r.created_at).getTime()
        return diff < 7 * 24 * 60 * 60 * 1000
    }).length

    const handleFile = (file, error) => {
        if (error) { setUploadError(error); setImageFile(null); setImagePreview(null); return }
        setUploadError(null)
        setImageFile(file)
        setImagePreview(URL.createObjectURL(file))
        setPrediction(null)
        setInferenceError(null)
    }

    const handleClear = () => {
        if (imagePreview) URL.revokeObjectURL(imagePreview)
        setImageFile(null)
        setImagePreview(null)
        setPrediction(null)
        setInferenceError(null)
        setUploadError(null)
    }

    const handleAnalyze = async () => {
        if (!imageFile) return
        setAnalyzing(true)
        setPrediction(null)
        setInferenceError(null)
        try {
            const fd = new FormData()
            fd.append('file', imageFile)
            const result = await api.predictDisease(fd)
            setPrediction(result)
            refetchHistory()
            setActiveTab('results')
        } catch (err) {
            if (err.status === 503 || err.status === 404) {
                setInferenceError(t('disease.modelUnavailable'))
            } else {
                setInferenceError(t('disease.inferenceError'))
            }
        } finally {
            setAnalyzing(false)
        }
    }

    const handleDelete = async (scanId) => {
        if (!window.confirm(t('confirm') + '?')) return
        try {
            await api.deleteDiseaseRecord(scanId)
            refetchHistory()
            if (selectedRecord?.scan_id === scanId) setSelectedRecord(null)
        } catch { /* ignore */ }
    }

    const cardCls = `rounded-xl border shadow-sm ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`
    const inputCls = `w-full px-3 py-2 rounded-lg border text-sm ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'} focus:outline-none focus:ring-2 focus:ring-primary-500`
    const tabCls = (active) => `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${active ? 'bg-primary-500 text-white' : isDark ? 'hover:bg-gray-700 text-gray-400' : 'hover:bg-gray-100 text-gray-600'}`

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                    <h2 className="text-2xl font-bold flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-400 to-emerald-600 flex items-center justify-center shadow-md">
                            <Leaf className="w-5 h-5 text-white" />
                        </div>
                        {t('disease.title')}
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{t('disease.subtitle')}</p>
                </div>

                {/* Model status badge */}
                {modelStatus && (
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${modelAvailable
                        ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800'
                        : 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800'
                        }`}>
                        {modelAvailable ? '✅ Model Ready' : '⚠ Model Unavailable'}
                    </span>
                )}
            </div>

            {/* Tab navigation */}
            <div className="flex items-center gap-2 flex-wrap">
                {[
                    { id: 'dashboard', label: t('disease.dashboard'), icon: BarChart3 },
                    { id: 'upload', label: t('disease.uploadAnalyze'), icon: UploadCloud },
                    { id: 'results', label: t('disease.results'), icon: Eye },
                    { id: 'history', label: t('disease.history'), icon: History },
                ].map(tab => {
                    const Icon = tab.icon
                    return (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={tabCls(activeTab === tab.id)}>
                            <span className="flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" />{tab.label}</span>
                        </button>
                    )
                })}
            </div>

            {/* ── DASHBOARD TAB ─────────────────────────────────────────────── */}
            {activeTab === 'dashboard' && (
                <div className="space-y-6">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <MetricCard icon={BarChart3} label={t('disease.totalScans')} value={totalScans} color="blue" />
                        <MetricCard icon={CheckCircle2} label={t('disease.healthyDetections')} value={healthyCount} color="green" />
                        <MetricCard icon={ShieldAlert} label={t('disease.diseaseDetections')} value={diseaseCount} color="red" />
                        <MetricCard icon={Clock} label={t('disease.detectionsThisWeek')} value={thisWeek} color="amber" />
                    </div>

                    {/* Recent scans */}
                    <Card>
                        <div className="p-5">
                            <h3 className="font-semibold text-base mb-4 flex items-center gap-2">
                                <History className="w-4 h-4 text-indigo-500" /> {t('disease.recentScans')}
                            </h3>
                            {records.length === 0 ? (
                                <div className="py-8 flex flex-col items-center gap-2 text-gray-400">
                                    <Leaf className="w-10 h-10 opacity-30" />
                                    <p className="text-sm">{t('disease.emptyState')}</p>
                                </div>
                            ) : (
                                <DiseaseHistoryTable
                                    records={records.slice(0, 5)}
                                    onDelete={handleDelete}
                                    onView={(r) => { setSelectedRecord(r); setActiveTab('results') }}
                                    loading={false}
                                    t={t}
                                    isDark={isDark}
                                />
                            )}
                        </div>
                    </Card>

                    {!modelAvailable && !(modelStatus === null) && <ModelUnavailableBanner t={t} isDark={isDark} />}
                </div>
            )}

            {/* ── UPLOAD & ANALYZE TAB ──────────────────────────────────────── */}
            {activeTab === 'upload' && (
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                    <div className="lg:col-span-3 space-y-4">
                        {!imagePreview ? (
                            <UploadZone onFile={handleFile} isDark={isDark} t={t} />
                        ) : (
                            <Card className="p-5">
                                <div className="relative">
                                    <img src={imagePreview} alt="preview" className="w-full max-h-80 object-contain rounded-lg" />
                                    <button
                                        onClick={handleClear}
                                        className="absolute top-2 right-2 p-1.5 bg-black/60 rounded-full text-white hover:bg-black/80 transition-colors"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                                <div className="flex items-center gap-3 mt-4">
                                    <button
                                        onClick={handleAnalyze}
                                        disabled={analyzing}
                                        className="flex-1 py-2.5 rounded-lg bg-primary-500 hover:bg-primary-600 disabled:opacity-60 text-white font-semibold flex items-center justify-center gap-2 transition-colors"
                                    >
                                        {analyzing ? (
                                            <><RefreshCw className="w-4 h-4 animate-spin" /> {t('disease.analyzing')}</>
                                        ) : (
                                            <><Leaf className="w-4 h-4" /> {t('disease.analyzeImage')}</>
                                        )}
                                    </button>
                                    <button
                                        onClick={handleClear}
                                        className="px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium text-sm"
                                    >
                                        {t('disease.clearImage')}
                                    </button>
                                </div>
                            </Card>
                        )}

                        {uploadError && (
                            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm">
                                <XCircle className="w-4 h-4 flex-shrink-0" /> {uploadError}
                            </div>
                        )}
                        {inferenceError && (
                            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm">
                                <XCircle className="w-4 h-4 flex-shrink-0" /> {inferenceError}
                            </div>
                        )}
                    </div>

                    <div className="lg:col-span-2 space-y-4">
                        {!modelAvailable && !(modelStatus === null) && <ModelUnavailableBanner t={t} isDark={isDark} />}
                        <Card className="p-5">
                            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
                                <Info className="w-4 h-4 text-blue-500" /> How it works
                            </h3>
                            <ol className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                                <li className="flex items-start gap-2"><span className="w-5 h-5 rounded-full bg-primary-500 text-white text-xs flex items-center justify-center flex-shrink-0 font-bold">1</span>Upload a clear photo of the plant leaf</li>
                                <li className="flex items-start gap-2"><span className="w-5 h-5 rounded-full bg-primary-500 text-white text-xs flex items-center justify-center flex-shrink-0 font-bold">2</span>Click "Analyze Image" to run AI inference</li>
                                <li className="flex items-start gap-2"><span className="w-5 h-5 rounded-full bg-primary-500 text-white text-xs flex items-center justify-center flex-shrink-0 font-bold">3</span>View predicted disease, confidence, and recommendations</li>
                            </ol>
                            <div className="mt-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 text-xs text-amber-700 dark:text-amber-400">
                                <strong>Note:</strong> AI predictions are not a confirmed diagnosis. Consult an agronomist for critical decisions.
                            </div>
                        </Card>
                    </div>
                </div>
            )}

            {/* ── RESULTS TAB ────────────────────────────────────────────────── */}
            {activeTab === 'results' && (
                <div className="space-y-6">
                    {(() => {
                        const result = selectedRecord
                            ? {
                                crop: selectedRecord.crop,
                                disease_class: selectedRecord.disease_class,
                                is_healthy: selectedRecord.is_healthy,
                                confidence: selectedRecord.confidence,
                                alternatives: selectedRecord.alternatives,
                                created_at: selectedRecord.created_at,
                                model_version: selectedRecord.model_version,
                                image_url: selectedRecord.image_url,
                            }
                            : prediction

                        if (!result) {
                            return (
                                <div className="py-16 flex flex-col items-center gap-3 text-gray-400">
                                    <Eye className="w-12 h-12 opacity-20" />
                                    <p className="text-base font-medium">{t('disease.emptyState')}</p>
                                    <button onClick={() => setActiveTab('upload')} className="mt-2 px-4 py-2 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors">
                                        {t('disease.uploadAnalyze')}
                                    </button>
                                </div>
                            )
                        }

                        const confidencePct = result.confidence != null
                            ? (result.confidence > 1 ? result.confidence : result.confidence * 100).toFixed(1)
                            : null
                        const lowConf = confidencePct !== null && parseFloat(confidencePct) < 60

                        return (
                            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                                <div className="lg:col-span-3 space-y-4">
                                    {/* Result card */}
                                    <Card className="p-5">
                                        <div className="flex items-center gap-3 mb-4">
                                            <h3 className="font-semibold text-base flex-1">{t('disease.results')}</h3>
                                            <StatusBadge healthy={result.is_healthy} />
                                            {selectedRecord && (
                                                <button onClick={() => setSelectedRecord(null)} className="text-xs text-gray-400 hover:text-gray-600">Clear</button>
                                            )}
                                        </div>

                                        {result.image_url && (
                                            <img src={result.image_url} alt="analyzed" className="w-full max-h-48 object-contain rounded-lg mb-4 border border-gray-200 dark:border-gray-700" />
                                        )}

                                        <div className="grid grid-cols-2 gap-4">
                                            <div className={`p-3 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
                                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{t('disease.detectedCrop')}</p>
                                                <p className="font-semibold">{result.crop || '—'}</p>
                                            </div>
                                            <div className={`p-3 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
                                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{t('disease.confidence')}</p>
                                                <p className={`font-bold text-lg ${confColor(result.confidence)}`}>{confidencePct != null ? `${confidencePct}%` : '—'}</p>
                                            </div>
                                        </div>

                                        <div className={`mt-4 p-3 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
                                            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{t('disease.predictedDisease')}</p>
                                            <p className="font-semibold break-words">{result.disease_class || '—'}</p>
                                        </div>

                                        {result.created_at && (
                                            <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
                                                <Clock className="w-3 h-3" />
                                                {new Date(result.created_at).toLocaleString()}
                                                {result.model_version && <span className="ml-auto">Model: {result.model_version}</span>}
                                            </div>
                                        )}

                                        {lowConf && (
                                            <div className="mt-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 flex items-start gap-2 text-sm text-amber-700 dark:text-amber-400">
                                                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                                <div>
                                                    <strong>{t('disease.uncertainty')}: </strong>{t('disease.uncertaintyMsg')}
                                                </div>
                                            </div>
                                        )}
                                    </Card>

                                    {/* Alternatives */}
                                    {result.alternatives?.length > 0 && (
                                        <Card className="p-5">
                                            <h4 className="font-semibold text-sm mb-3">{t('disease.alternativePredictions')}</h4>
                                            <div className="space-y-2">
                                                {result.alternatives.map((alt, i) => (
                                                    <div key={i} className="flex items-center justify-between text-sm">
                                                        <span className="text-gray-600 dark:text-gray-400">{alt.class}</span>
                                                        <span className={`font-mono font-semibold ${confColor(alt.confidence)}`}>
                                                            {((alt.confidence > 1 ? alt.confidence : alt.confidence * 100)).toFixed(1)}%
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </Card>
                                    )}
                                </div>

                                <div className="lg:col-span-2">
                                    <DiseaseInfoPanel prediction={result} t={t} isDark={isDark} />
                                </div>
                            </div>
                        )
                    })()}
                </div>
            )}

            {/* ── HISTORY TAB ────────────────────────────────────────────────── */}
            {activeTab === 'history' && (
                <div className="space-y-4">
                    {/* Filters */}
                    <Card className="p-4">
                        <div className="flex flex-wrap items-center gap-3">
                            <div className="relative flex-1 min-w-48">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                <input
                                    type="text"
                                    placeholder={`${t('search')}...`}
                                    value={histSearch}
                                    onChange={e => setHistSearch(e.target.value)}
                                    className={`${inputCls} pl-9`}
                                />
                            </div>
                            <select value={histCropFilter} onChange={e => setHistCropFilter(e.target.value)} className={inputCls} style={{ width: 'auto' }}>
                                <option value="all">{t('disease.filterByCrop')}</option>
                                {uniqueCrops.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                            <select value={histStatusFilter} onChange={e => setHistStatusFilter(e.target.value)} className={inputCls} style={{ width: 'auto' }}>
                                <option value="all">{t('all')}</option>
                                <option value="healthy">{t('healthy')}</option>
                                <option value="diseased">{t('diseased')}</option>
                            </select>
                            <button onClick={refetchHistory} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                                <RefreshCw className="w-4 h-4" />
                            </button>
                        </div>
                    </Card>

                    <Card>
                        <div className="p-1">
                            <DiseaseHistoryTable
                                records={filteredRecords}
                                onDelete={handleDelete}
                                onView={(r) => { setSelectedRecord(r); setActiveTab('results') }}
                                loading={histLoading}
                                t={t}
                                isDark={isDark}
                            />
                        </div>
                        {records.length > 0 && filteredRecords.length === 0 && (
                            <div className="py-6 text-center text-sm text-gray-400">{t('disease.noResultsFilter')}</div>
                        )}
                    </Card>
                </div>
            )}
        </div>
    )
}

export default PlantDisease
