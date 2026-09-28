/** Displays a cover SVG string as an A4 sheet. The SVG is built by our own
 *  templates with every user string escaped (see lib/cover/text.ts#esc). */
export function CoverView({
  svg,
  watermark = false,
  className = "",
}: {
  svg: string;
  watermark?: boolean;
  className?: string;
}) {
  return (
    <div
      style={{ containerType: "inline-size" }}
      className={`relative aspect-[595/842] w-full overflow-hidden rounded-[4px] bg-paper shadow-[0_1px_2px_rgba(15,23,42,.06),0_12px_32px_-8px_rgba(15,23,42,.18)] ${className}`}
    >
      <div className="absolute inset-0 [&>svg]:h-full [&>svg]:w-full" dangerouslySetInnerHTML={{ __html: svg }} />
      {watermark && (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-[18%] overflow-hidden select-none">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="font-display text-[7cqw] font-extrabold tracking-widest whitespace-nowrap text-brand-700/[.13] -rotate-[35deg]"
            >
              APERÇU · PAGINYA
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
