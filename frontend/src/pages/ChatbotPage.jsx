import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Trash2 } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'

const SYSTEM_PROMPT = `You are an Expense Assistant. You ONLY answer questions related to:
- Expense management and tracking
- Budget planning and management
- Saving strategies and tips
- Spending analysis and patterns
- Financial habits improvement
- Expense categorization advice

If asked ANYTHING outside these topics (movies, sports, programming, politics, general knowledge, etc.), 
respond EXACTLY with: "I can't answer this question. I am only allowed to provide information related to expenses, budgeting, spending analysis, and financial planning."

Be concise, helpful, and practical. Use ₹ for currency examples when relevant.`

const WELCOME = {
  id: 'welcome',
  role: 'assistant',
  content: "Hi! I'm your Expense Assistant 👋\n\nI can help you with:\n• Budget planning\n• Spending analysis\n• Saving strategies\n• Expense categorization\n\nWhat would you like to know?",
  time: new Date(),
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${
        isUser ? 'bg-[#1E3A5F]' : 'bg-[#2E86AB]'
      }`}>
        {isUser ? <User size={15} className="text-white" /> : <Bot size={15} className="text-white" />}
      </div>

      {/* Bubble */}
      <div className={`max-w-[78%] rounded-2xl px-4 py-3 ${
        isUser
          ? 'bg-[#1E3A5F] text-white rounded-tr-sm'
          : 'rounded-tl-sm'
      }`} style={!isUser ? { background: 'var(--hover)', color: 'var(--text-primary)', border: '1px solid var(--border)' } : {}}>
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        <p className={`text-xs mt-1.5 ${isUser ? 'text-blue-200' : ''}`}
          style={!isUser ? { color: 'var(--text-muted)' } : {}}>
          {msg.time?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full bg-[#2E86AB] flex items-center justify-center flex-shrink-0">
        <Bot size={15} className="text-white" />
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-tl-sm"
        style={{ background: 'var(--hover)', border: '1px solid var(--border)' }}>
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map(i => (
            <div key={i} className="w-2 h-2 rounded-full bg-[#2E86AB] animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </div>
    </div>
  )
}

export default function ChatbotPage() {
  const { user } = useAuth()
  const [messages, setMessages] = useState([WELCOME])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { id: Date.now(), role: 'user', content: text, time: new Date() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      // Build conversation history for context (last 10 messages)
      const history = messages
        .filter(m => m.id !== 'welcome')
        .slice(-10)
        .map(m => ({ role: m.role, content: m.content }))

      history.push({ role: 'user', content: text })

      const { data } = await client.post('/api/chatbot', {
        messages: history,
        system: SYSTEM_PROMPT,
      })

      const botMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        time: new Date(),
      }
      setMessages(prev => [...prev, botMsg])
    } catch (e) {
      const errMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        time: new Date(),
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const clearChat = () => setMessages([WELCOME])

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const suggestions = [
    'How can I reduce my food expenses?',
    'Create a monthly budget plan for ₹30,000',
    'Tips to save money on daily expenses',
    'How to categorize my expenses better?',
  ]

  return (
    <div className="max-w-3xl mx-auto flex flex-col" style={{ height: 'calc(100vh - 120px)' }}>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="page-title">Expense Assistant</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Ask me anything about budgeting, saving, or expense management
          </p>
        </div>
        <button onClick={clearChat}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors"
          style={{ color: 'var(--text-muted)', background: 'var(--hover)' }}
          title="Clear chat">
          <Trash2 size={14} /> Clear
        </button>
      </div>

      {/* Chat window */}
      <div className="card flex-1 overflow-y-auto space-y-4 p-5 mb-3">
        {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions (only shown at start) */}
      {messages.length <= 1 && (
        <div className="flex gap-2 flex-wrap mb-3">
          {suggestions.map(s => (
            <button key={s} onClick={() => { setInput(s); inputRef.current?.focus() }}
              className="text-xs px-3 py-1.5 rounded-full border transition-colors hover:border-[#2E86AB] hover:text-[#2E86AB]"
              style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)', background: 'var(--bg-card)' }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="card p-3 flex gap-3 items-end">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about budgeting, saving strategies, expense tips..."
          rows={1}
          className="flex-1 resize-none text-sm focus:outline-none bg-transparent leading-relaxed"
          style={{ color: 'var(--text-primary)', maxHeight: 120, minHeight: 36 }}
          onInput={e => {
            e.target.style.height = 'auto'
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
          }}
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim() || loading}
          className="w-9 h-9 rounded-xl flex items-center justify-center transition-all disabled:opacity-40 flex-shrink-0"
          style={{ background: input.trim() && !loading ? '#1E3A5F' : 'var(--border)' }}
        >
          <Send size={16} className="text-white" />
        </button>
      </div>

      <p className="text-xs text-center mt-2" style={{ color: 'var(--text-muted)' }}>
        Press Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}
