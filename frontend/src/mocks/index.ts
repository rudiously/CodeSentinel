import fixture from './scan_report.json';
import type {ScanReport} from '../api/types';
const scans:ScanReport[]=[structuredClone(fixture) as ScanReport];
export async function mockRequest(path:string,init?:RequestInit):Promise<unknown> {
  await new Promise(resolve=>setTimeout(resolve,100));
  if(path==='/auth/config')return {dev_login_enabled:true,github_enabled:false,auth_required:false};
  if(path==='/auth/dev')return {access_token:'SYNTHETIC-MOCK-SESSION',dev_only:true};
  if(path==='/repos')return [{id:1,repository:'demo/example',latest_scan:{decision:'PASS',risk_score:0.05,artifact_kind:'STUB',timestamp:'2026-10-22T12:00:00Z'}}];
  if(path==='/model/info')return {model_version:'stub-v1',model_mode:'stub',artifact_kind:'STUB',metrics:null,thresholds:{classification:0.5},limitations:['SYNTHETIC mock data','STUB predictions; no trained model','Non-C performance unvalidated']};
  if(path==='/scan'&&init?.method==='POST')throw new Error('Mock mode does not scan code. Switch to the API for a real STUB-service scan.');
  if(path.startsWith('/history/')){const scan=scans.find(s=>s.scan_id===path.split('/').pop());if(!scan)throw new Error('Scan not found');return scan;}
  if(path.startsWith('/history'))return scans;
  throw new Error('No mock for this endpoint');
}
