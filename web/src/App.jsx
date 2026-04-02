import { useState } from 'react'
import './index.css'

const API = '/api'

function ScoreGauge({ score }) {
  const color = score >= 80 ? '#22c55e' : score >= 50 ? '#eab308' : '#ef4444'
  return (
    <div className="flex flex-col items-center py-6">
      <div className="text-6xl font-bold" style={{ color }}>{score}</div>
      <div className="text-sm text-gray-500 mt-1">Compliance Score</div>
    </div>
  )
}

function FindingCard({ finding }) {
  const colors = {
    error: { bg: 'bg-red-50', border: 'border-red-400', text: 'text-red-700', badge: 'bg-red-100 text-red-800' },
    warning: { bg: 'bg-amber-50', border: 'border-amber-400', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-800' },
    suggestion: { bg: 'bg-blue-50', border: 'border-blue-400', text: 'text-blue-700', badge: 'bg-blue-100 text-blue-800' },
  }
  const style = colors[finding.level] || colors.warning
  return (
    <div className={`${style.bg} border-l-4 ${style.border} p-3 my-2 rounded-r`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-xs font-semibold px-2 py-0.5 rounded ${style.badge}`}>
          {finding.level.toUpperCase()}
        </span>
        <span className="text-xs text-gray-500 font-mono">{finding.rule}</span>
        {finding.regulation && finding.regulation !== 'common' && (
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{finding.regulation}</span>
        )}
      </div>
      <p className={`text-sm ${style.text}`}>{finding.message}</p>
      {finding.citation && <p className="text-xs text-gray-400 mt-1">{finding.citation}</p>}
    </div>
  )
}

function SummaryCards({ summary }) {
  return (
    <div className="grid grid-cols-3 gap-4 my-4">
      <div className="bg-red-50 rounded-lg p-4 text-center">
        <div className="text-3xl font-bold text-red-600">{summary.errors}</div>
        <div className="text-xs text-gray-500 uppercase mt-1">Errors</div>
      </div>
      <div className="bg-amber-50 rounded-lg p-4 text-center">
        <div className="text-3xl font-bold text-amber-600">{summary.warnings}</div>
        <div className="text-xs text-gray-500 uppercase mt-1">Warnings</div>
      </div>
      <div className="bg-blue-50 rounded-lg p-4 text-center">
        <div className="text-3xl font-bold text-blue-600">{summary.suggestions}</div>
        <div className="text-xs text-gray-500 uppercase mt-1">Suggestions</div>
      </div>
    </div>
  )
}

function UploadArea({ onUpload, loading }) {
  const [dragOver, setDragOver] = useState(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) onUpload(file)
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) onUpload(file)
  }

  return (
    <div
      className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors
        ${dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => document.getElementById('file-input').click()}
    >
      <input id="file-input" type="file" className="hidden" accept=".pdf,.docx,.doc,.md,.txt,.html" onChange={handleFileSelect} />
      {loading ? (
        <div className="text-gray-500">
          <div className="animate-spin inline-block w-8 h-8 border-4 border-gray-300 border-t-blue-500 rounded-full mb-3"></div>
          <p>Analyzing document...</p>
        </div>
      ) : (
        <>
          <div className="text-4xl mb-3">📄</div>
          <p className="text-lg font-medium text-gray-700">Drop a compliance document here</p>
          <p className="text-sm text-gray-500 mt-1">PDF, Word, Markdown, HTML</p>
          <p className="text-xs text-gray-400 mt-3">or click to browse</p>
        </>
      )}
    </div>
  )
}

function RegulationFilter({ findings, activeFilter, onFilter }) {
  const regulations = [...new Set(findings.map(f => f.regulation))].sort()
  return (
    <div className="flex flex-wrap gap-2 my-4">
      <button
        className={`text-xs px-3 py-1 rounded-full border ${!activeFilter ? 'bg-gray-900 text-white border-gray-900' : 'border-gray-300 hover:bg-gray-50'}`}
        onClick={() => onFilter(null)}
      >
        All ({findings.length})
      </button>
      {regulations.map(reg => {
        const count = findings.filter(f => f.regulation === reg).length
        return (
          <button
            key={reg}
            className={`text-xs px-3 py-1 rounded-full border ${activeFilter === reg ? 'bg-gray-900 text-white border-gray-900' : 'border-gray-300 hover:bg-gray-50'}`}
            onClick={() => onFilter(reg)}
          >
            {reg} ({count})
          </button>
        )
      })}
    </div>
  )
}

function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [institution, setInstitution] = useState('')
  const [regulation, setRegulation] = useState('bsa-aml')
  const [regFilter, setRegFilter] = useState(null)
  const [fileName, setFileName] = useState('')

  const handleUpload = async (file) => {
    setLoading(true)
    setError(null)
    setFileName(file.name)

    const formData = new FormData()
    formData.append('file', file)

    const params = new URLSearchParams({
      regulation,
      institution_name: institution || 'Institution',
    })

    try {
      const resp = await fetch(`${API}/analyze?${params}`, {
        method: 'POST',
        body: formData,
      })
      if (!resp.ok) {
        const errData = await resp.json()
        throw new Error(errData.detail || 'Analysis failed')
      }
      const data = await resp.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadReport = async () => {
    if (!result) return
    // Re-upload for HTML report
    const input = document.getElementById('file-input')
    const file = input?.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)
    const params = new URLSearchParams({
      regulation,
      institution_name: institution || 'Institution',
    })

    const resp = await fetch(`${API}/analyze/report?${params}`, {
      method: 'POST',
      body: formData,
    })
    const html = await resp.text()
    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${fileName.replace(/\.[^/.]+$/, '')}_gap_report.html`
    a.click()
    URL.revokeObjectURL(url)
  }

  const filteredFindings = result?.findings?.filter(f => !regFilter || f.regulation === regFilter) || []

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">FinCompliance</h1>
            <p className="text-xs text-gray-500">Financial compliance documentation linter</p>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="bg-green-100 text-green-800 px-2 py-1 rounded">49 rules</span>
            <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">9 regulations</span>
            <a href="https://github.com/BipinRimal314/comply" target="_blank" rel="noopener" className="hover:text-gray-900">GitHub</a>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {!result ? (
          <>
            {/* Config */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Institution Name</label>
                <input
                  type="text"
                  value={institution}
                  onChange={(e) => setInstitution(e.target.value)}
                  placeholder="Your Credit Union"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Primary Regulation</label>
                <select
                  value={regulation}
                  onChange={(e) => setRegulation(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                >
                  <option value="bsa-aml">BSA/AML</option>
                  <option value="sox">SOX</option>
                  <option value="pci-dss">PCI-DSS</option>
                  <option value="glba">GLBA</option>
                  <option value="udaap">UDAAP</option>
                  <option value="reg-e">Regulation E</option>
                  <option value="reg-cc">Regulation CC</option>
                  <option value="reg-dd">Regulation DD</option>
                  <option value="all">All Regulations</option>
                </select>
              </div>
            </div>

            {/* Upload */}
            <UploadArea onUpload={handleUpload} loading={loading} />

            {error && (
              <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
                {error}
              </div>
            )}

            {/* Features */}
            <div className="grid grid-cols-3 gap-6 mt-12">
              <div className="text-center p-6">
                <div className="text-3xl mb-2">🔍</div>
                <h3 className="font-medium text-gray-900">49 Deterministic Rules</h3>
                <p className="text-sm text-gray-500 mt-1">No AI hallucinations. Every finding cites a specific regulation.</p>
              </div>
              <div className="text-center p-6">
                <div className="text-3xl mb-2">📋</div>
                <h3 className="font-medium text-gray-900">9 Regulations</h3>
                <p className="text-sm text-gray-500 mt-1">BSA/AML, SOX, PCI-DSS, GLBA, UDAAP, Reg E/CC/DD, NCUA</p>
              </div>
              <div className="text-center p-6">
                <div className="text-3xl mb-2">📄</div>
                <h3 className="font-medium text-gray-900">PDF, Word, Markdown</h3>
                <p className="text-sm text-gray-500 mt-1">Upload any document format. Get results in seconds.</p>
              </div>
            </div>
          </>
        ) : (
          <>
            {/* Results */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-bold text-gray-900">Analysis: {fileName}</h2>
                <p className="text-sm text-gray-500">{institution || 'Institution'} | {regulation.toUpperCase()}</p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleDownloadReport}
                  className="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-800 transition-colors"
                >
                  Download Gap Report
                </button>
                <button
                  onClick={() => { setResult(null); setFileName('') }}
                  className="border border-gray-300 px-4 py-2 rounded-lg text-sm hover:bg-gray-50 transition-colors"
                >
                  New Analysis
                </button>
              </div>
            </div>

            <ScoreGauge score={result.summary.score} />
            <SummaryCards summary={result.summary} />

            {/* Metadata check */}
            {result.metadata_check && (
              <div className="bg-white rounded-lg border border-gray-200 p-4 my-4">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Document Metadata</h3>
                <div className="flex flex-wrap gap-3">
                  {Object.entries(result.metadata_check).map(([field, present]) => (
                    <span key={field} className={`text-xs px-2 py-1 rounded ${present ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {present ? '✓' : '✗'} {field}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Findings */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 my-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">
                Findings ({result.summary.total_findings})
              </h3>
              <RegulationFilter findings={result.findings || []} activeFilter={regFilter} onFilter={setRegFilter} />
              <div className="max-h-[600px] overflow-y-auto">
                {filteredFindings.map((f, i) => <FindingCard key={i} finding={f} />)}
              </div>
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between text-xs text-gray-400">
          <span>FinCompliance v0.6.0 — 49 rules, 9 regulations, 0 hallucinations</span>
          <a href="https://pypi.org/project/fincompliance/" target="_blank" rel="noopener" className="hover:text-gray-600">pip install fincompliance</a>
        </div>
      </footer>
    </div>
  )
}

export default App
