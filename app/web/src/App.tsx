import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type Status } from './api';
import { CriteriaStep, NoteStep, Running, SentenceStep, type Draft } from './Flow';
import Inspect from './Inspect';
import LandingOrb from './LandingOrb';
import { CriterionDetail, Results, type Screening } from './Results';
import { ConfirmDialog, Notice, TopBar } from './shared';

const EMPTY: Draft = { note: '', sentences: [], inclusion: '', exclusion: '', mode: 'cached' };
const STEP_LABELS: Record<string, string> = { note: 'Step 1 of 3', sentences: 'Step 2 of 3', criteria: 'Step 3 of 3' };
const readRoute = () => window.location.hash.replace(/^#\/?/, '');
const go = (route: string) => {
  window.location.hash = `/${route}`;
};
const replace = (route: string) => window.location.replace(`#/${route}`);
const splitLines = (text: string) => text.split('\n').map((line) => line.trim()).filter(Boolean);

export default function App() {
  const [route, setRoute] = useState(readRoute);
  const [status, setStatus] = useState<Status | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [jobId, setJobId] = useState('');
  const [screening, setScreening] = useState<Screening | null>(null);
  const [failure, setFailure] = useState('');
  const [confirmHome, setConfirmHome] = useState(false);
  const mainRef = useRef<HTMLElement>(null);

  const update = useCallback((patch: Partial<Draft>) => setDraft((current) => ({ ...current, ...patch })), []);

  useEffect(() => {
    const onChange = () => setRoute(readRoute());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  useEffect(() => {
    let active = true;
    let timer = 0;
    const poll = async () => {
      try {
        const next = await api.status();
        if (!active) return;
        setStatus(next);
        if (next.state === 'loading') timer = window.setTimeout(poll, 1500);
      } catch {
        if (active) timer = window.setTimeout(poll, 3000);
      }
    };
    poll();
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    mainRef.current?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [route]);

  // A refreshed or hand-typed address may point at a screen whose data no longer exists.
  const detailIndex = route.startsWith('detail/') ? Number(route.slice(7)) : -1;
  useEffect(() => {
    if (route === 'sentences' && !draft.sentences.length) replace('note');
    if (route === 'criteria' && !draft.sentences.length) replace('note');
    if (route === 'running' && !jobId) replace(draft.sentences.length ? 'criteria' : 'note');
    if ((route === 'results' || route.startsWith('detail/')) && !screening) replace('note');
    if (route.startsWith('detail/') && screening && !(Number.isInteger(detailIndex) && screening.results[detailIndex])) replace('results');
  }, [route, draft.sentences.length, jobId, screening, detailIndex]);

  const hasWork = Boolean(draft.note || draft.sentences.length || draft.inclusion || draft.exclusion || screening);

  function resetAndGoHome() {
    setDraft(EMPTY);
    setScreening(null);
    setJobId('');
    setFailure('');
    setConfirmHome(false);
    go('');
  }

  const requestHome = () => (hasWork ? setConfirmHome(true) : resetAndGoHome());

  async function startRun() {
    const { id } = await api.screen({
      sentences: draft.sentences,
      inclusion: splitLines(draft.inclusion),
      exclusion: splitLines(draft.exclusion),
      mode: draft.mode,
    });
    setFailure('');
    setJobId(id);
    go('running');
  }

  async function openReport(id: string) {
    try {
      const report = await api.report(id);
      setScreening({ overall: report.overall, results: report.results, reportId: report.id, sentences: report.patient_sentences.map((item) => item.text) });
      go('results');
    } catch (error) {
      setFailure((error as Error).message);
    }
  }

  const inspectButton = (
    <button type="button" className="btn" onClick={() => go('inspect')}>
      Inspect
    </button>
  );

  let body = null;
  if (route === 'note') body = <NoteStep draft={draft} update={update} onNext={() => go('sentences')} />;
  else if (route === 'sentences') body = <SentenceStep draft={draft} update={update} onBack={() => go('note')} onNext={() => go('criteria')} />;
  else if (route === 'criteria') body = <CriteriaStep draft={draft} update={update} status={status} onBack={() => go('sentences')} onRun={startRun} />;
  else if (route === 'running' && jobId)
    body = (
      <Running
        jobId={jobId}
        onDone={(job) => {
          setScreening({ overall: job.overall!, results: job.results, reportId: job.report_id!, sentences: draft.sentences });
          replace('results');
        }}
        onFailed={(message) => {
          setFailure(message);
          replace('failed');
        }}
        onCancelled={() => replace('criteria')}
      />
    );
  else if (route === 'failed')
    body = (
      <div className="flex max-w-md flex-col items-center gap-5">
        <Notice message={failure || 'The run failed. Try again.'} />
        <button type="button" className="btn" onClick={() => replace('criteria')}>
          Back to criteria
        </button>
      </div>
    );
  else if (route === 'results' && screening) body = <Results screening={screening} onOpen={(index) => go(`detail/${index}`)} onEdit={() => (draft.sentences.length ? go('criteria') : (update({ sentences: screening.sentences }), go('criteria')))} />;
  else if (route.startsWith('detail/') && screening?.results[detailIndex])
    body = <CriterionDetail screening={screening} index={detailIndex} onBack={() => go('results')} onMove={(index) => replace(`detail/${index}`)} />;

  const firstResult = screening?.results[0];

  return (
    <main ref={mainRef} tabIndex={-1} className="outline-none">
      {route === '' && (
        <div className="screen flex min-h-dvh flex-col items-center justify-center">
          <p className="display absolute top-7 left-8 m-0 text-xl font-medium tracking-wide">CRS</p>
          <LandingOrb />
          <button type="button" className="btn glass -mt-2" onClick={() => go('note')}>
            Get started
          </button>
        </div>
      )}
      {route === 'inspect' && (
        <div className="screen min-h-dvh">
          <TopBar onHome={requestHome} right={<button type="button" className="btn" onClick={() => window.history.back()}>Back</button>} />
          <Inspect
            status={status}
            sentences={draft.sentences.length ? draft.sentences : screening?.sentences ?? []}
            criterion={firstResult?.criterion ?? splitLines(draft.inclusion)[0] ?? ''}
            criterionType={firstResult?.criterion_type ?? 'inclusion'}
            onOpenReport={openReport}
          />
        </div>
      )}
      {route !== '' && route !== 'inspect' && (
        <div className="screen flex min-h-dvh flex-col">
          <TopBar onHome={requestHome} center={STEP_LABELS[route]} right={route !== 'running' ? inspectButton : undefined} />
          <div className={`flex flex-1 justify-center px-5 py-10 ${route === 'running' ? 'items-center' : 'items-start md:items-center'}`}>{body}</div>
        </div>
      )}
      {confirmHome && (
        <ConfirmDialog
          title="Go to the home screen?"
          message="This clears the note, criteria and results on screen. Saved reports stay in Inspect."
          confirm="Go home"
          onConfirm={resetAndGoHome}
          onCancel={() => setConfirmHome(false)}
        />
      )}
    </main>
  );
}
