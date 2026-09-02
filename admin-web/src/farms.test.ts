import { describe, expect, it } from 'vitest';
import { farmCoverageRows, farmCoverageCsv } from './Farms';
describe('Farm coverage',()=>{
  it('uses actual crop aggregates and matches listing crop names without case sensitivity',()=>{
    const rows=farmCoverageRows({crop_distribution:[{label:'Paddy',count:3},{label:'Cotton',count:2}],produce_by_crop:[{label:'paddy',count:1}],farmer_growth:[]});
    expect(rows).toEqual([{label:'Paddy',count:3,listings:1},{label:'Cotton',count:2,listings:0}]);
  });
  it('handles an empty analytics response',()=>{expect(farmCoverageRows({crop_distribution:[],produce_by_crop:[],farmer_growth:[]})).toEqual([]);});
  it('escapes CSV cells and spreadsheet formulas',()=>{expect(farmCoverageCsv([{label:'=SUM(1,2)',count:2,listings:0}])).toContain('"\'=SUM(1,2)"');});
});
