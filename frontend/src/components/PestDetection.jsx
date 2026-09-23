import React, { useState, useRef, useCallback, useEffect } from 'react'
import {
    Bug, UploadCloud, History, BarChart3, Search, Trash2, AlertTriangle,
    CheckCircle2, XCircle, RefreshCw, Info, Camera, X, Clock, Eye,
    ShieldAlert, Layers, Crosshair
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'

// ── Validation constants ──────────────────────────────────────────────────────
const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
const MAX_SIZE_BYTES = 10 * 1024 * 1024

// ── Confidence coloring ───────────────────────────────────────────────────────
const confColor = (conf) => {
    if (!conf && conf !== 0) return 'text-gray-400'
    const pct = conf > 1 ? conf : conf * 100
    if (pct >= 80) return 'text-green-500'
    if (pct >= 60) return 'text-amber-500'
    return 'text-red-400'
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
const MetricCard = ({ icon: Icon, label, value, color = 'blue' }) => {
    const colorMap = {
        blue: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
        red: 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400',
        green: 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400',
        amber: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
    }
    return (
        <Card>
            <div className="p-5">
                <div className={`w-10 h-10 rounded-lg ${colorMap[color]} flex items-center justify-center mb-3`}>
                    <Icon className="w-5 h-5" />
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
                <p className="text-2xl font-bold">{value ?? '—'}</p>
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
            onFile(null, t('pest.invalidFormat'))
            return
        }
        if (file.size > MAX_SIZE_BYTES) {
            onFile(null, t('pest.fileTooLarge'))
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
            <div className="w-16 h-16 rounded-full bg-orange-50 dark:bg-orange-900/20 flex items-center justify-center">
                <Bug className="w-8 h-8 text-orange-500" />
            </div>
            <div className="text-center">
                <p className="font-semibold text-base">{t('pest.uploadImage')}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{t('pest.dragDrop')}</p>
                <p className="text-xs text-gray-400 mt-2">{t('pest.supportedFormats')}</p>
                <p className="text-xs text-gray-400">{t('pest.maxSize')}</p>
            </div>
            <div className="flex gap-2 mt-2">
                <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); inputRef.current?.click() }}
                    className="px-4 py-2 rounded-lg bg-orange-500 text-white text-sm font-medium hover:bg-orange-600 transition-colors"
                >
                    {t('pest.browseFiles')}
                </button>
                <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); cameraRef.current?.click() }}
                    className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
                >
                    <Camera className="w-4 h-4" /> {t('pest.captureCamera')}
                </button>
            </div>
            <input ref={inputRef} type="file" accept="image/jpeg,image/jpg,image/png,image/webp" className="hidden" onChange={(e) => handle(e.target.files[0])} />
            <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => handle(e.target.files[0])} />
        </div>
    )
}

// ── Bounding Box Canvas ───────────────────────────────────────────────────────
const BoundingBoxCanvas = ({ imageUrl, boxes }) => {
    const canvasRef = useRef(null)
    const imgRef = useRef(null)

    useEffect(() => {
        if (!imageUrl || !boxes?.length || !canvasRef.current) return
        const img = new Image()
        img.onload = () => {
            const canvas = canvasRef.current
            if (!canvas) return
            canvas.width = img.naturalWidth
            canvas.height = img.naturalHeight
            const ctx = canvas.getContext('2d')
            ctx.drawImage(img, 0, 0)
            boxes.forEach((box, i) => {
                const colors = ['#ef4444', '#f59e0b', '#10b981', '#6366f1', '#ec4899']
                const color = colors[i % colors.length]
                ctx.strokeStyle = color
                ctx.lineWidth = 3
                ctx.strokeRect(box.x, box.y, box.width, box.height)
                ctx.fillStyle = color
                ctx.fillRect(box.x, box.y - 20, 80, 20)
                ctx.fillStyle = 'white'
                ctx.font = '12px sans-serif'
                ctx.fillText(`${box.label || 'pest'} ${((box.conf || 0) * 100).toFixed(0)}%`, box.x + 4, box.y - 6)
            })
        }
        img.src = imageUrl
    }, [imageUrl, boxes])

    if (!boxes?.length) return (
        <img src={imageUrl} alt="analyzed" className="w-full max-h-64 object-contain rounded-lg" />
    )

    return (
        <canvas ref={canvasRef} style={{ maxWidth: '100%', borderRadius: '0.5rem' }} />
    )
}

