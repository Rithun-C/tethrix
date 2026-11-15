interface PlaceholderPageProps {
  title: string;
  bolt: string;
}

/** Stands in for a screen that a later bolt builds. */
export function PlaceholderPage({ title, bolt }: PlaceholderPageProps) {
  return (
    <>
      <h1>{title}</h1>
      <p>Nothing here yet. This screen is built in bolt {bolt}.</p>
    </>
  );
}
