import React, { useState } from 'react';
import {
  FileText,
  Search,
  Filter,
  Upload,
  Download,
  Trash2,
  FileCheck,
  Eye,
  Plus,
  Calendar,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { GlassCard } from '../components/GlassCard';

interface DocItem {
  id: string;
  title: string;
  category: 'Environmental Impact' | 'Municipal Directives' | 'Sensor Calibration' | 'Water Conservation';
  format: 'PDF' | 'CSV' | 'GEOJSON';
  size: string;
  date: string;
  author: string;
  verified: boolean;
}

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocItem[]>([
    {
      id: 'doc-1',
      title: 'Delhi NCR Winter Particulate Action Framework (GRAP-IV)',
      category: 'Municipal Directives',
      format: 'PDF',
      size: '2.4 MB',
      date: 'Oct 04, 2026',
      author: 'CAQM Secretariat',
      verified: true,
    },
    {
      id: 'doc-2',
      title: 'Dwarka Sector 21 Micro-Meteorology & Silt Resuspension Baseline',
      category: 'Environmental Impact',
      format: 'PDF',
      size: '4.8 MB',
      date: 'Sep 28, 2026',
      author: 'ClearSky Analytics Team',
      verified: true,
    },
    {
      id: 'doc-3',
      title: 'CAAQMS Multi-Station Sensor Cross-Calibration Logs',
      category: 'Sensor Calibration',
      format: 'CSV',
      size: '850 KB',
      date: 'Oct 01, 2026',
      author: 'CPCB Technical Division',
      verified: true,
    },
    {
      id: 'doc-4',
      title: 'Anti-Smog Gun Pumping Energy & Water Efficiency Audit',
      category: 'Water Conservation',
      format: 'PDF',
      size: '1.9 MB',
      date: 'Oct 08, 2026',
      author: 'Municipal Water Board',
      verified: true,
    },
    {
      id: 'doc-5',
      title: 'High-Resolution Delhi Road Segment Boundary GIS Layers',
      category: 'Environmental Impact',
      format: 'GEOJSON',
      size: '12.1 MB',
      date: 'Sep 15, 2026',
      author: 'Urban Spatial Lab',
      verified: false,
    },
  ]);

  const [activeCategory, setActiveCategory] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<DocItem | null>(null);

  // New doc form
  const [newTitle, setNewTitle] = useState('');
  const [newCategory, setNewCategory] = useState<DocItem['category']>('Environmental Impact');
  const [newFormat, setNewFormat] = useState<DocItem['format']>('PDF');

  const categories = [
    'All',
    'Environmental Impact',
    'Municipal Directives',
    'Sensor Calibration',
    'Water Conservation',
  ];

  const filteredDocs = documents.filter((doc) => {
    const matchesCat = activeCategory === 'All' || doc.category === activeCategory;
    const matchesSearch =
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.author.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const handleUpload = () => {
    if (!newTitle.trim()) return;
    const newDoc: DocItem = {
      id: `doc-${Date.now()}`,
      title: newTitle,
      category: newCategory,
      format: newFormat,
      size: '1.2 MB',
      date: new Date().toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }),
      author: 'ClearSky Operator',
      verified: true,
    };
    setDocuments([newDoc, ...documents]);
    setNewTitle('');
    setIsUploadModalOpen(false);
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this document from the operational record?')) {
      setDocuments(documents.filter((d) => d.id !== id));
    }
  };

  const handleDownload = (doc: DocItem) => {
    const blob = new Blob([`Document Content for: ${doc.title}\nCategory: ${doc.category}\nDate: ${doc.date}`], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${doc.title.replace(/[^a-zA-Z0-9]/g, '_')}.${doc.format.toLowerCase()}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 animate-fade-up max-w-[1780px] mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Documents &amp; Compliance Vault
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl">
            Central repository for environmental impact filings, official municipal guidelines, sensor calibration data, and water audits.
          </p>
        </div>

        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-md transition-all self-start sm:self-auto"
        >
          <Upload className="w-4 h-4" />
          <span>Upload Document</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <GlassCard className="p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Category Pills */}
        <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                activeCategory === cat
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-white/80 text-slate-600 hover:bg-white border border-slate-200/80'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search Field */}
        <div className="relative w-full md:w-64">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-slate-200 bg-white/90 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>
      </GlassCard>

      {/* Document Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDocs.map((doc) => (
          <GlassCard key={doc.id} className="p-5 flex flex-col justify-between group hover:shadow-lg">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200/60">
                  {doc.format} • {doc.size}
                </span>
                <span className="text-[11px] text-slate-400 font-medium">
                  {doc.date}
                </span>
              </div>

              <h3 className="font-bold text-sm text-slate-900 group-hover:text-emerald-700 transition-colors leading-snug">
                {doc.title}
              </h3>

              <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-2">
                <span>Category:</span>
                <span className="font-medium text-slate-700">{doc.category}</span>
              </div>

              <div className="text-[11px] text-slate-400 mt-1">
                Issued by {doc.author}
              </div>
            </div>

            {/* Actions Bar */}
            <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between">
              <button
                onClick={() => setPreviewDoc(doc)}
                className="flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
              >
                <Eye className="w-3.5 h-3.5" /> Preview
              </button>

              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleDownload(doc)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
                  title="Download File"
                >
                  <Download className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                  title="Delete Document"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>

      {filteredDocs.length === 0 && (
        <div className="p-12 text-center text-slate-400 glass-panel">
          <FileText className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm font-semibold">No documents found matching your filter.</p>
        </div>
      )}

      {/* Upload Document Modal */}
      {isUploadModalOpen && (
        <div
          className="fixed inset-0 z-[1200] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-up"
          onClick={() => setIsUploadModalOpen(false)}
        >
          <div
            className="glass-panel max-w-md w-full p-6 bg-white/95 text-slate-800 shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-slate-900 mb-1">
              Upload New Document
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Add regulatory records, audit PDFs, or geospatial data packages.
            </p>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Document Title</label>
                <input
                  type="text"
                  placeholder="e.g., Q4 Water Conservation Compliance Audit"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Category</label>
                  <select
                    value={newCategory}
                    onChange={(e: any) => setNewCategory(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  >
                    <option value="Environmental Impact">Environmental Impact</option>
                    <option value="Municipal Directives">Municipal Directives</option>
                    <option value="Sensor Calibration">Sensor Calibration</option>
                    <option value="Water Conservation">Water Conservation</option>
                  </select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Format</label>
                  <select
                    value={newFormat}
                    onChange={(e: any) => setNewFormat(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  >
                    <option value="PDF">PDF Report</option>
                    <option value="CSV">CSV Dataset</option>
                    <option value="GEOJSON">GeoJSON Spatial</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 mt-6 pt-3 border-t border-slate-100">
              <button
                onClick={() => setIsUploadModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-md transition-all"
              >
                Upload File
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewDoc && (
        <div
          className="fixed inset-0 z-[1200] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-up"
          onClick={() => setPreviewDoc(null)}
        >
          <div
            className="glass-panel max-w-lg w-full p-6 bg-white/95 text-slate-800 shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="font-bold text-sm text-slate-900 truncate pr-2">
                {previewDoc.title}
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="w-6 h-6 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <div className="my-5 p-6 rounded-2xl bg-slate-50 border border-slate-100 text-center space-y-2">
              <FileText className="w-10 h-10 text-emerald-600 mx-auto" />
              <div className="font-bold text-sm text-slate-800">{previewDoc.title}</div>
              <div className="text-xs text-slate-500">{previewDoc.category} • {previewDoc.size}</div>
              <div className="inline-block px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-semibold mt-2">
                Verified Signed Document
              </div>
            </div>

            <button
              onClick={() => {
                handleDownload(previewDoc);
                setPreviewDoc(null);
              }}
              className="w-full py-2.5 rounded-xl bg-slate-900 text-white font-semibold text-xs shadow-md"
            >
              Download Full Document ({previewDoc.size})
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentsPage;
