import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/layout/Layout'
import { ETFDirectory } from './pages/ETFDirectory'
import { ETFDetail } from './pages/ETFDetail'
import { CompositionHistory } from './pages/CompositionHistory'
import { RebalancingAlerts } from './pages/RebalancingAlerts'
import { CrossETFSearch } from './pages/CrossETFSearch'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<ETFDirectory />} />
            <Route path="/etfs/:ticker" element={<ETFDetail />} />
            <Route path="/etfs/:ticker/history" element={<CompositionHistory />} />
            <Route path="/alerts" element={<RebalancingAlerts />} />
            <Route path="/search" element={<CrossETFSearch />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
