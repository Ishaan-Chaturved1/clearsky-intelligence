import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Send,
  MessageCircle,
  Mail,
  Mic,
  Camera,
  Award,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Clock,
  MapPin,
  Flame,
  HardHat,
  Factory,
  Wind,
  Trash2,
  Gift,
  ExternalLink,
  ChevronRight,
  X,
  Volume2
} from 'lucide-react';
import { api } from '../services/api';
import { CitizenReport, RewardItem, CitizenWallet, ViolationCategory } from '../types';

export const CitizenWatchPage: React.FC = () => {
  const [reports, setReports] = useState<CitizenReport[]>([]);
  const [rewards, setRewards] = useState<RewardItem[]>([]);
  const [wallet, setWallet] = useState<CitizenWallet | null>(null);
  const [activeTab, setActiveTab] = useState<'FEED' | 'REWARDS'>('FEED');
  const [isSubmitOpen, setIsSubmitOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [redemptionSuccess, setRedemptionSuccess] = useState<any | null>(null);

  // Form State
  const [category, setCategory] = useState<ViolationCategory>('UNCOVERED_CONSTRUCTION');
  const [address, setAddress] = useState('');
  const [zoneId, setZoneId] = useState('DL-01');
  const [description, setDescription] = useState('');
  const [reporterName, setReporterName] = useState('Vikram Sharma');
  const [reporterContact, setReporterContact] = useState('+91 98112 43210');
  const [photoUrl, setPhotoUrl] = useState('https://images.unsplash.com/photo-1541888946425-d0fbb186156f?auto=format&fit=crop&w=600&q=80');
  const [hasVoiceNote, setHasVoiceNote] = useState(false);
  const [voiceNoteText, setVoiceNoteText] = useState('');

  const loadData = async () => {
    try {
      const [reps, rews, wal] = await Promise.all([
        api.getCitizenReports(30).catch(() => []),
        api.getRewardsCatalog().catch(() => []),
        api.getCitizenWallet(reporterContact).catch(() => null)
      ]);
      setReports(reps);
      setRewards(rews);
      if (wal) setWallet(wal);
    } catch (err) {
      console.error('Failed to load citizen watch data:', err);
    }
  };

  useEffect(() => {
    loadData();
  }, [reporterContact]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      const newReport = await api.submitCitizenReport({
        category,
        zone_id: zoneId,
        latitude: 28.647,
        longitude: 77.315,
        location_address: address || 'Anand Vihar Urban Corridor, Delhi',
        description,
        photo_url: photoUrl,
        has_voice_note: hasVoiceNote,
        voice_note_transcript: hasVoiceNote ? voiceNoteText || 'Voice Note: Dust plume observed blowing across road without mitigation.' : undefined,
        reporter_name: reporterName,
        reporter_contact: reporterContact,
        channel: 'WEB'
      });
      setReports([newReport, ...reports]);
      setIsSubmitOpen(false);
      setDescription('');
      setAddress('');
      setHasVoiceNote(false);
      await loadData();
    } catch (err) {
      console.error('Submit report failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSimulateVerify = async (reportId: string) => {
    try {
      const updated = await api.verifyCitizenReport(
        reportId,
        'VERIFIED_VIOLATION',
        100,
        'Verified by municipal inspection team. 100 ClearSky Points credited!'
      );
      setReports(reports.map((r) => (r.report_id === reportId ? updated : r)));
      await loadData();
    } catch (err) {
      console.error('Verify failed:', err);
    }
  };

  const handleRedeem = async (itemId: string) => {
    try {
      const result = await api.redeemRewardItem(reporterContact, itemId);
      setRedemptionSuccess(result);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Redemption failed. Check your points balance.');
    }
  };

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case 'UNCOVERED_CONSTRUCTION':
      case 'ILLEGAL_DEMOLITION':
        return <HardHat className="w-4 h-4 text-amber-600" />;
      case 'INDUSTRIAL_EMISSION':
        return <Factory className="w-4 h-4 text-accent-500" />;
      case 'OPEN_WASTE_BURNING':
        return <Flame className="w-4 h-4 text-accent-600" />;
      case 'UNPAVED_ROAD_DUST':
      default:
        return <Wind className="w-4 h-4 text-earth-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED_VIOLATION':
        return (
          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-sage-50 text-sage-700 border border-sage-200 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-sage-600" />
            <span>VERIFIED VIOLATION</span>
          </span>
        );
      case 'ACTION_DISPATCHED':
        return (
          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-accent-50 text-accent-700 border border-accent-200 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-accent-500" />
            <span>ACTION DISPATCHED</span>
          </span>
        );
      case 'RESOLVED':
        return (
          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-warm-100 text-earth-700 border border-warm-300">
            RESOLVED
          </span>
        );
      case 'PENDING_AUDIT':
      default:
        return (
          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1">
            <Clock className="w-3 h-3 text-amber-500" />
            <span>PENDING AUDIT</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 animate-fade-up">

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-warm-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="font-mono text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-accent-500/10 text-accent-600 border border-accent-500/20">
              Community Environmental Action
            </span>
            <span className="text-xs font-clarendon text-earth-500">Public Reporting Loop</span>
          </div>
          <h1 className="font-sentinel font-bold text-3xl sm:text-4xl text-earth-900 tracking-tight">
            Citizen Watch &amp; Eco-Points
          </h1>
          <p className="text-sm font-clarendon text-earth-600 mt-1 max-w-2xl leading-relaxed">
            Report unmitigated construction dust, industrial stack smoke, or illegal burning. Verified infractions earn ClearSky Points redeemable for HEPA filters, N95 masks, and clean air rewards.
          </p>
        </div>

        {/* User Points Card */}
        <div className="bg-white p-4 rounded-2xl border border-warm-200 shadow-warm-sm flex items-center gap-4 min-w-[240px]">
          <div className="w-12 h-12 rounded-xl bg-accent-500/10 border border-accent-500/20 flex items-center justify-center text-accent-500">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <div className="text-[10px] font-sans font-semibold uppercase tracking-wider text-earth-400">
              Your ClearSky Balance
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="font-sentinel font-bold text-2xl text-earth-900">
                {wallet?.total_points || 250}
              </span>
              <span className="text-xs font-sans font-semibold text-accent-600">Points</span>
            </div>
            <div className="text-[10px] font-clarendon text-earth-500">
              {wallet?.verified_reports_count || 2} verified reports
            </div>
          </div>
        </div>
      </div>

      {/* Multi-Channel Quick Dispatch Ribbon */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        
        {/* WhatsApp Channel */}
        <a
          href="https://wa.me/919811243210?text=ClearSky%20Report:%20[Attach%20Photo,%20GPS%20Location,%20Audio/Text]"
          target="_blank"
          rel="noopener noreferrer"
          className="bg-white hover:bg-warm-50 p-4 rounded-2xl border border-warm-200 shadow-warm-sm hover:shadow-warm transition-all flex items-center gap-3.5 group"
        >
          <div className="w-10 h-10 rounded-xl bg-sage-500/10 border border-sage-500/20 flex items-center justify-center text-sage-600 group-hover:scale-105 transition-transform">
            <MessageCircle className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-sentinel font-bold text-sm text-earth-900 group-hover:text-accent-600 transition-colors">
              WhatsApp Dispatch
            </div>
            <div className="text-[11px] font-clarendon text-earth-500 truncate">
              Send photo, GPS pin, &amp; voice note
            </div>
          </div>
          <ExternalLink className="w-3.5 h-3.5 text-earth-300 group-hover:text-accent-500" />
        </a>

        {/* Telegram Channel */}
        <a
          href="https://t.me/ClearSkyWatchBot"
          target="_blank"
          rel="noopener noreferrer"
          className="bg-white hover:bg-warm-50 p-4 rounded-2xl border border-warm-200 shadow-warm-sm hover:shadow-warm transition-all flex items-center gap-3.5 group"
        >
          <div className="w-10 h-10 rounded-xl bg-accent-500/10 border border-accent-500/20 flex items-center justify-center text-accent-500 group-hover:scale-105 transition-transform">
            <Send className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-sentinel font-bold text-sm text-earth-900 group-hover:text-accent-600 transition-colors">
              Telegram Bot
            </div>
            <div className="text-[11px] font-clarendon text-earth-500 truncate">
              Automated 24/7 incident logger
            </div>
          </div>
          <ExternalLink className="w-3.5 h-3.5 text-earth-300 group-hover:text-accent-500" />
        </a>

        {/* Web Submission Trigger */}
        <button
          onClick={() => setIsSubmitOpen(true)}
          className="bg-accent-500 hover:bg-accent-600 p-4 rounded-2xl text-white shadow-warm hover:shadow-warm-lg transition-all flex items-center gap-3.5 text-left group"
        >
          <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center text-white group-hover:scale-105 transition-transform">
            <Camera className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-sans font-bold text-sm">
              Submit Web Report
            </div>
            <div className="text-[11px] text-white/80 truncate">
              Attach image &amp; earn +100 Points
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-white/80 group-hover:translate-x-0.5 transition-transform" />
        </button>

      </div>

      {/* Tabs: Public Feed vs Eco-Rewards */}
      <div className="flex items-center justify-between border-b border-warm-200 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('FEED')}
            className={`px-4 py-2 rounded-xl font-sans text-xs font-semibold transition-all ${
              activeTab === 'FEED'
                ? 'bg-earth-900 text-warm-50 shadow-warm'
                : 'text-earth-600 hover:text-earth-900 hover:bg-warm-100'
            }`}
          >
            Public Incident Ledger ({reports.length})
          </button>
          <button
            onClick={() => setActiveTab('REWARDS')}
            className={`px-4 py-2 rounded-xl font-sans text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'REWARDS'
                ? 'bg-earth-900 text-warm-50 shadow-warm'
                : 'text-earth-600 hover:text-earth-900 hover:bg-warm-100'
            }`}
          >
            <Gift className="w-3.5 h-3.5 text-accent-400" />
            <span>Eco-Rewards Store ({rewards.length})</span>
          </button>
        </div>

        <button
          onClick={() => setIsSubmitOpen(true)}
          className="hidden sm:flex items-center gap-1.5 text-xs font-sans font-semibold text-accent-600 hover:text-accent-700 transition-colors"
        >
          <span>Report New Infraction</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* TAB 1: INCIDENT FEED */}
      {activeTab === 'FEED' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {reports.map((report) => (
              <div
                key={report.report_id}
                className="bg-white rounded-2xl p-5 border border-warm-200 shadow-warm-sm flex flex-col justify-between hover:shadow-warm transition-all"
              >
                <div>
                  {/* Top Bar */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <div className="p-2 rounded-xl bg-warm-100 border border-warm-200">
                        {getCategoryIcon(report.category)}
                      </div>
                      <div>
                        <div className="font-sentinel font-bold text-sm text-earth-900">
                          {report.category_label}
                        </div>
                        <div className="text-[11px] font-mono text-earth-400">
                          {report.report_id} • via {report.channel}
                        </div>
                      </div>
                    </div>

                    {getStatusBadge(report.status)}
                  </div>

                  {/* Photo & Description */}
                  <div className="flex flex-col sm:flex-row gap-4 my-3">
                    {report.photo_url && (
                      <div className="w-full sm:w-28 h-28 rounded-xl overflow-hidden bg-warm-100 border border-warm-200 flex-shrink-0">
                        <img
                          src={report.photo_url}
                          alt="Incident evidence"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    )}

                    <div className="flex-1">
                      <div className="flex items-center gap-1 text-[11px] font-clarendon text-earth-500 mb-1">
                        <MapPin className="w-3 h-3 text-accent-500 flex-shrink-0" />
                        <span className="font-medium text-earth-800">{report.zone_name || 'Delhi NCR'}</span> — {report.location_address}
                      </div>

                      <p className="font-clarendon text-xs text-earth-700 leading-relaxed line-clamp-3">
                        {report.description}
                      </p>

                      {report.has_voice_note && (
                        <div className="mt-2.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-warm-100 border border-warm-200 text-[11px] font-mono text-earth-600">
                          <Volume2 className="w-3.5 h-3.5 text-accent-500" />
                          <span>Voice memo attached</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Evidence Correlation */}
                  {report.evidence_correlation && (
                    <div className="p-3 rounded-xl bg-warm-50 border border-warm-200/80 text-[11px] font-clarendon text-earth-600 mb-3">
                      <strong className="text-earth-900 font-sans font-semibold block mb-0.5">Automated Sensor Correlation:</strong>
                      {report.evidence_correlation}
                    </div>
                  )}
                </div>

                {/* Footer Status & Verification Action */}
                <div className="pt-3 border-t border-warm-200 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-sans text-earth-400">Reporter: {report.reporter_name}</span>
                    {report.points_awarded > 0 && (
                      <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-accent-500/10 text-accent-600 border border-accent-500/20">
                        +{report.points_awarded} Points
                      </span>
                    )}
                  </div>

                  {/* Admin Simulation Button for Live Audit Demo */}
                  {report.status === 'PENDING_AUDIT' && (
                    <button
                      onClick={() => handleSimulateVerify(report.report_id)}
                      className="px-2.5 py-1 rounded-lg bg-sage-500/10 hover:bg-sage-500/20 text-sage-700 font-sans font-semibold text-[11px] border border-sage-500/30 transition-colors"
                      title="Simulate municipal audit verification"
                    >
                      Audit &amp; Credit 100 Pts
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: ECO-REWARDS MARKETPLACE */}
      {activeTab === 'REWARDS' && (
        <div className="space-y-6">
          <div className="bg-warm-100/70 p-6 rounded-2xl border border-warm-300/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h2 className="font-sentinel font-bold text-xl text-earth-900">
                ClearSky Eco-Rewards Store
              </h2>
              <p className="font-clarendon text-xs text-earth-600 mt-1 max-w-xl">
                Redeem your earned ClearSky Points for certified clean air equipment, particulate protective respirators, and green transit subsidies provided by Delhi clean air partners.
              </p>
            </div>
            <div className="text-right">
              <span className="text-[11px] font-sans text-earth-500 uppercase tracking-wider block">Available Balance</span>
              <span className="font-sentinel font-bold text-3xl text-accent-600">
                {wallet?.total_points || 250} Pts
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {rewards.map((item) => (
              <div
                key={item.item_id}
                className="bg-white rounded-2xl p-6 border border-warm-200 shadow-warm-sm flex flex-col justify-between hover:shadow-warm transition-all"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-warm-100 border border-warm-200 text-earth-600">
                      {item.category}
                    </span>
                    {item.badge_label && (
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-accent-500/10 text-accent-600 border border-accent-500/20">
                        {item.badge_label}
                      </span>
                    )}
                  </div>

                  <h3 className="font-sentinel font-bold text-lg text-earth-900 mb-2">
                    {item.title}
                  </h3>

                  <p className="font-clarendon text-xs text-earth-600 leading-relaxed mb-4">
                    {item.description}
                  </p>
                </div>

                <div className="pt-4 border-t border-warm-200 flex items-center justify-between">
                  <div>
                    <span className="font-sentinel font-bold text-xl text-earth-900">
                      {item.points_cost}
                    </span>
                    <span className="text-xs font-sans text-earth-500 ml-1">Pts</span>
                    <div className="text-[10px] font-clarendon text-earth-400">
                      Sponsored by {item.sponsor}
                    </div>
                  </div>

                  <button
                    onClick={() => handleRedeem(item.item_id)}
                    disabled={(wallet?.total_points || 250) < item.points_cost}
                    className="px-4 py-2 rounded-xl bg-accent-500 hover:bg-accent-600 disabled:bg-warm-200 text-white disabled:text-earth-400 font-sans font-semibold text-xs transition-all shadow-warm-sm"
                  >
                    {(wallet?.total_points || 250) < item.points_cost ? 'Need More Pts' : 'Redeem Now'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* REPORT SUBMISSION MODAL */}
      {isSubmitOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-earth-900/40 backdrop-blur-sm animate-fade-up">
          <div className="bg-white border border-warm-200 rounded-3xl max-w-lg w-full shadow-warm-xl p-6 sm:p-8 max-h-[90vh] overflow-y-auto">
            
            <div className="flex items-center justify-between pb-4 border-b border-warm-200">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-accent-500/10 border border-accent-500/20 flex items-center justify-center text-accent-500">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-sentinel font-bold text-lg text-earth-900">
                    Report Environmental Violation
                  </h3>
                  <p className="text-xs font-clarendon text-earth-500">Earn +100 ClearSky Points on verification</p>
                </div>
              </div>
              <button
                onClick={() => setIsSubmitOpen(false)}
                className="p-1.5 text-earth-400 hover:text-earth-700 rounded-xl hover:bg-warm-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 my-5 text-xs text-earth-700">
              
              {/* Category */}
              <div>
                <label className="font-sans font-semibold text-earth-800 block mb-1">
                  Violation Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as ViolationCategory)}
                  className="w-full p-2.5 rounded-xl bg-warm-50 border border-warm-300 font-sans focus:outline-none focus:border-accent-500"
                >
                  <option value="UNCOVERED_CONSTRUCTION">Uncovered Construction Debris &amp; Excavation</option>
                  <option value="ILLEGAL_DEMOLITION">Illegal Demolition Without Anti-Smog Gun</option>
                  <option value="INDUSTRIAL_EMISSION">Industrial Stack Black Smoke / Boilers</option>
                  <option value="OPEN_WASTE_BURNING">Open Waste or Biomass Burning</option>
                  <option value="UNPAVED_ROAD_DUST">Unpaved Road Resuspension Hazard</option>
                </select>
              </div>

              {/* Monitored Sector */}
              <div>
                <label className="font-sans font-semibold text-earth-800 block mb-1">
                  Nearest Delhi NCR Sector
                </label>
                <select
                  value={zoneId}
                  onChange={(e) => setZoneId(e.target.value)}
                  className="w-full p-2.5 rounded-xl bg-warm-50 border border-warm-300 font-sans focus:outline-none focus:border-accent-500"
                >
                  <option value="DL-01">DL-01 Anand Vihar Corridor</option>
                  <option value="DL-02">DL-02 RK Puram Sector</option>
                  <option value="DL-03">DL-03 Wazirpur Industrial Area</option>
                  <option value="DL-04">DL-04 Jahangirpuri Transport Area</option>
                  <option value="DL-05">DL-05 Rohini Sector 16</option>
                  <option value="DL-06">DL-06 Punjabi Bagh West</option>
                  <option value="DL-07">DL-07 Okhla Phase II</option>
                  <option value="DL-09">DL-09 Mundka Industrial Area</option>
                </select>
              </div>

              {/* Exact Address */}
              <div>
                <label className="font-sans font-semibold text-earth-800 block mb-1">
                  Street Landmark / GPS Address
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Flyover pillar construction site near Anand Vihar ISBT"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full p-2.5 rounded-xl bg-warm-50 border border-warm-300 font-clarendon focus:outline-none focus:border-accent-500"
                />
              </div>

              {/* Description */}
              <div>
                <label className="font-sans font-semibold text-earth-800 block mb-1">
                  Incident Description
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Describe the particulate plume, lack of water misting, odor, or construction equipment involved..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-2.5 rounded-xl bg-warm-50 border border-warm-300 font-clarendon focus:outline-none focus:border-accent-500"
                />
              </div>

              {/* Attachments: Photo + Voice Note */}
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="p-3 rounded-xl border border-warm-200 bg-warm-50 flex items-center gap-2">
                  <Camera className="w-4 h-4 text-accent-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <span className="font-sans font-semibold block text-[11px]">Photo Evidence</span>
                    <span className="text-[10px] text-earth-400">Attached (Geo-tagged)</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setHasVoiceNote(!hasVoiceNote);
                    if (!hasVoiceNote) setVoiceNoteText('Audio Note (20s): Extreme dust blowing across road from unmitigated demolition.');
                  }}
                  className={`p-3 rounded-xl border flex items-center gap-2 text-left transition-all ${
                    hasVoiceNote
                      ? 'border-accent-500 bg-accent-500/10 text-accent-700'
                      : 'border-warm-200 bg-warm-50 text-earth-600 hover:bg-warm-100'
                  }`}
                >
                  <Mic className="w-4 h-4 text-accent-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <span className="font-sans font-semibold block text-[11px]">
                      {hasVoiceNote ? 'Voice Note Added' : 'Add Voice Note'}
                    </span>
                    <span className="text-[10px] text-earth-400">
                      {hasVoiceNote ? '20s recorded' : 'Optional memo'}
                    </span>
                  </div>
                </button>
              </div>

              {/* Reporter Contact */}
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="font-sans font-semibold text-earth-800 block mb-1">
                    Your Name
                  </label>
                  <input
                    type="text"
                    required
                    value={reporterName}
                    onChange={(e) => setReporterName(e.target.value)}
                    className="w-full p-2.5 rounded-xl bg-warm-50 border border-warm-300 font-sans focus:outline-none focus:border-accent-500"
                  />
                </div>
                <div>
                  <label className="font-sans font-semibold text-earth-800 block mb-1">
                    Mobile / Contact
                  </label>
                  <input
                    type="text"
                    required
                    value={reporterContact}
                    onChange={(e) => setReporterContact(e.target.value)}
                    className="w-full p-2.5 rounded-xl bg-warm-50 border border-warm-300 font-sans focus:outline-none focus:border-accent-500"
                  />
                </div>
              </div>

              {/* Submit CTA */}
              <div className="pt-4 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsSubmitOpen(false)}
                  className="px-4 py-2.5 rounded-xl font-sans font-medium text-earth-600 hover:bg-warm-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-6 py-2.5 rounded-xl bg-accent-500 hover:bg-accent-600 disabled:opacity-50 text-white font-sans font-semibold shadow-warm transition-all"
                >
                  {isSubmitting ? 'Submitting...' : 'Dispatch Report (+100 Pts)'}
                </button>
              </div>

            </form>

          </div>
        </div>
      )}

      {/* REDEMPTION SUCCESS MODAL */}
      {redemptionSuccess && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-earth-900/40 backdrop-blur-sm animate-fade-up">
          <div className="bg-white border border-warm-200 rounded-3xl max-w-md w-full shadow-warm-xl p-8 text-center space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-sage-500/10 border border-sage-500/20 text-sage-600 mx-auto flex items-center justify-center">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <h3 className="font-sentinel font-bold text-2xl text-earth-900">
              Voucher Generated!
            </h3>

            <p className="font-clarendon text-xs text-earth-600">
              You redeemed <span className="font-bold text-earth-900">{redemptionSuccess.item_title}</span> for {redemptionSuccess.points_spent} ClearSky Points.
            </p>

            <div className="p-4 rounded-2xl bg-warm-100 border border-warm-300 font-mono text-base font-bold text-accent-600 tracking-wider">
              {redemptionSuccess.voucher_code}
            </div>

            <p className="text-[11px] font-clarendon text-earth-500">
              {redemptionSuccess.instructions}
            </p>

            <button
              onClick={() => setRedemptionSuccess(null)}
              className="w-full py-3 rounded-xl bg-earth-900 text-warm-50 font-sans font-semibold text-xs shadow-warm hover:bg-earth-800 transition-all"
            >
              Close &amp; View Balance ({redemptionSuccess.remaining_points} Pts)
            </button>
          </div>
        </div>
      )}

    </div>
  );
};
