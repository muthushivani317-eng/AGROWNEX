import {describe,expect,it} from 'vitest';
import {crmRows} from './BuyerCRM';
import type {Procurement} from './types';
const row={offer_id:'one',admin_status:'new',buyer_name:null,buyer_offer_price:null,follow_up_at:null} as Procurement;
describe('Buyer CRM recorded facts',()=>{
  it('separates recorded buyers from matching needs',()=>{expect(crmRows([row],'Buyers')).toHaveLength(0);expect(crmRows([row],'Matching Queue')).toHaveLength(1);expect(crmRows([{...row,buyer_name:'Buyer'}],'Buyers')).toHaveLength(1);});
  it('does not treat zero-price offers as missing',()=>{expect(crmRows([{...row,buyer_offer_price:0}],'Offers')).toHaveLength(1);});
  it('counts only due valid follow-ups and excludes cancelled listings',()=>{const now=Date.parse('2026-08-31T12:00:00Z');expect(crmRows([{...row,follow_up_at:'2026-08-30T12:00:00Z'},{...row,follow_up_at:'2026-09-01T12:00:00Z'},{...row,follow_up_at:'bad'},{...row,admin_status:'cancelled',follow_up_at:'2026-08-30T12:00:00Z'}],'Follow-ups',now)).toHaveLength(1);});
});
