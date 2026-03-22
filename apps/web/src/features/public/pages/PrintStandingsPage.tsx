import { useParams } from "react-router-dom";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";

export function PrintStandingsPage() {
  const { slug } = useParams();
  const detail = useApiResource(() => api.getPublicTournament(slug ?? ""), [slug]);
  const standings = useApiResource(() => api.getPublicStandings(slug ?? ""), [slug]);

  if (detail.loading || standings.loading) {
    return <div className="print-page"><p>Loading standings...</p></div>;
  }

  if (detail.error || standings.error || !detail.data || !standings.data) {
    return <div className="print-page"><p>{detail.error ?? standings.error ?? "Standings unavailable"}</p></div>;
  }

  return (
    <div className="print-page">
      <button type="button" className="print-button" onClick={() => window.print()}>
        Print standings
      </button>
      <header className="print-header">
        <h1>{detail.data.name}</h1>
        <p>{detail.data.description || "Tournament standings"}</p>
      </header>
      <table className="print-table">
        <thead>
          <tr>
            <th>Place</th>
            <th>Name</th>
            <th>Points</th>
            <th>Matches</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {standings.data.map((entry, index) => (
            <tr key={entry.participant_id}>
              <td>#{entry.final_placement ?? index + 1}</td>
              <td>{entry.display_name}</td>
              <td>{entry.total_points}</td>
              <td>{entry.matches_played}</td>
              <td>{entry.current_status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <footer className="print-footer">Generated {new Date().toLocaleString()}</footer>
    </div>
  );
}
