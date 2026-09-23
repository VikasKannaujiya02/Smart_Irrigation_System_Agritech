import React, { useState } from 'react'
import { DarkModeProvider } from './context/DarkModeContext'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Dashboard from './components/Dashboard'
import Sensors from './components/Sensors'
import PumpStatus from './components/PumpStatus'
import WeatherWidget from './components/WeatherWidget'
import AIPrediction from './components/AIPrediction'
import DigitalTwin from './components/DigitalTwin'
import Analytics from './components/Analytics'
import WaterSaving from './components/WaterSaving'
import NPK from './components/NPK'
import CropRecommendation from './components/CropRecommendation'
import CropLifecycle from './components/CropLifecycle'
import Alerts from './components/Alerts'
import History from './components/History'
import Config from './components/Config'
import PlantDisease from './components/PlantDisease'
import PestDetection from './components/PestDetection'

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard />
      case 'sensors': return <Sensors />
      case 'pump': return (
        <div className="max-w-md mx-auto">
          <h2 className="text-2xl font-bold mb-6">Pump Control</h2>
          <PumpStatus />
        </div>
      )
      case 'weather': return (
        <div className="max-w-md mx-auto">
          <h2 className="text-2xl font-bold mb-6">Weather</h2>
          <WeatherWidget />
        </div>
      )
      case 'ai': return <AIPrediction />
      case 'digital-twin': return <DigitalTwin />
      case 'analytics': return <Analytics />
      case 'water-saving': return <WaterSaving />
      case 'npk': return <NPK />
      case 'crop-recommendation': return <CropRecommendation />
      case 'crop-lifecycle': return <CropLifecycle />
      case 'alerts': return <Alerts />
      case 'history': return <History />
      case 'config': return <Config />
      case 'plant-disease': return <PlantDisease />
      case 'pest-detection': return <PestDetection />
      default: return <Dashboard />
    }
  }

  return (
    <DarkModeProvider>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex">
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          isMobileOpen={isMobileOpen}
          setIsMobileOpen={setIsMobileOpen}
        />
        <div className="flex-1 flex flex-col min-w-0">
          <Header setIsMobileOpen={setIsMobileOpen} />
          <main className="p-6 flex-1 overflow-auto">
            {renderContent()}
          </main>
        </div>
      </div>
    </DarkModeProvider>
  )
}

export default App
