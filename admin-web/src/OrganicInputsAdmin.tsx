import { useState } from 'react';
import { getCsrfToken } from './api';
import { getConfig } from './config';
import { Card, DataTable, ErrorPanel, Loading, PageTitle } from './components';
import { useResource } from './useResource';
import './OrganicInputsAdmin.css';

// ---------------------------------------------------------------------------
// /admin/organic-inputs/* returns plain JSON, not the {success,data} envelope
// the shared api() helper expects -- same reason OrganicPilot.tsx and
// PartnerOrganizations.tsx have their own fetch wrapper instead of api().
// ---------------------------------------------------------------------------
async function inputsRequest<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`${getConfig().apiBaseUrl}${path}`, {
    method,
    credentials: 'include',
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(method !== 'GET' && getCsrfToken() ? { 'X-CSRF-Token': getCsrfToken()! } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as
      | { detail?: { message?: string } | string }
      | null;
    const message = typeof detail?.detail === 'string' ? detail.detail : detail?.detail?.message;
    throw new Error(message ?? `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Types (mirror backend/app/modules/organic_inputs/schemas.py exactly)
// ---------------------------------------------------------------------------

type Category = {
  id: string; slug: string; name: string; name_ta: string | null;
  description: string | null; status: string; display_order: number;
};
type ProductTypeVersion = {
  id: string; version: number; is_current: boolean; unit_of_measurement: string;
  allowed_pack_sizes: string[]; intended_purposes: string[]; suitable_crops: string[];
  suitable_crop_stages: string[]; regulatory_classification: string | null; updated_at: string;
};
type ProductType = {
  id: string; category_id: string; slug: string; name: string; name_ta: string | null;
  status: string; current_version: ProductTypeVersion | null;
};
type ProductRequest = {
  id: string; proposed_name_en: string; proposed_name_ta: string | null;
  status: string; review_note: string | null; created_at: string;
};
type SupplierDoc = { id: string; document_type: string; file_url: string; verified: boolean; verification_note: string | null };
type Supplier = {
  id: string; status: string; production_location: string | null; district: string | null;
  village: string | null; contact_name: string | null; contact_phone: string | null;
  production_capacity_note: string | null; rejection_reason: string | null;
  suspension_reason: string | null; created_at: string; updated_at: string;
  documents?: SupplierDoc[];
};
type BatchIngredient = { ingredient_name: string; ingredient_name_ta: string | null; source: string | null; quantity: string | null; unit: string | null };
type BatchDoc = { id: string; document_type: string; file_url: string; caption: string | null };
type Batch = {
  id: string; batch_code: string; product_type_id: string; status: string;
  batch_quantity: string; unit: string; available_quantity_offered: string | null;
  expected_procurement_price: string | null; use_before_date: string | null;
  submission_date: string | null; latest_review_note: string | null;
  approved_quantity: string | null; rejected_quantity: string | null; created_at: string;
  ingredients: BatchIngredient[]; documents: BatchDoc[];
};
type TestResult = {
  id: string; parameter_name: string; parameter_name_ta: string | null;
  expected_limit: Record<string, unknown> | null; measured_value: string | null;
  unit: string | null; pass_fail: boolean; lab_name: string | null; tested_at: string | null;
};
type Sample = {
  id: string; sample_code: string; collected_at: string; quantity: string | null;
  unit: string | null; storage_condition: string | null; test_results: TestResult[];
};
type Offer = {
  id: string; batch_id: string; offered_quantity: string; unit: string;
  offered_unit_price: string; status: string; offered_at: string;
  decided_at: string | null; rejection_reason: string | null;
};
type Receipt = { id: string; received_quantity: string; unit: string; received_at: string; condition_note: string | null };
type Movement = { id: string; movement_type: string; quantity_delta: string; note: string | null; created_at: string };
type InventoryLot = {
  id: string; batch_id: string; product_type_id: string; quantity_available: string;
  unit: string; unit_cost: string; created_at: string; movements: Movement[];
};

// Client-side mirror of the backend's *_ADMIN_DECISIONS maps (constants.py) --
// only used to populate the "next status" dropdown; the backend re-checks
// every transition itself via assert_transition_allowed, so a stale/incorrect
// client map can only make the UI offer a choice the server then rejects,
// never bypass the real guard.
const SUPPLIER_NEXT: Record<string, string[]> = {
  submitted: ['under_review'],
  under_review: ['clarification_required', 'inspection_scheduled', 'rejected'],
  clarification_required: ['under_review'],
  inspection_scheduled: ['inspection_completed'],
  inspection_completed: ['approved', 'rejected'],
  approved: ['suspended', 'expired'],
  suspended: ['approved', 'expired'],
};
const BATCH_NEXT: Record<string, string[]> = {
  submitted: ['under_review'],
  under_review: ['clarification_required', 'inspection_required', 'rejected'],
  clarification_required: ['under_review'],
  testing: ['retest_required', 'approved', 'partially_approved', 'rejected'],
  received: ['quarantined', 'released_for_sale'],
  quarantined: ['released_for_sale', 'rejected'],
  released_for_sale: ['sold_out', 'expired', 'recalled'],
};

const label = (value: string) => value.replaceAll('_', ' ');

function StatusPill({ value }: { value: string }) {
  return <span className="oi-pill" data-status={value}>{label(value)}</span>;
}

const TABS = ['Catalogue', 'Suppliers', 'Batches & QC', 'Procurement & Inventory'] as const;
type Tab = (typeof TABS)[number];

export function OrganicInputsAdminPage({ permissions }: { permissions: string[] }) {
  const [tab, setTab] = useState<Tab>('Catalogue');
  const canCatalog = permissions.includes('manage_marketplace_catalog');
  const canSuppliers = permissions.includes('manage_marketplace_suppliers');
  const canQc = permissions.includes('manage_marketplace_qc');
  const canProcurement = permissions.includes('manage_marketplace_procurement');
  return (
    <>
      <PageTitle
        title="Organic Inputs Marketplace"
        subtitle="Catalogue, supplier onboarding, batch QC, procurement and inventory. Every action here is audit-logged."
      />
      <div className="oi-tabs" aria-label="Organic inputs sections">
        {TABS.map((name) => (
          <button key={name} aria-pressed={tab === name} onClick={() => setTab(name)}>{name}</button>
        ))}
      </div>
      {tab === 'Catalogue' && <CatalogueTab canWrite={canCatalog} />}
      {tab === 'Suppliers' && <SuppliersTab canWrite={canSuppliers} />}
      {tab === 'Batches & QC' && <BatchesTab canQc={canQc} canSuppliers={canSuppliers} />}
      {tab === 'Procurement & Inventory' && <ProcurementTab canWrite={canProcurement} />}
    </>
  );
}

// ---------------------------------------------------------------------------
// Catalogue
// ---------------------------------------------------------------------------

function CatalogueTab({ canWrite }: { canWrite: boolean }) {
  const categories = useResource(() => inputsRequest<Category[]>('/admin/organic-inputs/categories'));
  const productTypes = useResource(() => inputsRequest<ProductType[]>('/admin/organic-inputs/product-types'));
  const requests = useResource(() => inputsRequest<ProductRequest[]>('/admin/organic-inputs/product-type-requests'));

  const [catForm, setCatForm] = useState({ slug: '', name: '', name_ta: '', description: '' });
  const [ptForm, setPtForm] = useState({ category_id: '', slug: '', name: '', name_ta: '' });
  const [verForm, setVerForm] = useState({ product_type_id: '', unit_of_measurement: '', suitable_crops: '', regulatory_classification: '' });
  const [error, setError] = useState('');

  if (!canWrite) {
    return (
      <Card>
        <h2>Catalogue</h2>
        <p>Managing categories and product types needs the Catalog permission (Owner / Super Admin only).</p>
      </Card>
    );
  }

  async function reloadAll() {
    await Promise.all([categories.reload(), productTypes.reload(), requests.reload()]);
  }

  async function createCategory(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await inputsRequest('/admin/organic-inputs/categories', 'POST', {
        slug: catForm.slug, name: catForm.name,
        name_ta: catForm.name_ta || null, description: catForm.description || null,
      });
      setCatForm({ slug: '', name: '', name_ta: '', description: '' });
      await categories.reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create category.'); }
  }

  async function createProductType(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await inputsRequest('/admin/organic-inputs/product-types', 'POST', {
        category_id: ptForm.category_id, slug: ptForm.slug,
        name: ptForm.name, name_ta: ptForm.name_ta || null,
      });
      setPtForm({ category_id: '', slug: '', name: '', name_ta: '' });
      await productTypes.reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create product type.'); }
  }

  async function publishVersion(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/product-types/${verForm.product_type_id}/versions`, 'POST', {
        unit_of_measurement: verForm.unit_of_measurement,
        suitable_crops: verForm.suitable_crops ? verForm.suitable_crops.split(',').map((s) => s.trim()).filter(Boolean) : [],
        regulatory_classification: verForm.regulatory_classification || null,
      });
      setVerForm({ product_type_id: '', unit_of_measurement: '', suitable_crops: '', regulatory_classification: '' });
      await productTypes.reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not publish version.'); }
  }

  async function setStatus(productTypeId: string, status: string) {
    setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/product-types/${productTypeId}/status`, 'POST', { status });
      await productTypes.reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not change status.'); }
  }

  async function decideRequest(id: string, status: 'approved' | 'rejected') {
    setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/product-type-requests/${id}/decision`, 'POST', { status });
      await requests.reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not decide request.'); }
  }

  return (
    <>
      {error && <p className="form-error">{error}</p>}
      <div className="split">
        <Card>
          <h2>Add category</h2>
          <form className="stack" onSubmit={createCategory}>
            <label>Slug<input required pattern="[a-z0-9-]+" placeholder="liquid-inputs" value={catForm.slug} onChange={(e) => setCatForm({ ...catForm, slug: e.target.value })} /></label>
            <label>Name<input required value={catForm.name} onChange={(e) => setCatForm({ ...catForm, name: e.target.value })} /></label>
            <label>Name (Tamil, optional)<input value={catForm.name_ta} onChange={(e) => setCatForm({ ...catForm, name_ta: e.target.value })} /></label>
            <label>Description (optional)<input value={catForm.description} onChange={(e) => setCatForm({ ...catForm, description: e.target.value })} /></label>
            <button>Add category</button>
          </form>
        </Card>
        <Card>
          <h2>Add product type</h2>
          <form className="stack" onSubmit={createProductType}>
            <label>Category<select required value={ptForm.category_id} onChange={(e) => setPtForm({ ...ptForm, category_id: e.target.value })}>
              <option value="">Select a category</option>
              {(categories.data ?? []).map((c) => <option key={c.id} value={c.id}>{c.name} ({c.status})</option>)}
            </select></label>
            <label>Slug<input required pattern="[a-z0-9-]+" placeholder="fish-amino-acid" value={ptForm.slug} onChange={(e) => setPtForm({ ...ptForm, slug: e.target.value })} /></label>
            <label>Name<input required value={ptForm.name} onChange={(e) => setPtForm({ ...ptForm, name: e.target.value })} /></label>
            <label>Name (Tamil, optional)<input value={ptForm.name_ta} onChange={(e) => setPtForm({ ...ptForm, name_ta: e.target.value })} /></label>
            <button>Add product type</button>
          </form>
        </Card>
      </div>

      <Card>
        <h2>Categories</h2>
        {categories.loading ? <Loading /> : categories.error ? <ErrorPanel message={categories.error} retry={() => void categories.reload()} /> :
          <DataTable columns={['Slug', 'Name', 'Status', 'Order']} rows={(categories.data ?? []).map((c) => [c.slug, c.name, <StatusPill value={c.status} />, c.display_order])} />}
      </Card>

      <Card>
        <h2>Product types</h2>
        {productTypes.loading ? <Loading /> : productTypes.error ? <ErrorPanel message={productTypes.error} retry={() => void productTypes.reload()} /> :
          <DataTable
            columns={['Slug', 'Name', 'Status', 'Current version', 'Set status']}
            rows={(productTypes.data ?? []).map((p) => [
              p.slug, p.name, <StatusPill value={p.status} />,
              p.current_version ? `v${p.current_version.version} · ${p.current_version.unit_of_measurement}` : 'No version yet',
              <select defaultValue="" onChange={(e) => { if (e.target.value) void setStatus(p.id, e.target.value); e.target.value = ''; }}>
                <option value="">Change…</option>
                <option value="draft">draft</option><option value="active">active</option>
                <option value="suspended">suspended</option><option value="archived">archived</option>
              </select>,
            ])}
          />}
      </Card>

      <Card>
        <h2>Publish a new product-type version</h2>
        <p>A batch already referencing an older version keeps that snapshot — this never edits a past version.</p>
        <form className="stack" onSubmit={publishVersion}>
          <label>Product type<select required value={verForm.product_type_id} onChange={(e) => setVerForm({ ...verForm, product_type_id: e.target.value })}>
            <option value="">Select a product type</option>
            {(productTypes.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select></label>
          <label>Unit of measurement<input required placeholder="litre / kg" value={verForm.unit_of_measurement} onChange={(e) => setVerForm({ ...verForm, unit_of_measurement: e.target.value })} /></label>
          <label>Suitable crops (comma-separated, optional)<input placeholder="paddy, chilli, tomato" value={verForm.suitable_crops} onChange={(e) => setVerForm({ ...verForm, suitable_crops: e.target.value })} /></label>
          <label>Regulatory classification (optional)<input value={verForm.regulatory_classification} onChange={(e) => setVerForm({ ...verForm, regulatory_classification: e.target.value })} /></label>
          <button>Publish version</button>
        </form>
      </Card>

      <Card>
        <h2>New-product-type requests from farmers</h2>
        {requests.loading ? <Loading /> : requests.error ? <ErrorPanel message={requests.error} retry={() => void requests.reload()} /> :
          <DataTable
            columns={['Proposed name', 'Status', 'Submitted', 'Decision']}
            rows={(requests.data ?? []).map((r) => [
              r.proposed_name_en, <StatusPill value={r.status} />, new Date(r.created_at).toLocaleDateString('en-IN'),
              r.status === 'pending'
                ? <span className="oi-actions"><button onClick={() => void decideRequest(r.id, 'approved')}>Approve</button><button className="secondary-button" onClick={() => void decideRequest(r.id, 'rejected')}>Reject</button></span>
                : (r.review_note ?? '—'),
            ])}
          />}
        <p className="oi-note">Approving only clears the queue — it does not itself create a sellable product type; add that deliberately above.</p>
      </Card>
    </>
  );
}

// ---------------------------------------------------------------------------
// Suppliers
// ---------------------------------------------------------------------------

function SuppliersTab({ canWrite }: { canWrite: boolean }) {
  const [statusFilter, setStatusFilter] = useState('');
  const suppliers = useResource(() => inputsRequest<Supplier[]>(`/admin/organic-inputs/suppliers${statusFilter ? `?status=${statusFilter}` : ''}`), [statusFilter]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const detail = useResource(() => (selectedId ? inputsRequest<Supplier>(`/admin/organic-inputs/suppliers/${selectedId}`) : Promise.resolve(null)), [selectedId]);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');

  async function decide(status: string) {
    if (!selectedId) return;
    setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/suppliers/${selectedId}/decision`, 'POST', { status, note: note || null });
      setNote('');
      await Promise.all([suppliers.reload(), detail.reload()]);
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not decide.'); }
  }

  return (
    <>
      {error && <p className="form-error">{error}</p>}
      <Card>
        <div className="section-head">
          <h2>Suppliers</h2>
          <label>Filter by status<select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            {['draft', 'submitted', 'under_review', 'clarification_required', 'inspection_scheduled', 'inspection_completed', 'approved', 'rejected', 'suspended', 'expired'].map((s) => <option key={s} value={s}>{label(s)}</option>)}
          </select></label>
        </div>
        {suppliers.loading ? <Loading /> : suppliers.error ? <ErrorPanel message={suppliers.error} retry={() => void suppliers.reload()} /> :
          <DataTable
            columns={['District / Village', 'Contact', 'Status', 'Applied', '']}
            rows={(suppliers.data ?? []).map((s) => [
              [s.district, s.village].filter(Boolean).join(' / ') || '—',
              [s.contact_name, s.contact_phone].filter(Boolean).join(' · ') || '—',
              <StatusPill value={s.status} />,
              new Date(s.created_at).toLocaleDateString('en-IN'),
              <button onClick={() => setSelectedId(s.id)}>View</button>,
            ])}
          />}
      </Card>

      {selectedId && (
        <Card>
          {detail.loading ? <Loading /> : detail.error ? <ErrorPanel message={detail.error} retry={() => void detail.reload()} /> : detail.data && (
            <>
              <div className="section-head"><h2>Supplier detail</h2><StatusPill value={detail.data.status} /></div>
              <dl className="oi-dl">
                <div><dt>Location</dt><dd>{detail.data.production_location ?? '—'}</dd></div>
                <div><dt>District / Village</dt><dd>{[detail.data.district, detail.data.village].filter(Boolean).join(' / ') || '—'}</dd></div>
                <div><dt>Contact</dt><dd>{[detail.data.contact_name, detail.data.contact_phone].filter(Boolean).join(' · ') || '—'}</dd></div>
                <div><dt>Capacity note</dt><dd>{detail.data.production_capacity_note ?? '—'}</dd></div>
                {detail.data.rejection_reason && <div><dt>Rejection reason</dt><dd>{detail.data.rejection_reason}</dd></div>}
                {detail.data.suspension_reason && <div><dt>Suspension reason</dt><dd>{detail.data.suspension_reason}</dd></div>}
              </dl>
              <h3>Documents</h3>
              {detail.data.documents?.length ? (
                <DataTable columns={['Type', 'Link', 'Verified']} rows={detail.data.documents.map((d) => [d.document_type, <a href={d.file_url} target="_blank" rel="noreferrer">Open</a>, d.verified ? 'Yes' : 'No'])} />
              ) : <p>No documents uploaded yet.</p>}
              {canWrite && SUPPLIER_NEXT[detail.data.status]?.length ? (
                <div className="oi-decide">
                  <h3>Decision</h3>
                  <label>Note (optional, required for reject/suspend)<input value={note} onChange={(e) => setNote(e.target.value)} /></label>
                  <div className="oi-actions">
                    {SUPPLIER_NEXT[detail.data.status].map((s) => <button key={s} className={s === 'rejected' || s === 'suspended' ? 'secondary-button' : ''} onClick={() => void decide(s)}>{label(s)}</button>)}
                  </div>
                </div>
              ) : canWrite ? <p className="oi-note">No further decision is reachable from this status.</p> : <p className="oi-note">Deciding needs the Suppliers permission (Field Verifier / Owner / Super Admin).</p>}
            </>
          )}
        </Card>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Batches & QC
// ---------------------------------------------------------------------------

function BatchesTab({ canQc, canSuppliers }: { canQc: boolean; canSuppliers: boolean }) {
  const [statusFilter, setStatusFilter] = useState('');
  const batches = useResource(() => inputsRequest<Batch[]>(`/admin/organic-inputs/batches${statusFilter ? `?status=${statusFilter}` : ''}`), [statusFilter]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const detail = useResource(() => (selectedId ? inputsRequest<Batch>(`/admin/organic-inputs/batches/${selectedId}`) : Promise.resolve(null)), [selectedId]);
  const samples = useResource(() => (selectedId ? inputsRequest<Sample[]>(`/admin/organic-inputs/batches/${selectedId}/samples`) : Promise.resolve([])), [selectedId]);
  const [error, setError] = useState('');

  const [inspection, setInspection] = useState<{ outcome: 'passed' | 'failed'; findings_note: string }>({ outcome: 'passed', findings_note: '' });
  const [sampleForm, setSampleForm] = useState({ quantity: '', unit: '', storage_condition: '' });
  const [resultForm, setResultForm] = useState({ sample_id: '', parameter_name: '', measured_value: '', unit: '', pass_fail: 'true', lab_name: '' });
  const [decision, setDecision] = useState({ status: '', note: '', approved_quantity: '', rejected_quantity: '' });

  async function reload() { await Promise.all([batches.reload(), detail.reload(), samples.reload()]); }

  async function recordInspection(e: React.FormEvent) {
    e.preventDefault(); if (!selectedId) return; setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/batches/${selectedId}/inspection`, 'POST', { outcome: inspection.outcome, findings_note: inspection.findings_note || null });
      setInspection({ outcome: 'passed', findings_note: '' });
      await reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not record inspection.'); }
  }

  async function collectSample(e: React.FormEvent) {
    e.preventDefault(); if (!selectedId) return; setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/batches/${selectedId}/samples`, 'POST', {
        quantity: sampleForm.quantity ? Number(sampleForm.quantity) : null,
        unit: sampleForm.unit || null, storage_condition: sampleForm.storage_condition || null,
      });
      setSampleForm({ quantity: '', unit: '', storage_condition: '' });
      await reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not collect sample.'); }
  }

  async function addTestResult(e: React.FormEvent) {
    e.preventDefault(); if (!selectedId || !resultForm.sample_id) return; setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/batches/${selectedId}/samples/${resultForm.sample_id}/test-results`, 'POST', {
        parameter_name: resultForm.parameter_name, measured_value: resultForm.measured_value || null,
        unit: resultForm.unit || null, pass_fail: resultForm.pass_fail === 'true', lab_name: resultForm.lab_name || null,
      });
      setResultForm({ sample_id: '', parameter_name: '', measured_value: '', unit: '', pass_fail: 'true', lab_name: '' });
      await reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not add test result.'); }
  }

  async function submitDecision(e: React.FormEvent) {
    e.preventDefault(); if (!selectedId || !decision.status) return; setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/batches/${selectedId}/decision`, 'POST', {
        status: decision.status, note: decision.note || null,
        approved_quantity: decision.approved_quantity ? Number(decision.approved_quantity) : null,
        rejected_quantity: decision.rejected_quantity ? Number(decision.rejected_quantity) : null,
      });
      setDecision({ status: '', note: '', approved_quantity: '', rejected_quantity: '' });
      await reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not record decision.'); }
  }

  const b = detail.data;
  return (
    <>
      {error && <p className="form-error">{error}</p>}
      <Card>
        <div className="section-head">
          <h2>Batches</h2>
          <label>Filter by status<select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            {['submitted', 'under_review', 'clarification_required', 'inspection_required', 'inspection_completed', 'sample_collected', 'testing', 'retest_required', 'approved', 'partially_approved', 'rejected', 'procurement_offered', 'offer_accepted', 'offer_rejected', 'received', 'quarantined', 'released_for_sale', 'sold_out'].map((s) => <option key={s} value={s}>{label(s)}</option>)}
          </select></label>
        </div>
        {batches.loading ? <Loading /> : batches.error ? <ErrorPanel message={batches.error} retry={() => void batches.reload()} /> :
          <DataTable
            columns={['Batch', 'Quantity', 'Status', 'Submitted', '']}
            rows={(batches.data ?? []).map((x) => [x.batch_code, `${x.batch_quantity} ${x.unit}`, <StatusPill value={x.status} />, x.submission_date ? new Date(x.submission_date).toLocaleDateString('en-IN') : '—', <button onClick={() => setSelectedId(x.id)}>View</button>])}
          />}
      </Card>

      {b && (
        <Card>
          <div className="section-head"><h2>Batch {b.batch_code}</h2><StatusPill value={b.status} /></div>
          <dl className="oi-dl">
            <div><dt>Quantity</dt><dd>{b.batch_quantity} {b.unit}</dd></div>
            {b.approved_quantity && <div><dt>Approved qty</dt><dd>{b.approved_quantity} {b.unit}</dd></div>}
            {b.rejected_quantity && <div><dt>Rejected qty</dt><dd>{b.rejected_quantity} {b.unit}</dd></div>}
            {b.latest_review_note && <div><dt>Latest note</dt><dd>{b.latest_review_note}</dd></div>}
          </dl>
          {b.ingredients.length > 0 && <><h3>Ingredients</h3><DataTable columns={['Ingredient', 'Source', 'Quantity']} rows={b.ingredients.map((i) => [i.ingredient_name, i.source ?? '—', i.quantity ? `${i.quantity} ${i.unit ?? ''}` : '—'])} /></>}
          {b.documents.length > 0 && <><h3>Documents</h3><DataTable columns={['Type', 'Link']} rows={b.documents.map((d) => [d.document_type, <a href={d.file_url} target="_blank" rel="noreferrer">Open</a>])} /></>}

          {canQc && b.status === 'inspection_required' && (
            <div className="oi-decide"><h3>Record site inspection</h3>
              <form className="stack" onSubmit={recordInspection}>
                <label>Outcome<select value={inspection.outcome} onChange={(e) => setInspection({ ...inspection, outcome: e.target.value as 'passed' | 'failed' })}><option value="passed">Passed</option><option value="failed">Failed</option></select></label>
                <label>Findings (optional)<input value={inspection.findings_note} onChange={(e) => setInspection({ ...inspection, findings_note: e.target.value })} /></label>
                <button>Record inspection</button>
              </form>
            </div>
          )}

          {canQc && (b.status === 'inspection_completed' || b.status === 'retest_required') && (
            <div className="oi-decide"><h3>Collect a sample</h3>
              <form className="stack" onSubmit={collectSample}>
                <label>Quantity (optional)<input type="number" min="0" step="0.001" value={sampleForm.quantity} onChange={(e) => setSampleForm({ ...sampleForm, quantity: e.target.value })} /></label>
                <label>Unit (optional)<input value={sampleForm.unit} onChange={(e) => setSampleForm({ ...sampleForm, unit: e.target.value })} /></label>
                <label>Storage condition (optional)<input value={sampleForm.storage_condition} onChange={(e) => setSampleForm({ ...sampleForm, storage_condition: e.target.value })} /></label>
                <button>Collect sample</button>
              </form>
            </div>
          )}

          <h3>Samples</h3>
          {samples.loading ? <Loading /> : (samples.data ?? []).length ? (samples.data ?? []).map((s) => (
            <Card key={s.id} className="oi-nested">
              <p><strong>{s.sample_code}</strong> · collected {new Date(s.collected_at).toLocaleString('en-IN')}</p>
              {s.test_results.length > 0 && <DataTable columns={['Parameter', 'Measured', 'Result', 'Lab']} rows={s.test_results.map((t) => [t.parameter_name, t.measured_value ? `${t.measured_value} ${t.unit ?? ''}` : '—', t.pass_fail ? 'Pass' : 'Fail', t.lab_name ?? '—'])} />}
            </Card>
          )) : <p>No samples collected yet.</p>}

          {canQc && (b.status === 'sample_collected' || b.status === 'testing') && (samples.data ?? []).length > 0 && (
            <div className="oi-decide"><h3>Add a test result</h3>
              <form className="stack" onSubmit={addTestResult}>
                <label>Sample<select required value={resultForm.sample_id} onChange={(e) => setResultForm({ ...resultForm, sample_id: e.target.value })}>
                  <option value="">Select a sample</option>
                  {(samples.data ?? []).map((s) => <option key={s.id} value={s.id}>{s.sample_code}</option>)}
                </select></label>
                <label>Parameter name<input required value={resultForm.parameter_name} onChange={(e) => setResultForm({ ...resultForm, parameter_name: e.target.value })} /></label>
                <label>Measured value (optional)<input value={resultForm.measured_value} onChange={(e) => setResultForm({ ...resultForm, measured_value: e.target.value })} /></label>
                <label>Unit (optional)<input value={resultForm.unit} onChange={(e) => setResultForm({ ...resultForm, unit: e.target.value })} /></label>
                <label>Result<select value={resultForm.pass_fail} onChange={(e) => setResultForm({ ...resultForm, pass_fail: e.target.value })}><option value="true">Pass</option><option value="false">Fail</option></select></label>
                <label>Lab name (optional)<input value={resultForm.lab_name} onChange={(e) => setResultForm({ ...resultForm, lab_name: e.target.value })} /></label>
                <button>Add test result</button>
              </form>
            </div>
          )}

          {(canQc || canSuppliers) && BATCH_NEXT[b.status]?.length ? (
            <div className="oi-decide"><h3>Decision</h3>
              <form className="stack" onSubmit={submitDecision}>
                <label>New status<select required value={decision.status} onChange={(e) => setDecision({ ...decision, status: e.target.value })}>
                  <option value="">Select…</option>
                  {BATCH_NEXT[b.status].map((s) => <option key={s} value={s}>{label(s)}</option>)}
                </select></label>
                {b.status === 'testing' && <>
                  <label>Approved quantity (optional)<input type="number" min="0" step="0.001" value={decision.approved_quantity} onChange={(e) => setDecision({ ...decision, approved_quantity: e.target.value })} /></label>
                  <label>Rejected quantity (optional)<input type="number" min="0" step="0.001" value={decision.rejected_quantity} onChange={(e) => setDecision({ ...decision, rejected_quantity: e.target.value })} /></label>
                </>}
                <label>Note (optional)<input value={decision.note} onChange={(e) => setDecision({ ...decision, note: e.target.value })} /></label>
                <button>Record decision</button>
              </form>
            </div>
          ) : <p className="oi-note">No decision reachable from this status here (this batch may await inspection/sampling/testing evidence, or a supplier's own procurement-offer decision, first).</p>}
        </Card>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Procurement & Inventory
// ---------------------------------------------------------------------------

function ProcurementTab({ canWrite }: { canWrite: boolean }) {
  const batches = useResource(() => inputsRequest<Batch[]>('/admin/organic-inputs/batches'));
  const inventory = useResource(() => inputsRequest<InventoryLot[]>('/admin/organic-inputs/inventory'));
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const offer = useResource(() => (selectedId ? inputsRequest<Offer | null>(`/admin/organic-inputs/batches/${selectedId}/procurement-offer`).catch(() => null) : Promise.resolve(null)), [selectedId]);
  const lot = useResource(() => (selectedId ? inputsRequest<InventoryLot | null>(`/admin/organic-inputs/batches/${selectedId}/inventory`).catch(() => null) : Promise.resolve(null)), [selectedId]);
  const [error, setError] = useState('');

  const [offerForm, setOfferForm] = useState({ offered_quantity: '', unit: '', offered_unit_price: '' });
  const [receiptForm, setReceiptForm] = useState({ received_quantity: '', unit: '', condition_note: '' });
  const [movementForm, setMovementForm] = useState({ movement_type: 'adjustment', quantity_delta: '', note: '' });

  async function reload() { await Promise.all([batches.reload(), inventory.reload(), offer.reload(), lot.reload()]); }

  async function createOffer(e: React.FormEvent) {
    e.preventDefault(); if (!selectedId) return; setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/batches/${selectedId}/procurement-offer`, 'POST', {
        offered_quantity: Number(offerForm.offered_quantity), unit: offerForm.unit, offered_unit_price: Number(offerForm.offered_unit_price),
      });
      setOfferForm({ offered_quantity: '', unit: '', offered_unit_price: '' });
      await reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create offer.'); }
  }

  async function recordReceipt(e: React.FormEvent) {
    e.preventDefault(); if (!selectedId) return; setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/batches/${selectedId}/receipt`, 'POST', {
        received_quantity: Number(receiptForm.received_quantity), unit: receiptForm.unit, condition_note: receiptForm.condition_note || null,
      });
      setReceiptForm({ received_quantity: '', unit: '', condition_note: '' });
      await reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not record receipt.'); }
  }

  async function recordMovement(e: React.FormEvent) {
    e.preventDefault(); if (!selectedId) return; setError('');
    try {
      await inputsRequest(`/admin/organic-inputs/batches/${selectedId}/inventory/movements`, 'POST', {
        movement_type: movementForm.movement_type, quantity_delta: Number(movementForm.quantity_delta), note: movementForm.note || null,
      });
      setMovementForm({ movement_type: 'adjustment', quantity_delta: '', note: '' });
      await reload();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not record movement.'); }
  }

  const selected = (batches.data ?? []).find((x) => x.id === selectedId) ?? null;

  if (!canWrite) {
    return (
      <Card>
        <h2>Procurement & Inventory</h2>
        <p>This section needs the Procurement permission (Quality Control / Owner / Super Admin).</p>
        <h3>Inventory (read-only)</h3>
        {inventory.loading ? <Loading /> : <DataTable columns={['Batch', 'Quantity available', 'Unit cost']} rows={(inventory.data ?? []).map((l) => [l.batch_id, `${l.quantity_available} ${l.unit}`, `₹${l.unit_cost}`])} />}
      </Card>
    );
  }

  return (
    <>
      {error && <p className="form-error">{error}</p>}
      <Card>
        <h2>Select a batch</h2>
        <select value={selectedId ?? ''} onChange={(e) => setSelectedId(e.target.value || null)}>
          <option value="">Select a batch…</option>
          {(batches.data ?? []).filter((x) => ['approved', 'partially_approved', 'procurement_offered', 'offer_accepted', 'received', 'quarantined', 'released_for_sale', 'sold_out'].includes(x.status)).map((x) => (
            <option key={x.id} value={x.id}>{x.batch_code} — {label(x.status)}</option>
          ))}
        </select>
      </Card>

      {selected && (
        <div className="split">
          <Card>
            <div className="section-head"><h2>Procurement offer</h2><StatusPill value={selected.status} /></div>
            {offer.data ? (
              <dl className="oi-dl">
                <div><dt>Offered</dt><dd>{offer.data.offered_quantity} {offer.data.unit} @ ₹{offer.data.offered_unit_price}</dd></div>
                <div><dt>Status</dt><dd>{label(offer.data.status)}</dd></div>
                {offer.data.rejection_reason && <div><dt>Rejection reason</dt><dd>{offer.data.rejection_reason}</dd></div>}
              </dl>
            ) : (selected.status === 'approved' || selected.status === 'partially_approved') ? (
              <form className="stack" onSubmit={createOffer}>
                <label>Offered quantity<input required type="number" min="0.001" step="0.001" value={offerForm.offered_quantity} onChange={(e) => setOfferForm({ ...offerForm, offered_quantity: e.target.value })} /></label>
                <label>Unit (must match batch unit: {selected.unit})<input required value={offerForm.unit} onChange={(e) => setOfferForm({ ...offerForm, unit: e.target.value })} /></label>
                <label>Offered unit price ₹<input required type="number" min="0.01" step="0.01" value={offerForm.offered_unit_price} onChange={(e) => setOfferForm({ ...offerForm, offered_unit_price: e.target.value })} /></label>
                <button>Make offer</button>
              </form>
            ) : <p className="oi-note">No offer for this batch yet, and this status can't receive one.</p>}
            <p className="oi-note">Accepting or rejecting the offer is the supplier's own decision, made in the mobile app — not here.</p>
          </Card>

          <Card>
            <h2>Receipt & inventory</h2>
            {lot.data ? (
              <>
                <dl className="oi-dl">
                  <div><dt>Available</dt><dd>{lot.data.quantity_available} {lot.data.unit}</dd></div>
                  <div><dt>Unit cost</dt><dd>₹{lot.data.unit_cost}</dd></div>
                </dl>
                <DataTable columns={['Type', 'Δ Qty', 'Note', 'When']} rows={lot.data.movements.map((m) => [label(m.movement_type), m.quantity_delta, m.note ?? '—', new Date(m.created_at).toLocaleString('en-IN')])} />
                <div className="oi-decide"><h3>Record a movement</h3>
                  <form className="stack" onSubmit={recordMovement}>
                    <label>Type<select value={movementForm.movement_type} onChange={(e) => setMovementForm({ ...movementForm, movement_type: e.target.value })}><option value="adjustment">Adjustment</option><option value="withdrawal">Withdrawal</option></select></label>
                    <label>Quantity change (negative to reduce)<input required type="number" step="0.001" value={movementForm.quantity_delta} onChange={(e) => setMovementForm({ ...movementForm, quantity_delta: e.target.value })} /></label>
                    <label>Note (optional)<input value={movementForm.note} onChange={(e) => setMovementForm({ ...movementForm, note: e.target.value })} /></label>
                    <button>Record movement</button>
                  </form>
                </div>
              </>
            ) : selected.status === 'offer_accepted' ? (
              <form className="stack" onSubmit={recordReceipt}>
                <label>Received quantity<input required type="number" min="0.001" step="0.001" value={receiptForm.received_quantity} onChange={(e) => setReceiptForm({ ...receiptForm, received_quantity: e.target.value })} /></label>
                <label>Unit (must match the accepted offer's unit)<input required value={receiptForm.unit} onChange={(e) => setReceiptForm({ ...receiptForm, unit: e.target.value })} /></label>
                <label>Condition note (optional)<input value={receiptForm.condition_note} onChange={(e) => setReceiptForm({ ...receiptForm, condition_note: e.target.value })} /></label>
                <button>Record receipt</button>
              </form>
            ) : <p className="oi-note">No inventory lot yet — this is created automatically when a receipt is recorded against an accepted offer.</p>}
          </Card>
        </div>
      )}

      <Card>
        <h2>All inventory</h2>
        {inventory.loading ? <Loading /> : inventory.error ? <ErrorPanel message={inventory.error} retry={() => void inventory.reload()} /> :
          <DataTable columns={['Batch', 'Quantity available', 'Unit cost', 'Created']} rows={(inventory.data ?? []).map((l) => [l.batch_id, `${l.quantity_available} ${l.unit}`, `₹${l.unit_cost}`, new Date(l.created_at).toLocaleDateString('en-IN')])} />}
      </Card>
    </>
  );
}
