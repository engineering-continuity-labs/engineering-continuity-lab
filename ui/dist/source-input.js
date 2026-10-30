export function repositoryInputError(input) {
 const value=input.trim();
 if(!/^[a-z][a-z0-9+.-]*:\/\//i.test(value))return null;
 let url;
 try{url=new URL(value);}catch{return 'Enter a valid local repository path or HTTPS Git clone URL.';}
 if(url.protocol!=='https:')return 'Use an HTTPS Git clone URL.';
 if(url.username||url.password)return 'Do not put credentials in the URL.';
 if(url.search||url.hash)return 'The clone URL must not include a query or fragment.';
 return null;
}
