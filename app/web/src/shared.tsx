import type { ReactNode } from 'react';

const MET = ['included', 'not excluded'];
const FAILED = ['excluded', 'not included'];

export function verdictKind(label: string) {
  if (MET.includes(label)) return 'met';
  if (FAILED.includes(label)) return 'failed';
  if (label === 'not enough information') return 'unknown';
  if (label === 'not applicable') return 'na';
  return 'invalid';
}

export function verdictText(label: string) {
  const text = label === '__invalid__' ? 'unverified output' : label;
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function Verdict({ label, className = '' }: { label: string; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span className={`dot dot-${verdictKind(label)}`} aria-hidden="true" />
      {verdictText(label)}
    </span>
  );
}

export function HomeButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className="btn !p-2.5" onClick={onClick} aria-label="Home" title="Home">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M3 11.5 12 4l9 7.5" />
        <path d="M5.5 9.8V20h13V9.8" />
        <path d="M10 20v-5.5h4V20" />
      </svg>
    </button>
  );
}

export function TopBar({ onHome, center, right }: { onHome: () => void; center?: ReactNode; right?: ReactNode }) {
  return (
    <header className="flex items-center justify-between gap-4 px-5 pt-5">
      <HomeButton onClick={onHome} />
      <p className="m-0 text-sm text-neutral-400 tabular-nums">{center}</p>
      <div className="flex min-w-11 justify-end">{right}</div>
    </header>
  );
}

export function Notice({ message }: { message: string }) {
  return (
    <div className="card px-5 py-4 text-center text-neutral-100" role="alert">
      {message}
    </div>
  );
}

export function ConfirmDialog({ title, message, confirm, onConfirm, onCancel }: { title: string; message: string; confirm: string; onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/70 px-4" role="dialog" aria-modal="true" aria-label={title}>
      <div className="card max-w-sm bg-black p-6 text-center">
        <h2 className="m-0 text-xl font-medium">{title}</h2>
        <p className="m-0 mt-2 text-neutral-300">{message}</p>
        <div className="mt-5 flex justify-center gap-3">
          <button type="button" className="btn" onClick={onCancel} autoFocus>
            Stay
          </button>
          <button type="button" className="btn btn-primary" onClick={onConfirm}>
            {confirm}
          </button>
        </div>
      </div>
    </div>
  );
}

export function StepFooter({ onBack, nextLabel, onNext, nextDisabled }: { onBack?: () => void; nextLabel: string; onNext: () => void; nextDisabled?: boolean }) {
  return (
    <div className="mt-2 flex items-center justify-between">
      {onBack ? (
        <button type="button" className="btn" onClick={onBack}>
          Back
        </button>
      ) : (
        <span />
      )}
      <button type="button" className="btn btn-primary" onClick={onNext} disabled={nextDisabled}>
        {nextLabel}
      </button>
    </div>
  );
}
