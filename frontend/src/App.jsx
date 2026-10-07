import { useCallback, useEffect, useRef, useState } from 'react'
import {
  FileText,
  Search,
  Upload,
  Eye,
  Download,
  Trash2,
  Bookmark,
  MessageSquareText,
  BookOpenText,
  ArrowLeft,
  UserPlus,
  X,
  CalendarDays,
  Users,
  UserCheck,
  FileCheck2,
  FileClock,
  FileX2,
  Bell,
  Pencil,
  Save,
} from 'lucide-react'
import Sidebar from './components/Layout/Sidebar'
import Header from './components/Layout/Header'
import TanzaniaStripe from './components/Layout/TanzaniaStripe'
import DashboardOverview from './components/Dashboard/DashboardOverview'
import LoginPage from './components/Auth/LoginPage'
import {
  askQuestion,
  getDocuments,
  searchDocuments,
  summarizeDocument,
  uploadDocument,
  previewUpload,
  getDashboardSummary,
  getCurrentUser,
  getDocument,
  deleteDocument,
  updateDocumentMetadata,
  downloadDocument,
  getDocumentViewUrl,
  saveDocument,
  unsaveDocument,
  getSavedDocuments,
  updateProfile,
  logout,
  getAdminDashboard,
  getAdminActivityLogs,
  getAdminActivityNotifications,
  markActivityReviewed,
  exportAdminReport,
  listUsers,
  createAdminUser,
  updateUserRole,
  updateUserStatus,
  deleteUser,
} from './services/api'

const pagePaths = {
  dashboard: '/dashboard',
  documents: '/research-documents',
  search: '/search',
  chat: '/ask-ai',
  summarize: '/summaries',
  upload: '/upload',
  saved: '/saved-research',
  profile: '/profile',
  settings: '/settings',
  admin: '/admin',
  adminUsers: '/admin/users',
}

const pathPages = Object.fromEntries(Object.entries(pagePaths).map(([page, path]) => [path, page]))

const BackButton = () => (
  <button type="button" onClick={() => { if (window.history.length > 1) window.history.back(); else window.location.assign('/dashboard') }} className="mb-4 inline-flex min-h-10 items-center gap-2 rounded-lg border border-[#d9ddda] bg-white px-3 py-2 text-sm font-semibold text-[#313938] shadow-sm transition-colors hover:border-[#c99a2e] hover:text-[#8e650f] focus:outline-none focus:ring-2 focus:ring-[#c99a2e]/30">
    <ArrowLeft size={16} /> Back
  </button>
)

