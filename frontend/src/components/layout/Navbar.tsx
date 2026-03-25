import { Link, useLocation } from 'react-router-dom'
import { useThemeContext, type Theme } from '../../context/ThemeContext'

const links = [
  { to: '/', label: 'Directory' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/search', label: 'Search' },
  { to: '/download', label: 'Download' },
]

function SunIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
    </svg>
  )
}

function MonitorIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  )
}

const THEME_BUTTONS: { id: Theme; title: string; icon: React.ReactNode }[] = [
  { id: 'light',  title: 'Light',  icon: <SunIcon /> },
  { id: 'system', title: 'System', icon: <MonitorIcon /> },
  { id: 'dark',   title: 'Dark',   icon: <MoonIcon /> },
]

export function Navbar() {
  const { pathname } = useLocation()
  const { theme, setTheme } = useThemeContext()

  return (
    <nav className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-6 py-3 flex items-center gap-6 shadow-sm sticky top-0 z-10">
      <Link to="/" className="font-bold text-blue-700 text-lg tracking-tight mr-4">
        SSGA ETF Tracker
      </Link>
      {links.map(l => (
        <Link
          key={l.to}
          to={l.to}
          className={`text-sm font-medium ${
            pathname === l.to
              ? 'text-blue-700 border-b-2 border-blue-700 pb-0.5'
              : 'text-gray-600 dark:text-gray-400 hover:text-blue-700 dark:hover:text-blue-400'
          }`}
        >
          {l.label}
        </Link>
      ))}

      {/* Theme toggle */}
      <div className="ml-auto flex items-center gap-0.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-0.5">
        {THEME_BUTTONS.map(({ id, title, icon }) => (
          <button
            key={id}
            title={title}
            onClick={() => setTheme(id)}
            className={`p-1.5 rounded-md transition-colors ${
              theme === id
                ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-300 shadow-sm'
                : 'text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            {icon}
          </button>
        ))}
      </div>
    </nav>
  )
}
