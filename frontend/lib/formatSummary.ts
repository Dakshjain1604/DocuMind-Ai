/**
 * Normalises the model's summary markdown before rendering.
 *
 * Extracted from the Dashboard so it can be exercised without a browser —
 * the emoji strip here previously wrote \u1F600-style escapes, which JS
 * parses as \u1F60 followed by a literal "0", turning the character class
 * into a range from "0" upward that deleted nearly all ASCII text.
 */
export function formatSummaryMarkdown(raw: string): string {
  if (!raw) return "";
  let text = raw;

  // Strip decorative emoji the model sometimes prefixes headings with.
  // NB: this must use \p{...} with the u flag. The previous form wrote
  // \u1F600 etc., which JS parses as \u1F60 followed by a literal '0', making
  // the character class a range from '0' upward — it deleted nearly all ASCII.
  text = text.replace(/\p{Extended_Pictographic}\uFE0F?/gu, "");

  text = text.replace(/^#*\s*(Executive Summary.*)$/gmi, "# $1");
  text = text.replace(/^#*\s*(Key Takeaways.*)$/gmi, "\n---\n\n## $1");
  text = text.replace(/^#*\s*(Section & Structural Breakdown.*)$/gmi, "\n---\n\n## $1");
  text = text.replace(/^#*\s*(Practical Impact.*)$/gmi, "\n---\n\n## $1");
  text = text.replace(/^>?\s*(Executive Abstract:\s*)(.*)$/gm, "> **Executive Abstract**: $2");

  return text;
}
