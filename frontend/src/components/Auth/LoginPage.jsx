import { useEffect, useState } from 'react'
import { Eye, EyeOff, LockKeyhole, ShieldCheck } from 'lucide-react'
import { login } from '../../services/api'

const descriptions = [
  'Bring approved Bank of Tanzania research documents together in one secure workspace, ready for discovery and review.',
  'Find relevant institutional research by meaning and context, helping you move beyond keyword-only document searches.',
  'Ask research questions and receive AI-assisted responses grounded in the institution\'s processed documents and source excerpts.',
  'Turn processed research documents into focused summaries that make important findings easier to review and share.',
  'Explore a growing institutional knowledge base built from real economic research, policy reports, and working papers.',
]

const LoginPage = ({ onAuthenticated }) => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [descriptionIndex, setDescriptionIndex] = useState(0)
  const [typedDescription, setTypedDescription] = useState('')
  const [deletingDescription, setDeletingDescription] = useState(false)

  useEffect(() => {
    const currentDescription = descriptions[descriptionIndex]
    const delay = deletingDescription ? 24 : typedDescription.length === currentDescription.length ? 10000 : 62
    const timer = window.setTimeout(() => {
      if (!deletingDescription && typedDescription.length < currentDescription.length) {
        setTypedDescription(currentDescription.slice(0, typedDescription.length + 1))
      } else if (!deletingDescription) {
        setDeletingDescription(true)
      } else if (typedDescription.length > 0) {
        setTypedDescription(currentDescription.slice(0, typedDescription.length - 1))
      } else {
        setDescriptionIndex((index) => (index + 1) % descriptions.length)
        setDeletingDescription(false)
      }
    }, delay)
    return () => window.clearTimeout(timer)
  }, [descriptionIndex, typedDescription, deletingDescription])

  const submit = async (event) => {
    event.preventDefault()
    if (!username.trim() || !password) {
      setError('Enter your username or email and password to continue.')
      return
    }

    try {
      setSubmitting(true)
      setError('')
      const authenticatedUser = await login(username.trim(), password)
      await onAuthenticated({
        id: authenticatedUser.user_id,
        username: authenticatedUser.username,
        email: authenticatedUser.email,
        full_name: authenticatedUser.full_name,
        role: authenticatedUser.role,
        is_active: authenticatedUser.is_active,
        is_verified: authenticatedUser.is_verified,
        created_at: authenticatedUser.created_at,
        last_login: authenticatedUser.last_login,
      })
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Sign in failed. Check your credentials and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page min-h-screen overflow-hidden bg-[#0d0d0d] text-white">
      <div className="grid min-h-screen lg:grid-cols-[minmax(0,0.9fr)_minmax(480px,1.1fr)]">
        <section className="login-brand-panel relative flex min-h-[430px] flex-col justify-center overflow-hidden px-7 py-12 sm:px-12 lg:min-h-screen lg:px-[9%]">
          <div className="login-pattern absolute inset-0 opacity-70" aria-hidden="true" />
          <div className="relative z-10 max-w-[430px]">
            <img src="/bot-logo.svg" alt="Bank of Tanzania" className="mb-8 h-28 w-28 object-contain drop-shadow-[0_0_18px_rgba(209,177,95,0.4)]" />
            <p className="mb-3 text-sm font-semibold uppercase tracking-[0.12em] text-[#d5b15e]">Bank of Tanzania</p>
            <h1 className="max-w-[390px] text-4xl font-extrabold uppercase leading-[1.08] tracking-tight sm:text-5xl">AI Research Knowledge Hub</h1>
            <div className="my-7 h-px w-16 bg-[#d5b15e]" />
            <p className="login-description text-base leading-8 sm:text-lg">{typedDescription}</p>
          </div>
        </section>

        <section className="login-form-panel flex items-center justify-center bg-[#e9edf0] px-5 py-10 text-[#15191a] sm:px-10 lg:px-16">
          <div className="w-full max-w-[525px] rounded-[22px] border border-[#dfd7c2] bg-[#f8f3e8] p-6 shadow-[0_24px_55px_rgba(13,13,13,0.22)] sm:p-10">
            <div className="text-center">
              <img src="/bot-logo.svg" alt="Bank of Tanzania" className="mx-auto h-24 w-24 object-contain" />
              <h2 className="mt-4 text-3xl font-bold tracking-tight">Sign In</h2>
              <p className="mt-2 text-sm text-[#5f6867]">Access the Bank of Tanzania AI Research Knowledge Hub</p>
              <div className="mx-auto my-6 flex items-center gap-3"><span className="h-px flex-1 bg-[#e3d5b5]" /><span className="h-2.5 w-2.5 rotate-45 bg-[#c99a2e]" /><span className="h-px flex-1 bg-[#e3d5b5]" /></div>
            </div>
            <form onSubmit={submit} className="space-y-5">
              <label className="block text-sm font-semibold">Email Address<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} className="mt-2 w-full rounded-lg border border-[#cda653] bg-transparent px-4 py-3 text-sm outline-none transition-shadow focus:ring-2 focus:ring-[#c99a2e]/30" placeholder="Enter your email address" /></label>
              <label className="block text-sm font-semibold">Password<div className="relative mt-2"><input autoComplete="current-password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-lg border border-[#cda653] bg-transparent px-4 py-3 pr-12 text-sm outline-none transition-shadow focus:ring-2 focus:ring-[#c99a2e]/30" placeholder="Enter your password" /><button type="button" onClick={() => setShowPassword((visible) => !visible)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8e650f]" aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></label>
              {error && <div role="alert" className="rounded-lg border border-[#d9a49b] bg-[#fff5f3] px-3 py-2 text-sm text-[#8c3f2d]">{error}</div>}
              <button type="submit" disabled={submitting} className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#bd870d] px-4 py-3.5 text-base font-semibold text-white shadow-[0_8px_15px_rgba(141,100,15,0.22)] transition-colors hover:bg-[#a87508] disabled:cursor-not-allowed disabled:opacity-60"><LockKeyhole size={18} />{submitting ? 'Signing in...' : 'Sign In'}</button>
            </form>
            <div className="mt-7 border-t border-[#e2e5e3] pt-5 text-center"><div className="flex items-center justify-center gap-2 text-sm font-semibold"><ShieldCheck size={18} className="text-[#bd870d]" />Secure. Official. Trusted.</div><p className="mt-2 text-xs text-[#5f6867]">Bank of Tanzania <span className="mx-2 text-[#c99a2e]">|</span> Excellence in Economic Research</p></div>
          </div>
        </section>
      </div>
    </div>
  )
}

export default LoginPage