// ── Pest info panel ───────────────────────────────────────────────────────────
const PEST_INFO = {
    'aphid': {
        commonName: 'Aphids',
        scientificName: 'Aphididae spp.',
        cropsAffected: ['Wheat', 'Cotton', 'Vegetables', 'Fruits'],
        damageSymptoms: ['Curled or distorted leaves', 'Sticky honeydew secretion', 'Sooty mold growth', 'Stunted plant growth'],
        prevention: ['Encourage natural predators like ladybugs', 'Use reflective mulches', 'Avoid excessive nitrogen fertilization', 'Inspect transplants before planting'],
        ipm: ['Use insecticidal soaps or neem oil', 'Introduce predatory insects', 'Water sprays to dislodge colonies'],
        monitoring: ['Check undersides of leaves weekly', 'Monitor for ant activity (ants protect aphids)', 'Use sticky traps'],
    },
    'whitefly': {
        commonName: 'Whiteflies',
        scientificName: 'Trialeurodes vaporariorum',
        cropsAffected: ['Tomato', 'Cotton', 'Eggplant', 'Cucumber'],
        damageSymptoms: ['Yellow mottled leaves', 'Wilting', 'Sooty mold', 'Virus transmission'],
        prevention: ['Use yellow sticky traps', 'Reflective mulch', 'Screen openings in greenhouses', 'Remove weeds near crops'],
        ipm: ['Neem-based products', 'Insect growth regulators', 'Biological control with Encarsia wasps'],
        monitoring: ['Check undersides of leaves', 'Count adults on yellow sticky traps weekly'],
    },
    'thrips': {
        commonName: 'Thrips',
        scientificName: 'Thrips tabaci',
        cropsAffected: ['Onion', 'Cotton', 'Bean', 'Cucumber'],
        damageSymptoms: ['Silver streaking or stippling on leaves', 'Leaf tip damage', 'Deformed flowers and fruit'],
        prevention: ['Remove crop debris', 'Use reflective mulches', 'Avoid planting next to infested fields'],
        ipm: ['Spinosad-based insecticides', 'Introduce predatory mites', 'Blue sticky traps for monitoring'],
        monitoring: ['Tap plant onto white paper', 'Check flowers regularly'],
    },
}

