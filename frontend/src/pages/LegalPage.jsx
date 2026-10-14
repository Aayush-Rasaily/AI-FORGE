import { ArrowLeft, ArrowUpRight, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import FooterSuperchat from "../components/registry/footer-superchat";
import { useEffect } from "react";

const LEGAL_CONTENT = {
  privacy: {
    eyebrow: "Privacy policy",
    title: "Your evidence stays yours.",
    intro: "This policy explains what AI-FORGE collects, why we use it, and the choices available to you when you investigate with the platform.",
    sections: [
      ["Information we process", "AI-FORGE may process account details, investigation metadata, uploaded evidence, analysis results, and technical information such as browser type and service events. We only ask for information needed to provide, secure, and improve the service."],
      ["How we use information", "We use information to authenticate users, run forensic analysis, keep investigations available, prevent abuse, troubleshoot failures, and improve reliability. We do not sell personal information or use uploaded evidence for advertising."],
      ["Evidence and retention", "Evidence is retained only for as long as your workspace or an investigation requires it, subject to your organisation's settings and any applicable legal obligations. Remove files you no longer need from the product to begin deletion."],
      ["Your choices", "You may request access, correction, export, or deletion of personal information associated with your account. Contact support and include enough context for us to locate the relevant workspace."],
      ["Contact", "For privacy questions, contact support@ai-forge.local. This page is a clear product policy template and should be reviewed with your organisation's legal adviser before production launch."],
    ],
  },
  terms: {
    eyebrow: "Terms and conditions",
    title: "A clear contract for careful work.",
    intro: "These terms set the ground rules for using AI-FORGE to organise evidence, run analysis, and collaborate on investigations.",
    sections: [
      ["Using the service", "You may use AI-FORGE only for lawful investigations and with the authority to process the evidence you upload. Keep your sign-in details secure and make sure people using your workspace have the permissions they need."],
      ["Analysis is decision support", "AI-FORGE produces signals, comparisons, and explanations to support human review. Results are not legal advice, a final finding, or a substitute for professional judgment. Verify important conclusions against the original evidence."],
      ["Your content", "You retain responsibility for the evidence and information you provide. You grant AI-FORGE the limited permission needed to host, transform, analyse, and display that content to deliver the service."],
      ["Acceptable use", "Do not use the service to infringe rights, upload malicious code, evade security controls, or investigate people without a lawful basis. We may restrict access when necessary to protect users or the service."],
      ["Availability and changes", "We work to keep AI-FORGE dependable, but maintenance, outages, and changes can happen. We may update these terms as the service evolves and will provide notice where the change materially affects your use."],
    ],
  },
  cookies: {
    eyebrow: "Cookie policy",
    title: "Small files, clearly explained.",
    intro: "AI-FORGE uses a minimal set of browser storage technologies to keep the product secure, remember your preferences, and understand whether the service is working reliably.",
    sections: [
      ["Essential storage", "Authentication and security tokens are required to sign in and keep protected pages protected. The application may also store interface preferences such as a collapsed sidebar setting."],
      ["Service measurement", "If enabled in your deployment, technical events may be used in aggregate to understand performance, errors, and feature use. These signals are used to improve the product, not to follow you across unrelated websites."],
      ["Managing cookies", "You can clear site data through your browser settings. Clearing essential storage will sign you out and may reset local preferences. Blocking all storage can prevent protected areas of the application from working."],
      ["Third-party services", "Your deployment may connect AI-FORGE to infrastructure or identity providers selected by your organisation. Those providers may set their own cookies under their own policies."],
      ["Questions", "For questions about cookies in your deployment, contact support@ai-forge.local and include the environment or workspace you are using."],
    ],
  },
};

export default function LegalPage({ type }) {
  const content = LEGAL_CONTENT[type] || LEGAL_CONTENT.privacy;

  useEffect(() => {
    document.title = `${content.eyebrow} | AI-FORGE`;
    return () => { document.title = "AI-FORGE"; };
  }, [content.eyebrow]);

  return (
    <div className="forge-legal-page">
      <header className="forge-legal-header">
        <Link className="forge-legal-brand" to="/dashboard" aria-label="Back to AI-FORGE dashboard">
          <span className="forge-brand-mark"><ShieldCheck size={18} /></span>
          <span><strong>AI-FORGE</strong><small>Forensic Intelligence</small></span>
        </Link>
        <Link className="forge-legal-back" to="/dashboard"><ArrowLeft size={15} /> Back to dashboard</Link>
      </header>

      <main className="forge-legal-main">
        <div className="forge-legal-intro">
          <p className="forge-legal-eyebrow">{content.eyebrow}</p>
          <h1>{content.title}</h1>
          <p className="forge-legal-lede">{content.intro}</p>
          <p className="forge-legal-updated">Last updated 14 October 2026 <ArrowUpRight size={14} aria-hidden="true" /></p>
        </div>
        <div className="forge-legal-content">
          {content.sections.map(([heading, body], index) => (
            <section key={heading} className="forge-legal-section">
              <span className="forge-legal-index">{String(index + 1).padStart(2, "0")}</span>
              <div><h2>{heading}</h2><p>{body}</p></div>
            </section>
          ))}
        </div>
      </main>
      <FooterSuperchat />
    </div>
  );
}
