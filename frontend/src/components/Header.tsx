"use client";

interface HeaderProps {
  showDescription?: boolean;
}

export function Header({ showDescription = true }: HeaderProps) {
  return (
    <header className="container-narrow py-16 md:py-24">
      <div className="text-center space-y-5">
        <p className="heading-2 mt-2 md:mt-8">Official Adjudication Portal</p>
        <h1 className="heading-display">
          The People's Court{" "}
          <span className="heading-display-accent">is in Session.</span>
        </h1>
        {showDescription && (
          <p className="body-regular font-medium max-w-lg mx-auto">
            <span className="font-semibold">Am I The Asshole?</span> Submit your
            grievance. A decade of{" "}
            <a
              href="https://www.reddit.com/r/AmItheAsshole/"
              target="_blank"
              rel="noopener noreferrer"
              className="link-inline"
            >
              case law
            </a>{" "}
            will be used to render a verdict.
          </p>
        )}
      </div>
    </header>
  );
}
