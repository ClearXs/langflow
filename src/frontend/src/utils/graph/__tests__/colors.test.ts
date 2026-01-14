/**
 * Unit tests for color utilities
 */

import { describe, expect, it } from "vitest";
import {
  ENTITY_TYPE_COLORS,
  generateColorMap,
  getEdgeOpacity,
  getEdgeWidth,
  getEntityTypeColor,
} from "../colors";

describe("ENTITY_TYPE_COLORS", () => {
  it("should have 10 predefined colors", () => {
    const colors = Object.keys(ENTITY_TYPE_COLORS);
    expect(colors).toHaveLength(10);
  });

  it("should have valid hex color values", () => {
    const hexColorRegex = /^#[0-9A-F]{6}$/i;
    Object.values(ENTITY_TYPE_COLORS).forEach((color) => {
      expect(color).toMatch(hexColorRegex);
    });
  });

  it("should include common entity types", () => {
    expect(ENTITY_TYPE_COLORS).toHaveProperty("Person");
    expect(ENTITY_TYPE_COLORS).toHaveProperty("Organization");
    expect(ENTITY_TYPE_COLORS).toHaveProperty("Location");
    expect(ENTITY_TYPE_COLORS).toHaveProperty("Event");
    expect(ENTITY_TYPE_COLORS).toHaveProperty("Other");
  });

  it("should have unique colors for each type", () => {
    const colors = Object.values(ENTITY_TYPE_COLORS);
    const uniqueColors = new Set(colors);
    expect(uniqueColors.size).toBe(colors.length);
  });
});

describe("getEntityTypeColor", () => {
  it("should return correct color for known entity types", () => {
    expect(getEntityTypeColor("Person")).toBe("#5B8FF9");
    expect(getEntityTypeColor("Organization")).toBe("#5AD8A6");
    expect(getEntityTypeColor("Location")).toBe("#5D7092");
  });

  it("should return Other color for unknown entity types", () => {
    const otherColor = ENTITY_TYPE_COLORS.Other;
    expect(getEntityTypeColor("UnknownType")).toBe(otherColor);
    expect(getEntityTypeColor("RandomType")).toBe(otherColor);
  });

  it("should be case sensitive", () => {
    expect(getEntityTypeColor("person")).toBe(ENTITY_TYPE_COLORS.Other);
    expect(getEntityTypeColor("PERSON")).toBe(ENTITY_TYPE_COLORS.Other);
  });

  it("should handle empty string", () => {
    expect(getEntityTypeColor("")).toBe(ENTITY_TYPE_COLORS.Other);
  });
});

describe("generateColorMap", () => {
  it("should generate color map for entity types", () => {
    const types = ["Person", "Organization", "Location"];
    const colorMap = generateColorMap(types);

    expect(Object.keys(colorMap)).toHaveLength(3);
    expect(colorMap).toHaveProperty("Person");
    expect(colorMap).toHaveProperty("Organization");
    expect(colorMap).toHaveProperty("Location");
  });

  it("should assign unique colors to unique types", () => {
    const types = ["Type1", "Type2", "Type3"];
    const colorMap = generateColorMap(types);

    const colors = Object.values(colorMap);
    const uniqueColors = new Set(colors);
    expect(uniqueColors.size).toBe(3);
  });

  it("should handle duplicate entity types", () => {
    const types = ["Person", "Person", "Organization"];
    const colorMap = generateColorMap(types);

    expect(Object.keys(colorMap)).toHaveLength(2);
    expect(colorMap).toHaveProperty("Person");
    expect(colorMap).toHaveProperty("Organization");
  });

  it("should cycle colors for more than 10 types", () => {
    const types = Array.from({ length: 15 }, (_, i) => `Type${i}`);
    const colorMap = generateColorMap(types);

    expect(Object.keys(colorMap)).toHaveLength(15);

    const paletteColors = Object.values(ENTITY_TYPE_COLORS);
    Object.values(colorMap).forEach((color) => {
      expect(paletteColors).toContain(color);
    });
  });

  it("should handle empty array", () => {
    const colorMap = generateColorMap([]);
    expect(Object.keys(colorMap)).toHaveLength(0);
  });

  it("should produce consistent results for same input", () => {
    const types = ["Person", "Organization", "Location"];
    const colorMap1 = generateColorMap(types);
    const colorMap2 = generateColorMap(types);

    expect(colorMap1).toEqual(colorMap2);
  });
});

describe("getEdgeOpacity", () => {
  it("should map weight 0.0 to opacity 0.3", () => {
    expect(getEdgeOpacity(0.0)).toBe(0.3);
  });

  it("should map weight 1.0 to opacity 1.0", () => {
    expect(getEdgeOpacity(1.0)).toBe(1.0);
  });

  it("should map weight 0.5 to opacity 0.65", () => {
    expect(getEdgeOpacity(0.5)).toBe(0.65);
  });

  it("should handle intermediate values correctly", () => {
    expect(getEdgeOpacity(0.25)).toBeCloseTo(0.475, 2);
    expect(getEdgeOpacity(0.75)).toBeCloseTo(0.825, 2);
  });

  it("should produce values in range [0.3, 1.0]", () => {
    for (let weight = 0; weight <= 1; weight += 0.1) {
      const opacity = getEdgeOpacity(weight);
      expect(opacity).toBeGreaterThanOrEqual(0.3);
      expect(opacity).toBeLessThanOrEqual(1.0);
    }
  });

  it("should be monotonically increasing", () => {
    let prevOpacity = getEdgeOpacity(0);
    for (let weight = 0.1; weight <= 1; weight += 0.1) {
      const opacity = getEdgeOpacity(weight);
      expect(opacity).toBeGreaterThan(prevOpacity);
      prevOpacity = opacity;
    }
  });
});

describe("getEdgeWidth", () => {
  it("should map weight 0.0 to width 1", () => {
    expect(getEdgeWidth(0.0)).toBe(1);
  });

  it("should map weight 1.0 to width 4", () => {
    expect(getEdgeWidth(1.0)).toBe(4);
  });

  it("should map weight 0.5 to width 2.5", () => {
    expect(getEdgeWidth(0.5)).toBe(2.5);
  });

  it("should handle intermediate values correctly", () => {
    expect(getEdgeWidth(0.25)).toBeCloseTo(1.75, 2);
    expect(getEdgeWidth(0.75)).toBeCloseTo(3.25, 2);
  });

  it("should produce values in range [1, 4]", () => {
    for (let weight = 0; weight <= 1; weight += 0.1) {
      const width = getEdgeWidth(weight);
      expect(width).toBeGreaterThanOrEqual(1);
      expect(width).toBeLessThanOrEqual(4);
    }
  });

  it("should be monotonically increasing", () => {
    let prevWidth = getEdgeWidth(0);
    for (let weight = 0.1; weight <= 1; weight += 0.1) {
      const width = getEdgeWidth(weight);
      expect(width).toBeGreaterThan(prevWidth);
      prevWidth = width;
    }
  });

  it("should produce different widths for different weights", () => {
    const width1 = getEdgeWidth(0.2);
    const width2 = getEdgeWidth(0.8);
    expect(width1).not.toBe(width2);
    expect(width2).toBeGreaterThan(width1);
  });
});
