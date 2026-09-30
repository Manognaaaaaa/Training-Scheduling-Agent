interface Props {
  title: string
  description: string
}

/** Temporary page body used until each feature is built. */
export default function PlaceholderPage({ title, description }: Props) {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
      <p className="mt-2 text-base text-slate-600">{description}</p>
    </div>
  )
}