const PestInfoPanel = ({ pestClass, t, isDark }) => {
    const key = pestClass?.toLowerCase().split('_').find(k => PEST_INFO[k]) || Object.keys(PEST_INFO).find(k => pestClass?.toLowerCase().includes(k))
    const info = key ? PEST_INFO[key] : null
    if (!info) return null

    return (
        <Card>
            <div className="p-5">
                <h3 className="font-semibold text-base mb-4 flex items-center gap-2">
                    <Bug className="w-4 h-4 text-orange-500" /> {t('pest.pestInfo')}
                </h3>
                <div className="space-y-1 mb-4">
                    <div className="flex items-center gap-2 text-sm">
                        <span className="text-gray-500 dark:text-gray-400">{t('pest.commonName')}:</span>
                        <span className="font-semibold">{info.commonName}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                        <span className="text-gray-500 dark:text-gray-400">{t('pest.scientificName')}:</span>
                        <span className="italic text-gray-600 dark:text-gray-300">{info.scientificName}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm flex-wrap">
                        <span className="text-gray-500 dark:text-gray-400">{t('pest.cropsAffected')}:</span>
                        <span>{info.cropsAffected.join(', ')}</span>
                    </div>
                </div>

                <div className="space-y-3">
                    {[
                        { key: 'damageSymptoms', label: t('pest.damageSymptoms'), color: 'text-red-500' },
                        { key: 'prevention', label: t('pest.prevention'), color: 'text-green-500' },
                        { key: 'ipm', label: t('pest.ipm'), color: 'text-blue-500' },
                        { key: 'monitoring', label: t('pest.monitoring'), color: 'text-purple-500' },
                    ].map(({ key, label, color }) => (
                        <div key={key}>
                            <p className={`text-xs font-semibold uppercase tracking-wide ${color} mb-1.5`}>{label}</p>
                            <ul className="space-y-1">
                                {info[key]?.map((item, i) => (
                                    <li key={i} className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-1.5">
                                        <span className="mt-1 w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-gray-600 flex-shrink-0" />
                                        {item}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>

                <div className="mt-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 text-xs text-amber-700 dark:text-amber-400">
                    <strong>Note:</strong> AI predictions are not a confirmed diagnosis. Do not apply chemicals solely based on AI output.
                </div>
            </div>
        </Card>
    )
}

// ── Model Unavailable ─────────────────────────────────────────────────────────
const ModelUnavailableBanner = ({ t, isDark }) => (
    <div className={`rounded-xl border p-5 flex items-start gap-4 ${isDark ? 'bg-amber-900/10 border-amber-800' : 'bg-amber-50 border-amber-200'}`}>
        <AlertTriangle className="w-6 h-6 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
            <p className="font-semibold text-amber-700 dark:text-amber-400">{t('pest.modelUnavailable')}</p>
            <p className="text-sm text-amber-600 dark:text-amber-500 mt-1">{t('pest.modelUnavailableMsg')}</p>
            <div className="mt-3 text-xs text-amber-600 dark:text-amber-500 space-y-1">
                <p className="font-semibold">Required to activate:</p>
                <ul className="space-y-0.5 ml-3">
                    <li>• Trained pest detection model (YOLO/SSD/custom classifier)</li>
                    <li>• Backend endpoint: POST /api/pest/predict</li>
                    <li>• Class labels file for pest categories</li>
                </ul>
            </div>
        </div>
    </div>
)

// ── History Table ─────────────────────────────────────────────────────────────
const PestHistoryTable = ({ records, onDelete, onView, loading, t, isDark }) => {
    if (loading) return (
        <div className="py-12 flex items-center justify-center text-gray-400">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" /> {t('loading')}
        </div>
    )
    if (!records?.length) return (
        <div className="py-12 flex flex-col items-center gap-2 text-gray-400">
            <Bug className="w-10 h-10 opacity-30" />
            <p className="text-sm">{t('pest.noHistory')}</p>
        </div>
    )
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className={`text-left text-xs font-semibold uppercase tracking-wide ${isDark ? 'text-gray-400' : 'text-gray-500'} border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                        <th className="px-4 py-3">{t('pest.scanId')}</th>
                        <th className="px-4 py-3">{t('pest.dateTime')}</th>
                        <th className="px-4 py-3">{t('pest.pestName')}</th>
                        <th className="px-4 py-3">{t('pest.confidence')}</th>
                        <th className="px-4 py-3">{t('pest.detectionCount')}</th>
                        <th className="px-4 py-3">{t('actions')}</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {records.map((rec) => (
                        <tr key={rec.scan_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                            <td className="px-4 py-3 font-mono text-xs text-gray-500">{rec.scan_id?.slice(0, 8)}...</td>
                            <td className="px-4 py-3 text-xs">{rec.created_at ? new Date(rec.created_at).toLocaleString() : '—'}</td>
                            <td className="px-4 py-3 text-xs max-w-32 truncate" title={rec.pest_class}>{rec.pest_class || '—'}</td>
                            <td className={`px-4 py-3 font-mono font-bold ${confColor(rec.confidence)}`}>
                                {rec.confidence != null ? `${(rec.confidence * 100).toFixed(0)}%` : '—'}
                            </td>
                            <td className="px-4 py-3">{rec.detection_count ?? '—'}</td>
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
const PestDetection = () => {
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
    const [selectedRecord, setSelectedRecord] = useState(null)

    // History data
    const { data: histData, loading: histLoading, refetch: refetchHistory } =
        useApiData(() => api.getPestHistory(100), [], { intervalMs: 0 })

    // Model status
    const { data: modelStatus } = useApiData(() => api.getPestStatus(), [], { intervalMs: 30000 })
    const modelAvailable = modelStatus?.available === true

    const records = histData?.records || []
    const filteredRecords = records.filter(r => {
        return !histSearch || r.pest_class?.toLowerCase().includes(histSearch.toLowerCase())
    })

    const totalScans = records.length
    const pestDetections = records.filter(r => r.pest_class && r.pest_class !== 'no_pest').length
    const cleanDetections = totalScans - pestDetections
    const thisWeek = records.filter(r => {
        if (!r.created_at) return false
        return Date.now() - new Date(r.created_at).getTime() < 7 * 24 * 60 * 60 * 1000
    }).length

    const handleFile = (file, error) => {
        if (error) { setUploadError(error); return }
        setUploadError(null)
        setImageFile(file)
        setImagePreview(URL.createObjectURL(file))
        setPrediction(null)
        setInferenceError(null)
    }

    const handleClear = () => {
        if (imagePreview) URL.revokeObjectURL(imagePreview)
        setImageFile(null); setImagePreview(null); setPrediction(null); setInferenceError(null); setUploadError(null)
    }

    const handleAnalyze = async () => {
        if (!imageFile) return
        setAnalyzing(true); setPrediction(null); setInferenceError(null)
        try {
            const fd = new FormData()
            fd.append('file', imageFile)
            const result = await api.predictPest(fd)
            setPrediction(result)
            refetchHistory()
            setActiveTab('results')
        } catch (err) {
            if (err.status === 503 || err.status === 404) {
                setInferenceError(t('pest.modelUnavailable'))
            } else {
                setInferenceError(t('pest.inferenceError'))
            }
        } finally {
            setAnalyzing(false)
        }
    }

    const handleDelete = async (scanId) => {
        if (!window.confirm(t('confirm') + '?')) return
        try {
            await api.deletePestRecord(scanId)
            refetchHistory()
            if (selectedRecord?.scan_id === scanId) setSelectedRecord(null)
        } catch { /* ignore */ }
    }

    const cardCls = `rounded-xl border shadow-sm ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`
    const inputCls = `w-full px-3 py-2 rounded-lg border text-sm ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'} focus:outline-none focus:ring-2 focus:ring-primary-500`
    const tabCls = (active) => `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${active ? 'bg-orange-500 text-white' : isDark ? 'hover:bg-gray-700 text-gray-400' : 'hover:bg-gray-100 text-gray-600'}`

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                    <h2 className="text-2xl font-bold flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center shadow-md">
                            <Bug className="w-5 h-5 text-white" />
                        </div>
                        {t('pest.title')}
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{t('pest.subtitle')}</p>
                </div>

                {modelStatus && (
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${modelAvailable
                        ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800'
                        : 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800'
                        }`}>
                        {modelAvailable ? '✅ Model Ready' : '⚠ Model Unavailable'}
                    </span>
                )}
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-2 flex-wrap">
                {[
                    { id: 'dashboard', label: t('pest.dashboard'), icon: BarChart3 },
                    { id: 'upload', label: t('pest.uploadAnalyze'), icon: UploadCloud },
                    { id: 'results', label: t('pest.results'), icon: Eye },
                    { id: 'history', label: t('pest.history'), icon: History },
                ].map(tab => {
                    const Icon = tab.icon
                    return (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={tabCls(activeTab === tab.id)}>
                            <span className="flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" />{tab.label}</span>
                        </button>
                    )
                })}
            </div>

            {/* ── DASHBOARD ───────────────────────────────────────────────────── */}
            {activeTab === 'dashboard' && (
                <div className="space-y-6">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <MetricCard icon={BarChart3} label={t('pest.totalScans')} value={totalScans} color="blue" />
                        <MetricCard icon={Bug} label={t('pest.pestDetections')} value={pestDetections} color="red" />
                        <MetricCard icon={CheckCircle2} label={t('pest.cleanDetections')} value={cleanDetections} color="green" />
                        <MetricCard icon={Clock} label={t('pest.detectionsThisWeek')} value={thisWeek} color="amber" />
                    </div>

                    <div className={`${cardCls} p-5`}>
                        <h3 className="font-semibold text-base mb-4 flex items-center gap-2">
                            <History className="w-4 h-4 text-orange-500" /> {t('pest.recentDetections')}
                        </h3>
                        {records.length === 0 ? (
                            <div className="py-8 flex flex-col items-center gap-2 text-gray-400">
                                <Bug className="w-10 h-10 opacity-30" />
                                <p className="text-sm">{t('pest.emptyState')}</p>
                            </div>
                        ) : (
                            <PestHistoryTable
                                records={records.slice(0, 5)}
                                onDelete={handleDelete}
                                onView={(r) => { setSelectedRecord(r); setActiveTab('results') }}
                                loading={false}
                                t={t}
                                isDark={isDark}
                            />
                        )}
                    </div>

                    {!modelAvailable && !(modelStatus === null) && <ModelUnavailableBanner t={t} isDark={isDark} />}
                </div>
            )}

            {/* ── UPLOAD ──────────────────────────────────────────────────────── */}
            {activeTab === 'upload' && (
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                    <div className="lg:col-span-3 space-y-4">
                        {!imagePreview ? (
                            <UploadZone onFile={handleFile} isDark={isDark} t={t} />
                        ) : (
                            <div className={`${cardCls} p-5`}>
                                <div className="relative">
                                    <img src={imagePreview} alt="preview" className="w-full max-h-80 object-contain rounded-lg" />
                                    <button onClick={handleClear} className="absolute top-2 right-2 p-1.5 bg-black/60 rounded-full text-white hover:bg-black/80 transition-colors">
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                                <div className="flex items-center gap-3 mt-4">
                                    <button
                                        onClick={handleAnalyze}
                                        disabled={analyzing}
                                        className="flex-1 py-2.5 rounded-lg bg-orange-500 hover:bg-orange-600 disabled:opacity-60 text-white font-semibold flex items-center justify-center gap-2 transition-colors"
                                    >
                                        {analyzing
                                            ? <><RefreshCw className="w-4 h-4 animate-spin" /> {t('pest.analyzing')}</>
                                            : <><Bug className="w-4 h-4" /> {t('pest.analyzeImage')}</>
                                        }
                                    </button>
                                    <button onClick={handleClear} className="px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium text-sm">
                                        {t('pest.clearImage')}
                                    </button>
                                </div>
                            </div>
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
                        <div className={`${cardCls} p-5`}>
                            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
                                <Info className="w-4 h-4 text-orange-500" /> How it works
                            </h3>
                            <ol className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                                <li className="flex items-start gap-2"><span className="w-5 h-5 rounded-full bg-orange-500 text-white text-xs flex items-center justify-center flex-shrink-0 font-bold">1</span>Upload a clear field or crop image</li>
                                <li className="flex items-start gap-2"><span className="w-5 h-5 rounded-full bg-orange-500 text-white text-xs flex items-center justify-center flex-shrink-0 font-bold">2</span>AI detects and classifies visible pests</li>
                                <li className="flex items-start gap-2"><span className="w-5 h-5 rounded-full bg-orange-500 text-white text-xs flex items-center justify-center flex-shrink-0 font-bold">3</span>Review pest info, count, and IPM recommendations</li>
                            </ol>
                        </div>
                    </div>
                </div>
            )}

            {/* ── RESULTS ─────────────────────────────────────────────────────── */}
            {activeTab === 'results' && (
                <div className="space-y-6">
                    {(() => {
                        const result = selectedRecord
                            ? {
                                pest_class: selectedRecord.pest_class,
                                confidence: selectedRecord.confidence,
                                detection_count: selectedRecord.detection_count,
                                alternatives: selectedRecord.alternatives,
                                created_at: selectedRecord.created_at,
                                model_version: selectedRecord.model_version,
                                bounding_boxes: selectedRecord.bounding_boxes,
                                image_url: selectedRecord.image_url,
                            }
                            : prediction

                        if (!result) {
                            return (
                                <div className="py-16 flex flex-col items-center gap-3 text-gray-400">
                                    <Bug className="w-12 h-12 opacity-20" />
                                    <p className="text-base font-medium">{t('pest.emptyState')}</p>
                                    <button onClick={() => setActiveTab('upload')} className="mt-2 px-4 py-2 rounded-lg bg-orange-500 text-white text-sm font-medium hover:bg-orange-600 transition-colors">
                                        {t('pest.uploadAnalyze')}
                                    </button>
                                </div>
                            )
                        }

                        const noPest = !result.pest_class || result.pest_class === 'no_pest'
                        const confidencePct = result.confidence != null
                            ? (result.confidence > 1 ? result.confidence : result.confidence * 100).toFixed(1)
                            : null

                        return (
                            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                                <div className="lg:col-span-3 space-y-4">
                                    <div className={`${cardCls} p-5`}>
                                        <div className="flex items-center gap-3 mb-4">
                                            <h3 className="font-semibold text-base flex-1">{t('pest.results')}</h3>
                                            {noPest ? (
                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 text-xs font-semibold">
                                                    <CheckCircle2 className="w-3 h-3" /> {t('pest.noPestFound')}
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 text-xs font-semibold">
                                                    <Bug className="w-3 h-3" /> {t('pest.pestAlert')}
                                                </span>
                                            )}
                                            {selectedRecord && (
                                                <button onClick={() => setSelectedRecord(null)} className="text-xs text-gray-400 hover:text-gray-600">Clear</button>
                                            )}
                                        </div>

                                        {/* Image with optional bounding boxes */}
                                        {result.image_url && (
                                            <div className="mb-4">
                                                {result.bounding_boxes?.length > 0 ? (
                                                    <>
                                                        <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
                                                            <Crosshair className="w-3 h-3" /> Bounding boxes shown
                                                        </div>
                                                        <BoundingBoxCanvas imageUrl={result.image_url} boxes={result.bounding_boxes} />
                                                    </>
                                                ) : (
                                                    <img src={result.image_url} alt="analyzed" className="w-full max-h-48 object-contain rounded-lg border border-gray-200 dark:border-gray-700" />
                                                )}
                                            </div>
                                        )}

                                        <div className="grid grid-cols-3 gap-3">
                                            <div className={`p-3 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
                                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{t('pest.pestClass')}</p>
                                                <p className="font-semibold text-sm truncate">{result.pest_class || '—'}</p>
                                            </div>
                                            <div className={`p-3 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
                                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{t('pest.confidence')}</p>
                                                <p className={`font-bold text-lg ${confColor(result.confidence)}`}>{confidencePct != null ? `${confidencePct}%` : '—'}</p>
                                            </div>
                                            <div className={`p-3 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
                                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{t('pest.detectedCount')}</p>
                                                <p className="font-bold text-lg">{result.detection_count ?? '—'}</p>
                                            </div>
                                        </div>

                                        {result.created_at && (
                                            <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
                                                <Clock className="w-3 h-3" />
                                                {new Date(result.created_at).toLocaleString()}
                                                {result.model_version && <span className="ml-auto">Model: {result.model_version}</span>}
                                            </div>
                                        )}
                                    </div>

                                    {result.alternatives?.length > 0 && (
                                        <div className={`${cardCls} p-5`}>
                                            <h4 className="font-semibold text-sm mb-3">{t('pest.alternativePredictions')}</h4>
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
                                        </div>
                                    )}
                                </div>

                                <div className="lg:col-span-2">
                                    <PestInfoPanel pestClass={result.pest_class} t={t} isDark={isDark} />
                                </div>
                            </div>
                        )
                    })()}
                </div>
            )}

            {/* ── HISTORY ─────────────────────────────────────────────────────── */}
            {activeTab === 'history' && (
                <div className="space-y-4">
                    <div className={`${cardCls} p-4`}>
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
                            <button onClick={refetchHistory} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                                <RefreshCw className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    <div className={cardCls}>
                        <div className="p-1">
                            <PestHistoryTable
                                records={filteredRecords}
                                onDelete={handleDelete}
                                onView={(r) => { setSelectedRecord(r); setActiveTab('results') }}
                                loading={histLoading}
                                t={t}
                                isDark={isDark}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default PestDetection
