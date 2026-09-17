jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { localExpertProvider } from '../services/localExpertProvider';
import { ExpertError } from '../services/expertProvider';
import { expertStorage } from '../services/expertStorage';
import type { ConsultationInput } from '../types';

function input(overrides: Partial<ConsultationInput> = {}): ConsultationInput {
  return {
    category: 'crop_disease',
    subject: 'Yellow spots on paddy',
    description: 'Yellow spots are spreading on my paddy leaves.',
    ...overrides,
  };
}

describe('localExpertProvider', () => {
  beforeEach(() => expertStorage.clear());

  it('seeds verified experts and lists them', async () => {
    const page = await localExpertProvider.listExperts({});
    expect(page.total).toBeGreaterThanOrEqual(5);
    expect(page.items.every((e) => e.verified)).toBe(true);
  });

  it('filters experts by category', async () => {
    const page = await localExpertProvider.listExperts({ category: 'soil_health' });
    expect(page.items.every((e) => e.categories.includes('soil_health'))).toBe(true);
  });

  it('creates a consultation, assigns a desk and opens the thread', async () => {
    const c = await localExpertProvider.createConsultation(input());
    expect(c.status).toBe('assigned');
    expect(c.assignedExpertId).toBeTruthy();
    expect(c.expert?.categories).toContain('crop_disease');
    // Opening farmer message + a system acknowledgement (no fabricated advice).
    expect(c.messages).toHaveLength(2);
    expect(c.messages[0].senderType).toBe('farmer');
    expect(c.messages[1].isSystem).toBe(true);
    expect(c.statusHistory.map((h) => h.newStatus)).toEqual(['submitted', 'assigned']);
  });

  it('attaches photos to the opening message', async () => {
    const c = await localExpertProvider.createConsultation(
      input({ attachments: [{ fileUrl: 'https://r2/leaf.jpg', kind: 'image' }] }),
    );
    expect(c.attachmentCount).toBe(1);
    expect(c.attachments[0].messageId).toBe(c.messages[0].id);
  });

  it('appends a reply and moves the thread to the expert', async () => {
    const created = await localExpertProvider.createConsultation(input());
    const c = await localExpertProvider.reply(created.id, { body: 'Started 3 days ago.' });
    expect(c.messages).toHaveLength(3);
    expect(c.status).toBe('awaiting_expert');
  });

  it('reopens a resolved consultation on a farmer reply', async () => {
    const created = await localExpertProvider.createConsultation(input());
    await localExpertProvider.updateStatus(created.id, 'resolved');
    const c = await localExpertProvider.reply(created.id, { body: 'It came back.' });
    expect(c.status).toBe('in_progress');
  });

  it('blocks a reply once cancelled', async () => {
    const created = await localExpertProvider.createConsultation(input());
    await localExpertProvider.updateStatus(created.id, 'cancelled');
    await expect(
      localExpertProvider.reply(created.id, { body: 'hello?' }),
    ).rejects.toBeInstanceOf(ExpertError);
  });

  it('resolves with a note and timestamp', async () => {
    const created = await localExpertProvider.createConsultation(input());
    const c = await localExpertProvider.updateStatus(created.id, 'resolved', 'Sorted');
    expect(c.status).toBe('resolved');
    expect(c.resolvedAt).toBeTruthy();
    expect(c.resolutionNote).toBe('Sorted');
  });

  it('rejects a status a farmer cannot set', async () => {
    const created = await localExpertProvider.createConsultation(input());
    await expect(
      localExpertProvider.updateStatus(created.id, 'in_progress'),
    ).rejects.toBeInstanceOf(ExpertError);
  });

  it('splits pending and history', async () => {
    const open = await localExpertProvider.createConsultation(input({ subject: 'Open' }));
    const done = await localExpertProvider.createConsultation(input({ subject: 'Done' }));
    await localExpertProvider.updateStatus(done.id, 'resolved');

    const pending = await localExpertProvider.pending();
    const history = await localExpertProvider.history();
    expect(pending.items.map((c) => c.id)).toContain(open.id);
    expect(history.items.map((c) => c.id)).toContain(done.id);
    expect(pending.items.map((c) => c.id)).not.toContain(done.id);
  });

  it('adds a standalone attachment', async () => {
    const created = await localExpertProvider.createConsultation(input());
    const c = await localExpertProvider.addAttachment(created.id, {
      fileUrl: 'https://r2/extra.jpg',
      caption: 'close-up',
    });
    expect(c.attachments.some((a) => a.caption === 'close-up')).toBe(true);
  });

  it('throws for an unknown consultation', async () => {
    await expect(localExpertProvider.getConsultation('nope')).rejects.toBeInstanceOf(
      ExpertError,
    );
  });
});
