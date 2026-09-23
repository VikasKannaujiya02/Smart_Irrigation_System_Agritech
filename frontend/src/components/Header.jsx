import React, { useState, useRef, useEffect } from 'react'
import { Sun, Moon, Menu, Bell, User, Settings, Shield, ChevronDown, CheckCircle, Globe } from 'lucide-react'
import { useDarkMode } from '../context/DarkModeContext'
import { api } from '../api'
import useApiData from '../hooks/useApiData'
import { useTranslation } from 'react-i18next'

// ── Click-outside hook ─────────────────────────────────────────────────────────
const useClickOutside = (refs, handler) => {
  useEffect(() => {
    const listener = (e) => {
      if (refs.every(r => r.current && !r.current.contains(e.target))) {
        handler()
      }
    }
    document.addEventListener('mousedown', listener)
    return () => document.removeEventListener('mousedown', listener)
  }, [refs, handler])
}

// ── Alert severity colour ──────────────────────────────────────────────────────
const SEVERITY_COLOR = {
  critical: 'text-red-500',
  high: 'text-orange-500',
  medium: 'text-amber-500',
  low: 'text-blue-500',
  info: 'text-gray-400',
}

const Header = ({ setIsMobileOpen }) => {
  const { isDark, toggleDarkMode } = useDarkMode()
  const { t, i18n } = useTranslation()

  // Alerts
  const { data: alertsData, refetch: refetchAlerts } = useApiData(() => api.getAlerts(20), [], { intervalMs: 10000 })
  const activeAlerts = alertsData?.active || []
  const hasActiveAlerts = activeAlerts.length > 0

  // Panel state
  const [notifOpen, setNotifOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [langOpen, setLangOpen] = useState(false)

  const notifRef = useRef(null)
  const profileRef = useRef(null)
  const langRef = useRef(null)

  useClickOutside(
    [notifRef, profileRef, langRef],
    () => { setNotifOpen(false); setProfileOpen(false); setLangOpen(false) }
  )

  const handleResolve = async (alertId) => {
    try {
      await api.resolveAlert(alertId)
      refetchAlerts()
    } catch (e) { /* ignore */ }
  }

  const switchLanguage = (lang) => {
    i18n.changeLanguage(lang)
    localStorage.setItem('language', lang)
    setLangOpen(false)
  }

  const currentLang = i18n.language || 'en'

  const panel = `absolute right-0 mt-2 rounded-xl shadow-2xl border z-50 ${isDark ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-gray-200 text-gray-900'
    }`

  return (
    <header className={`sticky top-0 z-30 px-6 py-3 border-b ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      } shadow-sm`}>
      <div className="flex items-center justify-between">
        {/* Left: hamburger + title */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsMobileOpen(prev => !prev)}
            className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Menu className="w-5 h-5" />
          </button>
          <h2 className="text-lg font-semibold hidden sm:block">{t('header.title')}</h2>
        </div>

        {/* Right: actions */}
        <div className="flex items-center gap-2">

          {/* ── Language Toggle ───────────────────────────────────── */}
          <div className="relative" ref={langRef}>
            <button
              onClick={() => { setLangOpen(v => !v); setNotifOpen(false); setProfileOpen(false) }}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm font-medium"
              title={t('header.language')}
            >
              <Globe className="w-4 h-4" />
              <span className="hidden sm:inline">{currentLang === 'hi' ? 'हिंदी' : 'EN'}</span>
              <ChevronDown className={`w-3 h-3 transition-transform ${langOpen ? 'rotate-180' : ''}`} />
            </button>

            {langOpen && (
              <div className={`${panel} w-36`} style={{ top: '100%' }}>
                <div className="py-1">
                  <button
                    onClick={() => switchLanguage('en')}
                    className={`w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${currentLang === 'en' ? 'text-primary-600 font-semibold' : ''}`}
                  >
                    {currentLang === 'en' && <span className="w-2 h-2 rounded-full bg-primary-500 flex-shrink-0" />}
                    {currentLang !== 'en' && <span className="w-2 h-2 flex-shrink-0" />}
                    English
                  </button>
                  <button
                    onClick={() => switchLanguage('hi')}
                    className={`w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${currentLang === 'hi' ? 'text-primary-600 font-semibold' : ''}`}
                  >
                    {currentLang === 'hi' && <span className="w-2 h-2 rounded-full bg-primary-500 flex-shrink-0" />}
                    {currentLang !== 'hi' && <span className="w-2 h-2 flex-shrink-0" />}
                    हिंदी
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Dark mode */}
          <button
            onClick={toggleDarkMode}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title={isDark ? t('header.lightMode') : t('header.darkMode')}
          >
            {isDark ? <Sun className="w-5 h-5 text-yellow-400" /> : <Moon className="w-5 h-5 text-gray-600" />}
          </button>

          {/* ── Notification bell ───────────────────────────────── */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => { setNotifOpen(v => !v); setProfileOpen(false); setLangOpen(false) }}
              className="relative p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title={t('header.notifications')}
            >
              <Bell className="w-5 h-5" />
              {hasActiveAlerts && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white dark:ring-gray-800 animate-pulse" />
              )}
            </button>

            {notifOpen && (
              <div className={`${panel} w-80 sm:w-96`} style={{ top: '100%' }}>
                <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
                  <h3 className="font-semibold text-sm">{t('header.notifications')}</h3>
                  {hasActiveAlerts && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 font-semibold">
                      {activeAlerts.length} {t('header.active')}
                    </span>
                  )}
                </div>

                <div className="max-h-80 overflow-y-auto">
                  {activeAlerts.length === 0 ? (
                    <div className="flex flex-col items-center gap-2 py-8 text-gray-400">
                      <CheckCircle className="w-8 h-8 text-green-400" />
                      <p className="text-sm">{t('header.noAlerts')}</p>
                    </div>
                  ) : (
                    activeAlerts.map(alert => (
                      <div key={alert.alert_id}
                        className={`px-4 py-3 border-b border-gray-50 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors`}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5 mb-0.5">
                              <span className={`text-xs font-bold uppercase ${SEVERITY_COLOR[alert.level] ?? 'text-gray-400'}`}>
                                {alert.level}
                              </span>
                              <span className="text-xs text-gray-400">·</span>
                              <span className="text-xs text-gray-400 truncate">{alert.type}</span>
                            </div>
                            <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed line-clamp-2">{alert.message}</p>
                            <p className="text-xs text-gray-400 mt-1">
                              {alert.timestamp ? new Date(alert.timestamp).toLocaleString() : ''}
                            </p>
                          </div>
                          <button
                            onClick={() => handleResolve(alert.alert_id)}
                            className="shrink-0 text-xs px-2 py-1 rounded-lg bg-green-50 hover:bg-green-100 text-green-700 dark:bg-green-900/20 dark:hover:bg-green-900/40 dark:text-green-300 transition-colors font-medium"
                          >
                            {t('header.resolve')}
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {activeAlerts.length > 0 && (
                  <div className="px-4 py-2 border-t border-gray-100 dark:border-gray-700">
                    <a href="#/alerts" onClick={() => setNotifOpen(false)}
                      className="text-xs text-indigo-500 hover:underline">
                      {t('header.viewAllAlerts')}
                    </a>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ── Profile avatar ──────────────────────────────────── */}
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => { setProfileOpen(v => !v); setNotifOpen(false); setLangOpen(false) }}
              className="flex items-center gap-2 p-1 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title={t('header.profile')}
            >
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shadow-md">
                AD
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform ${profileOpen ? 'rotate-180' : ''}`} />
            </button>

            {profileOpen && (
              <div className={`${panel} w-56`} style={{ top: '100%' }}>
                {/* User info */}
                <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold">
                      AD
                    </div>
                    <div>
                      <p className="text-sm font-semibold">{t('header.admin')}</p>
                      <p className="text-xs text-gray-400">{t('header.systemAdmin')}</p>
                    </div>
                  </div>
                </div>

                {/* Menu items */}
                <div className="py-1">
                  <ProfileItem icon={User} label={t('header.profile')} />
                  <ProfileItem icon={Shield} label="System Role: Admin" muted />
                  <ProfileItem
                    icon={Settings}
                    label={t('header.configuration')}
                    onClick={() => {
                      setProfileOpen(false)
                      window.location.hash = '#/config'
                    }}
                  />
                </div>

                <div className="border-t border-gray-100 dark:border-gray-700 py-1">
                  <button
                    onClick={() => { setProfileOpen(false); toggleDarkMode() }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-left">
                    {isDark ? <Sun className="w-4 h-4 text-yellow-400" /> : <Moon className="w-4 h-4 text-gray-500" />}
                    {isDark ? t('header.lightMode') : t('header.darkMode')}
                  </button>
                </div>

                {/* Version */}
                <div className="px-4 py-2 border-t border-gray-100 dark:border-gray-700">
                  <p className="text-xs text-gray-400">{t('header.version')}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

const ProfileItem = ({ icon: Icon, label, muted, onClick }) => (
  <button
    className={`w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors text-left ${muted
      ? 'text-gray-400 cursor-default'
      : 'hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
      }`}
    onClick={onClick ?? undefined}
  >
    <Icon className="w-4 h-4" />
    {label}
  </button>
)

export default Header
