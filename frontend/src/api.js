export async function api(path,{method='GET',body,blob=false}={}){
 const token=sessionStorage.getItem('sentinel-token');
 let res;
 try{res=await fetch('/api'+path,{method,headers:{...(token?{Authorization:'Bearer '+token}:{}),...(body!==undefined?{'Content-Type':'application/json'}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})})}
 catch{throw new Error('Backend unavailable. Start FastAPI on 127.0.0.1:8000.')}
 if(!res.ok){if(res.status===401&&token)window.dispatchEvent(new Event('sentinel-expired'));let message=await res.text();try{const data=JSON.parse(message);message=typeof data.detail==='string'?data.detail:(data.detail||[]).map(x=>x.msg).join('; ')}catch{}throw new Error(message||`HTTP ${res.status}`)}
 if(res.status===204)return null;
 return blob?res.blob():res.json();
}