function App() {
  const [activePage, setActivePage] = useState(() => pathPages[window.location.pathname] || 'dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 1024)
  const [documents, setDocuments] = useState([])
  const [savedDocuments, setSavedDocuments] = useState([])
  const [documentsLoading, setDocumentsLoading] = useState(true)
  const [documentsError, setDocumentsError] = useState(null)
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [documentViewUrl, setDocumentViewUrl] = useState('')
  const [documentDetailLoading, setDocumentDetailLoading] = useState(false)
  const [documentDetailError, setDocumentDetailError] = useState('')
  const [dashboardSummary, setDashboardSummary] = useState(null)
  const [dashboardLoading, setDashboardLoading] = useState(true)
  const [dashboardError, setDashboardError] = useState('')
  const [currentUser, setCurrentUser] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [chatQuestion, setChatQuestion] = useState('What are the main drivers of inflation in Tanzania?')
  const [chatAnswer, setChatAnswer] = useState('')
  const [chatSources, setChatSources] = useState([])
  const [chatLoading, setChatLoading] = useState(false)
  const [summary, setSummary] = useState('')
  const [summaryDocumentId, setSummaryDocumentId] = useState('')
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState('')
  const [authLoading, setAuthLoading] = useState(true)
  const [profileStatus, setProfileStatus] = useState('')
  const userSessionRef = useRef(0)
  const role = String(currentUser?.role || '').toLowerCase()
  const isAdmin = role === 'admin'
  const isResearcher = role === 'researcher' || isAdmin
  const canManageDocuments = isResearcher
  const canAccessAdmin = isAdmin

  const fetchDocuments = async () => {
    try {
      setDocumentsLoading(true)
      setDocumentsError('')
      const response = await getDocuments().catch(error => {
        setDocumentsError('Unable to load research documents.')
        console.error('Failed to fetch documents:', error)
      })
      setDocuments(Array.isArray(response?.documents) ? response.documents : [])
    } catch (error) {
      setDocuments([])
      setDocumentsError('Unable to load research documents.')
      console.error('Failed to fetch documents:', error)
    } finally {
      setDocumentsLoading(false)
    }
  }

  const openDocument = async (documentId) => {
    try {
      setDocumentDetailLoading(true)
      setDocumentDetailError('')
      setSelectedDocument(await getDocument(documentId))
      setActivePage('document')
    } catch (error) {
      setDocumentDetailError('Unable to load document details.')
      console.error('Failed to fetch document:', error)
    } finally {
      setDocumentDetailLoading(false)
    }
  }

  const viewDocument = async (documentId, pageNumber = null) => {
    try {
      const viewUrl = await getDocumentViewUrl(documentId)
      setDocumentViewUrl(pageNumber ? `${viewUrl}#page=${pageNumber}` : viewUrl)
    } catch (error) {
      setDocumentDetailError('Unable to open document file.')
      console.error('Failed to open document:', error)
    }
  }

  const askAboutDocument = (document) => {
    setChatQuestion(`What are the key findings in "${document.title || document.file_name}"?`)
    setChatAnswer('')
    setChatSources([])
    setActivePage('chat')
  }

  const clearUserScopedState = () => {
    userSessionRef.current += 1
    setChatQuestion('What are the main drivers of inflation in Tanzania?')
    setChatAnswer('')
    setChatSources([])
    setSearchQuery('')
    setSearchResults([])
    setSelectedDocument(null)
    setSavedDocuments([])
    setSummary('')
    setSummaryDocumentId('')
    setDashboardSummary(null)
    setDashboardError('')
  }

  const handleGlobalSearch = (event) => {
    event.preventDefault()
    const query = searchQuery.trim()
    if (!query) {
      setSearchResults([])
      setActivePage('search')
      return
    }
    navigateTo('search')
    handleSearch(event)
  }

  const handleLogout = async () => {
    try {
      await logout()
    } finally {
      clearUserScopedState()
      setCurrentUser(null)
      window.history.pushState({}, '', '/login')
    }
  }

  const navigateTo = (page) => {
    setActivePage(page)
    window.history.pushState({}, '', pagePaths[page] || '/dashboard')
    if (window.innerWidth < 1024) setSidebarOpen(false)
  }

  const handleProfileUpdate = async (profile) => {
    try {
      setProfileStatus('Saving profile...')
      setCurrentUser(await updateProfile(profile))
      setProfileStatus('Profile updated successfully.')
    } catch (error) {
      setProfileStatus(error.response?.data?.detail || 'Unable to update profile.')
    }
  }

  const fetchDashboard = async () => {
    const requestSession = userSessionRef.current
    try {
      setDashboardLoading(true)
      setDashboardError('')
      const summary = await getDashboardSummary()
      if (requestSession === userSessionRef.current) setDashboardSummary(summary)
    } catch (error) {
      if (requestSession === userSessionRef.current) setDashboardError('Unable to load dashboard statistics.')
      console.error('Failed to fetch dashboard summary:', error)
    } finally {
      setDashboardLoading(false)
    }
  }

  useEffect(() => {
    const restoreSession = async () => {
      try {
        const user = await getCurrentUser()
        setCurrentUser(user)
        if (user && (window.location.pathname === '/login' || (user.role === 'admin' && window.location.pathname === '/dashboard'))) {
          const landingPage = String(user.role).toLowerCase() === 'admin' ? 'admin' : 'dashboard'
          window.history.replaceState({}, '', pagePaths[landingPage])
          setActivePage(landingPage)
        }
      } catch (error) {
        localStorage.removeItem('access_token')
        setCurrentUser(null)
        console.error('Failed to restore current user:', error)
      } finally {
        setAuthLoading(false)
      }
    }
    restoreSession()
  }, [])

  useEffect(() => {
    if (!currentUser) return
    const loadUserData = window.setTimeout(() => {
      fetchDocuments()
      if (String(currentUser.role || '').toLowerCase() === 'admin') return
      fetchDashboard()
      getSavedDocuments().then((response) => setSavedDocuments(Array.isArray(response?.documents) ? response.documents : [])).catch((error) => console.error('Failed to fetch saved documents:', error))
    }, 0)
    return () => window.clearTimeout(loadUserData)
  }, [currentUser])

  useEffect(() => {
    const syncPath = () => setActivePage(pathPages[window.location.pathname] || 'dashboard')
    window.addEventListener('popstate', syncPath)
    return () => window.removeEventListener('popstate', syncPath)
  }, [])

  if (authLoading) return <div className="flex min-h-screen items-center justify-center bg-[#0d0d0d] text-sm text-[#d5b15e]">Checking secure session...</div>
  if (!currentUser) return <LoginPage onAuthenticated={(user) => {
    const landingPage = String(user?.role || '').toLowerCase() === 'admin' ? 'admin' : 'dashboard'
    clearUserScopedState()
    setCurrentUser(user)
    window.history.replaceState({}, '', pagePaths[landingPage])
    setActivePage(landingPage)
  }} />

  const handleSearch = async (e) => {
    e?.preventDefault()
    const query = searchQuery.trim()
    if (!query) return

    try {
      setSearchLoading(true)
      const results = await searchDocuments(query, 5)
      setSearchResults(Array.isArray(results) ? results : [])
    } catch (error) {
      console.error('Search failed:', error)
      setSearchResults([])
    } finally {
      setSearchLoading(false)
    }
  }

  const handleChat = async (e) => {
    e?.preventDefault()
    const question = chatQuestion.trim()
    if (!question) return

    try {
      const requestSession = userSessionRef.current
      setChatLoading(true)
      setChatAnswer('')
      const result = await askQuestion(question, 5)
      if (requestSession !== userSessionRef.current) return
      setChatAnswer(result?.answer?.trim() || result?.error || 'The AI service returned an empty response.')
      setChatSources(Array.isArray(result?.sources) ? result.sources : [])
      if (result?.success) await fetchDashboard()
    } catch (error) {
      console.error('Chat failed:', error)
      setChatAnswer(error.response?.data?.detail || 'The AI assistant could not retrieve a response right now.')
      setChatSources([])
    } finally {
      setChatLoading(false)
    }
  }

  const handleUpload = async (formData) => {
    const file = formData.get('file')
    if (!file) return

    try {
      setUploadStatus('Uploading and processing document...')
      const result = await uploadDocument(formData)
      setUploadStatus(`Uploaded and processed: ${result?.title || result?.file_name || file.name}`)
      await fetchDocuments()
      await fetchDashboard()
    } catch (error) {
      setUploadStatus(error.response?.data?.detail || 'Upload failed. Check the backend server and file type.')
      console.error('Upload failed:', error)
    }
  }

  const handleDeleteDocument = async (documentId) => {
    if (!canManageDocuments) {
      setDocumentsError('Only researchers and administrators can delete documents.')
      return
    }
    if (!window.confirm('Delete this document from the repository?')) return

    try {
      await deleteDocument(documentId)
      await fetchDocuments()
      await fetchDashboard()
    } catch (error) {
      setDocumentsError(error.response?.data?.detail || 'Unable to delete this document.')
      console.error('Failed to delete document:', error)
    }
  }

  const handleUpdateDocumentMetadata = async (documentId, metadata) => {
    const updatedDocument = await updateDocumentMetadata(documentId, metadata)
    setSelectedDocument((current) => current?.id === documentId ? { ...current, ...updatedDocument } : current)
    await fetchDocuments()
    await fetchDashboard()
    return updatedDocument
  }

  const handleSaveDocument = async (documentId) => {
    try {
      await saveDocument(documentId)
      const response = await getSavedDocuments()
      setSavedDocuments(Array.isArray(response?.documents) ? response.documents : [])
    } catch (error) {
      console.error('Failed to save document:', error)
    }
  }

  const handleUnsaveDocument = async (documentId) => {
    try {
      await unsaveDocument(documentId)
      const response = await getSavedDocuments()
      setSavedDocuments(Array.isArray(response?.documents) ? response.documents : [])
    } catch (error) {
      console.error('Failed to remove saved document:', error)
    }
  }

  const handleDownloadDocument = async (documentId) => {
    try {
      await downloadDocument(documentId)
    } catch (error) {
      console.error('Failed to download document:', error)
    }
  }

  const handleSummarize = async (documentId) => {
    if (!documentId) return

    const requestSession = userSessionRef.current
    const summaryId = String(documentId)
    setSummaryDocumentId(summaryId)
    setSummary('')

    try {
      setSummaryLoading(true)
      const result = await summarizeDocument(Number(documentId), 1400, 0.25)
      if (requestSession !== userSessionRef.current) return
      const summarizeData = result?.summary || {}
      const summaryLabels = {
        report_title: '',
        report_source: 'Source',
        report_authors: 'Authors',
        executive_summary: '1. Executive Summary',
        research_objective: '2. Research Objective and Scope',
        methodology: '3. Methodology and Data',
        key_findings: '4. Principal Findings',
        effects: '5. Economic, Sectoral, Fiscal or Welfare Effects',
        constraints: '6. Constraints and Risks',
        policy_implications: '7. Policy Implications',
        main_conclusions: '8. Conclusion',
        limitations: '9. Limitations and Evidence Gaps',
      }
      const summaryText = Object.entries(summaryLabels)
        .filter(([key]) => summarizeData[key])
        .map(([key, label]) => key === 'report_title' ? `# RESEARCH SUMMARY\n\n## ${summarizeData[key]}` : `${label ? `${label}\n` : ''}${summarizeData[key]}`)
        .join('\n\n') || result?.raw_summary || 'No summary available yet.'
      setSummary(summaryText)
    } catch (error) {
      if (requestSession !== userSessionRef.current) return
      console.error('Summarization failed:', error)
      setSummary('Summarization failed. Please check if the document has been processed.')
    } finally {
      setSummaryLoading(false)
    }
  }

  const renderPage = () => {
    const adminPages = ['admin', 'adminUsers', 'adminDocuments', 'adminProcessing', 'adminCategories', 'adminTypes', 'adminTopics', 'adminActivity']
    if (adminPages.includes(activePage) && !canAccessAdmin) {
      return <div className="mx-auto max-w-[800px] rounded-[24px] border border-[#d9ddda] bg-white p-5 text-sm text-[#5a554f]">This area is restricted to administrators.</div>
    }

    switch (activePage) {
      case 'documents':
        return <DocumentsPage documents={documents} loading={documentsLoading} error={documentsError} canManage={canManageDocuments} onView={openDocument} onViewFile={viewDocument} onDownload={handleDownloadDocument} onDelete={handleDeleteDocument} onSave={handleSaveDocument} onAsk={askAboutDocument} onSummarize={(documentId) => { handleSummarize(documentId); setActivePage('summarize') }} />
      case 'document':
        return <DocumentDetailsPage document={selectedDocument} loading={documentDetailLoading} error={documentDetailError} canManage={canManageDocuments} onUpdate={handleUpdateDocumentMetadata} onViewFile={() => selectedDocument && viewDocument(selectedDocument.id)} onDownload={() => selectedDocument && handleDownloadDocument(selectedDocument.id)} onSave={() => selectedDocument && handleSaveDocument(selectedDocument.id)} onAsk={() => selectedDocument && askAboutDocument(selectedDocument)} onSummarize={() => { if (selectedDocument) { handleSummarize(selectedDocument.id); setSummaryDocumentId(String(selectedDocument.id)); setActivePage('summarize') } }} />
      case 'search':
        return (
          <SearchPage
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            searchResults={searchResults}
            searchLoading={searchLoading}
            handleSearch={handleSearch}
            onViewSource={(documentId, pageNumber) => viewDocument(documentId, pageNumber)}
          />
        )
      case 'chat':
        return (
          <ChatPage
            chatQuestion={chatQuestion}
            setChatQuestion={setChatQuestion}
            chatAnswer={chatAnswer}
            chatSources={chatSources}
            chatLoading={chatLoading}
            handleChat={handleChat}
            onViewSource={(documentId, pageNumber) => viewDocument(documentId, pageNumber)}
          />
        )
      case 'summarize':
        return (
          <SummarizePage
            documents={documents}
            selectedDocumentId={summaryDocumentId}
            summary={summary}
            summaryLoading={summaryLoading}
            handleSummarize={(documentId) => {
              setSummaryDocumentId(String(documentId || ''))
              handleSummarize(documentId)
            }}
          />
        )
      case 'upload':
        return <UploadPage canManage={canManageDocuments} uploadStatus={uploadStatus} onUpload={handleUpload} />
      case 'saved':
        return <SavedPage documents={savedDocuments} onView={openDocument} onViewFile={viewDocument} onDownload={handleDownloadDocument} onUnsave={handleUnsaveDocument} onAsk={askAboutDocument} onSummarize={(documentId) => { setSummaryDocumentId(String(documentId || '')); handleSummarize(documentId); setActivePage('summarize') }} />
      case 'profile':
        return <ProfilePage user={currentUser} status={profileStatus} onSave={handleProfileUpdate} />
      case 'settings':
        return <SettingsPage user={currentUser} />
      case 'admin':
        return <AdminDashboardPage user={currentUser} />
      default:
        return (
          <DashboardOverview
            documents={documents}
            summary={dashboardSummary}
            documentsLoading={documentsLoading}
            documentsError={documentsError}
            summaryLoading={dashboardLoading}
            summaryError={dashboardError}
            setActivePage={navigateTo}
            onViewDocument={openDocument}
            onViewFile={viewDocument}
            onAskDocument={askAboutDocument}
            canManage={canManageDocuments}
            onDownloadDocument={handleDownloadDocument}
          />
        )
    }
  }

  if (isAdmin) {
    return (
      <AdminShell
        user={currentUser}
        activePage={activePage}
        setActivePage={navigateTo}
        onLogout={handleLogout}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        onSearch={handleGlobalSearch}
        documents={documents}
        documentsLoading={documentsLoading}
        documentsError={documentsError}
        onViewDocument={openDocument}
        onViewFile={viewDocument}
        selectedDocument={selectedDocument}
        documentViewUrl={documentViewUrl}
        documentDetailLoading={documentDetailLoading}
        documentDetailError={documentDetailError}
        onCloseDocumentViewer={() => { URL.revokeObjectURL(documentViewUrl); setDocumentViewUrl('') }}
        onDownload={handleDownloadDocument}
        onDeleteDocument={handleDeleteDocument}
        onUpdateDocumentMetadata={handleUpdateDocumentMetadata}
        onSaveDocument={handleSaveDocument}
        onAskDocument={askAboutDocument}
        onSummarizeDocument={(documentId) => { handleSummarize(documentId); navigateTo('summarize') }}
        searchResults={searchResults}
        searchLoading={searchLoading}
        handleSearch={handleSearch}
        uploadStatus={uploadStatus}
        onUpload={handleUpload}
        summary={summary}
        summaryLoading={summaryLoading}
        handleSummarize={handleSummarize}
      />
    )
  }

  return (
    <div className="app-shell min-h-screen text-[#111111]">
      <div className="flex min-h-screen">
        <aside className={`fixed inset-y-0 left-0 z-50 transition-transform duration-300 lg:static lg:inset-auto lg:flex ${sidebarOpen ? 'translate-x-0 lg:translate-x-0' : '-translate-x-full lg:hidden'}`}>
            <Sidebar activePage={activePage} setActivePage={navigateTo} user={currentUser} />
        </aside>

        {sidebarOpen && <div className="fixed inset-0 z-40 bg-black/35 lg:hidden" onClick={() => setSidebarOpen(false)} />}

        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <Header onMenuClick={() => setSidebarOpen((open) => !open)} user={currentUser} searchQuery={searchQuery} setSearchQuery={setSearchQuery} onSearch={handleGlobalSearch} onLogout={handleLogout} onProfileClick={() => navigateTo('profile')} />

          <main className="flex-1 overflow-x-hidden px-4 pb-3 pt-3 sm:px-5 lg:px-6">{renderPage()}</main>
          {documentViewUrl && <div className="fixed inset-0 z-[60] bg-black/70 p-4"><div className="mx-auto flex h-full max-w-6xl flex-col overflow-hidden rounded-xl bg-white"><div className="flex items-center justify-between border-b border-[#d9ddda] px-4 py-3"><span className="text-sm font-semibold">Document viewer</span><button type="button" onClick={() => { URL.revokeObjectURL(documentViewUrl); setDocumentViewUrl('') }} className="rounded-md bg-[#111111] px-3 py-2 text-xs font-semibold text-white">Close</button></div><iframe title="Research document viewer" src={documentViewUrl} className="min-h-0 flex-1" /></div></div>}

          <TanzaniaStripe position="bottom" />
          <Footer />
        </div>
      </div>
    </div>
  )
}

const DocumentDetailsPage = ({ document, loading, error, canManage, onUpdate, onViewFile, onDownload, onSave, onAsk, onSummarize }) => {
  const [editingMetadata, setEditingMetadata] = useState(false)
  const [metadataDraft, setMetadataDraft] = useState({ title: '', author: '', publication_year: '' })
  const [savingMetadata, setSavingMetadata] = useState(false)
  const [metadataError, setMetadataError] = useState('')

  const beginMetadataEdit = () => {
    setMetadataDraft({
      title: document.title || '',
      author: document.author || '',
      publication_year: document.publication_year ? String(document.publication_year) : '',
    })
    setMetadataError('')
    setEditingMetadata(true)
  }

  const saveMetadata = async (event) => {
    event.preventDefault()
    setSavingMetadata(true)
    setMetadataError('')
    try {
      await onUpdate(document.id, {
        title: metadataDraft.title,
        author: metadataDraft.author,
        publication_year: metadataDraft.publication_year ? Number(metadataDraft.publication_year) : null,
      })
      setEditingMetadata(false)
    } catch (saveError) {
      setMetadataError(saveError.response?.data?.detail || 'Unable to save document metadata.')
    } finally {
      setSavingMetadata(false)
    }
  }

  return (
    <div className="mx-auto max-w-[900px] rounded-[24px] border border-[#e7dcc6] bg-[#f9f7f2] p-5 shadow-[0_12px_20px_rgba(17,17,17,0.03)]">
      <BackButton />
      {loading ? (
        <div className="text-sm text-[#5a554f]">Loading document details...</div>
      ) : error ? (
        <div className="rounded-xl border border-[#e7cfc6] bg-[#fff8f5] p-4 text-sm text-[#8c3f2d]">{error}</div>
      ) : !document ? (
        <div className="rounded-xl border border-[#e7dcc6] bg-[#fffdf9] p-4 text-sm text-[#5a554f]">Select a document to view its details.</div>
      ) : (
        <>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-[#151515]">{document.title || document.file_name}</h2>
              <p className="mt-1 text-sm text-[#5c564f]">{document.file_name}</p>
            </div>
            <span className="rounded-full border border-[#d3f0da] bg-[#ebfaf0] px-2 py-1 text-[0.62rem] font-medium text-[#158b4d]">{document.processing_status || 'Unknown'}</span>
          </div>
          <dl className="mt-6 grid gap-3 text-sm text-[#4e4743] sm:grid-cols-2">
            <div><dt className="font-semibold text-[#1b1b1b]">Author</dt><dd>{document.author || '—'}</dd></div>
            <div><dt className="font-semibold text-[#1b1b1b]">Department</dt><dd>{document.department || '—'}</dd></div>
            <div><dt className="font-semibold text-[#1b1b1b]">Document type</dt><dd>{document.document_type || document.file_type || '—'}</dd></div>
            <div><dt className="font-semibold text-[#1b1b1b]">Publication year</dt><dd>{document.publication_year || '—'}</dd></div>
            <div><dt className="font-semibold text-[#1b1b1b]">Chunks</dt><dd>{document.chunk_count ?? '—'}</dd></div>
            <div><dt className="font-semibold text-[#1b1b1b]">File size</dt><dd>{document.file_size ? `${Math.round(document.file_size / 1024)} KB` : '—'}</dd></div>
            <div><dt className="font-semibold text-[#1b1b1b]">Research topics</dt><dd>{document.topics?.length ? document.topics.join(', ') : '—'}</dd></div>
          </dl>
          <div className="mt-6 flex flex-wrap gap-3">
            {canManage && <button type="button" onClick={beginMetadataEdit} className="inline-flex items-center gap-2 rounded-xl border border-[#d9ddda] bg-white px-4 py-3 text-sm font-semibold text-[#1b1b1b]"><Pencil size={15} />Edit metadata</button>}
            <button type="button" onClick={onViewFile} className="rounded-xl border border-[#d9ddda] bg-white px-4 py-3 text-sm font-semibold text-[#1b1b1b]">View document</button>
            <button type="button" onClick={onDownload} className="rounded-xl border border-[#d9ddda] bg-white px-4 py-3 text-sm font-semibold text-[#1b1b1b]">Download</button>
            <button type="button" onClick={onSave} className="rounded-xl border border-[#d9ddda] bg-white px-4 py-3 text-sm font-semibold text-[#1b1b1b]">Save research</button>
            <button type="button" onClick={onAsk} className="rounded-xl bg-[#111111] px-4 py-3 text-sm font-semibold text-[#f4ebd1]">Ask AI about this document</button>
            <button type="button" onClick={onSummarize} className="rounded-xl border border-[#d6b979] bg-[#f5eecb] px-4 py-3 text-sm font-semibold text-[#5b4517]">Generate summary</button>
          </div>
          {editingMetadata && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !savingMetadata) setEditingMetadata(false) }}>
            <form role="dialog" aria-modal="true" aria-labelledby="metadata-editor-title" onSubmit={saveMetadata} className="w-full max-w-lg space-y-4 rounded-xl border border-[#d9ddda] bg-white p-5 shadow-xl">
              <div className="flex items-start justify-between gap-4"><div><h3 id="metadata-editor-title" className="text-lg font-bold text-[#151515]">Edit document metadata</h3><p className="mt-1 text-sm text-[#5c6463]">Changes are saved to the document record.</p></div><button type="button" onClick={() => setEditingMetadata(false)} disabled={savingMetadata} aria-label="Close editor" className="rounded-md p-2 text-[#53615d] hover:bg-[#eef1ef] disabled:opacity-50"><X size={18} /></button></div>
              {metadataError && <p role="alert" className="rounded-lg bg-[#fff1ee] px-3 py-2 text-sm text-[#8c3f2d]">{metadataError}</p>}
              <label className="block text-sm font-semibold text-[#4e4743]">Title<input required maxLength={500} value={metadataDraft.title} onChange={(event) => setMetadataDraft((current) => ({ ...current, title: event.target.value }))} className="mt-1 w-full rounded-lg border border-[#d9ddda] px-3 py-2 font-normal outline-none focus:border-[#c99a2e]" /></label>
              <label className="block text-sm font-semibold text-[#4e4743]">Author<input maxLength={255} value={metadataDraft.author} onChange={(event) => setMetadataDraft((current) => ({ ...current, author: event.target.value }))} placeholder="Enter author name" className="mt-1 w-full rounded-lg border border-[#d9ddda] px-3 py-2 font-normal outline-none focus:border-[#c99a2e]" /></label>
              <label className="block text-sm font-semibold text-[#4e4743]">Publication year<input type="number" min="1900" max="2100" value={metadataDraft.publication_year} onChange={(event) => setMetadataDraft((current) => ({ ...current, publication_year: event.target.value }))} className="mt-1 w-full rounded-lg border border-[#d9ddda] px-3 py-2 font-normal outline-none focus:border-[#c99a2e]" /></label>
              <div className="flex justify-end gap-2"><button type="button" onClick={() => setEditingMetadata(false)} disabled={savingMetadata} className="rounded-lg border border-[#d9ddda] px-4 py-2 text-sm font-semibold text-[#4e4743]">Cancel</button><button type="submit" disabled={savingMetadata} className="inline-flex items-center gap-2 rounded-lg bg-[#111111] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"><Save size={15} />{savingMetadata ? 'Saving...' : 'Save changes'}</button></div>
            </form>
          </div>}
        </>
      )}
    </div>
  )
}

