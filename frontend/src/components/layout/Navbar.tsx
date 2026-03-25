import { Link, useLocation } from 'react-router-dom'

const links = [
  { to: '/', label: 'Directory' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/search', label: 'Search' },
  { to: '/download', label: 'Download' },
]

export function Navbar() {
  const { pathname } = useLocation()
  return (
    <nav className="border-b bg-white px-6 py-3 flex items-center gap-6 shadow-sm sticky top-0 z-10">
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
              : 'text-gray-600 hover:text-blue-700'
          }`}
        >
          {l.label}
        </Link>
      ))}
    </nav>
  )
}
