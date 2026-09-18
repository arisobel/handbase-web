import type { ReactNode } from "react";

/**
 * Wraps text that is always read left-to-right — an email address, a UUID, a
 * field key — so it stays legible inside a Hebrew sentence.
 *
 * `<bdi>` isolates the run from the surrounding paragraph, which stops a
 * trailing dot or parenthesis from jumping to the wrong side; `dir="ltr"` fixes
 * the direction inside it.
 */
export default function Technical({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <bdi dir="ltr" className={className ? `technical ${className}` : "technical"}>
      {children}
    </bdi>
  );
}
