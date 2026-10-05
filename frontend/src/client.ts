import type {paths} from './api-schema';
type Path = keyof paths;
export class ApiError extends Error { constructor(public status:number, message:string){super(message)} }
export const session={login:'research@demo',workspace:''};
export async function api(path:Path|string,options:RequestInit={}){
 const response=await fetch(path,{...options,headers:{'Content-Type':'application/json','X-Vip-Login':session.login,'X-Vip-Workspace':session.workspace,...options.headers}});
 const data=await response.json().catch(()=>({}));
 if(!response.ok) throw new ApiError(response.status,typeof data.detail==='string'?data.detail:'请求未完成，请检查输入后重试');
 return data;
}
export const post=(path:Path|string,data:unknown,headers?:Record<string,string>)=>api(path,{method:'POST',body:JSON.stringify(data),headers});
