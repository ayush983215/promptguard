export function PageHeader({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="max-w-2xl">
        <h1 className="text-2xl font-semibold tracking-tight text-balance md:text-3xl">{title}</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground md:text-base">{description}</p>
      </div>
      {action}
    </div>
  );
}
