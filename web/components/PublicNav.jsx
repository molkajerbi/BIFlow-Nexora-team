"use client";
import Link from "next/link";
import Icon from "./Icon";
import { Logo } from "./ui";

export default function PublicNav({ links = true }) {
  return (
    <header className="nav">
      <div className="nav-in">
        <Link href="/"><Logo /></Link>
        {links && (
          <nav className="nav-links">
            <a href="/#how">How it works</a>
            <a href="/#agents">The agents</a>
            <a href="/#guarantees">Guarantees</a>
          </nav>
        )}
        <div className="nav-cta">
          <Link className="btn sm" href="/signin"><Icon name="login" size={15} /> Sign in</Link>
          <Link className="btn sm primary" href="/signup"><Icon name="user-plus" size={15} /> Create account</Link>
        </div>
      </div>
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer className="footer">
      <div className="wrap">
        <span>BIFlow · Nexora team · ESPRIT</span>
        <span>Your data stays on this computer · Local AI (Ollama), no API key</span>
      </div>
    </footer>
  );
}
