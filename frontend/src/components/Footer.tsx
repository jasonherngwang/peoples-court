"use client";

export function Footer() {
  return (
    <footer className="container-narrow py-12 border-t border-border">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="body-small text-center md:text-left">
          Adjudication powered by historical precedent analysis
        </p>
        <p className="body-small opacity-60">
          The People's Court © {new Date().getFullYear()}
        </p>
      </div>
    </footer>
  );
}
