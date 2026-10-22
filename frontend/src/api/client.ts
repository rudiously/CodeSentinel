import {mockRequest} from '../mocks';
import type {AuthConfig,ModelInfo,Repo,ScanReport} from './types';
export const useMocks=import.meta.env.VITE_USE_MOCKS==='true';
export const apiUrl=(import.meta.env.VITE_API_URL as string|undefined)||'http://localhost:8000';
export async function request<T>(path:string,init:RequestInit={}):Promise<T>{
  if(useMocks)return await mockRequest(path,init) as T;
  const token=sessionStorage.getItem('codesentinel_token');
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),30000);
  try{
    const response=await fetch(apiUrl+path,{...init,signal:controller.signal,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{}) ,...init.headers}});
    const body=await response.json() as {error?:{message?:string};decision?:string};
    if(!response.ok && body.decision!=='ERROR')throw new Error(body.error?.message||`API returned ${response.status}`);
    return body as T;
  }finally{clearTimeout(timer)}
}
export const api={history:()=>request<ScanReport[]>('/history'),detail:(id:string)=>request<ScanReport>('/history/'+encodeURIComponent(id)),repos:()=>request<Repo[]>('/repos'),model:()=>request<ModelInfo>('/model/info'),auth:()=>request<AuthConfig>('/auth/config'),devLogin:()=>request<{access_token:string;dev_only:boolean}>('/auth/dev',{method:'POST'}),scan:(code:string)=>request<ScanReport>('/scan',{method:'POST',body:JSON.stringify({repository:'local/demo',files:[{path:'submitted.py',language:'python',code}]})})};
