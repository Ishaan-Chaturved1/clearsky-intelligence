import React from 'react';
import { Users, Server, ShieldAlert, Cpu, HeartHandshake, Layers, Code2 } from 'lucide-react';

export const AboutPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto space-y-10 animate-fade-up">
      
      {/* Hero Section */}
      <div className="bg-white rounded-3xl p-8 sm:p-10 border border-warm-200 shadow-warm-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 w-72 h-72 bg-accent-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex items-center gap-2 mb-3">
          <span className="font-sans font-bold text-xs uppercase tracking-wider text-accent-600 px-2.5 py-0.5 rounded-full bg-accent-500/10 border border-accent-500/20">
            Quantified Minds
          </span>
          <span className="text-xs font-clarendon text-earth-500">Environmental Intelligence Platform</span>
        </div>

        <h1 className="font-sentinel font-bold text-3xl sm:text-4xl text-earth-900 tracking-tight">
          ClearSky Intelligence
        </h1>
        <p className="font-sentinel italic text-lg text-accent-600 mt-1">
          Smart Urban Air Intelligence
        </p>

        <p className="font-clarendon text-base text-earth-800 leading-relaxed mt-5 max-w-2xl font-medium">
          “Smarter environmental decisions. Cleaner, more sustainable cities.”
        </p>

        <p className="font-clarendon text-sm text-earth-600 leading-relaxed mt-2 max-w-3xl">
          ClearSky Intelligence analyzes air-quality measurements, micrometeorology, thermal fire anomalies, and proximate construction land use to help municipal authorities make evidence-based, water-efficient decisions for urban particulate mitigation.
        </p>
      </div>

      {/* Engineering Team */}
      <div className="bg-white rounded-3xl p-8 border border-warm-200 shadow-warm-sm">
        <div className="flex items-center gap-2 mb-6">
          <Users className="w-5 h-5 text-accent-500" />
          <h2 className="font-sentinel font-bold text-xl text-earth-900">
            Quantified Minds Engineering Team
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div className="bg-warm-100/60 p-6 rounded-2xl border border-warm-200 hover:border-warm-300 transition-all">
            <span className="font-sentinel font-bold text-lg text-earth-900 block">
              Ishaan Chaturvedi
            </span>
            <span className="text-xs font-mono text-accent-600 font-semibold block mt-0.5">
              Full-Stack &amp; AI Systems Engineer
            </span>
            <p className="font-clarendon text-xs text-earth-600 mt-3 leading-relaxed">
              Architect of the deterministic environmental decision engine, FastAPI gateway, and warm editorial command center interface.
            </p>
          </div>

          <div className="bg-warm-100/60 p-6 rounded-2xl border border-warm-200 hover:border-warm-300 transition-all">
            <span className="font-sentinel font-bold text-lg text-earth-900 block">
              Ankit Kumar Tiwari
            </span>
            <span className="text-xs font-mono text-accent-600 font-semibold block mt-0.5">
              Environmental Data Scientist &amp; Cloud Architect
            </span>
            <p className="font-clarendon text-xs text-earth-600 mt-3 leading-relaxed">
              Design of inverse-distance weighting (IDW) geospatial interpolation models, water conservation calculations, and AWS cloud deployment.
            </p>
          </div>
        </div>
      </div>

      {/* Architecture & Tech Stack */}
      <div className="bg-white rounded-3xl p-8 border border-warm-200 shadow-warm-sm space-y-5">
        <div className="flex items-center gap-2">
          <Code2 className="w-5 h-5 text-sage-600" />
          <h2 className="font-sentinel font-bold text-xl text-earth-900">
            Technology Architecture
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="bg-warm-50 p-5 rounded-2xl border border-warm-200">
            <strong className="text-earth-900 block font-sentinel text-sm mb-1.5">Frontend</strong>
            <p className="text-earth-600 leading-relaxed font-clarendon text-xs">
              React 18, Vite, TypeScript, Tailwind CSS, Leaflet GIS, Recharts, Lucide React, Sentinel &amp; Clarendon typography.
            </p>
          </div>

          <div className="bg-warm-50 p-5 rounded-2xl border border-warm-200">
            <strong className="text-earth-900 block font-sentinel text-sm mb-1.5">Backend &amp; Engine</strong>
            <p className="text-earth-600 leading-relaxed font-clarendon text-xs">
              Python 3.13, FastAPI, Uvicorn, Pydantic V2, HTTPX, NumPy, Pandas, Pytest test suite.
            </p>
          </div>

          <div className="bg-warm-50 p-5 rounded-2xl border border-warm-200">
            <strong className="text-earth-900 block font-sentinel text-sm mb-1.5">Data &amp; Cloud</strong>
            <p className="text-earth-600 leading-relaxed font-clarendon text-xs">
              SQLite local dev, Amazon DynamoDB, AWS Lambda, EventBridge, CloudFront, S3.
            </p>
          </div>
        </div>
      </div>

      {/* Ethical AI & Operational Restraint */}
      <div className="bg-warm-100/70 rounded-3xl p-8 border border-warm-300/80 text-xs text-earth-700 space-y-4">
        <div className="flex items-center gap-2 text-earth-900 font-sentinel font-bold text-lg">
          <ShieldAlert className="w-5 h-5 text-accent-500" />
          <span>Ethical Environmental Computing Principles</span>
        </div>

        <p className="font-clarendon text-earth-600 leading-relaxed text-xs">
          Smart city deployments must remain scientifically responsible:
        </p>

        <ul className="space-y-2.5 pl-4 list-disc font-clarendon text-earth-600 text-xs">
          <li>
            <strong className="text-earth-800">No fabricated readings:</strong> When station measurements are missing, the system records explicit absence and falls back to labeled models or demo scenarios.
          </li>
          <li>
            <strong className="text-earth-800">No false claims:</strong> ClearSky Intelligence makes no claim that anti-smog mist guns eliminate fine PM2.5 or substitute for systemic emission abatement.
          </li>
          <li>
            <strong className="text-earth-800">Transparent water savings:</strong> All conservation metrics explicitly document their baseline comparative assumptions.
          </li>
        </ul>
      </div>

    </div>
  );
};
