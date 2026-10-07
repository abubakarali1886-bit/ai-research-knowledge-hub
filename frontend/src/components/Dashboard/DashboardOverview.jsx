import { useEffect, useState } from 'react'
import { ArrowRight, BrainCircuit, CheckCircle2, Eye, FileText, MoreVertical, X } from 'lucide-react'

const palette = ['#d39b16', '#b97809', '#262626', '#786e61', '#e8ca83', '#4d8b75']

const PanelLoading = () => <div className="grid h-32 place-items-center text-sm text-[#746b60]">Loading...</div>
const PanelError = ({ message }) => <div className="grid h-32 place-items-center rounded-lg border border-[#e5c9bd] bg-[#fff8f5] p-3 text-center text-xs text-[#8c3f2d]">{message}</div>

const DonutChart = ({ items, total }) => {
  const segments = items.reduce((result, item, index) => {
    const offset = result.offset
    const percentage = total ? (item.count / total) * 100 : 0
    const segment = `${palette[index % palette.length]} ${offset}% ${offset + percentage}%`
    result.segments.push(segment)
    result.offset += percentage
    return result
  }, { segments: [], offset: 0 }).segments

  return (
    <div className="flex items-center gap-5">
      <div className="relative grid h-32 w-32 shrink-0 place-items-center rounded-full" style={{ background: segments.length ? `conic-gradient(${segments.join(', ')})` : '#dfe4e2' }}>
        <div className="grid h-20 w-20 place-items-center rounded-full bg-white text-center">
          <strong className="text-xl text-[#161514]">{total}</strong>
          <span className="text-[0.58rem] text-[#746b60]">records</span>
        </div>
      </div>
      <div className="min-w-0 space-y-2">
        {items.length ? items.slice(0, 5).map((item, index) => (
          <div key={item.label} className="flex items-center gap-2 text-[0.68rem] text-[#514a42]">
            <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: palette[index % palette.length] }} />
            <span className="truncate">{item.label}</span>
            <span className="ml-auto text-[#81766a]">{item.count}</span>
          </div>
        )) : <span className="text-[0.7rem] text-[#746b60]">No records available</span>}
      </div>
    </div>
  )
}

const QuestionChart = ({ points = [], loading = false, error = '' }) => {
  const visiblePoints = points.slice(-14)
  const maximum = Math.max(...visiblePoints.map((point) => point.count), 1)
  const hasQuestions = visiblePoints.some((point) => point.count > 0)
  if (error) return <PanelError message={error} />
  if (loading) return <PanelLoading />
  return (
    <div className="relative rounded-lg border border-[#d9ddda] bg-[#f7f9f8] px-3 pb-2 pt-3" role="img" aria-label="AI questions per day bar chart">
      {visiblePoints.length && hasQuestions ? <div className="relative h-36"><div className="pointer-events-none absolute inset-x-0 bottom-6 top-0 flex flex-col justify-between"><span className="border-t border-dashed border-[#d8dfdc]" /><span className="border-t border-dashed border-[#d8dfdc]" /><span className="border-t border-dashed border-[#d8dfdc]" /><span className="border-t border-[#bfcac5]" /></div><div className="absolute inset-x-0 bottom-0 top-0 flex items-end gap-1.5 sm:gap-2">{visiblePoints.map((point) => <div key={point.date} className="group flex min-w-0 flex-1 flex-col items-center justify-end"><div className="flex h-[108px] w-full items-end justify-center"><span className="absolute -translate-y-1 text-[0.58rem] font-bold text-[#6a531d] opacity-0 transition-opacity group-hover:opacity-100">{point.count}</span><div className="w-full max-w-7 rounded-t-md bg-[#c99a2e] shadow-[0_2px_4px_rgba(154,113,22,0.18)] transition-colors group-hover:bg-[#8e650f]" style={{ height: `${Math.max((point.count / maximum) * 102, 7)}px` }} title={`${point.date}: ${point.count} questions`} /></div><span className="mt-1 w-full truncate text-center text-[0.52rem] text-[#68716f]">{point.date.slice(5)}</span></div>)}</div></div> : <div className="grid h-36 place-items-center text-center text-[0.7rem] text-[#746b60]">No AI questions yet.</div>}
    </div>
  )
}

