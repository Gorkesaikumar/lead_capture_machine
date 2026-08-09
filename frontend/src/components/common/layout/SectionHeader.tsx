interface SectionHeaderProps {
  title: string;
  description?: string;
}

export function SectionHeader({ title, description }: SectionHeaderProps) {
  return (
    <div className="pb-4 mb-6 border-b border-gray-100">
      <h2 className="text-lg font-medium tracking-tight text-slate-900">{title}</h2>
      {description && <p className="text-sm text-slate-500 mt-1">{description}</p>}
    </div>
  );
}