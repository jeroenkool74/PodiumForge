import { schemePlaybook } from "../features/tournaments/schemePlaybook";

export function TournamentSchemeLibrary({
  title = "Scheme library",
  subtitle = "Current support plus the most likely future formats, with the next engine investments called out clearly.",
}: {
  title?: string;
  subtitle?: string;
}) {
  return (
    <section className="card content-stack">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Format map</span>
          <h2>{title}</h2>
          <p className="muted-text">{subtitle}</p>
        </div>
      </div>

      <div className="card-grid">
        {schemePlaybook.map((scheme) => (
          <article key={scheme.id} className="scheme-library-card">
            <div className="card-header-row">
              <div>
                <span className="eyebrow">Format idea</span>
                <h3>{scheme.name}</h3>
              </div>
              <span className="scheme-fit-chip">{scheme.fit}</span>
            </div>
            <p>{scheme.tagline}</p>
            <p className="muted-text">{scheme.description}</p>
            <div className="scheme-library-note">
              <strong>Best for</strong>
              <p>{scheme.bestFor}</p>
            </div>
            <div className="scheme-library-note soft-note">
              <strong>Implementation note</strong>
              <p>{scheme.nextStep}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
