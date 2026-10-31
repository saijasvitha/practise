import { useCallback,useState } from 'react';
import { issues as sampleIssues } from '../mock/issues.js';
export default function useIssues(){const [data,setData]=useState(sampleIssues);const refresh=useCallback(()=>setData([...sampleIssues]),[]);const recheck=useCallback((id)=>{setData(items=>items.map(item=>item.id===id?{...item,status:'Resolved'}:item));return Promise.resolve({verified:true,mock:true})},[]);return {issues:data,loading:false,error:null,refresh,recheck}}
