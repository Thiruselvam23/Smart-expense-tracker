import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Button from '../ui/Button'
import { CATEGORIES, PAYMENT_METHODS } from '../../constants'

const schema = z.object({
  title:          z.string().min(1, 'Title is required'),
  amount:         z.coerce.number().positive('Amount must be greater than 0'),
  category:       z.string().min(1, 'Category is required'),
  date:           z.string().min(1, 'Date is required'),
  description:    z.string().optional(),
  payment_method: z.string().optional(),
  tags:           z.string().optional(),
})

export default function ExpenseForm({ defaultValues, onSubmit, loading }) {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: defaultValues || { date: new Date().toISOString().split('T')[0], payment_method: 'Cash' },
  })

  const submit = (data) => {
    const payload = {
      ...data,
      amount: parseFloat(data.amount),
      tags: data.tags ? data.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
    }
    onSubmit(payload)
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4">
      <Input label="Title *" placeholder="e.g. Swiggy dinner" error={errors.title?.message} {...register('title')} />
      <div className="grid grid-cols-2 gap-4">
        <Input label="Amount (₹) *" type="number" step="0.01" placeholder="0.00" error={errors.amount?.message} {...register('amount')} />
        <Input label="Date *" type="date" error={errors.date?.message} {...register('date')} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Select label="Category *" placeholder="Select category" error={errors.category?.message}
          options={CATEGORIES.map(c => ({ value: c, label: c }))} {...register('category')} />
        <Select label="Payment Method" placeholder="Select method"
          options={PAYMENT_METHODS.map(m => ({ value: m, label: m }))} {...register('payment_method')} />
      </div>
      <Input label="Description" placeholder="Optional note" {...register('description')} />
      <Input label="Tags (comma-separated)" placeholder="food, delivery, dinner" {...register('tags')} />
      <Button type="submit" loading={loading} className="w-full">Save Expense</Button>
    </form>
  )
}
