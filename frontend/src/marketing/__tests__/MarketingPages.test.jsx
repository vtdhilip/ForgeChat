import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, act, renderHook } from '@testing-library/react';
import { useHashRoute } from '../../hooks/useHashRoute.js';
import MarketingLayout from '../MarketingLayout.jsx';
import MarketingHeader from '../MarketingHeader.jsx';
import MarketingFooter from '../MarketingFooter.jsx';
import LandingPage from '../pages/LandingPage.jsx';
import FeaturesPage from '../pages/FeaturesPage.jsx';
import SolutionsPage from '../pages/SolutionsPage.jsx';
import PricingPage from '../pages/PricingPage.jsx';
import AboutContactPage from '../pages/AboutContactPage.jsx';
import WhatsAppSimulator from '../components/WhatsAppSimulator.jsx';
import PricingCalculator from '../components/PricingCalculator.jsx';
import DemoBookingModal from '../components/DemoBookingModal.jsx';

describe('Synaptic Chat Marketing Pages Suite', () => {
  it('renders LandingPage with headline, simulator, and CTAs', () => {
    const onNavigate = vi.fn();
    const onOpenDemo = vi.fn();
    render(<LandingPage onNavigate={onNavigate} onOpenDemo={onOpenDemo} />);

    expect(screen.getAllByText(/Autonomous AI/i)[0]).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Start Free Trial/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Book Live Demo/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Start Free Trial/i }));
    expect(onNavigate).toHaveBeenCalledWith('login');

    fireEvent.click(screen.getByRole('button', { name: /Book Live Demo/i }));
    expect(onOpenDemo).toHaveBeenCalled();
  });

  it('renders FeaturesPage and toggles between capability tabs', () => {
    const onNavigate = vi.fn();
    render(<FeaturesPage onNavigate={onNavigate} onOpenDemo={vi.fn()} />);

    expect(screen.getByText(/Shared Team Inbox/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Multi-Tenant Security/i })).not.toBeInTheDocument();
    const aiAgentsTab = screen.getByRole('button', { name: /AI Agents \(BYOK\)/i });
    fireEvent.click(aiAgentsTab);
    expect(screen.getByText(/Autonomous AI Agents with Tool Calling/i)).toBeInTheDocument();
  });

  it('renders SolutionsPage with industry cards', () => {
    render(<SolutionsPage onNavigate={vi.fn()} onOpenDemo={vi.fn()} />);

    expect(screen.getByText(/E-Commerce & D2C Brands/i)).toBeInTheDocument();
    expect(screen.getByText(/Healthcare, Dental & Clinics/i)).toBeInTheDocument();
    expect(screen.getByText(/Real Estate & Property Developers/i)).toBeInTheDocument();
  });

  it('renders PricingPage with monthly/annual toggle and FAQ accordion', () => {
    const onNavigate = vi.fn();
    const onOpenDemo = vi.fn();
    render(<PricingPage onNavigate={onNavigate} onOpenDemo={onOpenDemo} />);

    expect(screen.getByText(/Starter Community/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Professional Growth/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/Enterprise Scale/i)[0]).toBeInTheDocument();

    // Toggle to Annual billing
    const annualBtn = screen.getByRole('button', { name: /Annual Billing/i });
    fireEvent.click(annualBtn);
    expect(screen.getByText('₹1,999')).toBeInTheDocument(); // 20% discount on ₹2,499
    expect(screen.getByText('₹5,199')).toBeInTheDocument();
    expect(screen.getByText('₹13,599')).toBeInTheDocument();

    // Expand FAQ
    const faqQuestion = screen.getByText(/Do I need an official WhatsApp Business API account/i);
    fireEvent.click(faqQuestion);
    expect(screen.getByText(/integrates directly with Meta’s official WhatsApp Cloud API/i)).toBeInTheDocument();
  });

  it('calculates ROI and recommended plan in PricingCalculator', () => {
    const onSelectPlan = vi.fn();
    render(<PricingCalculator onSelectPlan={onSelectPlan} />);

    expect(screen.getByText(/Interactive ROI & Volume Calculator/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Professional Growth/i)[0]).toBeInTheDocument(); // default 10,000 chats
    expect(screen.getByText(/₹6,499 \/ month/i)).toBeInTheDocument();

    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '40000' } });
    expect(screen.getAllByText(/Enterprise Scale/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/₹16,999 \/ month/i)).toBeInTheDocument();

    const selectBtn = screen.getByRole('button', { name: /Select Enterprise Scale/i });
    fireEvent.click(selectBtn);
    expect(onSelectPlan).toHaveBeenCalledWith('enterprise');
  });

  it('validates and submits DemoBookingModal', () => {
    const onClose = vi.fn();
    const { rerender } = render(<DemoBookingModal isOpen={false} onClose={onClose} />);
    expect(screen.queryByText(/Schedule a 1-on-1 Product Demo/i)).not.toBeInTheDocument();

    rerender(<DemoBookingModal isOpen={true} onClose={onClose} />);
    expect(screen.getByText(/Schedule a 1-on-1 Product Demo/i)).toBeInTheDocument();

    // Trigger validation error by clearing or clicking submit with empty values
    const submitBtn = screen.getByRole('button', { name: /Request Personalized Demo/i });
    fireEvent.click(submitBtn);

    // Fill valid inputs
    fireEvent.change(screen.getByPlaceholderText(/e\.g\. Alex Johnson/i), { target: { value: 'Jane Doe' } });
    fireEvent.change(screen.getByPlaceholderText(/alex@company\.com/i), { target: { value: 'jane@enterprise.com' } });
    fireEvent.change(screen.getByPlaceholderText(/\+1 \(555\) 000-0000/i), { target: { value: '+19876543210' } });

    fireEvent.click(submitBtn);
    expect(screen.getByText(/Demo Request Received!/i)).toBeInTheDocument();
  });

  it('renders MarketingHeader and triggers navigation and demo modal', () => {
    const onNavigate = vi.fn();
    const onOpenDemo = vi.fn();
    render(<MarketingHeader activeRoute="features" onNavigate={onNavigate} onOpenDemo={onOpenDemo} user={null} />);

    expect(screen.getByText('Synaptic Chat')).toBeInTheDocument();
    const pricingBtn = screen.getByRole('button', { name: 'Pricing' });
    fireEvent.click(pricingBtn);
    expect(onNavigate).toHaveBeenCalledWith('pricing');

    const signInBtn = screen.getByRole('button', { name: 'Sign In' });
    fireEvent.click(signInBtn);
    expect(onNavigate).toHaveBeenCalledWith('login');
  });

  it('plays through full WhatsAppSimulator scenarios without crashing', () => {
    vi.useFakeTimers();
    render(<WhatsAppSimulator />);

    // Step through all AI scenario messages (5 messages * 900ms + extra ticks)
    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(screen.getByText(/Does it support automated order tracking and CRM sync/i)).toBeInTheDocument();

    // Switch to Team Coexistence scenario and play through
    fireEvent.click(screen.getByRole('button', { name: /Team Coexistence/i }));
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(screen.getByText(/That was super fast, thank you!/i)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('renders MarketingLayout across all public routes cleanly', () => {
    const onNavigate = vi.fn();
    const { rerender } = render(
      <MarketingLayout activeRoute="landing" onNavigate={onNavigate} user={null} />,
    );
    expect(screen.getAllByText(/Autonomous AI/i)[0]).toBeInTheDocument();

    for (const route of ['features', 'solutions', 'pricing', 'about', 'contact']) {
      rerender(<MarketingLayout activeRoute={route} onNavigate={onNavigate} user={null} />);
    }
    expect(screen.getAllByText(/Meta Cloud API/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/Synaptic Info/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/End-to-End Encrypted Sessions/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Meta WhatsApp Business Compliant/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Self-hosted & Enterprise Cloud/i)).not.toBeInTheDocument();
  });

  it('uses clean path URLs without # for marketing pages and keeps # for SaaS app routes', () => {
    window.history.replaceState(null, '', '/');
    const { result } = renderHook(() => useHashRoute());

    act(() => {
      result.current[1]('features');
    });
    expect(window.location.pathname).toBe('/features');
    expect(window.location.hash).toBe('');
    expect(result.current[0]).toEqual(['features']);

    act(() => {
      result.current[1]('landing');
    });
    expect(window.location.pathname).toBe('/');
    expect(window.location.hash).toBe('');

    act(() => {
      result.current[1]('home');
    });
    expect(window.location.pathname).toBe('/');
    expect(window.location.hash).toBe('#/home');
    expect(result.current[0]).toEqual(['home']);
  });
});
