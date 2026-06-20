import { useState, useEffect } from 'react'
import Select from '../ui/Select'
import Button from '../ui/Button'
import { CATEGORIES } from '../../constants'
import { Search, X } from 'lucide-react'

const EMPTY = { search: '', category: '', start_date: '', end_date: '' }

export default function ExpenseFilters({ filters, onChange }) {
  // Local state is always a FULL copy — never inherits stale parent state on reset
  const [local, setLocal] = useState({ ...EMPTY, ...filters })

  // Sync if parent resets externally
  useEffect(() => {
    setLocal({ ...EMPTY, ...filters })
  }, [JSON.stringify(filters)])

  const set = (key, val) => setLocal(p => ({ ...p, [key]: val }))

  const apply = () => onChange({ ...local })

  // Reset: wipe local state completely, then notify parent with EMPTY object
  const reset = () => {
    setLocal({ ...EMPTY })
    onChange({ ...EMPTY })
  }

  return (
    <div className="card mb-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        {/* Search */}
        <div className="relative sm:col-span-2 md:col-span-1">
          <input
            className="input-field pr-8"
            placeholder="Search expenses..."
            value={local.search}
            onChange={e => set('search', e.target.value)}
            onKeyDown={e => e.key === 'Enter' && apply()}
          />
          <Search size={14} className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
        </div>

        {/* Category */}
        <select
          className="input-field"
          value={local.category}
          onChange={e => set('category', e.target.value)}
        >
          <option value="">All Categories</option>
          {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        {/* Date From */}
        <input
          type="date"
          className="input-field"
          value={local.start_date}
          onChange={e => set('start_date', e.target.value)}
        />

        {/* Date To */}
        <input
          type="date"
          className="input-field"
          value={local.end_date}
          onChange={e => set('end_date', e.target.value)}
        />
      </div>

      <div className="flex gap-2 mt-3">
        <Button size="sm" onClick={apply}>
          <Search size={13} /> Apply
        </Button>
        <Button size="sm" variant="ghost" onClick={reset}>
          <X size={13} /> Reset All
        </Button>
      </div>
    </div>
  )
}
