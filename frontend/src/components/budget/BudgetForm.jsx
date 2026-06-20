import { useForm } from 'react-hook-form'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Button from '../ui/Button'
import { CATEGORIES, MONTHS } from '../../constants'

export default function BudgetForm({ defaultValues, onSubmit, loading }) {
  const now = new Date()
  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: defaultValues || {
      month: now.getMonth() + 1, year: now.getFullYear(), total_budget: '',
      ...Object.fromEntries(CATEGORIES.map(c => [`cat_${c}`, ''])),
    },
  })

  const submit = (data) => {
    const category_budgets = {}
    CATEGORIES.forEach(c => { category_budgets[c] = parseFloat(data[`cat_${c}`] || 0) })
    onSubmit({ month: parseInt(data.month), year: parseInt(data.year), total_budget: parseFloat(data.total_budget), category_budgets })
  }

  const months = MONTHS.map((m, i) => ({ value: i + 1, label: m }))
  const years = [2024, 2025, 2026].map(y => ({ value: y, label: y }))

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Select label="Month" options={months} {...register('month')} />
        <Select label="Year" options={years} {...register('year')} />
      </div>
      <Input label="Total Monthly Budget (₹) *" type="number" step="0.01" placeholder="15000"
        error={errors.total_budget?.message} {...register('total_budget', { required: 'Required' })} />
      <div>
        <p className="label mb-2">Category Budgets (₹)</p>
        <div className="grid grid-cols-2 gap-3">
          {CATEGORIES.map(cat => (
            <Input key={cat} label={cat} type="number" step="0.01" placeholder="0"
              {...register(`cat_${cat}`)} />
          ))}
        </div>
      </div>
      <Button type="submit" loading={loading} className="w-full">Save Budget</Button>
    </form>
  )
}
