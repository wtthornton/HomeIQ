/**
 * Naming rubric parity (TAP-6230).
 *
 * The device-intelligence service owns the only naming/area rubric. The
 * dashboard used to carry a second copy in TypeScript and the two disagreed on
 * six axes, so the Overview and HA Setup tabs could show different numbers for
 * the same entity.
 *
 * `contracts/naming-rubric/golden-vectors.json` is generated from the Python
 * engine (`contracts/naming-rubric/generate_vectors.py`). This suite feeds each
 * vector's server response through the dashboard's mapping and asserts the
 * number the user sees is the number the backend computed. The Python suite
 * asserts the other half — that the engine still produces these vectors — so a
 * rubric change that reaches only one side fails CI.
 */

import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';
import { toAuditScore } from '../useEntityAudit';
import type { ServerEntityScore } from '../../services/namingApi';

interface GoldenVector {
  name: string;
  why: string;
  entity: Record<string, unknown>;
  expected: ServerEntityScore;
}

const vectors: GoldenVector[] = JSON.parse(
  readFileSync(
    resolve(__dirname, '../../../../../../contracts/naming-rubric/golden-vectors.json'),
    'utf-8'
  )
).vectors;

describe('naming rubric parity with the backend', () => {
  it('has vectors to check', () => {
    expect(vectors.length).toBeGreaterThan(0);
  });

  it.each(vectors)('renders the backend score for $name unchanged', ({ expected, why }) => {
    expect(toAuditScore(expected).total, why).toBe(expected.total_score);
  });

  it.each(vectors)('never reports above the rubric maximum for $name', ({ expected }) => {
    const score = toAuditScore(expected);
    expect(score.total).toBeLessThanOrEqual(score.max);
  });

  it('derives every audit flag from the backing rule, not from the entity', () => {
    const perfect = vectors.find(v => v.name === 'perfect_sensor');
    const bare = vectors.find(v => v.name === 'bare_entity');
    expect(perfect && bare).toBeTruthy();

    const good = toAuditScore(perfect!.expected);
    expect(good).toMatchObject({
      hasArea: true,
      hasLabels: true,
      hasAliases: true,
      hasDeviceClass: true,
      nameFollowsConvention: true,
    });

    const empty = toAuditScore(bare!.expected);
    expect(empty).toMatchObject({
      hasArea: false,
      hasLabels: false,
      hasAliases: false,
      hasDeviceClass: false,
      nameFollowsConvention: false,
    });
  });

  it('treats a partially-credited name as not following convention', () => {
    // 'lowercase_name' loses points for case but keeps its area prefix, so the
    // flag must track full credit rather than any credit.
    const partial = vectors.find(v => v.name === 'lowercase_name');
    expect(partial).toBeTruthy();
    expect(toAuditScore(partial!.expected).nameFollowsConvention).toBe(false);
  });
});
