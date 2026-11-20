import { describe, it, expect } from 'vitest';
import { extractVars, resolvePreviewText } from '../templateInterpolation.js';

describe('templateInterpolation', () => {
  describe('extractVars', () => {
    it('extracts and deduplicates variable indices in ascending order', () => {
      const text = 'Hello {{2}}, your order {{1}} is confirmed! See you {{2}}.';
      expect(extractVars(text)).toEqual(['1', '2']);
    });

    it('returns empty array when text has no template variables', () => {
      expect(extractVars('Plain message without variables')).toEqual([]);
      expect(extractVars('')).toEqual([]);
      expect(extractVars(null)).toEqual([]);
    });
  });

  describe('resolvePreviewText', () => {
    const contact = {
      name: 'Alice',
      contact_number: '919876543210',
      custom_fields: { plan: 'Enterprise' },
      tags: [{ category_id: 10, name: 'VIP' }],
    };

    it('substitutes contact name and custom fields', () => {
      const text = 'Hello {{1}}, welcome to {{2}} plan!';
      const mapping = { '1': 'name', '2': 'custom_fields.plan' };
      expect(resolvePreviewText(text, mapping, contact)).toBe('Hello Alice, welcome to Enterprise plan!');
    });

    it('substitutes category tags', () => {
      const text = 'Tier: {{1}}';
      const mapping = { '1': 'category_tag.10' };
      expect(resolvePreviewText(text, mapping, contact)).toBe('Tier: VIP');
    });

    it('falls back to variable token if field is unmapped or absent', () => {
      const text = 'Hello {{1}} and {{2}}';
      const mapping = { '1': 'unmapped' };
      expect(resolvePreviewText(text, mapping, contact)).toBe('Hello unmapped and {{2}}');
    });

    it('returns original text if contact is missing', () => {
      expect(resolvePreviewText('Hello {{1}}', { '1': 'name' }, null)).toBe('Hello {{1}}');
    });
  });
});