const AskAiFloatingButton = ({ onClick }) => {
  const [label, setLabel] = useState('')
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    const fullLabel = 'ASK AI'
    const delay = deleting ? 125 : label.length === fullLabel.length ? 1800 : 175
    const timer = window.setTimeout(() => {
      if (!deleting && label.length < fullLabel.length) {
        setLabel(fullLabel.slice(0, label.length + 1))
      } else if (!deleting) {
        setDeleting(true)
      } else if (label.length > 0) {
        setLabel(fullLabel.slice(0, label.length - 1))
      } else {
        setDeleting(false)
      }
    }, delay)
    return () => window.clearTimeout(timer)
  }, [label, deleting])

  return <button type="button" onClick={onClick} aria-label="Open Ask AI" title="Ask AI" className="ask-ai-floating"><span className="ask-ai-floating__label">{label}</span><span className="ask-ai-floating__icon"><BrainCircuit size={24} /></span></button>
}

const DashboardOverview = ({ documents, summary, documentsLoading, documentsError, summaryLoading, summaryError, setActivePage, onViewDocument, onAskDocument }) => {
  const [selectedMetric, setSelectedMetric] = useState(null)
  const recentDocuments = [...(documents || [])].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)).slice(0, 5)
  const totalDocuments = summary?.stats?.total_documents ?? (documentsLoading ? null : documents?.length ?? 0)
  const topicItems = summary?.topics || []
  const categoryItems = summary?.categories || []
  const documentTypes = summary?.document_types || []
  const questionPoints = summary?.questions_per_day || []
  const totalQuestions = summary?.stats?.ai_questions ?? 0

  return (
    <div className="dashboard-overview mx-auto max-w-[1480px] space-y-6 pb-6">
      <section className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <button type="button" onClick={() => setSelectedMetric('documents')} className="rounded-2xl border border-[#d9ddda] bg-[#ffffff] p-5 text-left shadow-[0_10px_24px_rgba(17,17,17,0.04)] transition-shadow hover:border-[#b88b1e] hover:shadow-[0_12px_26px_rgba(17,17,17,0.08)]">
          <div className="mb-4 flex items-start justify-between"><div><h2 className="text-lg font-bold">Total Documents</h2></div><FileText className="text-[#c28d1b]" size={20} /></div>
          {documentsError ? <PanelError message={documentsError} /> : documentsLoading ? <PanelLoading /> : <DonutChart items={documentTypes} total={totalDocuments || 0} />}
        </button>
        <button type="button" onClick={() => setSelectedMetric('topics')} className="rounded-2xl border border-[#d9ddda] bg-[#ffffff] p-5 text-left shadow-[0_10px_24px_rgba(17,17,17,0.04)] transition-shadow hover:border-[#b88b1e] hover:shadow-[0_12px_26px_rgba(17,17,17,0.08)]">
          <div className="mb-4 flex items-start justify-between"><div><h2 className="text-lg font-bold">Research Topics</h2></div><span className="text-2xl font-bold text-[#b27a0c]">{summaryLoading ? '—' : summary?.stats?.research_topics ?? '—'}</span></div>
          {summaryError ? <PanelError message={summaryError} /> : summaryLoading ? <PanelLoading /> : <DonutChart items={topicItems} total={summary?.stats?.research_topics ?? 0} />}
        </button>
        <button type="button" onClick={() => setSelectedMetric('questions')} className="rounded-2xl border border-[#d9ddda] bg-[#ffffff] p-5 text-left shadow-[0_10px_24px_rgba(17,17,17,0.04)] transition-shadow hover:border-[#b88b1e] hover:shadow-[0_12px_26px_rgba(17,17,17,0.08)]">
          <div className="mb-4 flex items-start justify-between"><div><h2 className="text-lg font-bold">AI Questions Per Day</h2><span className="text-2xl font-bold text-[#b27a0c]">{summaryLoading ? '—' : totalQuestions}</span></div><BrainCircuit className="text-[#c28d1b]" size={20} /></div>
          <QuestionChart points={questionPoints} loading={summaryLoading} error={summaryError} />
        </button>
        <button type="button" onClick={() => setSelectedMetric('categories')} className="rounded-2xl border border-[#d9ddda] bg-[#ffffff] p-5 text-left shadow-[0_10px_24px_rgba(17,17,17,0.04)] transition-shadow hover:border-[#b88b1e] hover:shadow-[0_12px_26px_rgba(17,17,17,0.08)]">
          <div className="mb-4 flex items-start justify-between"><div><h2 className="text-lg font-bold">Departments</h2></div><span className="text-2xl font-bold text-[#b27a0c]">{summaryLoading ? '—' : categoryItems.length}</span></div>
          {summaryError ? <PanelError message={summaryError} /> : summaryLoading ? <PanelLoading /> : <DonutChart items={categoryItems} total={categoryItems.reduce((sum, item) => sum + item.count, 0)} />}
        </button>
      </section>

      <section className="overflow-hidden rounded-2xl border border-[#e7dcc6] bg-[#fffaf0]/90 shadow-[0_10px_24px_rgba(17,17,17,0.04)]">
        <div className="flex items-center justify-between border-b border-[#eadfca] px-5 py-4"><h2 className="font-bold">Recent Research Documents</h2><button type="button" onClick={() => setActivePage('documents')} className="inline-flex items-center gap-1 text-xs font-semibold text-[#a87513]">View all <ArrowRight size={14} /></button></div>
        {documentsLoading ? <div className="p-6 text-sm text-[#746b60]">Loading research documents...</div> : documentsError ? <div className="p-6 text-sm text-[#8c3f2d]">{documentsError}</div> : recentDocuments.length === 0 ? <div className="p-6 text-sm text-[#746b60]">No documents available.</div> : <div className="overflow-x-auto"><table className="min-w-full text-left text-xs"><thead className="bg-[#f5ecdb] text-[#625a50]"><tr>{['Document Title', 'Author', 'Year', 'Department / Type', 'Date Added', 'Status', 'Actions'].map((heading) => <th key={heading} className="whitespace-nowrap px-4 py-3 font-semibold">{heading}</th>)}</tr></thead><tbody>{recentDocuments.map((doc, index) => <tr key={doc.id} className={index % 2 ? 'bg-[#fcf7ed]' : 'bg-[#fffdf8]'}><td className="max-w-[260px] border-t border-[#f0e6d0] px-4 py-3 font-medium">{doc.title || doc.file_name || '—'}</td><td className="border-t border-[#f0e6d0] px-4 py-3">{doc.author || '—'}</td><td className="border-t border-[#f0e6d0] px-4 py-3">{doc.publication_year || '—'}</td><td className="border-t border-[#f0e6d0] px-4 py-3">{[doc.department, doc.document_type].filter(Boolean).join(' / ') || '—'}</td><td className="whitespace-nowrap border-t border-[#f0e6d0] px-4 py-3">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}</td><td className="border-t border-[#f0e6d0] px-4 py-3"><span className="inline-flex items-center gap-1 rounded-full bg-[#ebfaf0] px-2 py-1 text-[0.65rem] text-[#158b4d]"><CheckCircle2 size={11} />{doc.is_processed ? 'Processed' : (doc.processing_status || 'Pending')}</span></td><td className="border-t border-[#f0e6d0] px-4 py-3"><div className="flex gap-1 text-[#61584e]"><button type="button" onClick={() => onViewDocument(doc.id)} title="View details" aria-label={`View ${doc.title || doc.file_name}`} className="p-1.5 hover:text-[#a87513]"><Eye size={14} /></button><button type="button" onClick={() => onAskDocument(doc)} title="Ask AI" aria-label={`Ask AI about ${doc.title || doc.file_name}`} className="p-1.5 hover:text-[#a87513]"><BrainCircuit size={14} /></button><button type="button" onClick={() => onViewDocument(doc.id)} title="View details" aria-label={`View details for ${doc.title || doc.file_name}`} className="p-1.5 hover:text-[#a87513]"><MoreVertical size={15} /></button></div></td></tr>)}</tbody></table></div>}
      </section>

      <AskAiFloatingButton onClick={() => setActivePage('chat')} />

      {selectedMetric && <div className="fixed inset-0 z-40 grid place-items-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label={`${selectedMetric} statistics`}>
        <div className="max-h-[calc(100vh-2rem)] w-full max-w-lg overflow-y-auto rounded-2xl border border-[#c9ced0] bg-white p-6 shadow-2xl">
          <div className="flex items-center justify-between"><div><p className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-[#997326]">Dashboard details</p><h2 className="mt-1 text-lg font-bold text-[#151515]">{selectedMetric === 'documents' ? 'Document Statistics' : selectedMetric === 'topics' ? 'Research Topic Statistics' : selectedMetric === 'categories' ? 'Department Statistics' : 'AI Question Statistics'}</h2></div><button type="button" onClick={() => setSelectedMetric(null)} aria-label="Close statistics" className="rounded-md p-2 text-[#4d5557] hover:bg-[#eef0ef]"><X size={18} /></button></div>
          {selectedMetric === 'documents' && <div className="metric-detail-content mt-5"><div className="metric-detail-highlight"><span>Total documents</span><strong>{totalDocuments ?? '—'}</strong><small>{summary?.stats?.processed_documents ?? 0} processed and ready</small></div><div className="metric-detail-grid"><div><span>Processed</span><strong>{summary?.stats?.processed_documents ?? '—'}</strong></div><div><span>Document types</span><strong>{documentTypes.length || '—'}</strong></div><div><span>Recent additions</span><strong>{recentDocuments.length || '—'}</strong></div></div><div className="metric-detail-list">{documentTypes.length ? documentTypes.map((item) => <div key={item.label}><span>{item.label}</span><b>{item.count}</b><i><em style={{ width: `${totalDocuments ? `${(item.count / totalDocuments) * 100}%` : '0%'}` }} /></i></div>) : <p>No document type data available.</p>}</div></div>}
          {selectedMetric === 'topics' && <div className="metric-detail-content mt-5"><div className="metric-detail-highlight"><span>Research topics</span><strong>{summary?.stats?.research_topics ?? '—'}</strong><small>Distinct topics linked to active documents</small></div><div className="metric-detail-list">{topicItems.length ? topicItems.map((topic) => <div key={topic.label}><span>{topic.label}</span><b>{topic.count}</b><i><em style={{ width: `${topicItems[0]?.count ? `${(topic.count / topicItems[0].count) * 100}%` : '0%'}` }} /></i></div>) : <p>No research topics available.</p>}</div></div>}
          {selectedMetric === 'categories' && <div className="metric-detail-content mt-5"><div className="metric-detail-highlight"><span>Active departments</span><strong>{categoryItems.length || '—'}</strong><small>BOT-aligned departments linked to active documents</small></div><div className="metric-detail-list">{categoryItems.length ? categoryItems.map((category) => <div key={category.label}><span>{category.label}</span><b>{category.count}</b></div>) : <p>No departments available.</p>}</div></div>}
          {selectedMetric === 'questions' && <div className="mt-5"><div className="grid gap-3 sm:grid-cols-2"><div className="rounded-xl border border-[#e2e6e4] bg-[#f7f9f8] p-3"><p className="text-xs text-[#68716f]">Total questions</p><strong className="mt-1 block text-2xl text-[#151515]">{summary?.stats?.ai_questions ?? '—'}</strong></div><div className="rounded-xl border border-[#e2e6e4] bg-[#f7f9f8] p-3"><p className="text-xs text-[#68716f]">Recorded days</p><strong className="mt-1 block text-2xl text-[#151515]">{questionPoints.length}</strong></div></div><div className="mt-4 space-y-2">{questionPoints.length ? questionPoints.map((point) => <div key={point.date} className="flex items-center justify-between rounded-lg border border-[#e5e9e7] bg-white px-3 py-2 text-sm text-[#4d5557]"><span>{point.date}</span><strong className="text-[#8e650f]">{point.count} questions</strong></div>) : <p className="text-sm text-[#68716f]">No AI questions yet.</p>}</div></div>}
        </div>
      </div>}
    </div>
  )
}

export default DashboardOverview