const DocumentsPage = ({ documents: sourceDocuments, loading, error, onView, onViewFile, onDownload, onDelete, onSave, onAsk, onSummarize, canManage }) => {
  const [documentQuery, setDocumentQuery] = useState('')
  const [documentYear, setDocumentYear] = useState('')
  const documents = sourceDocuments.filter((document) => {
    const query = documentQuery.trim().toLowerCase()
    const nameMatches = !query || [document.title, document.file_name, document.document_name].some((value) => value?.toLowerCase().includes(query)) || [document.file_name, document.title].some((value) => value?.toLowerCase().includes(query))
    const yearMatches = !documentYear || String(document.publication_period || document.publication_year || '').includes(documentYear)
    return nameMatches && yearMatches
  })

  return (
  <div className={`documents-page mx-auto max-w-[1480px] overflow-hidden rounded-[24px] border border-[#d9ddda] bg-white shadow-[0_12px_20px_rgba(17,17,17,0.04)] ${canManage ? '' : 'viewer-documents'}`}>
    <div className="px-5 pt-5"><BackButton /></div>
    <div className="border-b border-[#e1e5e3] px-5 py-5"><h2 className="text-2xl font-bold text-[#151515]">Research Documents</h2><p className="mt-1 text-sm text-[#5c6463]">Search by uploaded document name or publication year.</p><div className="mt-4 flex flex-col gap-3 sm:flex-row"><input value={documentQuery} onChange={(event) => setDocumentQuery(event.target.value)} placeholder="Search document name..." className="flex-1 rounded-lg border border-[#d9ddda] bg-white px-3 py-2 text-sm outline-none focus:border-[#c99a2e]" /><input value={documentYear} onChange={(event) => setDocumentYear(event.target.value)} placeholder="Year or range" className="sm:w-40 rounded-lg border border-[#d9ddda] bg-white px-3 py-2 text-sm outline-none focus:border-[#c99a2e]" /></div></div>
    {loading ? <div className="p-6 text-sm text-[#5a554f]">Loading documents...</div> : error ? <div className="m-5 rounded-xl border border-[#e7cfc6] bg-[#fff8f5] p-4 text-sm text-[#8c3f2d]">{error}</div> : documents.length === 0 ? <div className="m-5 rounded-xl border border-[#d9ddda] bg-[#f7f9f8] p-4 text-sm text-[#5a554f]">No matching research documents found.</div> : (
      <div className="overflow-x-auto"><table className="min-w-[1050px] w-full text-left text-xs"><thead className="bg-[#eef1ef] text-[#56605e]"><tr>{['Document Title', 'Author', 'Year', 'Department', 'Type', 'Date Added', 'Status', 'Actions'].map((heading) => <th key={heading} className="whitespace-nowrap px-4 py-3 font-semibold">{heading}</th>)}</tr></thead><tbody>{documents.map((doc, index) => <tr key={doc.id || doc.file_name} className={index % 2 ? 'bg-[#fbfcfb]' : 'bg-white'}><td className="max-w-[250px] border-t border-[#e8ecea] px-4 py-3 font-semibold text-[#1b1b1b]">{doc.title || doc.file_name || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{doc.author || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{doc.publication_year || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{doc.department || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 uppercase text-[#4f5957]">{doc.document_type || doc.file_type || '—'}</td><td className="whitespace-nowrap border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3"><span className="inline-flex rounded-full bg-[#ebfaf0] px-2 py-1 font-medium text-[#158b4d]">{doc.is_processed ? 'Processed' : (doc.processing_status || 'Pending')}</span></td><td className="border-t border-[#e8ecea] px-4 py-3"><div className="flex items-center gap-1 text-[#5b6563]"><button type="button" onClick={() => onView(doc.id)} title="View details" aria-label={`View details for ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><Eye size={15} /></button><button type="button" onClick={() => onViewFile(doc.id)} title="Open document" aria-label={`Open ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><FileText size={15} /></button><button type="button" onClick={() => onDownload(doc.id)} title="Download" aria-label={`Download ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><Download size={15} /></button><button type="button" onClick={() => onSave(doc.id)} title="Save research" aria-label={`Save ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><Bookmark size={15} /></button><button type="button" onClick={() => onAsk(doc)} title="Ask AI" aria-label={`Ask AI about ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><MessageSquareText size={15} /></button><button type="button" onClick={() => onSummarize(doc.id)} title="Generate summary" aria-label={`Generate summary for ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><BookOpenText size={15} /></button>{canManage && <button type="button" onClick={() => onDelete(doc.id)} title="Delete" aria-label={`Delete ${doc.title || doc.file_name}`} className="rounded-md p-1.5 text-[#8c3f2d] hover:bg-[#fff1ee]"><Trash2 size={15} /></button>}</div></td></tr>)}</tbody></table></div>
    )}
  </div>
  )
}

const SearchPage = ({ searchQuery, setSearchQuery, searchResults, searchLoading, handleSearch, onViewSource }) => (
  <div className="mx-auto max-w-[1000px] rounded-[24px] border border-[#e7dcc6] bg-[#f9f7f2] p-5 shadow-[0_12px_20px_rgba(17,17,17,0.03)]">
    <BackButton />
    <h2 className="text-2xl font-bold text-[#151515]">Semantic Search</h2>

    <form onSubmit={(event) => { event.preventDefault(); handleSearch(); }} className="mt-5 space-y-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6d6258]" size={17} />
        <input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search for inflation, policy, exchange rate, stability..."
          className="w-full rounded-xl border border-[#e2d5b0] bg-white/70 py-3 pl-10 pr-4 text-sm text-[#1d1b19] outline-none"
        />
      </div>
      <button type="submit" disabled={searchLoading} className="rounded-xl bg-[#111111] px-5 py-3 text-sm font-semibold text-[#f4ebd1] disabled:opacity-70">
        {searchLoading ? 'Searching...' : 'Search'}
      </button>
    </form>

    <div className="mt-6 space-y-3">
      {searchResults.length === 0 ? (
        <div className="rounded-xl border border-[#e7dcc6] bg-[#fffdf9] p-4 text-sm text-[#5a554f]">No search results yet. Run a query to retrieve research fragments from the backend.</div>
      ) : (
        searchResults.map((result, index) => (
          <div key={`${result.document || index}-${index}`} className="rounded-xl border border-[#e7dcc6] bg-[#fffdf9] p-4">
            <div className="mb-2 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-[#1b1b1b]">
                {result.metadata?.title || 'Research Result'}
                {result.metadata?.page_number && <span className="ml-2 rounded-md bg-[#f3e7c7] px-2 py-1 text-[0.62rem] font-semibold text-[#765711]">Page {result.metadata.page_number}</span>}
              </h3>
              <span className="text-[0.62rem] text-[#6c645d]">Score: {Number(result.distance || 0).toFixed(3)}</span>
            </div>
            <p className="text-[0.72rem] leading-6 text-[#4e4743]">{result.metadata?.excerpt || result.document || result.excerpt || 'No excerpt provided by backend.'}</p>
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
              <p className="text-[0.62rem] text-[#6c645d]">{[result.metadata?.author, result.metadata?.publication_year, result.metadata?.document_type].filter(Boolean).join(' | ') || 'Institutional research source'}</p>
              <button
                type="button"
                onClick={() => onViewSource(result.metadata?.document_id, result.metadata?.page_number)}
                disabled={!result.metadata?.document_id}
                className="inline-flex items-center gap-1 rounded-md border border-[#d9ddda] px-2 py-1 text-[0.62rem] font-semibold text-[#1b1b1b] hover:border-[#c99a2e] disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Eye size={13} /> View{result.metadata?.page_number ? ` page ${result.metadata.page_number}` : ''}
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  </div>
)

const ChatPage = ({ chatQuestion, setChatQuestion, chatAnswer, chatSources, chatLoading, handleChat, onViewSource }) => (
  <div className="mx-auto max-w-[900px] rounded-[24px] border border-[#e7dcc6] bg-[#f9f7f2] p-5 shadow-[0_12px_20px_rgba(17,17,17,0.03)]">
    <BackButton />
    <h2 className="text-2xl font-bold text-[#151515]">Ask AI</h2>

    <form onSubmit={(event) => { event.preventDefault(); handleChat(); }} className="mt-5 space-y-3">
      <textarea
        rows={4}
        value={chatQuestion}
        onChange={(e) => setChatQuestion(e.target.value)}
        placeholder="Ask a question about inflation, exchange rate policy, or financial stability..."
        className="w-full resize-none rounded-xl border border-[#e2d5b0] bg-white/70 p-4 text-sm text-[#1d1b19] outline-none"
      />
      <button type="submit" disabled={chatLoading} className="self-end rounded-xl bg-[#111111] px-5 py-3 text-sm font-semibold text-[#f4ebd1] disabled:opacity-70">
        {chatLoading ? 'Generating answer...' : 'Ask AI'}
      </button>
    </form>

    <div className="mt-6 rounded-xl border border-[#e7dcc6] bg-[#fffdf9] p-4 text-[0.76rem] leading-6 text-[#4e4743]">
      {chatAnswer || 'Response from the backend AI assistant will appear here.'}
    </div>
    {chatSources.length > 0 && (
      <div className="mt-3 rounded-xl border border-[#e7dcc6] bg-[#fffdf9] p-4">
        <h3 className="text-xs font-semibold text-[#1b1b1b]">Sources</h3>
        <div className="mt-2 space-y-2">
          {chatSources.map((source) => (
            <div key={`${source.document_id}-${source.chunk_index}`} className="border-b border-[#f0e6d0] pb-2 text-[0.7rem] text-[#4e4743] last:border-0 last:pb-0">
              <div className="flex items-center justify-between gap-2">
                <span>{source.title || `Document ${source.document_id}`} {source.page_number ? `| Page ${source.page_number}` : ''}</span>
                <button type="button" onClick={() => onViewSource(source.document_id, source.page_number)} disabled={!source.document_id} className="inline-flex items-center gap-1 rounded-md border border-[#d9ddda] px-2 py-1 text-[0.62rem] font-semibold text-[#1b1b1b] hover:border-[#c99a2e] disabled:cursor-not-allowed disabled:opacity-40"><Eye size={13} /> View{source.page_number ? ` page ${source.page_number}` : ''}</button>
              </div>
              <div>{[source.author, source.publication_year, source.document_type].filter(Boolean).join(' | ')}</div>
              <div>{source.excerpt}</div>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
)

const SummarizePage = ({ documents, selectedDocumentId, summary, summaryLoading, handleSummarize }) => {
  const [selectedId, setSelectedId] = useState(selectedDocumentId || documents[0]?.id || '')
  const effectiveSelectedId = documents.some((document) => String(document.id) === String(selectedId)) ? selectedId : (selectedDocumentId || documents[0]?.id || '')

  useEffect(() => {
    if (selectedDocumentId) {
      const timer = window.setTimeout(() => setSelectedId(String(selectedDocumentId)), 0)
      return () => window.clearTimeout(timer)
    }
  }, [selectedDocumentId])

  return (
    <div className="mx-auto max-w-[1000px] space-y-6">
      <BackButton />
      <div>
        <h2 className="text-2xl font-bold text-[#151515]">Research Summaries</h2>
        <p className="mt-1 text-sm text-[#5c564f]">Generate a structured brief from a processed research document.</p>
      </div>

      <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
        <label className="block min-w-0 text-sm font-semibold text-[#4e4743]">
          Research document
          <select
            value={effectiveSelectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="mt-2 block min-h-12 w-full rounded-lg border border-[#d9ddda] bg-white px-4 py-3 text-sm font-normal text-[#1d1b19] outline-none focus:border-[#b2872e] focus:ring-2 focus:ring-[#b2872e]/20"
          >
            {documents.length === 0 ? <option value="">No processed documents available</option> : documents.map((doc) => (
              <option key={doc.id || doc.file_name} value={doc.id || ''}>
                {doc.title || doc.file_name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => handleSummarize(effectiveSelectedId)} disabled={summaryLoading || !effectiveSelectedId} className="inline-flex min-h-12 w-full items-center justify-center rounded-lg bg-[#171916] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#30382f] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto">
          {summaryLoading ? 'Generating summary...' : 'Generate summary'}
        </button>
      </div>

      <div aria-live="polite" className="min-h-48 rounded-lg border border-[#e7dcc6] bg-[#fffdf9] p-5 text-sm leading-7 text-[#393632] whitespace-pre-line sm:p-7">
        {summary || 'The generated research summary will appear here.'}
      </div>
    </div>
  )
}

const UploadPage = ({ canManage, uploadStatus, onUpload }) => {
  const [file, setFile] = useState(null)
  const [metadata, setMetadata] = useState(null)
  const [metadataLoading, setMetadataLoading] = useState(false)
  const [metadataConfirmed, setMetadataConfirmed] = useState(false)
  const [metadataEditing, setMetadataEditing] = useState(false)

  const handleFileChange = async (selectedFile) => {
    setFile(selectedFile)
    setMetadata(null)
    setMetadataConfirmed(false)
    setMetadataEditing(false)
    if (!selectedFile) return

    try {
      setMetadataLoading(true)
      const formData = new FormData()
      formData.append('file', selectedFile)
      setMetadata(await previewUpload(formData))
    } catch (error) {
      setMetadata({ error: error.response?.data?.detail || 'Metadata preview failed.' })
    } finally {
      setMetadataLoading(false)
    }
  }

  const updateMetadata = (field, value) => {
    setMetadata((current) => field === 'author'
      ? { ...current, author: value, authors: value.trim() ? [value.trim()] : [], author_source: value.trim() ? 'Manually entered' : null, author_confidence: null }
      : { ...current, [field]: value })
    setMetadataConfirmed(false)
  }

  const submitUpload = async (event) => {
    event.preventDefault()
    if (!file || !metadata || metadata.error || !metadataConfirmed) return
    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', metadata.title || '')
    formData.append('author', metadata.author || '')
    formData.append('publication_year', metadata.publication_year || '')
    formData.append('authors_json', JSON.stringify(metadata.authors?.length ? metadata.authors : (metadata.author ? [metadata.author] : [])))
    formData.append('author_type', metadata.author_type || '')
    formData.append('author_confidence', metadata.author_confidence || '')
    formData.append('author_source', metadata.author_source || '')
    formData.append('metadata_review_status', 'reviewed')
    await onUpload(formData)
  }

  if (!canManage) return <div className="mx-auto max-w-[800px] rounded-[24px] border border-[#d9ddda] bg-white p-5 text-sm text-[#5a554f]">Document uploads are available to researchers and administrators.</div>

  return (
  <div className="upload-page mx-auto max-w-[800px] rounded-[24px] border border-[#d9ddda] bg-white p-5 shadow-[0_12px_20px_rgba(17,17,17,0.03)]">
    <BackButton />
    <h2 className="text-2xl font-bold text-[#151515]">Upload Document</h2>
    <p className="mt-1 text-sm text-[#5c564f]">Upload a PDF or DOCX. Metadata is extracted from the document and stored with the research record.</p>

    <div className="mt-6 rounded-[20px] border border-dashed border-[#d6b979] bg-[#fffdf9] p-8 text-center">
      <Upload className="mx-auto mb-3 text-[#c99d39]" size={28} />
      <form onSubmit={submitUpload} className="space-y-3 text-left"><input id="document-file" type="file" required accept=".pdf,.docx" onChange={(event) => handleFileChange(event.target.files?.[0] || null)} className="sr-only" />
      <label htmlFor="document-file" className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-[#d9ddda] bg-white px-4 py-5 text-center shadow-sm transition-colors hover:border-[#c99a2e] focus-within:ring-2 focus-within:ring-[#c99a2e]/30"><span className="rounded-lg bg-[#111111] px-4 py-2 text-sm font-semibold text-[#f4ebd1]">{file ? 'Change file' : 'Choose file'}</span><span className="mt-2 max-w-full truncate text-sm font-medium text-[#15191a]">{file ? file.name : 'Select a PDF or DOCX document'}</span>{file && <span className="mt-1 text-xs text-[#5f6867]">{file.type || file.name.split('.').pop().toUpperCase()} | {(file.size / 1024 / 1024).toFixed(2)} MB</span>}</label>
      {file && <button type="button" onClick={() => handleFileChange(null)} className="inline-flex items-center gap-1 text-xs font-semibold text-[#8c3f2d] hover:underline">Remove file</button>}
      {metadataLoading && <p className="rounded-lg bg-[#f5ecdb] px-3 py-2 text-xs text-[#5e5953]">Extracting metadata for confirmation...</p>}
      {metadata?.error && <p className="rounded-lg bg-[#fbe9e5] px-3 py-2 text-xs text-[#8c3f2d]">{metadata.error}</p>}
      {metadata && !metadata.error && <div className="space-y-3 rounded-xl border border-[#d9ddda] bg-white p-4">
        <div className="flex items-start justify-between gap-3"><div><p className="text-sm font-semibold text-[#151515]">Extracted metadata</p><p className="text-xs text-[#5e5953]">Values are extracted automatically from the document before upload.</p></div><button type="button" onClick={() => { setMetadataEditing((editing) => !editing); setMetadataConfirmed(false) }} className="text-xs font-semibold text-[#765711] hover:underline">{metadataEditing ? 'Use extracted values' : 'Edit only if needed'}</button></div>
        <label className="block text-xs font-semibold text-[#4e4743]">Title<input readOnly={!metadataEditing} value={metadata.title || ''} onChange={(event) => updateMetadata('title', event.target.value)} className="mt-1 w-full rounded-lg border border-[#d9ddda] px-3 py-2 text-sm font-normal read-only:bg-[#f7f7f5]" /></label>
        <label className="block text-xs font-semibold text-[#4e4743]">Author<input readOnly={!metadataEditing} value={metadata.author || ''} onChange={(event) => updateMetadata('author', event.target.value)} className="mt-1 w-full rounded-lg border border-[#d9ddda] px-3 py-2 text-sm font-normal read-only:bg-[#f7f7f5]" /></label>
        <label className="block text-xs font-semibold text-[#4e4743]">Publication year<input readOnly={!metadataEditing} value={metadata.publication_year || ''} onChange={(event) => updateMetadata('publication_year', event.target.value)} inputMode="numeric" className="mt-1 w-full rounded-lg border border-[#d9ddda] px-3 py-2 text-sm font-normal read-only:bg-[#f7f7f5]" /></label>
        <p className="text-xs text-[#5e5953]">Author source: {metadata.author_source || 'Not identified'}{metadata.author_confidence ? ` | ${Math.round(metadata.author_confidence * 100)}% confidence` : ''}<br />Year source: {metadata.publication_year_source || 'Not identified'}{metadata.publication_year_confidence ? ` | ${Math.round(metadata.publication_year_confidence * 100)}% confidence` : ''}</p>
        <p className={`rounded-lg px-3 py-2 text-xs ${metadata.metadata_review_status === 'reviewed' ? 'bg-[#eaf5ec] text-[#28613a]' : 'bg-[#fff4d8] text-[#765711]'}`}>{metadata.metadata_review_status === 'reviewed' ? 'Metadata automatically verified from strong document evidence.' : 'Some metadata has weaker or ambiguous evidence. Please verify it before upload.'}</p>
        <label className="flex items-start gap-2 text-xs text-[#4e4743]"><input type="checkbox" checked={metadataConfirmed} onChange={(event) => setMetadataConfirmed(event.target.checked)} className="mt-0.5" />I confirm that the extracted metadata is correct.</label>
      </div>}
      <button type="submit" disabled={!file || !metadata || !!metadata.error || !metadataConfirmed || metadataLoading} className="inline-flex cursor-pointer items-center justify-center rounded-xl bg-[#111111] px-5 py-3 text-sm font-semibold text-[#f4ebd1] disabled:cursor-not-allowed disabled:opacity-40">Upload and process document</button></form>
      <p className="mt-4 text-[0.72rem] text-[#5e5953]">{uploadStatus || 'PDF and DOCX files supported.'}</p>
    </div>
  </div>
)
}

const SavedPage = ({ documents, onView, onViewFile, onDownload, onUnsave, onAsk, onSummarize }) => (
  <div className="mx-auto max-w-[1480px] overflow-hidden rounded-[24px] border border-[#d9ddda] bg-white shadow-[0_12px_20px_rgba(17,17,17,0.04)]">
    <div className="px-5 pt-5"><BackButton /></div>
    <div className="border-b border-[#e1e5e3] px-5 py-5"><h2 className="text-2xl font-bold text-[#151515]">Saved Research</h2><p className="mt-1 text-sm text-[#5c6463]">Documents saved to your personal research collection.</p></div>
    {documents.length === 0 ? <div className="m-5 rounded-xl border border-[#d9ddda] bg-[#f7f9f8] p-4 text-sm text-[#5a554f]">No saved research available.</div> : <div className="overflow-x-auto"><table className="min-w-[900px] w-full text-left text-xs"><thead className="bg-[#eef1ef] text-[#56605e]"><tr>{['Document Title', 'Author', 'Year', 'Date Added', 'Actions'].map((heading) => <th key={heading} className="whitespace-nowrap px-4 py-3 font-semibold">{heading}</th>)}</tr></thead><tbody>{documents.map((doc, index) => <tr key={doc.id || doc.file_name} className={index % 2 ? 'bg-[#fbfcfb]' : 'bg-white'}><td className="max-w-[320px] border-t border-[#e8ecea] px-4 py-3 font-semibold text-[#1b1b1b]">{doc.title || doc.file_name || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{doc.author || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{doc.publication_year || '—'}</td><td className="whitespace-nowrap border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3"><div className="flex items-center gap-1 text-[#5b6563]"><button type="button" onClick={() => onView(doc.id)} title="View details" aria-label={`View details for ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><Eye size={15} /></button><button type="button" onClick={() => onViewFile(doc.id)} title="Open document" aria-label={`Open ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><FileText size={15} /></button><button type="button" onClick={() => onDownload(doc.id)} title="Download" aria-label={`Download ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><Download size={15} /></button><button type="button" onClick={() => onAsk(doc)} title="Ask AI" aria-label={`Ask AI about ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><MessageSquareText size={15} /></button><button type="button" onClick={() => onSummarize(doc.id)} title="Generate summary" aria-label={`Generate summary for ${doc.title || doc.file_name}`} className="rounded-md p-1.5 hover:bg-[#f3e7c7] hover:text-[#8e650f]"><BookOpenText size={15} /></button><button type="button" onClick={() => onUnsave(doc.id)} title="Remove from saved research" aria-label={`Remove ${doc.title || doc.file_name} from saved research`} className="rounded-md px-2 py-1 text-[#8c3f2d] hover:bg-[#fff1ee]">Remove</button></div></td></tr>)}</tbody></table></div>}
  </div>
)

const ProfilePage = ({ user, status, onSave }) => {
  const [profile, setProfile] = useState({ username: user?.username || '', email: user?.email || '', full_name: user?.full_name || '' })
  return (
  <div className="mx-auto max-w-[800px] rounded-[24px] border border-[#e7dcc6] bg-[#f9f7f2] p-5 shadow-[0_12px_20px_rgba(17,17,17,0.03)]">
    <BackButton />
    <h2 className="text-2xl font-bold text-[#151515]">Profile</h2>
    {user ? (
      <form onSubmit={(event) => { event.preventDefault(); onSave(profile) }} className="mt-5 grid gap-4 text-sm text-[#4e4743] sm:grid-cols-2">
        {[['full_name', 'Full name'], ['username', 'Username'], ['email', 'Email']].map(([key, label]) => <label key={key} className="font-semibold text-[#1b1b1b]">{label}<input required={key !== 'full_name'} type={key === 'email' ? 'email' : 'text'} value={profile[key]} onChange={(event) => setProfile({ ...profile, [key]: event.target.value })} className="mt-1 w-full rounded-lg border border-[#d9ddda] bg-white px-3 py-2 font-normal outline-none focus:border-[#c99a2e]" /></label>)}
        <div><dt className="font-semibold text-[#1b1b1b]">Role</dt><dd className="mt-2 capitalize">{user.role || '—'}</dd></div><div><dt className="font-semibold text-[#1b1b1b]">Account status</dt><dd className="mt-2">{user.is_active ? 'Active' : 'Inactive'}</dd></div>
        <div className="sm:col-span-2 flex flex-wrap items-center gap-3"><button type="submit" className="rounded-lg bg-[#111111] px-5 py-3 font-semibold text-[#f4ebd1]">Save profile</button>{status && <span className="text-sm text-[#5f6867]">{status}</span>}</div>
      </form>
    ) : <p className="mt-3 text-sm text-[#5a554f]">No authenticated user is currently available.</p>}
  </div>
  )
}

const SettingsPage = ({ user }) => (
  <div className="mx-auto max-w-[800px] rounded-[24px] border border-[#e7dcc6] bg-[#f9f7f2] p-5 shadow-[0_12px_20px_rgba(17,17,17,0.03)]">
    <BackButton />
    <h2 className="text-2xl font-bold text-[#151515]">Settings</h2>
    <p className="mt-3 text-sm text-[#5a554f]">No configurable settings are exposed by the backend.</p>
    <h3 className="mt-6 border-t border-[#e7dcc6] pt-5 text-sm font-bold text-[#1b1b1b]">Profile</h3>
    {user ? <dl className="mt-3 grid gap-3 text-sm text-[#4e4743] sm:grid-cols-2"><div><dt className="font-semibold text-[#1b1b1b]">Name</dt><dd>{user.full_name || '—'}</dd></div><div><dt className="font-semibold text-[#1b1b1b]">Username</dt><dd>{user.username || '—'}</dd></div><div><dt className="font-semibold text-[#1b1b1b]">Email</dt><dd>{user.email || '—'}</dd></div><div><dt className="font-semibold text-[#1b1b1b]">Phone Number</dt><dd>{user.phone_number || '—'}</dd></div><div><dt className="font-semibold text-[#1b1b1b]">Staff ID</dt><dd>{user.staff_id || '—'}</dd></div><div><dt className="font-semibold text-[#1b1b1b]">Role</dt><dd className="capitalize">{user.role || '—'}</dd></div></dl> : <p className="mt-3 text-sm text-[#5a554f]">No authenticated user is currently available.</p>}
  </div>
)

const AdminShell = ({ user, activePage, setActivePage, onLogout, searchQuery, setSearchQuery, onSearch, documents, documentsLoading, documentsError, onViewDocument, onViewFile, selectedDocument, documentViewUrl, documentDetailLoading, documentDetailError, onCloseDocumentViewer, onDownload, onDeleteDocument, onUpdateDocumentMetadata, onSaveDocument, onAskDocument, onSummarizeDocument, searchResults, searchLoading, handleSearch, uploadStatus, onUpload, summary, summaryLoading, handleSummarize }) => {
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 1024)
  const adminContent = () => {
    if (activePage === 'search') return <SearchPage searchQuery={searchQuery} setSearchQuery={setSearchQuery} searchResults={searchResults} searchLoading={searchLoading} handleSearch={handleSearch} onViewSource={onViewFile} />
    if (activePage === 'summarize') return <SummarizePage documents={documents} summary={summary} summaryLoading={summaryLoading} handleSummarize={handleSummarize} />
    if (activePage === 'upload') return <UploadPage canManage uploadStatus={uploadStatus} onUpload={onUpload} />
    if (activePage === 'document') return <DocumentDetailsPage document={selectedDocument} loading={documentDetailLoading} error={documentDetailError} canManage onUpdate={onUpdateDocumentMetadata} onViewFile={() => selectedDocument && onViewFile(selectedDocument.id)} onDownload={() => selectedDocument && onDownload(selectedDocument.id)} onSave={() => selectedDocument && onSaveDocument(selectedDocument.id)} onAsk={() => selectedDocument && onAskDocument(selectedDocument)} onSummarize={() => selectedDocument && onSummarizeDocument(selectedDocument.id)} />
    if (activePage === 'adminDocuments') return <DocumentsPage documents={documents} loading={documentsLoading} error={documentsError} onView={onViewDocument} onViewFile={onViewFile} onDownload={onDownload} onDelete={onDeleteDocument} onSave={onSaveDocument} onAsk={onAskDocument} onSummarize={onSummarizeDocument} canManage />
    if (activePage === 'adminProcessing') return <AdminProcessingPage documents={documents} loading={documentsLoading} error={documentsError} onView={onViewDocument} />
    if (activePage === 'adminUsers') return <AdminUsersPage />
    if (activePage === 'adminActivity') return <AdminActivityLogPage />
    if (['adminCategories', 'adminTypes', 'adminTopics'].includes(activePage)) return <AdminReferencePage section={activePage} />
    if (activePage === 'settings') return <SettingsPage user={user} />
    return <AdminDashboardPage onViewDocument={onViewDocument} onViewFile={onViewFile} onDownload={onDownload} onDeleteDocument={onDeleteDocument} />
  }


const AdminUsersPage = () => {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '', full_name: '', role: 'viewer' })

  const refreshUsers = async () => {
    try {
      setLoading(true)
      const response = await listUsers()
      setUsers(Array.isArray(response?.users) ? response.users : [])
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to load users.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(refreshUsers, 0)
    return () => window.clearTimeout(timer)
  }, [])

  const changeRole = async (userId, role) => {
    try { await updateUserRole(userId, role); await refreshUsers() } catch (requestError) { setError(requestError.response?.data?.detail || 'Unable to update role.') }
  }

  const changeStatus = async (userId, isActive) => {
    try { await updateUserStatus(userId, isActive); await refreshUsers() } catch (requestError) { setError(requestError.response?.data?.detail || 'Unable to update status.') }
  }

  const removeUser = async (userId) => {
    if (!window.confirm('Delete this user account? This action cannot be undone.')) return
    try { await deleteUser(userId); await refreshUsers() } catch (requestError) { setError(requestError.response?.data?.detail || 'Unable to delete user.') }
  }

  const createUser = async (event) => {
    event.preventDefault()
    try {
      setCreating(true)
      await createAdminUser(form)
      setForm({ username: '', email: '', password: '', full_name: '', role: 'viewer' })
      setShowCreateForm(false)
      await refreshUsers()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to register user.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="mx-auto max-w-[1480px] overflow-hidden rounded-[24px] border border-[#d9ddda] bg-white shadow-[0_12px_20px_rgba(17,17,17,0.04)]">
      <div className="flex flex-col gap-4 border-b border-[#e1e5e3] px-5 py-5 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-2xl font-bold text-[#151515]">User Management</h2><p className="mt-1 text-sm text-[#5c6463]">Manage real user accounts, access levels, and account status.</p></div><button type="button" onClick={() => setShowCreateForm((visible) => !visible)} className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[#111111] px-4 py-2.5 text-sm font-semibold text-[#f4ebd1] hover:bg-[#2b2b2b]"><UserPlus size={16} /> Register new user</button></div>
      {error && <div className="m-5 rounded-xl border border-[#e7cfc6] bg-[#fff8f5] p-4 text-sm text-[#8c3f2d]">{error}</div>}
      {showCreateForm && <form onSubmit={createUser} className="m-5 rounded-2xl border border-[#e7dcc6] bg-[#f9f7f2] p-4"><div className="mb-4 flex items-center justify-between"><div><h3 className="text-base font-bold text-[#151515]">Register new user</h3><p className="mt-1 text-xs text-[#71807b]">The account will be active immediately with the selected role.</p></div><button type="button" onClick={() => setShowCreateForm(false)} aria-label="Close registration form" className="rounded-lg p-2 text-[#53615d] hover:bg-white"><X size={17} /></button></div><div className="grid gap-3 md:grid-cols-2"><label className="text-xs font-semibold text-[#27312f]">Full name<input required value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} className="mt-1 w-full rounded-lg border border-[#d9ddda] bg-white px-3 py-2.5 text-sm font-normal outline-none focus:border-[#c99a2e]" /></label><label className="text-xs font-semibold text-[#27312f]">Username<input required value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} className="mt-1 w-full rounded-lg border border-[#d9ddda] bg-white px-3 py-2.5 text-sm font-normal outline-none focus:border-[#c99a2e]" /></label><label className="text-xs font-semibold text-[#27312f]">Email<input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} className="mt-1 w-full rounded-lg border border-[#d9ddda] bg-white px-3 py-2.5 text-sm font-normal outline-none focus:border-[#c99a2e]" /></label><label className="text-xs font-semibold text-[#27312f]">Temporary password<input required minLength={8} type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} className="mt-1 w-full rounded-lg border border-[#d9ddda] bg-white px-3 py-2.5 text-sm font-normal outline-none focus:border-[#c99a2e]" /></label><label className="text-xs font-semibold text-[#27312f]">Role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} className="mt-1 w-full rounded-lg border border-[#d9ddda] bg-white px-3 py-2.5 text-sm font-normal capitalize outline-none focus:border-[#c99a2e]"><option value="viewer">Viewer</option><option value="researcher">Researcher</option><option value="admin">Admin</option></select></label></div><button type="submit" disabled={creating} className="mt-4 rounded-lg bg-[#c99a2e] px-4 py-2.5 text-sm font-semibold text-[#111111] disabled:opacity-60">{creating ? 'Registering...' : 'Create account'}</button></form>}
      {loading ? <div className="p-6 text-sm text-[#5a554f]">Loading users...</div> : users.length === 0 ? <div className="m-5 rounded-xl border border-[#d9ddda] bg-[#f7f9f8] p-4 text-sm text-[#5a554f]">No users found.</div> : (
        <div className="overflow-x-auto"><table className="min-w-[1050px] w-full text-left text-xs"><thead className="bg-[#eef1ef] text-[#56605e]"><tr>{['Name', 'Email', 'Role', 'Status', 'Created Date', 'Last Login', 'Actions'].map((heading) => <th key={heading} className="whitespace-nowrap px-4 py-3 font-semibold">{heading}</th>)}</tr></thead><tbody>{users.map((entry, index) => <tr key={entry.id} className={index % 2 ? 'bg-[#fbfcfb]' : 'bg-white'}><td className="border-t border-[#e8ecea] px-4 py-3 font-semibold text-[#1b1b1b]">{entry.full_name || entry.username}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{entry.email}</td><td className="border-t border-[#e8ecea] px-4 py-3"><select value={entry.role} onChange={(event) => changeRole(entry.id, event.target.value)} className="rounded-lg border border-[#d9ddda] bg-white px-2 py-1.5 text-xs capitalize outline-none focus:border-[#c99a2e]"><option value="admin">Admin</option><option value="researcher">Researcher</option><option value="viewer">Viewer</option></select></td><td className="border-t border-[#e8ecea] px-4 py-3"><label className="inline-flex items-center gap-2 text-[#4f5957]"><input type="checkbox" checked={Boolean(entry.is_active)} onChange={(event) => changeStatus(entry.id, event.target.checked)} />{entry.is_active ? 'Active' : 'Inactive'}</label></td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{entry.created_at ? new Date(entry.created_at).toLocaleDateString() : '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{entry.last_login ? new Date(entry.last_login).toLocaleString() : 'Never'}</td><td className="border-t border-[#e8ecea] px-4 py-3"><button type="button" onClick={() => removeUser(entry.id)} className="rounded-lg border border-[#e7cfc6] bg-[#fff7f4] px-2 py-1.5 text-[0.68rem] font-semibold text-[#8c3f2d] hover:bg-[#fceae5]">Delete</button></td></tr>)}</tbody></table></div>
      )}
    </div>
  )
}

const AdminProcessingPage = ({ documents, loading, error, onView }) => {
  const statuses = ['pending', 'processing', 'completed', 'failed']
  return (
    <div className="mx-auto max-w-[1480px] overflow-hidden rounded-[24px] border border-[#d9ddda] bg-white shadow-[0_12px_20px_rgba(17,17,17,0.04)]">
      <div className="border-b border-[#e1e5e3] px-5 py-5"><h2 className="text-2xl font-bold text-[#151515]">Document Processing</h2><p className="mt-1 text-sm text-[#5c6463]">Monitor the real processing pipeline and identify failed records.</p></div>
      {loading ? <div className="p-6 text-sm text-[#5a554f]">Loading processing records...</div> : error ? <div className="m-5 rounded-xl border border-[#e7cfc6] bg-[#fff8f5] p-4 text-sm text-[#8c3f2d]">{error}</div> : <div className="grid gap-4 p-5 md:grid-cols-4">{statuses.map((status) => { const rows = documents.filter((document) => String(document.processing_status || '').toLowerCase() === status); return <div key={status} className="rounded-xl border border-[#d9ddda] bg-[#f8faf9] p-4"><div className="flex items-center justify-between"><span className="text-xs font-semibold uppercase tracking-[0.08em] text-[#53615d]">{status}</span><span className="text-2xl font-bold text-[#17201f]">{rows.length}</span></div><div className="mt-4 space-y-2">{rows.length === 0 ? <div className="text-xs text-[#71807b]">No documents</div> : rows.slice(0, 5).map((document) => <button key={document.id} type="button" onClick={() => onView(document.id)} className="block w-full truncate rounded-lg border border-[#e1e5e3] bg-white px-2 py-2 text-left text-xs text-[#27312f] hover:border-[#c99a2e]">{document.title || document.file_name}</button>)}</div></div> })}</div>}
    </div>
  )
}

const AdminReferencePage = ({ section }) => {
  const [data, setData] = useState(null)
  const labels = { adminCategories: ['Categories', 'categories'], adminTypes: ['Document Types', 'documents_by_type'], adminTopics: ['Research Topics', 'documents_by_topic'], adminActivity: ['Activity / Audit Logs', 'recent_activity'] }
  const [title, key] = labels[section] || ['Administration', '']

  useEffect(() => {
    const timer = window.setTimeout(() => { getAdminDashboard().then(setData).catch(() => setData(null)) }, 0)
    return () => window.clearTimeout(timer)
  }, [section])

  const entries = data?.[key] || []
  return <div className="mx-auto max-w-[1100px] rounded-[24px] border border-[#e7dcc6] bg-[#f9f7f2] p-5 shadow-[0_12px_20px_rgba(17,17,17,0.03)]"><h2 className="text-2xl font-bold text-[#151515]">{title}</h2><p className="mt-1 text-sm text-[#5c564f]">Data-backed administration records from the current knowledge hub.</p><div className="mt-5 space-y-2">{entries.length === 0 ? <div className="rounded-xl border border-[#d9ddda] bg-white p-4 text-sm text-[#5a554f]">No records are available for this section.</div> : entries.map((entry, index) => <div key={`${entry.label || entry.kind}-${index}`} className="flex items-center justify-between rounded-xl border border-[#e7dcc6] bg-white px-4 py-3 text-sm"><span className="text-[#1b1b1b]">{entry.label || entry.text}</span><span className="font-semibold text-[#53615d]">{entry.count ?? (entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '')}</span></div>)}</div></div>
}

const getLocalDate = () => {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

const AdminActivityLogPage = () => {
  const [activityDate, setActivityDate] = useState(getLocalDate)
  const [activityRows, setActivityRows] = useState([])
  const [activityLoading, setActivityLoading] = useState(true)
  const [notificationCount, setNotificationCount] = useState(0)
  const [notificationItems, setNotificationItems] = useState([])
  const [notificationOpen, setNotificationOpen] = useState(false)
  const [error, setError] = useState('')

  const loadActivityLogs = useCallback(async (selectedDate = activityDate) => {
    try {
      setActivityLoading(true)
      const response = await getAdminActivityLogs(selectedDate)
      setActivityRows(Array.isArray(response?.items) ? response.items : [])
      setError('')
    } catch (requestError) {
      console.error('Failed to load activity logs:', requestError)
      setActivityRows([])
      setError(requestError.response?.data?.detail || 'Unable to load activity history.')
    } finally {
      setActivityLoading(false)
    }
  }, [activityDate])

  const loadNotifications = useCallback(async () => {
    try {
      const response = await getAdminActivityNotifications()
      setNotificationCount(Number(response?.unreviewed_count ?? response?.count ?? 0))
      setNotificationItems(Array.isArray(response?.items) ? response.items : [])
    } catch (requestError) {
      console.error('Failed to load notifications:', requestError)
      setNotificationCount(0)
      setNotificationItems([])
    }
  }, [])

  useEffect(() => {
    const loadAuditPage = async () => {
      await loadActivityLogs(activityDate)
      await loadNotifications()
    }
    loadAuditPage()
  }, [activityDate, loadActivityLogs, loadNotifications])

  const reviewActivity = async (activityId) => {
    try {
      await markActivityReviewed(activityId)
      await Promise.all([loadNotifications(), loadActivityLogs(activityDate)])
    } catch (requestError) {
      console.error('Failed to review activity:', requestError)
      setError(requestError.response?.data?.detail || 'Unable to mark activity as reviewed.')
    }
  }

  const reviewAllNotifications = async () => {
    try {
      await Promise.all(notificationItems.map((item) => markActivityReviewed(item.id)))
      await Promise.all([loadNotifications(), loadActivityLogs(activityDate)])
    } catch (requestError) {
      console.error('Failed to review notifications:', requestError)
      setError(requestError.response?.data?.detail || 'Unable to review all notifications.')
    }
  }

  const exportReport = async () => {
    try {
      const pdfBlob = await exportAdminReport(activityDate)
      const url = URL.createObjectURL(pdfBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `admin-activity-report-${activityDate}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to export the activity report.')
    }
  }

  return (
    <div className="mx-auto max-w-[1480px] overflow-hidden rounded-[24px] border border-[#d9ddda] bg-white shadow-[0_12px_20px_rgba(17,17,17,0.04)]">
      <div className="flex flex-col gap-3 border-b border-[#e1e5e3] px-5 py-5 lg:flex-row lg:items-end lg:justify-between">
        <div><h2 className="text-2xl font-bold text-[#151515]">Activity / Audit Logs</h2><p className="mt-1 text-sm text-[#5c6463]">Permanent activity history from the audit database.</p></div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-2 rounded-lg border border-[#d9ddda] bg-white px-3 py-2 text-xs text-[#53615d]"><CalendarDays size={14} /><input type="date" value={activityDate} onChange={(event) => setActivityDate(event.target.value)} className="bg-transparent text-[#2d3736] outline-none" /></label>
          <button type="button" onClick={exportReport} disabled={activityRows.length === 0} className="rounded-lg bg-[#c99a2e] px-3 py-2 text-xs font-semibold text-[#111111] disabled:opacity-50">Export Report</button>
          <div className="relative">
            <button type="button" onClick={() => setNotificationOpen((open) => !open)} className="relative inline-flex h-10 w-10 items-center justify-center rounded-full border border-[#d9ddda] bg-white text-[#1b1b1b] shadow-sm hover:border-[#c99a2e]" aria-label="Open admin notifications"><Bell size={18} />{notificationCount > 0 && <span className="absolute -right-1 -top-1 inline-flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[#b32020] px-1 text-[0.62rem] font-bold text-white">{notificationCount}</span>}</button>
            {notificationOpen && <div className="absolute right-0 top-12 z-20 w-80 rounded-xl border border-[#d9ddda] bg-white p-3 shadow-xl"><div className="mb-2 flex items-center justify-between"><strong className="text-sm text-[#151515]">New activity notifications</strong>{notificationItems.length > 0 && <button type="button" onClick={reviewAllNotifications} className="text-[0.65rem] font-semibold text-[#8e650f]">Review shown</button>}</div><div className="max-h-72 space-y-2 overflow-y-auto">{notificationItems.length === 0 ? <div className="text-xs text-[#6a706d]">No new notifications.</div> : notificationItems.map((item) => <div key={item.id} className="rounded-lg border border-[#e7dcc6] bg-[#fffdf8] p-2"><div className="text-[0.72rem] font-semibold text-[#1b1b1b]">{item.activity}</div><div className="mt-1 text-[0.65rem] text-[#53615d]">{item.user} • {item.role}</div><div className="mt-1 text-[0.65rem] text-[#5a554f]">{item.resource} • {item.date} {item.time}</div><button type="button" onClick={() => reviewActivity(item.id)} className="mt-2 rounded-md bg-[#111111] px-2 py-1 text-[0.6rem] font-semibold text-[#f4ebd1]">Review</button></div>)}</div></div>}
          </div>
        </div>
      </div>
      {error && <div className="m-5 rounded-xl border border-[#e7cfc6] bg-[#fff8f5] p-4 text-sm text-[#8c3f2d]">{error}</div>}
      <div className="border-b border-[#e8ecea] px-5 py-3 text-sm text-[#53615d]">{activityLoading ? 'Loading activities...' : `${activityRows.length} activities recorded on ${activityDate}`}</div>
      <div className="overflow-x-auto">
        <table className="min-w-[1100px] w-full text-left text-xs"><thead className="bg-[#eef1ef] text-[#56605e]"><tr>{['Date', 'Time', 'User', 'Role', 'Activity', 'Resource', 'Details', 'Status'].map((heading) => <th key={heading} className="px-4 py-3 font-semibold">{heading}</th>)}</tr></thead><tbody>{activityRows.length === 0 && !activityLoading ? <tr><td colSpan="8" className="px-4 py-8 text-center text-sm text-[#71807b]">No activities recorded for this date.</td></tr> : activityRows.map((item, index) => <tr key={item.id} className={index % 2 ? 'bg-[#fbfcfb]' : 'bg-white'}><td className="border-t border-[#e8ecea] px-4 py-3">{item.date}</td><td className="border-t border-[#e8ecea] px-4 py-3">{item.time}</td><td className="border-t border-[#e8ecea] px-4 py-3 font-semibold">{item.user}</td><td className="border-t border-[#e8ecea] px-4 py-3 capitalize">{item.role}</td><td className="border-t border-[#e8ecea] px-4 py-3">{item.activity}</td><td className="border-t border-[#e8ecea] px-4 py-3">{item.resource}</td><td className="max-w-[320px] border-t border-[#e8ecea] px-4 py-3">{item.details}</td><td className="border-t border-[#e8ecea] px-4 py-3"><span className={item.reviewed ? 'text-[#158b4d]' : 'font-semibold text-[#b32020]'}>{item.status}</span></td></tr>)}</tbody></table>
      </div>
    </div>
  )
}
  return (
    <div className="app-shell min-h-screen text-[#111111]">
      <div className="flex min-h-screen">
        <aside className={`fixed inset-y-0 left-0 z-50 transition-transform duration-300 lg:static lg:inset-auto lg:flex ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:hidden'}`}>
          <Sidebar activePage={activePage} setActivePage={setActivePage} user={user} adminMode />
        </aside>
        {sidebarOpen && <div className="fixed inset-0 z-40 bg-black/35 lg:hidden" onClick={() => setSidebarOpen(false)} />}
        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <Header onMenuClick={() => setSidebarOpen((open) => !open)} user={user} searchQuery={searchQuery} setSearchQuery={setSearchQuery} onSearch={onSearch} onLogout={onLogout} onProfileClick={() => setActivePage('settings')} />
          <main className="flex-1 overflow-x-hidden px-4 pb-3 pt-3 sm:px-5 lg:px-6">{adminContent()}</main>
          {documentViewUrl && <div className="fixed inset-0 z-[60] bg-black/70 p-4"><div className="mx-auto flex h-full max-w-6xl flex-col overflow-hidden rounded-xl bg-white"><div className="flex items-center justify-between border-b border-[#d9ddda] px-4 py-3"><span className="text-sm font-semibold">Document viewer</span><button type="button" onClick={onCloseDocumentViewer} className="rounded-md bg-[#111111] px-3 py-2 text-xs font-semibold text-white">Close</button></div><iframe title="Research document viewer" src={documentViewUrl} className="min-h-0 flex-1" /></div></div>}
          <TanzaniaStripe position="bottom" />
          <Footer />
        </div>
      </div>
    </div>
  )
}
  const AdminActivityChart = ({ data, onSelect }) => {
    const maximum = Math.max(...data.map((entry) => entry.count), 1)
    return <div className="relative h-44 border-b border-l border-[#d8dfdc] px-3 pb-0 pt-3"><div className="pointer-events-none absolute inset-x-3 top-3 bottom-6 flex flex-col justify-between"><span className="border-t border-dashed border-[#e5ebe8]" /><span className="border-t border-dashed border-[#e5ebe8]" /><span className="border-t border-dashed border-[#e5ebe8]" /><span className="border-t border-dashed border-[#e5ebe8]" /></div><div className="relative flex h-full items-end gap-1">{data.length === 0 ? <div className="pb-4 pl-3 text-sm text-[#71807b]">No activity data available.</div> : data.map((entry) => <button type="button" key={entry.date} onClick={() => onSelect?.({ label: entry.date, count: entry.count, source: 'Persisted audit activity entries' })} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1"><span className="text-[0.6rem] font-semibold text-[#17201f]">{entry.count || ''}</span><span className="w-full max-w-5 rounded-t-md bg-[#537b9e] transition-all hover:bg-[#315c80]" style={{ height: `${Math.max((entry.count / maximum) * 78, entry.count ? 8 : 2)}%` }} title={`${entry.date}: ${entry.count} activities`} /><span className="truncate text-[0.55rem] text-[#53615d]">{entry.date.slice(5)}</span></button>)}</div></div>
  }

  const AdminQuestionChart = ({ data, onSelect }) => {
    const width = 640
    const height = 190
    const maximum = Math.max(...data.map((entry) => entry.count), 1)
    const points = data.map((entry, index) => `${(index / Math.max(data.length - 1, 1)) * width},${height - (entry.count / maximum) * 150 - 15}`).join(' ')
    return data.length === 0 ? <div className="flex h-44 items-center justify-center text-sm text-[#71807b]">No AI question activity available.</div> : <button type="button" onClick={() => onSelect?.({ label: 'AI questions over the last 30 days', count: data.reduce((total, entry) => total + entry.count, 0), source: 'Persisted AI question timestamps' })} className="block w-full text-left"><div className="overflow-hidden"><svg viewBox={`0 0 ${width} ${height}`} className="h-44 w-full" role="img" aria-label="AI questions over the last 30 days"><line x1="0" y1="30" x2={width} y2="30" stroke="#e5ebe8" strokeDasharray="5 5" /><line x1="0" y1="75" x2={width} y2="75" stroke="#e5ebe8" strokeDasharray="5 5" /><line x1="0" y1="120" x2={width} y2="120" stroke="#e5ebe8" strokeDasharray="5 5" /><line x1="0" y1="175" x2={width} y2="175" stroke="#d8dfdc" /><polyline points={points} fill="none" stroke="#d5a62f" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /><polyline points={`0,175 ${points} ${width},175`} fill="#d5a62f" fillOpacity="0.12" stroke="none" /></svg><div className="flex justify-between text-[0.65rem] text-[#71807b]"><span>{data[0].date}</span><span>{data[Math.floor(data.length / 2)]?.date}</span><span>{data[data.length - 1].date}</span></div></div></button>
  }

  const AdminTopicChart = ({ data, onSelect }) => {
    const visibleData = data.slice(0, 7)
    const maximum = Math.max(...visibleData.map((entry) => entry.count), 1)
    return <div className="space-y-0.5">{visibleData.length === 0 ? <div className="text-sm text-[#71807b]">No topic data available.</div> : visibleData.map((entry) => <button type="button" key={entry.label} onClick={() => onSelect?.({ label: entry.label, count: entry.count, source: 'Active documents linked to this research topic' })} className="block w-full text-left"><div className="mb-0 flex justify-between gap-3 text-[0.68rem]"><span className="truncate text-[#27312f]">{entry.label}</span><span className="font-semibold text-[#53615d]">{entry.count}</span></div><div className="h-1 rounded-full bg-[#e5ebe8]"><div className="h-full rounded-full bg-[#537b9e] transition-all hover:bg-[#315c80]" style={{ width: `${Math.max((entry.count / maximum) * 100, 5)}%` }} /></div></button>)}</div>
  }

  const AdminTypeChart = ({ data, onSelect }) => {
    const total = data.reduce((sum, entry) => sum + entry.count, 0)
    let cursor = 0
    const colors = ['#c99a2e', '#537b9e', '#1b9a62', '#8f6b9d', '#c66d4b', '#66736e']
    const gradient = total ? data.map((entry, index) => { const start = cursor; cursor += (entry.count / total) * 100; return `${colors[index % colors.length]} ${start}% ${cursor}%` }).join(', ') : '#e5ebe8 0% 100%'
    return <div className="grid items-center gap-5 sm:grid-cols-[150px_1fr]"><div className="relative mx-auto h-36 w-36 rounded-full" style={{ background: `conic-gradient(${gradient})` }} role="img" aria-label="Documents by document type"><div className="absolute inset-6 grid place-items-center rounded-full bg-white text-center"><strong className="text-xl text-[#17201f]">{total}</strong><span className="text-[0.58rem] text-[#71807b]">Total</span></div></div><div className="space-y-2">{data.length === 0 ? <div className="text-sm text-[#71807b]">No document-type data available.</div> : data.map((entry, index) => <button type="button" key={entry.label} onClick={() => onSelect?.({ label: entry.label, count: entry.count, source: 'Active documents assigned to this document type' })} className="flex w-full items-center justify-between gap-3 text-left text-xs"><span className="flex min-w-0 items-center gap-2 truncate"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: colors[index % colors.length] }} />{entry.label}</span><span className="font-semibold text-[#53615d]">{entry.count}</span></button>)}</div></div>
  }

  const AdminDonutChart = ({ data, title, onSelect }) => {
    const total = data.reduce((sum, entry) => sum + entry.count, 0)
    let cursor = 0
    const colors = ['#1b9a62', '#537b9e', '#c99a2e', '#c66d4b', '#8f6b9d']
    const gradient = total ? data.map((entry, index) => { const start = cursor; cursor += (entry.count / total) * 100; return `${colors[index % colors.length]} ${start}% ${cursor}%` }).join(', ') : '#e5ebe8 0% 100%'
    return <div className="grid items-center gap-5 sm:grid-cols-[150px_1fr]"><div className="relative mx-auto h-36 w-36 rounded-full" style={{ background: `conic-gradient(${gradient})` }} role="img" aria-label={title}><div className="absolute inset-5 flex flex-col items-center justify-center rounded-full bg-white text-center"><strong className="text-2xl text-[#17201f]">{total}</strong><span className="text-[0.6rem] uppercase tracking-[0.1em] text-[#71807b]">Total</span></div></div><div className="space-y-2">{data.length === 0 ? <div className="text-sm text-[#71807b]">No status data available.</div> : data.map((entry, index) => <button type="button" key={entry.label} onClick={() => onSelect?.({ label: entry.label, count: entry.count, source: title })} className="flex w-full items-center justify-between gap-3 text-left text-xs"><span className="flex min-w-0 items-center gap-2 capitalize"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: colors[index % colors.length] }} />{entry.label}</span><span className="font-semibold text-[#53615d]">{entry.count} ({total ? Math.round((entry.count / total) * 100) : 0}%)</span></button>)}</div></div>
  }

const AdminDashboardPage = ({ onViewDocument, onViewFile, onDownload, onDeleteDocument }) => {
  const [summary, setSummary] = useState(null)
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedInsight, setSelectedInsight] = useState(null)
  const [dateRange, setDateRange] = useState('30')
  const [activityDate, setActivityDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [notificationCount, setNotificationCount] = useState(0)
  const [notificationItems, setNotificationItems] = useState([])
  const [notificationOpen, setNotificationOpen] = useState(false)

  const refreshAdminData = async () => {
    try {
      setLoading(true)
      const dashboardDays = dateRange === 'all' ? 3650 : Number(dateRange)
      const dashboardData = await getAdminDashboard(dashboardDays)
      const userData = await listUsers()
      setSummary(dashboardData)
      setUsers(Array.isArray(userData?.users) ? userData.users : [])
      setError('')
    } catch (fetchError) {
      console.error('Failed to load admin dashboard:', fetchError)
      const detail = fetchError.response?.data?.detail
      setError(Array.isArray(detail) ? detail.map((item) => item.msg).join(', ') : (detail || 'Unable to load admin dashboard data.'))
    } finally {
      setLoading(false)
    }
  }

  const loadNotifications = useCallback(async () => {
    try {
      const response = await getAdminActivityNotifications()
      const nextCount = Number(response?.unreviewed_count ?? response?.count ?? 0)
      setNotificationCount(nextCount)
      setNotificationItems(Array.isArray(response?.items) ? response.items : [])
    } catch (requestError) {
      console.error('Failed to load notifications:', requestError)
      setNotificationCount(0)
      setNotificationItems([])
    }
  }, [])

  useEffect(() => {
    const loadAdminData = window.setTimeout(() => {
      refreshAdminData()
    }, 0)
    return () => window.clearTimeout(loadAdminData)
  // refreshAdminData intentionally closes over the selected server-side range.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange])

  useEffect(() => {
    const timer = window.setTimeout(loadNotifications, 0)
    return () => window.clearTimeout(timer)
  }, [loadNotifications])

  useEffect(() => {
    const rows = document.querySelectorAll('.admin-dashboard-page table tbody tr')
    ;(summary?.recent_documents || []).forEach((entry, index) => {
      const uploaderCell = rows[index]?.children?.[6]
      if (uploaderCell) uploaderCell.textContent = entry.uploaded_by || entry.uploader_email || 'Unknown user'
    })
  }, [summary])

  const handleNotificationReview = async (activityId) => {
    try {
      await markActivityReviewed(activityId)
      await loadNotifications()
    } catch (requestError) {
      console.error('Failed to review activity:', requestError)
    }
  }

  const handleRoleChange = async (userId, role) => {
    try {
      await updateUserRole(userId, role)
      await refreshAdminData()
    } catch (updateError) {
      console.error('Failed to update user role:', updateError)
      setError(updateError.response?.data?.detail || 'Unable to update user role.')
    }
  }

  const handleStatusChange = async (userId, isActive) => {
    try {
      await updateUserStatus(userId, isActive)
      await refreshAdminData()
    } catch (updateError) {
      console.error('Failed to update user status:', updateError)
      setError(updateError.response?.data?.detail || 'Unable to update user status.')
    }
  }

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Delete this user account? This action cannot be undone.')) return

    try {
      await deleteUser(userId)
      await refreshAdminData()
    } catch (deleteError) {
      console.error('Failed to delete user:', deleteError)
      setError(deleteError.response?.data?.detail || 'Unable to delete user.')
    }
  }

  const adminStats = summary?.stats || {}
  const roleBreakdown = summary?.role_breakdown || []
  const maximumRoleCount = Math.max(...roleBreakdown.map((entry) => entry.count), 1)
  const activeRate = adminStats.total_users ? Math.round((adminStats.active_users / adminStats.total_users) * 100) : 0
  const statCards = [
    { label: 'Total Users', value: adminStats.total_users, icon: Users, tone: 'gold' },
    { label: 'Active Users', value: adminStats.active_users, icon: UserCheck, tone: 'green' },
    { label: 'Total Research Documents', value: adminStats.total_documents, icon: FileText, tone: 'blue' },
    { label: 'Processed Documents', value: adminStats.processed_documents, icon: FileCheck2, tone: 'blue' },
    { label: 'Pending Documents', value: adminStats.pending_documents, icon: FileClock, tone: 'gold' },
    { label: 'Failed Documents', value: adminStats.failed_documents, icon: FileX2, tone: 'red' },
  ]
  const exportReport = async () => {
    try {
      const pdfBlob = await exportAdminReport(activityDate)
      const url = URL.createObjectURL(pdfBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `admin-activity-report-${activityDate || new Date().toISOString().slice(0, 10)}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch (requestError) {
      console.error('Failed to export activity report:', requestError)
      setError(requestError.response?.data?.detail || 'Unable to export the activity report.')
    }
  }

  return (
    <div className="admin-dashboard-page mx-auto max-w-[1480px] space-y-3 rounded-[18px] border border-[#d9ddda] bg-[#f7f9f8] p-3 shadow-[0_12px_20px_rgba(17,17,17,0.03)] sm:p-4">
      <div className="flex flex-col gap-3 border-b border-[#e7dcc6] pb-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#151515]">Administrator Dashboard</h2>
          <p className="mt-1 text-sm text-[#5c564f]">System overview and management analytics.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-2 rounded-lg border border-[#d9ddda] bg-white px-3 py-2 text-xs text-[#53615d]"><CalendarDays size={14} /><select value={dateRange} onChange={(event) => setDateRange(event.target.value)} className="bg-transparent outline-none"><option value="30">Last 30 days</option><option value="90">Last 90 days</option><option value="365">Last 12 months</option><option value="all">All available data</option></select></label>
          <label className="flex items-center gap-2 rounded-lg border border-[#d9ddda] bg-white px-3 py-2 text-xs text-[#53615d]"><CalendarDays size={14} /><input type="date" value={activityDate} onChange={(event) => setActivityDate(event.target.value)} className="bg-transparent text-[#2d3736] outline-none" /></label>
          <button type="button" onClick={exportReport} disabled={!summary} className="rounded-lg bg-[#c99a2e] px-3 py-2 text-xs font-semibold text-[#111111] disabled:opacity-50">Export Report</button>
          <div className="relative">
            <button type="button" onClick={() => setNotificationOpen((open) => !open)} className="relative inline-flex h-10 w-10 items-center justify-center rounded-full border border-[#d9ddda] bg-white text-[#1b1b1b] shadow-sm hover:border-[#c99a2e]" aria-label="Open admin notifications">
              <Bell size={18} />
              {notificationCount > 0 && <span className="absolute -right-1 -top-1 inline-flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[#b32020] px-1 text-[0.62rem] font-bold text-white">{notificationCount}</span>}
            </button>
            {notificationOpen && (
              <div className="absolute right-0 top-12 z-20 w-80 rounded-xl border border-[#d9ddda] bg-white p-3 shadow-xl">
                <div className="mb-2 flex items-center justify-between"><strong className="text-sm text-[#151515]">New activity notifications</strong><span className="text-[0.7rem] text-[#53615d]">{notificationCount} unread</span></div>
                <div className="max-h-64 space-y-2 overflow-y-auto">
                  {notificationItems.length === 0 ? <div className="text-xs text-[#6a706d]">No new notifications.</div> : notificationItems.map((item) => (
                    <div key={item.id} className="rounded-lg border border-[#e7dcc6] bg-[#fffdf8] p-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-[0.72rem] font-semibold text-[#1b1b1b]">{item.activity}</div>
                          <div className="mt-1 text-[0.65rem] text-[#53615d]">{item.user} • {item.role}</div>
                        </div>
                        <button type="button" onClick={() => handleNotificationReview(item.id)} className="rounded-md bg-[#111111] px-2 py-1 text-[0.6rem] font-semibold text-[#f4ebd1]">Review</button>
                      </div>
                      <div className="mt-1 text-[0.65rem] text-[#5a554f]">{item.resource} • {item.date} {item.time}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {error && <div className="rounded-xl border border-[#e7cfc6] bg-[#fff8f5] p-4 text-sm text-[#8c3f2d]">{error}</div>}

      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
        {statCards.map(({ label, value, icon: Icon, tone }) => <button type="button" key={label} onClick={() => setSelectedInsight({ label, count: value ?? 0, source: 'Admin analytics database query' })} className="rounded-xl border border-[#e1e5e3] bg-white p-3 text-left shadow-[0_5px_12px_rgba(17,17,17,0.04)] transition-transform hover:-translate-y-0.5"><div className="flex items-start justify-between gap-2"><span className="block text-[0.62rem] font-semibold text-[#53615d]">{label}</span><span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${tone === 'green' ? 'bg-[#e5f7ed] text-[#16965b]' : tone === 'blue' ? 'bg-[#e8f2ff] text-[#287bd4]' : tone === 'red' ? 'bg-[#ffebeb] text-[#e64545]' : 'bg-[#fff4dc] text-[#d99a13]'}`}><Icon size={15} /></span></div><strong className="mt-1 block text-2xl leading-none text-[#17201f]">{value ?? 0}</strong><span className="mt-2 block text-[0.58rem] text-[#71807b]">{tone === 'green' || tone === 'blue' ? 'Live from backend' : 'Current total'}</span></button>)}
      </div>

      {loading ? (
        <div className="rounded-xl border border-[#e7dcc6] bg-[#fffdf9] p-5 text-sm text-[#5a554f]">Loading administrator data...</div>
      ) : (
        <>
          <div className="hidden grid gap-6 xl:grid-cols-[1.1fr_1.4fr]">
            <div className="rounded-[20px] border border-[#e7dcc6] bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-bold text-[#151515]">Role distribution</h3>
                  <p className="mt-1 text-xs text-[#71807b]">Current accounts by access level</p>
                </div>
                <div className="text-right"><div className="text-2xl font-bold text-[#17201f]">{activeRate}%</div><div className="text-[0.62rem] uppercase tracking-[0.08em] text-[#71807b]">active rate</div></div>
              </div>
              <div className="mt-6 flex h-44 items-end gap-5 border-b border-l border-[#d8dfdc] px-4 pb-0 pt-4">
                {roleBreakdown.length === 0 ? (
                  <div className="pb-4 text-sm text-[#5a554f]">No role data available.</div>
                ) : (
                  roleBreakdown.map((entry) => (
                    <div key={entry.role} className="flex h-full min-w-16 flex-1 flex-col items-center justify-end gap-2">
                      <span className="text-xs font-semibold text-[#17201f]">{entry.count}</span>
                      <button type="button" onClick={() => setSelectedInsight({ label: `${entry.role} users`, count: entry.count, source: 'Users table grouped by role' })} className="w-full max-w-20 rounded-t-lg bg-[#d5b15e] transition-all hover:bg-[#b58f32]" style={{ height: `${Math.max((entry.count / maximumRoleCount) * 78, 8)}%` }} title={`${entry.role}: ${entry.count}`} aria-label={`${entry.role}: ${entry.count}`} />
                      <span className="text-[0.68rem] capitalize text-[#53615d]">{entry.role}</span>
                    </div>
                  ))
                )}
              </div>
              <div className="mt-5">
                <div className="mb-2 flex items-center justify-between text-xs text-[#53615d]"><span>Active accounts</span><span>{adminStats.active_users ?? 0} of {adminStats.total_users ?? 0}</span></div>
                <div className="h-2 overflow-hidden rounded-full bg-[#e5ebe8]"><div className="h-full rounded-full bg-[#1b9a62]" style={{ width: `${activeRate}%` }} /></div>
              </div>
            </div>

            <div className="rounded-[20px] border border-[#e7dcc6] bg-white p-4">
              <h3 className="text-base font-bold text-[#151515]">Recent users</h3>
              <div className="mt-4 space-y-3">
                {(summary?.recent_users || []).length === 0 ? (
                  <div className="text-sm text-[#5a554f]">No recent users found.</div>
                ) : (
                  summary.recent_users.map((entry) => (
                    <div key={entry.id} className="flex items-center justify-between rounded-xl border border-[#f0e7d1] bg-[#fffdf8] p-3">
                      <div>
                        <div className="text-sm font-semibold text-[#1b1b1b]">{entry.full_name || entry.username}</div>
                        <div className="text-[0.72rem] text-[#5a554f]">{entry.email}</div>
                      </div>
                      <div className="text-right text-[0.72rem] text-[#5a554f]">
                        <div className="capitalize">{entry.role}</div>
                        <div>{entry.is_active ? 'Active' : 'Inactive'}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-3">
            <div className="min-h-[270px] rounded-[20px] border border-[#e7dcc6] bg-white p-4">
              <h3 className="text-base font-bold text-[#151515]">AI Questions Over Time</h3>
              <p className="mt-1 text-xs text-[#71807b]">Total questions asked by users.</p>
              <div className="mt-4"><AdminQuestionChart data={summary?.questions_over_time || []} onSelect={setSelectedInsight} /></div>
            </div>
            <div className="min-h-[270px] rounded-[20px] border border-[#e7dcc6] bg-white p-4">
              <h3 className="text-base font-bold text-[#151515]">Activities Done Per Day</h3>
              <p className="mt-1 text-xs text-[#71807b]">All persisted user and system actions.</p>
              <div className="mt-4"><AdminActivityChart data={summary?.activity_per_day || []} onSelect={setSelectedInsight} /></div>
            </div>
            <div className="min-h-[270px] rounded-[20px] border border-[#e7dcc6] bg-white p-4">
              <h3 className="text-base font-bold text-[#151515]">Documents by Department</h3>
              <p className="mt-1 text-xs text-[#71807b]">Distribution by department or category.</p>
              <div className="mt-5"><AdminTypeChart data={summary?.categories || []} onSelect={setSelectedInsight} /></div>
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="min-h-[240px] rounded-[20px] border border-[#e7dcc6] bg-white p-4">
              <h3 className="text-base font-bold text-[#151515]">Top Research Topics</h3>
              <p className="mt-1 text-xs text-[#71807b]">Based on active document count.</p>
              <div className="mt-5"><AdminTopicChart data={summary?.documents_by_topic || []} onSelect={setSelectedInsight} /></div>
            </div>
            <div className="min-h-[240px] rounded-[20px] border border-[#e7dcc6] bg-white p-4">
              <h3 className="text-base font-bold text-[#151515]">Document Processing Status</h3>
              <p className="mt-1 text-xs text-[#71807b]">Real-time processing overview.</p>
              <div className="mt-5"><AdminDonutChart data={summary?.processing_status || []} title="Document processing status" onSelect={setSelectedInsight} /></div>
            </div>
          </div>

          <div className="hidden grid gap-3 xl:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-[20px] border border-[#e7dcc6] bg-white p-4">
              <h3 className="text-base font-bold text-[#151515]">Document Processing Status</h3>
              <p className="mt-1 text-xs text-[#71807b]">Real-time processing overview from active documents.</p>
              <div className="mt-5"><AdminDonutChart data={summary?.processing_status || []} title="Document processing status" onSelect={setSelectedInsight} /></div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6">
            <div className="overflow-hidden rounded-[20px] border border-[#e7dcc6] bg-white">
              <div className="border-b border-[#e8ecea] px-4 py-4"><h3 className="text-base font-bold text-[#151515]">Recent Documents</h3><p className="mt-1 text-xs text-[#71807b]">Latest uploaded or processed documents.</p></div>
              {(summary?.recent_documents || []).length === 0 ? <div className="p-4 text-sm text-[#71807b]">No documents available.</div> : <div className="overflow-x-auto"><table className="min-w-[1150px] w-full text-left text-xs"><thead className="bg-[#eef1ef] text-[#56605e]"><tr>{['Document Title', 'Author', 'Type', 'Category', 'Year', 'Status', 'Uploaded By', 'Date Uploaded', 'Actions'].map((heading) => <th key={heading} className="px-4 py-3 font-semibold">{heading}</th>)}</tr></thead><tbody>{summary.recent_documents.map((document, index) => <tr key={document.id} className={index % 2 ? 'bg-[#fbfcfb]' : 'bg-white'}><td className="max-w-[240px] truncate border-t border-[#e8ecea] px-4 py-3 font-semibold text-[#1b1b1b]">{document.title || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{document.author || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{document.document_type || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{document.category || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{document.publication_year || '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3"><span className={`rounded-full px-2 py-1 font-medium ${document.processing_status === 'failed' ? 'bg-[#fff0ec] text-[#a24735]' : document.processing_status === 'completed' ? 'bg-[#ebfaf0] text-[#158b4d]' : 'bg-[#fff8e5] text-[#8e650f]'}`}>{document.processing_status || '—'}</span></td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">—</td><td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{document.created_at ? new Date(document.created_at).toLocaleDateString() : '—'}</td><td className="border-t border-[#e8ecea] px-4 py-3"><div className="flex items-center gap-1"><button type="button" onClick={() => onViewDocument(document.id)} title="View details" aria-label={`View ${document.title}`} className="rounded-md p-1.5 text-[#53615d] hover:bg-[#f3e7c7]"><Eye size={14} /></button><button type="button" onClick={() => onViewFile(document.id)} title="Open document" aria-label={`Open ${document.title}`} className="rounded-md p-1.5 text-[#53615d] hover:bg-[#f3e7c7]"><FileText size={14} /></button><button type="button" onClick={() => onDownload(document.id)} title="Download" aria-label={`Download ${document.title}`} className="rounded-md p-1.5 text-[#53615d] hover:bg-[#f3e7c7]"><Download size={14} /></button><button type="button" onClick={() => onDeleteDocument(document.id)} title="Delete" aria-label={`Delete ${document.title}`} className="rounded-md p-1.5 text-[#a24735] hover:bg-[#fff0ec]"><Trash2 size={14} /></button></div></td></tr>)}</tbody></table></div>}
            </div>
          </div>

          <div className="hidden overflow-hidden rounded-[20px] border border-[#e7dcc6] bg-white">
            <div className="overflow-x-auto">
              <table className="min-w-[1100px] w-full text-left text-xs">
                <thead className="bg-[#eef1ef] text-[#56605e]">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Name</th>
                    <th className="px-4 py-3 font-semibold">Email</th>
                    <th className="px-4 py-3 font-semibold">Role</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                    <th className="px-4 py-3 font-semibold">Joined</th>
                    <th className="px-4 py-3 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-5 text-sm text-[#5a554f]">No users available.</td>
                    </tr>
                  ) : (
                    users.map((entry, index) => (
                      <tr key={entry.id} className={index % 2 === 0 ? 'bg-[#fffdfa]' : 'bg-[#f8f4ed]'}>
                        <td className="border-t border-[#e8ecea] px-4 py-3 text-[#1b1b1b] font-semibold">{entry.full_name || entry.username}</td>
                        <td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">{entry.email}</td>
                        <td className="border-t border-[#e8ecea] px-4 py-3">
                          <select
                            value={entry.role}
                            onChange={(event) => handleRoleChange(entry.id, event.target.value)}
                            className="rounded-lg border border-[#d9ddda] bg-white px-2 py-1.5 text-xs font-medium capitalize text-[#1b1b1b] outline-none focus:border-[#c99a2e]"
                          >
                            <option value="admin">Admin</option>
                            <option value="researcher">Researcher</option>
                            <option value="viewer">Viewer</option>
                          </select>
                        </td>
                        <td className="border-t border-[#e8ecea] px-4 py-3">
                          <label className="inline-flex items-center gap-2 text-[#4f5957]">
                            <input
                              type="checkbox"
                              checked={Boolean(entry.is_active)}
                              onChange={(event) => handleStatusChange(entry.id, event.target.checked)}
                              className="h-4 w-4 rounded border-[#d9ddda] text-[#111111] focus:ring-[#c99a2e]"
                            />
                            {entry.is_active ? 'Active' : 'Inactive'}
                          </label>
                        </td>
                        <td className="border-t border-[#e8ecea] px-4 py-3 text-[#4f5957]">
                          {entry.created_at ? new Date(entry.created_at).toLocaleDateString() : '—'}
                        </td>
                        <td className="border-t border-[#e8ecea] px-4 py-3">
                          <button
                            type="button"
                            onClick={() => handleDeleteUser(entry.id)}
                            className="rounded-lg border border-[#e7cfc6] bg-[#fff7f4] px-2 py-1.5 text-[0.68rem] font-semibold text-[#8c3f2d] hover:bg-[#fceae5]"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {selectedInsight && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label={`${selectedInsight.label} statistics`}>
          <div className="w-full max-w-lg rounded-2xl border border-[#d9ddda] bg-white p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-[#e8ecea] pb-4">
              <div>
                <p className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-[#997326]">Dashboard details</p>
                <h2 className="mt-1 text-xl font-bold text-[#151515]">{selectedInsight.label}</h2>
              </div>
              <button type="button" onClick={() => setSelectedInsight(null)} className="rounded-lg p-2 text-[#53615d] hover:bg-[#f1f3f2]" aria-label="Close statistic details"><X size={18} /></button>
            </div>
            <div className="mt-5 rounded-xl border border-[#e7dcc6] bg-[#fffaf2] p-4">
              <span className="text-xs text-[#71807b]">Current value</span>
              <strong className="mt-1 block text-3xl text-[#17201f]">{selectedInsight.count}</strong>
              <span className="mt-1 block text-xs text-[#5a554f]">Live value from the backend analytics query.</span>
            </div>
            <div className="mt-4 border-t border-[#e8ecea] pt-3 text-xs text-[#71807b]">Source: {selectedInsight.source}</div>
          </div>
        </div>
      )}
    </div>
  )
}

const Footer = () => (
  <footer className="bg-[#0d0d0d] px-6 py-4 text-[0.7rem] text-[#f4e9d1]/70">
    <div className="mx-auto flex max-w-[1440px] flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <span>© 2026 AI Research Knowledge Hub</span>
      <div className="flex flex-wrap items-center gap-4">
        <a href="#" className="transition-colors hover:text-[#f7f3ea]">Privacy Policy</a>
        <a href="#" className="transition-colors hover:text-[#f7f3ea]">Terms of Use</a>
        <a href="#" className="transition-colors hover:text-[#f7f3ea]">Support</a>
      </div>
    </div>
  </footer>
)

export default App