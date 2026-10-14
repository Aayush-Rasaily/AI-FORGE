import { motion } from "framer-motion";
import {
  ChevronDown,
  Globe,
  Mail,
  Shield,
} from "lucide-react";
import { Link } from "react-router-dom";

const COLORS = {
  background: "#020210",
  accent: "#3CC2F3",
  textPrimary: "#FFFFFF",
  textSecondary: "#9090A0",
  textMuted: "#6B6B7B",
  border: "#1A1A2E",
};

const PRODUCT_LINKS = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Cases", href: "/cases" },
  { label: "Investigations", href: "/investigation" },
  { label: "Reports", href: "/reports" },
];

const COMPANY_LINKS = [
  { label: "Help center", href: "/help" },
  { label: "Settings", href: "/settings" },
  { label: "Sign in", href: "/login" },
];

const RESOURCES_LINKS = [
  { label: "History", href: "/history" },
  { label: "Signature analysis", href: "/signature-analysis" },
  { label: "Contact support", href: "mailto:support@ai-forge.local", external: true },
];

const LEGAL_LINKS = [
  { label: "Privacy policy", href: "/privacy" },
  { label: "Terms and conditions", href: "/terms" },
  { label: "Cookies", href: "/cookies" },
];

function ForgeLogo() {
  return (
    <div className="forge-footer-logo" aria-hidden="true">
      <Shield size={22} strokeWidth={1.8} />
    </div>
  );
}

function FooterLink({ href, label, external }) {
  const className = "forge-footer-link";
  if (external) {
    return <a className={className} href={href}>{label}</a>;
  }
  return <Link className={className} to={href}>{label}</Link>;
}

function FooterColumn({ title, links, delay }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.25 }}
      transition={{ duration: 0.45, delay }}
    >
      <h2 className="forge-footer-heading">{title}</h2>
      <ul className="forge-footer-links">
        {links.map((link) => (
          <li key={link.label}>
            <FooterLink {...link} />
          </li>
        ))}
      </ul>
    </motion.div>
  );
}

export default function FooterSuperchat({
  companyName = "AI-FORGE",
  tagline = "Evidence, examined\nwith precision.",
  email = "support@ai-forge.local",
  copyright = "2026 AI-FORGE",
  location = "Forensic Intelligence",
}) {
  return (
    <footer className="forge-footer" style={{ backgroundColor: COLORS.background }}>
      <div className="forge-footer-main">
        <motion.div
          className="forge-footer-brand"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.45 }}
        >
          <ForgeLogo />
          <p className="forge-footer-brand-name">{companyName}</p>
          <p className="forge-footer-tagline">{tagline}</p>
          <a className="forge-footer-contact" href={`mailto:${email}`}>
            <Mail size={15} aria-hidden="true" />
            <span>{email}</span>
          </a>
        </motion.div>

        <div className="forge-footer-nav">
          <FooterColumn title="Product" links={PRODUCT_LINKS} delay={0.06} />
          <FooterColumn title="Company" links={COMPANY_LINKS} delay={0.12} />
          <FooterColumn title="Resources" links={RESOURCES_LINKS} delay={0.18} />
        </div>
      </div>

      <div className="forge-footer-bottom">
        <div className="forge-footer-bottom-inner">
          <div className="forge-footer-meta">
            <button className="forge-footer-language" type="button" aria-label="Language: English">
              <Globe size={14} aria-hidden="true" />
              <span>English</span>
              <ChevronDown size={13} aria-hidden="true" />
            </button>
            <span>© {copyright}</span>
            <span className="forge-footer-location">{location}</span>
            <nav className="forge-footer-legal" aria-label="Legal">
              {LEGAL_LINKS.map((link) => <FooterLink key={link.label} {...link} />)}
            </nav>
          </div>
          <span className="forge-footer-signoff">Built for careful decisions <span aria-hidden="true">♥</span></span>
        </div>
      </div>
    </footer>
  );
}
