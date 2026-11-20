import { maskPhone } from '../constants.js';

export function extractVars(text) {
  const matches = [...(text || '').matchAll(/\{\{(\d+)\}\}/g)];
  return [...new Set(matches.map(x => x[1]))].sort((a, b) => +a - +b);
}

export function resolvePreviewText(text, mapping = {}, contact = null) {
  if (!text || !contact) return text || '';
  return text.replace(/\{\{(\d+)\}\}/g, (_, v) => {
    const field = mapping[v];
    if (!field) return `{{${v}}}`;
    if (field === 'name') return contact.name || `{{${v}}}`;
    if (field === 'contact_number') return maskPhone(contact.contact_number) || `{{${v}}}`;
    if (field.startsWith('custom_fields.')) {
      const id = field.split('.')[1];
      return contact.custom_fields?.[id] || `{{${v}}}`;
    }
    if (field.startsWith('category_tag.')) {
      const catId = field.split('.')[1];
      const tag = contact.tags?.find(t => t.category_id == catId);
      return tag?.name || `{{${v}}}`;
    }
    return field || `{{${v}}}`;
  });
}
