import React from 'react'
import {
  Droplets, Wind, Thermometer, Activity, Cpu, BarChart3,
  Tractor, AlertTriangle, Settings, History, Gauge, Sprout,
  Leaf, Bug
} from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { useTranslation } from 'react-i18next'

const Sidebar = ({ activeTab, setActiveTab, isMobileOpen, setIsMobileOpen }) => {
  const { isDark } = useDarkMode()
  const { t } = useTranslation()

  const menuItems = [
    { id: 'dashboard', labelKey: 'nav.dashboard', icon: Activity },
    { id: 'sensors', labelKey: 'nav.sensors', icon: Thermometer },
    { id: 'pump', labelKey: 'nav.pump', icon: Gauge },
    { id: 'weather', labelKey: 'nav.weather', icon: Wind },
    { id: 'ai', labelKey: 'nav.aiPrediction', icon: Cpu },
    { id: 'digital-twin', labelKey: 'nav.digitalTwin', icon: Tractor },
    { id: 'analytics', labelKey: 'nav.analytics', icon: BarChart3 },
    { id: 'water-saving', labelKey: 'nav.waterSaving', icon: Droplets },
    { id: 'npk', labelKey: 'nav.npk', icon: Wind },
    { id: 'crop-recommendation', labelKey: 'nav.cropRecommendation', icon: Tractor },
    { id: 'crop-lifecycle', labelKey: 'nav.cropLifecycle', icon: Sprout },
    { id: 'alerts', labelKey: 'nav.alerts', icon: AlertTriangle },
    { id: 'history', labelKey: 'nav.history', icon: History },
    { id: 'config', labelKey: 'nav.config', icon: Settings },
    // ── AI Image Modules (top-level, same as every other section) ──
    { id: 'plant-disease', labelKey: 'nav.plantDisease', icon: Leaf },
    { id: 'pest-detection', labelKey: 'nav.pestDetection', icon: Bug },
  ]

  const handleTabChange = (id) => {
    setActiveTab(id)
    setIsMobileOpen(false)
  }

  const btnCls = (isActive) =>
    `w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all text-sm font-medium ${isActive
      ? 'bg-primary-500 text-white shadow-sm'
      : isDark
        ? 'hover:bg-gray-800 text-gray-300'
        : 'hover:bg-gray-100 text-gray-700'
    }`

  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      <aside
        className={`fixed lg:static top-0 left-0 z-50 h-full flex flex-col transform transition-transform duration-300
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          ${isDark ? 'bg-gray-900 text-white' : 'bg-white text-gray-800'}
          border-r ${isDark ? 'border-gray-800' : 'border-gray-200'}`}
        style={{ width: '15rem', minWidth: '15rem' }}
      >
        {/* Logo */}
        <div className="p-5 border-b border-gray-700/30 flex-shrink-0">
          <h1 className="text-lg font-bold flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-400 to-emerald-600 flex items-center justify-center shadow-md">
              <Droplets className="w-4 h-4 text-white" />
            </div>
            <span className="leading-tight">
              <span className="text-primary-500">AI</span> Irrigation DT
            </span>
          </h1>
        </div>

        {/* Navigation — scrollable */}
        <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-0.5">
          {menuItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.id}
                onClick={() => handleTabChange(item.id)}
                className={btnCls(activeTab === item.id)}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span className="truncate">{t(item.labelKey)}</span>
              </button>
            )
          })}
        </nav>

        {/* Footer */}
        <div className={`px-4 py-3 border-t flex-shrink-0 ${isDark ? 'border-gray-800' : 'border-gray-200'}`}>
          <p className="text-xs text-gray-400">AI Irrigation DT v1.0.0</p>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
