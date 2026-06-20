export default function Button({ children, variant = 'primary', size = 'md', loading, className = '', ...props }) {
  const base = 'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  const variants = {
    primary:   'bg-[#1E3A5F] text-white hover:bg-[#152B47]',
    secondary: 'border border-[#1E3A5F] text-[#1E3A5F] hover:opacity-80',
    danger:    'bg-red-600 text-white hover:bg-red-700',
    ghost:     'hover:opacity-70',
  }
  const styles = {
    secondary: { background: 'var(--bg-card)' },
    ghost:     { color: 'var(--text-secondary)' },
  }
  const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-6 py-3 text-base' }
  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      style={styles[variant] || {}}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading && <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />}
      {children}
    </button>
  )
}
