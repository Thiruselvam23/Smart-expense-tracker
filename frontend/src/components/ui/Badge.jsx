import { CATEGORY_COLORS } from '../../constants'
export default function Badge({ label, type = 'category' }) {
  if (type === 'category') {
    const color = CATEGORY_COLORS[label] || '#C8D6E5'
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-white"
        style={{ backgroundColor: color }}>{label}</span>
    )
  }
  return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
    style={{ background: 'var(--hover)', color: 'var(--text-secondary)' }}>{label}</span>
}
