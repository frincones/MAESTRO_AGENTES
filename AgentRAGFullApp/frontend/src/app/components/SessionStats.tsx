interface SessionStatsProps {
  caseState: Record<string, unknown> | null;
}

export default function SessionStats({ caseState }: SessionStatsProps) {
  if (!caseState || !caseState.turn_count) return null;

  const turns = (caseState.turn_count as number) || 0;
  const norms = ((caseState.norms_cited as string[]) || []).length;
  const juris = ((caseState.jurisprudence_cited as string[]) || []).length;
  const areas = ((caseState.areas_involved as string[]) || []).join(', ');

  return (
    <div className="flex items-center gap-2 text-[10px] text-muted-foreground/70 px-1">
      <span>Turno {turns}</span>
      {norms > 0 && <><span className="opacity-30">|</span><span>{norms} normas</span></>}
      {juris > 0 && <><span className="opacity-30">|</span><span>{juris} sentencias</span></>}
      {areas && <><span className="opacity-30">|</span><span className="truncate max-w-[150px]">{areas}</span></>}
    </div>
  );
}
