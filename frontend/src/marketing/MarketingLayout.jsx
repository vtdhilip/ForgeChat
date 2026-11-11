import { useState } from 'react';
import MarketingHeader from './MarketingHeader.jsx';
import MarketingFooter from './MarketingFooter.jsx';
import LandingPage from './pages/LandingPage.jsx';
import FeaturesPage from './pages/FeaturesPage.jsx';
import SolutionsPage from './pages/SolutionsPage.jsx';
import PricingPage from './pages/PricingPage.jsx';
import AboutContactPage from './pages/AboutContactPage.jsx';
import LegalPage from './pages/LegalPage.jsx';
import DemoBookingModal from './components/DemoBookingModal.jsx';
import { C, FONT } from '../constants.js';

export default function MarketingLayout({ activeRoute, onNavigate, user }) {
  const [demoModalOpen, setDemoModalOpen] = useState(false);

  const renderContent = () => {
    switch (activeRoute) {
      case 'features':
        return <FeaturesPage onNavigate={onNavigate} onOpenDemo={() => setDemoModalOpen(true)} />;
      case 'solutions':
        return <SolutionsPage onNavigate={onNavigate} onOpenDemo={() => setDemoModalOpen(true)} />;
      case 'pricing':
        return <PricingPage onNavigate={onNavigate} onOpenDemo={() => setDemoModalOpen(true)} />;
      case 'about':
      case 'contact':
        return <AboutContactPage onNavigate={onNavigate} onOpenDemo={() => setDemoModalOpen(true)} />;
      case 'privacy-policy':
      case 'terms':
      case 'data-deletion':
        return <LegalPage page={activeRoute} onNavigate={onNavigate} />;
      case 'landing':
      default:
        return <LandingPage onNavigate={onNavigate} onOpenDemo={() => setDemoModalOpen(true)} />;
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: '100vh',
        width: '100%',
        overflowY: 'auto',
        background: C.pageBg,
        fontFamily: FONT,
        position: 'relative',
      }}
    >
      <MarketingHeader
        activeRoute={activeRoute}
        onNavigate={onNavigate}
        onOpenDemo={() => setDemoModalOpen(true)}
        user={user}
      />

      <main style={{ flex: 1 }}>
        {renderContent()}
      </main>

      <MarketingFooter
        onNavigate={onNavigate}
        onOpenDemo={() => setDemoModalOpen(true)}
      />

      <DemoBookingModal
        isOpen={demoModalOpen}
        onClose={() => setDemoModalOpen(false)}
      />
    </div>
  );
}
