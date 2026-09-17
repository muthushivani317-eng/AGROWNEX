import { deriveTitle, generateMockReply } from '../services/mockReply';

describe('mockReply', () => {
  it('derives a trimmed, capped title', () => {
    expect(deriveTitle('  How   do I   grow paddy?  ')).toBe('How do I grow paddy?');
    expect(deriveTitle('')).toBe('Chat');
    expect(deriveTitle('x'.repeat(100))).toHaveLength(60);
  });

  it('replies in the requested language and echoes the question', () => {
    const ta = generateMockReply('எப்படி?', 'ta');
    expect(ta).toContain('எப்படி?');
    expect(ta).toContain('டெமோ பதில்');

    const en = generateMockReply('How?', 'en');
    expect(en).toContain('How?');
    expect(en).toContain('demo response');
  });
});
