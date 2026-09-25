import { formatPoints, formatRelative } from "@/lib/utils";

describe("formatPoints", () => {
  it("formats positive, negative and zero points", () => {
    expect(formatPoints(5)).toBe("+5");
    expect(formatPoints(-25)).toBe("−25");
    expect(formatPoints(0)).toBe("0");
  });
});

describe("formatRelative", () => {
  const now = new Date("2026-09-25T12:00:00Z");
  it("describes recent times", () => {
    expect(formatRelative("2026-09-25T11:59:30Z", now)).toBe("just now");
    expect(formatRelative("2026-09-25T11:30:00Z", now)).toBe("30 min ago");
    expect(formatRelative("2026-09-25T09:00:00Z", now)).toBe("3 h ago");
    expect(formatRelative("2026-09-23T12:00:00Z", now)).toBe("2 d ago");
  });
});
