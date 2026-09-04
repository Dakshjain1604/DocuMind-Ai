import { describe, expect, it } from "vitest";
import { parseCitationSegments } from "./citations";

describe("parseCitationSegments", () => {
  it("returns a single text segment when there are no citations", () => {
    expect(parseCitationSegments("no citations here")).toEqual([
      { type: "text", value: "no citations here" },
    ]);
  });

  it("splits a single trailing citation marker", () => {
    const segs = parseCitationSegments("The answer is 42 [1]");
    expect(segs).toEqual([
      { type: "text", value: "The answer is 42 " },
      { type: "citation", ids: [1] },
      { type: "text", value: "" },
    ]);
  });

  it("parses a comma-grouped citation marker as multiple ids", () => {
    const segs = parseCitationSegments("see [1,2,3]");
    expect(segs.find((s) => s.type === "citation")).toEqual({ type: "citation", ids: [1, 2, 3] });
  });

  it("parses multiple separate citation markers in one string", () => {
    const segs = parseCitationSegments("[1] and [2]");
    const citationSegs = segs.filter((s) => s.type === "citation");
    expect(citationSegs).toEqual([
      { type: "citation", ids: [1] },
      { type: "citation", ids: [2] },
    ]);
  });

  it("supports full-width bracket variants", () => {
    const segs = parseCitationSegments("见【4】");
    expect(segs.find((s) => s.type === "citation")).toEqual({ type: "citation", ids: [4] });
  });

  it("does not treat a bare number in brackets-less text as a citation", () => {
    expect(parseCitationSegments("chunk 12 was retrieved")).toEqual([
      { type: "text", value: "chunk 12 was retrieved" },
    ]);
  });
});
