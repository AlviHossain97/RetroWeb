/** Sanitize and format text to look like natural chat, replacing citations with chips. */
export function RenderCleanMessage({ content, isUser }: { content: string; isUser: boolean }) {
  if (!content) return null;

  if (isUser) {
    return <span>{content}</span>;
  }

  let text = content.replace(/Based on the provided (data|sources|evidence)[^,.]*[,:]?\s*/gi, "");
  text = text.replace(/According to the (data|sources|evidence)[^,.]*[,:]?\s*/gi, "");
  text = text.replace(/\n{3,}/g, "\n\n").trim();
  text = text.replace(/\*\*([^*]+)\*\*/g, "$1");
  text = text.replace(/(?<!\w)\*([^*]+)\*(?!\w)/g, "$1");

  const paragraphs = text.split("\n\n");

  return (
    <div className="flex flex-col gap-2">
      {paragraphs.map((p, i) => {
        const segments = p.split(/(\[\d+(?:,\s*\d+)*\])/g);
        return (
          <p key={i} className="leading-relaxed">
            {segments.map((seg, j) => {
              const match = seg.match(/^\[(.*)\]$/);
              if (match) {
                const nums = match[1].split(",").map((n) => n.trim());
                return (
                  <span key={j} className="inline-flex gap-0.5 ml-1 mr-0.5 align-text-top mt-0.5">
                    {nums.map((num, k) => (
                      <span
                        key={k}
                        className="inline-flex items-center justify-center w-4 h-4 text-[9px] font-bold rounded-full cursor-help transition-colors"
                        style={{ background: "var(--surface-3)", color: "var(--accent-cyan)" }}
                        title={`Source ${num}`}
                      >
                        {num}
                      </span>
                    ))}
                  </span>
                );
              }
              return (
                <span key={j}>
                  {seg.split("\n").map((line, k, arr) => (
                    <span key={k}>
                      {line}
                      {k < arr.length - 1 && <br />}
                    </span>
                  ))}
                </span>
              );
            })}
          </p>
        );
      })}
    </div>
  );
}
