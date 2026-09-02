import { describe,expect,it } from 'vitest';
import { inListingGroup,listingExport } from './ProduceListings';
import type { Procurement } from './types';
const row={offer_id:'id',listing_ref:'AGP-1',farmer_ref:'AGF-1',crop:'Paddy',quantity:15,unit:'kg',admin_status:'new',buyer_contact:'SECRET',buyer_offer_price:0} as Procurement;
describe('Produce listing presentation',()=>{
  it('filters recorded pipeline stages without treating acceptance as closed',()=>{
    expect(inListingGroup(row,'New')).toBe(true);
    expect(inListingGroup(row,'Buyer Matching')).toBe(false);
    expect(inListingGroup({...row,admin_status:'finding_buyers'},'Buyer Matching')).toBe(true);
    expect(inListingGroup({...row,admin_status:'farmer_accepted'},'Closed')).toBe(false);
    expect(inListingGroup({...row,admin_status:'cancelled'},'Closed')).toBe(true);
  });
  it('exports listing facts without protected buyer data',()=>{const csv=listingExport([row]);expect(csv).toContain('AGP-1');expect(csv).not.toContain('SECRET');expect(csv).toContain('15');});
  it('neutralises formula injection in exported references',()=>{expect(listingExport([{...row,listing_ref:'=SUM(1,2)'}])).toContain("'=SUM(1,2)");});
});
