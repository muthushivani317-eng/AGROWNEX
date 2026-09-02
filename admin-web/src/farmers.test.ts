import { describe, expect, it } from 'vitest';
import { directoryCsv, farmerDirectoryPath, maskFarmerPhone } from './Farmers';
import type { Farmer } from './types';
describe('Farmer directory', () => {
  it('encodes server filters and pagination', () => {
    const path=farmerDirectoryPath(' Ruba & family ','Thoothukudi','Banana',2,25);
    const params=new URLSearchParams(path.split('?')[1]);
    expect(params.get('search')).toBe('Ruba & family');
    expect(params.get('district')).toBe('Thoothukudi');
    expect(params.get('page')).toBe('2');
    expect(params.get('page_size')).toBe('25');
    expect(farmerDirectoryPath('','','',1,10)).not.toContain('search=');
  });
  it('masks phone numbers including short values', () => {
    expect(maskFarmerPhone('+91 9876543210')).toBe('•••••• 3210');
    expect(maskFarmerPhone('123')).toBe('••••');
    expect(maskFarmerPhone(null)).toBe('—');
  });
  it('exports masked phones and neutralises spreadsheet formulas', () => {
    const row: Farmer={user_id:'1',farmer_ref:'AGF-1',full_name:'=SUM(1,2)',phone_number:'+919876543210',district:'A,"B"',village:null,primary_crop:'Banana',farm_count:2,created_at:null};
    const csv=directoryCsv([row]);
    expect(csv).not.toContain('+919876543210');
    expect(csv).toContain('•••••• 3210');
    expect(csv).toContain("'=SUM(1,2)");
    expect(csv).toContain('A,""B""');
  });
});
