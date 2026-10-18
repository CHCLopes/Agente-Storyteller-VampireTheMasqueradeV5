import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const stylesheet = readFileSync(
  resolve(process.cwd(), 'src', 'index.css'),
  'utf8',
);

describe('theme contract', () => {
  it('binds Tailwind dark and light variants to the explicit html classes', () => {
    expect(stylesheet).toContain(
      '@custom-variant dark (&:where(.dark, .dark *));',
    );
    expect(stylesheet).toContain(
      '@custom-variant light (&:where(.light, .light *));',
    );
    expect(stylesheet).toContain(':root.light');
    expect(stylesheet).toContain('color-scheme: light');
  });
});
