export const OfficialImages = ({
  endpoint = "https://api.zode.dev/v1/official-images",
  readme = "https://github.com/zodeops/runner-images#readme",
}) => {
  const [state, setState] = useState({ status: "loading", images: [] });

  useEffect(() => {
    let cancelled = false;
    fetch(endpoint, { headers: { Accept: "application/json" } })
      .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then((body) => {
        if (cancelled) return;
        const images = Array.isArray(body && body.images) ? body.images : [];
        setState({ status: "ready", images });
      })
      .catch((err) => {
        if (cancelled) return;
        setState({ status: "error", images: [], message: String(err && err.message ? err.message : err) });
      });
    return () => {
      cancelled = true;
    };
  }, [endpoint]);

  const fallback = (
    <a href={readme}>software list in the runner-images README</a>
  );

  if (state.status === "loading") {
    return (
      <p>
        Loading the current list from <code>GET /v1/official-images</code>. The same list is in the {fallback}.
      </p>
    );
  }

  if (state.status === "error") {
    return (
      <p>
        The current list could not be loaded ({state.message}). Read the {fallback} instead. It is regenerated on every release.
      </p>
    );
  }

  if (state.images.length === 0) {
    return (
      <p>
        No official image is published yet. The planned contents are in the {fallback}.
      </p>
    );
  }

  const formatDate = (iso) => {
    if (!iso) return "not published";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toISOString().slice(0, 16).replace("T", " ") + " UTC";
  };

  return (
    <div>
      {state.images.map((image) => {
        const manifest = image.manifest || {};
        const groups = Array.isArray(manifest.groups) ? manifest.groups : [];
        const env = manifest.env && typeof manifest.env === "object" ? Object.entries(manifest.env) : [];
        const sizes = Array.isArray(image.sizes) ? image.sizes : [];
        return (
          <div key={image.line} className="mt-8">
            <h3 id={"line-" + image.line}>
              <code>{image.ref || "zode/" + image.line}</code>
            </h3>
            <ul>
              <li>
                Version <code>{image.version}</code>
                {image.commit ? (
                  <span>
                    {" "}from commit{" "}
                    {image.source_url ? (
                      <a href={image.source_url}>
                        <code>{String(image.commit).slice(0, 7)}</code>
                      </a>
                    ) : (
                      <code>{String(image.commit).slice(0, 7)}</code>
                    )}
                  </span>
                ) : null}
              </li>
              <li>Published {formatDate(image.published_at)}</li>
              {manifest.os ? <li>OS: {manifest.os}</li> : null}
              {sizes.length > 0 ? (
                <li>
                  Sizes:{" "}
                  {sizes.map((s, i) => (
                    <span key={s}>
                      {i > 0 ? ", " : ""}
                      <code>{s}</code>
                    </span>
                  ))}
                </li>
              ) : null}
              {image.building && image.building.version ? (
                <li>
                  Version <code>{image.building.version}</code> is building. It replaces this one when every build is ready.
                </li>
              ) : null}
            </ul>
            {groups.map((group) => (
              <div key={group.name}>
                <h4>{group.name}</h4>
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Version</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(Array.isArray(group.items) ? group.items : []).map((item, i) => (
                      <tr key={item.name + "-" + i}>
                        <td>{item.name}</td>
                        <td>
                          <code>{item.version}</code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
            {env.length > 0 ? (
              <div>
                <h4>Environment</h4>
                <table>
                  <thead>
                    <tr>
                      <th>Variable</th>
                      <th>Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {env.map(([k, v]) => (
                      <tr key={k}>
                        <td>
                          <code>{k}</code>
                        </td>
                        <td>
                          <code>{String(v)}</code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
};
