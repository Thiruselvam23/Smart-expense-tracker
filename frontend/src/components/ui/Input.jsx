import { forwardRef } from 'react'
const Input = forwardRef(({ label, error, className = '', ...props }, ref) => (
  <div className="w-full">
    {label && <label className="label">{label}</label>}
    <input ref={ref} className={`input-field ${error ? 'border-red-400 focus:ring-red-400' : ''} ${className}`} {...props} />
    {error && <p className="error-text">{error}</p>}
  </div>
))
Input.displayName = 'Input'
export default Input
